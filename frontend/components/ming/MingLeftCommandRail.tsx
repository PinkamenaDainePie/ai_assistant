'use client';

import React from 'react';
import type { MingCommandModal } from '../../game/ming/mingTurnPhase';

type Props = {
  eventsCount?: number;
  secretOrderBadge?: number;
  edictBadge?: number;
  activeModal: MingCommandModal;
  issuesOpen?: boolean;
  onOpenIssues: () => void;
  onOpenEdict: () => void;
  onOpen: (modal: MingCommandModal) => void;
};

const btn = (active: boolean): React.CSSProperties => ({
  width: '100%',
  padding: '10px 6px',
  borderRadius: 6,
  border: active ? '1px solid rgba(255,215,0,0.85)' : '1px solid rgba(255,215,0,0.25)',
  background: active
    ? 'linear-gradient(180deg, rgba(255,215,0,0.15), rgba(0,0,0,0.4))'
    : 'linear-gradient(180deg, rgba(30,20,15,0.92), rgba(10,8,10,0.95))',
  color: '#f5f5f5',
  cursor: 'pointer',
  textAlign: 'center',
  position: 'relative',
});

export const MingLeftCommandRail: React.FC<Props> = ({
  eventsCount = 0,
  secretOrderBadge = 0,
  edictBadge = 0,
  activeModal,
  issuesOpen = false,
  onOpenIssues,
  onOpenEdict,
  onOpen,
}) => {
  const slots: Array<{
    kind: 'issues' | 'edict' | 'modal';
    key: MingCommandModal;
    label: string;
    sub: string;
    badge?: number;
    active?: boolean;
  }> = [
    {
      kind: 'issues',
      key: 'none',
      label: '奏疏',
      sub: `${eventsCount} 件`,
      badge: eventsCount,
      active: issuesOpen,
    },
    {
      kind: 'modal',
      key: 'secret_orders',
      label: '密令',
      sub: '进行中',
      badge: secretOrderBadge,
      active: activeModal === 'secret_orders',
    },
    {
      kind: 'modal',
      key: 'history',
      label: '史册',
      sub: '奏报/诏书',
      active: activeModal === 'history',
    },
    {
      kind: 'modal',
      key: 'extraction',
      label: '邸报',
      sub: '账目明细',
      active: activeModal === 'extraction',
    },
    {
      kind: 'edict',
      key: 'edict',
      label: '拟诏',
      sub: edictBadge ? `${edictBadge} 道` : '本回合',
      badge: edictBadge,
      active: activeModal === 'edict',
    },
  ];

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        padding: '8px 6px',
        background: 'linear-gradient(180deg, rgba(12,10,12,0.96), rgba(5,4,6,0.98))',
        borderRight: '1px solid rgba(255,215,0,0.2)',
        boxSizing: 'border-box',
        justifyContent: 'center',
      }}
    >
      {slots.map((slot) => (
        <button
          key={slot.label}
          type="button"
          style={btn(!!slot.active)}
          onClick={() => {
            if (slot.kind === 'issues') onOpenIssues();
            else if (slot.kind === 'edict') onOpenEdict();
            else onOpen(slot.key);
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 700, color: '#ffd700' }}>{slot.label}</span>
          <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{slot.sub}</div>
          {slot.badge != null && slot.badge > 0 && (
            <span
              style={{
                position: 'absolute',
                top: 4,
                right: 4,
                minWidth: 14,
                height: 14,
                padding: '0 3px',
                borderRadius: 7,
                background: '#c41e3a',
                color: '#fff',
                fontSize: 9,
                lineHeight: '14px',
              }}
            >
              {slot.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
};
