import type { SalvageMinister } from '../game/ming/salvageStateTypes';
import type {
  MingDirective,
  MingGameState,
  MingSettleStreamOutcome,
  MingExtractionData,
  MingSecretOrder,
  MingHistoryTurnItem,
  MingHistoryDetail,
  MingStructuredDirectiveTemplate,
  MingStructuredDirective,
  MingCourtChatMessage,
  MingCourtChatResponse,
  MingSaveEntry,
  MingLlmConfig,
  MingGameSettings,
} from '../game/ming/mingTurnPhase';
import {
  adaptSalvageToMingGameState,
  formatSalvageApiError,
  normalizeSalvageGameState,
  mergeSalvageGameState,
  resolveMinisterName,
  salvageSessionId,
  type SalvageGameState,
  type SalvageAdapterContext,
} from './mingSalvageAdapter';
import { resolveFrontendScenarioFromSalvageId, type ScenarioId } from '../game/scenarios';

function frontendScenarioFromSalvageId(salvageId: string): ScenarioId {
  return resolveFrontendScenarioFromSalvageId(salvageId);
}

export type ApiConfig = {
  baseUrl?: string;
};

function getSalvageBaseUrl(config?: ApiConfig): string {
  if (config?.baseUrl) return config.baseUrl.replace(/\/+$/, '');
  const env = process.env.NEXT_PUBLIC_MING_SALVAGE_URL;
  if (env?.trim()) return env.trim().replace(/\/+$/, '');
  if (typeof window !== 'undefined') {
    // 开发环境直连 :8010，避免 Next 反代缓冲 SSE（CORS 已在 salvage 后端放行 localhost:*）
    if (process.env.NODE_ENV === 'development') {
      return 'http://127.0.0.1:8010';
    }
    return `${window.location.origin}/api/ming-salvage`.replace(/\/+$/, '');
  }
  const proxy = process.env.MING_SALVAGE_PROXY_URL || 'http://127.0.0.1:8010';
  return proxy.replace(/\/+$/, '');
}

