import { create } from 'zustand';
import {
  getScenario,
  resolveFrontendScenarioFromSalvageId,
  resolveSalvageScenarioId,
  type ScenarioId,
} from '../scenarios';
import type { Character, NationState } from '../types';
import type {
  MingGameState,
  MingPendingDecision,
  MingStructuredDirective,
  MingTurnPhase,
  MingChatMessage,
  MingChatSuggestion,
  MingSecretOrder,
} from './mingTurnPhase';
import type { SalvageMinister } from './salvageStateTypes';
import {
  buildNationFromSalvage,
  mergeSalvageMinisters,
  parsePendingDecisions,
  resolveMinisterName,
  salvageSessionId,
  adaptSalvageToMingGameState,
  normalizeSalvageGameState,
  mergeSalvageGameState,
  type SalvageGameState,
  type SalvageAdapterContext,
} from '../../lib/mingSalvageAdapter';
import {
  mingComposeDecree,
  mingConfirmDirective,
  mingCreateDirective,
  mingDeleteDirective,
  mingDeleteStructuredDirective,
  mingEditDecree,
  mingExitSession,
  mingFetchMenuStatus,
  mingFetchState,
  mingIssueDecreeStream,
  mingFetchMinisterChat,
  mingMinisterChatStream,
  mingUndoMinisterChat,
  mingCreateMinisterSecretOrder,
  mingUploadMinisterPortrait,
  mingFetchSecretOrders,
  mingAddFavorite,
  mingRemoveFavorite,
  mingArchiveMinister,
  mingPatchDirective,
  mingRejectDirective,
  mingResolveDecisionsStream,
  mingCreateStructuredDirective,
  mingUpdateStructuredDirective,
  mingNewSession,
  mingMenuContinue,
  mingLoadSave,
  mingResetGame,
} from '../../lib/mingApi';
import {
  clearSalvageSessionPersist,
  isSalvageSessionPersisted,
  persistSalvageSession,
  readSalvageSession,
} from './mingSessionStorage';
import {
  loadCourtChatStreamSpeed,
  normalizeCourtChatStreamSpeed,
  saveCourtChatStreamSpeedLocal,
} from './mingCourtChatThrottle';
import {
  syncSalvagePlaythrough,
  tryCreateSalvagePlaythrough,
  type SalvageTurnChapterOptions,
} from './mingPlaythroughSync';

let settleAbortController: AbortController | null = null;

function clearSettleOverlay(extra?: Record<string, unknown>) {
  return {
    loading: false,
    settleStage: '',
    settleThinking: '',
    settleNarrative: '',
    ...extra,
  };
}

type MingStore = {
  active: boolean;
  activeSalvageScenarioId: ScenarioId | null;
  loading: boolean;
  error?: string;
  sessionId: string;
  gameSessionId: string;
  playthroughId: string;
  state?: MingGameState;
  salvageRaw?: SalvageGameState;
  nationState: NationState;
  characters: Character[];
  decreeText: string;
  lastReport: string;
  settleStage: string;
  settleThinking: string;
  settleNarrative: string;
  postSettleReport: string | null;
  chatHistory: MingChatMessage[];
  chatSuggestions: MingChatSuggestion[];
  streamingMinisterReply: string;
  pendingUserMessage: string;
  chatNotice: string;
  chatBusy: boolean;
  activeMinisterMeta: SalvageMinister | null;
  ministerSecretOrders: MingSecretOrder[];
  activeMinisterId: string | null;
  pendingDecisions: MingPendingDecision[];
  cheatDirective: string;
  menuHasMainDb: boolean;
  menuActiveSalvageId: string | null;
  boundScenarioId: string | null;
  scenarioProgress: Record<string, boolean>;
  courtChatStreamSpeed: number;
  uiResetNonce: number;

  handleStartGame: () => Promise<void>;
  handleContinueGame: () => Promise<void>;
  fetchMenuBootstrap: () => Promise<void>;
  setActiveSalvageScenarioId: (id: ScenarioId) => void;
  canContinueSalvageScenario: (id: ScenarioId) => boolean;
  setCourtChatStreamSpeed: (value: number, persistLocal?: boolean) => void;
  restoreSession: () => Promise<boolean>;
  handleExit: () => void;
  bootstrapFromSalvageRaw: (raw: SalvageGameState) => void;
  setCheatDirective: (text: string) => void;
  loadSave: (name: string) => Promise<void>;
  resetGame: () => Promise<void>;
  refreshState: () => Promise<void>;
  setActiveMinister: (id: string | null) => void;
  loadMinisterChat: () => Promise<void>;
  sendMinisterChat: (message: string) => Promise<void>;
  undoMinisterChat: () => Promise<void>;
  createMinisterSecretOrder: (title: string, content: string) => Promise<void>;
  uploadMinisterPortrait: (file: File) => Promise<void>;
  toggleMinisterFavorite: () => Promise<void>;
  archiveActiveMinister: () => Promise<void>;
  clearChatNotice: () => void;
  confirmDirective: (id: number) => Promise<void>;
  rejectDirective: (id: number) => Promise<void>;
  deleteDirective: (id: number) => Promise<void>;
  patchDirective: (id: number, text: string) => Promise<void>;
  confirmAllDirectives: () => Promise<void>;
  addManualDirective: (text: string) => Promise<void>;
  addCourtChatDirective: (option: string) => Promise<void>;
  saveStructuredDirective: (
    editing: MingStructuredDirective | null,
    templateId: string,
    fields: Record<string, string>,
  ) => Promise<void>;
  deleteStructuredDirective: (id: number) => Promise<void>;
  composeDecree: (force?: boolean) => Promise<void>;
  saveDecreeEdit: (text: string) => Promise<void>;
  issueDecree: () => Promise<void>;
  submitDecisions: (choices: Array<{ label?: string; hint?: string; note?: string }>) => Promise<void>;
  cancelSettlement: () => void;
  bumpUiReset: () => void;
  clearError: () => void;
  clearPostSettleReport: () => void;
};

