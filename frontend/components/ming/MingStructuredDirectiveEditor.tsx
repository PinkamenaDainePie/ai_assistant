'use client';

import React, { useEffect, useState } from 'react';
import type {
  MingStructuredDirective,
  MingStructuredDirectiveFieldSpec,
  MingStructuredDirectiveTemplate,
} from '../../game/ming/mingTurnPhase';
import type { SalvageGameState } from '../../lib/mingSalvageAdapter';
import type { ScenarioId } from '../../game/scenarios';
import {
  displayFiscalLabel,
  isRegionalFiscalKey,
  resolveTaxTypeOptions,
} from '../../game/ming/fiscalDisplay';
import { mingCloseBtn, mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Props = {
  editing: MingStructuredDirective | null;
  templates: MingStructuredDirectiveTemplate[];
  salvageRaw?: SalvageGameState;
  scenarioId?: ScenarioId;
  onClose: () => void;
  onSaved: (
    editing: MingStructuredDirective | null,
    templateId: string,
    fields: Record<string, string>,
  ) => Promise<void>;
};

function resolveOptions(
  field: MingStructuredDirectiveFieldSpec,
  salvageRaw?: SalvageGameState,
): string[] {
  if (field.options?.length) return field.options;
  const src = field.option_source;
  if (src === 'taxes') return [...resolveTaxTypeOptions()];
  if (!src || !salvageRaw) return [];
  if (src === 'armies') return (salvageRaw.armies || []).map((a) => String(a.name || a.id || '')).filter(Boolean);
  if (src === 'regions' || src === 'regions_or_all') {
    const regions = (salvageRaw.regions || []).map((r) => String(r.name || r.id || '')).filter(Boolean);
    return src === 'regions_or_all' ? ['全国', ...regions] : regions;
  }
  if (src === 'departments') return (salvageRaw.departments || []).map((d) => String(d.name || '')).filter(Boolean);
  if (src === 'buildings') return (salvageRaw.buildings || []).map((b) => String(b.name || b.id || '')).filter(Boolean);
  if (src === 'weapons') return (salvageRaw.arms_stock || []).map((w) => String(w.name || w.id || '')).filter(Boolean);
  if (src === 'people') return (salvageRaw.ministers || []).map((m) => String(m.name || '')).filter(Boolean);
  return [];
}

export const MingStructuredDirectiveEditor: React.FC<Props> = ({
  editing,
  templates,
  salvageRaw,
  scenarioId,
  onClose,
  onSaved,
}) => {
  const initialTemplateId = editing?.template_id || templates[0]?.id || '';
  const [templateId, setTemplateId] = useState(initialTemplateId);
  const [fields, setFields] = useState<Record<string, string>>(() => editing?.fields || {});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const template = templates.find((t) => t.id === templateId) || templates[0] || null;

  const isFieldRequired = (field: MingStructuredDirectiveFieldSpec) => {
    if (field.required) return true;
    const cond = field.required_when;
    if (!cond) return false;
    return (cond.values || []).includes(fields[cond.field] || '');
  };

  const isFieldVisible = (field: MingStructuredDirectiveFieldSpec) => {
    if (template?.id === 'tax_reform' && field.key === 'scope') {
      return isRegionalFiscalKey(fields.tax_type || '');
    }
    return true;
  };

  useEffect(() => {
    if (!template) return;
    setFields((current) => {
      const next: Record<string, string> = {};
      for (const field of template.fields || []) {
        next[field.key] = current[field.key] || '';
      }
      return next;
    });
  }, [template?.id]);

  const save = async () => {
    if (!template) {
      setErr('没有可用模板');
      return;
    }
    for (const field of template.fields || []) {
      if (!isFieldVisible(field)) continue;
      if (isFieldRequired(field) && !String(fields[field.key] || '').trim()) {
        setErr(`字段「${field.label}」不能为空`);
        return;
      }
    }
    setBusy(true);
    setErr('');
    try {
      await onSaved(editing, template.id, fields);
    } catch (e) {
      setErr(e instanceof Error ? e.message : '保存失败');
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2600,
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
          width: 'min(520px, 96vw)',
          maxHeight: '85vh',
          overflow: 'auto',
          borderRadius: 10,
          border: '1px solid rgba(255,215,0,0.5)',
          background: 'linear-gradient(180deg, #1b1010, #0d0b10)',
          padding: 16,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <b style={{ color: '#ffe7a3' }}>{editing ? '编辑固定指令' : '新建固定指令'}</b>
          <button type="button" onClick={onClose} style={mingCloseBtn}>×</button>
        </div>
        {!templates.length ? (
          <p style={{ color: '#888', fontSize: 13 }}>无可用模板。</p>
        ) : (
          <>
            <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>指令类型</label>
            <select
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              style={{
                width: '100%',
                marginBottom: 12,
                padding: 8,
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,215,0,0.25)',
                color: '#f5f5f5',
                borderRadius: 6,
              }}
            >
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.label}（{t.category}）</option>
              ))}
            </select>
            {template?.settlement_hint && (
              <p style={{ fontSize: 11, color: '#888', marginBottom: 12, lineHeight: 1.5 }}>
                {template.settlement_hint}
              </p>
            )}
            {(template?.fields || []).filter(isFieldVisible).map((field) => {
              const options = resolveOptions(field, salvageRaw);
              return (
                <div key={field.key} style={{ marginBottom: 10 }}>
                  <label style={{ display: 'block', fontSize: 12, color: '#ccc', marginBottom: 4 }}>
                    {field.label}
                    {isFieldRequired(field) ? ' *' : ''}
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      value={fields[field.key] || ''}
                      onChange={(e) => setFields((f) => ({ ...f, [field.key]: e.target.value }))}
                      placeholder={field.placeholder || ''}
                      rows={3}
                      style={{
                        width: '100%',
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                        fontSize: 13,
                      }}
                    />
                  ) : field.type === 'select' && options.length > 0 ? (
                    <select
                      value={fields[field.key] || ''}
                      onChange={(e) => setFields((f) => ({ ...f, [field.key]: e.target.value }))}
                      style={{
                        width: '100%',
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                      }}
                    >
                      <option value="">请选择</option>
                      {options.map((opt) => (
                        <option key={opt} value={opt}>
                          {displayFiscalLabel(opt, scenarioId)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.type === 'number' ? 'number' : 'text'}
                      value={fields[field.key] || ''}
                      onChange={(e) => setFields((f) => ({ ...f, [field.key]: e.target.value }))}
                      placeholder={field.placeholder || (field.option_source ? '输入名称' : '')}
                      style={{
                        width: '100%',
                        padding: 8,
                        background: 'rgba(0,0,0,0.35)',
                        border: '1px solid rgba(255,215,0,0.2)',
                        color: '#f5f5f5',
                        borderRadius: 6,
                        fontSize: 13,
                      }}
                    />
                  )}
                </div>
              );
            })}
            {err && <p style={{ color: '#e57373', fontSize: 12, marginBottom: 8 }}>{err}</p>}
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button type="button" style={mingPrimaryBtn} disabled={busy} onClick={() => void save()}>
                {busy ? '保存中…' : '保存'}
              </button>
              <button type="button" style={mingOutlineBtn} onClick={onClose}>取消</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
