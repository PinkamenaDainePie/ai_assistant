'use client';

import React from 'react';
import type { RegionDetailView } from '@/game/map/regionDisplay';

interface MapInfoCardProps {
  detail: RegionDetailView | null;
  onClose: () => void;
}

const toneColor = (tone: RegionDetailView['metrics'][number]['tone']) => {
  if (tone === 'good') return '#8fd4a0';
  if (tone === 'warn') return '#ffb080';
  return '#f0ebe4';
};

export function MapInfoCard({ detail, onClose }: MapInfoCardProps) {
  if (!detail) return null;

  return (
    <aside className="map-region-panel panel-enter-left">
      <div className="map-region-panel__header">
        <div>
          <div className="map-region-panel__eyebrow">地区信息</div>
          <h3 className="map-region-panel__title">{detail.name}</h3>
          <div className="map-region-panel__regime">所属政权 · {detail.dynasty}</div>
        </div>
        <button type="button" className="map-region-panel__close" onClick={onClose} aria-label="关闭">
          ×
        </button>
      </div>

      <div className="map-region-panel__status">{detail.statusLabel}</div>

      <div className="map-region-panel__scroll">
        <section className="map-region-panel__section">
          <div className="map-region-panel__section-title">区域描述</div>
          <p className="map-region-panel__description">{detail.description}</p>
        </section>

        {detail.focusTags.length > 0 ? (
          <section className="map-region-panel__section">
            <div className="map-region-panel__section-title">关目</div>
            <div className="map-region-panel__tags">
              {detail.focusTags.map((tag) => (
                <span key={tag} className="map-region-panel__tag">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        <section className="map-region-panel__section">
          <div className="map-region-panel__section-title">基本信息</div>
          <div className="map-region-panel__metrics">
            {detail.metrics.map((metric) => (
              <div key={metric.label} className="map-region-panel__metric-row">
                <span className="map-region-panel__metric-label">{metric.label}</span>
                <span
                  className="map-region-panel__metric-value"
                  style={{ color: toneColor(metric.tone) }}
                >
                  {metric.value}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </aside>
  );
}