async function salvageFetch<T>(
  path: string,
  init?: RequestInit,
  config?: ApiConfig,
): Promise<T> {
  const base = getSalvageBaseUrl(config);
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`;
  const resp = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => '');
    throw new Error(formatSalvageApiError(detail, resp.status));
  }
  return (await resp.json()) as T;
}

function mapDirectivesPayload(raw: {
  directives?: SalvageGameState['directives'];
  pending_count?: number;
}): { ok: boolean; directives: MingDirective[]; pending_count: number } {
  const directives: MingDirective[] = (raw.directives || []).map((d) => ({
    id: Number(d.id),
    text: String(d.text || ''),
    status: (d.status || 'draft') as MingDirective['status'],
    actor: d.actor,
    notes: d.notes,
  }));
  return {
    ok: true,
    directives,
    pending_count: Number(raw.pending_count ?? 0),
  };
}

export function mingActivateScenario(
  scenarioId: string,
  config?: ApiConfig,
): Promise<{ active_id: string }> {
  return salvageFetch<{ active_id: string }>(
    `/api/scenarios/${encodeURIComponent(scenarioId)}/activate`,
    { method: 'POST' },
    config,
  );
}

export function mingNewSession(
  payload: {
    session_id?: string;
    game_session_id?: string;
    scenario_id?: string;
    data_root?: string;
  },
  config?: ApiConfig,
): Promise<{ ok: boolean; state: MingGameState; salvageRaw?: SalvageGameState }> {
  const scenarioId = payload.scenario_id || 'ming_wanli';
  const adapterCtx: SalvageAdapterContext = {
    scenarioId: frontendScenarioFromSalvageId(scenarioId),
  };
  const activateFirst = payload.scenario_id
    ? mingActivateScenario(payload.scenario_id, config).catch(() => undefined)
    : Promise.resolve(undefined);

  return activateFirst.then(() =>
    salvageFetch<{ state: SalvageGameState }>(
      '/api/menu/new_game',
      { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId }) },
      config,
    ).then(
      (out) => {
        const salvageRaw = normalizeSalvageGameState(out.state || {});
        return {
          ok: true,
          state: adaptSalvageToMingGameState(salvageRaw, adapterCtx),
          salvageRaw,
        };
      },
    ),
  );
}

export function mingFetchMenuStatus(
  scenarioId?: string,
  config?: ApiConfig,
): Promise<{
  ok: boolean;
  has_running_game: boolean;
  has_main_db: boolean;
  has_api_key: boolean;
  active_scenario?: { id?: string; name?: string } | null;
  bound_scenario_id?: string | null;
  running_scenario_id?: string | null;
  scenario_progress?: Record<string, boolean>;
  game_settings?: MingGameSettings;
  saves?: MingSaveEntry[];
}> {
  const query = scenarioId?.trim()
    ? `?scenario_id=${encodeURIComponent(scenarioId.trim())}`
    : '';
  return salvageFetch<{
    has_running_game?: boolean;
    has_main_db?: boolean;
    has_api_key?: boolean;
    active_scenario?: { id?: string; name?: string } | null;
    bound_scenario_id?: string | null;
    running_scenario_id?: string | null;
    scenario_progress?: Record<string, boolean>;
    game_settings?: MingGameSettings;
    saves?: MingSaveEntry[];
  }>(`/api/menu/status${query}`, { method: 'GET' }, config).then((raw) => ({
    ok: true,
    has_running_game: Boolean(raw.has_running_game),
    has_main_db: Boolean(raw.has_main_db),
    has_api_key: Boolean(raw.has_api_key),
    active_scenario: raw.active_scenario ?? null,
    bound_scenario_id: raw.bound_scenario_id?.trim() || null,
    running_scenario_id: raw.running_scenario_id?.trim() || null,
    scenario_progress: raw.scenario_progress ?? undefined,
    game_settings: raw.game_settings,
    saves: raw.saves,
  }));
}

export function mingFetchCourtLayout(
  config?: ApiConfig,
): Promise<Record<string, { px: number; py: number }>> {
  return salvageFetch<{ layout?: string }>('/api/court_layout', { method: 'GET' }, config)
    .then((raw) => {
      try {
        return JSON.parse(raw.layout || '{}') as Record<string, { px: number; py: number }>;
      } catch {
        return {};
      }
    })
    .catch(() => ({}));
}

export function mingSaveCourtLayout(
  layout: Record<string, { px: number; py: number }>,
  config?: ApiConfig,
): Promise<void> {
  return salvageFetch('/api/court_layout', {
    method: 'POST',
    body: JSON.stringify({ layout: JSON.stringify(layout) }),
  }, config).then(() => undefined);
}

export function mingFetchState(
  _sessionId: string,
  config?: ApiConfig,
): Promise<{ ok: boolean; state: MingGameState; salvageRaw?: SalvageGameState }> {
  return salvageFetch<SalvageGameState>('/api/game/state', { method: 'GET' }, config).then((raw) => {
    const salvageRaw = normalizeSalvageGameState(raw);
    return {
      ok: true,
      state: adaptSalvageToMingGameState(salvageRaw),
      salvageRaw,
    };
  });
}

export function mingFetchMap(config?: ApiConfig): Promise<{ nodes: SalvageGameState['map_nodes'] }> {
  return salvageFetch<{ nodes?: SalvageGameState['map_nodes'] }>('/api/map', { method: 'GET' }, config).then(
    (raw) => ({
      nodes: raw.nodes || [],
    }),
  );
}

export function mingCreateDirective(
  payload: {
    session_id: string;
    text: string;
    actor?: string;
    notes?: string;
    status?: string;
  },
  config?: ApiConfig,
): Promise<{ ok: boolean; directives: MingDirective[]; pending_count: number }> {
  return salvageFetch<{ directives?: SalvageGameState['directives'] }>(
    '/api/directives',
    {
      method: 'POST',
      body: JSON.stringify({
        text: payload.text,
        notes: payload.notes || '',
      }),
    },
    config,
  ).then((raw) => mapDirectivesPayload(raw));
}

export function mingConfirmDirective(
  _sessionId: string,
  directiveId: number,
  config?: ApiConfig,
): Promise<{ ok: boolean; directives: MingDirective[]; pending_count: number }> {
  return salvageFetch<{ directives?: SalvageGameState['directives']; pending_count?: number }>(
    `/api/directives/${directiveId}/confirm`,
    { method: 'POST', body: '{}' },
    config,
  ).then((raw) => mapDirectivesPayload(raw));
}

export function mingRejectDirective(
  _sessionId: string,
  directiveId: number,
  config?: ApiConfig,
): Promise<{ ok: boolean; directives: MingDirective[]; pending_count: number }> {
  return salvageFetch<{ directives?: SalvageGameState['directives']; pending_count?: number }>(
    `/api/directives/${directiveId}/reject`,
    { method: 'POST', body: '{}' },
    config,
  ).then((raw) => mapDirectivesPayload(raw));
}

export function mingDeleteDirective(
  _sessionId: string,
  directiveId: number,
  config?: ApiConfig,
): Promise<{ ok: boolean; directives: MingDirective[]; pending_count: number }> {
  return salvageFetch<{ directives?: SalvageGameState['directives'] }>(
    `/api/directives/${directiveId}`,
    { method: 'DELETE' },
    config,
  ).then((raw) => mapDirectivesPayload(raw));
}

export function mingMinisterChat(
  payload: {
    session_id: string;
    character_id: string;
    message: string;
    capture_directive?: boolean;
    metrics?: Record<string, number>;
    minister_name?: string;
  },
  config?: ApiConfig,
): Promise<{
  ok: boolean;
  reply: string;
  proposed_directive?: MingDirective | null;
  history: Array<{ role: string; content: string }>;
}> {
  const ministerName =
    payload.minister_name ||
    resolveMinisterName(payload.character_id, []);
  return salvageFetch<{
    answer?: string;
    history?: Array<{ role: string; content: string }>;
    proposed_directive?: { id: number; text: string; status: string; notes?: string };
    pending_count?: number;
  }>(
    `/api/ministers/${encodeURIComponent(ministerName)}/chat`,
    {
      method: 'POST',
      body: JSON.stringify({ message: payload.message }),
    },
    config,
  ).then((out) => ({
    ok: true,
    reply: String(out.answer || ''),
    proposed_directive: out.proposed_directive
      ? {
          id: Number(out.proposed_directive.id),
          text: String(out.proposed_directive.text || ''),
          status: (out.proposed_directive.status || 'pending') as MingDirective['status'],
          notes: out.proposed_directive.notes,
        }
      : null,
    history: (out.history || []).map((m) => ({
      role: m.role === 'minister' ? 'assistant' : m.role,
      content: m.content,
    })),
  }));
}

export function getMingSalvageAssetUrl(path: string, config?: ApiConfig): string {
  const base = getSalvageBaseUrl(config);
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

export function mingFetchMinisterChat(
  ministerName: string,
  config?: ApiConfig,
): Promise<{
  minister: Record<string, unknown>;
  history: Array<{ role: string; content: string }>;
  suggestions: Array<{ label: string; text: string; prefix?: boolean }>;
}> {
  return salvageFetch<{
    minister?: Record<string, unknown>;
    history?: Array<{ role: string; content: string }>;
    suggestions?: Array<{ label: string; text: string; prefix?: boolean }>;
  }>(`/api/ministers/${encodeURIComponent(ministerName)}/chat`, { method: 'GET' }, config).then(
    (out) => ({
      minister: out.minister || {},
      history: out.history || [],
      suggestions: out.suggestions || [],
    }),
  );
}

function parseMinisterChatDone(raw: Record<string, unknown>): import('../game/ming/mingTurnPhase').MingMinisterChatDone {
  const proposed = raw.proposed_directive as Record<string, unknown> | null | undefined;
  const directives = Array.isArray(raw.directives)
    ? (raw.directives as Array<Record<string, unknown>>).map((d) => ({
        id: Number(d.id),
        text: String(d.text || ''),
        status: (d.status || 'draft') as MingDirective['status'],
        actor: d.actor ? String(d.actor) : undefined,
        notes: d.notes ? String(d.notes) : undefined,
      }))
    : undefined;
  return {
    answer: String(raw.answer || ''),
    history: (Array.isArray(raw.history) ? raw.history : []) as Array<{ role: string; content: string }>,
    suggestions: (Array.isArray(raw.suggestions) ? raw.suggestions : []) as Array<{
      label: string;
      text: string;
      prefix?: boolean;
    }>,
    directives,
    pending_count: raw.pending_count != null ? Number(raw.pending_count) : undefined,
    court_action: raw.court_action ? String(raw.court_action) : undefined,
    next_minister: raw.next_minister ? String(raw.next_minister) : undefined,
    proposed_directive: proposed
      ? {
          id: Number(proposed.id),
          text: String(proposed.text || ''),
          status: (proposed.status || 'pending') as MingDirective['status'],
          notes: proposed.notes ? String(proposed.notes) : undefined,
        }
      : null,
    secret_order_id: raw.secret_order_id != null ? Number(raw.secret_order_id) : undefined,
  };
}

export async function mingMinisterChatStream(
  ministerName: string,
  message: string,
  onDelta: (delta: string) => void,
  config?: ApiConfig,
): Promise<import('../game/ming/mingTurnPhase').MingMinisterChatDone> {
  const base = getSalvageBaseUrl(config);
  const resp = await fetch(`${base}/api/ministers/${encodeURIComponent(ministerName)}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => '');
    throw new Error(formatSalvageApiError(detail, resp.status));
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      let evName = '';
      let dataRaw = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) evName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataRaw += line.slice(6);
      }
      if (!evName || !dataRaw) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataRaw) as Record<string, unknown>;
      } catch {
        data = { content: dataRaw };
      }
      if (evName === 'delta') {
        onDelta(String(data.content || ''));
      } else if (evName === 'done') {
        return parseMinisterChatDone(data);
      } else if (evName === 'error') {
        const msg =
          typeof data.message === 'string'
            ? data.message
            : typeof data.detail === 'string'
              ? data.detail
              : '流式回复失败';
        throw new Error(msg);
      }
    }
  }
  throw new Error('流式回复中断，未收到完成事件。');
}

