'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { ATLAS_TIMELINE, COMPARE_ROWS } from '@/game/portalContent';
import { getPolityById } from '@/game/worldPolityProfiles';
import { GlobeDetailPanel } from './GlobeDetailPanel';
import { AtlasSlideIn } from './AtlasSlideIn';

const GlobeScene = dynamic(() => import('./GlobeScene').then((m) => m.GlobeScene), {
  ssr: false,
  loading: () => <div className="portal-globe__loading">加载 3D 地球…</div>,
});

type AtlasTab = 'globe' | 'timeline' | 'compare';

type GlobeAtlasPanelProps = {
  onEnterGame: () => void;
};

export const GlobeAtlasPanel: React.FC<GlobeAtlasPanelProps> = ({ onEnterGame }) => {
  const [tab, setTab] = useState<AtlasTab>('globe');
  const [selectedPolityId, setSelectedPolityId] = useState<string | null>('song');
  const [selectedNodeId, setSelectedNodeId] = useState('xining');

  const selectedPolity = selectedPolityId ? getPolityById(selectedPolityId) ?? null : null;
  const selectedNode = ATLAS_TIMELINE.find((n) => n.id === selectedNodeId) ?? ATLAS_TIMELINE[3];

  return (
    <div className="portal-atlas">
      <div className="portal-atlas__tabs">
        <button
          type="button"
          className={`portal-atlas__tab${tab === 'globe' ? ' portal-atlas__tab--active' : ''}`}
          onClick={() => setTab('globe')}
        >
          3D 地球
        </button>
        <button
          type="button"
          className={`portal-atlas__tab${tab === 'timeline' ? ' portal-atlas__tab--active' : ''}`}
          onClick={() => setTab('timeline')}
        >
          制度时间轴
        </button>
        <button
          type="button"
          className={`portal-atlas__tab${tab === 'compare' ? ' portal-atlas__tab--active' : ''}`}
          onClick={() => setTab('compare')}
        >
          中西对照
        </button>
      </div>

      {tab === 'globe' ? (
        <div className="portal-atlas__panel-wrap">
          <AtlasSlideIn animKey={`tab-${tab}`}>
            <div className="portal-globe">
              <div className="portal-globe__canvas-col">
                <div className="portal-globe__canvas-wrap">
                  <GlobeScene selectedId={selectedPolityId} onSelect={setSelectedPolityId} />
                </div>
                <p className="portal-globe__caption">
                  地球纹理来自公开素材；彩色区域为约 11 世纪东亚核心政权粗略国界（示意，非精确 GIS，参考历史地图集类资料）。
                </p>
              </div>
              <GlobeDetailPanel
                polity={selectedPolity}
                onEnterGame={() => {
                  onEnterGame();
                }}
              />
            </div>
          </AtlasSlideIn>
        </div>
      ) : null}

      {tab === 'timeline' ? (
        <div className="portal-atlas__panel-wrap">
          <AtlasSlideIn animKey={`tab-${tab}`}>
            <div className="portal-atlas__timeline">
              {ATLAS_TIMELINE.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  className={`portal-atlas__node portal-atlas__node--${node.tone}${selectedNodeId === node.id ? ' portal-atlas__node--active' : ''}`}
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <span className="portal-atlas__era">{node.era}</span>
                  <span className="portal-atlas__node-title">{node.title}</span>
                  <span className="portal-atlas__year">{node.year}</span>
                </button>
              ))}
            </div>
            <div className={`portal-atlas__detail portal-atlas__detail--${selectedNode.tone}`}>
              <AtlasSlideIn animKey={selectedNodeId}>
                <h3>{selectedNode.title}</h3>
                <p className="portal-atlas__meta">
                  {selectedNode.era} · {selectedNode.year}
                </p>
                <p>{selectedNode.summary}</p>
                {selectedNodeId === 'xining' ? (
                  <button type="button" className="portal-btn portal-btn--dark" style={{ marginTop: 16 }} onClick={onEnterGame}>
                    进入熙宁制度模拟 →
                  </button>
                ) : null}
              </AtlasSlideIn>
            </div>
          </AtlasSlideIn>
        </div>
      ) : null}

      {tab === 'compare' ? (
        <div className="portal-atlas__panel-wrap">
          <AtlasSlideIn animKey={`tab-${tab}`}>
            <div className="portal-atlas__compare portal-atlas__compare--solo">
              <h4>中西对照（以宋代与罗马/欧洲为参照）</h4>
              <div className="portal-atlas__table-wrap">
                <table className="portal-atlas__table">
                  <thead>
                    <tr>
                      <th>维度</th>
                      <th>中国（以宋为代表）</th>
                      <th>西方（罗马等）</th>
                    </tr>
                  </thead>
                  <tbody>
                    {COMPARE_ROWS.map((row) => (
                      <tr key={row.dimension}>
                        <td>{row.dimension}</td>
                        <td>{row.china}</td>
                        <td>{row.west}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </AtlasSlideIn>
        </div>
      ) : null}
    </div>
  );
};
