'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

export type PortalTheme = 'light' | 'dark';

const STORAGE_KEY = 'portal-theme';

type PortalThemeContextValue = {
  theme: PortalTheme;
  isDark: boolean;
  toggling: boolean;
  toggleTheme: () => void;
  setTheme: (theme: PortalTheme) => void;
};

const PortalThemeContext = createContext<PortalThemeContextValue | null>(null);

function readStoredTheme(): PortalTheme {
  if (typeof window === 'undefined') return 'light';
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw === 'dark' ? 'dark' : 'light';
}

export function PortalThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<PortalTheme>('light');
  const [toggling, setToggling] = useState(false);

  useEffect(() => {
    setThemeState(readStoredTheme());
  }, []);

  const setTheme = useCallback((next: PortalTheme) => {
    setToggling(true);
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    window.setTimeout(() => setToggling(false), 520);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [setTheme, theme]);

  const value = useMemo(
    () => ({
      theme,
      isDark: theme === 'dark',
      toggling,
      toggleTheme,
      setTheme,
    }),
    [theme, toggling, toggleTheme, setTheme],
  );

  return <PortalThemeContext.Provider value={value}>{children}</PortalThemeContext.Provider>;
}

export function usePortalTheme(): PortalThemeContextValue {
  const ctx = useContext(PortalThemeContext);
  if (!ctx) {
    throw new Error('usePortalTheme must be used within PortalThemeProvider');
  }
  return ctx;
}
