import { getScenario, type ScenarioId } from '../game/scenarios';
import { mapSalvageMetrics } from '../game/ming/mingMetricDisplay';
import type { Character, NationState } from '../game/types';
import type {
  MingDirective,
  MingGameState,
  MingPendingDecision,
  MingSalvageIssue,
  MingClosedIssue,
  MingEnding,
  MingStructuredDirective,
  MingTurnPhase,
} from '../game/ming/mingTurnPhase';
import type {
  SalvageBudget,
  SalvageGameState,
  SalvageLegacy,
  SalvageMapNode,
  SalvagePower,
  SalvagePresetTrees,
  SalvageVictoryStatus,
  SalvageBuilding,
  SalvageRegion,
} from '../game/ming/salvageStateTypes';

export type { SalvageGameState } from '../game/ming/salvageStateTypes';

export type SalvageAdapterContext = {
  /** 前端 ScenarioId（如 ming_wanli / song_xining_v2） */
  scenarioId?: ScenarioId | string;
};

/** 区划 UI 展示名：优先 API display_name，回退 name */
export function salvageRegionDisplayName(
  region: Pick<SalvageRegion, 'display_name' | 'name' | 'circuit_name'>,
): string {
  const display = region.display_name?.trim();
  if (display) return display;
  return region.name;
}

function resolveScenarioId(ctx?: SalvageAdapterContext): ScenarioId {
  const id = ctx?.scenarioId?.trim();
  if (id && getScenario(id)) return id as ScenarioId;
  return 'ming_wanli';
}

const SALVAGE_STATE_KNOWN_KEYS = new Set([
  'turn', 'metrics', 'treasury', 'directives', 'pending_count', 'pending_decisions',
  'last_decree', 'last_report', 'previous_summary', 'max_decree_issues', 'issue_log_limit',
  'structured_directives', 'ending', 'ministers', 'archived_ministers', 'consorts',
  'issues', 'closed_this_turn', 'regions', 'armies', 'arms_stock', 'troop_rates',
  'departments', 'technologies', 'map_nodes', 'buildings', 'budget', 'legacies',
  'victory_status', 'region_warning', 'army_warning', 'power_warning', 'powers',
  'preset_trees', 'events', 'secret_orders',
]);

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function asArray<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

function flattenBuildingsFromMapNodes(nodes: SalvageMapNode[]): SalvageGameState['buildings'] {
  const out: NonNullable<SalvageGameState['buildings']> = [];
  const seen = new Set<string>();
  for (const node of nodes) {
    for (const b of node.buildings || []) {
      if (!b.id || seen.has(b.id)) continue;
      seen.add(b.id);
      out.push({
        ...b,
        region_id: b.region_id || node.region?.id || node.id,
      });
    }
  }
  return out;
}

function enrichMapNodesWithPowers(
  nodes: SalvageMapNode[],
  powers: SalvagePower[],
): SalvageMapNode[] {
  if (!powers.length) return nodes;
  const byId = new Map(powers.map((p) => [p.id, p]));
  return nodes.map((node) => {
    const powerId = node.region?.controlled_by;
    if (!powerId || !byId.has(powerId)) return node;
    return { ...node, power: byId.get(powerId) };
  });
}

/**
 * 将 web_app.state_payload() 规范为完整 SalvageGameState，不丢弃未知字段。
 */