export function mingUndoMinisterChat(
  ministerName: string,
  config?: ApiConfig,
): Promise<{
  history: Array<{ role: string; content: string }>;
  suggestions: Array<{ label: string; text: string; prefix?: boolean }>;
  directives: MingDirective[];
  pending_count: number;
}> {
  return salvageFetch<{
    history?: Array<{ role: string; content: string }>;
    suggestions?: Array<{ label: string; text: string; prefix?: boolean }>;
    directives?: SalvageGameState['directives'];
    pending_count?: number;
  }>(
    `/api/ministers/${encodeURIComponent(ministerName)}/chat/undo`,
    { method: 'POST', body: '{}' },
    config,
  ).then((out) => ({
    history: out.history || [],
    suggestions: out.suggestions || [],
    directives: (out.directives || []).map((d) => ({
      id: Number(d!.id),
      text: String(d!.text || ''),
      status: (d!.status || 'draft') as MingDirective['status'],
      actor: d!.actor,
      notes: d!.notes,
    })),
    pending_count: Number(out.pending_count ?? 0),
  }));
}

export function mingCreateMinisterSecretOrder(
  ministerName: string,
  payload: { title: string; content: string; tags?: string[]; deadline_months?: number },
  config?: ApiConfig,
): Promise<{ order_id: number; minister_name: string; title: string; status: string }> {
  return salvageFetch<{ order_id: number; minister_name: string; title: string; status: string }>(
    `/api/ministers/${encodeURIComponent(ministerName)}/secret_order`,
    {
      method: 'POST',
      body: JSON.stringify({
        title: payload.title,
        content: payload.content,
        tags: payload.tags || [],
        deadline_months: payload.deadline_months ?? 0,
      }),
    },
    config,
  );
}

