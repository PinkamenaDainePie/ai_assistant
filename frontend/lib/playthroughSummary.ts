import type { PlaythroughRecord } from './classroomApi';

export type ParsedPlaythroughSummary = {
  titleZh: string;
  summaryZh: string;
  score: number | null;
  scoreLabelZh: string;
  kind: string;
  endingMode: string;
  highlightsZh: string[];
  historyCompareZh: string;
  sections: Array<{ label: string; text: string }>;
  hasContent: boolean;
};

const SECTION_LABELS: Array<[key: string, label: string]> = [
  ['life_chronicle_zh', '生平事迹'],
  ['ending_scene_zh', '结局描述'],
  ['merits_demerits_zh', '功过总结'],
  ['temple_name_zh', '庙号'],
  ['future_projection_zh', '未来推演'],
];

function asString(value: unknown): string {
  if (typeof value === 'string') return value.trim();
  if (value == null) return '';
  return String(value).trim();
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => asString(item)).filter(Boolean);
}

export function parsePlaythroughSummary(
  raw: Record<string, unknown> | null | undefined,
): ParsedPlaythroughSummary {
  const data = raw || {};
  const sectionsRaw =
    data.sections && typeof data.sections === 'object' && !Array.isArray(data.sections)
      ? (data.sections as Record<string, unknown>)
      : {};

  const sections = SECTION_LABELS.map(([key, label]) => ({
    label,
    text: asString(sectionsRaw[key]),
  })).filter((row) => row.text);

  const titleZh = asString(data.title_zh);
  const summaryZh = asString(data.summary_zh);
  const score = asNumber(data.score);
  const scoreLabelZh = asString(data.score_label_zh);
  const kind = asString(data.kind);
  const endingMode = asString(data.ending_mode);
  const highlightsZh = asStringList(data.highlights_zh);
  const historyCompareZh = asString(data.history_compare_zh);

  const hasContent =
    Boolean(titleZh || summaryZh || score != null || highlightsZh.length || historyCompareZh) ||
    sections.length > 0;

  return {
    titleZh,
    summaryZh,
    score,
    scoreLabelZh,
    kind,
    endingMode,
    highlightsZh,
    historyCompareZh,
    sections,
    hasContent,
  };
}

export function formatPlaythroughScore(
  record: Pick<
    PlaythroughRecord,
    'status' | 'summary_json' | 'teacher_review_score' | 'teacher_review_comment'
  >,
): string {
  if (record.status !== 'finished') return '—';
  if (record.teacher_review_score != null) {
    return String(record.teacher_review_score);
  }
  const parsed = parsePlaythroughSummary(record.summary_json);
  if (parsed.score == null) return '—';
  return parsed.scoreLabelZh ? `${parsed.score} · ${parsed.scoreLabelZh}` : String(parsed.score);
}

export function formatOfficialPlaythroughScoreLabel(
  record: Pick<PlaythroughRecord, 'status' | 'summary_json' | 'teacher_review_score'>,
): string {
  if (record.status !== 'finished') return '—';
  if (record.teacher_review_score != null) return `${record.teacher_review_score}（教师）`;
  return formatPlaythroughScore(record);
}
