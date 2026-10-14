'use client';

import React from 'react';
import { UserAvatarMenu } from '../auth/UserAvatarMenu';
import { PortalThemeToggle } from './PortalThemeToggle';

type PortalNavProps = {
  onNavigate: (section: 'atlas' | 'dialogue' | 'tutor' | 'game') => void;
};

export const PortalNav: React.FC<PortalNavProps> = ({ onNavigate }) => {
  return (
    <header className="portal-nav">
      <div className="portal-nav__inner">
        <div className="portal-nav__brand">
          <span className="portal-nav__logo" aria-hidden>
            财
          </span>
          <div>
            <div className="portal-nav__title">中国财税史</div>
            <div className="portal-nav__subtitle">智慧课堂</div>
          </div>
        </div>
        <nav className="portal-nav__links" aria-label="功能导航">
          <button type="button" className="portal-nav__link" onClick={() => onNavigate('atlas')}>
            财税史图谱
          </button>
          <button type="button" className="portal-nav__link" onClick={() => onNavigate('dialogue')}>
            史家对话
          </button>
          <button type="button" className="portal-nav__link" onClick={() => onNavigate('tutor')}>
            AI 助教
          </button>
          <button type="button" className="portal-nav__link" onClick={() => onNavigate('game')}>
            制度模拟
          </button>
        </nav>
        <div className="portal-nav__actions">
          <UserAvatarMenu />
          <PortalThemeToggle />
          <button type="button" className="portal-btn portal-btn--dark portal-nav__cta" onClick={() => onNavigate('game')}>
            进入制度模拟
            <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </header>
  );
};
