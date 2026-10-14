'use client';

import React from 'react';
import type { SalvageMapNode } from '../../../game/ming/salvageStateTypes';
import {
  getMapIntelStyle,
  labelPower,
  mapNodeTitle,
} from '../../../game/ming/mingMapDisplay';
import { regionMonthlyTax } from '../../../game/ming/mingSalvageFormat';
import { mingOutlineBtn } from '../../../game/ming/mingUiStyles';
import { useDraggablePanel } from '../../../hooks/useDraggablePanel';

type Props = {
  node: SalvageMapNode;
  onClose: () => void;
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  color: '#aaa',
  padding: '4px 8px 4px 0',
  verticalAlign: 'top',
  whiteSpace: 'nowrap',
};

const tdStyle: React.CSSProperties = {
  color: '#ddd',
  padding: '4px 0',
  verticalAlign: 'top',
};

export const MingMapIntelPanel: React.FC<Props> = ({ node, onClose }) => {
  const region = node.region;
  const title = mapNodeTitle(node);
  const { panelRef, dragHandleProps, pos } = useDraggablePanel(node.id);
  const anchorStyle = pos
    ? { left: pos.left, top: pos.top, right: 'auto' as const, bottom: 'auto' as const, transform: 'none' }
    : getMapIntelStyle(node);

  return (
    <aside
      ref={panelRef}
      className="map-region-panel panel-enter-left ming-map-intel-panel"
      style={{
        position: 'fixed',
        zIndex: 1100,
        width: 'min(420px, calc(100vw - 24px))',
        ...anchorStyle,
      }}
    >
      <div className="map-region-panel__header" {...dragHandleProps}>
        <div>
          <div className="map-region-panel__eyebrow">
            {node.kind === 'theater' ? '战区情报' : node.kind === 'external' ? '外域' : '路分情报'}
          </div>
          <h3 className="map-region-panel__title">{title}</h3>
          {node.risk != null && (
            <div className="map-region-panel__regime">风险指数 · {node.risk}</div>
          )}
        </div>
        <button type="button" className="map-region-panel__close" onClick={onClose} aria-label="关闭">
          ×
        </button>
      </div>

      <div className="map-region-panel__scroll">
        {node.kind === 'external' ? (
          <>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <th style={thStyle}>归属</th>
                  <td style={tdStyle}>{labelPower(region?.controlled_by)}</td>
                </tr>
              </tbody>
            </table>
            <p style={{ color: '#888', fontSize: 12, margin: '12px 0 0' }}>
              非本朝直辖，详情不可见。
            </p>
          </>
        ) : null}

        {region && node.kind !== 'external' ? (
          <section className="map-region-panel__section">
            <div className="map-region-panel__section-title">路分概况</div>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <th style={thStyle}>人口</th>
                  <td style={tdStyle}>{region.population ?? '—'}万</td>
                  <th style={thStyle}>册田</th>
                  <td style={tdStyle}>{region.registered_land ?? '—'}万亩</td>
                </tr>
                <tr>
                  <th style={thStyle}>民心</th>
                  <td style={tdStyle}>{region.public_support ?? '—'}</td>
                  <th style={thStyle}>动乱</th>
                  <td style={tdStyle}>{region.unrest}</td>
                </tr>
                <tr>
                  <th style={thStyle}>粮产</th>
                  <td style={tdStyle}>
                    {Number(region.fiscal?.grain_output ?? region.grain_output ?? 0)}万石
                  </td>
                  <th style={thStyle}>余粮</th>
                  <td style={tdStyle}>
                    {Number(region.fiscal?.grain_stock ?? region.grain_stock ?? 0)}万石
                  </td>
                </tr>
                <tr>
                  <th style={thStyle}>实收</th>
                  <td style={tdStyle} colSpan={3}>{regionMonthlyTax(region)}万/月</td>
                </tr>
                <tr>
                  <th style={thStyle}>归属</th>
                  <td style={tdStyle}>{labelPower(region.controlled_by)}</td>
                  <th style={thStyle}>类型</th>
                  <td style={tdStyle}>{region.kind || '—'}</td>
                </tr>
                {(region.natural_disaster || region.human_disaster) && (
                  <tr>
                    <th style={thStyle}>灾患</th>
                    <td style={tdStyle} colSpan={3}>
                      {[region.natural_disaster, region.human_disaster].filter(Boolean).join(' · ')}
                    </td>
                  </tr>
                )}
                {region.status && (
                  <tr>
                    <th style={thStyle}>状况</th>
                    <td style={tdStyle} colSpan={3}>{region.status}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        ) : null}

        <section className="map-region-panel__section">
          <div className="map-region-panel__section-title">驻军</div>
          {node.armies?.length ? (
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ color: '#aaa' }}>
                  <th style={thStyle}>番号</th>
                  <th style={thStyle}>兵</th>
                  <th style={thStyle}>士气</th>
                  <th style={thStyle}>欠饷</th>
                </tr>
              </thead>
              <tbody>
                {node.armies.map((army) => {
                  const maint = army.maintenance_per_turn || 0;
                  const arr = army.arrears || 0;
                  const months = maint > 0 && arr > 0 ? arr / maint : 0;
                  const arrText =
                    arr > 0
                      ? months > 0
                        ? `${arr}万（≈${months.toFixed(1)}月）`
                        : `${arr}万`
                      : '—';
                  return (
                    <tr key={army.id}>
                      <td style={tdStyle}>{army.name}</td>
                      <td style={tdStyle}>{army.manpower}</td>
                      <td style={tdStyle}>{army.morale ?? '—'}</td>
                      <td style={tdStyle}>{arrText}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p style={{ color: '#888', fontSize: 12, margin: 0 }}>本地未记录常驻军。</p>
          )}
        </section>

        {region && node.buildings?.length ? (
          <section className="map-region-panel__section">
            <div className="map-region-panel__section-title">建筑</div>
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ color: '#aaa' }}>
                  <th style={thStyle}>名称</th>
                  <th style={thStyle}>等级</th>
                  <th style={thStyle}>完好</th>
                  <th style={thStyle}>维护</th>
                </tr>
              </thead>
              <tbody>
                {node.buildings.map((b) => (
                  <tr key={b.id}>
                    <td style={tdStyle}>{b.name}</td>
                    <td style={tdStyle}>{b.level ?? '—'}</td>
                    <td style={tdStyle}>{b.condition ?? '—'}</td>
                    <td style={tdStyle}>{b.maintenance ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}
      </div>

      <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
        <button type="button" style={mingOutlineBtn} onClick={onClose}>收起</button>
      </div>
    </aside>
  );
};
