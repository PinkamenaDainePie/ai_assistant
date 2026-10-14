'use client';

import React from 'react';
import type { MingGameState } from '../../game/ming/mingTurnPhase';
import type { SalvageGameState } from '../../lib/mingSalvageAdapter';
import { MingFullscreenModal } from './MingFullscreenModal';
import { formatMingReportText } from '../../game/ming/mingReportFormat';

type Props = {
  state: MingGameState;
  salvageRaw?: SalvageGameState;
  lastReport?: string;
  onClose: () => void;
};

export const MingStateModal: React.FC<Props> = ({ state, salvageRaw, lastReport, onClose }) => {
  const budget = salvageRaw?.budget as Record<string, { balance?: number; net?: number }> | undefined;
  const legacies = (salvageRaw?.legacies as Array<{ name?: string; effect_text?: string }>) || [];
  const victory = salvageRaw?.victory_status as Record<string, unknown> | undefined;

  return (
    <MingFullscreenModal
      wide
      title="本回合国势总览"
      subtitle={`${state.turn.label} · 阶段 ${state.turn_phase}`}
      onClose={onClose}
    >
      <section style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>国势指标</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 13 }}>
          {Object.entries(state.metrics).map(([k, v]) => (
            <li key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ color: '#aaa' }}>{k}</span>
              <b>{v}</b>
            </li>
          ))}
        </ul>
      </section>

      {budget && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>钱粮概览</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12 }}>
            {Object.entries(budget).map(([name, acc]) => (
              <li key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                <span style={{ color: '#aaa' }}>{name}</span>
                <span>
                  余额 {acc.balance ?? '—'} · 净 {acc.net ?? '—'} 万
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {legacies.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>现行修正（{legacies.length}）</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12 }}>
            {legacies.map((l, i) => (
              <li key={i} style={{ marginBottom: 6, color: '#bbb' }}>
                <b style={{ color: '#ffe7a3' }}>{l.name}</b>
                {l.effect_text ? ` — ${l.effect_text}` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}

      {victory && Object.keys(victory).length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>胜利条件</h3>
          <pre style={{ fontSize: 12, color: '#aaa', whiteSpace: 'pre-wrap', margin: 0 }}>
            {JSON.stringify(victory, null, 2)}
          </pre>
        </section>
      )}

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>
          在办局势（{state.issues.length}）
        </h3>
        {state.issues.length === 0 ? (
          <p style={{ color: '#888', fontSize: 12 }}>无在办局势。</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12 }}>
            {state.issues.map((issue) => (
              <li key={issue.id} style={{ marginBottom: 8, padding: 8, background: 'rgba(0,0,0,0.25)', borderRadius: 6 }}>
                <b>{issue.title}</b>
                <div style={{ color: '#888', marginTop: 4 }}>
                  进度 {issue.bar_value} · {issue.stage_text || '—'}
                  {issue.assignee ? ` · 承办：${issue.assignee}` : ''}
                  {issue.budget_pool ? ` · 专款 ${issue.budget_pool}万` : ''}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>
          本月指令（{state.directives.length + state.structured_directives.length}）
        </h3>
        <p style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
          待核定 {state.pending_count} 道 · draft {state.directives.filter((d) => d.status === 'draft').length} 道 · 固定指令 {state.structured_directives.length} 道
        </p>
        {state.directives.slice(0, 8).map((d) => (
          <div key={d.id} style={{ fontSize: 12, color: '#bbb', marginBottom: 4 }}>
            #{d.id} [{d.status}] {d.text.slice(0, 80)}{d.text.length > 80 ? '…' : ''}
          </div>
        ))}
      </section>

      {(lastReport || state.last_report || state.previous_summary) && (
        <section>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>近期奏报</h3>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.6, color: '#aaa', margin: 0, maxHeight: 200, overflow: 'auto' }}>
            {formatMingReportText(lastReport || state.last_report || state.previous_summary || '')}
          </pre>
        </section>
      )}
    </MingFullscreenModal>
  );
};
