# Google Sheets Add-on (Apps Script)

Боковая панель-копилот: выделил диапазон → спросил → получил превью плана →
принял (Approve) → применил (Apply) → при необходимости откатил (Undo).

**UI теперь полноценный чат (как в Claude для Excel):**
- История сообщений (пузыри user/assistant) с Markdown-рендером
- Выбор профиля/модели из `/v1/capabilities`
- Карточка превью плана: действия, затронутые ячейки, риск, провайдер
- Кнопки **Approve → Apply → Undo** (реально пишут/откатывают в таблице)
- Статус-строка: провайдер, токены, ошибки

## Файлы

- `Code.gs` — точка входа, меню, `getClientConfig()`, `setBackendUrl()`, `setClientToken()`
- `ContextCapture.gs` — захват контекста выделения (values/display/formulas + fingerprint)
- `ApiClient.gs` — вызовы backend `/v1/*` (ключи провайдеров НЕ хранятся здесь)
- `ActionExecutor.gs` — локальное применение одобренного бандла + snapshot/rollback (SET_VALUES, SET_FORMULAS, CLEAR_RANGE, FORMAT_RANGE, ADD_SHEET, RESTORE_RANGE)
- `Sidebar.html` — чат-UI (история, ввод, превью, Approve/Apply/Undo, статус)
- `appsscript.json` — манифест (scopes: currentonly, locale, email)

## Деплой (нужен Google-аккаунт с доступом к таблице)

1. Установить clasp: `npm i -g @google/clasp` (или локально `npm i @google/clasp`)
2. Авторизоваться: `clasp login` (откроется браузер)
3. Создать/привязать проект:
   - новый: `clasp create --type sheets --title "Spreadsheet AI Agent"`
   - к существующему: `clasp clone <SCRIPT_ID>`
4. Настроить `appsscript.json` (уже готов) и положить `.clasp.json` с `scriptId`.
5. Залить: `clasp push`
6. В таблице: Расширения → Apps Script → запустить `onOpen`, обновить таблицу.
   Появится меню **Spreadsheet AI → Open Assistant**.

## Backend-конфиг

Бэкенд должен быть доступен по **публичному HTTPS** (Apps Script на серверах Google не достанет localhost).

- В `Code.gs` задан `DEFAULT_BACKEND_URL = 'https://rostislavs-macbook-pro.tailc9f767.ts.net:8022'` (Tailscale, работает в tailnet).
- При необходимости сменить URL: в редакторе Apps Script выполнить `setBackendUrl("https://your-public-backend/v1")`.
- Токен пилота (если нужен): `setClientToken("<token>")` — хранится в User Properties.

Без публичного URL бэкенда сайдбар покажет "loading..." и не заработает.

## Текущий рабочий публичный URL

- **Tailscale**: `https://rostislavs-macbook-pro.tailc9f767.ts.net:8022` ✅ (нужен доступ к tailnet)
- **Cloudflare**: `https://spreadsheet.projectrost.ru` ❌ (заблокирован провайдером — часть edge IP недоступна). Требует Cloudflare WARP или другой провайдер.

## Безопасность

- Модель не пишет код в таблицу; только структурированные allowlisted-действия.
- Apply требует явного нажатия; токен подписан и с истечением срока.
- Snapshot снимается до применения → Undo локален и детерминирован.
- Никаких `eval`, `UrlFetch` на произвольные URL из вывода модели.
- Провайдерские ключи и Hermes-секреты — только на сервере бэкенда.