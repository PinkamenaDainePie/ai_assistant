export type ApiConfig = {
  baseUrl?: string;
};

/**
 * 未设置 NEXT_PUBLIC_API_BASE_URL 时：在浏览器里走同源 `/api/backend/*`（由 next.config rewrites 转到 FastAPI），
 * 避免部分环境直连 127.0.0.1:8000 出现 Failed to fetch。SSR/Node 仍直连 8000。
 */
/** 从 FastAPI 等 JSON 错误体里抽出可读说明 */
function formatApiErrorBody(status: number, raw: string): string {
  const trimmed = (raw || '').trim();
  if (!trimmed) return '';
  try {
    const j = JSON.parse(trimmed) as { detail?: unknown };
    const d = j?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d))
      return d
        .map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: unknown }).msg) : JSON.stringify(x)))
        .join('; ');
    if (d != null) return JSON.stringify(d);
  } catch {
    /* 非 JSON 则原样返回（截断） */
  }
  return trimmed.length > 800 ? `${trimmed.slice(0, 800)}…` : trimmed;
}

function getBaseUrl(config?: ApiConfig): string {
  if (config?.baseUrl) {
    return config.baseUrl.replace(/\/+$/, '');
  }
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env) {
    return env.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/backend`.replace(/\/+$/, '');
  }
  const ssrBackend =
    process.env.BACKEND_PROXY_URL || 'http://127.0.0.1:8000';
  return ssrBackend.replace(/\/+$/, '');
}

async function postJson<T>(
  path: string,
  payload: Record<string, unknown>,
  config?: ApiConfig,
): Promise<T> {
  const base = getBaseUrl(config);
  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const hint =
      err instanceof TypeError && String(err.message).includes('fetch')
        ? `无法连接后端（请确认已启动：${base}）。`
        : '';
    throw new Error(
      `${hint}网络请求失败 ${path}：${err instanceof Error ? err.message : String(err)}`,
    );
  }
  if (!resp.ok) {
    let detail = '';
    try {
      detail = await resp.text();
    } catch {
      detail = '';
    }
    const readable = formatApiErrorBody(resp.status, detail);
    throw new Error(
      readable
        ? `API ${path} failed: ${resp.status} — ${readable}`
        : `API ${path} failed: ${resp.status}`,
    );
  }
  return (await resp.json()) as T;
}

async function getJson<T>(path: string, config?: ApiConfig): Promise<T> {
  const base = getBaseUrl(config);
  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, { method: 'GET' });
  } catch (err) {
    const hint =
      err instanceof TypeError && String(err.message).includes('fetch')
        ? `无法连接后端（请确认已启动：${base}）。`
        : '';
    throw new Error(
      `${hint}GET 请求失败 ${path}：${err instanceof Error ? err.message : String(err)}`,
    );
  }
  if (!resp.ok) {
    let detail = '';
    try {
      detail = await resp.text();
    } catch {
      detail = '';
    }
    const readable = formatApiErrorBody(resp.status, detail);
    throw new Error(
      readable
        ? `API ${path} failed: ${resp.status} — ${readable}`
        : `API ${path} failed: ${resp.status}`,
    );
  }
  return (await resp.json()) as T;
}

/** 防止后端或 LLM 长时间无响应导致界面一直处于「加载中」无法操作 */
export async function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  label: string,
): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(
        new Error(
          `${label} 超时（>${Math.round(ms / 1000)} 秒）。请确认后端已启动、Next 代理 /api/backend 可达；若首次调用大模型较慢可稍后重试。`,
        ),
      );
    }, ms);
  });
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }
}

export type ChatRequest = {
  character_id: string;
  message: string;
  metrics?: Record<string, number>;
  top_k?: number;
};
export type ChatResponse = {
  reply: string;
  references?: Array<{
    source?: string;
    section?: string;
    preview?: string;
  }>;
  retrieved_count?: number;
};

export type TutorChatTurn = { role: 'user' | 'assistant'; content: string };

export type TutorChatRequest = {
  message: string;
  history?: TutorChatTurn[];
  top_k?: number;
};

export type TutorCitation = {
  id?: string;
  title?: string;
  era?: string;
  summary?: string;
};

export type TutorChatResponse = {
  reply: string;
  citations: TutorCitation[];
  retrieved_count: number;
  graph_backend: string;
  neo4j_connected: boolean;
};

export type EventRollRequest = {
  session_id: string;
  root_dir?: string;
  turn_id: number;
  seed?: number;
};
export type EventRollResponse = {
  rolled: boolean;
  reason?: string;
  session_id?: string;
  turn_id?: number;
  event_instance_id?: string;
  event?: {
    id: string;
    title: string;
    description?: string;
    category?: string;
    choices?: Array<{ id: string; text: string; tags?: string[] }>;
  };
};

export type EventChooseRequest = {
  session_id: string;
  event_instance_id: string;
  choice_id: string;
};
export type EventChooseResponse = {
  ok: boolean;
  reason?: string;
  event_id?: string;
  choice_id?: string;
  choice_text?: string;
  effects_applied?: Array<{ action: string; key: string; value: number }>;
  state_metrics?: Record<string, number>;
  outcome_narrative?: string;
};

export type QuarterSettleRequest = {
  session_id: string;
  /** 全局对局 UUID，与 ADP Workflow A/B session 对齐 */
  game_session_id?: string;
  root_dir?: string;
  edict_text?: string;
  edict_category?: string;
  quarters?: number;
  enable_layer3_llm?: boolean;
  event_effects_json?: string;
  debate_choice?: string;
  minister_name?: string;
  minister_advice_text?: string;
  /** 显式承办大臣；不传则从诏书原文匹配大臣表姓名 */
  edict_executor_name?: string;
  edict_executor_abilities?: Record<string, number>;
  use_legacy_category_multiplier?: boolean;
  auto_scale_small_resource?: boolean;
  /** 覆盖环境变量 POLICY_CANDIDATE_MODE：off | shadow | select | parse_only */
  policy_candidate_mode?: string;
  /** select 模式下采纳的 candidate_id */
  selected_candidate_id?: string;
};

export type EdictParseRequest = {
  edict_text: string;
  edict_category?: string;
  root_dir?: string;
  parse_mode?: 'effects' | 'candidate';
  enable_layer3_llm?: boolean;
  edict_executor_name?: string;
  edict_executor_abilities?: Record<string, number>;
};

export type EdictParseResponse = {
  effects: Array<Record<string, unknown>>;
  trace: Record<string, unknown>;
  semantic_frame?: Record<string, unknown>;
  policy_candidates?: Array<Record<string, unknown>>;
  rejected_candidates?: Array<Record<string, unknown>>;
  candidate_scores?: Array<Record<string, unknown>>;
  selected_candidate?: Record<string, unknown>;
  effect_preview?: Array<Record<string, unknown>>;
  policy_candidate_trace?: Record<string, unknown>;
};

export type MinisterAdviceRequest = {
  character_id?: string;
  message: string;
  history?: Array<{ role: string; content: string }>;
  top_k?: number;
  metrics?: Record<string, number>;
  minister_display_name?: string;
};

export type MinisterAdviceResponse = {
  reply: string;
  references: Array<{ source?: string; section?: string; preview?: string }>;
  retrieved_count: number;
  question_classification: Record<string, unknown>;
  stance: Record<string, unknown>;
  advice_candidates: Array<Record<string, unknown>>;
  candidate_scores: Array<Record<string, unknown>>;
  parse_warning?: string;
};
/** 诏书双轨叙事（后端写入 `input.decree_narrative`） */
export type DecreeNarrativePack = {
  track: string;
  mode: string;
  segments: string[];
  summary_zh: string;
};

export type QuarterSettleResponse = {
  input: Record<string, unknown> & {
    decree_narrative?: DecreeNarrativePack;
    policy_candidate_trace?: Record<string, unknown>;
  };
  reports: Array<Record<string, unknown>>;
  final_state: {
    quarter_index: number;
    metrics: Record<string, number>;
    flags: Record<string, boolean>;
  };
  growth_focus_prompt?: {
    next_quarter_index: number;
    focus_trees: Array<{ key: string; label: string }>;
    already_chosen: boolean;
  };
  /** 诏书委派任务已入队 */
  delegation_enqueued?: {
    task_id: string;
    action_id?: string;
    executor_display?: string;
    phases_total?: number;
  } | null;
  task_quarter_end?: Record<string, unknown>;
};

export type QuarterStartRequest = {
  session_id: string;
  game_session_id?: string;
  root_dir?: string;
  edict_text?: string;
  edict_category?: string;
  player_actions?: string[];
  enable_layer3_llm?: boolean;
};
export type GrowthPointWallet = {
  military: number;
  management: number;
  politics: number;
  scholarship: number;
  generic: number;
};
export type EdictPlaybookRef = {
  domain: string;
  task_key: string;
};

export type WarArcState = {
  arc_id: string;
  label_zh: string;
  phase_id: string;
  phase_label_zh: string;
  phase_quarter: number;
  pressure: Record<string, number>;
  outcome?: string | null;
  total_edict_contributions?: number;
};

export type WarArcsSnapshot = {
  arcs: Record<string, WarArcState>;
};

export type QuarterStartResponse = {
  ok: boolean;
  session_id: string;
  quarter_index: number;
  previous_task_results: Array<Record<string, unknown>>;
  new_tasks: Array<Record<string, unknown>>;
  task_history_tail: Array<Record<string, unknown>>;
  task_history?: Array<Record<string, unknown>>;
  quarter_report: Record<string, unknown> & {
    /** 朝政纪要标题，如「熙宁二年 秋朝政纪要——…」 */
    title_zh?: string;
    headline_zh?: string;
    highlights_zh?: string[];
    narrative_mode?: string;
    memorial?: Record<string, unknown>;
  };
  final_state: {
    quarter_index: number;
    metrics: Record<string, number>;
    flags: Record<string, boolean>;
  };
  growth_available_points: GrowthPointWallet;
  /** 各技能树累计投入点数（与 allocate_skills 返回的 skill_levels 同口径） */
  growth_cumulative_skill_points?: Record<string, number>;
  campaign_label_zh?: string;
  /** 玩家可下诏 playbook 白名单；国策图节点仅后端持有，不下发前端 */
  allowed_edict_playbooks?: EdictPlaybookRef[];
  campaign_end?: CampaignEndPayload;
  /** 上季 settle 缓存的 Workflow A 报告 */
  agent_flow_report?: Record<string, unknown>;
  /** 本局已归档季度总结（后端 session + 磁盘） */
  quarter_chapters?: Array<Record<string, unknown>>;
};

export type CampaignEndPayload = {
  kind: string;
  reason?: string;
  reason_zh?: string;
  prompt_zh?: string;
  can_continue_until_q?: number;
  epilogue?: {
    kind?: string;
    title_zh?: string;
    summary_zh?: string;
    quarter_index?: number;
    reform_skeleton_count?: number;
  };
};

export type CampaignMilestoneDecisionRequest = {
  session_id: string;
  decision: 'end' | 'continue';
};
export type CampaignMilestoneDecisionResponse = {
  ok: boolean;
  session_id: string;
  decision: string;
  milestone_continue: boolean;
};

export type EndingSummarySections = {
  life_chronicle_zh?: string;
  ending_scene_zh?: string;
  merits_demerits_zh?: string;
  temple_name_zh?: string;
  future_projection_zh?: string;
};

export type EndingSummaryReport = {
  ending_id?: string;
  ending_type?: string;
  score?: number;
  score_label_zh?: string;
  title_zh?: string;
  summary_zh?: string;
  sections?: EndingSummarySections;
  highlights_zh?: string[];
  history_compare_zh?: string;
  tone?: string;
  mode?: string;
};

export type EndingSummaryRequest = {
  session_id: string;
  game_session_id?: string;
  root_dir?: string;
  campaign_end?: CampaignEndPayload;
  scenario_id?: string;
  /** 浏览器 localStorage 归档的全局季总结，与后端合并后送 Workflow C */
  quarter_chapters?: Array<Record<string, unknown>>;
};

export type EndingSummaryResponse = {
  ok: boolean;
  session_id: string;
  ending_report: EndingSummaryReport;
  narrative_mode?: string;
  quarter_chapters_count?: number;
};

export type GrowthChooseFocusRequest = {
  session_id: string;
  /** 必须与本局 quarter/start / quarter/settle 使用的 root_dir 一致（song_xining 用 biaoge/song，万历用 biaoge），否则 growth 读到的季度索引与 focus 存储的 target_q 不匹配，导致 focus_not_chosen_for_quarter */
  root_dir?: string;
  focus_trees: string[];
};
export type GrowthChooseFocusResponse = {
  ok: boolean;
  session_id: string;
  quarter_index: number;
  focus_trees: string[];
};

export type GrowthAllocateSkillsRequest = {
  session_id: string;
  /** 必须与本局 quarter/start / quarter/settle 使用的 root_dir 一致（song_xining 用 biaoge/song），否则 growth 读到的 q 与之前 choose_focus 存的季度不一致 */
  root_dir?: string;
  allocation: Record<string, number>;
};
export type GrowthAllocateSkillsResponse = {
  ok: boolean;
  session_id: string;
  quarter_index: number;
  skill_levels: Record<string, number>;
  total_allocated: number;
  remaining_points?: Partial<GrowthPointWallet>;
};

export type TasksStateRequest = { session_id: string };
export type TasksStateResponse = {
  ok: boolean;
  session_id: string;
  active: Array<Record<string, unknown>>;
  history: Array<Record<string, unknown>>;
};

export type EventStateRequest = { session_id: string; root_dir?: string };
export type EventStateResponse = {
  ok: boolean;
  session_id: string;
  turn_id: number;
  quarter_index: number;
  metrics: Record<string, number>;
  flags: Record<string, boolean>;
  cooldowns: Record<string, number>;
  updated_ms: number;
};

export function postChat(
  payload: ChatRequest,
  config?: ApiConfig,
): Promise<ChatResponse> {
  return postJson('/chat', payload, config);
}

export function postTutorChat(
  payload: TutorChatRequest,
  config?: ApiConfig,
): Promise<TutorChatResponse> {
  return postJson('/tutor/chat', payload, config);
}

export function postEdictParse(
  payload: EdictParseRequest,
  config?: ApiConfig,
): Promise<EdictParseResponse> {
  return postJson('/edict/parse', payload, config);
}

export function postMinisterAdvice(
  payload: MinisterAdviceRequest,
  config?: ApiConfig,
): Promise<MinisterAdviceResponse> {
  return postJson('/minister/advice', payload, config);
}

export function postEventsRoll(
  payload: EventRollRequest,
  config?: ApiConfig,
): Promise<EventRollResponse> {
  return postJson('/events/roll', payload, config);
}

export function postEventsChoose(
  payload: EventChooseRequest,
  config?: ApiConfig,
): Promise<EventChooseResponse> {
  return postJson('/events/choose', payload, config);
}

export function postQuarterSettle(
  payload: QuarterSettleRequest,
  config?: ApiConfig,
): Promise<QuarterSettleResponse> {
  return postJson('/quarter/settle', payload, config);
}

export function postGrowthChooseFocus(
  payload: GrowthChooseFocusRequest,
  config?: ApiConfig,
): Promise<GrowthChooseFocusResponse> {
  return postJson('/growth/choose_focus', payload, config);
}

export function postQuarterStart(
  payload: QuarterStartRequest,
  config?: ApiConfig,
): Promise<QuarterStartResponse> {
  return postJson('/quarter/start', payload, config);
}

export function postGrowthAllocateSkills(
  payload: GrowthAllocateSkillsRequest,
  config?: ApiConfig,
): Promise<GrowthAllocateSkillsResponse> {
  return postJson('/growth/allocate_skills', payload, config);
}

export function postTasksState(
  payload: TasksStateRequest,
  config?: ApiConfig,
): Promise<TasksStateResponse> {
  return postJson('/tasks/state', payload, config);
}

export function postEventsState(
  payload: EventStateRequest,
  config?: ApiConfig,
): Promise<EventStateResponse> {
  return postJson('/events/state', payload, config);
}

// Semantic action aliases used by the frontend flow state machine.
export function startQuarter(
  payload: QuarterStartRequest,
  config?: ApiConfig,
): Promise<QuarterStartResponse> {
  return postQuarterStart(payload, config);
}

/** 预加载数值表到后端缓存；选剧本时 fire-and-forget 调用即可。 */
export function warmupNumericData(rootDir: string, config?: ApiConfig): Promise<{ ok: boolean }> {
  const q = encodeURIComponent(rootDir.trim());
  return getJson<{ ok: boolean }>(`/warmup?root_dir=${q}`, config);
}

export function drawQuarterTasks(
  payload: TasksStateRequest,
  config?: ApiConfig,
): Promise<TasksStateResponse> {
  return postTasksState(payload, config);
}

export function submitDecree(
  payload: QuarterSettleRequest,
  config?: ApiConfig,
): Promise<QuarterSettleResponse> {
  return postQuarterSettle(payload, config);
}

export function triggerRandomEvents(
  payload: EventRollRequest,
  config?: ApiConfig,
): Promise<EventRollResponse> {
  return postEventsRoll(payload, config);
}

export function submitEventChoice(
  payload: EventChooseRequest,
  config?: ApiConfig,
): Promise<EventChooseResponse> {
  return postEventsChoose(payload, config);
}

export function submitQuarterFocus(
  payload: GrowthChooseFocusRequest,
  config?: ApiConfig,
): Promise<GrowthChooseFocusResponse> {
  return postGrowthChooseFocus(payload, config);
}

export function settleQuarter(
  payload: QuarterSettleRequest,
  config?: ApiConfig,
): Promise<QuarterSettleResponse> {
  return postQuarterSettle(payload, config);
}

export function submitSkillPoints(
  payload: GrowthAllocateSkillsRequest,
  config?: ApiConfig,
): Promise<GrowthAllocateSkillsResponse> {
  return postGrowthAllocateSkills(payload, config);
}

export function getSkillCatalog(config?: ApiConfig): Promise<any> {
  return getJson('/growth/skill_catalog', config);
}

export function submitCampaignMilestoneDecision(
  payload: CampaignMilestoneDecisionRequest,
  config?: ApiConfig,
): Promise<CampaignMilestoneDecisionResponse> {
  return postJson('/campaign/milestone-decision', payload, config);
}

export function fetchEndingSummary(
  payload: EndingSummaryRequest,
  config?: ApiConfig,
): Promise<EndingSummaryResponse> {
  return postJson('/narrative/ending-summary', payload, config);
}
