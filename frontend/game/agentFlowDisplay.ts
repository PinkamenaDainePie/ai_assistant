/** 从 Workflow A / secondary_effects_report 提取季末可展示文案 */

export type AgentFlowDisplay = {
  hasContent: boolean;
  statusLine: string;
  proposalLines: string[];
  contestLines: string[];
  counterLines: string[];
  explanationZh: string;
  riskLevel: string;
};

const METRIC_LABELS: Record<string, string> = {
  treasury_balance: '国库',
  public_support: '民心',
  official_morale: '吏治',
  military_preparedness: '军备',
  border_stability: '边防',
  grain_reserve: '粮储',
};

function metricLabel(key: string): string {
  return METRIC_LABELS[key] || key;
}

function pickZh(obj: Record<string, unknown> | undefined, keys: string[]): string {
  if (!obj) return '';
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === 'string' && v.trim()) return v.trim();
  }
  return '';
}

function linesFromActors(block: Record<string, unknown> | undefined): string[] {
  if (!block) return [];
  const lines: string[] = [];
  const summary = pickZh(block, ['summary_zh', 'headline_zh', 'narrative_zh', 'stance_zh']);
  if (summary) lines.push(summary);
  const actors = block.opposing_actors;
  if (Array.isArray(actors)) {
    for (const a of actors.slice(0, 4)) {
      if (!a || typeof a !== 'object') continue;
      const row = a as Record<string, unknown>;
      const name = pickZh(row, ['name_zh', 'actor_label_zh', 'label_zh', 'id']);
      const resp = pickZh(row, ['response_zh', 'stance_zh', 'action_zh']);
      if (name && resp) lines.push(`${name}：${resp}`);
      else if (resp) lines.push(resp);
      else if (name) lines.push(name);
    }
  }
  const bureaucratic = pickZh(block, ['bureaucratic_response_zh', 'response_zh']);
  if (bureaucratic && !lines.includes(bureaucratic)) lines.push(bureaucratic);
  const followups = block.suggested_followups;
  if (Array.isArray(followups) && followups.length > 0) {
    lines.push(`后续动向：${followups.slice(0, 3).map(String).join('；')}`);
  }
  return lines;
}

export function formatAgentFlowReport(
  report?: Record<string, unknown> | null,
): AgentFlowDisplay {
  const r = report || {};
  const trace = (r.trace && typeof r.trace === 'object'
    ? r.trace
    : {}) as Record<string, unknown>;

  if (trace.skipped) {
    const reason = String(trace.reason || r.reason || 'skipped');
    return {
      hasContent: true,
      statusLine: `Agent A 未调用（${reason}）`,
      proposalLines: [],
      contestLines: [],
      counterLines: [],
      explanationZh: '',
      riskLevel: '',
    };
  }

  const proposals = (r.proposals && typeof r.proposals === 'object'
    ? r.proposals
    : {}) as Record<string, unknown>;
  const proposalLines: string[] = [];
  const deltas = proposals.metric_deltas;
  if (Array.isArray(deltas)) {
    for (const d of deltas) {
      if (!d || typeof d !== 'object') continue;
      const row = d as Record<string, unknown>;
      const key = String(row.key || '').trim();
      if (!key) continue;
      const val = Number(row.value ?? 0);
      const sign = val >= 0 ? '+' : '';
      proposalLines.push(`${metricLabel(key)} ${sign}${val}（Agent 提案，已尝试并入结算）`);
    }
  }
  const flags = proposals.flag_mutations;
  if (Array.isArray(flags)) {
    for (const f of flags) {
      if (!f || typeof f !== 'object') continue;
      const row = f as Record<string, unknown>;
      const key = String(row.key || '').trim();
      if (!key) continue;
      proposalLines.push(`标记 ${key} → ${row.value ? '开' : '关'}`);
    }
  }
  const stateFx = proposals.state_effects;
  if (Array.isArray(stateFx)) {
    for (const s of stateFx) {
      if (!s || typeof s !== 'object') continue;
      const row = s as Record<string, unknown>;
      const action = String(row.action || '').trim();
      const region = String(row.region || '').trim();
      if (action === 'set_region_status') {
        proposalLines.push(
          `地区 ${region} → ${row.status || 'unknown'}${row.occupier ? `（${row.occupier}）` : ''}`,
        );
      } else if (action === 'clear_region_status') {
        proposalLines.push(`地区 ${region} → 恢复常态`);
      }
    }
  }

  const merged = (r.merged_result && typeof r.merged_result === 'object'
    ? r.merged_result
    : {}) as Record<string, unknown>;
  const explanationZh = pickZh(merged, ['explanation_zh', 'summary_zh']);
  const riskLevel = pickZh(merged, ['risk_level']) || String(r.risk_level || '');

  const contestLines = linesFromActors(
    r.contest && typeof r.contest === 'object' ? (r.contest as Record<string, unknown>) : undefined,
  );
  const counterLines = linesFromActors(
    r.counter && typeof r.counter === 'object' ? (r.counter as Record<string, unknown>) : undefined,
  );

  const hasContent =
    proposalLines.length > 0 ||
    contestLines.length > 0 ||
    counterLines.length > 0 ||
    Boolean(explanationZh) ||
    Boolean(r.status);

  const statusParts: string[] = [];
  if (r.status) statusParts.push(String(r.status));
  if (r.route_mode) statusParts.push(String(r.route_mode));
  if (trace.source === 'adp_sse') statusParts.push('ADP');
  else if (trace.adp_fallback) statusParts.push('ADP 失败，本地 fallback');

  return {
    hasContent,
    statusLine: hasContent
      ? statusParts.length > 0
        ? `Agent A：${statusParts.join(' · ')}`
        : 'Agent A 已返回'
      : 'Agent A 无有效输出（检查 ADP / resolution_status / 人治类 playbook）',
    proposalLines,
    contestLines,
    counterLines,
    explanationZh,
    riskLevel,
  };
}
