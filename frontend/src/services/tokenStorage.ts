const TOKEN_STORAGE_KEY = 'meetmind_access_token';

/**
 * Centralized token storage using sessionStorage so tokens persist across
 * page refreshes within the current browser session.
 * Kept isolated to allow straightforward migration to HttpOnly cookies later.
 */
export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage quota or restricted context errors
  }
}

export function clearAccessToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
}
