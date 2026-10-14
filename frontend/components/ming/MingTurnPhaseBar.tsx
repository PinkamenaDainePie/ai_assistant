'use client';

import React from 'react';
import { MING_PHASE_LABEL } from '../../game/ming/mingTurnPhase';
import type { MingTurnPhase } from '../../game/ming/mingTurnPhase';

export const MING_TURN_PHASE_ORDER: MingTurnPhase[] = [
  'summoning',
  'reviewing',
  'awaiting_decision',
  'issued',
];

const PHASE_HINT: Record<MingTurnPhase, string> = {
  summoning: '召见大臣问策',
  reviewing: '核定拟旨草案',
  awaiting_decision: '圣意亲裁决策',
  issued: '已颁诏，可结束回合',
};

type Props = {
  phase: MingTurnPhase;
  onPhaseClick?: (phase: MingTurnPhase) => void;
};

export const MingTurnPhaseBar: React.FC<Props> = ({ phase, onPhaseClick }) => {
  const idx = MING_TURN_PHASE_ORDER.indexOf(phase);
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        padding: '8px 12px',
        borderBottom: '1px solid rgba(255,215,0,0.25)',
        background: 'rgba(8,6,10,0.85)',
      }}
    >
      {MING_TURN_PHASE_ORDER.map((p, i) => {
        const active = p === phase;
        const done = i < idx;
        const reachable = i <= idx;
        const label = MING_PHASE_LABEL[p];
        const title = reachable
          ? PHASE_HINT[p]
          : `需先完成「${MING_PHASE_LABEL[MING_TURN_PHASE_ORDER[idx]]}」`;

        const baseStyle: React.CSSProperties = {
          flex: 1,
          textAlign: 'center',
          fontSize: 12,
          padding: '6px 4px',
          borderRadius: 6,
          color: active ? '#111' : done ? '#ffd700' : '#888',
          background: active
            ? 'linear-gradient(90deg, #ffd700, #e8c860)'
            : 'rgba(255,255,255,0.04)',
          fontWeight: active ? 700 : 500,
          border: 'none',
          fontFamily: 'inherit',
        };

        if (!onPhaseClick || !reachable) {
          return (
            <div
              key={p}
              title={title}
              style={{
                ...baseStyle,
                cursor: reachable ? 'default' : 'not-allowed',
                opacity: reachable ? 1 : 0.55,
              }}
            >
              {label}
            </div>
          );
        }

        return (
          <button
            key={p}
            type="button"
            title={title}
            onClick={() => onPhaseClick(p)}
            style={{
              ...baseStyle,
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};
