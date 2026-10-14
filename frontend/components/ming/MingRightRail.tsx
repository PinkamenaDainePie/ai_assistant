'use client';

import React from 'react';
import type { MingTurnPhase } from '../../game/ming/mingTurnPhase';
import { mingRailBtn, mingRailShell } from '../../game/ming/mingUiStyles';

type Props = {
  phase: MingTurnPhase;
  loading: boolean;
  onOpenSummon: () => void;
  onOpenEdict: () => void;
  onIssueDecree: () => void;
};

export const MingRightRail: React.FC<Props> = ({
  phase,
  loading,
  onOpenSummon,
  onOpenEdict,
  onIssueDecree,
}) => {
  const primary =
    phase === 'summoning' || phase === 'reviewing'
      ? { label: '拟诏', action: onOpenEdict }
      : phase === 'awaiting_decision'
        ? null
      : phase === 'issued'
        ? { label: loading ? '…' : '下月', action: onIssueDecree }
        : null;

  return (
    <div style={{ ...mingRailShell, borderLeft: '1px solid rgba(255,215,0,0.2)' }}>
      <button
        type="button"
        title="择臣问策"
        onClick={onOpenSummon}
        style={{
          ...mingRailBtn(false),
          border: '1px solid rgba(255,215,0,0.9)',
          background: 'radial-gradient(circle at 30% 20%, #ffd700, #c41e3a)',
          color: '#1b1010',
        }}
      >
        问策
      </button>
      {primary && (
        <button
          type="button"
          title={primary.label}
          disabled={loading}
          onClick={primary.action}
          style={{
            ...mingRailBtn(false),
            opacity: loading ? 0.65 : 1,
            cursor: loading ? 'wait' : 'pointer',
            fontSize: primary.label === '…' ? 10 : 12,
          }}
        >
          {primary.label}
        </button>
      )}
    </div>
  );
};
