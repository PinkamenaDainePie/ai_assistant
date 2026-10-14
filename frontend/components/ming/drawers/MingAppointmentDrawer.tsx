'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageDepartment, SalvageMinister } from '../../../game/ming/salvageStateTypes';
import { getPlayerPowerId, type ScenarioId } from '../../../game/scenarios';
import { MingDrawerShell, drawerRowStyle, drawerSearchStyle, drawerSectionTitle } from './MingDrawerShell';

type Props = {
  open: boolean;
  ministers: SalvageMinister[];
  departments?: SalvageDepartment[];
  scenarioId?: ScenarioId;
  onOpenChat: (name: string) => void;
  onClose: () => void;
};

const BASE_OFFICES = ['内阁', '中书', '枢密', '吏部', '户部', '礼部', '兵部', '刑部', '工部'];

export const MingAppointmentDrawer: React.FC<Props> = ({
  open,
  ministers,
  departments,
  scenarioId,
  onOpenChat,
  onClose,
}) => {
  const [q, setQ] = useState('');
  const [detail, setDetail] = useState<SalvageMinister | null>(null);
  const playerPower = getPlayerPowerId(scenarioId);
  const active = useMemo(
    () => ministers.filter((m) => (m.power_id || playerPower) === playerPower && m.status === 'active'),
    [ministers, playerPower],
  );
  const deptNames = new Set((departments || []).map((d) => d.name).filter(Boolean));
  const extraOffices = [
    ...new Set([
      ...(departments || []).map((d) => d.name),
      ...active.map((m) => m.office_type || '').filter(Boolean),
    ]),
  ].filter((name) => name && !BASE_OFFICES.includes(name) && deptNames.has(name));
  const offices = [...BASE_OFFICES, ...extraOffices];

  const grouped = useMemo(() => {
    const map = new Map<string, SalvageMinister[]>();
    for (const office of offices) map.set(office, []);
    map.set('其他', []);
    for (const m of active) {
      const key = m.office_type && map.has(m.office_type) ? m.office_type : '其他';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    if (!q.trim()) return map;
    const needle = q.trim();
    const filtered = new Map<string, SalvageMinister[]>();
    for (const [office, rows] of map) {
      const hit = rows.filter(
        (m) => m.name.includes(needle) || (m.office || '').includes(needle) || (m.faction || '').includes(needle),
      );
      if (hit.length) filtered.set(office, hit);
    }
    return filtered;
  }, [active, offices, q]);

  return (
    <MingDrawerShell open={open} title="吏部 · 官员" subtitle="在朝名册" onClose={onClose} width={400}>
      <input
        style={drawerSearchStyle}
        placeholder="搜索姓名/官职…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {[...grouped.entries()].map(([office, rows]) =>
        rows.length ? (
          <div key={office}>
            <div style={drawerSectionTitle}>{office}</div>
            {rows.map((m) => (
              <button
                key={m.name}
                type="button"
                style={drawerRowStyle(detail?.name === m.name)}
                onClick={() => setDetail(detail?.name === m.name ? null : m)}
              >
                <div style={{ fontWeight: 600 }}>{m.name}</div>
                <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                  {m.office || '—'} · {m.faction || '—'}
                </div>
              </button>
            ))}
          </div>
        ) : null,
      )}
      {detail && (
        <section
          style={{
            marginTop: 12,
            padding: 12,
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.25)',
            background: 'rgba(0,0,0,0.35)',
            fontSize: 12,
          }}
        >
          <h3 style={{ margin: '0 0 6px', color: '#ffe7a3' }}>{detail.name}</h3>
          <p style={{ margin: '0 0 8px', color: '#aaa', lineHeight: 1.6 }}>
            {detail.office || '—'} · {detail.status_label || detail.status || '在朝'}
          </p>
          {detail.summary && <p style={{ margin: '0 0 8px', color: '#ccc', lineHeight: 1.6 }}>{detail.summary}</p>}
          <button
            type="button"
            style={{
              marginTop: 10,
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid rgba(255,215,0,0.5)',
              background: 'rgba(255,215,0,0.1)',
              color: '#ffd700',
              cursor: 'pointer',
            }}
            onClick={() => {
              onOpenChat(detail.name);
              onClose();
            }}
          >
            召对
          </button>
        </section>
      )}
    </MingDrawerShell>
  );
};
