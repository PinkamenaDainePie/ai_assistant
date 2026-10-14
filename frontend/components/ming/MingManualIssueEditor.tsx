'use client';

import React, { useEffect, useState } from 'react';
import type { MingSalvageIssue } from '../../game/ming/mingTurnPhase';
import { getPlayerPowerId, type ScenarioId } from '../../game/scenarios';
import { salvageRegionDisplayName } from '../../lib/mingSalvageAdapter';
import type { Character } from '../../game/types';
import type { SalvageGameState } from '../../lib/mingSalvageAdapter';
import {
  mingCreateManualIssue,
  mingUpdateManualIssue,
} from '../../lib/mingApi';
import { mingCloseBtn, mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

const ISSUE_THEMES = ['工程', '科技', '政治', '军事', '民生', '经济', '文化', '其他'] as const;
const THEME_ENTITY: Record<string, 'building' | 'department' | 'technology' | ''> = {
  工程: 'building',
  科技: 'technology',
  政治: 'department',
  军事: '',
  民生: '',
  经济: '',
  文化: '',
  其他: '',
};
const BUILDING_CATEGORIES = ['民生', '财政', '军事', '科技', '交通', '内廷'] as const;

type Props = {
  editing: MingSalvageIssue | null;
  characters: Character[];
  salvageRaw?: SalvageGameState;
  scenarioId?: ScenarioId;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
};

export const MingManualIssueEditor: React.FC<Props> = ({
  editing,
  characters,
  salvageRaw,
  scenarioId = 'ming_wanli',
  onClose,
  onSaved,
}) => {
  const isSong = getPlayerPowerId(scenarioId) === 'song';
  const [title, setTitle] = useState(editing?.title || '');
  const [goal, setGoal] = useState(editing?.goal || '');
  const [assignee, setAssignee] = useState(editing?.assignee || '');
  const [category, setCategory] = useState<string>(editing?.tags?.[0] || '民生');
  const [regionId, setRegionId] = useState(salvageRaw?.regions?.[0]?.id || '');
  const [bldCategory, setBldCategory] = useState('民生');
  const [maintenance, setMaintenance] = useState(1);
  const [authorityScope, setAuthorityScope] = useState('');
  const [power, setPower] = useState(50);
  const [effectSummary, setEffectSummary] = useState('');
  const [presetMode, setPresetMode] = useState<'preset' | 'custom'>('preset');
  const [presetKey, setPresetKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const entityKind = THEME_ENTITY[category] || '';
  const presetPool =
    entityKind === 'technology'
      ? salvageRaw?.preset_trees?.technologies || []
      : entityKind === 'department'
        ? salvageRaw?.preset_trees?.departments || []
        : [];
  const selectablePresets = presetPool.filter((p) => !p.unlocked);
  const selectedPreset = presetPool.find((p) => p.key === presetKey) || null;

  useEffect(() => {
    if (entityKind !== 'technology' && entityKind !== 'department') {
      setPresetKey('');
      return;
    }
    const first = selectablePresets.find((p) => p.available)?.key || selectablePresets[0]?.key || '';
    setPresetKey((cur) => (cur && selectablePresets.some((p) => p.key === cur) ? cur : first));
  }, [entityKind, selectablePresets]);

  useEffect(() => {
    if (editing || presetMode !== 'preset' || !selectedPreset) return;
    setTitle(selectedPreset.name);
    setGoal(selectedPreset.effect_summary || selectedPreset.name);
    if (entityKind === 'department') {
      setAuthorityScope(selectedPreset.authority_scope || '');
      setPower(selectedPreset.power ?? 50);
    } else if (entityKind === 'technology') {
      setEffectSummary(selectedPreset.effect_summary || '');
    }
  }, [editing, presetMode, selectedPreset?.key, entityKind]);
  const ministerNames = characters
    .filter((c) => c.id !== 'emperor')
    .map((c) => c.name)
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));

  const save = async () => {
    if (!title.trim()) {
      setErr('名称不能为空');
      return;
    }
    setBusy(true);
    setErr('');
    try {
      if (editing) {
        await mingUpdateManualIssue(editing.id, {
          title: title.trim(),
          assignee: assignee.trim(),
        });
      } else {
        let entity: Record<string, unknown> | null = null;
        if (entityKind === 'building') {
          if (!regionId) {
            setErr(isSong ? '请为建筑选择路分' : '请为建筑选择省份');
            setBusy(false);
            return;
          }
          entity = {
            kind: 'building',
            name: title.trim(),
            region_id: regionId,
            category: bldCategory,
            maintenance,
          };
        } else if (entityKind === 'department') {
          if (presetMode === 'preset' && selectedPreset) {
            if (!selectedPreset.available) {
              setErr('前置衙门未设立');
              setBusy(false);
              return;
            }
            entity = { kind: 'department', preset_key: selectedPreset.key };
          } else {
            entity = {
              kind: 'department',
              name: title.trim(),
              authority_scope: authorityScope.trim(),
              power,
            };
          }
        } else if (entityKind === 'technology') {
          if (presetMode === 'preset' && selectedPreset) {
            if (!selectedPreset.available) {
              setErr('前置科技未完成');
              setBusy(false);
              return;
            }
            entity = { kind: 'technology', preset_key: selectedPreset.key };
          } else {
            entity = {
              kind: 'technology',
              name: title.trim(),
              effect_summary: effectSummary.trim(),
            };
          }
        }
        await mingCreateManualIssue({
          title: title.trim(),
          goal: goal.trim(),
          assignee: assignee.trim(),
          tags: [category],
          entity,
        });
      }
      await onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2500,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 'min(480px, 96vw)',
          maxHeight: '85vh',
          overflow: 'auto',
          borderRadius: 10,
          border: '1px solid rgba(255,215,0,0.5)',
          background: 'linear-gradient(180deg, #1b1010, #0d0b10)',
          padding: 16,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <b style={{ color: '#ffe7a3' }}>{editing ? '编辑手动局势' : '新建局势'}</b>
          <button type="button" onClick={onClose} style={mingCloseBtn}>×</button>
        </div>

        <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>名称</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{
            width: '100%',
            marginBottom: 10,
            padding: 8,
            background: 'rgba(0,0,0,0.35)',
            border: '1px solid rgba(255,215,0,0.2)',
            color: '#f5f5f5',
            borderRadius: 6,
          }}
        />

        {!editing && (
          <>
            <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>题材分类</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{
                width: '100%',
                marginBottom: 10,
                padding: 8,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(255,215,0,0.2)',
                color: '#f5f5f5',
                borderRadius: 6,
              }}
            >
              {ISSUE_THEMES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>

            {entityKind === 'building' && (
              <>
                <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>
                  {isSong ? '所在路分' : '所在省份'}
                </label>
                <select
                  value={regionId}
                  onChange={(e) => setRegionId(e.target.value)}
                  style={{
                    width: '100%',
                    marginBottom: 10,
                    padding: 8,
                    background: 'rgba(0,0,0,0.35)',
                    border: '1px solid rgba(255,215,0,0.2)',
                    color: '#f5f5f5',
                    borderRadius: 6,
                  }}
                >
                  {(salvageRaw?.regions || []).map((r) => (
                    <option key={r.id} value={r.id}>{salvageRegionDisplayName(r)}</option>
                  ))}
                </select>
                <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>建筑类别</label>
                <select
                  value={bldCategory}
                  onChange={(e) => setBldCategory(e.target.value)}
                  style={{
                    width: '100%',
                    marginBottom: 10,
                    padding: 8,
                    background: 'rgba(0,0,0,0.35)',
                    border: '1px solid rgba(255,215,0,0.2)',
                    color: '#f5f5f5',
                    borderRadius: 6,
                  }}
                >
                  {BUILDING_CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>月维护费（万两）</label>
                <input
                  type="number"
                  min={0}
                  value={maintenance}
                  onChange={(e) => setMaintenance(Math.max(0, Number(e.target.value) || 0))}
                  style={{
                    width: '100%',
                    marginBottom: 10,
                    padding: 8,
                    background: 'rgba(0,0,0,0.35)',
                    border: '1px solid rgba(255,215,0,0.2)',
                    color: '#f5f5f5',
                    borderRadius: 6,
                  }}
                />
              </>
            )}

            {entityKind === 'department' && (
              <>
                <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                  {(['preset', 'custom'] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setPresetMode(mode)}
                      style={{
                        flex: 1,
                        padding: '6px 8px',
                        borderRadius: 6,
                        border:
                          presetMode === mode
                            ? '1px solid rgba(255,215,0,0.75)'
                            : '1px solid rgba(255,255,255,0.15)',
                        background: presetMode === mode ? 'rgba(255,215,0,0.12)' : 'transparent',
                        color: presetMode === mode ? '#ffd700' : '#aaa',
                        cursor: 'pointer',
                        fontSize: 11,
                      }}
                    >
                      {mode === 'preset' ? '预设衙门' : '自定义'}
                    </button>
                  ))}
                </div>
                {presetMode === 'preset' && selectablePresets.length > 0 ? (
                  <select
                    value={presetKey}
                    onChange={(e) => setPresetKey(e.target.value)}
                    style={{
                      width: '100%',
                      marginBottom: 10,
                      padding: 8,
                      background: 'rgba(0,0,0,0.35)',
                      border: '1px solid rgba(255,215,0,0.2)',
                      color: '#f5f5f5',
                      borderRadius: 6,
                    }}
                  >
                    {selectablePresets.map((p) => (
                      <option key={p.key} value={p.key} disabled={!p.available}>
                        {p.name}{!p.available ? '（前置未满足）' : ''}
                      </option>
                    ))}
                  </select>
                ) : null}
                {presetMode === 'custom' ? (
                  <>
                    <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>职权范围</label>
                    <input
                      value={authorityScope}
                      onChange={(e) => setAuthorityScope(e.target.value)}
                      style={{
                        width: '100%',
                        marginBottom: 10,
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                      }}
                    />
                    <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>权力值</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={power}
                      onChange={(e) => setPower(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                      style={{
                        width: '100%',
                        marginBottom: 10,
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                      }}
                    />
                  </>
                ) : null}
              </>
            )}

            {entityKind === 'technology' && (
              <>
                <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                  {(['preset', 'custom'] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setPresetMode(mode)}
                      style={{
                        flex: 1,
                        padding: '6px 8px',
                        borderRadius: 6,
                        border:
                          presetMode === mode
                            ? '1px solid rgba(255,215,0,0.75)'
                            : '1px solid rgba(255,255,255,0.15)',
                        background: presetMode === mode ? 'rgba(255,215,0,0.12)' : 'transparent',
                        color: presetMode === mode ? '#ffd700' : '#aaa',
                        cursor: 'pointer',
                        fontSize: 11,
                      }}
                    >
                      {mode === 'preset' ? '预设科技' : '自定义'}
                    </button>
                  ))}
                </div>
                {presetMode === 'preset' && selectablePresets.length > 0 ? (
                  <select
                    value={presetKey}
                    onChange={(e) => setPresetKey(e.target.value)}
                    style={{
                      width: '100%',
                      marginBottom: 10,
                      padding: 8,
                      background: 'rgba(0,0,0,0.35)',
                      border: '1px solid rgba(255,215,0,0.2)',
                      color: '#f5f5f5',
                      borderRadius: 6,
                    }}
                  >
                    {selectablePresets.map((p) => (
                      <option key={p.key} value={p.key} disabled={!p.available}>
                        {p.name}{!p.available ? '（前置未满足）' : ''}
                      </option>
                    ))}
                  </select>
                ) : null}
                {presetMode === 'custom' ? (
                  <>
                    <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>效果摘要</label>
                    <input
                      value={effectSummary}
                      onChange={(e) => setEffectSummary(e.target.value)}
                      style={{
                        width: '100%',
                        marginBottom: 10,
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                      }}
                    />
                  </>
                ) : null}
              </>
            )}

            <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>目标（立项后锁定）</label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              rows={3}
              style={{
                width: '100%',
                marginBottom: 10,
                padding: 8,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(255,215,0,0.2)',
                color: '#f5f5f5',
                borderRadius: 6,
                fontSize: 13,
              }}
            />
          </>
        )}

        <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>承办人</label>
        <select
          value={assignee}
          onChange={(e) => setAssignee(e.target.value)}
          style={{
            width: '100%',
            marginBottom: 10,
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

        {err && <p style={{ color: '#e57373', fontSize: 12, marginBottom: 8 }}>{err}</p>}

        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" style={mingPrimaryBtn} disabled={busy} onClick={() => void save()}>
            {busy ? '保存中…' : '保存'}
          </button>
          <button type="button" style={mingOutlineBtn} onClick={onClose}>取消</button>
        </div>
      </div>
    </div>
  );
};
