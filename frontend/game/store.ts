import { create } from 'zustand';
import {
  NationState,
  Character,
  Memorial,
  LogEntry,
  NationMetricKey,
  MetricDeltaPreview,
} from './types';
import {
  mockNationState,
  mockCharacters,
  mockMemorials,
  mockLogs,
} from './mockData';
import {
  cloneScenarioNationState,
  getScenario,
  isSalvageScenario,
  resolveScenarioDataRoot,
  type ScenarioId,
} from './scenarios';
import { scoreEdictText } from './edictScoring';
import { applyBackendReportToMetrics } from './backendMetrics';
import {
  buildDecreeImpactLines,
  formatTaskQuarterEndLines,
  summarizeTaskSettlement,
  type TaskSettlementStats,
} from './settlementSummary';
import {
  drawQuarterTasks,
  settleQuarter as settleQuarterApi,
  startQuarter as startQuarterApi,
  submitDecree,
  submitEventChoice,
  submitQuarterFocus,
  submitSkillPoints,
  getSkillCatalog,
  submitCampaignMilestoneDecision,
  fetchEndingSummary,
  triggerRandomEvents,
  warmupNumericData,
  withTimeout,
  type CampaignEndPayload,
  type EndingSummaryReport,
  type GrowthPointWallet,
  type WarArcState,
  type WarArcsSnapshot,
} from '../lib/renwuApi';
import { getAccessToken } from '../lib/authStorage';
import { createPlaythrough, updatePlaythrough } from '../lib/classroomApi';
import { syncPlaythroughQuarterChapters } from './playthroughQuarterSync';

function syncPlaythroughQuarter(playthroughId: string, quarter: number) {
  if (!playthroughId || quarter <= 0) return;
  void updatePlaythrough(playthroughId, { current_quarter: quarter }).catch(() => undefined);
}

function pushPlaythroughQuarterChapters(
  playthroughId: string,
  sessionId: string,
  chapters: QuarterChapterRecord[],
) {
  if (!playthroughId || chapters.length === 0) return;
  syncPlaythroughQuarterChapters(playthroughId, chapters, sessionId);
}
import { formatQuarterReportForDisplay } from './quarterReportDisplay';
import type { LoadingKind } from './actionProgress';
import {
  getLocalQuarterChapters,
  syncQuarterChaptersFromBackend,
  type QuarterChapterRecord,
} from './quarterChapterArchive';

function syncSessionQuarterChapters(
  sessionId: string,
  backendChapters?: Array<Record<string, unknown>> | null,
): QuarterChapterRecord[] {
  return syncQuarterChaptersFromBackend(
    sessionId,
    (backendChapters || []) as QuarterChapterRecord[],
  );
}

function newGameSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `gs_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

interface UIState {
  isMemorialDrawerOpen: boolean;
  selectedQuarterChapterId?: string;
  isQuarterChapterDetailOpen: boolean;
  isAIDialogOpen: boolean;
  isTaskHistoryOpen: boolean;
  taskHistoryLoading: boolean;
  isQuarterReportOpen: boolean;
  /** 底部任务池面板是否展开 */
  isTaskPanelOpen: boolean;
  /** 问策：null=人物选择，非空=已进入与该 id 的对话 */
  aiDialogCharacterId: string | null;
}

export type GamePhase =
  | 'HOME'
  | 'QUARTER_MAIN'
  | 'DECREE_MODAL'
  | 'EVENT_RESOLUTION'
  | 'FOCUS_SELECTION'
  | 'SKILL_ALLOCATION'
  | 'QUARTER_SETTLEMENT'
  | 'CAMPAIGN_MILESTONE'
  | 'GAME_END';

export type SkillTreeName = 'military' | 'management' | 'politics' | 'scholarship';

export type SkillNode = {
  id: string;
  tree: SkillTreeName;
  name: string;
  description: string;
  currentLevel: number;
  maxLevel: number;
  cost: number;
  effects: string[];
};

export type SkillTreeState = {
  nodes: SkillNode[];
};

export type SkillUIState = {
  activeTree: SkillTreeName;
  pointWallet: GrowthPointWallet;
  skillTrees: Record<SkillTreeName, SkillTreeState>;
  openNodeDetailId?: string;
};

export type QuarterEvent = {
  eventInstanceId: string;
  eventId: string;
  title: string;
  description: string;
  choices: Array<{
    id: string;
    text: string;
    effectsText: string[];
  }>;
};

export type EdictPlaybookRef = {
  domain: string;
  task_key: string;
};

export type CampaignEpilogue = {
  kind: string;
  title_zh: string;
  summary_zh: string;
  quarter_index?: number;
  score?: number;
  score_label_zh?: string;
  sections?: EndingSummaryReport['sections'];
  highlights_zh?: string[];
  history_compare_zh?: string;
  ending_mode?: string;
};

const CAMPAIGN_MAX_QUARTERS = 40;

function readWarArcs(payload?: {
  war_arcs?: WarArcsSnapshot;
  quarter_report?: Record<string, unknown>;
}): WarArcState[] {
  const snap =
    payload?.war_arcs ||
    (payload?.quarter_report?.war_arcs as WarArcsSnapshot | undefined);
  const arcs = snap?.arcs || {};
  return Object.values(arcs).filter((a) => a && !a.outcome);
}

function readRegionStatus(
  finalState?: Record<string, unknown> | null,
): Record<string, { status?: string; status_hint_zh?: string; visible?: boolean }> {
  const raw = finalState?.region_status;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  return { ...(raw as Record<string, { status?: string; status_hint_zh?: string; visible?: boolean }>) };
}

function readCampaignEnd(out: {
  campaign_end?: CampaignEndPayload;
  quarter_report?: Record<string, unknown>;
}): CampaignEndPayload | undefined {
  const direct = out.campaign_end;
  if (direct && typeof direct === 'object') return direct;
  const fromReport = out.quarter_report?.campaign_end;
  if (fromReport && typeof fromReport === 'object') {
    return fromReport as CampaignEndPayload;
  }
  return undefined;
}

function epilogueFromEnd(end: CampaignEndPayload): CampaignEpilogue {
  const ep = (end.epilogue || {}) as Record<string, unknown>;
  return {
    kind: String(end.kind || ep.kind || 'unknown'),
    title_zh: String(ep.title_zh || end.reason_zh || '战役收束'),
    summary_zh: String(ep.summary_zh || end.reason_zh || ''),
    quarter_index: typeof ep.quarter_index === 'number' ? ep.quarter_index : undefined,
  };
}

function mergeEndingReport(
  base: CampaignEpilogue,
  report?: EndingSummaryReport | null,
): CampaignEpilogue {
  if (!report) return base;
  const sections = report.sections || {};
  const summary =
    String(report.summary_zh || '').trim() ||
    [sections.life_chronicle_zh, sections.ending_scene_zh].filter(Boolean).join('\n\n').slice(0, 800) ||
    base.summary_zh;
  return {
    ...base,
    title_zh: String(report.title_zh || base.title_zh),
    summary_zh: summary,
    score: typeof report.score === 'number' ? report.score : base.score,
    score_label_zh: report.score_label_zh || base.score_label_zh,
    sections,
    highlights_zh: report.highlights_zh || base.highlights_zh,
    history_compare_zh: report.history_compare_zh || base.history_compare_zh,
    ending_mode: report.mode || base.ending_mode,
  };
}

async function loadEndingSummaryForSession(args: {
  sessionId: string;
  gameSessionId: string;
  scenarioId: ScenarioId | null;
  campaignEnd?: CampaignEndPayload;
  baseEpilogue: CampaignEpilogue;
  quarterChapters?: QuarterChapterRecord[];
}): Promise<CampaignEpilogue> {
  const localChapters =
    args.quarterChapters && args.quarterChapters.length > 0
      ? args.quarterChapters
      : getLocalQuarterChapters(args.sessionId);
  try {
    const out = await withTimeout(
      fetchEndingSummary({
        session_id: args.sessionId,
        game_session_id: args.gameSessionId,
        root_dir: resolveScenarioDataRoot(args.scenarioId),
        campaign_end: args.campaignEnd,
        scenario_id: args.scenarioId || undefined,
        quarter_chapters: localChapters as Array<Record<string, unknown>>,
      }),
      320_000,
      '结局总结 Workflow C',
    );
    return mergeEndingReport(args.baseEpilogue, out.ending_report);
  } catch {
    return args.baseEpilogue;
  }
}

function resolveEndPhase(
  end: CampaignEndPayload | undefined,
  scenarioId: ScenarioId | null,
  fallbackPhase: GamePhase,
): { phase: GamePhase; epilogue?: CampaignEpilogue; milestonePrompt?: string } {
  if (scenarioId !== 'song_xining' || !end?.kind) {
    return { phase: fallbackPhase };
  }
  if (end.kind === 'game_over' || end.kind === 'calendar_end') {
    return { phase: 'GAME_END', epilogue: epilogueFromEnd(end) };
  }
  if (end.kind === 'milestone_available') {
    return {
      phase: 'CAMPAIGN_MILESTONE',
      epilogue: epilogueFromEnd(end),
      milestonePrompt: String(end.prompt_zh || end.reason_zh || ''),
    };
  }
  return { phase: fallbackPhase };
}

function parsePendingEventsFromReport(
  report?: Record<string, unknown>,
): QuarterEvent[] {
  const pe = report?.pending_event as Record<string, unknown> | undefined;
  if (!pe?.rolled || !pe?.event_instance_id || !pe?.event) return [];
  const ev = pe.event as Record<string, unknown>;
  const choices = (ev.choices as Array<Record<string, unknown>>) || [];
  return [
    {
      eventInstanceId: String(pe.event_instance_id),
      eventId: String(ev.id || ''),
      title: String(ev.title || ''),
      description: String(ev.description || ''),
      choices: choices.slice(0, 3).map((choice) => ({
        id: String(choice.id || ''),
        text: String(choice.text || ''),
        effectsText: (choice.tags as string[]) || [],
      })),
    },
  ];
}

export type QuarterSettlement = {
  reports: Array<Record<string, unknown>>;
  quarterReport?: Record<string, unknown>;
  /** @deprecated 展示请用 taskStats；保留原始上季结算记录 */
  completedTasks: Array<Record<string, unknown>>;
  /** @deprecated 展示请用 taskStats；保留当前任务池快照 */
  activeTasks: Array<Record<string, unknown>>;
  taskStats: TaskSettlementStats;
  decreeImpactLines: string[];
  delegationEnqueued?: {
    task_id?: string;
    title?: string;
    task_path?: string;
    phases_total?: number;
  } | null;
  eventSummary: string[];
  decreeText: string;
  decreeCategory: string;
  decreePublished: boolean;
  baselineMetrics: Record<string, number>;
  finalMetrics: Record<string, number>;
  /** 本季 settle 返回的 Workflow A 报告（secondary_effects_report） */
  agentFlowReport?: Record<string, unknown>;
  /** 本季任务季末结算（stall / completed / failed_expired） */
  taskQuarterEnd?: Record<string, unknown>;
  taskQuarterEndLines: string[];
};

function buildQuarterSettlementSnapshot(args: {
  reports: Array<Record<string, unknown>>;
  quarterReport?: Record<string, unknown>;
  previousTaskResults: Array<Record<string, unknown>>;
  currentTasks: Array<Record<string, unknown>>;
  eventSummary: string[];
  decreeText: string;
  decreeCategory: string;
  decreePublished: boolean;
  baselineMetrics: Record<string, number>;
  finalMetrics: Record<string, number>;
  delegationEnqueued?: QuarterSettlement['delegationEnqueued'];
  agentFlowReport?: Record<string, unknown>;
  taskQuarterEnd?: Record<string, unknown>;
}): QuarterSettlement {
  const taskStats = summarizeTaskSettlement(args.previousTaskResults, args.currentTasks);
  return {
    reports: args.reports,
    quarterReport: args.quarterReport,
    completedTasks: args.previousTaskResults,
    activeTasks: args.currentTasks,
    taskStats,
    decreeImpactLines: buildDecreeImpactLines({
      decreeText: args.decreeText,
      decreePublished: args.decreePublished,
      reports: args.reports,
      quarterReport: args.quarterReport,
      delegationEnqueued: args.delegationEnqueued,
    }),
    delegationEnqueued: args.delegationEnqueued,
    eventSummary: args.eventSummary,
    decreeText: args.decreeText,
    decreeCategory: args.decreeCategory,
    decreePublished: args.decreePublished,
    baselineMetrics: args.baselineMetrics,
    finalMetrics: args.finalMetrics,
    agentFlowReport: args.agentFlowReport,
    taskQuarterEnd: args.taskQuarterEnd,
    taskQuarterEndLines: formatTaskQuarterEndLines(args.taskQuarterEnd),
  };
}

const EMPTY_WALLET: GrowthPointWallet = {
  military: 0,
  management: 0,
  politics: 0,
  scholarship: 0,
  generic: 0,
};

const normalizeWallet = (wallet?: Partial<GrowthPointWallet>): GrowthPointWallet => ({
  military: Number(wallet?.military || 0),
  management: Number(wallet?.management || 0),
  politics: Number(wallet?.politics || 0),
  scholarship: Number(wallet?.scholarship || 0),
  generic: Number(wallet?.generic || 0),
});

const ALL_SKILL_TREES: SkillTreeName[] = ['military', 'management', 'politics', 'scholarship'];

const pickInitialActiveTree = (focus: string[]): SkillTreeName => {
  const first = (focus || []).find((k) => ALL_SKILL_TREES.includes(k as SkillTreeName));
  return (first as SkillTreeName) || 'military';
};

const buildInitialSkillUi = (
  wallet?: Partial<GrowthPointWallet>,
  activeTree?: SkillTreeName,
  catalog?: any,
): SkillUIState => {
  const fromCatalog = (cat: any): SkillUIState['skillTrees'] | null => {
    if (!cat || !cat.trees) return null;
    const out: any = {};
    for (const treeKey of ALL_SKILL_TREES) {
      const t = cat.trees[treeKey];
      if (!t || !Array.isArray(t.nodes)) continue;
      out[treeKey] = {
        nodes: t.nodes.map((n: any) => ({
          id: n.id,
          tree: treeKey,
          name: n.name_zh || n.name || n.id,
          description: n.description_zh || n.desc_zh || n.description || '',
          currentLevel: 0,
          maxLevel: n.max_level || n.maxLevel || 1,
          cost: n.cost || 1,
          effects: Array.isArray(n.effects_zh) ? n.effects_zh : (n.effects || []),
        })),
      };
    }
    if (Object.keys(out).length === 0) return null;
    return out as any;
  };

  const catalogTrees = catalog ? fromCatalog(catalog) : null;
  const defaultTrees = {
    military: {
      nodes: [
        { id: 'mil-zhengjun', tree: 'military', name: '整军', description: '提升军队训练效率。', currentLevel: 0, maxLevel: 3, cost: 1, effects: ['军事任务奖励 +10%', '边军士气 +2'] },
        { id: 'mil-bingzhan', tree: 'military', name: '兵站', description: '优化前线补给能力。', currentLevel: 0, maxLevel: 2, cost: 2, effects: ['军需稳定度提升', '后勤事件风险降低'] },
        { id: 'mil-fangxian', tree: 'military', name: '防线', description: '加固边境防务。', currentLevel: 0, maxLevel: 2, cost: 1, effects: ['叛乱风险降低', '边防事件缓冲'] },
      ],
    },
    management: {
      nodes: [
        { id: 'mgr-qingli', tree: 'management', name: '清厘', description: '强化账目与财税稽核。', currentLevel: 0, maxLevel: 3, cost: 1, effects: ['财政压力下降', '贪腐蔓延减缓'] },
        { id: 'mgr-cangchu', tree: 'management', name: '仓储', description: '整顿粮仓和调配。', currentLevel: 0, maxLevel: 2, cost: 2, effects: ['民生稳定度提升', '灾害冲击缓解'] },
        { id: 'mgr-kaohe', tree: 'management', name: '考核', description: '建立官员绩效制度。', currentLevel: 0, maxLevel: 2, cost: 1, effects: ['政策执行率提升', '任务成功率提升'] },
      ],
    },
    politics: {
      nodes: [
        { id: 'pol-hezhong', tree: 'politics', name: '和众', description: '平衡朝堂派系与利益。', currentLevel: 0, maxLevel: 3, cost: 1, effects: ['朝局稳定度提升', '权威上升'] },
        { id: 'pol-suqing', tree: 'politics', name: '肃清', description: '压制结党营私。', currentLevel: 0, maxLevel: 2, cost: 2, effects: ['腐败下降', '政令阻力降低'] },
        { id: 'pol-xunfang', tree: 'politics', name: '巡访', description: '加强地方督察。', currentLevel: 0, maxLevel: 2, cost: 1, effects: ['民怨下降', '地方失控风险下降'] },
      ],
    },
    scholarship: {
      nodes: [
        { id: 'sch-jingxue', tree: 'scholarship', name: '经学', description: '夯实政令理论依据。', currentLevel: 0, maxLevel: 3, cost: 1, effects: ['税务执行度提升', '长期民心加成'] },
        { id: 'sch-shuxue', tree: 'scholarship', name: '术学', description: '强化实务人才培养。', currentLevel: 0, maxLevel: 2, cost: 2, effects: ['治理效率提升', '任务波动降低'] },
        { id: 'sch-jiaoyu', tree: 'scholarship', name: '教谕', description: '推动地方教化。', currentLevel: 0, maxLevel: 2, cost: 1, effects: ['治安隐患减少', '公共支持提升'] },
      ],
    },
  } as const;

  return {
    activeTree: activeTree && ALL_SKILL_TREES.includes(activeTree) ? activeTree : 'military',
    pointWallet: normalizeWallet(wallet),
    openNodeDetailId: undefined,
    skillTrees: (catalogTrees || defaultTrees) as any,
  };
};

/** 单树技能节点在满级时的最大可表示投入（与 buildInitialSkillUi 节点表一致） */
const MAX_SKILL_POINTS_PER_TREE: Record<SkillTreeName, number> = {
  military: 9,
  management: 9,
  politics: 9,
  scholarship: 9,
};

const EMPTY_GROWTH_CUM: Record<SkillTreeName, number> = {
  military: 0,
  management: 0,
  politics: 0,
  scholarship: 0,
};

const normalizeTreePointsFromApi = (raw?: Record<string, unknown>): Record<SkillTreeName, number> => {
  const out: Record<SkillTreeName, number> = {
    military: 0,
    management: 0,
    politics: 0,
    scholarship: 0,
  };
  ALL_SKILL_TREES.forEach((t) => {
    const v = raw?.[t];
    const n = typeof v === 'number' ? v : Number(v);
    out[t] = Number.isFinite(n) ? Math.max(0, Math.round(n)) : 0;
  });
  return out;
};

/**
 * 仅当 quarter/start 响应带上 growth_cumulative_skill_points 对象时使用服务端累计；
 * 缺字段时保留 fallback，避免旧后端或未重启 API 时用 undefined 归一成全 0 覆盖本地已知累计。
 */
const cumulativePointsFromQuarterResponse = (
  out: { growth_cumulative_skill_points?: unknown },
  fallback: Record<SkillTreeName, number>,
): Record<SkillTreeName, number> => {
  const raw = out.growth_cumulative_skill_points;
  if (raw !== undefined && raw !== null && typeof raw === 'object' && !Array.isArray(raw)) {
    return normalizeTreePointsFromApi(raw as Record<string, unknown>);
  }
  return { ...fallback };
};

/** 将「树累计投入点数」贪心分配到固定节点顺序上，用于展示历史加点（不超过节点表上限） */
const distributePointsIntoTree = (
  nodesTemplate: SkillNode[],
  targetPoints: number,
  tree: SkillTreeName,
): SkillNode[] => {
  const cap = Math.max(
    0,
    Math.min(Math.round(targetPoints), MAX_SKILL_POINTS_PER_TREE[tree] || 0),
  );
  const nodes = nodesTemplate.map((n) => ({ ...n, currentLevel: 0 }));
  let r = cap;
  for (const node of nodes) {
    while (node.currentLevel < node.maxLevel && r >= node.cost) {
      node.currentLevel += 1;
      r -= node.cost;
    }
  }
  return nodes;
};

const buildSkillUiFromWalletAndCumulative = (
  wallet: Partial<GrowthPointWallet> | undefined,
  cumulative: Record<SkillTreeName, number> | undefined,
  activeTree?: SkillTreeName,
  catalog?: any,
): SkillUIState => {
  const base = buildInitialSkillUi(wallet, activeTree, catalog);
  const cum = cumulative || {
    military: 0,
    management: 0,
    politics: 0,
    scholarship: 0,
  };
  const nextTrees = { ...base.skillTrees };
  ALL_SKILL_TREES.forEach((tree) => {
    nextTrees[tree] = {
      nodes: distributePointsIntoTree(base.skillTrees[tree].nodes, cum[tree] || 0, tree),
    };
  });
  return { ...base, skillTrees: nextTrees };
};

const buildIncrementalAllocationPayload = (
  ui: SkillUIState,
  baseline: Record<SkillTreeName, number>,
): Record<SkillTreeName, number> => {
  const cur = buildSkillAllocationPayload(ui);
  const out: Record<SkillTreeName, number> = {
    military: 0,
    management: 0,
    politics: 0,
    scholarship: 0,
  };
  ALL_SKILL_TREES.forEach((t) => {
    out[t] = Math.max(0, Math.round(Number(cur[t] || 0)) - Math.round(Number(baseline[t] || 0)));
  });
  return out;
};

const cloneSkillUi = (ui: SkillUIState): SkillUIState => ({
  activeTree: ui.activeTree,
  pointWallet: { ...ui.pointWallet },
  openNodeDetailId: ui.openNodeDetailId,
  skillTrees: {
    military: { nodes: ui.skillTrees.military.nodes.map((x) => ({ ...x })) },
    management: { nodes: ui.skillTrees.management.nodes.map((x) => ({ ...x })) },
    politics: { nodes: ui.skillTrees.politics.nodes.map((x) => ({ ...x })) },
    scholarship: { nodes: ui.skillTrees.scholarship.nodes.map((x) => ({ ...x })) },
  },
});

const buildSkillAllocationPayload = (
  ui: SkillUIState,
): Record<SkillTreeName, number> => {
  const out: Record<SkillTreeName, number> = {
    military: 0,
    management: 0,
    politics: 0,
    scholarship: 0,
  };
  (Object.keys(ui.skillTrees) as SkillTreeName[]).forEach((tree) => {
    out[tree] = ui.skillTrees[tree].nodes.reduce(
      (sum, node) => sum + node.currentLevel * node.cost,
      0,
    );
  });
  return out;
};

/**
 * 本季可用剩余点：节点展示含历史累计时，只把「本会话相对 skillAllocBaseline 的增量」计入消耗。
 */
export const computeSkillWalletRemaining = (
  ui: SkillUIState,
  sessionBaseline: Record<SkillTreeName, number>,
): GrowthPointWallet => {
  const spentTotal = buildSkillAllocationPayload(ui);
  const remaining = { ...ui.pointWallet };
  ALL_SKILL_TREES.forEach((tree) => {
    const treeBudget = Number(ui.pointWallet[tree] || 0);
    const spend = Math.max(
      0,
      Math.round(Number(spentTotal[tree] || 0)) - Math.round(Number(sessionBaseline[tree] || 0)),
    );
    const consumeTree = Math.min(treeBudget, spend);
    const spill = Math.max(0, spend - consumeTree);
    remaining[tree] = Math.max(0, treeBudget - consumeTree);
    remaining.generic = Math.max(0, remaining.generic - spill);
  });
  return remaining;
};

interface GameState {
  sessionId: string;
  /** ADP Workflow A/B 对局 UUID，开局生成并全程携带 */
  gameSessionId: string;
  /** 课堂服务端游玩记录 ID（登录学生开局时创建） */
  playthroughId: string;
  scenarioId: ScenarioId | null;
  gamePhase: GamePhase;
  currentQuarter: number;
  loading: boolean;
  /** 加载场景，驱动进度条文案与阶段 */
  loadingKind: LoadingKind;
  error?: string;
  decreeText: string;
  decreeCategory: 'internal' | 'military' | 'diplomacy' | 'other';
  nationState: NationState;
  currentTasks: Array<Record<string, unknown>>;
  previousTaskResults: Array<Record<string, unknown>>;
  events: QuarterEvent[];
  currentEventIndex: number;
  selectedFocus: string[];
  decreePublished: boolean;
  skillUi: SkillUIState;
  skillUiSnapshot?: SkillUIState;
  skillSubmitEnabled: boolean;
  /** 第2季起：进入新季后须先完成加点才能发诏书；取消加点回主界面后仍为 true，直至确认提交 */
  seasonStartSkillPending: boolean;
  settlement?: QuarterSettlement;
  characters: Character[];
  memorials: Memorial[];
  logs: LogEntry[];
  ui: UIState;
  /** 后端 /tasks/state 返回的 history：已结算任务记录 */
  taskHistory: Array<Record<string, unknown>>;
  /** 后端各技能树累计投入点数（与 API growth_cumulative_skill_points / skill_levels 对齐） */
  growthCumulativeByTree: Record<SkillTreeName, number>;
  /** 本季技能会话开始时各树已展示投入，用于计算提交给后端的「本季增量」 */
  skillAllocBaseline: Record<SkillTreeName, number>;
  /** 熙宁战役：本季已解锁诏书 playbook 白名单 */
  allowedEdictPlaybooks: EdictPlaybookRef[];
  /** 熙宁战役弧：熙河 / 交趾阶段与压力 */
  warArcs: WarArcState[];
  /** 各路地区态（occupied/disaster 等），来自后端 final_state.region_status */
  regionStatus: Record<
    string,
    { status?: string; status_hint_zh?: string; visible?: boolean; relief_pending?: boolean }
  >;
  /** L1/L2/L3 战役终局摘要 */
  campaignEpilogue?: CampaignEpilogue;
  campaignMilestonePrompt?: string;
  /** 最近一次 campaign_end 原始包（供 Workflow C） */
  lastCampaignEnd?: CampaignEndPayload;
  /** 最近一次 quarter/start 返回的朝政纪要（后端生成） */
  latestQuarterReport?: Record<string, unknown>;
  /** 最近一次 quarter/start 返回的上季 Agent A 缓存 */
  lastAgentFlowReport?: Record<string, unknown>;
  /** 本局已归档季度总结（localStorage + 后端同步） */
  quarterChapters: QuarterChapterRecord[];
  /** 开局时各指标快照，供终局报告对比 */
  campaignOpeningMetrics: Partial<Record<NationMetricKey, number>>;
  /** 技能树节点目录（从后端 /growth/skill_catalog 获取，作为UI真相源，避免前端硬编码 mock） */
  skillCatalog?: any;

  previewEdict: (text: string) => MetricDeltaPreview[];
  setScenarioId: (id: ScenarioId) => void;
  getDataRoot: () => string;
  handleStartGame: () => Promise<void>;
  handleOpenDecree: () => void;
  cancelDecreeModal: () => void;
  handleSubmitDecree: (
    text: string,
    category?: 'internal' | 'military' | 'diplomacy' | 'other',
  ) => Promise<void>;
  handleSelectEventOption: (choiceId: string) => Promise<void>;
  setSelectedFocus: (focusTrees: string[]) => void;
  handleSelectQuarterFocus: (focusTrees: string[]) => Promise<void>;
  handleOpenSkillAllocation: () => void;
  handleCancelSkillAllocation: () => void;
  handleSwitchSkillTree: (tree: SkillTreeName) => void;
  handleOpenSkillNodeDetail: (nodeId?: string) => void;
  handleAllocateSkillPoint: (nodeId: string) => void;
  handleConfirmSkillAllocation: () => Promise<void>;
  loadSkillCatalog: () => Promise<void>;
  handleNextQuarter: () => Promise<void>;
  handleCampaignMilestoneEnd: () => Promise<void>;
  handleCampaignMilestoneContinue: () => Promise<void>;
  clearError: () => void;
  /** 退出当前局，回到选剧本界面（保留已选 scenarioId） */
  handleExitToScenarioSelect: () => void;
  openMemorialDrawer: () => void;
  closeMemorialDrawer: () => void;
  openQuarterChapterDetail: (id: string) => void;
  closeQuarterChapterDetail: () => void;
  openAIDialog: () => void;
  closeAIDialog: () => void;
  selectAIDialogCharacter: (characterId: string) => void;
  backAIDialogPicker: () => void;
  openTaskHistory: () => Promise<void>;
  closeTaskHistory: () => void;
  openQuarterReport: () => void;
  closeQuarterReport: () => void;
  openTaskPanel: () => void;
  closeTaskPanel: () => void;
  toggleTaskPanel: () => void;
}

export const useGameStore = create<GameState>((set, get) => ({
  sessionId: `fe_${Date.now()}`,
  gameSessionId: '',
  playthroughId: '',
  scenarioId: null,
  gamePhase: 'HOME',
  currentQuarter: 0,
  loading: false,
  loadingKind: 'none',
  error: undefined,
  decreeText: '',
  decreeCategory: 'internal',
  nationState: mockNationState,
  currentTasks: [],
  previousTaskResults: [],
  events: [],
  currentEventIndex: 0,
  selectedFocus: [],
  decreePublished: false,
  skillUi: buildInitialSkillUi(),
  growthCumulativeByTree: { military: 0, management: 0, politics: 0, scholarship: 0 },
  skillAllocBaseline: { military: 0, management: 0, politics: 0, scholarship: 0 },
  allowedEdictPlaybooks: [],
  warArcs: [],
  regionStatus: {},
  campaignEpilogue: undefined,
  campaignMilestonePrompt: undefined,
  latestQuarterReport: undefined,
  lastAgentFlowReport: undefined,
  quarterChapters: [],
  campaignOpeningMetrics: {},
  skillCatalog: undefined,
  skillUiSnapshot: undefined,
  skillSubmitEnabled: false,
  seasonStartSkillPending: false,
  settlement: undefined,
  characters: mockCharacters,
  memorials: mockMemorials,
  logs: mockLogs,
  taskHistory: [],
  ui: {
    isMemorialDrawerOpen: false,
    selectedQuarterChapterId: undefined,
    isQuarterChapterDetailOpen: false,
    isAIDialogOpen: false,
    isTaskHistoryOpen: false,
    taskHistoryLoading: false,
    isQuarterReportOpen: false,
    isTaskPanelOpen: true,
    aiDialogCharacterId: null,
  },

  previewEdict: (text: string) => scoreEdictText(text),

  setScenarioId: (id: ScenarioId) => {
    const pack = getScenario(id);
    if (!pack) return;
    set({
      scenarioId: id,
      nationState: cloneScenarioNationState(id),
      characters: pack.characters,
      memorials: pack.memorials,
      logs: [...pack.logs],
      error: undefined,
    });
    if (!isSalvageScenario(id)) {
      const rootDir = resolveScenarioDataRoot(id);
      if (rootDir) {
        void warmupNumericData(rootDir).catch(() => undefined);
      }
    }
  },

  getDataRoot: () => resolveScenarioDataRoot(get().scenarioId),

  handleStartGame: async () => {
    const state = get();
    if (state.loading) return;
    if (!state.scenarioId) {
      set({ error: '请先在开场界面选择剧本（熙宁变法或万历改革）。' });
      return;
    }
    const rootDir = resolveScenarioDataRoot(state.scenarioId);
    try {
      set({
        loading: true,
        loadingKind: 'start_game',
        error: undefined,
        ui: {
          ...state.ui,
          isTaskHistoryOpen: false,
          taskHistoryLoading: false,
          isQuarterReportOpen: false,
        },
      });
      const sessionId = `fe_${Date.now()}`;
      const gameSessionId = newGameSessionId();
      let playthroughId = '';
      if (getAccessToken() && state.scenarioId) {
        try {
          const pt = await createPlaythrough({
            scenario_code: state.scenarioId,
            game_session_id: gameSessionId,
            campaign_session_id: sessionId,
          });
          playthroughId = pt.id;
        } catch {
          /* 课堂服务不可用时继续游戏 */
        }
      }
      const nationBaseline = cloneScenarioNationState(state.scenarioId);
      const scenarioPack = getScenario(state.scenarioId);
      const out = await withTimeout(
        Promise.all([
          startQuarterApi({
            session_id: sessionId,
            game_session_id: gameSessionId,
            root_dir: rootDir,
            edict_text: '',
            edict_category: 'other',
            player_actions: [],
            enable_layer3_llm: true,
          }),
          get().loadSkillCatalog(),
        ]).then(([startOut]) => startOut),
        180_000,
        '开局 quarter/start',
      );
      const quarter = Number(out.quarter_index || 1);
      const campaignLabel = String(out.campaign_label_zh || '').trim();
      const startEvents = parsePendingEventsFromReport(out.quarter_report);
      const cum = cumulativePointsFromQuarterResponse(out, EMPTY_GROWTH_CUM);
      // 传入当前已加载的目录（若 load 已在后台完成）；否则使用内嵌默认（向后兼容）
      const skillUi0 = buildSkillUiFromWalletAndCumulative(
        out.growth_available_points,
        cum,
        'military',
        (get() as any).skillCatalog,
      );
      const baseline0 = buildSkillAllocationPayload(skillUi0);
      const startEnd = readCampaignEnd(out);
      const startNormalPhase: GamePhase =
        startEvents.length > 0 ? 'EVENT_RESOLUTION' : 'QUARTER_MAIN';
      const startResolved = resolveEndPhase(startEnd, state.scenarioId, startNormalPhase);
      const openingMetrics = Object.fromEntries(
        nationBaseline.metrics.map((m) => [m.key, m.value]),
      ) as Partial<Record<NationMetricKey, number>>;
      const startChapters = syncSessionQuarterChapters(sessionId, out.quarter_chapters);
      set({
        sessionId,
        gameSessionId,
        playthroughId,
        currentQuarter: quarter,
        campaignOpeningMetrics: openingMetrics,
        nationState: {
          ...nationBaseline,
          yearLabel: campaignLabel || nationBaseline.yearLabel,
          metrics: nationBaseline.metrics.map((m) => ({
            ...m,
            trend: 'stable' as const,
          })),
        },
        allowedEdictPlaybooks: out.allowed_edict_playbooks || [],
        warArcs: readWarArcs({ quarter_report: out.quarter_report }),
        regionStatus: readRegionStatus(out.final_state as Record<string, unknown> | undefined),
        characters: scenarioPack?.characters ?? state.characters,
        memorials: scenarioPack?.memorials ?? state.memorials,
        logs: [
          {
            id: 'log-1',
            turn: quarter,
            timeLabel: campaignLabel || nationBaseline.yearLabel,
            summary: `第${quarter}季度开始（${scenarioPack?.labelZh ?? ''}），已加载任务 ${(out.new_tasks || []).length} 项。`,
            metricChanges: [],
          },
        ],
        currentTasks: out.new_tasks || [],
        previousTaskResults: out.previous_task_results || [],
        taskHistory: out.task_history || out.task_history_tail || [],
        events: startEvents,
        currentEventIndex: 0,
        selectedFocus: [],
        decreePublished: false,
        growthCumulativeByTree: cum,
        skillAllocBaseline: baseline0,
        skillUi: skillUi0,
        skillUiSnapshot: undefined,
        skillSubmitEnabled: false,
        seasonStartSkillPending: false,
        settlement: undefined,
        loading: false,
        loadingKind: 'none',
        decreeText: '',
        gamePhase: startResolved.phase,
        campaignEpilogue: startResolved.epilogue,
        campaignMilestonePrompt: startResolved.milestonePrompt,
        latestQuarterReport: out.quarter_report || undefined,
        lastAgentFlowReport: out.agent_flow_report || undefined,
        quarterChapters: startChapters,
      });
      pushPlaythroughQuarterChapters(playthroughId, sessionId, startChapters);
      syncPlaythroughQuarter(playthroughId, quarter);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  handleOpenDecree: () => {
    const st = get();
    if (st.gamePhase !== 'QUARTER_MAIN') return;
    if (st.seasonStartSkillPending) {
      set({ error: '请先完成本季度技能加点，再发布诏书。' });
      return;
    }
    if (st.decreePublished) {
      set({
        error: '本季诏书已颁布，请先处理事件并选择季度重心（季末再点「下季」）。',
      });
      return;
    }
    if (st.loading) {
      set({ error: '上一操作仍在进行，请稍候或点拟诏面板的「取消」。' });
      return;
    }
    set({ gamePhase: 'DECREE_MODAL', error: undefined });
  },

  cancelDecreeModal: () => {
    const st = get();
    if (st.gamePhase !== 'DECREE_MODAL') return;
    set({ gamePhase: 'QUARTER_MAIN', loading: false, loadingKind: 'none', error: undefined });
  },

  handleSubmitDecree: async (text: string, category = 'internal') => {
    const state = get();
    if (state.loading || state.gamePhase !== 'DECREE_MODAL') return;
    const trimmed = text.trim();
    if (!trimmed) {
      set({ error: '诏书内容不能为空。' });
      return;
    }
    try {
      set({ loading: true, loadingKind: 'none', error: undefined, decreeText: trimmed, decreeCategory: category });
      const settle = await withTimeout(
        submitDecree({
          session_id: state.sessionId,
          game_session_id: state.gameSessionId,
          root_dir: resolveScenarioDataRoot(state.scenarioId),
          edict_text: trimmed,
          edict_category: category,
          quarters: 1,
          enable_layer3_llm: true,
        }),
        120_000,
        '诏书 quarter/settle',
      );
      const merged = applyBackendReportToMetrics(
        state.nationState,
        settle.final_state?.metrics || {},
      );
      const baselineMetrics = Object.fromEntries(
        state.nationState.metrics.map((metric) => [metric.key, metric.value]),
      );
      const finalMetrics = Object.fromEntries(
        merged.map((metric) => [metric.key, metric.value]),
      );
      const events: QuarterEvent[] = [];
      if (state.scenarioId !== 'song_xining') {
        const roll = await withTimeout(
          triggerRandomEvents({
            session_id: state.sessionId,
            root_dir: resolveScenarioDataRoot(state.scenarioId),
            turn_id: state.currentQuarter,
            seed: state.currentQuarter + 17,
          }),
          30_000,
          '事件 events/roll',
        );
        if (roll.rolled && roll.event_instance_id && roll.event) {
          events.push({
            eventInstanceId: roll.event_instance_id,
            eventId: roll.event.id,
            title: roll.event.title,
            description: roll.event.description || '',
            choices: (roll.event.choices || []).slice(0, 3).map((choice) => ({
              id: choice.id,
              text: choice.text,
              effectsText: choice.tags || [],
            })),
          });
        }
      }

      const tasksAfterDecree = await withTimeout(
        drawQuarterTasks({ session_id: state.sessionId }),
        30_000,
        '任务列表 tasks/state',
      );
      const poolTasks = tasksAfterDecree.active || state.currentTasks;
      const agentFlowReport =
        settle.input?.secondary_effects_report &&
        typeof settle.input.secondary_effects_report === 'object'
          ? (settle.input.secondary_effects_report as Record<string, unknown>)
          : undefined;
      const taskQuarterEnd =
        (settle.task_quarter_end as Record<string, unknown> | undefined) ||
        (settle.input?.task_quarter_end as Record<string, unknown> | undefined);

      set({
        nationState: { ...state.nationState, metrics: merged },
        warArcs: readWarArcs({
          war_arcs: settle.input?.war_arcs as WarArcsSnapshot | undefined,
        }),
        regionStatus: readRegionStatus(settle.final_state as Record<string, unknown> | undefined),
        events,
        currentEventIndex: 0,
        gamePhase: events.length > 0 ? 'EVENT_RESOLUTION' : 'FOCUS_SELECTION',
        selectedFocus: [],
        decreePublished: true,
        currentTasks: poolTasks,
        taskHistory: tasksAfterDecree.history || state.taskHistory,
        settlement: buildQuarterSettlementSnapshot({
          reports: settle.reports || [],
          quarterReport: settle.input || {},
          previousTaskResults: state.previousTaskResults,
          currentTasks: poolTasks,
          eventSummary: [],
          decreeText: trimmed,
          decreeCategory: category,
          decreePublished: true,
          baselineMetrics,
          finalMetrics,
          delegationEnqueued: settle.delegation_enqueued ?? null,
          agentFlowReport,
          taskQuarterEnd,
        }),
        logs: [
          ...state.logs,
          {
            id: `log-${state.logs.length + 1}`,
            turn: state.currentQuarter,
            timeLabel: state.nationState.yearLabel,
            summary: events.length > 0
              ? `诏书已提交，触发事件：${events[0].title}`
              : agentFlowReport?.proposals
                ? '诏书已提交，Agent A 数值提案已返回。'
                : agentFlowReport && (agentFlowReport.contest || agentFlowReport.counter)
                  ? '诏书已提交，Agent A 人物对策已返回。'
                  : '诏书已提交，本季未触发随机事件。',
            metricChanges: [],
          },
        ],
        loading: false,
        loadingKind: 'none',
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    } finally {
      if (get().gamePhase === 'DECREE_MODAL') {
        set({ loading: false, loadingKind: 'none' });
      }
    }
  },

  handleSelectEventOption: async (choiceId: string) => {
    const state = get();
    if (state.loading || state.gamePhase !== 'EVENT_RESOLUTION') return;
    const event = state.events[state.currentEventIndex];
    if (!event) return;
    try {
      set({ loading: true, loadingKind: 'general', error: undefined });
      const out = await submitEventChoice({
        session_id: state.sessionId,
        event_instance_id: event.eventInstanceId,
        choice_id: choiceId,
      });
      const merged = applyBackendReportToMetrics(
        state.nationState,
        out.state_metrics || {},
      );
      const nextIndex = state.currentEventIndex + 1;
      const hasNext = nextIndex < state.events.length;
      set({
        nationState: { ...state.nationState, metrics: merged },
        settlement: state.settlement
          ? {
              ...state.settlement,
              finalMetrics: Object.fromEntries(
                merged.map((metric) => [metric.key, metric.value]),
              ),
            }
          : undefined,
        currentEventIndex: hasNext ? nextIndex : state.currentEventIndex,
        gamePhase: hasNext ? 'EVENT_RESOLUTION' : 'FOCUS_SELECTION',
        selectedFocus: hasNext ? state.selectedFocus : [],
        logs: [
          ...state.logs,
          {
            id: `log-${state.logs.length + 1}`,
            turn: state.currentQuarter,
            timeLabel: state.nationState.yearLabel,
            summary: `事件处理：${event.title} -> ${out.choice_text || choiceId}`,
            metricChanges: (out.effects_applied || [])
              .filter((x) => x.action === 'add_metric')
              .map((x) => ({
                metric: x.key as NationMetricKey,
                delta: Number(x.value),
              })),
          },
        ],
        loading: false,
        loadingKind: 'none',
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  setSelectedFocus: (focusTrees: string[]) => {
    if (focusTrees.length > 3) return;
    set({ selectedFocus: focusTrees });
  },

  handleSelectQuarterFocus: async (focusTrees: string[]) => {
    const state = get();
    if (state.loading || state.gamePhase !== 'FOCUS_SELECTION') return;
    if (focusTrees.length !== 3) {
      set({ error: '季度重心必须四选三，请选择恰好 3 项。' });
      return;
    }
    try {
      set({ loading: true, loadingKind: 'none', error: undefined });
      await submitQuarterFocus({
        session_id: state.sessionId,
        root_dir: resolveScenarioDataRoot(state.scenarioId),
        focus_trees: focusTrees,
      });
      const tasksState = await drawQuarterTasks({ session_id: state.sessionId });
      const poolTasks = tasksState.active || state.currentTasks;
      const baselineMetrics =
        state.settlement?.baselineMetrics ||
        Object.fromEntries(
          state.nationState.metrics.map((metric) => [metric.key, metric.value]),
        );
      const finalMetrics =
        state.settlement?.finalMetrics ||
        Object.fromEntries(
          state.nationState.metrics.map((metric) => [metric.key, metric.value]),
        );
      set({
        selectedFocus: focusTrees,
        currentTasks: poolTasks,
        taskHistory: tasksState.history || state.taskHistory,
        settlement: buildQuarterSettlementSnapshot({
          reports: state.settlement?.reports || [],
          quarterReport: state.settlement?.quarterReport || {},
          previousTaskResults: state.previousTaskResults,
          currentTasks: poolTasks,
          eventSummary: state.events.map((x) => x.title),
          decreeText: state.decreeText,
          decreeCategory: state.decreeCategory,
          decreePublished: state.decreePublished,
          baselineMetrics,
          finalMetrics,
          delegationEnqueued: state.settlement?.delegationEnqueued,
          agentFlowReport: state.settlement?.agentFlowReport,
        }),
        gamePhase: 'QUARTER_SETTLEMENT',
        skillSubmitEnabled: false,
        skillUiSnapshot: cloneSkillUi(state.skillUi),
        logs: [
          ...state.logs,
          {
            id: `log-${state.logs.length + 1}`,
            turn: state.currentQuarter,
            timeLabel: state.nationState.yearLabel,
            summary: `已提交下季重心：${focusTrees.join(' / ')}，将在进入下一季度初进行技能加点。`,
            metricChanges: [],
          },
        ],
        loading: false,
        loadingKind: 'none',
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  handleOpenSkillAllocation: () => {
    const state = get();
    if (!state.skillCatalog) {
      // 非阻塞加载；加载完成后下次打开或重渲染会使用目录定义的节点
      void get().loadSkillCatalog();
    }
    if (
      state.loading ||
      state.gamePhase !== 'QUARTER_MAIN' ||
      state.currentQuarter < 2 ||
      state.decreePublished ||
      !state.seasonStartSkillPending
    ) {
      return;
    }
    const focus = (state.selectedFocus || []).filter((t) =>
      ALL_SKILL_TREES.includes(t as SkillTreeName),
    ) as SkillTreeName[];
    const activeOk =
      focus.length === 3 && focus.includes(state.skillUi.activeTree)
        ? state.skillUi.activeTree
        : pickInitialActiveTree(state.selectedFocus);
    const skillUiPatched = buildSkillUiFromWalletAndCumulative(
      state.skillUi.pointWallet,
      state.growthCumulativeByTree,
      activeOk,
      state.skillCatalog,
    );
    const baselineOpen = buildSkillAllocationPayload(skillUiPatched);
    // #region agent log
    fetch('http://127.0.0.1:7607/ingest/501d7f5e-a3c4-4d94-ab0f-3b2cebc51f5b', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf98a' },
      body: JSON.stringify({
        sessionId: 'fcf98a',
        hypothesisId: 'H5',
        location: 'store.ts:handleOpenSkillAllocation',
        message: 'open skill panel',
        data: {
          growthCumulativeByTree: state.growthCumulativeByTree,
          milDisplayed: skillUiPatched.skillTrees.military.nodes.reduce(
            (s, n) => s + n.currentLevel * n.cost,
            0,
          ),
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
    set({
      gamePhase: 'SKILL_ALLOCATION',
      skillUi: skillUiPatched,
      skillAllocBaseline: baselineOpen,
      skillUiSnapshot: cloneSkillUi(skillUiPatched),
      skillSubmitEnabled: true,
      error: undefined,
    });
  },

  handleCancelSkillAllocation: () => {
    const state = get();
    if (state.gamePhase !== 'SKILL_ALLOCATION') return;
    if (state.skillSubmitEnabled) {
      const restored = state.skillUiSnapshot ? cloneSkillUi(state.skillUiSnapshot) : state.skillUi;
      set({
        gamePhase: 'QUARTER_MAIN',
        skillUi: restored,
        skillAllocBaseline: buildSkillAllocationPayload(restored),
        skillUiSnapshot: undefined,
        skillSubmitEnabled: false,
        seasonStartSkillPending: true,
        error: undefined,
      });
      return;
    }
    const restored2 = state.skillUiSnapshot ? cloneSkillUi(state.skillUiSnapshot) : state.skillUi;
    set({
      gamePhase: 'QUARTER_MAIN',
      skillUi: restored2,
      skillAllocBaseline: buildSkillAllocationPayload(restored2),
      skillUiSnapshot: undefined,
      skillSubmitEnabled: false,
      error: undefined,
    });
  },

  handleSwitchSkillTree: (tree: SkillTreeName) => {
    const state = get();
    if (state.gamePhase !== 'SKILL_ALLOCATION') return;
    const focus = (state.selectedFocus || []).filter((t) =>
      ALL_SKILL_TREES.includes(t as SkillTreeName),
    ) as SkillTreeName[];
    if (focus.length === 3 && !focus.includes(tree)) return;
    set({
      skillUi: {
        ...state.skillUi,
        activeTree: tree,
        openNodeDetailId: undefined,
      },
    });
  },

  handleOpenSkillNodeDetail: (nodeId?: string) => {
    const state = get();
    if (state.gamePhase !== 'SKILL_ALLOCATION') return;
    set({
      skillUi: {
        ...state.skillUi,
        openNodeDetailId: nodeId,
      },
    });
  },

  handleAllocateSkillPoint: (nodeId: string) => {
    const state = get();
    if (state.gamePhase !== 'SKILL_ALLOCATION') return;
    const tree = state.skillUi.activeTree;
    const focus = (state.selectedFocus || []).filter((t) =>
      ALL_SKILL_TREES.includes(t as SkillTreeName),
    ) as SkillTreeName[];
    if (focus.length === 3 && !focus.includes(tree)) return;
    const treeState = state.skillUi.skillTrees[tree];
    const node = treeState.nodes.find((x) => x.id === nodeId);
    if (!node) return;
    if (node.currentLevel >= node.maxLevel) return;
    const remaining = computeSkillWalletRemaining(state.skillUi, state.skillAllocBaseline);
    const availableForTree = Number(remaining[tree] || 0) + Number(remaining.generic || 0);
    if (availableForTree < node.cost) return;
    set({
      skillUi: {
        ...state.skillUi,
        skillTrees: {
          ...state.skillUi.skillTrees,
          [tree]: {
            ...treeState,
            nodes: treeState.nodes.map((x) =>
              x.id === nodeId ? { ...x, currentLevel: x.currentLevel + 1 } : x,
            ),
          },
        },
      },
    });
  },

  handleConfirmSkillAllocation: async () => {
    const state = get();
    if (state.loading || state.gamePhase !== 'SKILL_ALLOCATION') return;
    if (!state.skillSubmitEnabled) {
      set({
        gamePhase: 'QUARTER_MAIN',
        skillUiSnapshot: undefined,
        error: undefined,
      });
      return;
    }
    try {
      set({ loading: true, loadingKind: 'general', error: undefined });
      const allocationInc = buildIncrementalAllocationPayload(state.skillUi, state.skillAllocBaseline);
      const submitted = await submitSkillPoints({
        session_id: state.sessionId,
        root_dir: resolveScenarioDataRoot(state.scenarioId),
        allocation: allocationInc,
      });
      const remainingWallet = normalizeWallet(submitted.remaining_points || EMPTY_WALLET);
      const cumNext = normalizeTreePointsFromApi(
        (submitted.skill_levels as Record<string, unknown> | undefined) || undefined,
      );
      const skillUiAfter = {
        ...state.skillUi,
        pointWallet: remainingWallet,
      };
      const baselineAfter = buildSkillAllocationPayload(skillUiAfter);
      // #region agent log
      fetch('http://127.0.0.1:7607/ingest/501d7f5e-a3c4-4d94-ab0f-3b2cebc51f5b', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf98a' },
        body: JSON.stringify({
          sessionId: 'fcf98a',
          hypothesisId: 'H4',
          location: 'store.ts:handleConfirmSkillAllocation',
          message: 'allocate_skills ok',
          data: {
            allocationInc,
            skill_levels: submitted.skill_levels ?? null,
            cumNext,
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {});
      // #endregion
      const stAfter = get();
      const postSkillEvents = stAfter.events || [];
      set({
        gamePhase: postSkillEvents.length > 0 ? 'EVENT_RESOLUTION' : 'QUARTER_MAIN',
        seasonStartSkillPending: false,
        decreePublished: false,
        skillUiSnapshot: undefined,
        skillSubmitEnabled: false,
        growthCumulativeByTree: cumNext,
        skillAllocBaseline: baselineAfter,
        skillUi: skillUiAfter,
        logs: [
          ...state.logs,
          {
            id: `log-${state.logs.length + 1}`,
            turn: state.currentQuarter,
            timeLabel: state.nationState.yearLabel,
            summary: `本季度技能加点已确认（累计投入）：军${cumNext.military}/政${cumNext.politics}/管${cumNext.management}/学${cumNext.scholarship}`,
            metricChanges: [],
          },
        ],
        loading: false,
        loadingKind: 'none',
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  loadSkillCatalog: async () => {
    const state = get();
    if (state.skillCatalog) return; // already loaded
    try {
      const cat = await getSkillCatalog({
        // 显式直连后端，避免代理问题；与其它 growth 请求保持一致的 base 处理
      });
      set({ skillCatalog: cat });
    } catch (e) {
      // 失败不阻塞游戏；UI 会回退到本地节点定义（向后兼容）
      // 但日志提示一次
      // console.warn('load skill catalog failed, using local fallback nodes', e);
    }
  },

  handleNextQuarter: async () => {
    const state = get();
    if (state.loading || state.gamePhase !== 'QUARTER_SETTLEMENT') return;
    const maxQuarters = state.scenarioId === 'song_xining' ? CAMPAIGN_MAX_QUARTERS : 5;
    if (state.currentQuarter >= maxQuarters) {
      set({
        gamePhase: 'GAME_END',
        campaignEpilogue: {
          kind: 'calendar',
          title_zh: state.scenarioId === 'song_xining' ? '熙宁十年期满' : '五季已毕',
          summary_zh:
            state.scenarioId === 'song_xining'
              ? '日历行至熙宁十年之末，本阶段战役收束。'
              : '本场景季限已至。',
          quarter_index: state.currentQuarter,
        },
      });
      return;
    }
    try {
      set({ loading: true, loadingKind: 'next_quarter', error: undefined });
      const out = await startQuarterApi({
        session_id: state.sessionId,
        game_session_id: state.gameSessionId,
        root_dir: resolveScenarioDataRoot(state.scenarioId),
        edict_text: '',
        edict_category: 'other',
        player_actions: [],
        enable_layer3_llm: true,
      });
      const merged = applyBackendReportToMetrics(
        state.nationState,
        out.final_state?.metrics || {},
      );
      const nextQuarter = Number(out.quarter_index || state.currentQuarter + 1);
      const campaignLabel = String(out.campaign_label_zh || '').trim();
      const nextEvents = parsePendingEventsFromReport(out.quarter_report);
      const memorialDisplay = formatQuarterReportForDisplay(out.quarter_report, {
        currentQuarter: nextQuarter,
        scenarioId: state.scenarioId,
      });
      const autoOpenQuarterReport = nextQuarter >= 2 && memorialDisplay.hasContent;
      const enterSeasonStartSkill = nextQuarter >= 2;
      const cum = cumulativePointsFromQuarterResponse(out, state.growthCumulativeByTree);
      const activeTreeNext = pickInitialActiveTree(state.selectedFocus);
      const skillUiNext = buildSkillUiFromWalletAndCumulative(
        out.growth_available_points,
        cum,
        activeTreeNext,
        (get() as any).skillCatalog,
      );
      const baselineNext = buildSkillAllocationPayload(skillUiNext);
      const normalPhase: GamePhase = enterSeasonStartSkill
        ? 'SKILL_ALLOCATION'
        : nextEvents.length > 0
          ? 'EVENT_RESOLUTION'
          : 'QUARTER_MAIN';
      const quarterEnd = readCampaignEnd(out);
      const resolved = resolveEndPhase(quarterEnd, state.scenarioId, normalPhase);
      const endingLoadPending = resolved.phase === 'GAME_END' && !!resolved.epilogue;
      const nextChapters = syncSessionQuarterChapters(
        state.sessionId,
        out.quarter_chapters,
      );
      set({
        currentQuarter: nextQuarter,
        nationState: {
          ...state.nationState,
          yearLabel: campaignLabel || state.nationState.yearLabel,
          metrics: merged,
        },
        currentTasks: out.new_tasks || [],
        previousTaskResults: out.previous_task_results || [],
        taskHistory: out.task_history || state.taskHistory,
        allowedEdictPlaybooks: out.allowed_edict_playbooks || [],
        warArcs: readWarArcs({ quarter_report: out.quarter_report }),
        regionStatus: readRegionStatus(out.final_state as Record<string, unknown> | undefined),
        events: nextEvents,
        currentEventIndex: 0,
        decreePublished: false,
        growthCumulativeByTree: cum,
        skillAllocBaseline: baselineNext,
        skillUi: skillUiNext,
        skillUiSnapshot: enterSeasonStartSkill ? cloneSkillUi(skillUiNext) : undefined,
        skillSubmitEnabled: enterSeasonStartSkill,
        seasonStartSkillPending: enterSeasonStartSkill,
        settlement: undefined,
        decreeText: '',
        decreeCategory: 'internal',
        gamePhase: resolved.phase,
        campaignEpilogue: resolved.epilogue,
        campaignMilestonePrompt: resolved.milestonePrompt,
        lastCampaignEnd: quarterEnd,
        latestQuarterReport: out.quarter_report || undefined,
        lastAgentFlowReport: out.agent_flow_report || undefined,
        quarterChapters: nextChapters,
        ui: {
          ...state.ui,
          isQuarterReportOpen: autoOpenQuarterReport,
        },
        logs: [
          ...state.logs,
          {
            id: `log-${state.logs.length + 1}`,
            turn: nextQuarter,
            timeLabel: state.nationState.yearLabel,
            summary: enterSeasonStartSkill
              ? `进入第${nextQuarter}季度：请先完成本季技能加点。`
              : String(
                  (out.quarter_report?.title_zh as string | undefined) ||
                    (out.quarter_report?.summary as string | undefined) ||
                    `进入第${nextQuarter}季度。`,
                ),
            metricChanges: [],
          },
        ],
        loading: endingLoadPending,
        loadingKind: endingLoadPending ? 'general' : 'none',
      });
      pushPlaythroughQuarterChapters(state.playthroughId, state.sessionId, nextChapters);
      syncPlaythroughQuarter(state.playthroughId, nextQuarter);
      if (endingLoadPending && resolved.epilogue) {
        const chaptersForEnding = syncSessionQuarterChapters(
          state.sessionId,
          out.quarter_chapters,
        );
        const enriched = await loadEndingSummaryForSession({
          sessionId: state.sessionId,
          gameSessionId: state.gameSessionId,
          scenarioId: state.scenarioId,
          campaignEnd: quarterEnd,
          baseEpilogue: resolved.epilogue,
          quarterChapters: chaptersForEnding,
        });
        set({ campaignEpilogue: enriched, loading: false, loadingKind: 'none' });
      } else if (!endingLoadPending) {
        set({ loading: false, loadingKind: 'none' });
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  handleCampaignMilestoneEnd: async () => {
    const state = get();
    if (state.loading || state.gamePhase !== 'CAMPAIGN_MILESTONE') return;
    try {
      set({ loading: true, loadingKind: 'general', error: undefined });
      await submitCampaignMilestoneDecision({
        session_id: state.sessionId,
        decision: 'end',
      });
      const baseEpilogue =
        state.campaignEpilogue ||
        epilogueFromEnd(state.lastCampaignEnd || { kind: 'milestone' });
      set({
        gamePhase: 'GAME_END',
        campaignMilestonePrompt: undefined,
        campaignEpilogue: baseEpilogue,
      });
      const enriched = await loadEndingSummaryForSession({
        sessionId: state.sessionId,
        gameSessionId: state.gameSessionId,
        scenarioId: state.scenarioId,
        campaignEnd: state.lastCampaignEnd,
        baseEpilogue,
        quarterChapters: state.quarterChapters,
      });
      set({ campaignEpilogue: enriched, loading: false, loadingKind: 'none' });
      if (state.playthroughId) {
        void updatePlaythrough(state.playthroughId, {
          status: 'finished',
          current_quarter: state.currentQuarter,
          ending_type: enriched.kind || enriched.ending_mode || 'finished',
          summary_json: {
            title_zh: enriched.title_zh,
            summary_zh: enriched.summary_zh,
            kind: enriched.kind,
            ending_mode: enriched.ending_mode,
            score: enriched.score,
            score_label_zh: enriched.score_label_zh,
            highlights_zh: enriched.highlights_zh,
            history_compare_zh: enriched.history_compare_zh,
            campaign_end: state.lastCampaignEnd,
          },
        }).catch(() => undefined);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  handleCampaignMilestoneContinue: async () => {
    const state = get();
    if (state.loading || state.gamePhase !== 'CAMPAIGN_MILESTONE') return;
    try {
      set({ loading: true, loadingKind: 'general', error: undefined });
      await submitCampaignMilestoneDecision({
        session_id: state.sessionId,
        decision: 'continue',
      });
      const enterSkill = state.currentQuarter >= 2 && state.seasonStartSkillPending;
      const hasEvents = (state.events || []).length > 0;
      set({
        gamePhase: enterSkill
          ? 'SKILL_ALLOCATION'
          : hasEvents
            ? 'EVENT_RESOLUTION'
            : 'QUARTER_MAIN',
        loading: false,
        loadingKind: 'none',
        campaignMilestonePrompt: undefined,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set({ error: msg, loading: false, loadingKind: 'none' });
    }
  },

  clearError: () => set({ error: undefined }),

  handleExitToScenarioSelect: () => {
    const state = get();
    const nationReset = state.scenarioId
      ? cloneScenarioNationState(state.scenarioId)
      : state.nationState;
    set({
      gamePhase: 'HOME',
      loading: false,
      loadingKind: 'none',
      error: undefined,
      playthroughId: '',
      nationState: nationReset,
      ui: {
        ...state.ui,
        isMemorialDrawerOpen: false,
        isQuarterChapterDetailOpen: false,
        selectedQuarterChapterId: undefined,
        isAIDialogOpen: false,
        isTaskHistoryOpen: false,
        taskHistoryLoading: false,
        isQuarterReportOpen: false,
        aiDialogCharacterId: null,
      },
    });
  },

  openMemorialDrawer: () =>
    set((state) => ({
      ui: { ...state.ui, isMemorialDrawerOpen: true },
    })),
  closeMemorialDrawer: () =>
    set((state) => ({
      ui: { ...state.ui, isMemorialDrawerOpen: false },
    })),
  openQuarterChapterDetail: (id: string) =>
    set((state) => ({
      ui: {
        ...state.ui,
        selectedQuarterChapterId: id,
        isQuarterChapterDetailOpen: true,
      },
    })),
  closeQuarterChapterDetail: () =>
    set((state) => ({
      ui: {
        ...state.ui,
        isQuarterChapterDetailOpen: false,
      },
    })),
  openAIDialog: () =>
    set((state) => ({
      ui: { ...state.ui, isAIDialogOpen: true, aiDialogCharacterId: null },
    })),
  closeAIDialog: () =>
    set((state) => ({
      ui: { ...state.ui, isAIDialogOpen: false, aiDialogCharacterId: null },
    })),
  selectAIDialogCharacter: (characterId: string) =>
    set((state) => ({
      ui: { ...state.ui, aiDialogCharacterId: characterId },
    })),
  backAIDialogPicker: () =>
    set((state) => ({
      ui: { ...state.ui, aiDialogCharacterId: null },
    })),

  openTaskHistory: async () => {
    const state = get();
    set((s) => ({
      ui: { ...s.ui, isTaskHistoryOpen: true, taskHistoryLoading: true },
    }));
    try {
      const ts = await drawQuarterTasks({ session_id: state.sessionId });
      set((s) => ({
        taskHistory: ts.history || [],
        ui: { ...s.ui, taskHistoryLoading: false },
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set((s) => ({
        error: msg,
        ui: { ...s.ui, taskHistoryLoading: false },
      }));
    }
  },

  closeTaskHistory: () =>
    set((state) => ({
      ui: { ...state.ui, isTaskHistoryOpen: false },
    })),

  openQuarterReport: () =>
    set((state) => ({
      ui: { ...state.ui, isQuarterReportOpen: true },
    })),

  closeQuarterReport: () =>
    set((state) => ({
      ui: { ...state.ui, isQuarterReportOpen: false },
    })),

  openTaskPanel: () =>
    set((state) => ({
      ui: { ...state.ui, isTaskPanelOpen: true },
    })),

  closeTaskPanel: () =>
    set((state) => ({
      ui: { ...state.ui, isTaskPanelOpen: false },
    })),

  toggleTaskPanel: () =>
    set((state) => ({
      ui: { ...state.ui, isTaskPanelOpen: !state.ui.isTaskPanelOpen },
    })),
}));

