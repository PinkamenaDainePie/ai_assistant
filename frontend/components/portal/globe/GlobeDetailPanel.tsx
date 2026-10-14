'use client';

import React from 'react';
import type { WorldPolityProfile } from '@/game/worldPolityProfiles';
import { AtlasSlideIn } from './AtlasSlideIn';

type GlobeDetailPanelProps = {
  polity: WorldPolityProfile | null;
  onEnterGame?: () => void;
};

export const GlobeDetailPanel: React.FC<GlobeDetailPanelProps> = ({ polity, onEnterGame }) => {
  const animKey = polity?.id ?? 'empty';

  if (!polity) {
    return (
      <div className="portal-globe__detail-col">
        <div className="portal-globe__detail portal-globe__detail--empty">
          <AtlasSlideIn animKey={animKey}>
            <h3>点击地球上的色块区域</h3>
            <p>各政权简化国界已标注在地球表面（约 11 世纪东亚格局，非精确 GIS）。点击色块查看财税制度与经济概况。</p>
            <ul className="portal-globe__hint-list">
              <li>紫色：北宋（课程核心，可进入制度模拟）</li>
              <li>蓝色/黄色：辽、西夏</li>
              <li>绿/橙/青：大理、大越、占城、蒲甘、高棉、高丽、日本等</li>
            </ul>
          </AtlasSlideIn>
        </div>
      </div>
    );
  }

  return (
    <div className="portal-globe__detail-col">
      <div className="portal-globe__detail">
        <AtlasSlideIn animKey={animKey}>
          <div className="portal-globe__detail-header">
            <span className="portal-globe__detail-dot" style={{ background: polity.markerColor }} />
            <div>
              <h3>{polity.name}</h3>
              <p className="portal-globe__meta">{polity.periodLabel}</p>
            </div>
          </div>
          <p className="portal-globe__regime">{polity.regime} · {polity.relationToSong}</p>

          <section className="portal-globe__section">
            <h4>财税制度</h4>
            <p className="portal-globe__lead">{polity.fiscalSystem.title}</p>
            <ul>
              {polity.fiscalSystem.revenue.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="portal-globe__sub"><strong>货币：</strong>{polity.fiscalSystem.currency}</p>
            <p className="portal-globe__sub">
              <strong>机构：</strong>
              {polity.fiscalSystem.institutions.join('、')}
            </p>
          </section>

          <section className="portal-globe__section">
            <h4>经济概况</h4>
            <p className="portal-globe__sub"><strong>贸易：</strong>{polity.economy.trade}</p>
            <p className="portal-globe__sub"><strong>人口：</strong>{polity.economy.population}</p>
            <ul>
              {polity.economy.highlights.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          {polity.compareWest ? (
            <section className="portal-globe__section portal-globe__section--muted">
              <h4>中西对照</h4>
              <p>{polity.compareWest}</p>
            </section>
          ) : null}

          {polity.id === 'song' && onEnterGame ? (
            <button type="button" className="portal-btn portal-btn--dark portal-globe__cta" onClick={onEnterGame}>
              进入熙宁制度模拟 →
            </button>
          ) : null}
        </AtlasSlideIn>
      </div>
    </div>
  );
};
