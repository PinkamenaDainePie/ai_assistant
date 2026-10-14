import { updatePlaythrough } from '../lib/classroomApi';
import type { QuarterChapterRecord } from './quarterChapterArchive';

export type SalvageTurnChapterInput = {
  turn?: { turn?: number; year?: string; period?: string };
  last_report?: string;
  last_decree?: string;
};

export type SalvageTurnChapterOptions = {
  report?: string;
  decree?: string;
  /** 本条记录对应的已结算回合（月度）；不传则根据 currentTurn-1 推断 */
  reportingTurn?: number;
};

export function buildSalvageTurnChapter(
  st: SalvageTurnChapterInput | undefined,
  opts?: SalvageTurnChapterOptions,
): QuarterChapterRecord | null {
  if (!st) return null;
  const currentTurn = Number(st.turn?.turn) || 0;
  const report = String(opts?.report || st.last_report || '').trim();
  const decree = String(opts?.decree || st.last_decree || '').trim();
  if (!report && !decree) return null;

  let reportingTurn = opts?.reportingTurn;
  if (reportingTurn == null || reportingTurn <= 0) {
    reportingTurn = currentTurn > 1 ? currentTurn - 1 : currentTurn;
  }
  if (reportingTurn <= 0) return null;

  const year = String(st.turn?.year || '').trim();
  const period = String(st.turn?.period || '').trim();
  const label = [year, period].filter(Boolean).join(' ') || `第 ${reportingTurn} 月`;
  return {
    reporting_quarter_index: reportingTurn,
    quarter_label_zh: label,
    title_zh: `第 ${reportingTurn} 月奏报`,
    headline_zh: report.slice(0, 120) || (decree ? '本回合颁布诏书' : undefined),
    summary_zh: report.length > 320 ? `${report.slice(0, 320)}…` : report || decree.slice(0, 320),
    body_zh: report || decree,
    edict_text: decree,
    edict_summary_zh: decree ? '本回合颁布诏书' : '',
    narrative_mode: 'salvage_monthly',
    archived_at_ms: Date.now(),
  };
}

export function syncPlaythroughQuarterChapters(
  playthroughId: string,
  chapters: QuarterChapterRecord[],
  campaignSessionId?: string,
): void {
  const id = (playthroughId || '').trim();
  if (!id || !chapters.length) return;
  void updatePlaythrough(id, {
    quarter_chapters: chapters as Array<Record<string, unknown>>,
    campaign_session_id: campaignSessionId?.trim() || undefined,
  }).catch(() => undefined);
}
