import type {
  SalvageArmy,
  SalvageBudget,
  SalvageBuilding,
  SalvageDepartment,
  SalvageEvent,
  SalvageLegacy,
  SalvageMapNode,
  SalvageMinister,
  SalvagePower,
  SalvagePresetTrees,
  SalvageRegion,
  SalvageTechnology,
  SalvageVictoryStatus,
} from './salvageStateTypes';

export type MingTurnPhase =
  | 'summoning'
  | 'reviewing'
  | 'awaiting_decision'
  | 'issued';

export const MING_PHASE_LABEL: Record<MingTurnPhase, string> = {
  summoning: '召见',
  reviewing: '核定',
  awaiting_decision: '亲裁',
  issued: '已颁诏',
};

export type MingChatSuggestion = {
  label: string;
  text: string;
  prefix?: boolean;
};

export type MingChatMessage = {
  role: 'user' | 'minister' | string;
  content: string;
  pending?: boolean;
};

export type MingMinisterChatDone = {
  answer: string;
  history: MingChatMessage[];
  suggestions: MingChatSuggestion[];
  directives?: MingDirective[];
  pending_count?: number;
  court_action?: string;
  next_minister?: string;
  proposed_directive?: MingDirective | null;
  secret_order_id?: number;
};

export type MingDirective = {
  id: number;
  text: string;
  status: 'pending' | 'draft' | 'rejected' | 'issued';
  actor?: string;
  notes?: string;
  turn?: number;
};

export type MingDecisionOption = {
  label: string;
  hint: string;
};

export type MingPendingDecision = {
  idx: number;
  title: string;
  context: string;
  options: MingDecisionOption[];
};

export type MingSalvageIssue = {
  id: number;
  kind: 'situation' | 'initiative' | string;
  title: string;
  bar_value: number;
  bar_good_meaning: string;
  bar_bad_meaning: string;
  stage_text: string;
  phase?: string;
  severity?: number;
  tags?: string[];
  inertia?: number;
  resolve_condition?: string;
  fail_condition?: string;
  ongoing_text?: string;
  assignee?: string;
  status?: string;
  origin_kind?: string;
  origin_ref?: string;
  is_manual?: boolean;
  duration_turns?: number;
  goal?: string;
  budget_pool?: number;
  budget_source?: string;
  death_authority?: boolean;
  origin_turn?: number;
};

export type MingClosedIssue = {
  id: number;
  kind: string;
  title: string;
  status: 'resolved' | 'failed' | 'dropped' | string;
  bar_value: number;
  bar_good_meaning: string;
  bar_bad_meaning: string;
  closed_turn: number;
  stage_text: string;
  effect: Record<string, unknown>;
};

export type MingStructuredDirectiveFieldSpec = {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'number';
  option_source?: string;
  required?: boolean;
  required_when?: { field: string; values: string[] };
  placeholder?: string;
  options?: string[];
};

export type MingStructuredDirectiveTemplate = {
  id: string;
  label: string;
  category: string;
  settlement_hint: string;
  compiled_text: string;
  fields: MingStructuredDirectiveFieldSpec[];
};

export type MingStructuredDirective = {
  id: number;
  template_id: string;
  category: string;
  title: string;
  fields: Record<string, string>;
  compiled_text: string;
  settlement_hint: string;
  status: string;
};

export type MingSecretOrder = {
  id: number;
  turn_issued: number;
  due_turn: number;
  year_issued: number;
  period_issued: number;
  minister_name: string;
  title: string;
  content: string;
  tags: string[];
  importance: number;
  status: 'active' | 'pending_review' | 'done' | 'failed' | 'cancelled' | string;
  result: string;
  sim_note: string;
  turn_closed: number | null;
};

export type MingExtractionData = {
  turn: number;
  year: number;
  period: number;
  exists: boolean;
  narrative?: string;
  extractor_output?: Record<string, unknown>;
};

