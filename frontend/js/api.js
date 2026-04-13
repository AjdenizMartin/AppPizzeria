export const API_URL = "http://127.0.0.1:8000";
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
