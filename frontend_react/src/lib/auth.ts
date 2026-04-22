// Auth state management for Django backend (JWT)

const ACCESS_KEY = "zen_access_token";
const REFRESH_KEY = "zen_refresh_token";
const USER_KEY = "zen_user";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.zenqrmenu.com";

export function getToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(ACCESS_KEY, token);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** Build Authorization header if token exists */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Persist user info across refreshes */
export function getStoredUser(): { username: string; email: string } | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user: { username: string; email: string }): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  localStorage.removeItem(USER_KEY);
}

/** Refresh the access token using the refresh token */
export async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${BASE_URL}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });

    if (!res.ok) {
      clearToken();
      clearStoredUser();
      return false;
    }

    const data = await res.json();
    if (data.access) {
      setToken(data.access);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/** Fetch with auto-refresh: if 401, try refreshing the token and retry once */
export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const newToken = getToken();
      if (newToken) headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(url, { ...options, headers });
    }
  }

  return res;
}
