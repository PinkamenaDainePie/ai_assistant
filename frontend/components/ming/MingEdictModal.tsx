'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { MingFullscreenModal } from './MingFullscreenModal';
import { MingStructuredDirectiveEditor } from './MingStructuredDirectiveEditor';
import { formatMingReportText } from '../../game/ming/mingReportFormat';
import type {
  MingDirective,
  MingGameState,
  MingStructuredDirective,
  MingStructuredDirectiveTemplate,
  MingTurnPhase,
} from '../../game/ming/mingTurnPhase';
import type { SalvageGameState } from '../../lib/mingSalvageAdapter';
import type { ScenarioId } from '../../game/scenarios';
import { mingFetchStructuredDirectiveTemplates } from '../../lib/mingApi';
import { mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Props = {
  state: MingGameState;
  phase: MingTurnPhase;
  decreeText: string;
  lastReport: string;
  settleStage: string;
  settleNarrative: string;
  loading: boolean;
  salvageRaw?: SalvageGameState;
  scenarioId?: ScenarioId;
  onClose: () => void;
  onDecreeChange: (text: string) => void;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
  onConfirmAll: () => void;
  onDelete: (id: number) => void;
  onPatch: (id: number, text: string) => void;
  onAddDraft: (text: string) => void;
  onDeleteStructured: (id: number) => void;
  onSaveStructured: (
    editing: MingStructuredDirective | null,
    templateId: string,
    fields: Record<string, string>,
  ) => Promise<void>;
  onComposeDecree: () => void;
  onSaveDecree: () => void;
  onRewriteDecree: () => void;
  onIssue: () => void;
  onGoToCourtChat?: () => void;
};

export const MingEdictModal: React.FC<Props> = ({
  state,
  phase,
  decreeText,
  lastReport,
  settleStage,
  settleNarrative,
  loading,
  salvageRaw,
  scenarioId,
  onClose,
  onDecreeChange,
  onConfirm,
  onReject,
  onConfirmAll,
  onDelete,
  onPatch,
  onAddDraft,
  onDeleteStructured,
  onSaveStructured,
  onComposeDecree,
  onSaveDecree,
  onRewriteDecree,
  onIssue,
  onGoToCourtChat,
}) => {
  const [draftInput, setDraftInput] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [templates, setTemplates] = useState<MingStructuredDirectiveTemplate[]>([]);
  const [structuredEditor, setStructuredEditor] = useState<MingStructuredDirective | null | undefined>(undefined);

  useEffect(() => {
    void mingFetchStructuredDirectiveTemplates().then(({ templates: t }) => setTemplates(t || []));
  }, []);

  const pending = useMemo(() => state.directives.filter((d) => d.status === 'pending'), [state.directives]);
  const drafts = useMemo(() => state.directives.filter((d) => d.status === 'draft'), [state.directives]);
  const structured = state.structured_directives || [];
  const hasPending = pending.length > 0;
  const hasDrafts = drafts.length > 0;
  const hasStructured = structured.length > 0;

  const uiPhase: 'desk' | 'review' | 'issued' = lastReport && phase === 'issued' ? 'issued' : decreeText ? 'review' : 'desk';

  const openEdit = (d: MingDirective) => {
    setEditingId(d.id);
    setEditText(d.text);
  };

  const saveEdit = () => {
    if (editingId != null && editText.trim()) {
      onPatch(editingId, editText.trim());
      setEditingId(null);
    }
  };

  const footer = (
    <div
      style={{
        display: 'flex',
        gap: 8,
        flexWrap: 'wrap',
        alignItems: 'center',
        marginTop: 16,
        paddingTop: 12,
        borderTop: '1px solid rgba(255,215,0,0.15)',
      }}
    >
      {hasPending && (
        <small style={{ color: '#ffb74d', fontSize: 12 }}>
          尚有 {pending.length} 道大臣拟旨待朱批。
        </small>
      )}
      {onGoToCourtChat && uiPhase === 'desk' && (
        <button type="button" style={mingOutlineBtn} disabled={loading} onClick={onGoToCourtChat}>
          去廷议
        </button>
      )}
      {uiPhase === 'desk' && (
        <button
          type="button"
          style={mingPrimaryBtn}
          disabled={loading || hasPending}
          onClick={() => {
            if (hasDrafts) onComposeDecree();
            else onIssue();
          }}
        >
          {hasDrafts ? '拟诏 →' : hasStructured ? '核销指令 →' : '结束本月'}
        </button>
      )}
      {uiPhase === 'review' && (
        <>
          <button type="button" style={mingOutlineBtn} disabled={loading} onClick={onRewriteDecree}>
            重写拟旨
          </button>
          <button type="button" style={mingOutlineBtn} disabled={loading} onClick={onSaveDecree}>
            存改诏书
          </button>
          <button type="button" style={mingPrimaryBtn} disabled={loading} onClick={onIssue}>
            盖玺颁布
          </button>
        </>
      )}
      {uiPhase === 'issued' && phase === 'issued' && (
        <button type="button" style={mingPrimaryBtn} disabled={loading} onClick={onIssue}>
          进入下一月
        </button>
      )}
    </div>
  );

  return (
    <>
      <MingFullscreenModal
        wide
        title="拟诏 · 御案理政"
        subtitle={`${state.turn.label} · 待核定 ${state.pending_count} · 固定指令 ${structured.length}`}
        onClose={onClose}
      >
        {loading && settleStage && (
          <div style={{ fontSize: 12, color: '#b8a888', marginBottom: 8 }}>{settleStage}</div>
        )}
        {settleNarrative && (
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 11,
              color: '#999',
              marginBottom: 12,
              maxHeight: 80,
              overflow: 'auto',
            }}
          >
            {settleNarrative}
          </pre>
        )}

        {uiPhase === 'issued' ? (
          <div>
            {decreeText && (
              <section style={{ marginBottom: 16 }}>
                <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>本月诏书</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7, color: '#ddd' }}>
                  {decreeText}
                </pre>
              </section>
            )}
            {(lastReport || state.last_report) && (
              <section>
                <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>月末奏章</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7, color: '#ddd' }}>
                  {formatMingReportText(lastReport || state.last_report)}
                </pre>
              </section>
            )}
            {footer}
          </div>
        ) : uiPhase === 'review' ? (
          <div>
            <textarea
              value={decreeText}
              onChange={(e) => onDecreeChange(e.target.value)}
              rows={12}
              disabled={loading}
              style={{
                width: '100%',
                padding: 12,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(255,215,0,0.25)',
                borderRadius: 8,
                color: '#f5f5f5',
                fontSize: 14,
                lineHeight: 1.7,
                fontFamily: 'inherit',
              }}
            />
            {footer}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <section>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h3 style={{ fontSize: 13, color: '#ffd700', margin: 0 }}>
                  本月指令 · {state.directives.length + structured.length} 道
                </h3>
                {pending.length > 1 && (
                  <button type="button" style={mingOutlineBtn} disabled={loading} onClick={onConfirmAll}>
                    全部准奏
                  </button>
                )}
              </div>
              <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                {structured.map((sd) => (
                  <div
                    key={`s-${sd.id}`}
                    style={{
                      marginBottom: 8,
                      padding: 8,
                      borderRadius: 6,
                      border: '1px solid rgba(255,215,0,0.2)',
                      background: 'rgba(0,0,0,0.25)',
                      fontSize: 12,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <b style={{ color: '#ffe7a3' }}>令#{sd.id}</b>
                      <span style={{ color: '#888' }}>{sd.category}</span>
                    </div>
                    <p style={{ margin: '6px 0', color: '#ccc', lineHeight: 1.5 }}>{sd.compiled_text}</p>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button type="button" style={mingOutlineBtn} onClick={() => setStructuredEditor(sd)}>改</button>
                      <button type="button" style={mingOutlineBtn} onClick={() => onDeleteStructured(sd.id)}>删</button>
                    </div>
                  </div>
                ))}
                {state.directives.map((d) => (
                  <div
                    key={d.id}
                    style={{
                      marginBottom: 8,
                      padding: 8,
                      borderRadius: 6,
                      border: d.status === 'pending' ? '1px solid rgba(255,152,0,0.4)' : '1px solid rgba(255,215,0,0.15)',
                      background: 'rgba(0,0,0,0.25)',
                      fontSize: 12,
                    }}
                  >
                    {editingId === d.id ? (
                      <>
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={3}
                          style={{
                            width: '100%',
                            marginBottom: 6,
                            padding: 6,
                            background: 'rgba(0,0,0,0.4)',
                            border: '1px solid rgba(255,215,0,0.2)',
                            color: '#f5f5f5',
                            borderRadius: 4,
                            fontSize: 12,
                          }}
                        />
                        <button type="button" style={mingOutlineBtn} onClick={saveEdit}>保存</button>
                        <button type="button" style={mingOutlineBtn} onClick={() => setEditingId(null)}>取消</button>
                      </>
                    ) : (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <b>#{d.id}</b>
                          <span style={{ color: d.status === 'pending' ? '#ffb74d' : '#888' }}>{d.status}</span>
                        </div>
                        <p style={{ margin: '6px 0', color: '#ccc', lineHeight: 1.5 }}>{d.text}</p>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {d.status === 'pending' ? (
                            <>
                              <button type="button" style={mingOutlineBtn} onClick={() => onConfirm(d.id)}>准</button>
                              <button type="button" style={mingOutlineBtn} onClick={() => onReject(d.id)}>驳</button>
                            </>
                          ) : d.status === 'draft' ? (
                            <>
                              <button type="button" style={mingOutlineBtn} onClick={() => openEdit(d)}>改</button>
                              <button type="button" style={mingOutlineBtn} onClick={() => onDelete(d.id)}>删</button>
                            </>
                          ) : null}
                        </div>
                      </>
                    )}
                  </div>
                ))}
                {!state.directives.length && !structured.length && (
                  <p style={{ color: '#888', fontSize: 12, lineHeight: 1.6 }}>
                    无新指令。本月可直接结算，由各局势承办人照前旨推进。
                  </p>
                )}
              </div>
            </section>
            <section>
              <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>固定指令</h3>
              <button
                type="button"
                style={{ ...mingOutlineBtn, marginBottom: 12, width: '100%' }}
                disabled={loading || !templates.length}
                onClick={() => setStructuredEditor(null)}
              >
                + 新增固定指令
              </button>
              <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>御笔自拟</h3>
              <textarea
                value={draftInput}
                onChange={(e) => setDraftInput(e.target.value)}
                placeholder="御笔自拟草案…"
                rows={4}
                style={{
                  width: '100%',
                  padding: 8,
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid rgba(255,215,0,0.2)',
                  color: '#f5f5f5',
                  borderRadius: 6,
                  fontSize: 13,
                  marginBottom: 8,
                }}
              />
              <button
                type="button"
                style={mingOutlineBtn}
                disabled={loading || !draftInput.trim()}
                onClick={() => {
                  onAddDraft(draftInput.trim());
                  setDraftInput('');
                }}
              >
                新增草案
              </button>
            </section>
          </div>
        )}
        {uiPhase === 'desk' && footer}
      </MingFullscreenModal>

      {structuredEditor !== undefined && (
        <MingStructuredDirectiveEditor
          editing={structuredEditor}
          templates={templates}
          salvageRaw={salvageRaw}
          scenarioId={scenarioId}
          onClose={() => setStructuredEditor(undefined)}
          onSaved={async (editing, templateId, fields) => {
            await onSaveStructured(editing, templateId, fields);
            setStructuredEditor(undefined);
          }}
        />
      )}
    </>
  );
};
