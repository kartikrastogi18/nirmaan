/**
 * Every network call in this app goes through apiRequest(). This is the
 * frontend mirror of app/errors.py on the backend: rather than wrapping
 * every individual fetch() in its own try/catch and hoping nobody forgets
 * one, there's a single function that always catches failures and always
 * shows a toast. A network drop, a timeout, a 500, a validation 400 --
 * none of them can fail silently, because there's nowhere else a request
 * could be made from.
 */
const API_BASE = "/api";

let accessToken = localStorage.getItem("nirmaan_access_token");
let refreshToken = localStorage.getItem("nirmaan_refresh_token");

function setTokens({ access_token, refresh_token } = {}) {
  if (access_token) { accessToken = access_token; localStorage.setItem("nirmaan_access_token", access_token); }
  if (refresh_token) { refreshToken = refresh_token; localStorage.setItem("nirmaan_refresh_token", refresh_token); }
}

function clearTokens() {
  accessToken = null; refreshToken = null;
  localStorage.removeItem("nirmaan_access_token");
  localStorage.removeItem("nirmaan_refresh_token");
}

function isLoggedIn() {
  return !!accessToken;
}

async function refreshAccessToken() {
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, { method: "POST", headers: { Authorization: `Bearer ${refreshToken}` } });
    if (!response.ok) return false;
    const data = await response.json();
    setTokens(data);
    return true;
  } catch (_err) { return false; }
}

async function apiRequest(path, { method = "GET", body, auth = true, silent = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    window.dispatchEvent(new CustomEvent("nirmaan:network", { detail: { state: "offline" } }));
    if (!silent) showToast("Connection lost. Check your network and try again.", "error");
    throw networkError;
  }

  let data;
  try {
    data = await response.json();
  } catch (parseError) {
    showToast("The server sent back something unexpected.", "error");
    throw parseError;
  }

  if (!response.ok) {
    if (response.status === 401 && auth && !path.includes("/auth/refresh") && await refreshAccessToken()) {
      return apiRequest(path, { method, body, auth, silent });
    }
    if (response.status === 401 && auth) {
      clearTokens();
      if (typeof state !== "undefined") {
        state.user = null; state.projects = []; state.currentProject = null;
        if (typeof render === "function") queueMicrotask(render);
      }
    }
    if (!silent) showToast(data.error || `Request failed (${response.status}).`, "error");
    const err = new Error(data.error || `Request failed (${response.status}).`);
    err.status = response.status;
    err.body = data;
    throw err;
  }

  window.dispatchEvent(new CustomEvent("nirmaan:network", { detail: { state: "online" } }));
  return data;
}

async function apiFormRequest(path, formData, { method = "POST" } = {}) {
  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { method, headers, body: formData });
  } catch (networkError) {
    window.dispatchEvent(new CustomEvent("nirmaan:network", { detail: { state: "offline" } }));
    showToast("Connection lost. Check your network and try again.", "error");
    throw networkError;
  }
  let data = {};
  try { data = await response.json(); } catch (_err) { /* handled below */ }
  if (!response.ok) {
    if (response.status === 401) { clearTokens(); if (typeof state !== "undefined") { state.user = null; state.projects = []; state.currentProject = null; if (typeof render === "function") queueMicrotask(render); } }
    showToast(data.error || `Request failed (${response.status}).`, "error");
    throw new Error(data.error || `Request failed (${response.status}).`);
  }
  window.dispatchEvent(new CustomEvent("nirmaan:network", { detail: { state: "online" } }));
  return data;
}

async function apiBlob(path) {
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  const response = await fetch(path.startsWith("/api/") ? path : `${API_BASE}${path}`, { headers });
  if (!response.ok) throw new Error(`Media request failed (${response.status}).`);
  return response.blob();
}
