/** 从 quarter/start 的 quarter_report 提取可展示文案 */

import type { ScenarioId } from './scenarios';

export type QuarterReportDisplay = {
  title: string;
  body: string;
  hasContent: boolean;
};

const FIRST_QUARTER_REPORTS: Record<ScenarioId, QuarterReportDisplay> = {
  song_xining: {
    title: '第一季朝政纪要——熙宁开局',
    body: [
      '朝政纪要',
      '',
      '一、本季朝局',
      '· 陛下御极未久，锐意更张，朝堂新旧两派议论未息。',
      '· 参知政事王安石首倡新法，理财、强兵、育才诸策次第筹谋，诸司尚未尽行。',
      '· 枢密副使司马光等旧臣屡陈祖宗成法不可轻改，台谏亦多有封事。',
      '',
      '二、要务概览',
      '· 本季以颁诏定策、察民情、稳朝局为先，诸项要务已列入奏报。',
      '· 边患压力尚可，然西北、交趾之议已在廷议间偶被提及。',
      '',
      '三、下季展望',
      '· 若陛下决意推行新法，当以诏书明定次第，使诸路有所遵循。',
      '· 朝臣人心未齐，须留意士大夫支持与民心之消长。',
    ].join('\n'),
    hasContent: true,
  },
  song_xining_v2: {
    title: '第一季朝政纪要——熙宁开局（新引擎）',
    body: [
      '朝政纪要',
      '',
      '一、本季朝局',
      '· 陛下御极未久，锐意更张，朝堂新旧两派议论未息。',
      '· 参知政事王安石首倡新法，理财、强兵、育才诸策次第筹谋，诸司尚未尽行。',
      '· 枢密副使司马光等旧臣屡陈祖宗成法不可轻改，台谏亦多有封事。',
      '',
      '二、要务概览',
      '· 本季以颁诏定策、察民情、稳朝局为先，诸项要务已列入奏报。',
      '· 边患压力尚可，然西北、交趾之议已在廷议间偶被提及。',
      '',
      '三、下季展望',
      '· 若陛下决意推行新法，当以诏书明定次第，使诸路有所遵循。',
      '· 朝臣人心未齐，须留意士大夫支持与民心之消长。',
    ].join('\n'),
    hasContent: true,
  },
  ming_wanli: {
    title: '第一季朝政纪要——万历开局',
    body: [
      '朝政纪要',
      '',
      '一、本季朝局',
      '· 陛下初政，张居正等辅臣柄政，考成法、一条鞭诸政尚在酝酿。',
      '· 太仓储备不裕，边饷与河工之费仍是廷议所忧。',
      '',
      '二、要务概览',
      '· 本季以察吏治、清漕赋、稳边防为要，诸司奏报已汇于御前。',
      '',
      '三、下季展望',
      '· 改革若欲有成，须先明号令、定权责，使天下知所趋向。',
    ].join('\n'),
    hasContent: true,
  },
};

export type QuarterReportDisplayOptions = {
  currentQuarter?: number;
  scenarioId?: ScenarioId | null;
};

export function getFirstQuarterFallback(
  scenarioId: ScenarioId,
): QuarterReportDisplay {
  return FIRST_QUARTER_REPORTS[scenarioId];
}

export function formatQuarterReportForDisplay(
  report?: Record<string, unknown> | null,
  options?: QuarterReportDisplayOptions,
): QuarterReportDisplay {
  const qr = report || {};
  const memorial =
    qr.memorial && typeof qr.memorial === 'object'
      ? (qr.memorial as Record<string, unknown>)
      : undefined;

  const title = String(
    qr.title_zh || memorial?.title_zh || '朝政纪要',
  ).trim();

  const body = String(
    memorial?.body_zh || qr.summary || memorial?.summary_zh || '',
  ).trim();

  if (body.length > 0) {
    return { title, body, hasContent: true };
  }

  if (options?.currentQuarter === 1 && options.scenarioId) {
    return FIRST_QUARTER_REPORTS[options.scenarioId];
  }

  return {
    title,
    body,
    hasContent: body.length > 0,
  };
}
