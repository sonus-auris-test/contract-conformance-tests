#!/usr/bin/env python3
"""Build `fixtures/interface-contract-digest.json` from the real product contract.

Reads the generated JSON Schemas that `sonus-auris/sonus-auris-interfaces`
publishes and records, per schema file: its `$id`, title, SHA-256 of the exact
bytes, the property set with normalized type shapes, the required set, and every
enum. That digest is committed, so the deterministic pull-request lane asserts
against **real product data** rather than against this repository's own model.

    SONUS_AURIS_SOURCE_ROOT=/path/to/sonus-auris \
      python scripts/build_interface_digest.py > fixtures/interface-contract-digest.json

Deterministic: sorted keys throughout, no timestamps, no host paths. Re-running
it against an unchanged product tree produces byte-identical output.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deep_tests.interface_contract import (  # noqa: E402
    SCHEMA_DIR,
    normalize_property,
    schema_source_root,
)


def build(root: Path) -> dict:
    schema_dir = root / SCHEMA_DIR
    index = json.loads((schema_dir / "index.json").read_text(encoding="utf-8"))

    schemas = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
        table, kind = path.name.split(".")[0], path.name.split(".")[1]
        properties = document.get("properties", {})
        schemas[path.name] = {
            "table": table,
            "kind": kind,
            "id": document.get("$id"),
            "title": document.get("title"),
            "type": document.get("type"),
            "additionalProperties": document.get("additionalProperties"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "required": sorted(document.get("required", [])),
            "properties": {
                name: normalize_property(schema)
                for name, schema in sorted(properties.items())
            },
        }

    return {
        "_comment": (
            "Digest of the real generated contract in sonus-auris/sonus-auris-interfaces. "
            "Product data, not authored here: property names, required sets, enums and "
            "per-file SHA-256 are copied verbatim from the pinned checkout. Rebuild with "
            "scripts/build_interface_digest.py; never hand-edit to make a test pass."
        ),
        "fixture": "interface-contract-digest",
        "generator": "scripts/build_interface_digest.py",
        "schema_dir": SCHEMA_DIR,
        "index": {
            "entries": sorted(
                ({"table": e["table"], "kind": e["kind"], "path": e["path"]} for e in index["tables"]),
                key=lambda e: (e["table"], e["kind"]),
            )
        },
        "schemas": dict(sorted(schemas.items())),
    }


if __name__ == "__main__":
    json.dump(build(schema_source_root()), sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
