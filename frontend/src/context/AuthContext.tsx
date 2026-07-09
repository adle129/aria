"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  apiClient,
  clearStoredTaskId,
  fetchHealth,
  fetchMe,
  getStoredToken,
  login as apiLogin,
  setStoredToken,
  type AuthUser,
  type HealthData,
} from "@/api/client";

interface AuthContextValue {
  loading: boolean;
  authEnabled: boolean;
  user: AuthUser | null;
  isKbAdmin: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

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
    } catch {
      setStoredToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    void refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    setStoredToken(result.access_token);
    setUser(result.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      /* ignore */
    }
    setStoredToken(null);
    setUser(null);
    clearStoredTaskId();
  }, []);

  const value = useMemo(
    () => ({
      loading,
      authEnabled,
      user,
      isKbAdmin: user?.role === "kb_admin",
      login,
      logout,
      refresh,
    }),
    [loading, authEnabled, user, login, logout, refresh],
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
