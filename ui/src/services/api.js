const BACKEND_PORT = 8765;
const BACKEND_HOST = '127.0.0.1';

// When running inside Tauri (tauri://localhost), Vite dev (port 5174), or standalone:
// Route HTTP requests directly to the FastAPI gateway at 127.0.0.1:8765.
export const API_BASE = (
  typeof window !== 'undefined' &&
  (window.location.protocol === 'http:' || window.location.protocol === 'https:') &&
  (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
)
  ? ''
  : `http://${BACKEND_HOST}:${BACKEND_PORT}`;

export function apiUrl(endpoint) {
  if (!endpoint) return API_BASE;
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) return endpoint;
  const cleanPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE}${cleanPath}`;
}

export async function apiFetch(endpoint, options = {}) {
  const url = apiUrl(endpoint);
  return fetch(url, options);
}

export async function apiGet(endpoint) {
  const res = await apiFetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: Failed to fetch ${endpoint}`);
  }
  return res.json();
}

export async function apiPost(endpoint, data = {}) {
  const res = await apiFetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: Failed to post to ${endpoint}`);
  }
  return res.json();
}

export async function apiPut(endpoint, data = {}) {
  const res = await apiFetch(endpoint, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: Failed to put to ${endpoint}`);
  }
  return res.json();
}

export async function apiDelete(endpoint) {
  const res = await apiFetch(endpoint, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: Failed to delete ${endpoint}`);
  }
  return res.json();
}
