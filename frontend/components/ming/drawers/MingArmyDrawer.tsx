'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageArmy, SalvageArmsStockItem } from '../../../game/ming/salvageStateTypes';
import { labelPower } from '../../../game/ming/mingMapDisplay';
import { formatMoney } from '../../../game/ming/mingSalvageFormat';
import { useMingStore } from '../../../game/ming/mingStore';
import { resolvePlayerPowerId, type ScenarioId } from '../../../game/scenarios';
import { drawerRowStyle, drawerSearchStyle, MingDrawerShell, drawerSectionTitle } from './MingDrawerShell';

type Props = {
  open: boolean;
  armies: SalvageArmy[];
  armsStock?: SalvageArmsStockItem[];
  troopRates?: Record<string, number>;
  scenarioId?: ScenarioId;
  onClose: () => void;
};

export const MingArmyDrawer: React.FC<Props> = ({
  open,
  armies,
  armsStock,
  troopRates,
  scenarioId,
  onClose,
}) => {
  const [q, setQ] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const activeSalvageScenarioId = useMingStore((s) => s.activeSalvageScenarioId);
  const menuActiveSalvageId = useMingStore((s) => s.menuActiveSalvageId);
  const nationState = useMingStore((s) => s.nationState);
  const gameYear = useMingStore((s) => s.salvageRaw?.turn?.year);
  const effectiveScenarioId = scenarioId || activeSalvageScenarioId || undefined;
  const playerPower = resolvePlayerPowerId({
    scenarioId: effectiveScenarioId,
    salvageScenarioId: menuActiveSalvageId,
    dynasty: nationState?.dynasty,
    gameYear,
  });
  const playerArmies = useMemo(() => {
    const owned = armies.filter((a) => (a.owner_power || playerPower) === playerPower);
    if (owned.length) return owned;
    // 兜底：后端已标 song 但前端 scenario 仍落在 ming 默认时
    if (playerPower === 'song') {
      return armies.filter((a) => a.owner_power === 'song');
    }
    return owned;
  }, [armies, playerPower]);
  const filtered = useMemo(() => {
    if (!q.trim()) return playerArmies;
    const needle = q.trim();
    return playerArmies.filter(
      (a) =>
        a.name.includes(needle) ||
        (a.station || '').includes(needle) ||
        (a.commander || '').includes(needle),
    );
  }, [playerArmies, q]);
  const selected = playerArmies.find((a) => a.id === selectedId) || null;
  const visibleStock = (armsStock || []).filter((w) => w.unlocked && w.qty > 0);

  return (
    <MingDrawerShell
      open={open}
      title="兵部 · 军队"
      subtitle={playerPower === 'song' ? '禁军、边军编制与军备' : '番号、编制、军备'}
      onClose={onClose}
    >
      <input
        style={drawerSearchStyle}
        placeholder="搜索番号/驻地/统帅…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {visibleStock.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
          {visibleStock.map((w) => (
            <span
              key={w.id}
              style={{
                fontSize: 11,
                padding: '3px 8px',
                borderRadius: 999,
                border: '1px solid rgba(255,215,0,0.25)',
                color: '#ccc',
              }}
            >
              {w.name} <b style={{ color: '#ffd700' }}>{w.qty}</b>
            </span>
          ))}
        </div>
      )}
      {filtered.map((army) => (
        <button
          key={army.id}
          type="button"
          style={drawerRowStyle(selectedId === army.id)}
          onClick={() => setSelectedId(army.id === selectedId ? '' : army.id)}
        >
          <div style={{ fontWeight: 600 }}>{army.name}</div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
            {army.manpower}兵 · {army.station || '—'}
            {(army.arrears || 0) > 0 && (
              <span style={{ color: '#f5222d', marginLeft: 6 }}>欠饷{army.arrears}万</span>
            )}
          </div>
        </button>
      ))}
      {!filtered.length && (
        <p style={{ color: '#888', fontSize: 13 }}>
          {q ? '无匹配结果。' : `暂无${labelPower(playerPower)}军队记录。`}
        </p>
      )}
      {selected && (
        <section
          style={{
            marginTop: 14,
            padding: 12,
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.25)',
            background: 'rgba(0,0,0,0.35)',
            fontSize: 12,
            lineHeight: 1.7,
          }}
        >
          <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>{selected.name}</h3>
          <p style={{ margin: 0, color: '#aaa' }}>
            {selected.station || '—'} · {selected.theater || '—'}
          </p>
          <table style={{ width: '100%', marginTop: 8, borderCollapse: 'collapse' }}>
            <tbody>
              {[
                ['统帅', selected.commander || '—'],
                ['主管', selected.controller || '—'],
                ['兵种', selected.troop_type || '—'],
                ['兵力', String(selected.manpower)],
                ['月饷', `${selected.maintenance_per_turn ?? '—'}万两`],
                ['士气/补给', `${selected.morale ?? '—'} / ${selected.supply ?? '—'}`],
                ['操练/机动', `${selected.training ?? '—'} / ${selected.mobility ?? '—'}`],
                ['忠诚', String(selected.loyalty ?? '—')],
                ['状态', selected.status || '—'],
              ].map(([k, v]) => (
                <tr key={k}>
                  <th style={{ textAlign: 'left', color: '#888', padding: '3px 8px 3px 0', width: '30%' }}>
                    {k}
                  </th>
                  <td style={{ color: '#ddd' }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Object.entries(selected.troop_composition || {}).filter(([, n]) => Number(n) > 0).length > 0 && (
            <>
              <div style={{ ...drawerSectionTitle, marginTop: 10 }}>编制明细</div>
              {Object.entries(selected.troop_composition || {})
                .filter(([, n]) => Number(n) > 0)
                .map(([name, amount]) => {
                  const rate = troopRates?.[name] ?? 0.08;
                  const pay = (rate * Number(amount)) / 1000;
                  return (
                    <div key={name} style={{ display: 'flex', justifyContent: 'space-between', color: '#bbb' }}>
                      <span>
                        {name} ×{amount}
                      </span>
                      <span>{formatMoney(pay)}/月</span>
                    </div>
                  );
                })}
            </>
          )}
        </section>
      )}
    </MingDrawerShell>
  );
};
