# sonus-auris-test/contract-conformance-tests

Deterministic state-model, idempotency, serialization, and protocol contract conformance tests.

This repository is the `contract` deep-test suite for `sonus-auris`. It is intentionally dependency-light and deterministic so failures can be reproduced locally without production credentials or customer data.

## Run

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/verify_repository.py
```

The initial model is executable rather than a placeholder. Product adapters should be added through focused pull requests while preserving the reference-model tests as an oracle.

The auth oracle also models fresh-sign-in navigation and the account-deletion
re-authentication boundary: Home is mandatory after a completed sign-in, and
destructive deletion needs the exact account email plus a recent phone or TOTP
proof.

## Product adapter: the generated interfaces contract

The state model above is an oracle and stays that way. Alongside it,
`src/deep_tests/interface_contract.py` binds the oracle's assumptions to a real
product artifact — the JSON Schemas that `sonus-auris/sonus-auris-interfaces`
generates for every Supabase table — so a contract change in the product can
break this repository.

Two lanes:

- **Always on, no product checkout.** `fixtures/interface-contract-digest.json`
  holds real property names, required sets, enums and per-file SHA-256 lifted
  from the pinned interfaces checkout. The structural conformance rules run
  against that product data on every pull request: the index lists exactly the
  schemas that exist, every schema is a closed object, an insert can always
  produce a valid row, no insert requires a column the row does not carry, and
  **no table lets a client name the owning `user_id`** — the schema-level half
  of the IDOR boundary `SECURITY.md` records.
- **Gated on `SONUS_AURIS_SOURCE_ROOT`.** The live schema files are re-hashed
  and must still match the digest; adding, removing or editing a schema fails
  here. Unset is a blocked dependency (skip, with the always-on lane still
  running); set-but-wrong is a hard failure, never a skip.

The `devices` table is bound explicitly: it is the multi-device registry each
install upserts at sign-in, so the oracle's idempotency and convergence claims
are replayed over `devices`' own required columns and `platform`/`role` enums
rather than over synthetic `entity-N` ids.

Rebuild the digest after an intentional contract change:

```bash
SONUS_AURIS_SOURCE_ROOT=/path/to/sonus-auris \
  PYTHONPATH=src python scripts/build_interface_digest.py \
  > fixtures/interface-contract-digest.json
```

Never hand-edit the digest to make a test pass; regenerate it and review the
contract diff.

Tracking: https://github.com/ORESoftware/ai-agent-coordinator.rs/issues/139
