'use client';

import React from 'react';
import type { MingExtractionData } from '../../game/ming/mingTurnPhase';

function pickField(obj: Record<string, unknown> | undefined, cn: string, en: string): unknown {
  if (!obj) return undefined;
  return obj[cn] ?? obj[en];
}

function pickItem(obj: Record<string, unknown>, cn: string, en: string): unknown {
  return obj[cn] ?? obj[en];
}

function fmtDelta(n: unknown): string {
  const num = Number(n);
  if (!Number.isFinite(num)) return '0';
  return num > 0 ? `+${num}` : String(num);
}

function isEmpty(d: unknown): boolean {
  if (d == null) return true;
  if (Array.isArray(d)) return d.length === 0;
  if (typeof d === 'object') return Object.keys(d as object).length === 0;
  return false;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 13, color: '#ffd700', margin: '0 0 8px', borderBottom: '1px solid rgba(255,215,0,0.2)', paddingBottom: 4 }}>
        {title}
      </h3>
      {children}
    </section>
  );
}

function MetricBlock({ data }: { data: Record<string, unknown> }) {
  if (isEmpty(data)) return <p style={{ color: '#888', fontSize: 12 }}>无</p>;
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12 }}>
      {Object.entries(data).map(([k, v]) => (
        <li key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ color: '#aaa' }}>{k}</span>
          <b style={{ color: Number(v) >= 0 ? '#4caf50' : '#e57373' }}>{fmtDelta(v)}</b>
        </li>
      ))}
    </ul>
  );
}

function ListBlock({ data, render }: { data: unknown[]; render: (item: Record<string, unknown>, i: number) => React.ReactNode }) {
  if (!Array.isArray(data) || data.length === 0) return <p style={{ color: '#888', fontSize: 12 }}>无</p>;
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12 }}>
      {data.map((item, i) => (
        <li key={i} style={{ marginBottom: 8, padding: 8, borderRadius: 6, background: 'rgba(0,0,0,0.25)' }}>
          {render(item as Record<string, unknown>, i)}
        </li>
      ))}
    </ul>
  );
}

export function MingExtractionView({
  data,
  loading,
  error,
}: {
  data: MingExtractionData | null;
  loading: boolean;
  error: string;
}) {
  if (loading) return <p style={{ color: '#aaa', fontSize: 13 }}>加载中…</p>;
  if (error) return <p style={{ color: '#e57373', fontSize: 13 }}>加载失败：{error}</p>;
  if (!data || !data.exists) return <p style={{ color: '#888', fontSize: 13 }}>该回合无 extractor 数据。</p>;

  const rawOut = data.extractor_output;
  if (!rawOut || typeof rawOut !== 'object') {
    return (
      <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#ccc' }}>
        {String(rawOut ?? '')}
      </pre>
    );
  }

  const out =
    (rawOut as { mode?: string; merged?: Record<string, unknown> }).mode === 'modular' &&
    (rawOut as { merged?: Record<string, unknown> }).merged
      ? (rawOut as { merged: Record<string, unknown> }).merged
      : rawOut;

  return (
    <div>
      <Section title="国势变化">
        <MetricBlock data={(pickField(out as Record<string, unknown>, '国势变化', 'metric_delta') as Record<string, unknown>) || {}} />
      </Section>
      <Section title="钱粮收支">
        <ListBlock
          data={(pickField(out as Record<string, unknown>, '钱粮收支', 'economy_moves') as unknown[]) || []}
          render={(item) => (
            <>
              <b style={{ color: Number(pickItem(item, '增量', 'delta')) >= 0 ? '#4caf50' : '#e57373' }}>
                {String(pickItem(item, '账户', 'account') || '?')} {fmtDelta(pickItem(item, '增量', 'delta'))} 万
              </b>
              <div style={{ color: '#999', marginTop: 4 }}>
                {String(pickItem(item, '分类', 'category') || '')}
                {pickItem(item, '原因', 'reason') ? ` — ${pickItem(item, '原因', 'reason')}` : ''}
              </div>
            </>
          )}
        />
      </Section>
      <Section title="局势推进">
        <ListBlock
          data={(pickField(out as Record<string, unknown>, '局势推进', 'issue_advances') as unknown[]) || []}
          render={(item) => (
            <>
              <b>
                局势 #{String(pickItem(item, '局势编号', 'issue_id'))} 进度 {fmtDelta(pickItem(item, '进度增量', 'delta_bar'))}
              </b>
              {pickItem(item, '阶段', 'stage_text') && (
                <div style={{ color: '#999', marginTop: 4 }}>{String(pickItem(item, '阶段', 'stage_text'))}</div>
              )}
              {pickItem(item, '叙述', 'narrative') && (
                <div style={{ color: '#bbb', marginTop: 4, lineHeight: 1.5 }}>{String(pickItem(item, '叙述', 'narrative'))}</div>
              )}
            </>
          )}
        />
      </Section>
      <Section title="新立局势">
        <ListBlock
          data={(pickField(out as Record<string, unknown>, '新立局势', 'new_issues') as unknown[]) || []}
          render={(item) => (
            <b>{String(pickItem(item, '标题', 'title') || pickItem(item, '编号', 'id') || '新事项')}</b>
          )}
        />
      </Section>
      <Section title="结案 / 失败">
        <ListBlock
          data={(pickField(out as Record<string, unknown>, '结案局势', 'close_issues') as unknown[]) || []}
          render={(item) => (
            <>
              <b style={{ color: pickItem(item, '原因', 'reason') === 'resolved' ? '#4caf50' : '#e57373' }}>
                局势 #{String(pickItem(item, '局势编号', 'issue_id'))}{' '}
                {pickItem(item, '原因', 'reason') === 'resolved' ? '结案' : '失败'}
              </b>
              {pickItem(item, '叙述', 'narrative') && (
                <div style={{ color: '#999', marginTop: 4 }}>{String(pickItem(item, '叙述', 'narrative'))}</div>
              )}
            </>
          )}
        />
      </Section>
    </div>
  );
}
