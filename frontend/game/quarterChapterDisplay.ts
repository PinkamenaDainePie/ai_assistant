/** 季度总结列表与详情展示（奏折侧栏数据源） */

import type { QuarterChapterRecord } from './quarterChapterArchive';
import { chapterFromQuarterReport } from './quarterChapterArchive';
import { getFirstQuarterFallback } from './quarterReportDisplay';
import type { ScenarioId } from './scenarios';
import { getScenarioRuntime } from './scenarios';

export type QuarterChapterListItem = {
  id: string;
  reportingQuarterIndex: number;
  quarterLabel: string;
  title: string;
  abstract: string;
  headline?: string;
};

export type QuarterChapterDetailSection = {
  title: string;
  lines: string[];
};

export type QuarterChapterDetailView = {
  id: string;
  reportingQuarterIndex: number;
  quarterLabel: string;
  title: string;
  headline?: string;
  body: string;
  sections: QuarterChapterDetailSection[];
};

const FALLBACK_Q1_ID = 'fallback_q1';

export function quarterChapterId(ch: QuarterChapterRecord): string {
  const mid = String(ch.memorial_id || '').trim();
  if (mid) return mid;
  const q = Number(ch.reporting_quarter_index || 0);
  return q > 0 ? `quarter_${q}` : `chapter_${Date.now()}`;
}

function pickAbstract(ch: QuarterChapterRecord): string {
  const headline = String(ch.headline_zh || '').trim();
  if (headline) return headline;
  const summary = String(ch.summary_zh || '').trim();
  if (summary) return summary;
  const body = String(ch.body_zh || '').trim();
  if (!body) return '暂无摘要';
  return body.length > 120 ? `${body.slice(0, 120)}…` : body;
}

function pickQuarterLabel(ch: QuarterChapterRecord): string {
  const label = String(ch.quarter_label_zh || '').trim();
  if (label) return label;
  const q = Number(ch.reporting_quarter_index || 0);
  return q > 0 ? `第 ${q} 季` : '未知季';
}

function toListItem(ch: QuarterChapterRecord): QuarterChapterListItem {
  return {
    id: quarterChapterId(ch),
    reportingQuarterIndex: Number(ch.reporting_quarter_index || 0),
    quarterLabel: pickQuarterLabel(ch),
    title: String(ch.title_zh || '朝政纪要').trim() || '朝政纪要',
    abstract: pickAbstract(ch),
    headline: String(ch.headline_zh || '').trim() || undefined,
  };
}

function sectionFromLines(
  title: string,
  lines: string[] | undefined,
): QuarterChapterDetailSection | null {
  const clean = (lines || []).map((l) => String(l || '').trim()).filter(Boolean);
  if (clean.length === 0) return null;
  return { title, lines: clean };
}

function chapterToDetail(ch: QuarterChapterRecord): QuarterChapterDetailView {
  const body = String(ch.body_zh || ch.summary_zh || '').trim();
  const sections: QuarterChapterDetailSection[] = [];

  const highlights = sectionFromLines('本季要点', ch.highlights_zh);
  if (highlights) sections.push(highlights);

  const metrics = sectionFromLines('指标变化', ch.metric_changes_zh);
  if (metrics) sections.push(metrics);

  const edictText = String(ch.edict_text || '').trim();
  const edictSummary = String(ch.edict_summary_zh || '').trim();
  if (edictText) {
    sections.push({ title: '本季诏书', lines: [edictText] });
  } else if (edictSummary) {
    sections.push({ title: '本季诏书', lines: [edictSummary] });
  }

  const settled = sectionFromLines('已结算要务', ch.settled_tasks_zh);
  if (settled) sections.push(settled);

  const outlook = sectionFromLines('下季展望', ch.outlook_zh);
  if (outlook) sections.push(outlook);

  return {
    id: quarterChapterId(ch),
    reportingQuarterIndex: Number(ch.reporting_quarter_index || 0),
    quarterLabel: pickQuarterLabel(ch),
    title: String(ch.title_zh || '朝政纪要').trim() || '朝政纪要',
    headline: String(ch.headline_zh || '').trim() || undefined,
    body: body || '暂无正文。',
    sections,
  };
}

function fallbackQ1ListItem(scenarioId: ScenarioId): QuarterChapterListItem {
  const fb = getFirstQuarterFallback(scenarioId);
  const firstLine =
    fb.body
      .split('\n')
      .map((l) => l.replace(/^[·\s]+/, '').trim())
      .find((l) => l.length > 4 && !/^一、|^二、|^三、/.test(l)) || fb.body.slice(0, 80);
  return {
    id: FALLBACK_Q1_ID,
    reportingQuarterIndex: 1,
    quarterLabel: '第一季',
    title: fb.title,
    abstract: firstLine,
  };
}

function fallbackQ1Detail(scenarioId: ScenarioId): QuarterChapterDetailView {
  const fb = getFirstQuarterFallback(scenarioId);
  return {
    id: FALLBACK_Q1_ID,
    reportingQuarterIndex: 1,
    quarterLabel: '第一季',
    title: fb.title,
    body: fb.body,
    sections: [],
  };
}

export type QuarterChapterListOptions = {
  scenarioId?: ScenarioId | null;
  currentQuarter?: number;
  latestReport?: Record<string, unknown> | null;
};

function mergeChapterRecords(
  chapters: QuarterChapterRecord[],
  extra?: QuarterChapterRecord | null,
): QuarterChapterRecord[] {
  if (!extra || Number(extra.reporting_quarter_index || 0) <= 0) {
    return chapters;
  }
  const q = Number(extra.reporting_quarter_index);
  const without = chapters.filter((c) => Number(c.reporting_quarter_index) !== q);
  return [...without, extra];
}

export function buildQuarterChapterListItems(
  chapters: QuarterChapterRecord[],
  options?: QuarterChapterListOptions,
): QuarterChapterListItem[] {
  const merged = mergeChapterRecords(
    chapters,
    chapterFromQuarterReport(options?.latestReport),
  );
  const sorted = [...merged]
    .filter((c) => Number(c.reporting_quarter_index || 0) > 0)
    .sort(
      (a, b) =>
        Number(b.reporting_quarter_index || 0) -
        Number(a.reporting_quarter_index || 0),
    );

  const items = sorted.map(toListItem);

  const hasQ1 = sorted.some((c) => Number(c.reporting_quarter_index) === 1);
  if (
    !hasQ1 &&
    options?.scenarioId &&
    getScenarioRuntime(options.scenarioId) === 'quarter' &&
    (options.currentQuarter ?? 0) >= 1
  ) {
    items.push(fallbackQ1ListItem(options.scenarioId));
    items.sort((a, b) => b.reportingQuarterIndex - a.reportingQuarterIndex);
  }

  return items;
}

export function resolveQuarterChapterDetail(
  id: string | undefined,
  chapters: QuarterChapterRecord[],
  options?: QuarterChapterListOptions,
): QuarterChapterDetailView | null {
  const key = String(id || '').trim();
  if (!key) return null;

  if (key === FALLBACK_Q1_ID && options?.scenarioId) {
    return fallbackQ1Detail(options.scenarioId);
  }

  const merged = mergeChapterRecords(
    chapters,
    chapterFromQuarterReport(options?.latestReport),
  );
  const found = merged.find((c) => quarterChapterId(c) === key);
  if (found) return chapterToDetail(found);

  return null;
}
