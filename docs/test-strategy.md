# Deep test strategy

## Scope

Suite: `contract`
Test organization: `sonus-auris-test`
Primary organization: `sonus-auris`

## Invariants

- every randomized test uses an explicit deterministic seed;
- retries, duplicates, migrations, and rejected inputs are observable assertions, not sleeps;
- test data is synthetic and contains no production credentials or customer payloads;
- the suite runs without network access by default;
- a product adapter must preserve the reference model and publish the seed and minimized trace on failure;
- account access fails closed: signed-out and AAL1 states always outrank recovery, onboarding, voice unlock, and application-shell state;
- every newly completed sign-in resets the application tab to Home, while an ordinary authenticated-session restore may preserve the last tab;
- account deletion requires an exact signed-in email confirmation plus a phone or authenticator proof no more than five minutes old, with at most 60 seconds of future clock skew;
- scheduled CI is defense in depth; pull-request and main-branch checks remain authoritative.

## Expansion path

1. Add a versioned adapter for the primary repository contract.
2. Add sanitized golden fixtures owned by the canonical interface repository.
3. Run the same trace against the reference model and implementation.
4. Retain failing seeds as regression tests.
5. Link behavior changes to the matching Linear issue and repository PR.

## Product adapter — generated interfaces contract

`src/deep_tests/interface_contract.py` reads the generated JSON Schemas from
`sonus-auris/sonus-auris-interfaces` (pinned in `source-pins.json`). The
reference model in `contract_model.py` is preserved unchanged as the oracle; the
adapter binds its abstractions to real columns:

| Oracle abstraction | Product artifact it is bound to |
|---|---|
| `Command.entity_id` | `devices.insert.required` — the per-install `device_id` a client must supply |
| command payload domain | `devices.row.properties.platform.enum`, `role.enum` |
| tombstone / soft delete | `devices.row.properties.revoked_at` (nullable) |
| tenant boundary | `user_id` required on every row, forbidden on every insert |

Always-on lane asserts the committed digest (real product data). Gated lane
re-hashes the live tree and fails on drift. `SONUS_AURIS_SOURCE_ROOT` unset is a
blocked dependency; set-but-wrong is a hard failure.

Verified by mutating a scratch copy of the interfaces checkout: making
`devices.insert` require `user_id`, renaming a schema title, and removing a
schema file each produced failing tests, and a `SONUS_AURIS_SOURCE_ROOT`
pointing outside the interfaces repository produced a hard error rather than a
skip.