function salvageCtx(scenarioId?: ScenarioId | null): SalvageAdapterContext {
  return { scenarioId: scenarioId || 'ming_wanli' };
}

function buildNationFromMing(state: MingGameState, scenarioId?: ScenarioId | null): NationState {
  const [yearStr, periodStr] = state.turn.label.match(/(\d+)年(\d+)月/)?.slice(1) || [];
  return buildNationFromSalvage(
    {
      turn: {
        year: yearStr ? Number(yearStr) : undefined,
        period: periodStr ? Number(periodStr) : undefined,
        turn: state.turn.turn,
      },
      metrics: state.metrics,
    },
    salvageCtx(
      scenarioId ??
        (state.scenario_id ? resolveFrontendScenarioFromSalvageId(state.scenario_id) : null),
    ),
  );
}

function applySalvageBootstrap(
  raw: SalvageGameState,
  st: MingGameState,
  scenarioId: ScenarioId,
): Pick<MingStore, 'state' | 'nationState' | 'characters' | 'decreeText' | 'lastReport'> {
  const ctx = salvageCtx(scenarioId);
  return {
    state: st,
    nationState: buildNationFromSalvage(raw, ctx),
    characters: mergeSalvageMinisters(raw, ctx),
    decreeText: st.last_decree || '',
    lastReport: st.last_report || '',
  };
}

function adaptStreamState(
  raw: SalvageGameState | MingGameState | undefined,
  prevSalvage?: SalvageGameState,
  scenarioId?: ScenarioId | null,
): MingGameState | undefined {
  if (!raw) return undefined;
  if ('session_id' in raw) return raw as MingGameState;
  const merged = mergeSalvageGameState(prevSalvage, raw as SalvageGameState);
  return adaptSalvageToMingGameState(merged, salvageCtx(scenarioId));
}

function adaptStreamSalvage(
  raw: SalvageGameState | MingGameState | undefined,
  prevSalvage?: SalvageGameState,
): SalvageGameState | undefined {
  if (!raw) return prevSalvage;
  if ('session_id' in raw) return prevSalvage;
  return mergeSalvageGameState(prevSalvage, raw as SalvageGameState);
}

function applyStreamSalvageUpdate(
  rawState: SalvageGameState | MingGameState | undefined,
  prevSalvage?: SalvageGameState,
  scenarioId?: ScenarioId | null,
): { st?: MingGameState; salvageRaw?: SalvageGameState; nationState?: NationState } {
  const salvageRaw = adaptStreamSalvage(rawState, prevSalvage);
  const st = adaptStreamState(rawState, prevSalvage, scenarioId);
  if (!st) return {};
  const ctx = salvageCtx(scenarioId);
  return {
    st,
    salvageRaw,
    nationState: salvageRaw ? buildNationFromSalvage(salvageRaw, ctx) : buildNationFromMing(st, scenarioId),
  };
}

function syncPendingFromState(st: MingGameState): MingPendingDecision[] {
  if (st.turn_phase !== 'awaiting_decision') return [];
  return st.pending_decisions?.length ? st.pending_decisions : [];
}

function scenarioBootstrapChars(scenarioId: ScenarioId): Character[] {
  return (
    getScenario(scenarioId)?.characters.filter(
      (c) => c.consultable !== false && c.id !== 'emperor',
    ) || []
  );
}

function applyPlaythroughSync(
  st?: MingGameState,
  playthroughId?: string,
  sessionId?: string,
  chapterOpts?: SalvageTurnChapterOptions,
) {
  const id = playthroughId || '';
  if (!id || !st) return;
  void syncSalvagePlaythrough(id, st, sessionId, chapterOpts);
}

