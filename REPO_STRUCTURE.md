# Repository Structure

```text
spreadsheet-ai-agent/
├── README.md
├── AGENTS.md
├── PRD.md
├── ARCHITECTURE.md
├── MVP_SCOPE.md
├── IMPLEMENTATION_PLAN.md
├── PROVIDER_ADAPTERS.md
├── HERMES_INTEGRATION.md
├── GOOGLE_SHEETS_ADDON.md
├── API_CONTRACTS.md
├── TOOL_REGISTRY.md
├── PLANNER_PROMPT.md
├── SECURITY_GUARDRAILS.md
├── TEST_PLAN.md
├── ACCEPTANCE_CRITERIA.md
├── AGENT_IMPLEMENTATION_PROMPT.md
├── REPO_STRUCTURE.md
├── ROADMAP.md
├── .env.example
├── schemas/
│   ├── common.schema.json
│   ├── agent-plan.schema.json
│   ├── plan-request.schema.json
│   └── plan-response.schema.json
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                 # FastAPI routes, auth, error mapping
│   │   ├── core/                # settings, IDs, logging, limits
│   │   ├── domain/              # provider/run/action/context types
│   │   ├── context/             # selection-first packing
│   │   ├── planning/            # prompt, schema parse, repair
│   │   ├── policy/              # deterministic guardrails
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── router.py
│   │   │   └── implementations/
│   │   │       ├── fake.py
│   │   │       ├── openai_compatible.py
│   │   │       └── hermes.py
│   │   ├── tools/               # registry and validators
│   │   ├── runs/                # state machine/services
│   │   ├── audit/               # repository interfaces
│   │   └── persistence/         # SQLite models/migrations
│   └── tests/
│       ├── unit/
│       ├── contract/
│       ├── integration/
│       └── fixtures/
├── apps-script/
│   ├── appsscript.json
│   ├── Code.gs
│   ├── ContextCapture.gs
│   ├── ActionExecutor.gs
│   ├── Fingerprint.gs
│   ├── ApiClient.gs
│   ├── Properties.gs
│   ├── Sidebar.html
│   ├── SidebarJS.html
│   ├── Styles.html
│   └── tests/                    # clasp-compatible local tests where practical
├── config/
│   └── providers.example.yaml
├── scripts/
│   ├── dev.sh
│   ├── lint.sh
│   └── test.sh
└── docs/
    ├── decisions/                # future ADRs
    ├── pilot-runbook.md
    └── troubleshooting.md
```

## Dependency rules

- `domain` imports no FastAPI, vendor SDK, persistence, or Apps Script concerns.
- `providers/implementations` depend on provider-domain interfaces, never on tool executors.
- `planning` may read Tool Registry schemas but cannot execute tools.
- `api` orchestrates application services and maps transport models; business logic stays outside routes.
- Apps Script depends only on published JSON contracts, not Python implementation details.
- Schemas are source-controlled compatibility artifacts; generated Pydantic/TypeScript types must be checked for drift.

## Naming

- `run`: one planning lifecycle and possible apply/undo.
- `plan`: immutable validated proposed actions.
- `action_bundle`: approved, expiring executable representation of a plan.
- `apply_attempt`: one client execution attempt.
- `provider attempt`: one outbound model/orchestrator call.
- `profile`: user-facing routing policy, not necessarily a model.

## Versioning

API, plan schema, and each tool have independent major/minor versions. Additive optional fields increment minor versions. Removing/changing semantics requires a major version and an explicit migration window.
