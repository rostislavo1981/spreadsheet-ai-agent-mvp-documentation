# Google Sheets Add-on (Apps Script)

Боковая панель-копилот: выделил диапазон → спросил → получил превью плана →
принял (Approve) → применил (Apply) → при необходимости откатил (Undo).

## Файлы
- `Code.gs` — точка входа, меню, запуск Sidebar
- `ContextCapture.gs` — захват контекста выделения (values/display/formulas + fingerprint)
- `ApiClient.gs` — вызовы backend `/v1/*` (ключи провайдеров НЕ хранятся здесь)
- `ActionExecutor.gs` — локальное применение одобренного бандла + snapshot/rollback
- `Sidebar.html` — UI (selection chip, prompt, preview, Approve/Apply/Undo)
- `appsscript.json` — манифест (scopes: currentonly, locale, email)

## Деплой (нужен Google-аккаунт с доступом к таблице)
1. Установить clasp: `npm i -g @google/clasp`
2. Авторизоваться: `clasp login`
3. Создать/привязать проект:
   - новый: `clasp create --type sheets --title "Spreadsheet AI Agent"`
   - к существующему: `clasp clone <SCRIPT_ID>`
4. Настроить `appsscript.json` (уже готов) и положить `.clasp.json` с `scriptId`.
5. Залить: `clasp push`
6. В таблице: Расширения → Apps Script → запустить `onOpen`, обновить таблицу.
   Появится меню **Spreadsheet AI Agent → Open Assistant**.

## Backend-конфиг (на клиенте)
Токен пилота хранится в User Properties (не в коде):
```
PropertiesService.getUserProperties().setProperty('AGENT_PILOT_TOKEN', '<token>')
PropertiesService.getUserProperties().setProperty('AGENT_BACKEND_URL', 'https://your-backend/v1')
```
Без токена `/v1/runs:plan` вернёт 401.

## Безопасность
- Модель не пишет код в таблицу; только структурированные allowlisted-действия.
- Apply требует явного нажатия; токен подписан и с истечением срока.
- Snapshot снимается до применения → Undo локален и детерминирован.
- Никаких `eval`, `UrlFetch` на произвольные URL из вывода модели.
