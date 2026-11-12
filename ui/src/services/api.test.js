import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const invokeMock = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: invokeMock,
}));

import {
  apiUrl,
  fetchSessionToken,
  getSessionTokenSync,
  setSessionToken,
  apiFetch,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
} from './api';

describe('api service', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    setSessionToken(null);
    delete window.__JARVIS_TOKEN__;
    localStorage.clear();
    invokeMock.mockReset();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('formats endpoint URLs correctly', () => {
    expect(apiUrl('')).toMatch(/^http:\/\/127\.0\.0\.1:8765$|^$/);
    expect(apiUrl('test')).toMatch(/\/test$/);
    expect(apiUrl('/test')).toMatch(/\/test$/);
    expect(apiUrl('http://localhost:8765/custom')).toBe('http://localhost:8765/custom');
    expect(apiUrl('https://example.com/api')).toBe('https://example.com/api');
  });

  it('stores and retrieves session tokens synchronously from cache, window, and localStorage', () => {
    expect(getSessionTokenSync()).toBeNull();
    localStorage.setItem('jarvis_session_token', 'ls-token');
    expect(getSessionTokenSync()).toBe('ls-token');

    window.__JARVIS_TOKEN__ = 'win-token';
    expect(getSessionTokenSync()).toBe('win-token');

    setSessionToken('mock-secret-token');
    expect(getSessionTokenSync()).toBe('mock-secret-token');
  });

  it('fetches session token via Tauri invoke and caches it', async () => {
    invokeMock.mockResolvedValueOnce('tauri-token-123');
    const first = await fetchSessionToken();
    const second = await fetchSessionToken();

    expect(first).toBe('tauri-token-123');
    expect(second).toBe('tauri-token-123');
    expect(invokeMock).toHaveBeenCalledTimes(1);
    expect(invokeMock).toHaveBeenCalledWith('get_session_token');
  });

  it('falls back to window.__JARVIS_TOKEN__ or localStorage when Tauri invoke fails', async () => {
    invokeMock.mockRejectedValueOnce(new Error('No tauri'));
    localStorage.setItem('jarvis_session_token', 'fallback-ls-token');

    const token = await fetchSessionToken();
    expect(token).toBe('fallback-ls-token');

    setSessionToken(null);
    invokeMock.mockResolvedValueOnce('');
    window.__JARVIS_TOKEN__ = 'fallback-win-token';
    expect(await fetchSessionToken()).toBe('fallback-win-token');
  });

  it('apiFetch injects Bearer token without overriding explicit Authorization header', async () => {
    setSessionToken('bearer-xyz');
    globalThis.fetch.mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });

    await apiFetch('/api/settings');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/settings$/),
      expect.objectContaining({
        headers: { Authorization: 'Bearer bearer-xyz' },
      }),
    );

    await apiFetch('/api/settings', { headers: { Authorization: 'Bearer custom' } });
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/api\/settings$/),
      expect.objectContaining({
        headers: { Authorization: 'Bearer custom' },
      }),
    );
  });

  it('apiGet, apiPost, apiPut, apiDelete send expected methods and parse JSON', async () => {
    setSessionToken('tok');
    globalThis.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, items: [1] }),
    });

    expect(await apiGet('/api/items')).toEqual({ success: true, items: [1] });
    expect(await apiPost('/api/items', { a: 1 })).toEqual({ success: true, items: [1] });
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/api\/items$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ a: 1 }),
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer tok',
        }),
      }),
    );

    expect(await apiPut('/api/items/1', { a: 2 })).toEqual({ success: true, items: [1] });
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/api\/items\/1$/),
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ a: 2 }),
      }),
    );

    expect(await apiDelete('/api/items/1')).toEqual({ success: true, items: [1] });
    expect(globalThis.fetch).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/api\/items\/1$/),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('throws descriptive errors on non-OK responses', async () => {
    setSessionToken('tok');
    globalThis.fetch.mockResolvedValue({ ok: false, status: 403 });

    await expect(apiGet('/api/secret')).rejects.toThrow('HTTP 403: Failed to fetch /api/secret');
    await expect(apiPost('/api/secret', {})).rejects.toThrow('HTTP 403: Failed to post to /api/secret');
    await expect(apiPut('/api/secret', {})).rejects.toThrow('HTTP 403: Failed to put to /api/secret');
    await expect(apiDelete('/api/secret')).rejects.toThrow('HTTP 403: Failed to delete /api/secret');
  });
});
