# Sonus infrastructure oracle contract

The sibling org certifies only immutable `sonus-auris-infra` revisions.

- Pin the source PR/head SHA and every mirrored private-source file by Git blob SHA.
- Verify mirrored bytes before running tests.
- Run Terraform `fmt -check`, `init -backend=false -input=false`, and `validate` for preview, staging, and production.
- Never run `terraform apply` from the sibling org.
- Keep provider-native configuration under canonical module roots and keep `environments/` composition-only.
- Reject Git-tracked Terraform state/cache.

For the Durable Object coordinator, each Wrangler environment must preserve the same binding name/class and the declared SQLite storage export. A green Terraform result does not replace this Worker/DO contract check, and vice versa.

Any source or mirrored blob change requires a new oracle receipt.
