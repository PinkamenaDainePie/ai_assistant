'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageRegion } from '../../../game/ming/salvageStateTypes';
import { salvageRegionDisplayName } from '../../../lib/mingSalvageAdapter';
import { getPlayerPowerId, type ScenarioId } from '../../../game/scenarios';
import { regionMonthlyTax, unrestTone } from '../../../game/ming/mingSalvageFormat';
import { MingDrawerShell, drawerRowStyle, drawerSearchStyle, drawerSectionTitle } from './MingDrawerShell';

type Props = {
  open: boolean;
  regions: SalvageRegion[];
  regionWarning?: string;
  scenarioId?: ScenarioId;
  onClose: () => void;
};

export const MingRegionDrawer: React.FC<Props> = ({
  open,
  regions,
  regionWarning,
  scenarioId,
  onClose,
}) => {
  const [q, setQ] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const playerPower = getPlayerPowerId(scenarioId);
  const isSong = playerPower === 'song';
  const playerRegions = useMemo(
    () => regions.filter((r) => (r.controlled_by || playerPower) === playerPower),
    [playerPower, regions],
  );
  const filtered = useMemo(() => {
    if (!q.trim()) return playerRegions;
    const needle = q.trim();
    return playerRegions.filter((r) => {
      const label = salvageRegionDisplayName(r);
      return (
        label.includes(needle)
        || r.name.includes(needle)
        || (r.circuit_name?.includes(needle) ?? false)
      );
    });
  }, [playerRegions, q]);
  const selected = playerRegions.find((r) => r.id === selectedId) || null;

  return (
    <MingDrawerShell
      open={open}
      title={isSong ? '诸路' : '省份'}
      subtitle={isSong ? '北宋路分 · 直辖疆域' : '大明直辖行省'}
      onClose={onClose}
    >
      {regionWarning && (
        <p style={{ fontSize: 12, color: '#faad14', margin: '0 0 10px' }}>{regionWarning}</p>
      )}
      <input
        style={drawerSearchStyle}
        placeholder={isSong ? '搜索路名…' : '搜索省份名…'}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {filtered.map((r) => (
        <button
          key={r.id}
          type="button"
          style={{
            ...drawerRowStyle(selectedId === r.id),
            borderLeft: `3px solid ${unrestTone(r.unrest)}`,
          }}
          onClick={() => setSelectedId(r.id === selectedId ? '' : r.id)}
        >
          <div style={{ fontWeight: 600 }}>{salvageRegionDisplayName(r)}</div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
            动乱 {r.unrest} · 实收 {regionMonthlyTax(r)} 万/月
          </div>
        </button>
      ))}
      {!filtered.length && (
        <p style={{ color: '#888', fontSize: 13 }}>{q ? '无匹配结果。' : isSong ? '暂无路分记录。' : '暂无省份记录。'}</p>
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
          <h3 style={{ margin: '0 0 4px', color: '#ffe7a3' }}>{salvageRegionDisplayName(selected)}</h3>
          <p style={{ margin: 0, color: '#888' }}>
            {selected.kind || (isSong ? '路' : '行省')} · {selected.status || '—'}
          </p>
          <div style={drawerSectionTitle}>钱粮</div>
          <p style={{ margin: 0, color: '#ccc' }}>
            田赋账面 {selected.tax_per_turn ?? '—'} 万/月 · 四税实收 {regionMonthlyTax(selected)} 万/月
            {selected.tax_efficiency != null && ` · 效率 ${selected.tax_efficiency}%`}
          </p>
          <div style={drawerSectionTitle}>民情</div>
          <p style={{ margin: 0, color: '#ccc' }}>
            人口 {selected.population ?? '—'} · 民心 {selected.public_support ?? '—'} · 动乱{' '}
            {selected.unrest}
          </p>
          {(selected.natural_disaster || selected.human_disaster) && (
            <>
              <div style={drawerSectionTitle}>灾患</div>
              <p style={{ margin: 0, color: '#faa' }}>
                {[selected.natural_disaster, selected.human_disaster].filter(Boolean).join(' · ')}
              </p>
            </>
          )}
          <div style={drawerSectionTitle}>田土</div>
          <p style={{ margin: 0, color: '#ccc' }}>
            册田 {selected.registered_land ?? '—'} · 隐田 {selected.hidden_land ?? '—'} · 粮产{' '}
            {selected.grain_output ?? '—'} / 库存 {selected.grain_stock ?? '—'}
          </p>
        </section>
      )}
    </MingDrawerShell>
  );
};
