import type { WarArcState } from '../lib/renwuApi';
import type { NationMetric, NationMetricKey } from './types';

export type MetricTooltipRow = {
  label: string;
  value: string;
  tone?: 'good' | 'warn' | 'neutral';
};

export type MetricTooltipContent = {
  title: string;
  headline: string;
  rows: MetricTooltipRow[];
  footnote?: string;
};

export type MetricTooltipInput = {
  metric: NationMetric;
  allMetrics: NationMetric[];
  currentQuarter: number;
  settlement?: {
    baselineMetrics?: Record<string, number>;
    finalMetrics?: Record<string, number>;
  };
  warArcs: WarArcState[];
};

const clamp = (v: number, min = 0, max = 100) => Math.max(min, Math.min(max, v));

const fmtIndex = (v: number) => `${Number(v.toFixed(1))}`;

function readMetric(metrics: NationMetric[], key: NationMetricKey): number {
  return metrics.find((m) => m.key === key)?.value ?? 0;
}

function quarterDelta(
  settlement: MetricTooltipInput['settlement'],
  key: NationMetricKey,
): string {
  const before = settlement?.baselineMetrics?.[key];
  const after = settlement?.finalMetrics?.[key];
  if (typeof before !== 'number' || typeof after !== 'number') return '—';
  const delta = Number((after - before).toFixed(1));
  return delta >= 0 ? `+${delta}` : `${delta}`;
}

function deltaTone(deltaText: string): MetricTooltipRow['tone'] {
  if (deltaText === '—') return 'neutral';
  if (deltaText.startsWith('+')) return 'good';
  if (deltaText.startsWith('-')) return 'warn';
  return 'neutral';
}

function toneByIndex(v: number, invert = false): MetricTooltipRow['tone'] {
  if (invert) {
    if (v >= 65) return 'warn';
    if (v <= 35) return 'good';
    return 'neutral';
  }
  if (v >= 65) return 'good';
  if (v <= 35) return 'warn';
  return 'neutral';
}

function buildTreasuryTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement } = input;
  const external = readMetric(allMetrics, 'externalPressure');
  const publicSupport = readMetric(allMetrics, 'publicSupport');
  const treasuryWan = Number((metric.value * 3).toFixed(1));
  const mobile = clamp(metric.value - external * 0.28);
  const reliefReserve = clamp(publicSupport * 0.35 + metric.value * 0.15);
  const delta = quarterDelta(settlement, 'treasury');

  return {
    title: '国库储备明细',
    headline: `折算约 ${treasuryWan} 万两`,
    rows: [
      { label: '储备指数', value: fmtIndex(metric.value), tone: toneByIndex(metric.value) },
      { label: '机动可调拨', value: fmtIndex(mobile), tone: toneByIndex(mobile) },
      { label: '赈济预留能力', value: fmtIndex(reliefReserve), tone: toneByIndex(reliefReserve) },
      {
        label: '边军拨付压力',
        value: fmtIndex(clamp(external * 0.62)),
        tone: toneByIndex(external * 0.62, true),
      },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
    footnote: '指数为前端估算；提交诏令与季度结算后以后端结算为准。',
  };
}

function buildTaxTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement } = input;
  const treasury = readMetric(allMetrics, 'treasury');
  const fieldRate = metric.value;
  const tradeRate = clamp(metric.value - 4 + (treasury >= 50 ? 3 : -2));
  const collectionPressure = clamp(100 - metric.value + (treasury < 40 ? 6 : 0));
  const delta = quarterDelta(settlement, 'taxStability');

  return {
    title: '税收稳定明细',
    headline: `综合完纳 ${fmtIndex(metric.value)}`,
    rows: [
      { label: '田赋完纳率', value: fmtIndex(fieldRate), tone: toneByIndex(fieldRate) },
      { label: '商税完纳率', value: fmtIndex(tradeRate), tone: toneByIndex(tradeRate) },
      {
        label: '催科强度',
        value: fmtIndex(collectionPressure),
        tone: toneByIndex(collectionPressure, true),
      },
      { label: '漏税风险', value: fmtIndex(clamp(100 - tradeRate)), tone: toneByIndex(100 - tradeRate, true) },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
  };
}

function buildPublicSupportTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement } = input;
  const tax = readMetric(allMetrics, 'taxStability');
  const capital = clamp(metric.value + 2 - (tax < 40 ? 4 : 0));
  const regions = clamp(metric.value - 2);
  const complaintPressure = clamp(100 - metric.value + (tax < 45 ? 5 : 0));
  const delta = quarterDelta(settlement, 'publicSupport');

  return {
    title: '民心明细',
    headline: `全国民情 ${fmtIndex(metric.value)}`,
    rows: [
      { label: '京畿民情', value: fmtIndex(capital), tone: toneByIndex(capital) },
      { label: '诸路民情', value: fmtIndex(regions), tone: toneByIndex(regions) },
      {
        label: '灾伤投诉压力',
        value: fmtIndex(complaintPressure),
        tone: toneByIndex(complaintPressure, true),
      },
      { label: '变法接受度', value: fmtIndex(clamp(metric.value + tax * 0.08 - 8)), tone: 'neutral' },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
  };
}

function buildScholarSupportTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement } = input;
  const emperor = readMetric(allMetrics, 'emperorTrust');
  const censor = clamp(metric.value + 3);
  const court = clamp((metric.value + emperor) / 2);
  const local = clamp(metric.value - 5);
  const delta = quarterDelta(settlement, 'scholarSupport');

  return {
    title: '士大夫支持明细',
    headline: `朝野总支持 ${fmtIndex(metric.value)}`,
    rows: [
      { label: '台谏舆论', value: fmtIndex(censor), tone: toneByIndex(censor) },
      { label: '中枢同僚', value: fmtIndex(court), tone: toneByIndex(court) },
      { label: '地方士绅', value: fmtIndex(local), tone: toneByIndex(local) },
      { label: '异议声量', value: fmtIndex(clamp(100 - metric.value)), tone: toneByIndex(100 - metric.value, true) },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
  };
}

function buildEmperorTrustTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement } = input;
  const publicSupport = readMetric(allMetrics, 'publicSupport');
  const scholar = readMetric(allMetrics, 'scholarSupport');
  const audience = metric.value;
  const reform = clamp(metric.value + publicSupport * 0.12 - scholar * 0.08);
  const appointment = clamp((metric.value + scholar) / 2 - 3);
  const delta = quarterDelta(settlement, 'emperorTrust');

  return {
    title: '皇帝信任明细',
    headline: `御前信任 ${fmtIndex(metric.value)}`,
    rows: [
      { label: '奏对表现', value: fmtIndex(audience), tone: toneByIndex(audience) },
      { label: '变法推进认可', value: fmtIndex(reform), tone: toneByIndex(reform) },
      { label: '用人任使得失', value: fmtIndex(appointment), tone: toneByIndex(appointment) },
      { label: '失政风险', value: fmtIndex(clamp(100 - metric.value)), tone: toneByIndex(100 - metric.value, true) },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
  };
}

function buildExternalPressureTooltip(input: MetricTooltipInput): MetricTooltipContent {
  const { metric, allMetrics, settlement, warArcs } = input;
  const treasury = readMetric(allMetrics, 'treasury');
  const delta = quarterDelta(settlement, 'externalPressure');

  if (warArcs.length > 0) {
    const rows: MetricTooltipRow[] = warArcs.flatMap((arc) => {
      const pressures = Object.entries(arc.pressure || {}).slice(0, 2);
      if (pressures.length === 0) {
        return [{ label: arc.label_zh || arc.arc_id, value: fmtIndex(metric.value), tone: 'warn' as const }];
      }
      return pressures.map(([k, v]) => ({
        label: `${arc.label_zh || arc.arc_id}·${
          k === 'supply_line'
            ? '补给'
            : k === 'command_cohesion'
              ? '军心'
              : k === 'frontier_compliance'
                ? '边地'
                : k
        }`,
        value: fmtIndex(Number(v)),
        tone: toneByIndex(Number(v), true),
      }));
    });
    rows.push({ label: '军需拖累', value: fmtIndex(clamp(treasury < 45 ? 58 : 32)), tone: 'warn' });
    rows.push({ label: '上季净变动', value: delta, tone: deltaTone(delta) });
    return {
      title: '边患压力明细',
      headline: `综合边患 ${fmtIndex(metric.value)}`,
      rows: rows.slice(0, 5),
      footnote: '战役态势来自当前任务池关联战线。',
    };
  }

  return {
    title: '边患压力明细',
    headline: `综合边患 ${fmtIndex(metric.value)}`,
    rows: [
      { label: '西夏方向', value: fmtIndex(clamp(metric.value * 0.46)), tone: toneByIndex(metric.value * 0.46, true) },
      { label: '辽境压力', value: fmtIndex(clamp(metric.value * 0.34)), tone: toneByIndex(metric.value * 0.34, true) },
      { label: '内乱外溢', value: fmtIndex(clamp(metric.value * 0.2)), tone: toneByIndex(metric.value * 0.2, true) },
      {
        label: '军需拖累',
        value: fmtIndex(clamp(treasury < 45 ? 55 : 28)),
        tone: toneByIndex(treasury < 45 ? 55 : 28, true),
      },
      { label: '上季净变动', value: delta, tone: deltaTone(delta) },
    ],
  };
}

export function buildMetricTooltipContent(input: MetricTooltipInput): MetricTooltipContent {
  switch (input.metric.key) {
    case 'treasury':
      return buildTreasuryTooltip(input);
    case 'taxStability':
      return buildTaxTooltip(input);
    case 'publicSupport':
      return buildPublicSupportTooltip(input);
    case 'scholarSupport':
      return buildScholarSupportTooltip(input);
    case 'emperorTrust':
      return buildEmperorTrustTooltip(input);
    case 'externalPressure':
      return buildExternalPressureTooltip(input);
    default:
      return {
        title: input.metric.label,
        headline: fmtIndex(input.metric.value),
        rows: [{ label: '当前指数', value: fmtIndex(input.metric.value), tone: 'neutral' }],
      };
  }
}
