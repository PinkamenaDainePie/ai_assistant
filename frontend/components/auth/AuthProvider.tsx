'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  fetchAuthConfig,
  fetchMe,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  type AuthConfig,
  type ClassroomUser,
} from '../../lib/classroomApi';
import { getAccessToken } from '../../lib/authStorage';

type AuthState = {
  config: AuthConfig;
  user: ClassroomUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<ClassroomUser>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    student_id?: string;
  }) => Promise<ClassroomUser>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AuthConfig>({
    enabled: false,
    allow_register: false,
    swufe_sso_enabled: false,
    allow_local_login: true,
  });
  const [user, setUser] = useState<ClassroomUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const cfg = await fetchAuthConfig();
    setConfig(cfg);
    if (!cfg.enabled) {
      setUser(null);
      return;
    }
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await refresh();
      } finally {
        setLoading(false);
      }
    })();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const u = await apiLogin(email, password);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(
    async (payload: { email: string; password: string; name: string; student_id?: string }) => {
      const u = await apiRegister(payload);
      setUser(u);
      return u;
    },
    [],
  );

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ config, user, loading, login, register, logout, refresh }),
    [config, user, loading, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function useRequireAuth(allowedRoles?: string[]): {
  ready: boolean;
  user: ClassroomUser | null;
} {
  const { config, user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!config.enabled) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      router.replace(user.role === 'teacher' ? '/teacher' : '/');
    }
  }, [loading, config.enabled, user, allowedRoles, router]);

  return { ready: !loading && (!config.enabled || Boolean(user)), user };
}
