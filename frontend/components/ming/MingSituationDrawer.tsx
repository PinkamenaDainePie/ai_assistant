'use client';

import React, { useMemo, useState } from 'react';
import type { MingClosedIssue, MingSalvageIssue } from '../../game/ming/mingTurnPhase';
import type { Character } from '../../game/types';
import type { ScenarioId } from '../../game/scenarios';
import type { SalvageGameState } from '../../lib/mingSalvageAdapter';
import { mingDeleteManualIssue } from '../../lib/mingApi';
import {
  countMingDecreeIssues,
  formatMingClosedEffect,
  isMingLongTermIssue,
} from '../../game/ming/mingSituationFormat';
import { MingManualIssueEditor } from './MingManualIssueEditor';
import { MingSituationDetailModal } from './MingSituationDetailModal';
import { mingCloseBtn, mingOutlineBtn } from '../../game/ming/mingUiStyles';

function barTone(value: number): string {
  if (value >= 65) return '#4caf50';
  if (value <= 35) return '#e57373';
  return '#ffb74d';
}

type Props = {
  open: boolean;
  issues: MingSalvageIssue[];
  closedIssues: MingClosedIssue[];
  maxDecreeIssues?: number;
  characters: Character[];
  salvageRaw?: SalvageGameState;
  scenarioId?: ScenarioId;
  onClose: () => void;
  onChanged: () => void | Promise<void>;
};

