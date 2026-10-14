'use client';

import React from 'react';

type Props = {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
};

export const MingDrawerShell: React.FC<Props> = ({
  open,
  title,
  subtitle,
  onClose,
  children,
  width = 360,
}) => {
  if (!open) return null;
  return (
    <>
      <div
        role="presentation"
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1400,
          background: 'rgba(0,0,0,0.35)',
        }}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: `min(${width}px, 92vw)`,
          zIndex: 1500,
          display: 'flex',
          flexDirection: 'column',
          background: 'linear-gradient(180deg, #1a1210 0, #0d0b10 100%)',
          borderLeft: '1px solid rgba(255,215,0,0.35)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
        }}
      >
        <header
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 8,
            padding: '14px 16px',
            borderBottom: '1px solid rgba(255,215,0,0.2)',
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 16, color: '#ffd700' }}>{title}</h2>
            {subtitle && (
              <p style={{ margin: '4px 0 0', fontSize: 11, color: '#888' }}>{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            style={{
              border: 'none',
              background: 'transparent',
              color: '#aaa',
              fontSize: 22,
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </header>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px 20px' }}>{children}</div>
      </aside>
    </>
  );
};

export const drawerSearchStyle: React.CSSProperties = {
  width: '100%',
  marginBottom: 10,
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid rgba(255,215,0,0.2)',
  background: 'rgba(0,0,0,0.35)',
  color: '#f5f5f5',
  fontSize: 13,
};

export const drawerRowStyle = (selected: boolean): React.CSSProperties => ({
  width: '100%',
  textAlign: 'left',
  padding: '10px 12px',
  marginBottom: 6,
  borderRadius: 8,
  border: selected ? '1px solid rgba(255,215,0,0.75)' : '1px solid rgba(255,255,255,0.08)',
  background: selected ? 'rgba(255,215,0,0.1)' : 'rgba(0,0,0,0.25)',
  color: '#eee',
  cursor: 'pointer',
});

export const drawerSectionTitle: React.CSSProperties = {
  fontSize: 11,
  color: '#d4af37',
  letterSpacing: '0.08em',
  margin: '12px 0 6px',
  textTransform: 'uppercase',
};
