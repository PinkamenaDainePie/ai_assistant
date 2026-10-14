'use client';

import React, { useEffect, useState } from 'react';
import type { MingSalvageIssue } from '../../game/ming/mingTurnPhase';
import type { Character } from '../../game/types';
import { mingSetIssueAuthorization, mingUpdateIssueAssignee } from '../../lib/mingApi';
import { MingFullscreenModal } from './MingFullscreenModal';
import { mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Props = {
  issue: MingSalvageIssue;
  characters: Character[];
  onClose: () => void;
  onChanged: () => void | Promise<void>;
};

export const MingSituationDetailModal: React.FC<Props> = ({
  issue,
  characters,
  onClose,
  onChanged,
}) => {
  const [assignee, setAssignee] = useState(issue.assignee || '');
  const [assigneeSaving, setAssigneeSaving] = useState(false);
  const [assigneeErr, setAssigneeErr] = useState('');

  const [budgetAdd, setBudgetAdd] = useState(0);
  const [budgetSource, setBudgetSource] = useState(issue.budget_source || '国库');
  const [deathAuthority, setDeathAuthority] = useState(Boolean(issue.death_authority));
  const [authSaving, setAuthSaving] = useState(false);
  const [authErr, setAuthErr] = useState('');

  const ministerNames = characters
    .filter((c) => c.id !== 'emperor')
    .map((c) => c.name)
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));

  useEffect(() => {
    setAssignee(issue.assignee || '');
    setBudgetSource(issue.budget_source || '国库');
    setDeathAuthority(Boolean(issue.death_authority));
    setBudgetAdd(0);
  }, [issue]);

  const saveAssignee = async () => {
    setAssigneeSaving(true);
    setAssigneeErr('');
    try {
      await mingUpdateIssueAssignee(issue.id, assignee.trim());
      await onChanged();
    } catch (e) {
      setAssigneeErr(e instanceof Error ? e.message : String(e));
    } finally {
      setAssigneeSaving(false);
    }
  };

  const saveAuth = async () => {
    setAuthSaving(true);
    setAuthErr('');
    try {
      await mingSetIssueAuthorization(issue.id, {
        budget_add: budgetAdd,
        budget_source: budgetSource,
        death_authority: deathAuthority,
      });
      setBudgetAdd(0);
      await onChanged();
    } catch (e) {
      setAuthErr(e instanceof Error ? e.message : String(e));
    } finally {
      setAuthSaving(false);
    }
  };

  const pool = Number(issue.budget_pool || 0);
  const assigneeChanged = assignee !== (issue.assignee || '');
  const authChanged =
    budgetAdd > 0 ||
    budgetSource !== (issue.budget_source || '国库') ||
    deathAuthority !== Boolean(issue.death_authority);

  return (
    <MingFullscreenModal
      title={`局势 #${issue.id}`}
      subtitle={issue.title}
      onClose={onClose}
    >
      <div style={{ marginBottom: 12 }}>
        <div style={{ height: 8, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${issue.bar_value}%`,
              background: issue.bar_value >= 65 ? '#4caf50' : issue.bar_value <= 35 ? '#e57373' : '#ffb74d',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#888', marginTop: 4 }}>
          <span>{issue.bar_bad_meaning}</span>
          <span>{issue.bar_value}</span>
          <span>{issue.bar_good_meaning}</span>
        </div>
      </div>

      {issue.stage_text && (
        <p style={{ fontSize: 13, lineHeight: 1.6, color: '#ccc', marginBottom: 12 }}>{issue.stage_text}</p>
      )}

      {issue.goal && (
        <section style={{ marginBottom: 16, padding: 10, borderRadius: 8, background: 'rgba(0,0,0,0.25)' }}>
          <div style={{ fontSize: 12, color: '#ffd700', marginBottom: 4 }}>皇帝目标</div>
          <p style={{ fontSize: 13, color: '#bbb', lineHeight: 1.6, margin: 0 }}>{issue.goal}</p>
        </section>
      )}

      {(issue.resolve_condition || issue.fail_condition || issue.ongoing_text) && (
        <section style={{ marginBottom: 16, fontSize: 12, lineHeight: 1.6, color: '#aaa' }}>
          {issue.ongoing_text && <p><b style={{ color: '#ccc' }}>当前影响：</b>{issue.ongoing_text}</p>}
          {issue.resolve_condition && <p><b style={{ color: '#4caf50' }}>达成：</b>{issue.resolve_condition}</p>}
          {issue.fail_condition && <p><b style={{ color: '#e57373' }}>失败：</b>{issue.fail_condition}</p>}
          {issue.inertia != null && <p><b style={{ color: '#ccc' }}>月度惯性：</b>{issue.inertia}</p>}
        </section>
      )}

      <section style={{ marginBottom: 16, padding: 12, borderRadius: 8, border: '1px solid rgba(255,215,0,0.15)' }}>
        <div style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>承办人</div>
        <select
          value={assignee}
          onChange={(e) => setAssignee(e.target.value)}
          disabled={assigneeSaving}
          style={{
            width: '100%',
            marginBottom: 8,
            padding: 8,
            background: 'rgba(0,0,0,0.35)',
            border: '1px solid rgba(255,215,0,0.2)',
            color: '#f5f5f5',
            borderRadius: 6,
          }}
        >
          <option value="">未指定</option>
          {ministerNames.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
        <button
          type="button"
          style={mingOutlineBtn}
          disabled={assigneeSaving || !assigneeChanged}
          onClick={() => void saveAssignee()}
        >
          {assigneeSaving ? '保存中…' : '改派承办人'}
        </button>
        {assigneeErr && <p style={{ color: '#e57373', fontSize: 12, marginTop: 6 }}>{assigneeErr}</p>}
      </section>

      <section style={{ padding: 12, borderRadius: 8, border: '1px solid rgba(255,215,0,0.15)' }}>
        <div style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>
          承办人授权
          <span style={{ fontSize: 11, color: '#888', marginLeft: 6 }}>批专款后可逐月自理</span>
        </div>
        <p style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
          现有专款：{pool > 0 ? `${pool} 万两（${issue.budget_source || '—'}）` : '未拨'}
        </p>
        <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>追加拨款（万两）</label>
        <input
          type="number"
          min={0}
          value={budgetAdd}
          onChange={(e) => setBudgetAdd(Math.max(0, Number(e.target.value) || 0))}
          disabled={authSaving}
          style={{
            width: '100%',
            marginBottom: 8,
            padding: 8,
            background: 'rgba(0,0,0,0.35)',
            border: '1px solid rgba(255,215,0,0.2)',
            color: '#f5f5f5',
            borderRadius: 6,
          }}
        />
        <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>出库</label>
        <select
          value={budgetSource}
          onChange={(e) => setBudgetSource(e.target.value)}
          disabled={authSaving}
          style={{
            width: '100%',
            marginBottom: 8,
            padding: 8,
            background: 'rgba(0,0,0,0.35)',
            border: '1px solid rgba(255,215,0,0.2)',
            color: '#f5f5f5',
            borderRadius: 6,
          }}
        >
          <option value="国库">国库</option>
          <option value="内库">内库</option>
        </select>
        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#ccc', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={deathAuthority}
            onChange={(e) => setDeathAuthority(e.target.checked)}
            disabled={authSaving}
          />
          <span>赐专断之权（可不请旨拿问阻挠者；不得擅动在朝大臣）</span>
        </label>
        <button
          type="button"
          style={mingPrimaryBtn}
          disabled={authSaving || !authChanged}
          onClick={() => void saveAuth()}
        >
          {authSaving ? '授权中…' : '确认授权'}
        </button>
        {authErr && <p style={{ color: '#e57373', fontSize: 12, marginTop: 6 }}>{authErr}</p>}
      </section>
    </MingFullscreenModal>
  );
};
