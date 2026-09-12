"""Product adapter tests for the generated `sonus-auris-interfaces` contract.

The reference-model tests in `test_contract_conformance.py` stay untouched and
keep serving as the oracle. This module makes the oracle's assumptions checkable
against a real product artifact, so a change in `sonus-auris-interfaces` can
actually break this repository.

Lanes
-----
`InterfaceContractDigestTests` — always on. Asserts against
`fixtures/interface-contract-digest.json`, which holds real property names,
required sets, enums and per-file SHA-256 lifted from the pinned product tree.

`InterfaceContractDriftTests` — gated on `SONUS_AURIS_SOURCE_ROOT`. Re-hashes
the live schema files and fails on any drift from the digest. Unset is a blocked
dependency; set-but-wrong is a hard failure, never a skip.
"""

from __future__ import annotations

import os
import unittest

from deep_tests.contract_model import Command, replay
from deep_tests.interface_contract import (
    ENV_SOURCE_ROOT,
    live_schema_hashes,
    load_digest,
    normalize_property,
    schema_source_root,
    tables,
    client_supplied_required,
    server_derived_required,
)

DIGEST = load_digest()
TABLES = tables(DIGEST)


class InterfaceContractDigestTests(unittest.TestCase):
    """Structural conformance of the real generated contract."""

    def test_the_index_lists_exactly_the_schemas_that_exist(self) -> None:
        """An unlisted schema is invisible to consumers; a listed-but-absent one
        breaks every generator that walks the index."""
        listed = {
            (entry["table"], entry["kind"]) for entry in DIGEST["index"]["entries"]
        }
        present = {
            (entry["table"], entry["kind"]) for entry in DIGEST["schemas"].values()
        }
        self.assertEqual(listed, present)
        for entry in DIGEST["index"]["entries"]:
            with self.subTest(entry=entry["path"]):
                self.assertTrue(entry["path"].endswith(".schema.json"))
                self.assertTrue(entry["path"].startswith("generated/json-schema/"))

    def test_every_table_publishes_both_a_row_and_an_insert_shape(self) -> None:
        self.assertGreaterEqual(len(TABLES), 1)
        for table, kinds in TABLES.items():
            with self.subTest(table=table):
                self.assertEqual(set(kinds), {"row", "insert"})

    def test_every_schema_is_a_closed_object(self) -> None:
        """`additionalProperties: false` is what makes an unknown client field
        fail closed instead of being silently dropped on the way to the table."""
        for name, entry in DIGEST["schemas"].items():
            with self.subTest(schema=name):
                self.assertEqual(entry["type"], "object")
                self.assertIs(entry["additionalProperties"], False)

    def test_schema_ids_and_titles_are_unique(self) -> None:
        ids = [entry["id"] for entry in DIGEST["schemas"].values()]
        titles = [entry["title"] for entry in DIGEST["schemas"].values()]
        self.assertTrue(all(ids), "every schema must publish an $id")
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(titles)), len(titles))

    def test_an_insert_can_always_produce_a_valid_row(self) -> None:
        """Insert properties must be a subset of row properties, with identical
        shapes. Otherwise a client writes a field the row cannot represent."""
        for table, kinds in TABLES.items():
            insert_props = kinds["insert"]["properties"]
            row_props = kinds["row"]["properties"]
            with self.subTest(table=table):
                self.assertLessEqual(set(insert_props), set(row_props))
                for name in sorted(insert_props):
                    with self.subTest(property=name):
                        self.assertEqual(
                            normalize_property(insert_props[name]),
                            normalize_property(row_props[name]),
                        )

    def test_insert_never_requires_a_column_the_row_does_not_carry(self) -> None:
        for table, kinds in TABLES.items():
            with self.subTest(table=table):
                self.assertLessEqual(
                    set(kinds["insert"]["required"]), set(kinds["row"]["properties"])
                )

    def test_row_required_columns_all_exist_as_properties(self) -> None:
        for name, entry in DIGEST["schemas"].items():
            with self.subTest(schema=name):
                self.assertLessEqual(set(entry["required"]), set(entry["properties"]))

    def test_the_tenant_column_is_server_derived_on_every_table(self) -> None:
        """Fleet-wide tenant isolation as expressed in the contract: no table may
        let a client name the owning `user_id` on insert."""
        checked = 0
        for table, kinds in TABLES.items():
            if "user_id" not in kinds["row"]["properties"]:
                continue
            checked += 1
            with self.subTest(table=table):
                self.assertIn("user_id", kinds["row"]["required"])
                self.assertNotIn("user_id", kinds["insert"]["required"])
                self.assertIn("user_id", server_derived_required(DIGEST, table))
        self.assertGreater(checked, 0, "no user-scoped table found in the contract")

    def test_enums_are_non_empty_and_duplicate_free(self) -> None:
        """A generator emitting an empty or duplicated enum produces a type no
        client value can satisfy."""
        seen = 0
        for name, entry in DIGEST["schemas"].items():
            for prop, schema in entry["properties"].items():
                values = schema.get("enum") if isinstance(schema, dict) else None
                if values is None:
                    continue
                seen += 1
                with self.subTest(schema=name, property=prop):
                    self.assertTrue(values)
                    self.assertEqual(len(set(map(str, values))), len(values))
        self.assertGreater(seen, 0, "the contract should constrain some columns by enum")


