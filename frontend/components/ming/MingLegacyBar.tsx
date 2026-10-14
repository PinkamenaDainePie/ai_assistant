'use client';

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import type { SalvageLegacy } from '../../game/ming/salvageStateTypes';

type Props = {
  legacies: SalvageLegacy[];
};

export const MingLegacyBar: React.FC<Props> = ({ legacies }) => {
  const [open, setOpen] = useState(false);
  if (!legacies.length) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        style={{
          padding: '2px 10px',
          borderRadius: 8,
          border: '1px solid rgba(255,215,0,0.3)',
          background: 'rgba(255,215,0,0.06)',
          color: '#d4af37',
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        帝国修正 <b style={{ color: '#ffd700' }}>{legacies.length}</b>
      </button>
      {open &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 19000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(0,0,0,0.65)',
            }}
            onClick={() => setOpen(false)}
          >
            <div
              style={{
                width: 'min(480px, 92vw)',
                maxHeight: '80vh',
                overflowY: 'auto',
                padding: 20,
                borderRadius: 12,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'linear-gradient(180deg, #1a1210, #0d0b10)',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ margin: 0, color: '#ffd700' }}>现行帝国修正</h3>
                <button type="button" onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: '#aaa', fontSize: 20, cursor: 'pointer' }}>
                  ×
                </button>
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {legacies.map((lg) => (
                  <li
                    key={lg.id}
                    style={{
                      marginBottom: 12,
                      padding: 10,
                      borderRadius: 8,
                      border: '1px solid rgba(255,215,0,0.15)',
                      background: 'rgba(0,0,0,0.25)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <b style={{ color: '#ffe7a3' }}>{lg.name}</b>
                      <span style={{ fontSize: 11, color: '#888' }}>
                        {lg.remaining_months < 0 ? '永久' : `余 ${lg.remaining_months} 月`}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: '#bbb', lineHeight: 1.6 }}>{lg.effect_text}</p>
                    {lg.clear_condition && (
                      <p style={{ margin: '6px 0 0', fontSize: 11, color: '#777' }}>
                        消除：{lg.clear_condition}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};
