import type { ScenarioId } from '../scenarios';

/** 预算/税目展示名：引擎内部键不变，仅 UI 口径切换。 */
export function displayFiscalLabel(text: string, scenarioId?: ScenarioId): string {
  if (scenarioId !== 'song_xining_v2') return text;
  return text
    .replace(/田赋辽饷盐商/g, '田赋岁币边饷盐商')
    .replace(/辽饷/g, '岁币/边饷')
    .replace(/两京十三省/g, '诸路');
}

export function borderTaxDisplayKey(scenarioId?: ScenarioId): string {
  return scenarioId === 'song_xining_v2' ? '岁币/边饷' : '辽饷';
}

/** 引擎内部财政科目键（提交后端时不变） */
export const REGIONAL_FISCAL_KEYS = ['田赋', '辽饷', '盐税', '商税', '人头税'] as const;

export const DEFAULT_TAX_TYPE_OPTIONS = [
  '田赋',
  '辽饷',
  '盐税',
  '商税',
  '人头税',
  '皇庄',
] as const;

export function isRegionalFiscalKey(key: string): boolean {
  return (REGIONAL_FISCAL_KEYS as readonly string[]).includes(key);
}

export function resolveTaxTypeOptions(): readonly string[] {
  return DEFAULT_TAX_TYPE_OPTIONS;
}
