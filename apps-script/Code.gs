// Spreadsheet AI Agent — entry point, menu, sidebar launcher.

const DEFAULT_BACKEND_URL = 'https://sheets.projectrost.ru';

function onOpen(e) {
  // For Marketplace add-ons Google injects the add-on menu automatically;
  // we still ensure the assistant entries exist (works both as add-on and bound script).
  const ui = SpreadsheetApp.getUi();
  const menu = ui.createMenu('Spreadsheet AI');
  menu.addItem('Open assistant', 'openAssistant');
  menu.addItem('Settings', 'openSettings');
  menu.addItem('Audit history', 'openAuditHistory');
  menu.addToUi();
}

// Triggered by add-on install: adds the menu once the add-on is installed.
function onAddOnOpen() {
  const ui = SpreadsheetApp.getUi();
  const menu = ui.createAddonMenu();
  menu.addItem('Open assistant', 'openAssistant');
  menu.addItem('Settings', 'openSettings');
  menu.addItem('Audit history', 'openAuditHistory');
  menu.addToUi();
}

// Re-adds the menu after the user grants the spreadsheet file scope
// (only for add-ons; bound scripts rely on onOpen).
function onFileScopeGranted() {
  onAddOnOpen();
}

// Homepage card (addOns.common.homepageTrigger): what the user sees when
// opening the add-on from the Workspace Marketplace / add-ons manager.
function onHomepage(e) {
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('Spreadsheet AI Agent'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph().setText(
        'ИИ-ассистент для Google Таблиц: выделите диапазон, задайте вопрос — ' +
        'получите план изменений и примените его одной кнопкой.'
      ))
      .addWidget(CardService.newButtonSet().addButton(
        CardService.newTextButton()
          .setText('Open assistant')
          .setTextButtonStyle(CardService.TextButtonStyle.FILLED)
          .setBackgroundColor('#2563eb')
          .setOnClickAction(CardService.newAction().setFunctionName('openAssistant'))
      )))
    .build();
  return card;
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
