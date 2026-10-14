'use client';

import React, { useState } from 'react';
import type { MingDirective } from '../../game/ming/mingTurnPhase';
import {
  mingCard,
  mingCloseBtn,
  mingDraggableBottomPanelStyle,
  mingOutlineBtn,
  mingPrimaryBtn,
} from '../../game/ming/mingUiStyles';
import { useDraggablePanel } from '../../hooks/useDraggablePanel';

type Props = {
  open: boolean;
  directives: MingDirective[];
  pendingCount: number;
  phase: string;
  loading: boolean;
  onClose: () => void;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
  onAddDraft: (text: string) => void;
  onComposeDecree: () => void;
};

export const MingDirectivePanel: React.FC<Props> = ({
  open,
  directives,
  pendingCount,
  phase,
  loading,
  onClose,
  onConfirm,
  onReject,
  onAddDraft,
  onComposeDecree,
}) => {
  const [draftInput, setDraftInput] = useState('');
  const { panelRef, dragHandleProps, pos } = useDraggablePanel(`directive-${open}`);

  if (!open) return null;

  const pending = directives.filter((d) => d.status === 'pending');
  const drafts = directives.filter((d) => d.status === 'draft');

  return (
    <div
      ref={panelRef as React.RefObject<HTMLDivElement>}
      className="panel-enter-up ming-scroll"
      style={mingDraggableBottomPanelStyle(pos, 102, { maxHeight: '38vh', overflowY: 'auto', zIndex: 126 })}
    >
      <div
        {...dragHandleProps}
        style={{
          ...dragHandleProps.style,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
          gap: 8,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, color: '#ffd700', fontSize: 14 }}>拟旨 · 草案</div>
          <div style={{ color: '#999', fontSize: 12, marginTop: 2 }}>
            待核定 {pendingCount} 条 · 已 draft {drafts.length} 条
          </div>
        </div>
        <button type="button" onClick={onClose} title="关闭" style={mingCloseBtn}>
          ×
        </button>
      </div>

      {pending.map((d) => (
        <div key={d.id} style={mingCard}>
          <div style={{ color: '#ffb347', fontSize: 11 }}>{d.actor || '大臣'} · 待核定</div>
          <div style={{ margin: '6px 0', lineHeight: 1.5 }}>{d.text}</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              style={{ ...mingPrimaryBtn, flex: 1, padding: '4px 8px', fontSize: 12 }}
              disabled={loading}
              onClick={() => onConfirm(d.id)}
            >
              核定
            </button>
            <button
              type="button"
              style={{
                ...mingOutlineBtn,
                flex: 1,
                padding: '4px 8px',
                fontSize: 12,
                border: '1px solid rgba(255,100,100,0.5)',
                color: '#faa',
              }}
              disabled={loading}
              onClick={() => onReject(d.id)}
            >
              驳回
            </button>
          </div>
        </div>
      ))}

      {drafts.map((d) => (
        <div key={d.id} style={mingCard}>
          <div style={{ color: '#8fd694', fontSize: 11 }}>草案 #{d.id}</div>
          <div style={{ margin: '6px 0', lineHeight: 1.5 }}>{d.text}</div>
        </div>
      ))}

      {phase !== 'issued' && phase !== 'awaiting_decision' && pendingCount === 0 && (
        <>
          <textarea
            value={draftInput}
            onChange={(e) => setDraftInput(e.target.value)}
            placeholder="皇帝亲笔添加草案…"
            rows={3}
            className="ming-scroll edict-composer-textarea"
            style={{
              width: '100%',
              marginTop: 4,
              background: 'rgba(0,0,0,0.35)',
              border: '1px solid rgba(255,215,0,0.2)',
              borderRadius: 6,
              color: '#f5f5f5',
              padding: 8,
              resize: 'vertical',
            }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              style={mingOutlineBtn}
              disabled={loading || !draftInput.trim()}
              onClick={() => {
                onAddDraft(draftInput);
                setDraftInput('');
              }}
            >
              添加草案
            </button>
            <button
              type="button"
              style={mingPrimaryBtn}
              disabled={loading || drafts.length === 0}
              onClick={onComposeDecree}
            >
              合成诏书
            </button>
          </div>
        </>
      )}
    </div>
  );
};
