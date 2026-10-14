'use client';

import React, { useCallback, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './AuthProvider';
import { UserAvatar } from './UserAvatar';

export const UserAvatarMenu: React.FC = () => {
  const router = useRouter();
  const { config, user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<number | null>(null);

  const clearCloseTimer = useCallback(() => {
    if (closeTimer.current != null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }, []);

  const scheduleClose = useCallback(() => {
    clearCloseTimer();
    closeTimer.current = window.setTimeout(() => setOpen(false), 160);
  }, [clearCloseTimer]);

  if (!config.enabled || !user) return null;

  const goAccount = () => {
    setOpen(false);
    router.push('/account');
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div
      className="ui-avatar-menu"
      onMouseEnter={() => {
        clearCloseTimer();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
    >
      <button
        type="button"
        className="ui-avatar-menu__trigger"
        aria-label="个人中心"
        aria-expanded={open}
        onClick={goAccount}
      >
        <UserAvatar userId={user.id} name={user.name} size="sm" />
      </button>

      {open ? (
        <div className="ui-avatar-menu__dropdown" role="menu">
          <button type="button" className="ui-avatar-menu__item" role="menuitem" onClick={goAccount}>
            个人中心
          </button>
          <button
            type="button"
            className="ui-avatar-menu__item ui-avatar-menu__item--danger"
            role="menuitem"
            onClick={handleLogout}
          >
            退出登录
          </button>
        </div>
      ) : null}
    </div>
  );
};