export async function mingUploadMinisterPortrait(
  ministerName: string,
  file: File,
  config?: ApiConfig,
): Promise<{ name: string; portrait_id: string }> {
  const base = getSalvageBaseUrl(config);
  const form = new FormData();
  form.append('file', file);
  const resp = await fetch(`${base}/api/consorts/${encodeURIComponent(ministerName)}/portrait`, {
    method: 'POST',
    body: form,
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => '');
    throw new Error(formatSalvageApiError(detail, resp.status));
  }
  return (await resp.json()) as { name: string; portrait_id: string };
}

export function mingFetchConsortCandidates(
  config?: ApiConfig,
): Promise<{ candidates: SalvageMinister[] }> {
  return salvageFetch<{ candidates?: SalvageMinister[] }>(
    '/api/consorts/candidates',
    { method: 'GET' },
    config,
  ).then((raw) => ({ candidates: raw.candidates || [] }));
}

export function mingSelectConsort(
  name: string,
  config?: ApiConfig,
): Promise<{ selected: SalvageMinister }> {
  return salvageFetch<{ selected: SalvageMinister }>(
    `/api/consorts/${encodeURIComponent(name)}/select`,
    { method: 'POST' },
    config,
  );
}

export function mingCourtChatSummary(
  messages: Array<{ role: string; speaker: string; content: string }>,
  config?: ApiConfig,
): Promise<{
  role: string;
  speaker: string;
  content: string;
  displayContent: string;
  options?: string[];
}> {
  return salvageFetch<{
    role?: string;
    speaker?: string;
    content?: string;
    summary?: string;
    options?: string[];
  }>(
    '/api/court_chat/summary',
    { method: 'POST', body: JSON.stringify({ messages }) },
    config,
  ).then((raw) => {
    const content = String(raw.content || raw.summary || '');
    return {
      role: String(raw.role || 'conclusion'),
      speaker: String(raw.speaker || '朝议归纳'),
      content,
      displayContent: content,
      options: Array.isArray(raw.options) ? raw.options : undefined,
    };
  });
}

