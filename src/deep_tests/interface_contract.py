"""Product adapter: the generated `sonus-auris-interfaces` JSON-Schema contract.

The reference model in `contract_model.py` is an oracle for idempotency,
convergence and replay. On its own it proves nothing about `sonus-auris` — it is
a CRUD store agreeing with itself. This adapter binds the oracle's assumptions
to a real, versioned product artifact: the JSON Schemas that
`sonus-auris/sonus-auris-interfaces` generates for every Supabase table.

Two lanes:

* **Always on** — `fixtures/interface-contract-digest.json` carries the real
  property names, required sets, enums and per-file SHA-256 from a pinned
  product checkout. The structural conformance rules run against that on every
  pull request, with no product tree present.
* **Gated** — with `SONUS_AURIS_SOURCE_ROOT` pointing at a checkout of the
  pinned `sonus-auris-interfaces`, the live schema files are re-hashed and must
  still match the digest. Adding, removing or editing a schema fails here.

Fail-closed: env unset -> :class:`SchemaSourceUnavailable` (blocked dependency,
reported as a skip while the always-on lane still runs). Env set but wrong ->
:class:`SchemaBindingError`, a hard failure that never degrades to a pass.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

ENV_SOURCE_ROOT = "SONUS_AURIS_SOURCE_ROOT"
INTERFACES_REPO = "sonus-auris-interfaces"
SCHEMA_DIR = f"{INTERFACES_REPO}/generated/json-schema"

ROOT = Path(__file__).resolve().parents[2]
DIGEST_PATH = ROOT / "fixtures" / "interface-contract-digest.json"

# Ignored when comparing an insert property against its row counterpart: prose
# may reasonably differ between the two, the shape may not.
PROSE_KEYS = frozenset({"description", "title", "$comment", "examples"})


class SchemaSourceUnavailable(RuntimeError):
    """No product checkout configured. Blocked dependency, not a pass."""


class SchemaBindingError(AssertionError):
    """A product checkout is configured but is not the pinned contract."""


def normalize_property(schema: Any) -> Any:
    """Strip prose so two property schemas can be compared by shape alone."""
    if isinstance(schema, dict):
        return {
            key: normalize_property(value)
            for key, value in sorted(schema.items())
            if key not in PROSE_KEYS
        }
    if isinstance(schema, list):
        return [normalize_property(item) for item in schema]
    return schema


def load_digest(path: Path | None = None) -> Dict[str, Any]:
    return json.loads((path or DIGEST_PATH).read_text(encoding="utf-8"))


def schema_source_root(explicit: str | None = None) -> Path:
    raw = explicit if explicit is not None else os.environ.get(ENV_SOURCE_ROOT)
    if not raw:
        raise SchemaSourceUnavailable(
            f"{ENV_SOURCE_ROOT} is not set; the interfaces checkout is a blocked dependency"
        )
    root = Path(raw).expanduser()
    schema_dir = root / SCHEMA_DIR
    if not schema_dir.is_dir():
        raise SchemaBindingError(
            f"{ENV_SOURCE_ROOT}={raw!r} does not contain {SCHEMA_DIR}"
        )
    if not (schema_dir / "index.json").is_file():
        raise SchemaBindingError(f"{schema_dir} has no index.json")
    return root


def live_schema_hashes(root: Path) -> Dict[str, str]:
    schema_dir = root / SCHEMA_DIR
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(schema_dir.glob("*.schema.json"))
    }


def tables(digest: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """`{table: {"row": schema_entry, "insert": schema_entry}}` from the digest."""
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for entry in digest["schemas"].values():
        grouped.setdefault(entry["table"], {})[entry["kind"]] = entry
    return grouped


def client_supplied_required(digest: Dict[str, Any], table: str) -> tuple[str, ...]:
    """Columns a client must supply on insert.

    This is the concrete thing the `contract_model.ReferenceStore` oracle
    abstracts as the command payload plus `entity_id`; binding it to a real
    table is what makes the oracle's idempotency claim about `sonus-auris`
    rather than about itself.
    """
    return tuple(sorted(tables(digest)[table]["insert"]["required"]))


def server_derived_required(digest: Dict[str, Any], table: str) -> tuple[str, ...]:
    """Columns the row requires but the client is not allowed to supply.

    Row-required minus insert-required. These are defaulted server-side —
    `user_id` from `auth.uid()`, `created_at` from the insert time — which is the
    schema-level expression of the backend rule recorded in `SECURITY.md`:
    identity is derived from the token, never from client input.
    """
    entry = tables(digest)[table]
    return tuple(sorted(set(entry["row"]["required"]) - set(entry["insert"]["required"])))
