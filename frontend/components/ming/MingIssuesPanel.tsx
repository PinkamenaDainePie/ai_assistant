'use client';

import React from 'react';
import type { MingSalvageIssue } from '../../game/ming/mingTurnPhase';
import { mingCloseBtn, mingOutlineBtn, mingPanelShell } from '../../game/ming/mingUiStyles';

type Props = {
  open: boolean;
  issues: MingSalvageIssue[];
  onClose: () => void;
  onOpenDrawer: () => void;
};

function barTone(value: number): string {
  if (value >= 65) return '#4caf50';
  if (value <= 35) return '#e57373';
  return '#ffb74d';
}

export const MingIssuesPanel: React.FC<Props> = ({ open, issues, onClose, onOpenDrawer }) => {
  if (!open) return null;

  const preview = issues.slice(0, 4);

  return (
    <div
      style={{
        ...mingPanelShell,
        left: 120,
        right: 'auto',
        width: 340,
        top: 112,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 15, color: '#ffe7a3' }}>在办局势</h3>
        <button type="button" onClick={onClose} style={mingCloseBtn} aria-label="关闭">
          ×
        </button>
      </div>

      {!issues.length ? (
        <p style={{ fontSize: 13, color: '#999', lineHeight: 1.6 }}>当前无在办局势。</p>
      ) : (
        <div style={{ overflowY: 'auto', flex: 1, paddingRight: 4 }}>
          {preview.map((issue) => (
            <div
              key={issue.id}
              style={{
                marginBottom: 12,
                padding: 10,
                borderRadius: 8,
                border: '1px solid rgba(255,215,0,0.2)',
                background: 'rgba(0,0,0,0.3)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  gap: 8,
                  marginBottom: 6,
                }}
              >
                <strong style={{ fontSize: 14, color: '#f5f5f5' }}>{issue.title}</strong>
                <span style={{ fontSize: 12, color: '#c9a227' }}>{issue.bar_value}</span>
              </div>
              <div
                style={{
                  height: 6,
                  borderRadius: 999,
                  background: 'rgba(255,255,255,0.08)',
                  overflow: 'hidden',
                  marginBottom: 6,
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${Math.max(0, Math.min(100, issue.bar_value))}%`,
                    background: barTone(issue.bar_value),
                    borderRadius: 999,
                  }}
                />
              </div>
              {issue.assignee && (
                <p style={{ margin: 0, fontSize: 11, color: '#888' }}>承办：{issue.assignee}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        style={{ ...mingOutlineBtn, width: '100%', marginTop: 8 }}
        onClick={onOpenDrawer}
      >
        {issues.length > preview.length
          ? `局势管理 · 共 ${issues.length} 条`
          : '局势管理 · 详情 / 立项 / 授权'}
      </button>
    </div>
  );
};
