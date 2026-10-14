'use client';

import React from 'react';
import { mingOutlineBtn } from '../../game/ming/mingUiStyles';

type Props = {
  turnLabel?: string;
  lastReport?: string;
  settleNarrative?: string;
  onOpenEdict?: () => void;
};

export const MingTimelineLog: React.FC<Props> = ({
  turnLabel,
  lastReport,
  settleNarrative,
  onOpenEdict,
}) => {
  const snippet = settleNarrative?.trim() || lastReport?.trim();
  if (!snippet && !turnLabel && !onOpenEdict) return null;

  const preview =
    snippet && snippet.length > 120 ? `${snippet.slice(0, 120).trim()}…` : snippet;

  return (
    <div
      style={{
        height: 90,
        borderTop: '1px solid rgba(255,215,0,0.2)',
        background: 'linear-gradient(90deg, #120e0c 0, #0a0a0c 100%)',
        padding: '8px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          flex: 1,
          minWidth: 0,
          padding: '6px 10px',
          borderRadius: 8,
          border: '1px solid rgba(255,215,0,0.3)',
          background: 'rgba(0,0,0,0.4)',
          fontSize: 12,
          color: '#f5f5f5',
        }}
      >
        <div style={{ color: '#ffebc1', marginBottom: 4, fontWeight: 600 }}>
          {turnLabel ? `本回合 · ${turnLabel}` : '本回合'}
        </div>
        <div style={{ color: '#ddd', lineHeight: 1.5 }}>
          {preview || '召见大臣拟旨，核定后颁诏结算。'}
        </div>
      </div>
      {onOpenEdict ? (
        <button
          type="button"
          style={{
            ...mingOutlineBtn,
            flexShrink: 0,
            padding: '12px 16px',
            fontWeight: 700,
            color: '#ffd700',
          }}
          onClick={onOpenEdict}
        >
          拟诏 / 结束回合
        </button>
      ) : null}
    </div>
  );
};
