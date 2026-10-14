'use client';

import React from 'react';
import type { MingCommandModal } from '../../game/ming/mingTurnPhase';

type Slot = {
  key: MingCommandModal;
  label: string;
  caption: string;
  sub: string;
  badge?: number;
};

type Props = {
  eventsCount?: number;
  secretOrderBadge?: number;
  edictBadge?: number;
  activeModal: MingCommandModal;
  onOpen: (modal: MingCommandModal) => void;
};

const slotStyle = (active: boolean): React.CSSProperties => ({
  flex: 1,
  minWidth: 0,
  padding: '10px 8px',
  borderRadius: 8,
  border: active ? '1px solid rgba(255,215,0,0.85)' : '1px solid rgba(255,215,0,0.25)',
  background: active
    ? 'linear-gradient(180deg, rgba(255,215,0,0.15), rgba(0,0,0,0.4))'
    : 'linear-gradient(180deg, rgba(30,20,15,0.9), rgba(10,8,10,0.95))',
  color: '#f5f5f5',
  cursor: 'pointer',
  textAlign: 'center',
});

export const MingCommandBar: React.FC<Props> = ({
  eventsCount = 0,
  secretOrderBadge = 0,
  edictBadge = 0,
  activeModal,
  onOpen,
}) => {
  const slots: Slot[] = [
    {
      key: 'state',
      label: '奏疏',
      caption: '奏疏',
      sub: `${eventsCount} 件待览`,
      badge: eventsCount,
    },
    {
      key: 'extraction',
      label: '邸报',
      caption: '邸报详明',
      sub: '数项加减/账目明细',
    },
    {
      key: 'secret_orders',
      label: '密令',
      caption: '密令',
      sub: '进行中密令',
      badge: secretOrderBadge,
    },
    {
      key: 'history',
      label: '史册',
      caption: '史册',
      sub: '历代奏报/诏书',
    },
    {
      key: 'edict',
      label: '拟诏',
      caption: '拟诏/结束回合',
      sub: edictBadge ? `${edictBadge} 道` : '本回合',
      badge: edictBadge,
    },
  ];

  return (
    <div
      style={{
        flexShrink: 0,
        display: 'flex',
        gap: 8,
        padding: '8px 12px',
        borderTop: '1px solid rgba(255,215,0,0.2)',
        background: 'linear-gradient(90deg, #120e0c 0, #0a0a0c 100%)',
      }}
    >
      {slots.map((slot) => {
        const active = activeModal === slot.key;
        return (
          <button
            key={slot.key}
            type="button"
            style={slotStyle(active)}
            onClick={() => onOpen(slot.key)}
          >
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: '#ffd700' }}>{slot.label}</span>
              {slot.badge != null && slot.badge > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: -6,
                    right: -14,
                    minWidth: 16,
                    height: 16,
                    padding: '0 4px',
                    borderRadius: 8,
                    background: '#c41e3a',
                    color: '#fff',
                    fontSize: 10,
                    lineHeight: '16px',
                  }}
                >
                  {slot.badge}
                </span>
              )}
            </div>
            <div style={{ fontSize: 11, color: '#d4af37', marginTop: 2 }}>{slot.caption}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{slot.sub}</div>
          </button>
        );
      })}
    </div>
  );
};