export function mingComposeDecree(
  _sessionId: string,
  force = false,
  config?: ApiConfig,
): Promise<{ ok: boolean; decree: string }> {
  return salvageFetch<{ decree?: string }>(
    '/api/decree/write',
    { method: 'POST', body: JSON.stringify({ force }) },
    config,
  ).then((out) => ({ ok: true, decree: String(out.decree || '') }));
}

export function mingEditDecree(_sessionId: string, decree: string, config?: ApiConfig) {
  return salvageFetch<{ decree?: string }>(
    '/api/decree',
    { method: 'PATCH', body: JSON.stringify({ decree }) },
    config,
  ).then((out) => ({ ok: true, decree: String(out.decree || decree) }));
}

export function mingIssueDecree(
  _sessionId: string,
  cheat = '',
  config?: ApiConfig,
): Promise<{
  ok: boolean;
  awaiting_decision: boolean;
  report: string;
  state: MingGameState;
  ended: boolean;
}> {
  return salvageFetch<{
    report?: string;
    awaiting_decision?: boolean;
    state?: SalvageGameState;
  }>(
    '/api/decree/issue',
    { method: 'POST', body: JSON.stringify({ cheat }) },
    config,
  ).then((out) => {
    const state = adaptSalvageToMingGameState(out.state || {});
    return {
      ok: true,
      awaiting_decision: Boolean(out.awaiting_decision),
      report: String(out.report || state.last_report || ''),
      state,
      ended: state.ended,
    };
  });
}

export async function mingIssueDecreeStream(
  _sessionId: string,
  onEvent: (kind: string, data: Record<string, unknown>) => void,
  cheat = '',
  config?: ApiConfig,
  signal?: AbortSignal,
): Promise<MingSettleStreamOutcome> {
  const base = getSalvageBaseUrl(config);
  const resp = await fetch(`${base}/api/decree/issue/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cheat }),
    signal,
    cache: 'no-store',
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => '');
    return { kind: 'error', message: formatSalvageApiError(detail, resp.status) };
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      let evName = '';
      let dataRaw = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) evName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataRaw += line.slice(6);
      }
      if (!evName || !dataRaw) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataRaw) as Record<string, unknown>;
      } catch {
        data = { content: dataRaw };
      }
      onEvent(evName, data);
      if (evName === 'done') return { kind: 'done', data };
      if (evName === 'decisions') return { kind: 'decisions', data };
      if (evName === 'error') {
        const msg =
          typeof data.message === 'string'
            ? data.message
            : typeof data.content === 'string'
              ? data.content
              : '颁诏失败';
        return { kind: 'error', message: msg };
      }
    }
  }
  return { kind: 'error', message: '推演流意外中断。' };
}

export function mingResolveDecisions(
  _sessionId: string,
  choices: Array<{ label?: string; hint?: string; note?: string }>,
  cheat = '',
  config?: ApiConfig,
): Promise<{
  ok: boolean;
  report: string;
  state: MingGameState;
  ended: boolean;
}> {
  return parseSalvageIssueStream(
    '/api/decree/resolve_decisions/stream',
    { choices, cheat },
    config,
  );
}

export async function mingResolveDecisionsStream(
  _sessionId: string,
  choices: Array<{ label?: string; hint?: string; note?: string }>,
  onEvent: (kind: string, data: Record<string, unknown>) => void,
  cheat = '',
  config?: ApiConfig,
  signal?: AbortSignal,
): Promise<MingSettleStreamOutcome> {
  const base = getSalvageBaseUrl(config);
  const resp = await fetch(`${base}/api/decree/resolve_decisions/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ choices, cheat }),
    signal,
    cache: 'no-store',
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => '');
    return { kind: 'error', message: formatSalvageApiError(detail, resp.status) };
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      let evName = '';
      let dataRaw = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) evName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataRaw += line.slice(6);
      }
      if (!evName || !dataRaw) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataRaw) as Record<string, unknown>;
      } catch {
        data = { content: dataRaw };
      }
      onEvent(evName, data);
      if (evName === 'done') return { kind: 'done', data };
      if (evName === 'decisions') return { kind: 'decisions', data };
      if (evName === 'error') {
        const msg =
          typeof data.message === 'string'
            ? data.message
            : typeof data.content === 'string'
              ? data.content
              : '亲裁结算失败';
        return { kind: 'error', message: msg };
      }
    }
  }
  return { kind: 'error', message: '亲裁结算流意外中断。' };
}

