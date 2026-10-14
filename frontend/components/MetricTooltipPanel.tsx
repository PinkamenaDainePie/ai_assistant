'use client';

import React from 'react';
import type { MetricTooltipContent, MetricTooltipRow } from '../game/metricTooltipDisplay';

const toneColor = (tone: MetricTooltipRow['tone']) => {
  if (tone === 'good') return '#8fd4a0';
  if (tone === 'warn') return '#ffb080';
  return '#f0ebe4';
};

type Props = {
  content: MetricTooltipContent;
};

export const MetricTooltipPanel: React.FC<Props> = ({ content }) => {
  return (
    <div className="metric-tooltip-panel">
      <div className="metric-tooltip-panel__header">
        <div className="metric-tooltip-panel__title">{content.title}</div>
        <div className="metric-tooltip-panel__headline">{content.headline}</div>
      </div>
      <div className="metric-tooltip-panel__divider" />
      <div className="metric-tooltip-panel__rows">
        {content.rows.map((row) => (
          <div key={row.label} className="metric-tooltip-panel__row">
            <span className="metric-tooltip-panel__label">{row.label}</span>
            <span
              className="metric-tooltip-panel__value"
              style={{ color: toneColor(row.tone) }}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
      {content.footnote ? (
        <div className="metric-tooltip-panel__footnote">{content.footnote}</div>
      ) : null}
    </div>
  );
};