export function normalizeSalvageGameState(raw: unknown): SalvageGameState {
  const r = asRecord(raw);
  const mapNodes = asArray<SalvageMapNode>(r.map_nodes);
  const powers = asArray<SalvagePower>(r.powers);
  const enrichedNodes = enrichMapNodesWithPowers(mapNodes, powers);

  let buildings = asArray<SalvageBuilding>(r.buildings);
  if (!buildings.length && enrichedNodes.length) {
    buildings = flattenBuildingsFromMapNodes(enrichedNodes) || [];
  }

  const normalized: SalvageGameState = {
    turn: asRecord(r.turn) as SalvageGameState['turn'],
    metrics: asRecord(r.metrics) as Record<string, number>,
    treasury: r.treasury != null ? String(r.treasury) : '',
    directives: asArray(r.directives) as SalvageGameState['directives'],
    pending_count: Number(r.pending_count ?? 0),
    pending_decisions: asArray(r.pending_decisions),
    last_decree: String(r.last_decree || ''),
    last_report: String(r.last_report || ''),
    previous_summary: String(r.previous_summary || ''),
    max_decree_issues: Number(r.max_decree_issues ?? 10),
    issue_log_limit: Number(r.issue_log_limit ?? 6),
    structured_directives: asArray(r.structured_directives) as SalvageGameState['structured_directives'],
    ending: r.ending == null ? null : (r.ending as SalvageGameState['ending']),
    ministers: asArray(r.ministers) as SalvageGameState['ministers'],
    archived_ministers: asArray(r.archived_ministers) as SalvageGameState['archived_ministers'],
    consorts: asArray(r.consorts) as SalvageGameState['consorts'],
    issues: asArray(r.issues),
    closed_this_turn: asArray(r.closed_this_turn) as SalvageGameState['closed_this_turn'],
    regions: asArray(r.regions) as SalvageGameState['regions'],
    armies: asArray(r.armies) as SalvageGameState['armies'],
    arms_stock: asArray(r.arms_stock) as SalvageGameState['arms_stock'],
    troop_rates: asRecord(r.troop_rates) as Record<string, number>,
    departments: asArray(r.departments) as SalvageGameState['departments'],
    technologies: asArray(r.technologies) as SalvageGameState['technologies'],
    map_nodes: enrichedNodes,
    buildings,
    budget: r.budget as SalvageBudget | undefined,
    legacies: asArray<SalvageLegacy>(r.legacies),
    victory_status: asRecord(r.victory_status) as SalvageVictoryStatus,
    region_warning: String(r.region_warning || ''),
    army_warning: String(r.army_warning || ''),
    power_warning: String(r.power_warning || ''),
    powers,
    preset_trees: r.preset_trees as SalvagePresetTrees | undefined,
    events: asArray(r.events),
    secret_orders: asArray(r.secret_orders),
  };

  for (const [key, value] of Object.entries(r)) {
    if (!SALVAGE_STATE_KNOWN_KEYS.has(key)) {
      normalized[key] = value;
    }
  }
  return normalized;
}

/** 流式结算 partial state 与已有快照合并（保留未返回字段） */
export function mergeSalvageGameState(
  prev: SalvageGameState | undefined,
  partial: unknown,
): SalvageGameState {
  if (!prev) return normalizeSalvageGameState(partial);
  const p = asRecord(partial);
  const hasPayloadShape =
    'turn' in p || 'regions' in p || 'map_nodes' in p || 'budget' in p || 'metrics' in p;
  if (!hasPayloadShape) return prev;
  return normalizeSalvageGameState({ ...prev, ...p });
}

export function parsePendingDecisions(raw: unknown): MingPendingDecision[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((row, i) => {
    const d = row as Record<string, unknown>;
    const options = Array.isArray(d.options)
      ? d.options.map((o) => {
          const opt = o as Record<string, unknown>;
          return {
            label: String(opt.label || ''),
            hint: String(opt.hint || ''),
          };
        })
      : [];
    return {
      idx: Number(d.idx ?? i),
      title: String(d.title || '亲裁'),
      context: String(d.context || ''),
      options,
    };
  });
}

function parseSalvageIssueRow(row: Record<string, unknown>): MingSalvageIssue {
  return {
    id: Number(row.id || 0),
    kind: String(row.kind || 'situation'),
    title: String(row.title || '未命名局势'),
    bar_value: Math.max(0, Math.min(100, Number(row.bar_value ?? 50))),
    bar_good_meaning: String(row.bar_good_meaning || '向好'),
    bar_bad_meaning: String(row.bar_bad_meaning || '恶化'),
    stage_text: String(row.stage_text || ''),
    phase: row.phase ? String(row.phase) : undefined,
    severity: row.severity != null ? Number(row.severity) : undefined,
    tags: Array.isArray(row.tags) ? row.tags.map(String) : undefined,
    inertia: row.inertia != null ? Number(row.inertia) : undefined,
    resolve_condition: row.resolve_condition ? String(row.resolve_condition) : undefined,
    fail_condition: row.fail_condition ? String(row.fail_condition) : undefined,
    ongoing_text: row.ongoing_text ? String(row.ongoing_text) : undefined,
    assignee: row.assignee ? String(row.assignee) : undefined,
    status: row.status ? String(row.status) : undefined,
    origin_kind: row.origin_kind ? String(row.origin_kind) : undefined,
    origin_ref: row.origin_ref ? String(row.origin_ref) : undefined,
    is_manual: Boolean(row.is_manual),
    duration_turns: row.duration_turns != null ? Number(row.duration_turns) : undefined,
    goal: row.goal ? String(row.goal) : undefined,
    budget_pool: row.budget_pool != null ? Number(row.budget_pool) : undefined,
    budget_source: row.budget_source ? String(row.budget_source) : undefined,
    death_authority: Boolean(row.death_authority),
    origin_turn: row.origin_turn != null ? Number(row.origin_turn) : undefined,
  };
}

export function parseSalvageIssues(raw: SalvageGameState): MingSalvageIssue[] {
  const rows = raw.issues || [];
  return rows
    .filter((row) => {
      const kind = String(row.kind || '');
      return kind === 'situation' || kind === 'initiative';
    })
    .map(parseSalvageIssueRow);
}

