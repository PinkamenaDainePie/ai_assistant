'use client';

import React from 'react';
import { mingCloseBtn } from '../../game/ming/mingUiStyles';

type Props = {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
};

export const MingFullscreenModal: React.FC<Props> = ({
  title,
  subtitle,
  onClose,
  children,
  wide,
}) => (
  <div
    style={{
      position: 'fixed',
      inset: 0,
      zIndex: 2400,
      background: 'rgba(0,0,0,0.82)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16,
    }}
    onClick={onClose}
  >
    <div
      style={{
        width: wide ? 'min(960px, 96vw)' : 'min(720px, 96vw)',
        maxHeight: '90vh',
        borderRadius: 12,
        border: '1px solid rgba(255,215,0,0.55)',
        background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 100%)',
        color: '#f5f5f5',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 12px 48px rgba(0,0,0,0.65)',
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          padding: '14px 16px',
          borderBottom: '1px solid rgba(255,215,0,0.2)',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#ffe7a3' }}>{title}</h2>
          {subtitle && (
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#999' }}>{subtitle}</p>
          )}
        </div>
        <button type="button" onClick={onClose} aria-label="关闭" style={mingCloseBtn}>
          ×
        </button>
      </div>
      <div className="ming-scroll" style={{ flex: 1, overflow: 'auto', padding: 16 }}>{children}</div>
    </div>
  </div>
);
