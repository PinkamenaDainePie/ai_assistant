/** 终局报告表格：全程数值对比 + 季度总结一览 */

import { chapterFromQuarterReport } from './quarterChapterArchive';
import type { QuarterChapterRecord } from './quarterChapterArchive';
import {
  buildQuarterChapterListItems,
  quarterChapterId,
  type QuarterChapterListOptions,
} from './quarterChapterDisplay';
import type { NationMetricKey, NationState } from './types';

export type MetricSummaryRow = {
  key: NationMetricKey;
  label: string;
  opening: number;
  final: number;
  delta: number;
};

export type EndingChapterRow = {
  id: string;
  quarterIndex: number;
  quarterLabel: string;
  title: string;
  abstract: string;
  highlights: string;
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

function pickHighlights(ch: QuarterChapterRecord): string {
  const hl = (ch.highlights_zh || []).map((s) => String(s || '').trim()).filter(Boolean);
  if (hl.length > 0) return hl.join('；');
  const headline = String(ch.headline_zh || '').trim();
  if (headline) return headline;
  return '—';
}

export function buildCampaignMetricSummaryRows(
  opening: Partial<Record<NationMetricKey, number>>,
  nationState: NationState,
): MetricSummaryRow[] {
  return nationState.metrics.map((metric) => {
    const openVal = opening[metric.key] ?? metric.value;
    const finalVal = metric.value;
    const delta = Number((finalVal - openVal).toFixed(2));
    return {
      key: metric.key,
      label: metric.label,
      opening: Number(openVal.toFixed(2)),
      final: Number(finalVal.toFixed(2)),
      delta,
    };
  });
}

export function buildEndingChapterTableRows(
  chapters: QuarterChapterRecord[],
  options?: QuarterChapterListOptions,
): EndingChapterRow[] {
  const merged = mergeChapterRecords(
    chapters,
    chapterFromQuarterReport(options?.latestReport),
  );
  const byId = new Map(merged.map((ch) => [quarterChapterId(ch), ch]));
  const items = buildQuarterChapterListItems(chapters, options);

  return [...items]
    .sort((a, b) => a.reportingQuarterIndex - b.reportingQuarterIndex)
    .map((item) => {
      const ch = byId.get(item.id);
      return {
        id: item.id,
        quarterIndex: item.reportingQuarterIndex,
        quarterLabel: item.quarterLabel,
        title: item.title,
        abstract: item.abstract,
        highlights: ch ? pickHighlights(ch) : item.headline || '—',
      };
    });
}

export function formatMetricDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  if (delta === 0) return '0';
  return String(delta);
}