async function parseSalvageIssueStream(
  path: string,
  body: Record<string, unknown>,
  config?: ApiConfig,
  onEvent?: (kind: string, data: Record<string, unknown>) => void,
): Promise<{
  ok: boolean;
  report: string;
  state: MingGameState;
  ended: boolean;
  salvageRaw?: SalvageGameState;
}> {
  const base = getSalvageBaseUrl(config);
  const resp = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => '');
    throw new Error(formatSalvageApiError(detail, resp.status));
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let donePayload: Record<string, unknown> | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      let evName = '';
      let dataRaw = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) evName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataRaw += line.slice(6);
      }
      if (!evName || !dataRaw) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataRaw) as Record<string, unknown>;
      } catch {
        data = { content: dataRaw };
      }
      if (evName === 'done') donePayload = data;
      if (evName === 'error') {
        throw new Error(String(data.message || data.content || '结算失败'));
      }
      onEvent?.(evName, data);
    }
  }
  if (!donePayload) throw new Error('结算流意外中断。');
  const salvageRaw = normalizeSalvageGameState(donePayload.state || {});
  const state = adaptSalvageToMingGameState(salvageRaw);
  return {
    ok: true,
    report: String(donePayload.report || state.last_report || ''),
    state,
    ended: state.ended,
    salvageRaw,
  };
}

export function mingExitSession(_sessionId: string, config?: ApiConfig): Promise<void> {
  return salvageFetch('/api/menu/exit_to_menu', { method: 'POST', body: '{}' }, config).then(() => undefined);
}

export function mingMenuContinue(
  scenarioId?: string,
  config?: ApiConfig,
): Promise<{ state: SalvageGameState }> {
  const sid = scenarioId?.trim() || 'ming_wanli';
  const activateFirst = mingActivateScenario(sid, config).catch(() => undefined);
  return activateFirst.then(() =>
    salvageFetch<{ state: SalvageGameState }>(
      '/api/menu/continue',
      { method: 'POST', body: JSON.stringify({ scenario_id: sid }) },
      config,
    ).then((out) => ({ state: normalizeSalvageGameState(out.state) })),
  );
}

export function mingFetchSaves(config?: ApiConfig): Promise<{ saves: MingSaveEntry[] }> {
  return salvageFetch<{ saves?: MingSaveEntry[] }>('/api/saves', { method: 'GET' }, config).then((raw) => ({
    saves: raw.saves || [],
  }));
}

export function mingCreateSave(name: string, config?: ApiConfig): Promise<{ saves: MingSaveEntry[] }> {
  return salvageFetch<{ saves?: MingSaveEntry[] }>(
    '/api/saves',
    { method: 'POST', body: JSON.stringify({ name }) },
    config,
  ).then((raw) => ({ saves: raw.saves || [] }));
}

export function mingDeleteSave(name: string, config?: ApiConfig): Promise<{ saves: MingSaveEntry[] }> {
  return salvageFetch<{ saves?: MingSaveEntry[] }>(
    `/api/saves/${encodeURIComponent(name)}`,
    { method: 'DELETE' },
    config,
  ).then((raw) => ({ saves: raw.saves || [] }));
}

export function mingLoadSave(
  name: string,
  scenarioId?: string,
  config?: ApiConfig,
): Promise<{ state: SalvageGameState }> {
  const sid = scenarioId?.trim();
  if (sid) {
    const activateFirst = mingActivateScenario(sid, config).catch(() => undefined);
    return activateFirst.then(() =>
      salvageFetch<{ state: SalvageGameState }>(
        `/api/menu/load_save/${encodeURIComponent(name)}`,
        { method: 'POST', body: JSON.stringify({ scenario_id: sid }) },
        config,
      ).then((out) => ({ state: normalizeSalvageGameState(out.state) })),
    );
  }
  return salvageFetch<{ state: SalvageGameState }>(
    `/api/saves/${encodeURIComponent(name)}/load`,
    { method: 'POST', body: '{}' },
    config,
  ).then((out) => ({ state: normalizeSalvageGameState(out.state) }));
}

export function mingResetGame(config?: ApiConfig): Promise<{ state: SalvageGameState }> {
  return salvageFetch<{ state: SalvageGameState }>('/api/game/reset', { method: 'POST', body: '{}' }, config).then(
    (out) => ({ state: normalizeSalvageGameState(out.state) }),
  );
}

