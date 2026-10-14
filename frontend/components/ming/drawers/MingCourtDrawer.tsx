'use client';

import React, { useMemo, useState } from 'react';
import type { SalvageMinister } from '../../../game/ming/salvageStateTypes';
import { resolvePlayerPowerId, type ScenarioId } from '../../../game/scenarios';
import { useMingStore } from '../../../game/ming/mingStore';
import {
  mingAddFavorite,
  mingArchiveMinister,
  mingRemoveFavorite,
  mingRestoreMinister,
} from '../../../lib/mingApi';
import { MingDrawerShell, drawerRowStyle, drawerSearchStyle, drawerSectionTitle } from './MingDrawerShell';
import { MingCourtPerspectivePanel } from '../MingCourtPerspectivePanel';
import { CharacterNameTooltip } from '../../CharacterNameTooltip';

type Props = {
  open: boolean;
  ministers: SalvageMinister[];
  archivedMinisters?: SalvageMinister[];
  scenarioId?: ScenarioId;
  onOpenChat: (name: string) => void;
  onOpenCourtChat?: () => void;
  onChanged?: () => void;
  onClose: () => void;
};

const GROUPS = ['内阁六部', '收藏', '全部', '已归档'] as const;
const CABINET_OFFICE_TYPES = ['内阁', '中书', '枢密', '吏部', '户部', '礼部', '兵部', '刑部', '工部'];
const SIX_MINISTRIES = ['吏部', '户部', '礼部', '兵部', '刑部', '工部'] as const;
const CENTRAL_OFFICES = ['中书', '枢密', '内阁'] as const;

function groupMinistersByOffice(
  ministers: SalvageMinister[],
  offices: readonly string[],
): Map<string, SalvageMinister[]> {
  const map = new Map<string, SalvageMinister[]>();
  for (const office of offices) map.set(office, []);
  for (const m of ministers) {
    const key = m.office_type && map.has(m.office_type) ? m.office_type : '';
    if (key) map.get(key)!.push(m);
  }
  return map;
}

