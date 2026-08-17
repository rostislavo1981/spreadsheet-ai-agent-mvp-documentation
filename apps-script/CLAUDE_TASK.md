# Задача: довести клиент Google Таблиц до уровня «Claude для Excel»

Ты — Claude Code. Работаешь в репозитории `/Users/rostislav/projects/spreadsheet-ai-agent-mvp-documentation/apps-script/`.
Это клиент (надстройка Google Apps Script) для ИИ-копилота таблиц. Бэкенд уже готов и работает.
Цель: сделать сайдбар максимально похожим на полноценный чат-копилот (как Claude для Excel / Cursor для таблиц),
а не просто поле ввода.

## Что УЖЕ есть (не ломай структуру):
- `Code.gs` — entry point, меню, `getClientConfig()` возвращает `{backendUrl, clientToken}` из User Properties.
- `ApiClient.gs` — `apiPost(path, body)`, `apiGet(path)` шлют запросы к бэкенду с Bearer-токеном. РАБОТАЕТ.
- `ContextCapture.gs` — `captureSelection(scope)` возвращает `{workbook, selection, context, cellCount}`.
- `ActionExecutor.gs` — есть заглушка `applyBundle`.
- `Sidebar.html` — ЕСТЬ, но примитивный: нет истории чата, нет выбора модели, Apply/Undo не работают.

## Бэкенд (уже работает, живой):
- Base URL (публичный, доступен из таблицы): `https://rostislavs-macbook-pro.tailc9f767.ts.net:8022`
  (дефолт в `getClientConfig` сейчас `http://127.0.0.1:8000` — ИСПРАВИТЬ на этот Tailscale-URL).
- Эндпоинты (все POST, JSON, Bearer-токен клиента опционален):
  - `GET /v1/capabilities` → `{profiles:[{id,label}], tools:[{type}], limits:{...}}`
  - `POST /v1/runs:plan` (тело PlanRequest) → `{run_id, status:"PREVIEW_READY", assistant_message, plan:{actions:[{type,target:{a1_range},rationale}]}, preview:{plan_hash, changed_cells, risk}, route:{provider,model}, usage:{input_tokens,output_tokens}}`
  - `POST /v1/runs/{run_id}:approve` `{plan_hash, current_fingerprints:[], confirmation:{}}` → `{apply_attempt_id, approval_token}`
  - `POST /v1/runs/{run_id}:result` `{apply_attempt_id, approval_token, status:"APPLIED", after_snapshot:{ranges:[]}}` → `{status}`
  - `POST /v1/runs/{run_id}:prepare-undo` `{before_snapshot:{ranges:[]}}` → `{undo_attempt_id, approval_token, undo_bundle:{actions:[...]}}`
  - `POST /v1/runs/{run_id}:undo-result` `{undo_attempt_id, approval_token, status:"RESTORED"}` → `{status:"UNDONE"}`

## ЧТО СДЕЛАТЬ (приоритетно, как в Claude для Excel):

### 1. Sidebar.html — полноценный чат-UI
- **Лента сообщений** (scrollable): пузыри user (справа) и assistant (слева) с Markdown-рендером.
- **Поле ввода** снизу + кнопка Send + Enter-to-send.
- **Выбор модели/профиля**: dropdown, заполняется из `/v1/capabilities` (profiles). ДОБАВИТЬ отдельный выбор model, если бэкенд вернёт список моделей (пока используй profiles; если моделей нет — оставь профиль).
- **Карточка превью плана** при `PREVIEW_READY`: показать `assistant_message`, список действий (тип + диапазон + rationale), `changed_cells`, `risk`, провайдер/модель.
- **Кнопки Approve / Apply / Undo** (как в Claude для Excel): после превью → Approve (подтверждение) → Apply (применение) → Undo (откат).
- **Статус-строка**: provider, tokens, ошибки.
- Тёмная/светлая тема по желанию, но аккуратно (как в Claude для Excel — минималистично).
- Используй ТОЛЬКО vanilla JS + google.script.run (никаких внешних CDN — Apps Script их блокирует). Для Markdown можно маленький self-contained парсер (bold, code, lists, headers) прямо в файле.

### 2. Code.gs — обработчики
- Исправить `getClientConfig()`: дефолт `backendUrl` = `https://rostislavs-macbook-pro.tailc9f767.ts.net:8022`.
- Добавить `setBackendUrl(url)` и `setClientToken(tok)` (запись в User Properties) — для настройки.
- Убедиться, что `captureSelection` возвращает корректный PlanRequest-совместимый объект.

### 3. ActionExecutor.gs — РЕАЛЬНОЕ применение
- `applyBundle(bundle, token)`: снимок ДО (Snapshot.before), применение действий к таблице (SET_VALUES/SET_FORMULAS/CLEAR_RANGE/FORMAT_RANGE/ADD_SHEET), возврат `{status:"APPLIED"|"FAILED", error}`.
- `undoBundle(undoBundle)`: применение undo_bundle (RESTORE_RANGE) к таблице.

### 4. ApiClient.gs — без изменений (работает), но убедись, что пути и токен корректны.

## ОГРАНИЧЕНИЯ
- НЕ меняй бэкенд (он за пределами папки apps-script и уже протестирован).
- НЕ добавляй внешние JS-библиотеки (CDN не работают в Apps Script HTML).
- Сохраняй совместимость с `google.script.run` (все вызовы асинхронные через withSuccessHandler).
- После правок запусти `../node_modules/.bin/clasp push` из папки apps-script (clasp уже авторизован, проект создан).
- НЕ коммить в git (это сделает другой агент).

## ПРОВЕРКА
После деплоя: сайдбар должен показывать чат, после ввода запроса — превью плана с действиями, кнопки Approve→Apply→Undo должны работать (apply пишет в таблицу, undo отменяет).
Для теста без реальной таблицы: убедись, что `POST /v1/runs:plan` с тестовым телом (selection I5:I7, prompt "заполни ценами 0.1 0.2 0.3") возвращает PREVIEW_READY с action SET_VALUES.

Работай автономно, доведи до рабочего результата, задеплой через clasp push. Сообщи итог в конце.
