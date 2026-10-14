/** 季度总结本地归档（localStorage），按 session_id 分桶 */

export type QuarterChapterRecord = {
  reporting_quarter_index: number;
  quarter_label_zh?: string;
  new_quarter_label_zh?: string;
  title_zh?: string;
  headline_zh?: string;
  summary_zh?: string;
  body_zh?: string;
  highlights_zh?: string[];
  edict_summary_zh?: string;
  edict_text?: string;
  settled_tasks_zh?: string[];
  metric_changes_zh?: string[];
  outlook_zh?: string[];
  narrative_mode?: string;
  memorial_id?: string;
  game_session_id?: string;
  settlement_summary?: Record<string, unknown>;
  archived_at_ms?: number;
};

const STORAGE_KEY = 'ai_assistant_quarter_chapters_v1';

type ArchiveStore = Record<string, QuarterChapterRecord[]>;

function readStore(): ArchiveStore {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as ArchiveStore;
  } catch {
    return {};
  }
}

function writeStore(store: ArchiveStore): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // quota exceeded — ignore
  }
}

function chapterKey(ch: QuarterChapterRecord): number {
  return Number(ch.reporting_quarter_index || 0);
}

function mergeChapterLists(
  local: QuarterChapterRecord[],
  remote: QuarterChapterRecord[],
): QuarterChapterRecord[] {
  const byQ = new Map<number, QuarterChapterRecord>();
  for (const item of local) {
    const q = chapterKey(item);
    if (q > 0) byQ.set(q, item);
  }
  for (const item of remote) {
    const q = chapterKey(item);
    if (q > 0) byQ.set(q, item);
  }
  return Array.from(byQ.values()).sort(
    (a, b) => chapterKey(a) - chapterKey(b),
  );
}

export function getLocalQuarterChapters(
  sessionId: string,
): QuarterChapterRecord[] {
  const sid = (sessionId || '').trim();
  if (!sid) return [];
  const store = readStore();
  const list = store[sid];
  if (!Array.isArray(list)) return [];
  return mergeChapterLists([], list.filter(Boolean) as QuarterChapterRecord[]);
}

export function saveLocalQuarterChapters(
  sessionId: string,
  chapters: QuarterChapterRecord[],
): QuarterChapterRecord[] {
  const sid = (sessionId || '').trim();
  if (!sid) return [];
  const store = readStore();
  const merged = mergeChapterLists([], chapters);
  store[sid] = merged;
  writeStore(store);
  return merged;
}

/** 以后端列表为准合并本地缓存（同季覆盖，季序升序）。 */
export function syncQuarterChaptersFromBackend(
  sessionId: string,
  backendChapters: QuarterChapterRecord[] | undefined | null,
): QuarterChapterRecord[] {
  const sid = (sessionId || '').trim();
  if (!sid) return [];
  const local = getLocalQuarterChapters(sid);
  const remote = Array.isArray(backendChapters)
    ? backendChapters.filter(Boolean)
    : [];
  const merged =
    remote.length > 0 ? mergeChapterLists(local, remote) : local;
  return saveLocalQuarterChapters(sid, merged);
}

export function appendLocalQuarterChapter(
  sessionId: string,
  chapter: QuarterChapterRecord,
): QuarterChapterRecord[] {
  const sid = (sessionId || '').trim();
  if (!sid) return [];
  const local = getLocalQuarterChapters(sid);
  return saveLocalQuarterChapters(sid, mergeChapterLists(local, [chapter]));
}

export function clearLocalQuarterChapters(sessionId: string): void {
  const sid = (sessionId || '').trim();
  if (!sid) return;
  const store = readStore();
  delete store[sid];
  writeStore(store);
}

export function chapterFromQuarterReport(
  report?: Record<string, unknown> | null,
  gameSessionId?: string,
): QuarterChapterRecord | null {
  const qr = report || {};
  const memorial =
    qr.memorial && typeof qr.memorial === 'object'
      ? (qr.memorial as Record<string, unknown>)
      : undefined;
  const repQ = Number(
    memorial?.reporting_quarter_index ??
      (memorial?.settlement_summary as Record<string, unknown> | undefined)
        ?.reporting_quarter_index ??
      0,
  );
  if (repQ <= 0) return null;

  const settlement =
    memorial?.settlement_summary &&
    typeof memorial.settlement_summary === 'object'
      ? (memorial.settlement_summary as Record<string, unknown>)
      : undefined;

  const body = String(memorial?.body_zh || '').trim();
  let summary = String(memorial?.summary_zh || qr.summary || '').trim();
  if (!summary && body) {
    summary = body.length > 320 ? `${body.slice(0, 320)}…` : body;
  }

  return {
    reporting_quarter_index: repQ,
    quarter_label_zh: String(
      memorial?.quarter_label_zh || settlement?.quarter_label_zh || '',
    ).trim(),
    new_quarter_label_zh: String(settlement?.new_quarter_label_zh || '').trim(),
    title_zh: String(memorial?.title_zh || qr.title_zh || '').trim(),
    headline_zh: String(memorial?.headline_zh || qr.headline_zh || '').trim(),
    summary_zh: summary,
    body_zh: body,
    highlights_zh: Array.isArray(memorial?.highlights_zh)
      ? (memorial!.highlights_zh as string[])
      : Array.isArray(qr.highlights_zh)
        ? (qr.highlights_zh as string[])
        : [],
    edict_summary_zh: String(settlement?.edict_summary_zh || '').trim(),
    edict_text: String(settlement?.edict_text || '').trim(),
    narrative_mode: String(memorial?.mode || qr.narrative_mode || '').trim(),
    memorial_id: String(memorial?.memorial_id || '').trim(),
    game_session_id: (gameSessionId || '').trim(),
    settlement_summary: settlement,
    archived_at_ms: Date.now(),
  };
}
