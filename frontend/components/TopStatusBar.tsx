'use client';

import React, { useMemo, useState } from 'react';
import { useGameStore } from '../game/store';
import { buildMetricTooltipContent } from '../game/metricTooltipDisplay';
import { buildMingSalvageMetricTooltip } from '../game/ming/mingMetricDisplay';
import type { NationMetric, NationMetricKey, NationState } from '../game/types';
import type { SalvageBudget, SalvageLegacy } from '../game/ming/salvageStateTypes';
import { MetricTooltipPanel } from './MetricTooltipPanel';
import { MingBudgetHover } from './ming/MingBudgetHover';
import { MingLegacyBar } from './ming/MingLegacyBar';
import { MingRegionWarningHover } from './ming/MingRegionWarningHover';

type TopStatusBarProps = {
  /** 明代月度引擎等独立会话可注入指标，不读宋代 store */
  nationOverride?: NationState;
  /** 使用 ming-salvage 指标 tooltip（国库/内库/民心/皇威） */
  mingSalvageMetrics?: boolean;
  /** 游戏中返回选剧本 */
  onBack?: () => void;
  backLabel?: string;
  backDisabled?: boolean;
  /** 点击年月打开国势总览 */
  onYearClick?: () => void;
  /** 打开游戏菜单 */
  onOpenGameMenu?: () => void;
  /** ming-salvage 国库/内库 hover */
  mingBudget?: SalvageBudget;
  mingLegacies?: SalvageLegacy[];
  /** 行省风险摘要 hover */
  mingRegionWarning?: string;
  /** salvage 剧本 id，用于指标/预算展示口径 */
  salvageScenarioId?: import('../game/scenarios').ScenarioId;
};

export const TopStatusBar: React.FC<TopStatusBarProps> = ({
  nationOverride,
  mingSalvageMetrics = false,
  onBack,
  backLabel = '← 返回选剧本',
  backDisabled = false,
  onYearClick,
  onOpenGameMenu,
  mingBudget,
  mingLegacies,
  mingRegionWarning,
  salvageScenarioId,
}) => {
  const { nationState, currentQuarter, settlement, warArcs } = useGameStore((s) => ({
    nationState: nationOverride ?? s.nationState,
    currentQuarter: s.currentQuarter,
    settlement: s.settlement,
    warArcs: s.warArcs,
  }));
  const [hoveredKey, setHoveredKey] = useState<NationMetricKey | null>(null);

  const tooltipMap = useMemo(() => {
    const map = new Map<NationMetricKey, ReturnType<typeof buildMetricTooltipContent>>();
    for (const metric of nationState.metrics) {
      map.set(
        metric.key,
        mingSalvageMetrics
          ? buildMingSalvageMetricTooltip(metric, salvageScenarioId)
          : buildMetricTooltipContent({
              metric,
              allMetrics: nationState.metrics,
              currentQuarter,
              settlement,
              warArcs,
            }),
      );
    }
    return map;
  }, [nationState.metrics, currentQuarter, settlement, warArcs, mingSalvageMetrics, salvageScenarioId]);

  return (
    <div
      style={{
        position: 'relative',
        zIndex: 3000,
        background: 'linear-gradient(90deg, #1f130f, #261919)',
        borderBottom: '1px solid rgba(255,215,0,0.3)',
        padding: '8px 16px',
        display: 'flex',
        alignItems: 'center',
        color: '#f5f5f5',
        fontSize: 14,
      }}
    >
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          disabled={backDisabled}
          title="返回选剧本"
          style={{
            marginRight: 16,
            flexShrink: 0,
            border: '1px solid rgba(255,215,0,0.35)',
            borderRadius: 6,
            padding: '4px 10px',
            background: 'transparent',
            color: '#d4af37',
            cursor: backDisabled ? 'not-allowed' : 'pointer',
            fontSize: 12,
            opacity: backDisabled ? 0.5 : 1,
          }}
        >
          {backLabel}
        </button>
      ) : null}
      {onOpenGameMenu ? (
        <button
          type="button"
          onClick={onOpenGameMenu}
          title="游戏菜单"
          style={{
            marginRight: 12,
            flexShrink: 0,
            border: '1px solid rgba(255,215,0,0.35)',
            borderRadius: 6,
            padding: '4px 10px',
            background: 'transparent',
            color: '#d4af37',
            cursor: 'pointer',
            fontSize: 12,
          }}
        >
          ☰ 菜单
        </button>
      ) : null}
      <div
        onClick={onYearClick ? () => onYearClick() : undefined}
        title={onYearClick ? '点击查看本回合国势' : undefined}
        style={{
          marginRight: 24,
          fontWeight: 600,
          flexShrink: 0,
          cursor: onYearClick ? 'pointer' : 'default',
        }}
      >
        {nationState.dynasty} · {nationState.reignTitle} ·{' '}
        <span style={{ color: '#ffd700' }}>{nationState.yearLabel}</span>
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        {mingSalvageMetrics && mingBudget?.['国库'] && mingBudget?.['内库'] ? (
          <>
            <MingBudgetHover accountName="国库" budget={mingBudget['国库']} scenarioId={salvageScenarioId} />
            <MingBudgetHover accountName="内库" budget={mingBudget['内库']} scenarioId={salvageScenarioId} />
          </>
        ) : null}
        {nationState.metrics
          .filter((m) =>
            mingSalvageMetrics && mingBudget ? m.key !== 'treasury' && m.key !== 'innerTreasury' : true,
          )
          .map((m) => (
          <MetricPill
            key={m.key}
            metric={m}
            active={hoveredKey === m.key}
            onEnter={() => setHoveredKey(m.key)}
            onLeave={() => setHoveredKey((prev) => (prev === m.key ? null : prev))}
            tooltip={tooltipMap.get(m.key)}
          />
        ))}
        {mingLegacies && mingLegacies.length > 0 ? <MingLegacyBar legacies={mingLegacies} /> : null}
        {mingRegionWarning ? <MingRegionWarningHover regionWarning={mingRegionWarning} /> : null}
      </div>
    </div>
  );
};

type MetricPillProps = {
  metric: NationMetric;
  active: boolean;
  onEnter: () => void;
  onLeave: () => void;
  tooltip?: ReturnType<typeof buildMetricTooltipContent>;
};

const MetricPill: React.FC<MetricPillProps> = ({
  metric,
  active,
  onEnter,
  onLeave,
  tooltip,
}) => {
  return (
    <div
      style={{ position: 'relative' }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 8px',
          borderRadius: 999,
          background: active ? 'rgba(255,215,0,0.12)' : 'rgba(255,255,255,0.04)',
          border: active
            ? '1px solid rgba(255,215,0,0.55)'
            : '1px solid rgba(255,215,0,0.25)',
          cursor: 'default',
          transition: 'background 150ms ease, border-color 150ms ease',
        }}
      >
        <span style={{ color: '#ffebc1' }}>{metric.label}</span>
        <span style={{ fontWeight: 600 }}>{metric.value}</span>
        {metric.trend && (
          <span
            style={{
              color:
                metric.trend === 'up'
                  ? '#52c41a'
                  : metric.trend === 'down'
                    ? '#f5222d'
                    : '#888',
              fontSize: 10,
            }}
          >
            {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '·'}
          </span>
        )}
      </div>
      {active && tooltip ? (
        <div className="metric-tooltip-anchor">
          <MetricTooltipPanel content={tooltip} />
        </div>
      ) : null}
    </div>
  );
};
