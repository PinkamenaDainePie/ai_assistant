import type { NationMetric, NationMetricKey } from '../types';
import type { ScenarioId } from '../scenarios';

/** ming-salvage 四大指标 → 前端展示（万历/崇祯） */
export const MING_SALVAGE_METRIC_CATALOG: Record<
  string,
  { key: NationMetricKey; label: string; unit?: string; description: string }
> = {
  国库: {
    key: 'treasury',
    label: '国库',
    unit: '万两',
    description: '太仓银储，支应辽饷、宗禄、官俸、河工与赈济。',
  },
  内库: {
    key: 'innerTreasury',
    label: '内库',
    unit: '万两',
    description: '内廷帑藏，金花银、织造等入此，供宫廷与内廷开支。',
  },
  民心: {
    key: 'publicSupport',
    label: '民心',
    description: '天下舆情指数；催科过急、饥荒兵乱则降。',
  },
  皇威: {
    key: 'emperorTrust',
    label: '皇威',
    description: '皇帝权威与政令通行力；不足则阳奉阴违。',
  },
};

/** 熙宁 v2 指标说明（岁币/边饷口径） */
export const SONG_SALVAGE_METRIC_CATALOG: Record<
  string,
  { key: NationMetricKey; label: string; unit?: string; description: string }
> = {
  国库: {
    key: 'treasury',
    label: '国库',
    unit: '万两',
    description: '三司帑藏，支应岁币、边饷、官俸、河漕与赈济。',
  },
  内库: {
    key: 'innerTreasury',
    label: '内库',
    unit: '万两',
    description: '内廷帑藏，供宫廷与内廷开支。',
  },
  民心: {
    key: 'publicSupport',
    label: '民心',
    description: '天下舆情指数；催科过急、饥荒兵乱则降。',
  },
  皇威: {
    key: 'emperorTrust',
    label: '皇威',
    description: '皇帝权威与政令通行力；不足则阳奉阴违。',
  },
};

function metricCatalogForScenario(scenarioId?: ScenarioId) {
  return scenarioId === 'song_xining_v2' ? SONG_SALVAGE_METRIC_CATALOG : MING_SALVAGE_METRIC_CATALOG;
}

const ORDER = ['国库', '内库', '民心', '皇威'] as const;

export function mapSalvageMetrics(
  raw: Record<string, number> | undefined,
  scenarioId?: ScenarioId,
): NationMetric[] {
  const catalog = metricCatalogForScenario(scenarioId);
  const src = raw || {};
  const out: NationMetric[] = [];
  for (const id of ORDER) {
    const spec = catalog[id];
    if (!spec) continue;
    out.push({
      key: spec.key,
      label: spec.label,
      value: Number(src[id] ?? 0),
      trend: 'stable',
    });
  }
  for (const [id, value] of Object.entries(src)) {
    if (ORDER.includes(id as (typeof ORDER)[number])) continue;
    out.push({
      key: 'treasury',
      label: id,
      value: Number(value),
      trend: 'stable',
    });
  }
  return out;
}

export function buildMingSalvageMetricTooltip(metric: NationMetric, scenarioId?: ScenarioId) {
  const catalog = metricCatalogForScenario(scenarioId);
  const byLabel = Object.values(catalog).find((c) => c.label === metric.label);
  const byKey = catalog[metric.label];
  const spec = byLabel || byKey;
  const unit = spec?.unit;
  const valueText = unit
    ? `${Number(metric.value.toFixed(0))} ${unit}`
    : `${Number(metric.value.toFixed(0))}`;

  const dynastyHint = scenarioId === 'song_xining_v2' ? '北宋' : '明代';
  return {
    title: metric.label,
    headline: valueText,
    rows: [{ label: '说明', value: spec?.description || `${dynastyHint}国势指标。` }],
    footnote: '数据来自 ming-salvage 月度结算。',
  };
}
