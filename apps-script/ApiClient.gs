// ApiClient.gs — talks to the backend /v1 endpoints (no provider keys, ever).
// Pilot bearer token from User Properties; never logged.

function apiPost(path, body) {
  const cfg = getClientConfig();
  const url = cfg.backendUrl.replace(/\/$/, '') + path;
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + cfg.clientToken },
    payload: JSON.stringify(body),
    muteHttpExceptions: true,
  };
  const resp = UrlFetchApp.fetch(url, options);
  const code = resp.getResponseCode();
  const text = resp.getContentText();
  if (code >= 400) {
    return { ok: false, status: code, body: safeParse(text) };
  }
  return { ok: true, status: code, body: safeParse(text) };
}

function apiGet(path) {
  const cfg = getClientConfig();
  const url = cfg.backendUrl.replace(/\/$/, '') + path;
  const options = {
    method: 'get',
    headers: { Authorization: 'Bearer ' + cfg.clientToken },
    muteHttpExceptions: true,
  };
  const resp = UrlFetchApp.fetch(url, options);
  const code = resp.getResponseCode();
  return { ok: code < 400, status: code, body: safeParse(resp.getContentText()) };
}

function safeParse(text) {
  try { return JSON.parse(text); } catch (e) { return { raw: text }; }
}
