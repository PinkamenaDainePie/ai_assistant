'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageBudget } from '../../../game/ming/salvageStateTypes';
import { formatMoney, formatSignedMoney } from '../../../game/ming/mingSalvageFormat';
import { MingDrawerShell, drawerSearchStyle, drawerSectionTitle } from './MingDrawerShell';

type Props = {
  open: boolean;
  budget?: SalvageBudget;
  treasuryText?: string;
  onClose: () => void;
};

export const MingEconomyDrawer: React.FC<Props> = ({ open, budget, treasuryText, onClose }) => {
  const [tab, setTab] = useState<'国库' | '内库'>('国库');
  const [q, setQ] = useState('');
  const account = budget?.[tab];
  const match = (text: string) => !q.trim() || text.includes(q.trim());

  const incomeRows = useMemo(
    () => (account?.income || []).filter((item) => match(`${item.name} ${item.note || ''}`)),
    [account, q],
  );
  const expenseRows = useMemo(
    () => (account?.expense || []).filter((item) => match(`${item.name} ${item.note || ''}`)),
    [account, q],
  );
  const movementRows = useMemo(
    () =>
      (account?.movements || []).filter((m) => match(`${m.category || ''} ${m.reason || ''}`)),
    [account, q],
  );

  return (
    <MingDrawerShell open={open} title="户部 · 经济" subtitle="太仓流水与定额" onClose={onClose} width={400}>
      {treasuryText && (
        <p style={{ fontSize: 12, color: '#aaa', margin: '0 0 10px', lineHeight: 1.6 }}>{treasuryText}</p>
      )}
      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {(['国库', '内库'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            style={{
              flex: 1,
              padding: '6px 8px',
              borderRadius: 6,
              border: tab === t ? '1px solid rgba(255,215,0,0.75)' : '1px solid rgba(255,255,255,0.1)',
              background: tab === t ? 'rgba(255,215,0,0.12)' : 'transparent',
              color: tab === t ? '#ffd700' : '#aaa',
              cursor: 'pointer',
            }}
          >
            {t}
          </button>
        ))}
      </div>
      {!account ? (
        <p style={{ color: '#888' }}>暂无账册数据。</p>
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 10,
              fontSize: 13,
              color: '#ddd',
            }}
          >
            <span>
              余额 <b style={{ color: '#ffd700' }}>{formatMoney(account.balance)}</b>
            </span>
            <span style={{ color: account.net >= 0 ? '#52c41a' : '#f5222d' }}>
              月净 {formatSignedMoney(account.net)}
            </span>
          </div>
          <input
            style={drawerSearchStyle}
            placeholder="搜索收支项…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <div style={drawerSectionTitle}>固定收入</div>
          {incomeRows.map((item) => (
            <div
              key={`in-${item.name}`}
              style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}
            >
              <span style={{ color: '#ccc' }}>
                {item.name}
                {item.note && <small style={{ display: 'block', color: '#777' }}>{item.note}</small>}
              </span>
              <b style={{ color: '#52c41a' }}>+{formatMoney(item.amount)}</b>
            </div>
          ))}
          <div style={drawerSectionTitle}>固定支出</div>
          {expenseRows.map((item) => (
            <div
              key={`ex-${item.name}`}
              style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}
            >
              <span style={{ color: '#ccc' }}>{item.name}</span>
              <b style={{ color: '#f5222d' }}>-{formatMoney(item.amount)}</b>
            </div>
          ))}
          {movementRows.length > 0 && (
            <>
              <div style={drawerSectionTitle}>本月一次性入账</div>
              {movementRows.map((m, i) => (
                <div
                  key={`mv-${i}`}
                  style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}
                >
                  <span style={{ color: '#ccc' }}>{m.category || m.reason}</span>
                  <b style={{ color: m.delta >= 0 ? '#52c41a' : '#f5222d' }}>
                    {formatSignedMoney(m.delta)}
                  </b>
                </div>
              ))}
            </>
          )}
        </>
      )}
    </MingDrawerShell>
  );
};
