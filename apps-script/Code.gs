// Spreadsheet AI Agent — entry point, menu, sidebar launcher.

const DEFAULT_BACKEND_URL = 'https://sheets.projectrost.ru';

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
    .setWidth(380);
  SpreadsheetApp.getUi().showSidebar(html);
}

function openSettings() {
  const cfg = getClientConfig();
  const html = HtmlService.createHtmlOutput(
    '<p style="font:13px sans-serif;padding:10px">' +
    'Backend URL: <code>' + cfg.backendUrl + '</code><br>' +
    'Client token: ' + (cfg.clientToken ? 'set' : 'empty') + '<br><br>' +
    'To change, run <code>setBackendUrl("https://...")</code> and ' +
    '<code>setClientToken("...")</code> from the script editor.</p>'
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
    backendUrl: props.getProperty('BACKEND_URL') || DEFAULT_BACKEND_URL,
    clientToken: props.getProperty('CLIENT_TOKEN') || '',
  };
}

function setBackendUrl(url) {
  PropertiesService.getUserProperties().setProperty('BACKEND_URL', url);
  return 'BACKEND_URL set to ' + url;
}

function setClientToken(token) {
  PropertiesService.getUserProperties().setProperty('CLIENT_TOKEN', token);
  return 'CLIENT_TOKEN updated';
}