class DeviceRegistryOracleBindingTests(unittest.TestCase):
    """Bind the idempotency oracle to a real table instead of `entity-N`.

    `devices` is the multi-device registry: `MULTI_DEVICE.md` has each install
    upsert its own row at sign-in. That upsert is exactly the idempotent
    command the `ReferenceStore` oracle models, so the oracle's claims are
    replayed here over keys derived from the *product's* required columns.
    """

    def setUp(self) -> None:
        self.assertIn("devices", TABLES, "the product no longer publishes a devices contract")
        self.devices = TABLES["devices"]

    def test_the_devices_contract_supplies_a_client_addressable_install_id(self) -> None:
        """`device_id` is the per-install key the oracle's `entity_id` stands in
        for: a client must supply it on every registration upsert."""
        self.assertIn("device_id", client_supplied_required(DIGEST, "devices"))

    def test_the_owning_user_is_server_derived_not_client_supplied(self) -> None:
        """`user_id` is row-required and insert-forbidden on `devices`, so a
        client cannot register an install into somebody else's account. This is
        the schema-level half of the IDOR boundary `SECURITY.md` records as
        "identity is derived from the token-hash DB lookup, never client input"."""
        self.assertIn("user_id", self.devices["row"]["required"])
        self.assertNotIn("user_id", client_supplied_required(DIGEST, "devices"))
        self.assertIn("user_id", server_derived_required(DIGEST, "devices"))

    def test_the_devices_contract_can_express_a_soft_revocation(self) -> None:
        """The oracle has a delete/tombstone lane. It is only meaningful if the
        real table can represent a removal that is not a hard delete."""
        revoked = self.devices["row"]["properties"].get("revoked_at")
        self.assertIsNotNone(revoked, "devices.row no longer carries revoked_at")
        self.assertIn("anyOf", revoked)
        self.assertIn({"type": "null"}, revoked["anyOf"])

    def test_the_devices_contract_distinguishes_recorder_from_viewer(self) -> None:
        """The desktop master viewer and a recording phone must be separable in
        the registry, or the multi-device read model has no server-side shape."""
        role = self.devices["row"]["properties"].get("role")
        self.assertIsNotNone(role, "devices.row no longer carries role")
        self.assertEqual(sorted(role["enum"]), ["recorder", "viewer"])

    def test_replaying_real_device_upserts_converges_and_suppresses_duplicates(self) -> None:
        """The oracle, driven by product-shaped keys, over the product's own enums."""
        key_columns = client_supplied_required(DIGEST, "devices")
        platforms = self.devices["row"]["properties"]["platform"]["enum"]
        commands = []
        for index, platform in enumerate(platforms):
            entity_id = "|".join(f"{column}=synthetic-{index}" for column in key_columns)
            commands.append(
                Command(
                    kind="create",
                    entity_id=entity_id,
                    value=platform,
                    idempotency_key=f"register-{index}",
                )
            )
            commands.append(
                Command(
                    kind="update",
                    entity_id=entity_id,
                    value=f"{platform}-heartbeat",
                    idempotency_key=f"heartbeat-{index}",
                )
            )
        first = replay(commands, duplicate_every=1)
        second = replay(commands, duplicate_every=3)
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual(first.revision, len(commands))


@unittest.skipIf(
    not os.environ.get(ENV_SOURCE_ROOT),
    f"{ENV_SOURCE_ROOT} not set: the interfaces checkout is a blocked dependency, "
    "not a pass (the committed contract digest still runs unconditionally)",
)
class InterfaceContractDriftTests(unittest.TestCase):
    """Re-hash the live product schemas. Set-but-wrong must fail, never skip."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = schema_source_root()
        cls.live = live_schema_hashes(cls.root)

    def test_the_schema_set_has_not_gained_or_lost_a_file(self) -> None:
        self.assertEqual(set(self.live), set(DIGEST["schemas"]))

    def test_every_schema_file_still_hashes_to_the_committed_digest(self) -> None:
        for name, digest_entry in sorted(DIGEST["schemas"].items()):
            with self.subTest(schema=name):
                self.assertEqual(
                    self.live[name],
                    digest_entry["sha256"],
                    f"{name} changed in sonus-auris-interfaces; rebuild the digest with "
                    "scripts/build_interface_digest.py and review the contract diff",
                )

    def test_the_digest_is_reproducible_from_the_live_tree(self) -> None:
        import importlib.util
        from pathlib import Path

        script = Path(__file__).resolve().parents[1] / "scripts" / "build_interface_digest.py"
        spec = importlib.util.spec_from_file_location("build_interface_digest", script)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.build(self.root), DIGEST)


if __name__ == "__main__":
    unittest.main()