function parseClosedIssues(raw: SalvageGameState): MingClosedIssue[] {
  const rows = raw.closed_this_turn || [];
  return rows.map((row) => ({
    id: Number(row.id || 0),
    kind: String(row.kind || 'situation'),
    title: String(row.title || ''),
    status: String(row.status || 'resolved'),
    bar_value: Number(row.bar_value ?? 0),
    bar_good_meaning: String(row.bar_good_meaning || ''),
    bar_bad_meaning: String(row.bar_bad_meaning || ''),
    closed_turn: Number(row.closed_turn || 0),
    stage_text: String(row.stage_text || ''),
    effect: (row.effect as Record<string, unknown>) || {},
  }));
}

function parseEnding(raw: SalvageGameState): MingEnding | null {
  const e = raw.ending;
  if (!e) return null;
  const timeline = Array.isArray(e.timeline)
    ? e.timeline.map((row) => ({
        turn: Number(row.turn || 0),
        year: Number(row.year || 0),
        period: Number(row.period || 0),
        decree_brief: String(row.decree_brief || ''),
        effect_brief: String(row.effect_brief || ''),
        chapter: String(row.chapter || ''),
      }))
    : [];
  return {
    status: String(e.status || ''),
    label: String(e.label || '结局'),
    summary: String(e.summary || ''),
    score: typeof e.score === 'number' ? e.score : undefined,
    score_label_zh: e.score_label_zh ? String(e.score_label_zh) : undefined,
    timeline,
  };
}

function parseStructuredDirectives(raw: SalvageGameState): MingStructuredDirective[] {
  const rows = raw.structured_directives || [];
  return rows.map((row) => ({
    id: Number(row.id || 0),
    template_id: String(row.template_id || ''),
    category: String(row.category || ''),
    title: String(row.title || ''),
    fields: (row.fields as Record<string, string>) || {},
    compiled_text: String(row.compiled_text || ''),
    settlement_hint: String(row.settlement_hint || ''),
    status: String(row.status || 'draft'),
  }));
}

const SALVAGE_SESSION_ID = 'ming_salvage_singleton';

export function salvageSessionId(): string {
  return SALVAGE_SESSION_ID;
}

function turnLabelFromSalvage(turn: SalvageGameState['turn']): string {
  const year = Number(turn?.year || 0);
  const period = Number(turn?.period || 1);
  if (year > 0) return `${year}年${period}月`;
  const n = Number(turn?.turn || 1);
  return `第${n}月`;
}

function normalizePhase(raw: string | undefined): MingTurnPhase {
  const p = (raw || 'summoning').trim().toLowerCase();
  if (p === 'reviewing' || p === 'awaiting_decision' || p === 'issued' || p === 'summoning') {
    return p;
  }
  return 'summoning';
}

export function adaptSalvageToMingGameState(
  raw: SalvageGameState | unknown,
  ctx?: SalvageAdapterContext,
): MingGameState {
  const salvage = normalizeSalvageGameState(raw);
  const scenarioId = resolveScenarioId(ctx);
  const turn = salvage.turn || {};
  const directives: MingDirective[] = (salvage.directives || []).map((d) => ({
    id: Number(d.id),
    text: String(d.text || ''),
    status: (d.status || 'draft') as MingDirective['status'],
    actor: d.actor,
    notes: d.notes,
    turn: Number(turn.turn || 1),
  }));
  return {
    session_id: SALVAGE_SESSION_ID,
    scenario_id: scenarioId,
    turn: {
      turn: Number(turn.turn || 1),
      label: turnLabelFromSalvage(turn),
    },
    turn_phase: normalizePhase(turn.phase),
    metrics: { ...(salvage.metrics || {}) },
    flags: {},
    region_status: buildRegionStatusFromSalvage(salvage),
    directives,
    structured_directives: parseStructuredDirectives(salvage),
    pending_count: Number(salvage.pending_count ?? 0),
    max_decree_issues: Number(salvage.max_decree_issues ?? 10),
    issue_log_limit: Number(salvage.issue_log_limit ?? 6),
    last_decree: String(salvage.last_decree || ''),
    last_report: String(salvage.last_report || ''),
    previous_summary: String(salvage.previous_summary || ''),
    pending_decisions: parsePendingDecisions(salvage.pending_decisions),
    issues: parseSalvageIssues(salvage),
    closed_this_turn: parseClosedIssues(salvage),
    ending: parseEnding(salvage),
    ended: Boolean(salvage.ending) || Boolean(salvage.ending?.status),
    treasury: salvage.treasury || '',
    region_warning: salvage.region_warning || '',
    army_warning: salvage.army_warning || '',
    power_warning: salvage.power_warning || '',
    victory_status: salvage.victory_status,
    powers: salvage.powers,
    legacies: salvage.legacies,
    budget: salvage.budget,
    regions: salvage.regions,
    armies: salvage.armies,
    buildings: salvage.buildings,
    departments: salvage.departments,
    technologies: salvage.technologies,
    map_nodes: salvage.map_nodes,
    preset_trees: salvage.preset_trees,
    events: salvage.events,
    archived_ministers: salvage.archived_ministers,
    consorts: salvage.consorts,
  };
}

