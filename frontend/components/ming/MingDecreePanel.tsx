'use client';

import React from 'react';
import {
  mingCloseBtn,
  mingDraggableBottomPanelStyle,
  mingOutlineBtn,
  mingPrimaryBtn,
} from '../../game/ming/mingUiStyles';
import { useDraggablePanel } from '../../hooks/useDraggablePanel';

type Props = {
  open: boolean;
  bottom?: number;
  decreeText: string;
  lastReport: string;
  settleStage: string;
  settleNarrative: string;
  loading: boolean;
  phase: string;
  onClose: () => void;
  onDecreeChange: (text: string) => void;
  onSaveDecree: () => void;
  onIssue: () => void;
  onOpenSummon: () => void;
};

export const MingDecreePanel: React.FC<Props> = ({
  open,
  bottom = 102,
  decreeText,
  lastReport,
  settleStage,
  settleNarrative,
  loading,
  phase,
  onClose,
  onDecreeChange,
  onSaveDecree,
  onIssue,
  onOpenSummon,
}) => {
  const { panelRef, dragHandleProps, pos } = useDraggablePanel(`decree-${open}-${bottom}`);

  if (!open) return null;

  return (
    <div
      ref={panelRef as React.RefObject<HTMLDivElement>}
      className="panel-enter-up"
      style={mingDraggableBottomPanelStyle(pos, bottom, { maxWidth: 640, zIndex: 127 })}
    >
      <div
        {...dragHandleProps}
        style={{
          ...dragHandleProps.style,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <div style={{ color: '#ffd700', fontWeight: 700, fontSize: 14 }}>诏书 · 邸报</div>
        <button type="button" onClick={onClose} title="关闭" style={mingCloseBtn}>
          ×
        </button>
      </div>

      {loading && settleStage && (
        <div style={{ fontSize: 12, color: '#b8a888', marginBottom: 6 }}>{settleStage}</div>
      )}
      {settleNarrative && (
        <pre
          className="ming-scroll"
          style={{
            whiteSpace: 'pre-wrap',
            fontSize: 12,
            color: '#c8c0a8',
            marginBottom: 8,
            maxHeight: 100,
            overflow: 'auto',
            lineHeight: 1.5,
          }}
        >
          {settleNarrative}
        </pre>
      )}

      <textarea
        value={decreeText}
        onChange={(e) => onDecreeChange(e.target.value)}
        placeholder="拟诏正文（核定 draft 后合成，或手书）"
        rows={5}
        disabled={phase === 'issued' || loading}
        className="ming-scroll edict-composer-textarea"
        style={{
          width: '100%',
          background: 'rgba(0,0,0,0.35)',
          border: '1px solid rgba(255,215,0,0.2)',
          borderRadius: 6,
          color: '#f5f5f5',
          padding: 8,
          fontSize: 13,
          lineHeight: 1.6,
          resize: 'vertical',
        }}
      />

      <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {phase === 'awaiting_decision' && (
          <span style={{ fontSize: 12, color: '#ffb74d' }}>待亲裁决策点，请先完成弹窗裁断。</span>
        )}
        {phase !== 'issued' && phase !== 'awaiting_decision' && (
          <>
            <button type="button" style={mingOutlineBtn} disabled={loading || !decreeText.trim()} onClick={onSaveDecree}>
              保存诏书
            </button>
            <button type="button" style={mingPrimaryBtn} disabled={loading} onClick={onIssue}>
              {loading ? '颁诏结算中…' : decreeText.trim() ? '颁诏（月末）' : '结束本月（无新诏）'}
            </button>
            <button type="button" style={mingOutlineBtn} disabled={loading} onClick={onOpenSummon}>
              回召见
            </button>
          </>
        )}
        {phase === 'issued' && (
          <button type="button" style={mingPrimaryBtn} disabled={loading} onClick={onIssue}>
            {loading ? '进入下月中…' : '进入下一月'}
          </button>
        )}
      </div>

      {lastReport && (
        <details style={{ marginTop: 10, fontSize: 12 }}>
          <summary style={{ cursor: 'pointer', color: '#d4af37' }}>上回合邸报</summary>
          <pre
            className="ming-scroll"
            style={{ whiteSpace: 'pre-wrap', color: '#aaa', marginTop: 6, lineHeight: 1.5, maxHeight: 160, overflow: 'auto' }}
          >
            {lastReport}
          </pre>
        </details>
      )}
    </div>
  );
};