function IssueRow({
  issue,
  onDetail,
  onEdit,
  onChanged,
}: {
  issue: MingSalvageIssue;
  onDetail: () => void;
  onEdit?: () => void;
  onChanged: () => void | Promise<void>;
}) {
  const handleDelete = async () => {
    if (!window.confirm(`确定删除手动局势〔${issue.title}〕？`)) return;
    try {
      await mingDeleteManualIssue(issue.id);
      await onChanged();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  return (
    <article
      style={{
        marginBottom: 10,
        padding: 10,
        borderRadius: 8,
        border: '1px solid rgba(255,215,0,0.2)',
        background: 'rgba(0,0,0,0.3)',
        cursor: 'pointer',
      }}
      onClick={onDetail}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
        <b style={{ color: '#f5f5f5', fontSize: 14 }}>
          {issue.title}
          {issue.is_manual && (
            <span style={{ fontSize: 10, color: '#d4af37', marginLeft: 6 }}>手动</span>
          )}
        </b>
        <span style={{ color: '#c9a227', fontSize: 13 }}>{issue.bar_value}</span>
      </div>
      <div style={{ height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.08)', marginBottom: 6 }}>
        <div
          style={{
            height: '100%',
            width: `${issue.bar_value}%`,
            background: barTone(issue.bar_value),
            borderRadius: 999,
          }}
        />
      </div>
      <p style={{ fontSize: 12, color: '#bbb', margin: 0, lineHeight: 1.5 }}>{issue.stage_text}</p>
      {issue.assignee && (
        <p style={{ fontSize: 11, color: '#888', margin: '6px 0 0' }}>承办：{issue.assignee}</p>
      )}
      {issue.is_manual && (
        <div
          style={{ display: 'flex', gap: 6, marginTop: 8 }}
          onClick={(e) => e.stopPropagation()}
        >
          <button type="button" style={mingOutlineBtn} onClick={onEdit}>编辑</button>
          <button type="button" style={mingOutlineBtn} onClick={() => void handleDelete()}>删除</button>
        </div>
      )}
    </article>
  );
}

export const MingSituationDrawer: React.FC<Props> = ({
  open,
  issues,
  closedIssues,
  maxDecreeIssues = 10,
  characters,
  salvageRaw,
  scenarioId = 'ming_wanli',
  onClose,
  onChanged,
}) => {
  const [detailIssue, setDetailIssue] = useState<MingSalvageIssue | null>(null);
  const [editor, setEditor] = useState<{ mode: 'create' } | { mode: 'edit'; issue: MingSalvageIssue } | null>(null);

  const longTerm = useMemo(
    () => issues.filter(isMingLongTermIssue).sort((a, b) => a.id - b.id),
    [issues],
  );
  const nearTerm = useMemo(
    () => issues.filter((i) => !isMingLongTermIssue(i)).sort((a, b) => a.id - b.id),
    [issues],
  );
  const decreeCount = countMingDecreeIssues(issues);
  const atLimit = decreeCount >= maxDecreeIssues;

  if (!open) return null;

  return (
    <>
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1400,
          background: 'rgba(0,0,0,0.45)',
        }}
        onClick={onClose}
      />
      <aside
        style={{
          position: 'fixed',
          right: 0,
          top: 0,
          bottom: 0,
          width: 'min(400px, 92vw)',
          zIndex: 1500,
          background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 100%)',
          borderLeft: '1px solid rgba(255,215,0,0.45)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.6)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid rgba(255,215,0,0.2)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: 8,
          }}
        >
          <div>
            <strong style={{ color: '#ffe7a3', fontSize: 16 }}>局势管理</strong>
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              {issues.length} 条在办 · {closedIssues.length} 条本回合结案
            </div>
          </div>
          <button type="button" onClick={onClose} style={mingCloseBtn} aria-label="关闭">×</button>
        </div>

        <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,215,0,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: '#aaa' }}>
              decree 局势 {decreeCount} / {maxDecreeIssues}
            </span>
            <button
              type="button"
              style={mingOutlineBtn}
              disabled={atLimit}
              onClick={() => setEditor({ mode: 'create' })}
            >
              ＋ 新建局势
            </button>
          </div>
          {atLimit && (
            <p style={{ fontSize: 11, color: '#ffb74d', margin: '8px 0 0', lineHeight: 1.5 }}>
              已达上限。可在主菜单游戏设置调高（会增加推演 token）。
            </p>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {closedIssues.length > 0 && (
            <section style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 13, color: '#ffd700', margin: '0 0 8px' }}>本回合结案</h3>
              {closedIssues.map((ci) => (
                <div
                  key={ci.id}
                  style={{
                    marginBottom: 8,
                    padding: 10,
                    borderRadius: 8,
                    border: '1px solid rgba(255,215,0,0.15)',
                    background: 'rgba(0,0,0,0.25)',
                    fontSize: 12,
                  }}
                >
                  <div style={{ marginBottom: 4 }}>
                    <b style={{ color: '#ffe7a3' }}>
                      {ci.status === 'resolved' ? '已结案' : ci.status === 'failed' ? '已崩坏' : '已撤'}
                    </b>
                    <span style={{ color: '#ccc', marginLeft: 8 }}>{ci.title}</span>
                  </div>
                  <div style={{ color: '#999' }}>{formatMingClosedEffect(ci.effect)}</div>
                </div>
              ))}
            </section>
          )}

          {longTerm.length > 0 && (
            <section style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 13, color: '#ffd700', margin: '0 0 8px' }}>长期局势</h3>
              {longTerm.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  onDetail={() => setDetailIssue(issue)}
                  onEdit={() => setEditor({ mode: 'edit', issue })}
                  onChanged={onChanged}
                />
              ))}
            </section>
          )}

          {nearTerm.length > 0 && (
            <section>
              <h3 style={{ fontSize: 13, color: '#ffd700', margin: '0 0 8px' }}>近期局势</h3>
              {nearTerm.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  onDetail={() => setDetailIssue(issue)}
                  onEdit={() => setEditor({ mode: 'edit', issue })}
                  onChanged={onChanged}
                />
              ))}
            </section>
          )}

          {!issues.length && !closedIssues.length && (
            <p style={{ fontSize: 13, color: '#888', lineHeight: 1.6 }}>当前无在办局势，可新建手动局势追踪长期工程。</p>
          )}
        </div>
      </aside>

      {detailIssue && (
        <MingSituationDetailModal
          issue={detailIssue}
          characters={characters}
          onClose={() => setDetailIssue(null)}
          onChanged={async () => {
            await onChanged();
            setDetailIssue(null);
          }}
        />
      )}

      {editor && (
        <MingManualIssueEditor
          editing={editor.mode === 'edit' ? editor.issue : null}
          characters={characters}
          salvageRaw={salvageRaw}
          scenarioId={scenarioId}
          onClose={() => setEditor(null)}
          onSaved={async () => {
            setEditor(null);
            await onChanged();
          }}
        />
      )}
    </>
  );
};
