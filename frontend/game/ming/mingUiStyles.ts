import type React from 'react';

export const MING_BG = '#050406';

export const mingPanelShell: React.CSSProperties = {
  position: 'fixed',
  right: 72,
  top: 112,
  width: 320,
  maxHeight: 'calc(70vh - 40px)',
  borderRadius: 10,
  background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 60%, #050508 100%)',
  color: '#f5f5f5',
  display: 'flex',
  flexDirection: 'column',
  padding: 12,
  border: '1px solid rgba(255,215,0,0.6)',
  boxShadow: '0 0 18px rgba(0,0,0,0.8)',
  zIndex: 1100,
};

export const mingBottomPanel: React.CSSProperties = {
  position: 'absolute',
  left: '50%',
  transform: 'translateX(-50%)',
  minWidth: 520,
  maxWidth: 880,
  padding: '10px 14px',
  borderRadius: 10,
  background: 'linear-gradient(90deg, rgba(10,6,4,0.95), rgba(25,15,10,0.95))',
  border: '1px solid rgba(255,215,0,0.6)',
  boxShadow: '0 0 16px rgba(0,0,0,0.7)',
  color: '#f5f5f5',
  fontSize: 13,
  zIndex: 130,
};

export const mingDraggableBottomPanelStyle = (
  pos: { left: number; top: number } | null,
  bottom: number,
  extra?: React.CSSProperties,
): React.CSSProperties => ({
  ...mingBottomPanel,
  position: 'fixed',
  ...(pos
    ? { left: pos.left, top: pos.top, bottom: 'auto', transform: 'none' }
    : { bottom, left: '50%', transform: 'translateX(-50%)' }),
  ...extra,
});

export const mingRailShell: React.CSSProperties = {
  width: 56,
  height: '100%',
  background: 'linear-gradient(180deg, #151017 0, #0a080b 60%, #050507 100%)',
  paddingTop: 16,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 10,
};

export const mingRailBtn = (active?: boolean): React.CSSProperties => ({
  width: 40,
  height: 40,
  borderRadius: 999,
  border: active ? '1px solid rgba(255,215,0,0.85)' : '1px solid rgba(255,215,0,0.35)',
  background: active
    ? 'radial-gradient(circle at 30% 20%, rgba(255,215,0,0.35), rgba(10,8,12,0.9))'
    : 'radial-gradient(circle at 30% 20%, #343034, #151017)',
  color: '#f5f5f5',
  cursor: 'pointer',
  fontSize: 12,
  letterSpacing: '0.08em',
});

export const mingPrimaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 8,
  border: 'none',
  background: 'linear-gradient(90deg, #ffd700, #e8c860)',
  color: '#111',
  fontWeight: 700,
  cursor: 'pointer',
};

export const mingOutlineBtn: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 6,
  border: '1px solid rgba(255,215,0,0.4)',
  background: 'rgba(0,0,0,0.3)',
  color: '#eee',
  cursor: 'pointer',
};

export const mingCard: React.CSSProperties = {
  marginBottom: 10,
  padding: 10,
  borderRadius: 8,
  border: '1px solid rgba(255,215,0,0.15)',
  background: 'rgba(0,0,0,0.25)',
};

export const mingCloseBtn: React.CSSProperties = {
  width: 26,
  height: 26,
  borderRadius: 6,
  border: '1px solid rgba(255,215,0,0.35)',
  background: 'rgba(0,0,0,0.35)',
  color: '#ffebc1',
  fontSize: 16,
  lineHeight: 1,
  cursor: 'pointer',
};