export const MingCourtDrawer: React.FC<Props> = ({
  open,
  ministers,
  archivedMinisters,
  scenarioId,
  onOpenChat,
  onOpenCourtChat,
  onChanged,
  onClose,
}) => {
  const [group, setGroup] = useState<(typeof GROUPS)[number]>('内阁六部');
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState('');
  const menuActiveSalvageId = useMingStore((s) => s.menuActiveSalvageId);
  const nationState = useMingStore((s) => s.nationState);
  const gameYear = useMingStore((s) => s.salvageRaw?.turn?.year);
  const effectiveScenarioId = scenarioId || menuActiveSalvageId || undefined;
  const playerPower = resolvePlayerPowerId({
    scenarioId: effectiveScenarioId,
    salvageScenarioId: menuActiveSalvageId,
    dynasty: nationState?.dynasty,
    gameYear,
  });

  const active = useMemo(
    () => ministers.filter((m) => (m.power_id || playerPower) === playerPower && m.status === 'active'),
    [ministers, playerPower],
  );
  const archived = archivedMinisters || [];

  const cabinetRows = useMemo(
    () => active.filter((m) => CABINET_OFFICE_TYPES.includes(m.office_type || '')),
    [active],
  );
  const sixMinistryRows = useMemo(
    () => groupMinistersByOffice(cabinetRows, SIX_MINISTRIES),
    [cabinetRows],
  );
  const centralRows = useMemo(
    () => groupMinistersByOffice(cabinetRows, CENTRAL_OFFICES),
    [cabinetRows],
  );
  const isSong = playerPower === 'song';

  const rows = useMemo(() => {
    let list: SalvageMinister[] = [];
    if (group === '已归档') list = archived;
    else if (group === '收藏') list = active.filter((m) => m.favorite);
    else if (group === '全部') list = active;
    else list = active.filter((m) => CABINET_OFFICE_TYPES.includes(m.office_type || ''));
    if (!q.trim()) return list;
    const needle = q.trim();
    return list.filter(
      (m) =>
        m.name.includes(needle) ||
        (m.office || '').includes(needle) ||
        (m.office_type || '').includes(needle),
    );
  }, [active, archived, group, q]);

  const runAction = async (label: string, fn: () => Promise<unknown>) => {
    try {
      setBusy(label);
      await fn();
      onChanged?.();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy('');
    }
  };

  return (
    <MingDrawerShell open={open} title="朝堂" subtitle="召见、收藏、归档" onClose={onClose} width={400}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
        {GROUPS.map((g) => (
          <button
            key={g}
            type="button"
            onClick={() => setGroup(g)}
            style={{
              padding: '4px 8px',
              fontSize: 11,
              borderRadius: 6,
              border: group === g ? '1px solid rgba(255,215,0,0.75)' : '1px solid rgba(255,255,255,0.1)',
              background: group === g ? 'rgba(255,215,0,0.12)' : 'transparent',
              color: group === g ? '#ffd700' : '#aaa',
              cursor: 'pointer',
            }}
          >
            {g}
          </button>
        ))}
      </div>
      {onOpenCourtChat && (
        <button
          type="button"
          disabled={!!busy}
          onClick={() => {
            onOpenCourtChat();
            onClose();
          }}
          style={{
            width: '100%',
            marginBottom: 10,
            padding: '8px 12px',
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.5)',
            background: 'rgba(255,215,0,0.08)',
            color: '#ffd700',
            cursor: 'pointer',
          }}
        >
          廷议（多臣共议）
        </button>
      )}
      <input
        style={drawerSearchStyle}
        placeholder="搜索大臣…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {busy && <p style={{ fontSize: 11, color: '#888', margin: '0 0 8px' }}>{busy}…</p>}
      {group === '内阁六部' && (
        <>
          {isSong && (
            <section style={{ marginBottom: 12 }}>
              <div style={drawerSectionTitle}>六部尚书</div>
              {SIX_MINISTRIES.map((office) => {
                const rows = sixMinistryRows.get(office) || [];
                return (
                  <div key={office} style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: '#ffd700', marginBottom: 4 }}>{office}</div>
                    {rows.length ? (
                      rows.map((m) => (
                        <CharacterNameTooltip
                          key={m.name}
                          name={m.name}
                          brief={m.summary}
                          title={m.office || m.office_type}
                        >
                        <button
                          type="button"
                          style={{ ...drawerRowStyle(false), width: '100%', textAlign: 'left', marginBottom: 4 }}
                          onClick={() => {
                            onOpenChat(m.name);
                            onClose();
                          }}
                        >
                          <div style={{ fontWeight: 600 }}>{m.name}</div>
                          <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>{m.office || '—'}</div>
                        </button>
                        </CharacterNameTooltip>
                      ))
                    ) : (
                      <p style={{ color: '#666', fontSize: 12, margin: '0 0 4px' }}>缺员</p>
                    )}
                  </div>
                );
              })}
              <div style={{ ...drawerSectionTitle, marginTop: 10 }}>中书 · 枢密</div>
              {[...CENTRAL_OFFICES, '其他' as const].map((office) => {
                const rows =
                  office === '其他'
                    ? cabinetRows.filter(
                        (m) =>
                          !SIX_MINISTRIES.includes(m.office_type as (typeof SIX_MINISTRIES)[number]) &&
                          !CENTRAL_OFFICES.includes(m.office_type as (typeof CENTRAL_OFFICES)[number]),
                      )
                    : centralRows.get(office) || [];
                if (!rows.length) return null;
                return (
                  <div key={office} style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: '#c9a227', marginBottom: 4 }}>{office}</div>
                    {rows.map((m) => (
                      <CharacterNameTooltip
                        key={m.name}
                        name={m.name}
                        brief={m.summary}
                        title={m.office || m.office_type}
                      >
                      <button
                        type="button"
                        style={{ ...drawerRowStyle(false), width: '100%', textAlign: 'left', marginBottom: 4 }}
                        onClick={() => {
                          onOpenChat(m.name);
                          onClose();
                        }}
                      >
                        <div style={{ fontWeight: 600 }}>{m.name}</div>
                        <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>{m.office || '—'}</div>
                      </button>
                      </CharacterNameTooltip>
                    ))}
                  </div>
                );
              })}
            </section>
          )}
          <MingCourtPerspectivePanel
            ministers={cabinetRows}
            onOpenChat={(name) => {
              onOpenChat(name);
              onClose();
            }}
          />
        </>
      )}
      <div style={drawerSectionTitle}>
        {group} ({rows.length})
      </div>
      {rows.map((m) => (
        <div key={m.name} style={{ ...drawerRowStyle(false), cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <CharacterNameTooltip
              name={m.name}
              brief={m.summary}
              title={m.office || m.office_type}
            >
            <button
              type="button"
              style={{
                flex: 1,
                textAlign: 'left',
                background: 'transparent',
                border: 'none',
                color: '#eee',
                cursor: 'pointer',
                padding: 0,
              }}
              onClick={() => {
                onOpenChat(m.name);
                onClose();
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {m.name}
                {m.favorite && <span style={{ color: '#ffd700', marginLeft: 4 }}>★</span>}
              </div>
              <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                {m.office || m.office_type || '—'}
              </div>
            </button>
            </CharacterNameTooltip>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {group !== '已归档' && (
                <>
                  <button
                    type="button"
                    disabled={!!busy}
                    style={{ fontSize: 10, padding: '2px 6px', cursor: 'pointer' }}
                    onClick={() =>
                      void runAction(m.favorite ? '取消收藏' : '收藏', () =>
                        m.favorite ? mingRemoveFavorite(m.name) : mingAddFavorite(m.name),
                      )
                    }
                  >
                    {m.favorite ? '取消★' : '★'}
                  </button>
                  <button
                    type="button"
                    disabled={!!busy}
                    style={{ fontSize: 10, padding: '2px 6px', cursor: 'pointer' }}
                    onClick={() => void runAction('归档', () => mingArchiveMinister(m.name))}
                  >
                    归档
                  </button>
                </>
              )}
              {group === '已归档' && (
                <button
                  type="button"
                  disabled={!!busy}
                  style={{ fontSize: 10, padding: '2px 6px', cursor: 'pointer' }}
                  onClick={() => void runAction('恢复', () => mingRestoreMinister(m.name))}
                >
                  恢复
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
      {!rows.length && <p style={{ color: '#888', fontSize: 13 }}>暂无大臣。</p>}
    </MingDrawerShell>
  );
};
