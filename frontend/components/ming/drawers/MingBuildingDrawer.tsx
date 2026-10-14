'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageMapNode, SalvageTechnology } from '../../../game/ming/salvageStateTypes';
import { useMingStore } from '../../../game/ming/mingStore';
import { resolvePlayerPowerId, type ScenarioId } from '../../../game/scenarios';
import { MingDrawerShell, drawerRowStyle, drawerSearchStyle, drawerSectionTitle } from './MingDrawerShell';

type Props = {
  open: boolean;
  mapNodes?: SalvageMapNode[];
  technologies?: SalvageTechnology[];
  scenarioId?: ScenarioId;
  onClose: () => void;
};

export const MingBuildingDrawer: React.FC<Props> = ({
  open,
  mapNodes,
  technologies,
  scenarioId,
  onClose,
}) => {
  const [q, setQ] = useState('');
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
  const isSong = playerPower === 'song';

  const buildings = useMemo(() => {
    const out: Array<{ id: string; name: string; regionLabel: string; category?: string; level?: number }> = [];
    for (const node of mapNodes || []) {
      if (node.kind === 'external') continue;
      const regionLabel = node.region?.name || node.label || node.id;
      for (const b of node.buildings || []) {
        out.push({
          id: b.id,
          name: b.name,
          regionLabel,
          category: b.category,
          level: b.level,
        });
      }
    }
    return out;
  }, [mapNodes]);

  const filteredBuildings = useMemo(() => {
    if (!q.trim()) return buildings;
    const needle = q.trim();
    return buildings.filter(
      (b) => b.name.includes(needle) || b.regionLabel.includes(needle) || (b.category || '').includes(needle),
    );
  }, [buildings, q]);

  const filteredTech = useMemo(() => {
    const rows = technologies || [];
    if (!q.trim()) return rows;
    const needle = q.trim();
    return rows.filter(
      (t) => t.name.includes(needle) || (t.category || '').includes(needle) || (t.effect_summary || '').includes(needle),
    );
  }, [technologies, q]);

  const buildingSectionTitle = isSong ? '诸路工役' : '天下营造';
  const techSectionTitle = isSong ? '技艺条贯' : '技艺';

  return (
    <MingDrawerShell
      open={open}
      title="工部 · 营造"
      subtitle={isSong ? '将作·军器·都水诸监与河渠仓廪' : '营造与技艺'}
      onClose={onClose}
      width={400}
    >
      <input
        style={drawerSearchStyle}
        placeholder={isSong ? '搜索工役/河渠/仓廪…' : '搜索建筑/技艺…'}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div style={drawerSectionTitle}>
        {buildingSectionTitle} ({filteredBuildings.length})
      </div>
      {filteredBuildings.map((b) => (
        <div key={b.id} style={{ ...drawerRowStyle(false), cursor: 'default' }}>
          <div style={{ fontWeight: 600 }}>{b.name}</div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
            {b.regionLabel} · {b.category || (isSong ? '工役' : '营造')}
            {b.level != null && ` · Lv${b.level}`}
          </div>
        </div>
      ))}
      {!filteredBuildings.length && (
        <p style={{ color: '#888', fontSize: 12 }}>
          {isSong ? '暂无在册工役。新局或继续游戏后由工部载入。' : '暂无建筑记录。'}
        </p>
      )}
      <div style={drawerSectionTitle}>
        {techSectionTitle} ({filteredTech.length})
      </div>
      {filteredTech.map((t) => (
        <div key={t.id} style={{ ...drawerRowStyle(false), cursor: 'default' }}>
          <div style={{ fontWeight: 600 }}>
            {t.name}{' '}
            <span style={{ fontSize: 10, color: t.status === 'active' ? '#52c41a' : '#888' }}>
              {t.status || '—'}
            </span>
          </div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
            {t.category || '技艺'} · {t.effect_summary || '—'}
          </div>
        </div>
      ))}
      {!filteredTech.length && (
        <p style={{ color: '#888', fontSize: 12 }}>{isSong ? '暂无在研技艺。' : '暂无技艺记录。'}</p>
      )}
    </MingDrawerShell>
  );
};
