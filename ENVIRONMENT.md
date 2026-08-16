# Environment Configuration

Copy `.env.example` to `.env` for local development. `.env` is ignored and must never be committed. In deployed environments, inject equivalent values through the platform's secret/configuration service.

## Groups

- `APP_*`: runtime, SQLite URL, approval signing, hashed identifiers, and client authentication.
- `MAX_*`, timeouts, TTLs, and cost values: hard product guardrails. Code must validate them on startup and reject unsafe/invalid combinations.
- `ENABLED_PROVIDER_TARGETS` and `DEFAULT_ROUTING_PROFILE`: router configuration. A target references an adapter plus model/profile configuration; profile is not a raw model name.
- `FAKE_PROVIDER_*`: deterministic offline development and CI.
- `OPENAI_COMPATIBLE_*`: one configurable compatible endpoint. Use deployment config for multiple targets.
- convenience API key variables: optional; only native/configured adapters may read their own key.
- `HERMES_*`: explicit transport mode, endpoint, planner profile, tool policy, session isolation, and deadline.
- observability: telemetry endpoint and explicit unsafe logging switches. All raw-data switches remain `false` in normal environments.

## Required local values

For offline development: strong unique `APP_SIGNING_SECRET` and `APP_ID_HASH_SALT`; fake provider enabled. For a real provider, also enable/configure its target and key. For Hermes, set `HERMES_ENABLED=true`, select the verified mode, and provide credentials/profile.

## Validation rules

- Production refuses placeholder/short signing secrets and salts.
- Provider and Hermes base URLs require HTTPS except loopback development.
- `HERMES_TOOL_POLICY` must be `planner_only` in P0 production.
- TTLs, deadlines, attempts, cells, tokens, and costs must be positive and within compiled safety ceilings.
- An enabled target without required credentials/model fails configuration clearly; it is not silently skipped.
- `LOG_PROMPTS`, `LOG_SPREADSHEET_CONTEXT`, and `LOG_SNAPSHOTS` require explicit development-only override and redaction tests.

Apps Script has separate user settings: backend URL and pilot client token in User Properties. Provider keys and `APP_SIGNING_SECRET` never belong in Apps Script settings.

