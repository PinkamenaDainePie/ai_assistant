'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import { formatQuarterReportForDisplay } from '../game/quarterReportDisplay';
import type { ScenarioId } from '../game/scenarios';

type Props = {
  open: boolean;
  report?: Record<string, unknown> | null;
  currentQuarter?: number;
  scenarioId?: ScenarioId | null;
  onClose: () => void;
};

export const QuarterReportModal: React.FC<Props> = ({
  open,
  report,
  currentQuarter,
  scenarioId,
  onClose,
}) => {
  if (!open || typeof document === 'undefined') return null;

  const { title, body, hasContent } = formatQuarterReportForDisplay(report, {
    currentQuarter,
    scenarioId,
  });

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="quarter-report-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 20000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.58)',
        padding:
          'max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left))',
        boxSizing: 'border-box',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(640px, 100%)',
          maxHeight: 'min(88vh, calc(100vh - 40px))',
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
            alignItems: 'flex-start',
            gap: 12,
            padding: '14px 16px',
            borderBottom: '1px solid rgba(255,215,0,0.2)',
          }}
        >
          <span
            id="quarter-report-title"
            style={{ fontWeight: 700, color: '#ffd700', fontSize: 15, lineHeight: 1.45 }}
          >
            {title}
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              color: '#c8c0b8',
              cursor: 'pointer',
              fontSize: 20,
              lineHeight: 1,
              padding: '0 4px',
            }}
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        <div
          style={{
            padding: '16px 18px 20px',
            overflowY: 'auto',
            fontSize: 14,
            lineHeight: 1.75,
            whiteSpace: 'pre-wrap',
            color: '#e8e0d4',
            fontFamily: '"Noto Serif SC", "Songti SC", serif',
          }}
        >
          {hasContent ? (
            body
          ) : (
            <span style={{ color: '#a8a098' }}>
              暂无朝政纪要。完成「下季」推进后，后端将生成本季季度报告。
            </span>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
};
