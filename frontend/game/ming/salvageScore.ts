import type { MingEnding, MingGameState } from './mingTurnPhase';

export type SalvageScoreResult = {
  score: number;
  score_label_zh: string;
  score_source: 'heuristic' | 'llm';
};

const ENDING_MULTIPLIER: Record<string, number> = {
  capital_fallen: 0.35,
  emperor_suicide: 0.4,
  emperor_abdicate: 0.45,
  timeout: 1,
};

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

function scoreLabelZh(score: number): string {
  if (score >= 90) return '卓异';
  if (score >= 80) return '上';
  if (score >= 70) return '良';
  if (score >= 60) return '中';
  if (score >= 45) return '平';
  return '不足';
}

/** 钱粮指标（万两）粗归一化到 0–100 */
function normalizeTreasuryMetric(value: number): number {
  const v = Math.max(0, value);
  if (v <= 0) return 15;
  return clamp(18 + Math.log10(v + 1) * 22, 0, 100);
}

/**
 * A1：Salvage 终局启发式评分（民心/皇威 0–100，钱粮对数归一）。
 */
export function computeSalvageHeuristicScore(
  metrics: Record<string, number> | undefined,
  endingStatus: string,
): SalvageScoreResult {
  const m = metrics || {};
  const support = clamp(Number(m['民心'] ?? 50), 0, 100);
  const authority = clamp(Number(m['皇威'] ?? 50), 0, 100);
  const treasury = normalizeTreasuryMetric(Number(m['国库'] ?? 0));
  const inner = normalizeTreasuryMetric(Number(m['内库'] ?? 0));
  const fiscal = treasury * 0.6 + inner * 0.4;

  let base = support * 0.42 + authority * 0.33 + fiscal * 0.25;
  const mult = ENDING_MULTIPLIER[endingStatus] ?? 0.85;
  if (endingStatus && endingStatus !== 'timeout') {
    base *= mult;
  } else if (endingStatus === 'timeout') {
    base = base * 0.92 + 8;
  }

  const score = Math.round(clamp(base, 0, 100));
  return {
    score,
    score_label_zh: scoreLabelZh(score),
    score_source: 'heuristic',
  };
}

export function resolveSalvagePlaythroughScore(
  ending: MingEnding,
  metrics: Record<string, number> | undefined,
): SalvageScoreResult {
  const llmScore =
    typeof ending.score === 'number' && Number.isFinite(ending.score)
      ? clamp(Math.round(ending.score), 0, 100)
      : null;
  if (llmScore != null) {
    return {
      score: llmScore,
      score_label_zh: (ending.score_label_zh || '').trim() || scoreLabelZh(llmScore),
      score_source: 'llm',
    };
  }
  return computeSalvageHeuristicScore(metrics, ending.status);
}

export function buildSalvageSummaryJson(
  ending: MingEnding,
  turn: number,
  metrics?: Record<string, number>,
): Record<string, unknown> {
  const scored = resolveSalvagePlaythroughScore(ending, metrics);
  return {
    title_zh: ending.label,
    summary_zh: ending.summary,
    kind: ending.status,
    ending_mode: 'salvage',
    turn_count: turn,
    score: scored.score,
    score_label_zh: scored.score_label_zh,
    score_source: scored.score_source,
    metrics_snapshot: metrics || {},
    timeline: (ending.timeline || []).slice(-5),
  };
}

export function buildSalvageSummaryJsonFromState(st: MingGameState): Record<string, unknown> {
  const turn = Number(st.turn?.turn) || 0;
  if (!st.ending) {
    return { kind: 'ended', ending_mode: 'salvage', turn_count: turn };
  }
  return buildSalvageSummaryJson(st.ending, turn, st.metrics);
}