export function mingMenuShutdown(config?: ApiConfig): Promise<void> {
  return salvageFetch('/api/menu/shutdown', { method: 'POST', body: '{}' }, config).then(() => undefined);
}

export function mingFetchLlmConfig(config?: ApiConfig): Promise<MingLlmConfig> {
  return salvageFetch<MingLlmConfig>('/api/llm/config', { method: 'GET' }, config);
}

export function mingSaveLlmConfig(
  payload: Record<string, unknown>,
  config?: ApiConfig,
): Promise<MingLlmConfig> {
  return salvageFetch<MingLlmConfig>('/api/llm/config', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, config);
}

export function mingFetchGameSettings(config?: ApiConfig): Promise<{ game_settings: MingGameSettings }> {
  return salvageFetch<{ game_settings: MingGameSettings }>('/api/menu/game_settings', { method: 'GET' }, config);
}

export function mingSaveGameSettings(
  settings: MingGameSettings,
  config?: ApiConfig,
): Promise<{ ok: boolean; game_settings: MingGameSettings }> {
  return salvageFetch<{ ok: boolean; game_settings: MingGameSettings }>(
    '/api/menu/game_settings',
    { method: 'POST', body: JSON.stringify(settings) },
    config,
  );
}

export function mingPatchDirective(
  _sessionId: string,
  directiveId: number,
  text: string,
  config?: ApiConfig,
): Promise<{ ok: boolean; directives: MingDirective[]; pending_count: number }> {
  return salvageFetch<{ directives?: SalvageGameState['directives']; pending_count?: number }>(
    `/api/directives/${directiveId}`,
    { method: 'PATCH', body: JSON.stringify({ text }) },
    config,
  ).then((raw) => mapDirectivesPayload(raw));
}

export function mingFetchTurnExtraction(turn = -1, config?: ApiConfig): Promise<MingExtractionData> {
  const q = turn >= 0 ? `?turn=${turn}` : '';
  return salvageFetch<MingExtractionData>(`/api/turn_extraction${q}`, { method: 'GET' }, config);
}

export function mingFetchSecretOrders(config?: ApiConfig): Promise<{ orders: MingSecretOrder[] }> {
  return salvageFetch<{ orders: MingSecretOrder[] }>('/api/secret_orders', { method: 'GET' }, config);
}

export function mingDeleteSecretOrder(orderId: number, config?: ApiConfig): Promise<void> {
  return salvageFetch(`/api/secret_orders/${orderId}`, { method: 'DELETE' }, config).then(() => undefined);
}

export function mingFetchHistoryTurns(config?: ApiConfig): Promise<{ turns: MingHistoryTurnItem[] }> {
  return salvageFetch<{ turns: MingHistoryTurnItem[] }>('/api/history/turns', { method: 'GET' }, config);
}

export function mingFetchHistoryTurn(turn: number, config?: ApiConfig): Promise<MingHistoryDetail> {
  return salvageFetch<MingHistoryDetail>(`/api/history/turn/${turn}`, { method: 'GET' }, config);
}

export function mingFetchStructuredDirectiveTemplates(
  config?: ApiConfig,
): Promise<{ templates: MingStructuredDirectiveTemplate[] }> {
  return salvageFetch<{ templates: MingStructuredDirectiveTemplate[] }>(
    '/api/structured_directives/templates',
    { method: 'GET' },
    config,
  );
}

export function mingCreateStructuredDirective(
  templateId: string,
  fields: Record<string, string>,
  config?: ApiConfig,
): Promise<{ structured_directives: MingStructuredDirective[] }> {
  return salvageFetch<{ structured_directives: MingStructuredDirective[] }>(
    '/api/structured_directives',
    { method: 'POST', body: JSON.stringify({ template_id: templateId, fields }) },
    config,
  );
}

export function mingUpdateStructuredDirective(
  directiveId: number,
  templateId: string,
  fields: Record<string, string>,
  config?: ApiConfig,
): Promise<{ structured_directives: MingStructuredDirective[] }> {
  return salvageFetch<{ structured_directives: MingStructuredDirective[] }>(
    `/api/structured_directives/${directiveId}`,
    { method: 'PATCH', body: JSON.stringify({ template_id: templateId, fields }) },
    config,
  );
}

