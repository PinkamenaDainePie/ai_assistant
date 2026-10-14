'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import type { TaskDetailView } from '../game/taskDetailDisplay';

type Props = {
  open: boolean;
  detail?: TaskDetailView | null;
  onClose: () => void;
};

export const TaskDetailModal: React.FC<Props> = ({ open, detail, onClose }) => {
  if (!open || !detail || typeof document === 'undefined') return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="task-detail-title"
      className="task-detail-overlay"
      onClick={onClose}
    >
      <div className="task-detail-panel panel-enter-up" onClick={(e) => e.stopPropagation()}>
        <div className="task-detail-panel__toolbar">
          <button type="button" className="task-detail-panel__back" onClick={onClose}>
            返回
          </button>
          <span className="task-detail-panel__status">{detail.statusLabel}</span>
          <button
            type="button"
            className="task-detail-panel__close"
            onClick={onClose}
            aria-label="关闭任务详情"
          >
            ×
          </button>
        </div>

        <div className="task-detail-panel__header">
          <h2 id="task-detail-title" className="task-detail-panel__title">
            {detail.title}
          </h2>
          <div className="task-detail-panel__subtitle">{detail.subtitle}</div>
        </div>

        <div className="task-detail-panel__body">{detail.description}</div>

        <div className="task-detail-panel__sections">
          {detail.sections.map((section) => (
            <div key={section.title} className="task-detail-panel__section">
              <div className="task-detail-panel__section-title">{section.title}</div>
              {section.lines.map((line) => (
                <div key={`${section.title}-${line}`} className="task-detail-panel__section-line">
                  {line}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
};
