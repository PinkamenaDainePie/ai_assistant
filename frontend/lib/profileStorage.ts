/** 用户头像与本地偏好（按 user id 分桶，存 localStorage） */

export type AvatarPreset = 'indigo' | 'violet' | 'teal' | 'amber' | 'rose' | 'slate';

export const AVATAR_PRESETS: { id: AvatarPreset; label: string }[] = [
  { id: 'indigo', label: '靛青' },
  { id: 'violet', label: '紫' },
  { id: 'teal', label: '青' },
  { id: 'amber', label: '琥珀' },
  { id: 'rose', label: '玫' },
  { id: 'slate', label: '灰' },
];

type ProfileData = {
  preset?: AvatarPreset;
  customDataUrl?: string;
};

function key(userId: string): string {
  return `classroom_profile_v1_${userId}`;
}

export function loadProfile(userId: string): ProfileData {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(key(userId));
    return raw ? (JSON.parse(raw) as ProfileData) : {};
  } catch {
    return {};
  }
}

export function saveProfile(userId: string, data: ProfileData): void {
  localStorage.setItem(key(userId), JSON.stringify(data));
}

export function setAvatarPreset(userId: string, preset: AvatarPreset): void {
  const prev = loadProfile(userId);
  saveProfile(userId, { ...prev, preset, customDataUrl: undefined });
}

export function setAvatarCustom(userId: string, dataUrl: string): void {
  const prev = loadProfile(userId);
  saveProfile(userId, { ...prev, customDataUrl: dataUrl });
}

export function avatarInitial(name: string): string {
  const t = (name || '?').trim();
  return t.slice(0, 1).toUpperCase();
}
