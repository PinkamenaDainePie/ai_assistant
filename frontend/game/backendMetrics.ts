import { NationMetric, NationState } from './types';

const METRIC_BACKEND_TO_UI: Record<string, NationMetric['key']> = {
  treasury_balance: 'treasury',
  tax_completion_index: 'taxStability',
  public_support: 'publicSupport',
  authority: 'emperorTrust',
  corruption: 'scholarSupport',
  revolt_risk: 'externalPressure',
};

const UI_TO_BACKEND_CHAT: Partial<Record<NationMetric['key'], string>> = {
  treasury: 'treasury_balance',
  taxStability: 'tax_completion_index',
  publicSupport: 'public_support',
  scholarSupport: 'corruption',
  emperorTrust: 'authority',
  externalPressure: 'revolt_risk',
};

const clamp = (v: number, min = 0, max = 100) =>
  Math.max(min, Math.min(max, v));

export function applyBackendMetricsToNationState(
  prev: NationState,
  backendMetrics: Record<string, number>,
): NationState {
  const map: Record<string, number> = backendMetrics || {};
  const nextMetrics = prev.metrics.map((m) => {
    const backendKey = Object.keys(METRIC_BACKEND_TO_UI).find(
      (k) => METRIC_BACKEND_TO_UI[k] === m.key,
    );
    if (!backendKey) return m;
    const raw = map[backendKey];
    if (typeof raw !== 'number' || Number.isNaN(raw)) return m;
    // UI is mostly 0-100 index except treasury which we compress.
    const value =
      m.key === 'treasury'
        ? clamp(raw / 30000, 0, 100)
        : clamp(raw, 0, 100);
    const trend =
      value > m.value ? 'up' : value < m.value ? 'down' : 'stable';
    return {
      ...m,
      value: Number(value.toFixed(2)),
      trend: trend as 'up' | 'down' | 'stable',
    };
  });
  return { ...prev, metrics: nextMetrics };
}

export function applyBackendReportToMetrics(
  prev: NationState,
  reportMetrics: Record<string, number>,
): NationMetric[] {
  return applyBackendMetricsToNationState(prev, reportMetrics).metrics;
}

export function nationMetricsToApiPayload(
  state: NationState,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of state.metrics) {
    const key = UI_TO_BACKEND_CHAT[m.key];
    if (!key) continue;
    if (m.key === 'treasury') {
      out[key] = Number((m.value * 30000).toFixed(2));
    } else {
      out[key] = Number(m.value.toFixed(2));
    }
  }
  return out;
}

