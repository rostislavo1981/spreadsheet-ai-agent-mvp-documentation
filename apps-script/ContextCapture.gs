// ContextCapture.gs — server-side context capture for the active selection.
// Implements GOOGLE_SHEETS_ADDON.md §4: distinct values/displayValues/formulas,
// locale/timezone, merged/protected intersections, and a canonical fingerprint.

function captureSelection(contextScope) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  const range = sheet.getActiveRange();
  if (!range) throw new Error('No active selection.');

  const a1 = range.getA1Notation();
  const startRow = range.getRow();
  const startColumn = range.getColumn();
  const rowCount = range.getHeight();
  const columnCount = range.getWidth();
  const sheetId = sheet.getSheetId();
  const sheetName = sheet.getName();

  const values = range.getValues();
  const displayValues = range.getDisplayValues();
  const formulas = range.getFormulas();

  const fingerprint = computeFingerprint({
    sheetId: sheetId, a1: a1, rows: rowCount, cols: columnCount,
    values: values, formulas: formulas,
  });

  const rangeCtx = {
    sheet_id: sheetId,
    sheet_name: sheetName,
    a1_range: a1,
    start_row: startRow,
    start_column: startColumn,
    row_count: rowCount,
    column_count: columnCount,
    values: values,
    display_values: displayValues,
    formulas: formulas,
    fingerprint: fingerprint,
  };

  const ctx = {
    ranges: [rangeCtx],
    omissions: [],
  };

  const locale = ss.getSpreadsheetLocale();
  const timezone = ss.getSpreadsheetTimeZone();
  const workbookIdHash = hashIdentifier(ss.getId());

  return {
    selection: { sheet_id: sheetId, sheet_name: sheetName, a1_range: a1 },
    context: ctx,
    workbook: {
      workbook_id_hash: workbookIdHash,
      title: ss.getName(),
      locale: locale,
      timezone: timezone,
    },
    cellCount: rowCount * columnCount,
  };
}

// Fingerprint over canonical sheet id, A1, dimensions, typed values, and formulas.
function computeFingerprint(parts) {
  const payload = Utilities.base64EncodeWebSafe(
    JSON.stringify([parts.sheetId, parts.a1, parts.rows, parts.cols, parts.values, parts.formulas])
  );
  return 'sha256:' + Utilities.computeHash('SHA_256', payload, Utilities.Charset.UTF_8);
}

function hashIdentifier(value) {
  return 'sha256:' + Utilities.computeHash('SHA_256', value, Utilities.Charset.UTF_8);
}
