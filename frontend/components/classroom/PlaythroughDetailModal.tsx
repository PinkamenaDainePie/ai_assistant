'use client';

import React, { useEffect } from 'react';
import type { PlaythroughRecord } from '../../lib/classroomApi';
import { formatPlaythroughStatus, formatScenarioLabel, formatPlaythroughProgress } from '../../game/scenarioLabels';
import { PlaythroughSummaryPanel } from './PlaythroughSummaryPanel';

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

type Props = {
  record: PlaythroughRecord | null;
  onClose: () => void;
};

export function PlaythroughDetailModal({ record, onClose }: Props) {
  useEffect(() => {
    if (!record) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [record, onClose]);

  if (!record) return null;

  return (
    <div className="ui-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="ui-modal ui-modal--playthrough"
        role="dialog"
        aria-modal="true"
        aria-labelledby="playthrough-detail-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ui-modal__head">
          <h2 id="playthrough-detail-title" className="ui-modal__title">
            {formatScenarioLabel(record.scenario_code)}
          </h2>
          <button type="button" className="ui-modal__close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        <dl className="ui-dl ui-dl--compact">
          <dt>状态</dt>
          <dd>{formatPlaythroughStatus(record.status)}</dd>
          <dt>进度</dt>
          <dd>{formatPlaythroughProgress(record.scenario_code, record.current_quarter)}</dd>
          <dt>结局</dt>
          <dd>{record.ending_type || '—'}</dd>
          <dt>开始</dt>
          <dd>{formatTime(record.started_at)}</dd>
          <dt>结束</dt>
          <dd>{formatTime(record.finished_at)}</dd>
        </dl>

        <h3 className="ui-card__subtitle">终局测评</h3>
        <PlaythroughSummaryPanel summaryJson={record.summary_json} status={record.status} />
      </div>
    </div>
  );
}
