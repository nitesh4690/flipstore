import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import api, { getToken, setToken } from "../services/api.js";

const AuthContext = createContext(null);

/**
 * Authentication state:
 * - token persisted in localStorage (attached by services/api.js interceptor)
 * - user profile hydrated from GET /api/auth/me on mount when a token exists
 * - expired/invalid tokens are cleared by the axios 401 handler
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      setInitializing(false);
      return undefined;
    }
    api
      .get("/auth/me")
      .then((response) => {
        if (!cancelled) setUser(response.data.data);
      })
      .catch(() => {
        setToken(null); // expired/invalid — interceptor already handled redirect
      })
      .finally(() => {
        if (!cancelled) setInitializing(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const response = await api.post("/auth/login", { email, password });
    const data = response.data.data;
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (payload) => {
    const response = await api.post("/auth/register", payload);
    const data = response.data.data;
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Token may already be invalid — still clear local state.
    }
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, initializing, isAuthenticated: Boolean(user), login, register, logout, setUser }),
    [user, initializing, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
