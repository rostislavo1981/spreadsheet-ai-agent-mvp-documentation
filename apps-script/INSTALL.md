# Установка надстройки Spreadsheet AI в любую Google Таблицу

Эта инструкция показывает, как установить ИИ-копилот в **любую** Google-Таблицу
двумя способами: (1) как обычный **bound-скрипт** (быстро, приватно) или
(2) как полноценный **Google Add-on** (через меню «Надстройки»).

Публичный бэкенд уже работает: `https://sheets.projectrost.ru`.

---

## Вариант A — как bound-скрипт (быстро, 5 минут, приватно)

Подходит если таблица нужна только тебе/команде и не нужно публиковать в Marketplace.

1. Открой Google-Таблицу.
2. **Расширения → Apps Script**.
3. Удали содержимое файла `Code.gs` (по умолчанию) и **вставь код** из файлов репозитория:
   - `apps-script/Code.gs`
   - `apps-script/ContextCapture.gs`
   - `apps-script/ApiClient.gs`
   - `apps-script/ActionExecutor.gs`
   - `apps-script/Sidebar.html` → создай HTML-файл с именем `Sidebar` и вставь туда.
4. В редакторе Apps Script: **Файл → Проектные настройки**, в `appsscript.json`
   (код-файл `appsscript.json` или вкладка «Обзор проекта» → «Параметры проекта»)
   убедись, что OAuth-скопы включают `spreadsheets.currentonly`.
5. В редакторе нажми **Сохранить** (💾), затем **Выполнить → onOpen** (или просто
   обнови таблицу). Появится меню **Spreadsheet AI**.
6. Если бэкенд требует токен — в редакторе выполни:
   ```js
   setClientToken('<ваш-токен>');
   ```
   Токен выдаётся на бэкенде (скрипт `scripts/gen-client-token.sh`).

**Важно:** дефолтный URL бэкенда в `Code.gs` = `https://sheets.projectrost.ru`
(публичный, работает). Если бэкенд другой — выполни `setBackendUrl('https://...')`.

---

## Вариант B — Google Add-on (публично, через меню «Надстройки»)

Появляется в любой таблице через **Расширения → Надстройки**. Требует публикации в Google Workspace Marketplace.

### B1. Подготовка проекта (уже сделано в репозитории)
- `apps-script/appsscript.json` — манифест add-on:
  - `addOns.common.name` = «Spreadsheet AI Agent»
  - `addOns.common.logoUrl` = `https://sheets.projectrost.ru/logo.png` (публично доступен ✅)
  - `addOns.sheets` — триггер `onFileScopeGranted`
  - `urlFetchWhitelist` = `https://sheets.projectrost.ru/*`
- `Code.gs` содержит `onFileScopeGranted()`, `onHomepage()`, `onAddOnOpen()`.

### B2. Деплой через clasp
```bash
cd apps-script
npx @google/clasp login          # один раз
npx @google/clasp push --force   # залить код
npx @google/clasp deploy --description "Add-on production"  # получить версию
```
В выводе `clasp deploy` появится `Deployment ID`. Проверь:
```bash
npx @google/clasp deployments    # список: "@3" и т.д.
```

### B3. Установка в таблицу (вручную, для теста — без Marketplace)
1. **Расширения → Apps Script** → открой этот проект.
2. **Выполнить → onFileScopeGranted** (однократно, чтобы запросить доступ).
3. Перезапусти таблицу — в меню появится **Spreadsheet AI**.

### B4. Публикация в Google Workspace Marketplace (для всех)
Требует аккаунта разработчика и ревью Google:
1. Зайди в **console.cloud.google.com** → создай/выбери проект → включи
   «Google Workspace Marketplace SDK».
2. **Конфигурация приложения → Добавить приложение**:
   - URL проекта: `https://script.google.com/d/<SCRIPT_ID>/edit`
   - Тип: Google Sheets
   - Название, описание, иконка (128×128), категория «Продуктивность».
   - OAuth-согласие: скопы `spreadsheets.currentonly`, `userinfo.email`.
3. **Публикация → Проверить приложение** → пройти ревью Google (обычно 1-3 дня).
4. После одобрения надстройка появится в Marketplace; любой может установить через
   **Расширения → Надстройки → Получить надстройки** → поиск «Spreadsheet AI Agent».

---

## Использование
1. Открой таблицу → меню **Spreadsheet AI → Open Assistant**.
2. Выдели диапазон → напиши запрос → **Approve → Apply → Undo**.

## Требования к бэкенду
- Публичный HTTPS URL (`https://sheets.projectrost.ru` — уже развёрнут).
- Эндпоинты `/v1/*` и `/health/live`.
- Опциональный client token: `APP_CLIENT_TOKEN_HASHES` на бэкенде + `setClientToken()` на клиенте.
