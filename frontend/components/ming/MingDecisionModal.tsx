'use client';

import React, { useEffect, useState } from 'react';
import type { MingPendingDecision } from '../../game/ming/mingTurnPhase';
import { mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Choice = { label?: string; hint?: string; note?: string };

type Props = {
  decisions: MingPendingDecision[];
  onResolve: (choices: Choice[]) => void;
};

export const MingDecisionModal: React.FC<Props> = ({ decisions, onResolve }) => {
  const [cursor, setCursor] = useState(0);
  const [picks, setPicks] = useState<Choice[]>(() => decisions.map(() => ({})));

  useEffect(() => {
    setCursor(0);
    setPicks(decisions.map(() => ({})));
  }, [decisions]);

  if (!decisions.length) return null;

  const total = decisions.length;
  const cur = decisions[cursor];
  const pick = picks[cursor] || {};
  const decided = !!(pick.label || (pick.note || '').trim());
  const last = cursor >= total - 1;

  const setOption = (label: string, hint: string) =>
    setPicks((p) => p.map((x, i) => (i === cursor ? { ...x, label, hint } : x)));

  const setNote = (note: string) =>
    setPicks((p) => p.map((x, i) => (i === cursor ? { ...x, note } : x)));

  const next = () => {
    if (!decided) return;
    if (last) onResolve(picks);
    else setCursor((c) => c + 1);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="月末遇阻纠偏"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.82)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 3000,
        padding: 16,
      }}
    >
      <div
        style={{
          width: 'min(560px, 100%)',
          maxHeight: '85vh',
          overflow: 'auto',
          borderRadius: 12,
          border: '1px solid rgba(255,215,0,0.65)',
          background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 100%)',
          color: '#f5f5f5',
          padding: '20px 22px',
          boxShadow: '0 0 32px rgba(0,0,0,0.9)',
        }}
      >
        <div style={{ marginBottom: 12 }}>
          <span
            style={{
              fontSize: 12,
              color: '#c9a227',
              letterSpacing: '0.12em',
            }}
          >
            遇阻纠偏 · {cursor + 1}/{total}
          </span>
          <h2 style={{ margin: '6px 0 0', fontSize: 20, color: '#ffe7a3' }}>{cur.title}</h2>
        </div>

        {cur.context ? (
          <p style={{ fontSize: 14, lineHeight: 1.65, color: '#ccc', marginBottom: 16 }}>{cur.context}</p>
        ) : null}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
          {cur.options.map((o, i) => {
            const picked = pick.label === o.label;
            return (
              <button
                key={i}
                type="button"
                onClick={() => setOption(o.label, o.hint)}
                style={{
                  textAlign: 'left',
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: picked
                    ? '1px solid rgba(255,215,0,0.85)'
                    : '1px solid rgba(255,215,0,0.25)',
                  background: picked ? 'rgba(255,215,0,0.12)' : 'rgba(0,0,0,0.35)',
                  color: '#eee',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: o.hint ? 4 : 0 }}>{o.label}</div>
                {o.hint ? (
                  <div style={{ fontSize: 12, color: '#aaa', lineHeight: 1.5 }}>{o.hint}</div>
                ) : null}
              </button>
            );
          })}
        </div>

        <textarea
          placeholder="朱批（可选）：另有旨意可亲笔补写，将与所选一并定夺。"
          value={pick.note || ''}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          style={{
            width: '100%',
            boxSizing: 'border-box',
            padding: '8px 10px',
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.3)',
            background: 'rgba(0,0,0,0.4)',
            color: '#eee',
            fontSize: 13,
            resize: 'vertical',
            marginBottom: 14,
          }}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <span style={{ fontSize: 12, color: '#888' }}>
            {decided ? '' : '请择一选项或亲笔朱批，方可下一步。'}
          </span>
          <button type="button" disabled={!decided} onClick={next} style={mingPrimaryBtn}>
            {last ? '御笔亲断，续推时局' : '下一桩抉择'}
          </button>
        </div>
      </div>
    </div>
  );
};
