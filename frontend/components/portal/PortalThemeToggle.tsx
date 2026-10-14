'use client';

import React from 'react';
import { usePortalTheme } from './PortalThemeContext';

export const PortalThemeToggle: React.FC = () => {
  const { isDark, toggling, toggleTheme } = usePortalTheme();

  return (
    <button
      type="button"
      className={`portal-theme-toggle${isDark ? ' portal-theme-toggle--dark' : ''}${toggling ? ' portal-theme-toggle--animating' : ''}`}
      onClick={toggleTheme}
      aria-label={isDark ? '切换为浅色模式' : '切换为深色模式'}
      aria-pressed={isDark}
      title={isDark ? '浅色模式' : '深色模式'}
    >
      <span className="portal-theme-toggle__track" aria-hidden>
        <span className="portal-theme-toggle__glow" />
        <span className="portal-theme-toggle__thumb">
          <svg className="portal-theme-toggle__icon portal-theme-toggle__icon--sun" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
            <path
              d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          <svg className="portal-theme-toggle__icon portal-theme-toggle__icon--moon" viewBox="0 0 24 24" fill="none">
            <path
              d="M21 14.5A8.5 8.5 0 1 1 9.5 3a6.5 6.5 0 1 0 11.5 11.5Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </span>
      <span className="portal-theme-toggle__label">{isDark ? '深色' : '浅色'}</span>
    </button>
  );
};
