'use client';

import React, { useState } from 'react';
import { MingTurnPhaseBar } from './MingTurnPhaseBar';
import type { MingTurnPhase } from '../../game/ming/mingTurnPhase';

type Props = {
  phase: MingTurnPhase;
  onPhaseClick?: (phase: MingTurnPhase) => void;
};

export const MingPhaseBarDock: React.FC<Props> = ({ phase, onPhaseClick }) => {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        position: 'relative',
        zIndex: 2999,
        height: open ? 'auto' : 6,
        overflow: 'hidden',
        transition: 'height 200ms ease',
        background: open ? 'rgba(8,6,10,0.92)' : 'transparent',
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {!open && (
        <div
          style={{
            height: 6,
            background: 'linear-gradient(90deg, transparent, rgba(255,215,0,0.35), transparent)',
            cursor: 'default',
          }}
          title="靠近展开回合阶段"
        />
      )}
      <div
        style={{
          transform: open ? 'translateY(0)' : 'translateY(-100%)',
          opacity: open ? 1 : 0,
          transition: 'transform 200ms ease, opacity 200ms ease',
          pointerEvents: open ? 'auto' : 'none',
        }}
      >
        <MingTurnPhaseBar phase={phase} onPhaseClick={onPhaseClick} />
      </div>
    </div>
  );
};
