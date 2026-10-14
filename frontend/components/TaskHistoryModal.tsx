'use client';

import React from 'react';
import { createPortal } from 'react-dom';

export type TaskHistoryRow = Record<string, unknown>;

function formatResult(r: unknown): string {
  const s = String(r ?? '').toLowerCase();
  if (s === 'completed') return '已完成';
  if (s === 'failed') return '未达成';
  if (s === 'active') return '进行中';
  return s ? String(r) : '—';
}

type Props = {
  open: boolean;
  loading: boolean;
  rows: TaskHistoryRow[];
  onClose: () => void;
};

export const TaskHistoryModal: React.FC<Props> = ({ open, loading, rows, onClose }) => {
  if (!open || typeof document === 'undefined') return null;

  const displayRows = [...rows].reverse();

  // Portal to body: parent TaskPanel uses transform, which makes fixed children
  // position relative to that panel instead of the viewport (modal clipped by layout).
  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 20000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.55)',
        padding: 'max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left))',
        boxSizing: 'border-box',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(520px, 100%)',
          maxHeight: 'min(85vh, calc(100vh - 48px))',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          borderRadius: 12,
          border: '1px solid rgba(255,215,0,0.45)',
          background: 'linear-gradient(165deg, rgba(18,12,10,0.98), rgba(8,6,6,0.98))',
          boxShadow: '0 12px 40px rgba(0,0,0,0.65)',
          color: '#f0ebe4',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 14px',
            borderBottom: '1px solid rgba(255,215,0,0.2)',
          }}
        >
          <span style={{ fontWeight: 700, color: '#ffd700', fontSize: 15 }}>历史任务（已结算）</span>
          <button
            type="button"
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              color: '#c8c0b8',
              cursor: 'pointer',
              fontSize: 18,
              lineHeight: 1,
              padding: 4,
            }}
          >
            ×
          </button>
        </div>
        <div
          style={{
            padding: '10px 14px',
            overflowY: 'auto',
            flex: 1,
            minHeight: 0,
            WebkitOverflowScrolling: 'touch',
            fontSize: 13,
          }}
        >
          {loading ? (
            <div style={{ color: '#a09888' }}>加载中…</div>
          ) : displayRows.length === 0 ? (
            <div style={{ color: '#a09888' }}>暂无已结算任务记录（完成任务并进入下一季后会在此汇总）。</div>
          ) : (
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 10 }}>
              {displayRows.map((row, idx) => {
                const title = String(row.title ?? row.template_id ?? '未命名');
                const aq = row.assigned_quarter;
                const rq = row.resolved_quarter;
                const result = formatResult(row.result);
                const key = `${String(row.task_id ?? idx)}-${String(rq ?? '')}`;
                return (
                  <li
                    key={key}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: '1px solid rgba(255,215,0,0.15)',
                      background: 'rgba(0,0,0,0.35)',
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 6, color: '#ffebc8' }}>{title}</div>
                    <div style={{ fontSize: 12, color: '#bfb8a8', lineHeight: 1.6 }}>
                      <div>
                        指派季：{aq != null ? String(aq) : '—'}　→　结算季：{rq != null ? String(rq) : '—'}
                      </div>
                      <div style={{ marginTop: 4 }}>
                        结果：<span style={{ color: result === '已完成' ? '#7CFC98' : '#ffb090' }}>{result}</span>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
};