function buildRegionStatusFromSalvage(salvage: SalvageGameState): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const region of salvage.regions || []) {
    if (!region.id) continue;
    out[region.id] = {
      name: salvageRegionDisplayName(region),
      unrest: region.unrest,
      public_support: region.public_support,
      controlled_by: region.controlled_by,
      status: region.status,
    };
  }
  return out;
}

export function buildNationFromSalvage(
  raw: SalvageGameState | unknown,
  ctx?: SalvageAdapterContext,
): NationState {
  const salvage = normalizeSalvageGameState(raw);
  const turn = salvage.turn || {};
  const year = Number(turn.year || 0);
  const scenarioId = resolveScenarioId(ctx);
  const metrics = mapSalvageMetrics(salvage.metrics, scenarioId);
  const preview = getScenario(scenarioId)?.nationState;

  let dynasty = preview?.dynasty ?? '明';
  let reignTitle = preview?.reignTitle ?? '万历';

  if (scenarioId === 'song_xining_v2' || (year >= 1068 && year <= 1086)) {
    dynasty = '北宋';
    reignTitle = '熙宁';
  } else if (scenarioId === 'ming_wanli' || year >= 1573) {
    if (year >= 1573 && year <= 1620) reignTitle = '万历';
    else if (year >= 1627 && year <= 1644) reignTitle = '崇祯';
    else if (year > 0) reignTitle = '晚明';
  }

  return {
    dynasty,
    reignTitle,
    yearLabel: turnLabelFromSalvage(turn),
    metrics,
  };
}

/** 将 salvage 大臣名册与门户 roster 按姓名对齐 */
export function mergeSalvageMinisters(
  raw: SalvageGameState | unknown,
  ctx?: SalvageAdapterContext,
): Character[] {
  const salvage = normalizeSalvageGameState(raw);
  const base = getScenario(resolveScenarioId(ctx))?.characters || [];
  const byName = new Map(base.map((c) => [c.name, c]));
  const byId = new Map(base.map((c) => [c.id, c]));
  const salvageRows = salvage.ministers || [];
  if (!salvageRows.length) {
    return base.filter((c) => c.consultable !== false && c.id !== 'emperor');
  }
  const out: Character[] = [];
  for (const row of salvageRows) {
    if (row.office_type === '后宫') continue;
    if (row.status && row.status !== 'active') continue;
    const portraitKey = (row.portrait_id || row.id || '').trim();
    const hit =
      byName.get(row.name) ||
      (portraitKey ? byId.get(portraitKey) : undefined);
    if (hit) {
      out.push(hit);
      continue;
    }
    out.push({
      id: row.name,
      name: row.name,
      title: row.office || '朝臣',
      faction: 'other',
      ideologyTags: row.faction ? [row.faction] : [],
      avatarColor: '#8b4513',
      consultable: true,
      brief: row.summary || '',
    });
  }
  return out.length ? out : base.filter((c) => c.consultable !== false && c.id !== 'emperor');
}

export function resolveMinisterName(characterId: string, characters: Character[]): string {
  const hit = characters.find((c) => c.id === characterId);
  if (hit?.name) return hit.name;
  return characterId;
}

export function formatSalvageApiError(raw: string, status: number): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === 'string') {
      if (status === 412) {
        return `明代引擎未就绪（LLM 配置）：${detail}。请先在 ming-salvage-sim-main 配置 API Key 并启动 8010 服务。`;
      }
      if (status === 404) {
        return `无法连接 ming-salvage 引擎（${status}）。请先启动：cd ming-salvage-sim-main && python -m uvicorn web_app:app --port 8010`;
      }
      return detail;
    }
    if (detail && typeof detail === 'object') {
      const msg = (detail as { message?: string }).message;
      if (msg) return msg;
    }
  } catch {
    /* fall through */
  }
  if (status === 0 || raw.includes('Failed to fetch')) {
    return '无法连接 ming-salvage 引擎（:8010）。请确认已启动 web_app，且 frontend 已配置 MING_SALVAGE_PROXY_URL。';
  }
  return raw || `ming-salvage API 失败：${status}`;
}