export type MingHistoryTurnItem = {
  turn: number;
  year: number;
  period: number;
  has_report: boolean;
  has_extraction: boolean;
  has_directive: boolean;
};

export type MingHistoryDetail = {
  turn: number;
  exists: boolean;
  year: number;
  period: number;
  report: string;
  decree_text: string;
  directives: Array<Record<string, unknown>>;
  extraction: MingExtractionData | null;
};

export type MingEndingTimelineItem = {
  turn: number;
  year: number;
  period: number;
  decree_brief: string;
  effect_brief: string;
  chapter: string;
};

export type MingEnding = {
  status: string;
  label: string;
  summary: string;
  timeline: MingEndingTimelineItem[];
  score?: number;
  score_label_zh?: string;
};

export type MingGameState = {
  session_id: string;
  scenario_id: string;
  turn: { turn: number; label: string };
  turn_phase: MingTurnPhase;
  metrics: Record<string, number>;
  flags: Record<string, boolean>;
  region_status: Record<string, unknown>;
  directives: MingDirective[];
  structured_directives: MingStructuredDirective[];
  pending_count: number;
  max_decree_issues?: number;
  last_decree: string;
  last_report: string;
  previous_summary: string;
  pending_decisions: MingPendingDecision[];
  issues: MingSalvageIssue[];
  closed_this_turn: MingClosedIssue[];
  ending: MingEnding | null;
  ended: boolean;
  /** 自 salvage state_payload 透传，供不读 salvageRaw 的 UI */
  treasury?: string;
  region_warning?: string;
  army_warning?: string;
  power_warning?: string;
  victory_status?: SalvageVictoryStatus;
  powers?: SalvagePower[];
  legacies?: SalvageLegacy[];
  budget?: SalvageBudget;
  regions?: SalvageRegion[];
  armies?: SalvageArmy[];
  buildings?: SalvageBuilding[];
  departments?: SalvageDepartment[];
  technologies?: SalvageTechnology[];
  map_nodes?: SalvageMapNode[];
  preset_trees?: SalvagePresetTrees;
  events?: SalvageEvent[];
  archived_ministers?: SalvageMinister[];
  consorts?: SalvageMinister[];
  issue_log_limit?: number;
};

export type MingCommandModal =
  | 'none'
  | 'report'
  | 'extraction'
  | 'secret_orders'
  | 'history'
  | 'edict'
  | 'state'
  | 'court_chat'
  | 'ending'
  | 'menu';

export type MingSaveEntry = {
  name: string;
  size: number;
  mtime: number;
  label?: string;
  kind?: string;
  scenario_prefix?: string;
};

export type MingLlmConfig = {
  base_url: string;
  model: string;
  max_tokens: number;
  timeout_seconds: number;
  connect_timeout_seconds: number;
  read_timeout_seconds: number;
  thinking_level: string;
  advanced_model: string;
  advanced_base_url: string;
  has_advanced_api_key: boolean;
  advanced_thinking_level: string;
  has_api_key: boolean;
};

export type MingGameSettings = {
  hitl_min_decisions: number;
  court_chat_debate_rounds: number;
  court_chat_stream_speed: number;
  max_decree_issues: number;
  issue_log_limit: number;
  secret_order_person_limit: number;
  secret_order_total_limit: number;
  character_limit: number;
  minister_temperature: number;
  minister_top_p: number;
  simulator_temperature: number;
  simulator_top_p: number;
  extractor_temperature: number;
  extractor_top_p: number;
};

export type MingCourtChatMessage = {
  role: 'emperor' | 'minister' | 'conclusion';
  speaker: string;
  content: string;
  displayContent?: string;
  options?: string[];
};

export type MingCourtChatResponse = {
  turn: number;
  year: number;
  period: number;
  history: MingCourtChatMessage[];
};

export type MingSettleStreamOutcome =
  | { kind: 'done'; data: Record<string, unknown> }
  | { kind: 'decisions'; data: Record<string, unknown> }
  | { kind: 'error'; message: string };
