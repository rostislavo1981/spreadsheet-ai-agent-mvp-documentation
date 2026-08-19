# Бэкенд ИИ-агента для таблиц (MVP)

Независимый от провайдера бэкенд ИИ-копилота для Google Таблиц, собранный по
спецификации `spreadsheet-ai-agent-mvp-documentation`. План → Превью → явное
Применение. Только разрешённые P0-действия. Фирнгерпринт-конфликт, снимковый
откат, фолбэк провайдера, скрытое логирование, rate-limit.

## Архитектура (кратко)

```
backend/
├── app/
│   ├── api/           # FastAPI routes: /v1/runs:plan, :approve, :result, :prepare-undo, :undo-result, /v1/capabilities, /v1/audit, /v1/metrics
│   ├── context/engine.py     # ContextEngine: pack_context, scope expansion
│   ├── policy/service.py     # P0-валидация, защита защищённых/объединённых ячеек
│   ├── providers/router.py   # Приоритетный роутер с фолбэком (Hermes → fake)
│   ├── providers/implementations/  # fake, openai_compatible, hermes
│   ├── persistence/  # SQLite: runs + audit (survives restart)
│   ├── audit/        # Sanitized audit trail (no prompts/contexts/snapshots)
│   └── core/settings.py      # Pydantic Settings (env-driven)
├── tests/            # 61 passed: unit + contract + integration
├── data/agent.sqlite3 (gitignored)
├── .venv/ (gitignored)
├── .env.example
└── pyproject.toml
```

## Быстрый старт

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
# Вариант А: fake-провайдер (offline, CI)
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8022
# Вариант Б: Hermes fallback (нужен Hermes gateway на :4012/v1)
HERMES_ENABLED=true HERMES_BASE_URL=http://127.0.0.1:4012/v1 ENABLED_PROVIDER_TARGETS=fake,hermes uvicorn ...
```

## Публичный доступ (для клиента Apps Script)

Бэкенд должен быть доступен по HTTPS из интернета (Apps Script на серверах Google не достанет localhost).

- **Основной публичный домен** (работает): `https://sheets.projectrost.ru` — требует bearer-токен клиента (`APP_CLIENT_TOKEN_HASHES`).
- **Tailscale Serve** (запасной): `https://rostislavs-macbook-pro.tailc9f767.ts.net:8022` — требует tailnet.
- **Cloudflare Tunnel** (`spreadsheet.projectrost.ru`) — заблокирован провайдером (edge IP); требует Cloudflare WARP.

Дефолт в `Code.gs` — `https://sheets.projectrost.ru`.

## Запуск как сервисы (24/7 на Mac)

```bash
# Backend (launchd, автостарт + KeepAlive)
launchctl load ~/Library/LaunchAgents/com.spreadsheet-agent.backend.plist
launchctl start com.spreadsheet-agent.backend

# Cloudflare Tunnel (launchd)
launchctl load ~/Library/LaunchAgents/com.spreadsheet-agent.cloudflared.plist
launchctl start com.spreadsheet-agent.cloudflared
```

## Тесты

```bash
cd backend && . .venv/bin/activate
pytest tests -q        # 61 passed
ruff check app         # clean
```

## Эндпоинты (основные)

- `POST /v1/runs:plan` — построить план (PlanRequest → PREVIEW_READY)
- `POST /v1/runs/{id}:approve` — подписать токен одобрения
- `POST /v1/runs/{id}:result` — отчёт о применении (клиент)
- `POST /v1/runs/{id}:prepare-undo` — готовит undo_bundle + токен отката
- `POST /v1/runs/{id}:undo-result` — подтверждает откат
- `GET /v1/capabilities` — профили, инструменты, лимиты
- `GET /v1/audit` — очищенный аудит
- `GET /v1/metrics` — санитизированные счётчики
- `GET /health/live` — liveness

## Инварианты безопасности

- Чтение авто; запись — только после Apply с подписанным токеном.
- Только 6 P0-инструментов (SET_VALUES, SET_FORMULAS, CLEAR_RANGE, FORMAT_RANGE, ADD_SHEET, NO_OP).
- Selection-first, формулы сохраняются, откат по снимку.
- Prompt-injection scan (fail-closed 422).
- Rate limit (429), hard limits (cells/tokens/cost/attempts).
- Секреты провайдеров/Hermes — только сервер.
- Защита protected/merged ranges (write → reject).
- Context expansion с лимитом ячеек.

## Ссылки

- [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) — полный чек-лист
- [PILOT_RUNBOOK.md](../PILOT_RUNBOOK.md) — пилотный прогон
- [ИСПОЛЬЗОВАНИЕ.md](../ИСПОЛЬЗОВАНИЕ.md) — как подключить к любой таблице