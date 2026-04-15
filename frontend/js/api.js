const API_OVERRIDE_KEY = "pizzeria_api_url_override";

function isLocalDevHost(hostname) {
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "0.0.0.0") {
    return true;
  }

  if (hostname.startsWith("192.168.") || hostname.startsWith("10.")) {
    return true;
  }

  return /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);
}

function getApiUrl() {
  const storedOverride = localStorage.getItem(API_OVERRIDE_KEY);
  if (storedOverride) {
    return storedOverride.trim();
  }

  const { protocol, hostname, port } = window.location;

  if (port && port !== "8000" && isLocalDevHost(hostname)) {
    return `${protocol}//${hostname}:8000`;
  }

  return window.location.origin;
}

export const API_URL = getApiUrl();
const AUTH_TOKEN_KEY = "pizzeria_auth_token";

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export async function apiRequest(path, options = {}) {
  const {
    auth = true,
    headers = {},
    ...fetchOptions
  } = options;

  const finalHeaders = { ...headers };
  const token = getAuthToken();

  if (auth && token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers: finalHeaders,
  });

  const contentType = response.headers.get("content-type") || "";
  let data = null;

  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    data = text || null;
  }

  return { response, data };
}
