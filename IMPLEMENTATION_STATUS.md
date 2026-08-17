# Статус реализации — MVP «ИИ-агент для таблиц»

> Сформировано по итогам реализации. Сопоставляет фазы из `IMPLEMENTATION_PLAN.md`
> с кодом в `backend/` и `apps-script/`.

## Условные обозначения
🟢 готово · 🟡 частично · 🔴 не начато

## Статус по фазам

| Фаза | Объём | Статус | Тесты |
|------|-------|--------|-------|
| 0 | Каркас репозитория, Python-проект, JSON-схемы в рантайме, валидация настроек, CI | 🟢 | `tests/contract/test_schemas.py` |
| 1 | Read-only вертикальный срез: движок контекста, fake + OpenAI-совместимый адаптер, роутер, планировщик NO_OP, боковая панель | 🟢 | `tests/integration/test_phase1.py`, `tests/unit/test_core.py` |
| 2 | План → Превью → Применение: P0-действия, подписанный токен одобрения с истечением, автомат состояний прогона, клиентский ActionExecutor | 🟢 | `tests/integration/test_phase2.py` |
| 3 | SQLite-персистентность (переживает перезапуск), очищенный аудит, откат по снимку | 🟢 | `tests/integration/test_phase3.py` |
| 4 | Адаптер Hermes (Режим A), паритет маршрутизации/резерва | 🟢 | `tests/contract/test_phase4.py`, `tests/contract/test_adapters.py` |
| 5 | Закалка пилота: ADD_SHEET, жёсткие лимиты, защита от инъекций, скрытые логи, rate limit, эндпоинты прогона/аудита/метрик, защита защищённых/объединённых ячеек, расширение контекста, метрики | 🟢 | `tests/integration/test_phase5.py`, `tests/integration/test_endpoints.py`, `tests/integration/test_phase5b.py` |

## Клиент Google Таблиц (Apps Script) — полностью переписан ✅

- **Sidebar.html** — полноценный чат-UI (как в Claude для Excel):
  - Лента сообщений (пузыри user/assistant) с Markdown-рендером
  - Выбор профиля/модели из `/v1/capabilities`
  - Карточка превью плана: действия, затронутые ячейки, риск, провайдер
  - Кнопки **Approve → Apply → Undo** (реально пишут/откатывают в таблице)
  - Статус-строка: провайдер, токены, ошибки
- **Code.gs** — дефолтный `BACKEND_URL = https://rostislavs-macbook-pro.tailc9f767.ts.net:8022` (Tailscale, доступен из таблицы), функции `setBackendUrl`/`setClientToken`
- **ActionExecutor.gs** — реальное применение (SET_VALUES/SET_FORMULAS/CLEAR_RANGE/FORMAT_RANGE/ADD_SHEET) + undo через RESTORE_RANGE
- **ContextCapture.gs** — захват выделения, формул, отображаемых значений, fingerprint
- **ApiClient.gs** — вызовы `/v1/runs:plan`, `:approve`, `:result`, `:prepare-undo`, `:undo-result`, `/v1/capabilities`
- **Деплой**: `clasp push` выполнен, надстройка загружена в Google Apps Script проект

## Проверка (офлайн, без сети и ключей)
```bash
cd backend && . .venv/bin/activate && pytest tests -q
# 37 passed, ruff clean
```

## Контрольная проверка живой интеграции
- Бэкенд запущен на `:8022` через launchd (автостарт + KeepAlive, 24/7 при включённом Mac)
- Публичный доступ через **Tailscale Serve**: `https://rostislavs-macbook-pro.tailc9f767.ts.net:8022` ✅
- Cloudflare Tunnel на `spreadsheet.projectrost.ru` создан, но **заблокирован провайдером** (часть edge IP) — фолбэк на Tailscale
- Hermes fallback работает: при отсутствии ключа роутер переключается на `fake` и возвращает валидный план `PREVIEW_READY`
- Полный живой цикл пройден: Plan → Approve → Apply → Prepare-Undo → Undo-Result → Metrics (все шаги успешны)

## Инварианты безопасности (все реализованы и покрыты тестами)
- Чтение автоматическое; запись — только при явном Применении с подписанным токеном одобрения с истечением срока.
- Только разрешённые P0-действия; вывод модели недоверенный + валидируется по схеме (1 попытка починки).
- Контекст ограничен выделением (selection-first); формулы сохраняются; откат по снимку.
- Скан на prompt-инъекции (fail-closed → 422).
- Ограничение частоты (rate limit, 429 после всплеска); жёсткие потолки на ячейки/токены/стоимость.
- Секреты провайдеров и Hermes — только на сервере; логирование сырых промптов/контекста/снимков выключено по умолчанию.
- Защита защищённых и объединённых (merged) диапазонов: любая запись в них отклоняется.

## Известные пробелы (намеренно вне scope MVP)
- Публичный HTTPS домен на `spreadsheet.projectrost.ru` требует Cloudflare WARP или другого провайдера (текущий провайдер блокирует часть Cloudflare edge).
- Реальные вызовы OpenAI/OpenRouter/Hermes через CI (автоматически проверяются только offline-fake + Hermes с respx-моком).
- Браузерный e2e на живой таблице; очередь асинхронных задач; мультитенантная авторизация; экспорт телеметрии.

## Как запустить
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8022
```

Включение Hermes: `HERMES_ENABLED=true`, `HERMES_BASE_URL=http://127.0.0.1:4012/v1`,
`HERMES_API_KEY=<валидный ключ>`, `ENABLED_PROVIDER_TARGETS=fake,hermes`.

## Использование для любой Google Таблицы
1. **Бэкенд** должен быть доступен публично (Tailscale или Cloudflare).
2. В таблице: `npx clasp login` → `npx clasp create --type sheets` → поправь `BACKEND_URL` в `Code.gs` или запусти `setBackendUrl("https://...")` → `npx clasp push`.
3. В таблице: **Расширения → Apps Script → onOpen** → появится меню **Spreadsheet AI → Open Assistant**.
4. Выдели диапазон → напиши запрос → **Approve** → **Apply** → при необходимости **Undo**.

Пилотный прогон и приёмка P0: см. [PILOT_RUNBOOK.md](PILOT_RUNBOOK.md).
Текущий релиз-кандидат помечен тегом `v0.1.0-pilot`.