export function mingDeleteStructuredDirective(
  directiveId: number,
  config?: ApiConfig,
): Promise<{ structured_directives: MingStructuredDirective[] }> {
  return salvageFetch<{ structured_directives: MingStructuredDirective[] }>(
    `/api/structured_directives/${directiveId}`,
    { method: 'DELETE' },
    config,
  );
}

export function mingFetchCourtChatHistory(config?: ApiConfig): Promise<MingCourtChatResponse> {
  return salvageFetch<MingCourtChatResponse>('/api/court_chat', { method: 'GET' }, config);
}

export async function mingCourtChatStream(
  message: string,
  ministers: string[],
  onEvent: (event: string, data: Record<string, unknown>) => void,
  config?: ApiConfig,
  signal?: AbortSignal,
): Promise<MingCourtChatResponse> {
  const base = getSalvageBaseUrl(config);
  const resp = await fetch(`${base}/api/court_chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, ministers }),
    signal,
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => '');
    throw new Error(formatSalvageApiError(detail, resp.status));
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      let evName = '';
      let dataRaw = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) evName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataRaw += line.slice(6);
      }
      if (!evName || !dataRaw) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataRaw) as Record<string, unknown>;
      } catch {
        data = { content: dataRaw };
      }
      onEvent(evName, data);
      if (evName === 'done') return data as MingCourtChatResponse;
      if (evName === 'error') {
        const msg =
          typeof data.message === 'string'
            ? data.message
            : typeof data.detail === 'string'
              ? data.detail
              : '朝会回复失败';
        throw new Error(msg);
      }
    }
  }
  throw new Error('朝会流式回复中断，未收到完成事件。');
}

export function mingUpdateIssueAssignee(
  issueId: number,
  assignee: string,
  config?: ApiConfig,
): Promise<{ updated: boolean; id: number; assignee: string }> {
  return salvageFetch<{ updated: boolean; id: number; assignee: string }>(
    `/api/issues/${issueId}/assignee`,
    { method: 'PATCH', body: JSON.stringify({ assignee }) },
    config,
  );
}

export function mingSetIssueAuthorization(
  issueId: number,
  payload: { budget_add: number; budget_source: string; death_authority: boolean },
  config?: ApiConfig,
): Promise<Record<string, unknown>> {
  return salvageFetch<Record<string, unknown>>(
    `/api/issues/${issueId}/authorization`,
    { method: 'POST', body: JSON.stringify(payload) },
    config,
  );
}

export function mingCreateManualIssue(
  payload: {
    title: string;
    goal: string;
    assignee: string;
    tags: string[];
    entity?: Record<string, unknown> | null;
  },
  config?: ApiConfig,
): Promise<{ id: number; title: string }> {
  return salvageFetch<{ id: number; title: string }>(
    '/api/issues/manual',
    { method: 'POST', body: JSON.stringify(payload) },
    config,
  );
}

export function mingUpdateManualIssue(
  issueId: number,
  payload: { title?: string; assignee?: string },
  config?: ApiConfig,
): Promise<{ updated: boolean; id: number }> {
  return salvageFetch<{ updated: boolean; id: number }>(
    `/api/issues/manual/${issueId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
    config,
  );
}

export function mingDeleteManualIssue(issueId: number, config?: ApiConfig): Promise<void> {
  return salvageFetch(`/api/issues/manual/${issueId}`, { method: 'DELETE' }, config).then(() => undefined);
}

export function mingAddFavorite(ministerName: string, config?: ApiConfig): Promise<{ favorites: string[] }> {
  return salvageFetch<{ favorites: string[] }>(
    `/api/favorites/${encodeURIComponent(ministerName)}`,
    { method: 'POST', body: '{}' },
    config,
  );
}

export function mingRemoveFavorite(ministerName: string, config?: ApiConfig): Promise<{ favorites: string[] }> {
  return salvageFetch<{ favorites: string[] }>(
    `/api/favorites/${encodeURIComponent(ministerName)}`,
    { method: 'DELETE' },
    config,
  );
}

export function mingArchiveMinister(ministerName: string, config?: ApiConfig): Promise<Record<string, unknown>> {
  return salvageFetch<Record<string, unknown>>(
    `/api/ministers/${encodeURIComponent(ministerName)}/archive`,
    { method: 'POST', body: '{}' },
    config,
  );
}

export function mingRestoreMinister(ministerName: string, config?: ApiConfig): Promise<Record<string, unknown>> {
  return salvageFetch<Record<string, unknown>>(
    `/api/ministers/${encodeURIComponent(ministerName)}/restore`,
    { method: 'POST', body: '{}' },
    config,
  );
}

export { salvageSessionId };
