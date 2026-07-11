"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  apiClient,
  changePassword as apiChangePassword,
  clearStoredTaskId,
  fetchHealth,
  fetchMe,
  getStoredToken,
  login as apiLogin,
  refreshToken as apiRefreshToken,
  setStoredToken,
  type AuthUser,
  type HealthData,
} from "@/api/client";

const EXPIRES_AT_KEY = "aria_token_expires_at";

function getStoredExpiresAt(): Date | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(EXPIRES_AT_KEY);
  return v ? new Date(v) : null;
}

function setStoredExpiresAt(d: Date | null): void {
  if (typeof window === "undefined") return;
  if (d) {
    localStorage.setItem(EXPIRES_AT_KEY, d.toISOString());
  } else {
    localStorage.removeItem(EXPIRES_AT_KEY);
  }
}

interface AuthContextValue {
  loading: boolean;
  authEnabled: boolean;
  user: AuthUser | null;
  isKbAdmin: boolean;
  tokenExpiresAt: Date | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokenExpiresAt, setTokenExpiresAt] = useState<Date | null>(getStoredExpiresAt);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleRefresh = useCallback((expiresAt: Date) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const msUntilExpiry = expiresAt.getTime() - Date.now();
    const msUntilRefresh = msUntilExpiry - 30 * 60 * 1000;
    if (msUntilRefresh <= 0) return;
    refreshTimerRef.current = setTimeout(() => {
      void apiRefreshToken()
        .then((result) => {
          const newExpiry = new Date(result.expires_at);
          setStoredToken(result.access_token);
          setStoredExpiresAt(newExpiry);
          setTokenExpiresAt(newExpiry);
          scheduleRefresh(newExpiry);
        })
        .catch(() => {
          /* silent — 401 interceptor will redirect */
        });
    }, msUntilRefresh);
  }, []);

  const refresh = useCallback(async () => {
    let health: HealthData | null = null;
    try {
      health = await fetchHealth();
    } catch {
      setAuthEnabled(false);
      setUser(null);
      return;
    }
    const enabled = Boolean(health.auth_enabled);
    setAuthEnabled(enabled);
    if (!enabled) {
      setUser(null);
      return;
    }
    if (!getStoredToken()) {
      setUser(null);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
      const storedExpiry = getStoredExpiresAt();
      if (storedExpiry) scheduleRefresh(storedExpiry);
    } catch {
      setStoredToken(null);
      setStoredExpiresAt(null);
      setUser(null);
    }
  }, [scheduleRefresh]);

  useEffect(() => {
    void refresh().finally(() => setLoading(false));
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      const result = await apiLogin(username, password);
      const expiry = new Date(result.expires_at);
      setStoredToken(result.access_token);
      setStoredExpiresAt(expiry);
      setTokenExpiresAt(expiry);
      setUser(result.user);
      scheduleRefresh(expiry);
    },
    [scheduleRefresh],
  );

  const logout = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    try {
      await apiClient.post("/auth/logout");
    } catch {
      /* ignore */
    }
    setStoredToken(null);
    setStoredExpiresAt(null);
    setTokenExpiresAt(null);
    setUser(null);
    clearStoredTaskId();
  }, []);

  const changePassword = useCallback(async (oldPassword: string, newPassword: string) => {
    await apiChangePassword(oldPassword, newPassword);
  }, []);

  const value = useMemo(
    () => ({
      loading,
      authEnabled,
      user,
      isKbAdmin: user?.role === "kb_admin",
      tokenExpiresAt,
      login,
      logout,
      refresh,
      changePassword,
    }),
    [loading, authEnabled, user, tokenExpiresAt, login, logout, refresh, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

/** Returns minutes until token expires, or null if unknown */
export function useTokenExpiryWarning(): number | null {
  const { tokenExpiresAt, authEnabled, user } = useAuth();
  if (!authEnabled || !user || !tokenExpiresAt) return null;
  const mins = Math.floor((tokenExpiresAt.getTime() - Date.now()) / 60000);
  return mins;
}
