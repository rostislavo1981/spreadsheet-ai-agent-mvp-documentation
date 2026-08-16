// ActionExecutor.gs — applies approved bundles locally via batched Range calls.
// Implements GOOGLE_SHEETS_ADDON.md §6: validate → snapshot → execute → flush → report.
// Never uses eval / generated Apps Script / URLs from model output.

function applyBundle(bundle, approvalToken) {
  // 1. validate bundle version + action types against advertised capabilities
  if (!bundle || bundle.schema_version !== '1.0') throw new Error('unsupported bundle version');
  const sheetById = {};
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.getSheets().forEach(function(sh) { sheetById[sh.getSheetId()] = sh; });

  // 2. resolve + normalize every target
  const actions = bundle.actions || [];
  actions.forEach(function(a) {
    const t = a.target;
    if (!t) return;
    const sh = sheetById[t.sheet_id];
    if (!sh) throw new Error('unknown sheet_id ' + t.sheet_id);
    const range = sh.getRange(t.a1_range);
    // re-validate dimensions
    const args = a.arguments || {};
    if (a.type === 'SET_VALUES' || a.type === 'SET_FORMULAS') {
      const matrix = args.values || args.formulas || [];
      if (matrix.length !== range.getHeight() || matrix[0].length !== range.getWidth()) {
        throw new Error('dimension mismatch for ' + t.a1_range);
      }
    }
  });

  // 3. capture before snapshot (values + formulas + cell-kind mask)
  const before = snapshotTargets(actions, sheetById);

  // 4-5. execute ordered batched actions; rollback on failure
  try {
    actions.forEach(function(a) { executeAction(a, sheetById); });
    SpreadsheetApp.flush();
  } catch (e) {
    restoreSnapshot(before, sheetById);
    SpreadsheetApp.flush();
    return { status: 'FAILED_ROLLED_BACK', error: String(e) };
  }
  return { status: 'APPLIED', before: before };
}

function executeAction(a, sheetById) {
  const t = a.target;
  const sh = sheetById[t.sheet_id];
  const range = sh.getRange(t.a1_range);
  const args = a.arguments || {};
  switch (a.type) {
    case 'SET_VALUES': {
      const values = args.values;
      // formula-trigger escaping for literal strings
      const escaped = values.map(function(row) {
        return row.map(function(cell) {
          if (typeof cell === 'string' && ['=', '+', '-', '@'].indexOf(cell[0]) !== -1) {
            return "'" + cell;
          }
          return cell;
        });
      });
      range.setValues(escaped);
      break;
    }
    case 'SET_FORMULAS':
      range.setFormulas(args.formulas);
      break;
    case 'CLEAR_RANGE':
      range.clearContent();
      break;
    case 'FORMAT_RANGE': {
      if (args.background) range.setBackground(args.background);
      if (args.font_color) range.setFontColor(args.font_color);
      if (args.font_weight) range.setFontWeight(args.font_weight);
      if (args.number_format) range.setNumberFormat(args.number_format);
      if (args.horizontal_alignment) range.setHorizontalAlignment(args.horizontal_alignment);
      if (args.wrap !== undefined) range.setWrap(args.wrap);
      break;
    }
    case 'ADD_SHEET':
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      const title = sanitizeSheetTitle(args.title);
      const created = ss.insertSheet(title, ss.getSheets().length);
      if (args.rows) created.setRowCount(args.rows);
      if (args.columns) created.setColumnCount(args.columns);
      break;
    case 'NO_OP':
      break;
    default:
      throw new Error('unknown action type ' + a.type);
  }
}

function snapshotTargets(actions, sheetById) {
  const snaps = [];
  (actions || []).forEach(function(a) {
    const t = a.target;
    if (!t) return;
    const sh = sheetById[t.sheet_id];
    const range = sh.getRange(t.a1_range);
    snaps.push({
      sheet_id: t.sheet_id, a1_range: t.a1_range,
      values: range.getValues(), formulas: range.getFormulas(),
    });
  });
  return snaps;
}

function restoreSnapshot(snaps, sheetById) {
  snaps.forEach(function(s) {
    const sh = sheetById[s.sheet_id];
    const range = sh.getRange(s.a1_range);
    // restore formulas as formulas, literals as values (cell-kind mask)
    const restored = s.values.map(function(row, i) {
      return row.map(function(_, j) {
        return s.formulas[i][j] ? s.formulas[i][j] : s.values[i][j];
      });
    });
    range.setValues(restored);
  });
}

function sanitizeSheetTitle(title) {
  return String(title).replace(/[\\/?*\[\]:]/g, '_').slice(0, 100);
}