export const useMingStore = create<MingStore>((set, get) => ({
  active: false,
  activeSalvageScenarioId: 'ming_wanli',
  loading: false,
  sessionId: '',
  gameSessionId: '',
  playthroughId: '',
  salvageRaw: undefined,
  nationState: getScenario('ming_wanli')!.nationState,
  characters: scenarioBootstrapChars('ming_wanli'),
  decreeText: '',
  lastReport: '',
  settleStage: '',
  settleThinking: '',
  settleNarrative: '',
  postSettleReport: null,
  chatHistory: [],
  chatSuggestions: [],
  streamingMinisterReply: '',
  pendingUserMessage: '',
  chatNotice: '',
  chatBusy: false,
  activeMinisterMeta: null,
  ministerSecretOrders: [],
  activeMinisterId: null,
  pendingDecisions: [],
  cheatDirective: '',
  menuHasMainDb: false,
  menuActiveSalvageId: null,
  boundScenarioId: null,
  scenarioProgress: {},
  courtChatStreamSpeed: loadCourtChatStreamSpeed(),
  uiResetNonce: 0,

  clearError: () => set({ error: undefined }),

  clearChatNotice: () => set({ chatNotice: '' }),

  clearPostSettleReport: () => set({ postSettleReport: null }),

  setCheatDirective: (text) => set({ cheatDirective: text }),

  bumpUiReset: () => {
    set((s) => ({
      uiResetNonce: s.uiResetNonce + 1,
      chatHistory: [],
      chatSuggestions: [],
      streamingMinisterReply: '',
      pendingUserMessage: '',
      chatNotice: '',
      chatBusy: false,
      activeMinisterId: null,
      activeMinisterMeta: null,
      ministerSecretOrders: [],
      settleStage: '',
      settleThinking: '',
      settleNarrative: '',
    }));
  },

  bootstrapFromSalvageRaw: (raw) => {
    const scenarioId = get().activeSalvageScenarioId || 'ming_wanli';
    const normalized = normalizeSalvageGameState(raw);
    const st = adaptSalvageToMingGameState(normalized, salvageCtx(scenarioId));
    set({
      salvageRaw: normalized,
      ...applySalvageBootstrap(normalized, st, scenarioId),
      pendingDecisions: syncPendingFromState(st),
    });
  },

  loadSave: async (name) => {
    const scenarioId = get().activeSalvageScenarioId || 'ming_wanli';
    const salvageScenarioId = resolveSalvageScenarioId(scenarioId);
    try {
      set({ loading: true, error: undefined });
      const out = await mingLoadSave(name, salvageScenarioId);
      const raw = normalizeSalvageGameState(out.state);
      const ctx = salvageCtx(scenarioId);
      const st = adaptSalvageToMingGameState(raw, ctx);
      const sessionId = salvageSessionId();
      const persisted = readSalvageSession();
      let playthroughId = persisted?.playthroughId || '';
      if (!playthroughId) {
        playthroughId = await tryCreateSalvagePlaythrough(scenarioId, sessionId, sessionId);
      }
      persistSalvageSession(scenarioId, playthroughId || undefined);
      set({
        active: true,
        loading: false,
        activeSalvageScenarioId: scenarioId,
        sessionId,
        gameSessionId: sessionId,
        playthroughId,
        salvageRaw: raw,
        menuHasMainDb: true,
        menuActiveSalvageId: salvageScenarioId,
        boundScenarioId: salvageScenarioId,
        scenarioProgress: { ...get().scenarioProgress, [salvageScenarioId]: true },
        state: st,
        nationState: buildNationFromSalvage(raw, ctx),
        characters: mergeSalvageMinisters(raw, ctx),
        decreeText: st.last_decree || '',
        lastReport: st.last_report || '',
        pendingDecisions: syncPendingFromState(st),
      });
      applyPlaythroughSync(st, playthroughId, get().sessionId);
      get().bumpUiReset();
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : String(e) });
      throw e;
    }
  },

  resetGame: async () => {
    try {
      set({ loading: true, error: undefined });
      const out = await mingResetGame();
      get().bootstrapFromSalvageRaw(out.state);
      set({ loading: false, cheatDirective: '', decreeText: '', postSettleReport: null });
      get().bumpUiReset();
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : String(e) });
      throw e;
    }
  },

  handleExit: () => {
    const { sessionId } = get();
    if (sessionId) void mingExitSession(sessionId).catch(() => undefined);
    clearSalvageSessionPersist();
    set({
      active: false,
      loading: false,
      sessionId: '',
      gameSessionId: '',
      playthroughId: '',
      state: undefined,
      decreeText: '',
      lastReport: '',
      chatHistory: [],
      activeMinisterId: null,
      settleStage: '',
      settleThinking: '',
      settleNarrative: '',
      postSettleReport: null,
      pendingDecisions: [],
      salvageRaw: undefined,
      error: undefined,
    });
  },

  handleStartGame: async () => {
    const scenarioId = get().activeSalvageScenarioId || 'ming_wanli';
    const salvageScenarioId = resolveSalvageScenarioId(scenarioId);
    try {
      const status = await mingFetchMenuStatus();
      if (
        status.has_main_db &&
        typeof window !== 'undefined' &&
        !window.confirm('将覆盖当前主进度，是否继续？建议先在游戏中保存为存档。')
      ) {
        return;
      }
      set({ loading: true, error: undefined, menuHasMainDb: status.has_main_db });
      const sessionId = salvageSessionId();
      const playthroughId = await tryCreateSalvagePlaythrough(scenarioId, sessionId, sessionId);
      const out = await mingNewSession({
        session_id: sessionId,
        game_session_id: sessionId,
        scenario_id: salvageScenarioId,
      });
      const raw = (out as { salvageRaw?: SalvageGameState }).salvageRaw;
      persistSalvageSession(scenarioId, playthroughId || undefined);
      set({
        active: true,
        loading: false,
        activeSalvageScenarioId: scenarioId,
        sessionId,
        gameSessionId: sessionId,
        playthroughId,
        salvageRaw: raw,
        menuHasMainDb: true,
        menuActiveSalvageId: salvageScenarioId,
        boundScenarioId: salvageScenarioId,
        scenarioProgress: { ...get().scenarioProgress, [salvageScenarioId]: true },
        ...(raw
          ? applySalvageBootstrap(raw, out.state, scenarioId)
          : {
              state: out.state,
              nationState: buildNationFromMing(out.state, scenarioId),
              decreeText: out.state.last_decree || '',
              lastReport: out.state.last_report || '',
            }),
        pendingDecisions: syncPendingFromState(out.state),
      });
      applyPlaythroughSync(out.state, playthroughId, sessionId);
      get().bumpUiReset();
    } catch (e) {
      set({
        loading: false,
        active: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  },

  setActiveSalvageScenarioId: (id) => {
    const scenario = getScenario(id);
    const { boundScenarioId } = get();
    const expected = resolveSalvageScenarioId(id);
    if (boundScenarioId && boundScenarioId !== expected) {
      clearSalvageSessionPersist();
    }
    set({
      activeSalvageScenarioId: id,
      nationState: scenario?.nationState ?? get().nationState,
      characters: scenarioBootstrapChars(id),
    });
  },

  canContinueSalvageScenario: (id) => {
    const salvageId = resolveSalvageScenarioId(id);
    const progress = get().scenarioProgress;
    if (salvageId in progress) return Boolean(progress[salvageId]);
    return get().menuHasMainDb && get().boundScenarioId === salvageId;
  },

  fetchMenuBootstrap: async () => {
    try {
      const status = await mingFetchMenuStatus();
      const activeId = status.active_scenario?.id?.trim() || null;
      const progress = status.scenario_progress ?? {};
      const scenarioId = get().activeSalvageScenarioId;
      const currentSalvage = scenarioId ? resolveSalvageScenarioId(scenarioId) : '';
      set({
        menuHasMainDb: currentSalvage ? Boolean(progress[currentSalvage]) : Boolean(status.has_main_db),
        menuActiveSalvageId: activeId,
        boundScenarioId: status.bound_scenario_id?.trim() || null,
        scenarioProgress: progress,
      });
      const configuredSpeed = Number(status.game_settings?.court_chat_stream_speed);
      if (Number.isFinite(configuredSpeed)) {
        get().setCourtChatStreamSpeed(configuredSpeed, false);
      }
    } catch {
      /* ignore */
    }
  },

  setCourtChatStreamSpeed: (value, persistLocal = true) => {
    const next = normalizeCourtChatStreamSpeed(value);
    if (persistLocal) saveCourtChatStreamSpeedLocal(next);
    set({ courtChatStreamSpeed: next });
  },

  handleContinueGame: async () => {
    const scenarioId = get().activeSalvageScenarioId || 'ming_wanli';
    const expected = resolveSalvageScenarioId(scenarioId);
    try {
      set({ loading: true, error: undefined });
      if (!get().canContinueSalvageScenario(scenarioId)) {
        throw new Error('该剧本暂无上次进度，请先开始新游戏。');
      }
      const sessionId = salvageSessionId();
      const persisted = readSalvageSession();
      let playthroughId = persisted?.playthroughId || '';
      if (!playthroughId) {
        playthroughId = await tryCreateSalvagePlaythrough(scenarioId, sessionId, sessionId);
      }
      const continueOut = await mingMenuContinue(expected);
      const raw = normalizeSalvageGameState(continueOut.state);
      const ctx = salvageCtx(scenarioId);
      const st = adaptSalvageToMingGameState(raw, ctx);
      persistSalvageSession(scenarioId, playthroughId || undefined);
      set({
        active: true,
        loading: false,
        activeSalvageScenarioId: scenarioId,
        sessionId,
        gameSessionId: sessionId,
        playthroughId,
        salvageRaw: raw,
        menuHasMainDb: true,
        menuActiveSalvageId: expected,
        boundScenarioId: expected,
        scenarioProgress: { ...get().scenarioProgress, [expected]: true },
        state: st,
        nationState: buildNationFromSalvage(raw, ctx),
        characters: mergeSalvageMinisters(raw, ctx),
        decreeText: st.last_decree || '',
        lastReport: st.last_report || '',
        pendingDecisions: syncPendingFromState(st),
        settleStage: '',
        settleThinking: '',
        settleNarrative: '',
      });
      applyPlaythroughSync(st, playthroughId, get().sessionId);
      get().bumpUiReset();
    } catch (e) {
      set({
        loading: false,
        active: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  },

  restoreSession: async () => {
    const persisted = readSalvageSession();
    if (!persisted && !isSalvageSessionPersisted()) return false;
    if (get().active && get().state) return true;
    const scenarioId = persisted?.scenarioId || 'ming_wanli';
    const expected = resolveSalvageScenarioId(scenarioId);
    try {
      set({ loading: true, error: undefined, activeSalvageScenarioId: scenarioId });
      const status = await mingFetchMenuStatus(expected);
      const progress = status.scenario_progress ?? {};
      if (!status.has_running_game && !progress[expected]) {
        clearSalvageSessionPersist();
        set({ loading: false, active: false });
        return false;
      }
      const sessionId = salvageSessionId();
      let playthroughId = persisted?.playthroughId || '';
      if (!playthroughId) {
        playthroughId = await tryCreateSalvagePlaythrough(scenarioId, sessionId, sessionId);
      }
      persistSalvageSession(scenarioId, playthroughId || undefined);
      const continueOut = await mingMenuContinue(expected);
      const raw = normalizeSalvageGameState(continueOut.state);
      const ctx = salvageCtx(scenarioId);
      const st = adaptSalvageToMingGameState(raw, ctx);
      set({
        active: true,
        loading: false,
        activeSalvageScenarioId: scenarioId,
        sessionId,
        gameSessionId: sessionId,
        playthroughId,
        salvageRaw: raw,
        menuHasMainDb: Boolean(progress[expected] ?? status.has_main_db),
        menuActiveSalvageId: expected,
        boundScenarioId: expected,
        scenarioProgress: { ...progress, [expected]: true },
        state: st,
        nationState: buildNationFromSalvage(raw, ctx),
        characters: mergeSalvageMinisters(raw, ctx),
        decreeText: st.last_decree || '',
        lastReport: st.last_report || '',
        pendingDecisions: syncPendingFromState(st),
        settleStage: '',
        settleNarrative: '',
      });
      applyPlaythroughSync(st, playthroughId, get().sessionId);
      return true;
    } catch (e) {
      set({
        loading: false,
        active: false,
        error: e instanceof Error ? e.message : String(e),
      });
      return false;
    }
  },

  refreshState: async () => {
    const { sessionId, activeSalvageScenarioId, playthroughId } = get();
    if (!sessionId) return;
    const scenarioId = activeSalvageScenarioId || 'ming_wanli';
    const ctx = salvageCtx(scenarioId);
    const out = await mingFetchState(sessionId);
    const salvageRaw = out.salvageRaw ? normalizeSalvageGameState(out.salvageRaw) : get().salvageRaw;
    const st = out.state;
    set({
      state: st,
      nationState: salvageRaw ? buildNationFromSalvage(salvageRaw, ctx) : buildNationFromMing(st, scenarioId),
      salvageRaw,
      characters: salvageRaw ? mergeSalvageMinisters(salvageRaw, ctx) : get().characters,
      decreeText: st.last_decree || get().decreeText,
      lastReport: st.last_report || get().lastReport,
      pendingDecisions: syncPendingFromState(st),
    });
    applyPlaythroughSync(st, playthroughId, get().sessionId);
  },

  setActiveMinister: (id) => {
    set({
      activeMinisterId: id,
      chatHistory: [],
      chatSuggestions: [],
      streamingMinisterReply: '',
      pendingUserMessage: '',
      chatNotice: '',
      activeMinisterMeta: null,
      ministerSecretOrders: [],
    });
    if (id) void get().loadMinisterChat();
  },

  loadMinisterChat: async () => {
    const { activeMinisterId, characters } = get();
    if (!activeMinisterId) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      const [chatOut, ordersOut] = await Promise.all([
        mingFetchMinisterChat(name),
        mingFetchSecretOrders().catch(() => ({ orders: [] as MingSecretOrder[] })),
      ]);
      const minister = chatOut.minister as SalvageMinister;
      set({
        chatHistory: chatOut.history as MingChatMessage[],
        chatSuggestions: chatOut.suggestions,
        activeMinisterMeta: minister?.name ? minister : null,
        ministerSecretOrders: (ordersOut.orders || []).filter(
          (o) => o.minister_name === name && (o.status === 'active' || o.status === 'pending_review'),
        ),
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  sendMinisterChat: async (message) => {
    const { activeMinisterId, characters } = get();
    if (!activeMinisterId || !message.trim()) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    const trimmed = message.trim();
    try {
      set({
        chatBusy: true,
        error: undefined,
        pendingUserMessage: trimmed,
        streamingMinisterReply: '',
        chatNotice: '',
      });
      const done = await mingMinisterChatStream(name, trimmed, (delta) => {
        set((s) => ({ streamingMinisterReply: `${s.streamingMinisterReply}${delta}` }));
      });
      let notice = '';
      if (done.secret_order_id) {
        notice = `密令已秘密交付${name}，编号 #${done.secret_order_id}。`;
      } else if (done.proposed_directive) {
        notice = `${name}已拟旨一道，待陛下在「诏书草案」核定（准/驳）。`;
      } else if (done.court_action === 'dismiss') {
        notice = `${name}已退下。请择下一位大臣。`;
      }
      if (done.proposed_directive || done.directives) {
        await get().refreshState();
      } else if (done.secret_order_id) {
        const ordersOut = await mingFetchSecretOrders().catch(() => ({ orders: [] as MingSecretOrder[] }));
        set({
          ministerSecretOrders: (ordersOut.orders || []).filter(
            (o) => o.minister_name === name && (o.status === 'active' || o.status === 'pending_review'),
          ),
        });
      }
      set({
        chatBusy: false,
        pendingUserMessage: '',
        streamingMinisterReply: '',
        chatHistory: done.history as MingChatMessage[],
        chatSuggestions: done.suggestions,
        chatNotice: notice,
      });
      if (done.next_minister) {
        const next = characters.find((c) => c.name === done.next_minister);
        if (next) {
          set({ activeMinisterId: next.id, chatNotice: `已传${done.next_minister}入殿。` });
          void get().loadMinisterChat();
        }
      }
    } catch (e) {
      set({
        chatBusy: false,
        pendingUserMessage: '',
        streamingMinisterReply: '',
        error: e instanceof Error ? e.message : String(e),
      });
    }
  },

  undoMinisterChat: async () => {
    const { activeMinisterId, characters, chatBusy } = get();
    if (!activeMinisterId || chatBusy) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      set({ chatBusy: true, error: undefined, chatNotice: '' });
      const out = await mingUndoMinisterChat(name);
      set((s) => ({
        chatBusy: false,
        chatHistory: out.history as MingChatMessage[],
        chatSuggestions: out.suggestions,
        chatNotice: '已撤回上一轮召对。',
        state: s.state
          ? { ...s.state, directives: out.directives, pending_count: out.pending_count }
          : s.state,
      }));
    } catch (e) {
      set({ chatBusy: false, error: e instanceof Error ? e.message : String(e) });
    }
  },

  createMinisterSecretOrder: async (title, content) => {
    const { activeMinisterId, characters } = get();
    if (!activeMinisterId) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      set({ chatBusy: true, error: undefined });
      const out = await mingCreateMinisterSecretOrder(name, { title, content });
      const ordersOut = await mingFetchSecretOrders();
      set({
        chatBusy: false,
        chatNotice: `密令「${out.title}」已下达，编号 #${out.order_id}。`,
        ministerSecretOrders: (ordersOut.orders || []).filter(
          (o) => o.minister_name === name && (o.status === 'active' || o.status === 'pending_review'),
        ),
      });
    } catch (e) {
      set({ chatBusy: false, error: e instanceof Error ? e.message : String(e) });
    }
  },

  uploadMinisterPortrait: async (file) => {
    const { activeMinisterId, characters } = get();
    if (!activeMinisterId) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      set({ chatBusy: true, error: undefined });
      await mingUploadMinisterPortrait(name, file);
      await get().refreshState();
      await get().loadMinisterChat();
      set({ chatBusy: false, chatNotice: '立绘已更新。' });
    } catch (e) {
      set({ chatBusy: false, error: e instanceof Error ? e.message : String(e) });
    }
  },

  toggleMinisterFavorite: async () => {
    const { activeMinisterId, characters, activeMinisterMeta } = get();
    if (!activeMinisterId) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      if (activeMinisterMeta?.favorite) {
        await mingRemoveFavorite(name);
      } else {
        await mingAddFavorite(name);
      }
      await get().refreshState();
      await get().loadMinisterChat();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  archiveActiveMinister: async () => {
    const { activeMinisterId, characters } = get();
    if (!activeMinisterId) return;
    const name = resolveMinisterName(activeMinisterId, characters);
    try {
      await mingArchiveMinister(name);
      await get().refreshState();
      set({
        activeMinisterId: null,
        chatHistory: [],
        chatSuggestions: [],
        activeMinisterMeta: null,
        ministerSecretOrders: [],
        chatNotice: `${name}已归档。`,
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  confirmDirective: async (id) => {
    const { sessionId } = get();
    if (!sessionId) return;
    await mingConfirmDirective(sessionId, id);
    await get().refreshState();
  },

  rejectDirective: async (id) => {
    const { sessionId } = get();
    if (!sessionId) return;
    await mingRejectDirective(sessionId, id);
    await get().refreshState();
  },

  deleteDirective: async (id) => {
    const { sessionId } = get();
    if (!sessionId) return;
    await mingDeleteDirective(sessionId, id);
    await get().refreshState();
  },

  patchDirective: async (id, text) => {
    const { sessionId } = get();
    if (!sessionId || !text.trim()) return;
    await mingPatchDirective(sessionId, id, text.trim());
    await get().refreshState();
  },

  confirmAllDirectives: async () => {
    const { sessionId, state } = get();
    if (!sessionId || !state) return;
    const pending = state.directives.filter((d) => d.status === 'pending');
    for (const d of pending) {
      await mingConfirmDirective(sessionId, d.id);
    }
    await get().refreshState();
  },

  saveStructuredDirective: async (editing, templateId, fields) => {
    const { sessionId } = get();
    if (!sessionId) return;
    if (editing) {
      await mingUpdateStructuredDirective(editing.id, templateId, fields);
    } else {
      await mingCreateStructuredDirective(templateId, fields);
    }
    await get().refreshState();
  },

  deleteStructuredDirective: async (id) => {
    const { sessionId } = get();
    if (!sessionId) return;
    await mingDeleteStructuredDirective(id);
    await get().refreshState();
  },

  addManualDirective: async (text) => {
    const { sessionId } = get();
    if (!sessionId || !text.trim()) return;
    await mingCreateDirective({ session_id: sessionId, text: text.trim(), status: 'draft' });
    await get().refreshState();
  },

  addCourtChatDirective: async (option) => {
    const { sessionId } = get();
    const trimmed = option.trim();
    if (!sessionId || !trimmed) return;
    await mingCreateDirective({
      session_id: sessionId,
      text: `朝会裁断：${trimmed}`,
      notes: '由本月朝会结论转入草案',
    });
    await get().refreshState();
  },

  composeDecree: async (force = false) => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      const out = await mingComposeDecree(sessionId, force);
      set({ decreeText: out.decree });
      await mingEditDecree(sessionId, out.decree);
      await get().refreshState();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  saveDecreeEdit: async (text) => {
    const { sessionId } = get();
    if (!sessionId) return;
    await mingEditDecree(sessionId, text);
    set({ decreeText: text });
  },

  issueDecree: async () => {
    const { sessionId, cheatDirective } = get();
    if (!sessionId) return;
    settleAbortController?.abort();
    const abort = new AbortController();
    settleAbortController = abort;
    const cheatPayload = cheatDirective.trim();
    try {
      set({ loading: true, settleStage: '连接推演…', settleThinking: '', settleNarrative: '', postSettleReport: null, error: undefined });
      const outcome = await mingIssueDecreeStream(sessionId, (kind, data) => {
        if (kind === 'stage') {
          set({ settleStage: String(data.content || '') });
        } else if (kind === 'thinking') {
          set((s) => ({ settleThinking: `${s.settleThinking}${data.content || ''}` }));
        } else if (kind === 'text') {
          set((s) => ({ settleNarrative: `${s.settleNarrative}${data.content || ''}` }));
        }
      }, cheatPayload, undefined, abort.signal);
      if (cheatPayload) set({ cheatDirective: '' });
      if (outcome.kind === 'error') {
        set(clearSettleOverlay({ error: outcome.message }));
        return;
      }
      if (outcome.kind === 'decisions') {
        const decisions = parsePendingDecisions(outcome.data.decisions);
        const rawState = outcome.data.state as SalvageGameState | MingGameState | undefined;
        const applied = applyStreamSalvageUpdate(rawState, get().salvageRaw, get().activeSalvageScenarioId);
        const decree = String(outcome.data.decree || '');
        set({
          ...clearSettleOverlay(),
          pendingDecisions: decisions,
          ...(applied.st ? { state: applied.st, nationState: applied.nationState! } : {}),
          ...(applied.salvageRaw ? { salvageRaw: applied.salvageRaw } : {}),
          ...(decree ? { decreeText: decree } : {}),
        });
        if (applied.st) applyPlaythroughSync(applied.st, get().playthroughId, get().sessionId);
        return;
      }
      const rawState = outcome.data.state as SalvageGameState | MingGameState | undefined;
      const applied = applyStreamSalvageUpdate(rawState, get().salvageRaw, get().activeSalvageScenarioId);
      const report = String(outcome.data.report || applied.st?.last_report || '');
      const decreeForArchive = String(
        outcome.data.decree || get().decreeText || applied.st?.last_decree || '',
      ).trim();
      if (applied.st) {
        const settledTurn = Math.max(1, Number(applied.st.turn?.turn) - 1);
        set({
          ...clearSettleOverlay({
            state: applied.st,
            nationState: applied.nationState!,
            lastReport: report,
            decreeText: '',
            postSettleReport: report.trim() ? report : null,
            ...(applied.salvageRaw ? { salvageRaw: applied.salvageRaw } : {}),
          }),
        });
        applyPlaythroughSync(applied.st, get().playthroughId, get().sessionId, {
          report: report.trim(),
          decree: decreeForArchive,
          reportingTurn: settledTurn,
        });
        get().bumpUiReset();
      } else {
        set(clearSettleOverlay());
        await get().refreshState();
        get().bumpUiReset();
      }
    } catch (e) {
      if (abort.signal.aborted) {
        set(clearSettleOverlay());
        return;
      }
      set(clearSettleOverlay({ error: e instanceof Error ? e.message : String(e) }));
    } finally {
      if (settleAbortController === abort) settleAbortController = null;
    }
  },

  cancelSettlement: () => {
    settleAbortController?.abort();
    settleAbortController = null;
    set(clearSettleOverlay());
  },

  submitDecisions: async (choices) => {
    const { sessionId, cheatDirective } = get();
    if (!sessionId || !choices.length) return;
    settleAbortController?.abort();
    const abort = new AbortController();
    settleAbortController = abort;
    const cheatPayload = cheatDirective.trim();
    try {
      set({
        loading: true,
        pendingDecisions: [],
        settleStage: '圣意亲裁，续推时局',
        settleThinking: '',
        settleNarrative: '',
        error: undefined,
      });
      const outcome = await mingResolveDecisionsStream(
        sessionId,
        choices,
        (kind, data) => {
          if (kind === 'stage') {
            set({ settleStage: String(data.content || '') });
          } else if (kind === 'thinking') {
            set((s) => ({ settleThinking: `${s.settleThinking}${data.content || ''}` }));
          } else if (kind === 'text') {
            set((s) => ({ settleNarrative: `${s.settleNarrative}${data.content || ''}` }));
          }
        },
        cheatPayload,
        undefined,
        abort.signal,
      );
      if (cheatPayload) set({ cheatDirective: '' });
      if (outcome.kind === 'error') {
        set(clearSettleOverlay({ error: outcome.message }));
        return;
      }
      if (outcome.kind === 'decisions') {
        const decisions = parsePendingDecisions(outcome.data.decisions);
        const rawState = outcome.data.state as SalvageGameState | MingGameState | undefined;
        const applied = applyStreamSalvageUpdate(rawState, get().salvageRaw, get().activeSalvageScenarioId);
        const decree = String(outcome.data.decree || '');
        set({
          ...clearSettleOverlay(),
          pendingDecisions: decisions,
          ...(applied.st ? { state: applied.st, nationState: applied.nationState! } : {}),
          ...(applied.salvageRaw ? { salvageRaw: applied.salvageRaw } : {}),
          ...(decree ? { decreeText: decree } : {}),
        });
        if (applied.st) applyPlaythroughSync(applied.st, get().playthroughId, get().sessionId);
        return;
      }
      const rawState = outcome.data.state as SalvageGameState | MingGameState | undefined;
      const applied = applyStreamSalvageUpdate(rawState, get().salvageRaw, get().activeSalvageScenarioId);
      const report = String(outcome.data.report || applied.st?.last_report || '');
      const decreeForArchive = String(
        outcome.data.decree || get().decreeText || applied.st?.last_decree || '',
      ).trim();
      if (applied.st) {
        const settledTurn = Math.max(1, Number(applied.st.turn?.turn) - 1);
        set({
          ...clearSettleOverlay({
            state: applied.st,
            nationState: applied.nationState!,
            lastReport: report,
            decreeText: '',
            pendingDecisions: [],
            postSettleReport: report.trim() ? report : null,
            ...(applied.salvageRaw ? { salvageRaw: applied.salvageRaw } : {}),
          }),
        });
        applyPlaythroughSync(applied.st, get().playthroughId, get().sessionId, {
          report: report.trim(),
          decree: decreeForArchive,
          reportingTurn: settledTurn,
        });
        get().bumpUiReset();
      } else {
        set(clearSettleOverlay({ pendingDecisions: [] }));
        await get().refreshState();
        get().bumpUiReset();
      }
    } catch (e) {
      if (abort.signal.aborted) {
        set(clearSettleOverlay());
        return;
      }
      set(clearSettleOverlay({ error: e instanceof Error ? e.message : String(e) }));
    } finally {
      if (settleAbortController === abort) settleAbortController = null;
    }
  },
}));

export function mingPhaseAllowsChat(phase: MingTurnPhase | undefined): boolean {
  return phase === 'summoning' || phase === 'reviewing';
}
