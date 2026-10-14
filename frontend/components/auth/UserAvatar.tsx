'use client';

import React, { useEffect, useState } from 'react';
import {
  avatarInitial,
  loadProfile,
  type AvatarPreset,
} from '../../lib/profileStorage';

type UserAvatarProps = {
  userId: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
};

export const UserAvatar: React.FC<UserAvatarProps> = ({
  userId,
  name,
  size = 'md',
  className = '',
}) => {
  const [preset, setPreset] = useState<AvatarPreset>('indigo');
  const [customUrl, setCustomUrl] = useState<string | undefined>();

  useEffect(() => {
    const p = loadProfile(userId);
    if (p.preset) setPreset(p.preset);
    if (p.customDataUrl) setCustomUrl(p.customDataUrl);
  }, [userId]);

  useEffect(() => {
    const onStorage = () => {
      const p = loadProfile(userId);
      if (p.preset) setPreset(p.preset);
      setCustomUrl(p.customDataUrl);
    };
    window.addEventListener('storage', onStorage);
    window.addEventListener('profile-updated', onStorage);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('profile-updated', onStorage);
    };
  }, [userId]);

  const sizeClass = size === 'sm' ? 'ui-avatar--sm' : size === 'lg' ? 'ui-avatar--lg' : '';

  if (customUrl) {
    return (
      <span
        className={`ui-avatar ui-avatar--photo ${sizeClass} ${className}`.trim()}
        style={{ backgroundImage: `url(${customUrl})` }}
        aria-hidden
      />
    );
  }

  return (
    <span
      className={`ui-avatar ui-avatar--${preset} ${sizeClass} ${className}`.trim()}
      aria-hidden
    >
      {avatarInitial(name)}
    </span>
  );
};

export function notifyProfileUpdated(): void {
  window.dispatchEvent(new Event('profile-updated'));
}
