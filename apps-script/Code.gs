// Spreadsheet AI Agent — entry point, menu, sidebar launcher.
// Phase 1: open assistant; Phase 2/3 add Apply/Undo (see GOOGLE_SHEETS_ADDON.md).

function onOpen(e) {
  const ui = SpreadsheetApp.getUi();
  const menu = ui.createMenu('Spreadsheet AI');
  menu.addItem('Open assistant', 'openAssistant');
  menu.addItem('Settings', 'openSettings');
  menu.addItem('Audit history', 'openAuditHistory');
  menu.addToUi();
}

function openAssistant() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('Spreadsheet AI Assistant')
    .setWidth(360);
  SpreadsheetApp.getUi().showSidebar(html);
}

function openSettings() {
  const html = HtmlService.createHtmlOutput(
    '<p>Set backend URL and pilot client token in User Properties (not source).</p>'
  ).setTitle('Settings');
  SpreadsheetApp.getUi().showSidebar(html);
}

function openAuditHistory() {
  const html = HtmlService.createHtmlOutput('<p>Audit history UI lands in Phase 3.</p>')
    .setTitle('Audit history');
  SpreadsheetApp.getUi().showSidebar(html);
}

// Exposes backend base URL + token from User Properties (never source code).
function getClientConfig() {
  const props = PropertiesService.getUserProperties();
  return {
    backendUrl: props.getProperty('BACKEND_URL') || 'http://127.0.0.1:8000',
    clientToken: props.getProperty('CLIENT_TOKEN') || '',
  };
}
