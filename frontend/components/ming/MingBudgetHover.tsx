'use client';

import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { SalvageBudgetAccount } from '../../game/ming/salvageStateTypes';
import { displayFiscalLabel } from '../../game/ming/fiscalDisplay';
import type { ScenarioId } from '../../game/scenarios';
import { formatMoney, formatSignedMoney } from '../../game/ming/mingSalvageFormat';

type Props = {
  accountName: '国库' | '内库';
  budget: SalvageBudgetAccount;
  scenarioId?: ScenarioId;
};

export const MingBudgetHover: React.FC<Props> = ({ accountName, budget, scenarioId }) => {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const displayName = accountName === '国库' ? '国库' : '内库';
  const modifierPct = budget.modifier_pct || 0;
  const hasModifier = modifierPct !== 0 && budget.base_net !== undefined;

  const show = () => {
    const r = triggerRef.current?.getBoundingClientRect();
    if (r) setPos({ left: r.left, top: r.bottom + 6 });
    setOpen(true);
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onMouseEnter={show}
        onMouseLeave={() => setOpen(false)}
        onFocus={show}
        onBlur={() => setOpen(false)}
        onClick={() => (open ? setOpen(false) : show())}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          padding: '2px 10px',
          borderRadius: 8,
          border: open ? '1px solid rgba(255,215,0,0.55)' : '1px solid rgba(255,215,0,0.25)',
          background: open ? 'rgba(255,215,0,0.08)' : 'rgba(255,255,255,0.04)',
          color: '#ffebc1',
          cursor: 'pointer',
          fontSize: 13,
        }}
      >
        <span>
          {displayName} <b style={{ color: '#ffd700' }}>{formatMoney(budget.balance)}</b>
        </span>
        <small style={{ color: budget.net >= 0 ? '#52c41a' : '#f5222d', fontSize: 11 }}>
          月 {formatSignedMoney(budget.net)}
        </small>
      </button>
      {open && pos && typeof document !== 'undefined' &&
        createPortal(
          <div
            role="tooltip"
            style={{
              position: 'fixed',
              left: pos.left,
              top: pos.top,
              zIndex: 20000,
              minWidth: 260,
              maxWidth: 320,
              padding: 12,
              borderRadius: 8,
              border: '1px solid rgba(255,215,0,0.35)',
              background: 'rgba(14,11,16,0.98)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              fontSize: 12,
            }}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
          >
            <div style={{ marginBottom: 8, color: '#ffd700', fontWeight: 600 }}>
              {displayName}月度定额
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 8, color: '#ccc' }}>
              <span>
                入 <b style={{ color: '#52c41a' }}>{formatMoney(budget.income_total)}</b>
              </span>
              <span>
                出 <b style={{ color: '#f5222d' }}>{formatMoney(budget.expense_total)}</b>
              </span>
              <span>
                净{' '}
                <b style={{ color: budget.net >= 0 ? '#52c41a' : '#f5222d' }}>
                  {formatSignedMoney(budget.net)}
                </b>
              </span>
            </div>
            {hasModifier && (
              <p style={{ margin: '0 0 8px', color: '#888', fontSize: 11 }}>
                基准 {formatSignedMoney(budget.base_net || 0)}，修正 {modifierPct > 0 ? '+' : ''}
                {modifierPct}%
              </p>
            )}
            {(budget.income || []).slice(0, 6).map((item) => (
              <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#aaa' }}>{displayFiscalLabel(item.name, scenarioId)}</span>
                <span style={{ color: '#52c41a' }}>+{formatMoney(item.amount)}</span>
              </div>
            ))}
            {(budget.expense || []).slice(0, 6).map((item) => (
              <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#aaa' }}>{displayFiscalLabel(item.name, scenarioId)}</span>
                <span style={{ color: '#f5222d' }}>-{formatMoney(item.amount)}</span>
              </div>
            ))}
            {budget.movements?.length ? (
              <>
                <div style={{ marginTop: 10, marginBottom: 6, color: '#d4af37', fontSize: 11 }}>
                  本月一次性入账（上月末结算）
                  <span style={{ color: budget.movements_total >= 0 ? '#52c41a' : '#f5222d', marginLeft: 8 }}>
                    合计 {formatSignedMoney(budget.movements_total)}
                  </span>
                </div>
                {budget.movements.map((m, idx) => {
                  const sign = m.delta >= 0 ? '+' : '-';
                  const color = m.delta >= 0 ? '#52c41a' : '#f5222d';
                  return (
                    <div key={`mv-${idx}`} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <b style={{ color: '#ddd', fontSize: 12 }}>{m.category || '—'}</b>
                        <span style={{ color }}>{sign}{formatMoney(Math.abs(m.delta))}</span>
                      </div>
                      <small style={{ color: '#777', fontSize: 11 }}>{m.reason}</small>
                    </div>
                  );
                })}
              </>
            ) : (
              <div style={{ marginTop: 10, fontSize: 11, color: '#666' }}>本月一次性入账：暂无</div>
            )}
          </div>,
          document.body,
        )}
    </>
  );
};
