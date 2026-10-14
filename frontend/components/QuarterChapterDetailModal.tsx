'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import type { QuarterChapterDetailView } from '../game/quarterChapterDisplay';

type Props = {
  open: boolean;
  detail?: QuarterChapterDetailView | null;
  onClose: () => void;
};

export const QuarterChapterDetailModal: React.FC<Props> = ({
  open,
  detail,
  onClose,
}) => {
  if (!open || !detail || typeof document === 'undefined') return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="quarter-chapter-detail-title"
      className="quarter-chapter-detail-overlay"
      onClick={onClose}
    >
      <div
        className="quarter-chapter-detail-panel panel-enter-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="quarter-chapter-detail-panel__toolbar">
          <button
            type="button"
            className="quarter-chapter-detail-panel__back"
            onClick={onClose}
          >
            返回
          </button>
          <span className="quarter-chapter-detail-panel__season">
            {detail.quarterLabel}
          </span>
          <button
            type="button"
            className="quarter-chapter-detail-panel__close"
            onClick={onClose}
            aria-label="关闭季度总结详情"
          >
            ×
          </button>
        </div>

        <div className="quarter-chapter-detail-panel__header">
          <h2 id="quarter-chapter-detail-title" className="quarter-chapter-detail-panel__title">
            {detail.title}
          </h2>
          {detail.headline ? (
            <div className="quarter-chapter-detail-panel__headline">{detail.headline}</div>
          ) : null}
        </div>

        <div className="quarter-chapter-detail-panel__scroll">
          <div className="quarter-chapter-detail-panel__body">{detail.body}</div>

          {detail.sections.length > 0 ? (
            <div className="quarter-chapter-detail-panel__sections">
              {detail.sections.map((section) => (
                <div key={section.title} className="quarter-chapter-detail-panel__section">
                  <div className="quarter-chapter-detail-panel__section-title">
                    {section.title}
                  </div>
                  {section.lines.map((line) => (
                    <div
                      key={`${section.title}-${line}`}
                      className="quarter-chapter-detail-panel__section-line"
                    >
                      {line}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="quarter-chapter-detail-panel__footer">
          <button
            type="button"
            className="quarter-chapter-detail-panel__read-btn"
            onClick={onClose}
          >
            朕已阅
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
};
