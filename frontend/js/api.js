"use strict";
const API_BASE_URL =
  ["localhost", "127.0.0.1"].includes(window.location.hostname) &&
  window.location.port === "5500"
    ? "http://127.0.0.1:8000/api"
    : "/api";
// JWTs remain in sessionStorage. localStorage holds only a non-secret epoch/version.
const AuthStorage = (() => {
  const markerKey = 'icm_session_state';
  const tagKey = 'icm_session_tag';
  const uuid = () => typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  let volatileState = null, bootstrap = null, accountChanged = false;
  const waiters = new Map();
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('icm-auth-v1') : null;
  const validState = value => value && typeof value.id === 'string' &&
    typeof value.active === 'boolean' && Number.isSafeInteger(value.version) && value.version >= 0;
  function state() {
    try { const value = JSON.parse(localStorage.getItem(markerKey)); return validState(value) ? value : volatileState; }
    catch { return volatileState; }
  }
  function writeState(value) {
    volatileState = value;
    try { localStorage.setItem(markerKey, JSON.stringify(value)); } catch { /* per-tab fallback */ }
  }
  function tag() {
    try { return JSON.parse(sessionStorage.getItem(tagKey)); } catch { return null; }
  }
  function clearLocal() {
    for (const key of ['icm_access', 'icm_refresh', tagKey]) sessionStorage.removeItem(key);
  }
  function hidePrivate() {
    if (typeof document === 'undefined') return;
    for (const id of ['dashboard-app', 'resumes-app', 'job-match-app', 'career-app', 'history-app']) {
      const element = document.getElementById(id); if (element) element.hidden = true;
    }
  }
  function redirectLoggedOut() {
    hidePrivate();
    if (typeof location !== 'undefined' && !/(login|register)\.html$/.test(location.pathname)) window.location.replace('./login.html');
  }
  function reconcile(notify = false) {
    const current = state(), local = tag();
    // One-time migration of an existing per-tab login from the previous client.
    if (!current && !local && sessionStorage.getItem('icm_access') && sessionStorage.getItem('icm_refresh')) {
      const migrated = {id: uuid(), version: 0, active: true};
      writeState(migrated); sessionStorage.setItem(tagKey, JSON.stringify(migrated));
      return migrated;
    }
    if (sessionStorage.getItem('icm_access') && (!current?.active || current.id !== local?.id)) {
      accountChanged = !!current?.active;
      clearLocal();
      if (notify) hidePrivate();
    }
    // A getter may have already cleared tokens before the storage event arrives.
    if (notify && current?.active === false) { clearLocal(); redirectLoggedOut(); }
    return current;
  }
  function tokens() {
    const current = reconcile(), local = tag();
    if (!current?.active || local?.id !== current.id) return null;
    const access = sessionStorage.getItem('icm_access'), refresh = sessionStorage.getItem('icm_refresh');
    return access && refresh ? {state: local, access, refresh} : null;
  }
  function post(message) { channel?.postMessage(message); }
  function accept(message) {
    const current = state();
    if (!current?.active || current.id !== message.state?.id || current.version !== message.state.version ||
        typeof message.access !== 'string' || typeof message.refresh !== 'string') return false;
    const old = tag();
    const reload = accountChanged || (old && old.id !== current.id);
    sessionStorage.setItem('icm_access', message.access);
    sessionStorage.setItem('icm_refresh', message.refresh);
    sessionStorage.setItem(tagKey, JSON.stringify(current));
    accountChanged = false;
    if (reload && typeof location !== 'undefined' && !/(login|register)\.html$/.test(location.pathname)) {
      hidePrivate(); window.location.reload();
    }
    return true;
  }
  async function discover() {
    reconcile();
    if (!channel || state()?.active === false) return;
    const request = uuid();
    await new Promise(resolve => {
      const timer = setTimeout(() => { waiters.delete(request); resolve(); }, 500);
      waiters.set(request, () => { clearTimeout(timer); waiters.delete(request); resolve(); });
      post({type: 'request', request});
    });
  }
  if (channel) channel.onmessage = ({data: message}) => {
    if (!message || typeof message !== 'object') return;
    if (message.type === 'request') {
      const own = tokens();
      if (own && own.state.version === state()?.version) post({type: 'reply', request: message.request, ...own});
    } else if (message.type === 'reply') {
      if (waiters.has(message.request) && accept(message)) waiters.get(message.request)?.();
    } else if (message.type === 'update') accept(message);
    else if (message.type === 'logout') { reconcile(true); }
  };
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('storage', event => { if (event.key === markerKey) reconcile(true); });
    window.addEventListener('pageshow', () => reconcile(true));
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') reconcile(true);
    });
  }
  // Reconcile even on login pages and restored documents before any guard runs.
  reconcile();
  return {
    getAccessToken: () => { reconcile(); return sessionStorage.getItem('icm_access'); },
    getRefreshToken: () => { reconcile(); return sessionStorage.getItem('icm_refresh'); },
    getEpoch: () => { reconcile(); return tag()?.id || null; },
    async ready() {
      if (tokens()) return;
      if (!bootstrap) bootstrap = discover().finally(() => { bootstrap = null; });
      await bootstrap;
    },
    discover,
    saveTokens(access, refresh) {
      const current = {id: uuid(), version: 0, active: true};
      writeState(current);
      sessionStorage.setItem('icm_access', access); sessionStorage.setItem('icm_refresh', refresh);
      sessionStorage.setItem(tagKey, JSON.stringify(current));
      post({type: 'update', state: current, access, refresh});
    },
    updateTokens(access, refresh, epoch) {
      const current = state();
      if (!current?.active || current.id !== epoch) throw sessionChanged();
      const next = {...current, version: current.version + 1};
      writeState(next);
      sessionStorage.setItem('icm_access', access); sessionStorage.setItem('icm_refresh', refresh);
      sessionStorage.setItem(tagKey, JSON.stringify(next));
      post({type: 'update', state: next, access, refresh});
    },
    clearLocal,
    clear() {
      clearLocal(); writeState({id: uuid(), version: 0, active: false});
      post({type: 'logout'});
    }
  };
})();
function sessionEnded(shared = true) {
  if (shared) AuthStorage.clear(); else AuthStorage.clearLocal();
  const error = new Error("Sesi sudah berakhir. Silakan login kembali.");
  error.sessionExpired = true;
  return error;
}
function sessionChanged() {
  const error = new Error("Sesi berubah. Muat ulang halaman untuk melanjutkan.");
  error.sessionExpired = !AuthStorage.getEpoch();
  return error;
}
function extractErrorMessage(body, fallback) {
  return [body?.error?.message, body?.error, body?.detail, body?.message]
    .find(value => typeof value === "string") || fallback;
}
function responseError(body, status) {
  const error = new Error(status >= 500
    ? "Server sedang bermasalah. Silakan coba lagi."
    : extractErrorMessage(body, `Permintaan gagal (HTTP ${status}).`));
  error.status = error.httpStatus = status;
  // Only known validation fields are exposed; never render raw payloads or HTML.
  error.details = {};
  if (status === 400) {
    const details = body?.error?.details ?? body;
    for (const key of ["username", "email", "password", "non_field_errors"]) {
      const values = Array.isArray(details?.[key]) ? details[key] : [details?.[key]];
      const messages = values.filter(v => typeof v === "string").slice(0, 5).map(v => v.slice(0, 500));
      if (messages.length) error.details[key] = messages;
    }
  }
  return error;
}
async function sendRequest(endpoint, {method = "GET", body = null, authenticated = false} = {}) {
  const headers = {Accept: "application/json"};
  if (authenticated) headers.Authorization = `Bearer ${AuthStorage.getAccessToken()}`;
  const multipart = body instanceof FormData;
  if (body !== null && !multipart) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method, headers, body: body === null ? undefined : multipart ? body : JSON.stringify(body)
    });
  } catch {
    const error = new Error("Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.");
    error.networkError = true;
    throw error;
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.status === "error") throw responseError(result, response.status);
  return result.data ?? result;
}
let refreshInFlight = null;
async function refreshAccessToken(failedToken = AuthStorage.getAccessToken()) {
  if (!refreshInFlight) {
    const epoch = AuthStorage.getEpoch();
    const refresh = async () => {
      // Queued tabs first retrieve the result produced by the lock holder.
      await AuthStorage.discover();
      if (AuthStorage.getEpoch() !== epoch) throw sessionChanged();
      if (AuthStorage.getAccessToken() !== failedToken) return AuthStorage.getAccessToken();
      const token = AuthStorage.getRefreshToken();
      if (!token) throw sessionEnded(false);
      try {
        const result = await sendRequest('/auth/refresh/', {method: 'POST', body: {refresh: token}});
        if (AuthStorage.getEpoch() !== epoch) throw sessionChanged();
        if (!result.access) throw new Error('Respons sesi tidak lengkap. Silakan coba lagi.');
        AuthStorage.updateTokens(result.access, result.refresh || token, epoch);
        return result.access;
      } catch (error) {
        if (AuthStorage.getEpoch() !== epoch) throw sessionChanged();
        if ([400, 401].includes(error.status)) throw sessionEnded();
        throw error;
      }
    };
    refreshInFlight = typeof navigator !== 'undefined' && navigator.locks?.request
      ? navigator.locks.request('icm-refresh-v1', refresh) : refresh();
  }
  const pending = refreshInFlight;
  try { return await pending; } finally { if (refreshInFlight === pending) refreshInFlight = null; }
}
async function apiRequest(endpoint, options = {}) {
  if (options.authenticated) await AuthStorage.ready();
  const token = AuthStorage.getAccessToken(), epoch = AuthStorage.getEpoch();
  if (options.authenticated && !token) throw sessionEnded(false);
  const validateSession = result => {
    if (options.authenticated && AuthStorage.getEpoch() !== epoch) throw sessionChanged();
    return result;
  };
  try { return validateSession(await sendRequest(endpoint, options)); }
  catch (error) {
    if (!options.authenticated || error.status !== 401) throw error;
    if (AuthStorage.getEpoch() !== epoch) throw sessionChanged();
    if (AuthStorage.getAccessToken() === token) await refreshAccessToken(token);
    if (!AuthStorage.getAccessToken()) throw sessionEnded(false);
    try {
      // Only explicit DRF authentication rejection may replay once; never 5xx/network.
      return validateSession(await sendRequest(endpoint, options));
    } catch (retryError) {
      if (retryError.status === 401 && AuthStorage.getEpoch() === epoch) throw sessionEnded();
      throw retryError;
    }
  }
}
function setRequestLoading(button, busy, label) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
  button.replaceChildren();
  if (busy && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const spinner = document.createElement("span");
    spinner.className = "icm-spinner";
    spinner.setAttribute("aria-hidden", "true");
    button.append(spinner, document.createTextNode(" "));
  }
  button.append(document.createTextNode(label));
}
const ICMApi = {
  login: (username, password) => apiRequest("/auth/login/", {method: "POST", body: {username, password}}),
  register: (username, email, password) => apiRequest("/auth/register/", {method: "POST", body: {username, email, password}}),
  getMe: () => apiRequest("/auth/me/", {authenticated: true}),
  refreshAccessToken,
  handleSessionError(error) {
    if (!error?.sessionExpired) return false;
    window.location.replace("./login.html");
    return true;
  },
  listResumes: () => apiRequest("/resume/list/", {authenticated: true}),
  uploadResume(file) {
    const body = new FormData(); body.append("cv_file", file);
    return apiRequest("/resume/upload/", {method: "POST", body, authenticated: true});
  },
  createJobMatch: (resume_id, job_text) => apiRequest("/analysis/match/", {method: "POST", body: {resume_id, job_text}, authenticated: true}),
  generateCareer: resume_id => apiRequest("/recommendations/generate/", {method: "POST", body: {resume_id}, authenticated: true}),
  listCareerRecommendations: () => apiRequest("/recommendations/", {authenticated: true}),
  getCareerRecommendation: id => apiRequest(`/recommendations/${encodeURIComponent(id)}/`, {authenticated: true}),
  listJobMatches: () => apiRequest("/analysis/matches/", {authenticated: true})
};
