import { describe, it, expect, beforeEach } from 'vitest';
import { apiUrl, getSessionTokenSync, setSessionToken } from './api';

describe('api service', () => {
  beforeEach(() => {
    setSessionToken(null);
  });

  it('formats endpoint URLs correctly', () => {
    expect(apiUrl('test')).toMatch(/\/test$/);
    expect(apiUrl('/test')).toMatch(/\/test$/);
    expect(apiUrl('http://localhost:8765/custom')).toBe('http://localhost:8765/custom');
    expect(apiUrl('https://example.com/api')).toBe('https://example.com/api');
  });

  it('stores and retrieves session tokens synchronously', () => {
    expect(getSessionTokenSync()).toBeNull();
    setSessionToken('mock-secret-token');
    expect(getSessionTokenSync()).toBe('mock-secret-token');
  });
});
