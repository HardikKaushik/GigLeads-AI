"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { api, type User } from "./api";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (name: string, email: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => { throw new Error("Not initialized"); },
  signup: async () => { throw new Error("Not initialized"); },
  logout: () => {},
  refreshUser: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check for existing token
  useEffect(() => {
    const stored = localStorage.getItem("freelance_token");
    if (stored) {
      setToken(stored);
      api
        .getMe(stored)
        .then((u) => {
          setUser(u);
        })
        .catch(() => {
          localStorage.removeItem("freelance_token");
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<User> => {
    const res = await api.login({ email, password });
    localStorage.setItem("freelance_token", res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string): Promise<User> => {
    const res = await api.signup({ name, email, password });
    localStorage.setItem("freelance_token", res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("freelance_token");
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const t = localStorage.getItem("freelance_token");
    if (t) {
      const u = await api.getMe(t);
      setUser(u);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
