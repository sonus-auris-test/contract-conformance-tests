# Durable Object environment parity contract

Cloudflare Durable Object infrastructure must be checked as an environment matrix, not only as a valid base Wrangler file.

For preview, staging, and production:

- preserve the canonical Durable Object binding name and class name;
- preserve the declared storage mode (`sqlite`) for the exported class;
- require an explicit environment binding because Durable Object bindings are not treated as an inherited test assumption;
- keep preview URLs/environment exposure intentional per environment;
- keep Terraform Worker-shell creation opt-in until account/root wiring is explicitly supplied;
- ensure any Terraform worker name/environment tags agree with the intended Wrangler environment identity.

A base-config pass with a missing or divergent environment binding is a failure. A Terraform validation pass with a broken Wrangler/DO contract is also a failure.
