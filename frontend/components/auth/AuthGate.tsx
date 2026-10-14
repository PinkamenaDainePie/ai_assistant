'use client';

import React from 'react';
import { useAuth } from './AuthProvider';
import { AuthVideoBackground } from './AuthVideoBackground';

type AuthGateProps = {
  children: React.ReactNode;
};

/** 课堂模块启用时，未登录学生/教师会被引导至 /login */
export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { config, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="ui-auth-page">
        <AuthVideoBackground />
        <p className="ui-muted ui-auth-page__status ui-auth-page__status--pulse">正在加载…</p>
      </div>
    );
  }

  if (!config.enabled) {
    return <>{children}</>;
  }

  if (!user) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    return (
      <div className="ui-auth-page">
        <AuthVideoBackground />
        <p className="ui-muted ui-auth-page__status ui-auth-page__status--pulse">正在跳转登录…</p>
      </div>
    );
  }

  if (user.role === 'teacher') {
    if (typeof window !== 'undefined' && window.location.pathname === '/') {
      window.location.href = '/teacher';
      return (
        <div className="ui-auth-page">
          <AuthVideoBackground />
          <p className="ui-muted ui-auth-page__status ui-auth-page__status--pulse">正在进入教师后台…</p>
        </div>
      );
    }
  }

  return <>{children}</>;
};
