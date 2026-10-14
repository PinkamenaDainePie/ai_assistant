export const SCENARIO_LABELS: Record<string, string> = {
  song_xining: '熙宁变法（经典·已下架）',
  song_xining_v2: '熙宁变法',
  ming_wanli: '万历改革',
};

export function formatScenarioLabel(code: string): string {
  return SCENARIO_LABELS[code] || code;
}

export function formatPlaythroughStatus(status: string): string {
  const map: Record<string, string> = {
    in_progress: '进行中',
    finished: '已完成',
    abandoned: '已放弃',
  };
  return map[status] || status;
}

/** salvage 剧本存的是月度 turn，经典季度存的是季数 */
export function formatPlaythroughProgress(scenarioCode: string, value: number): string {
  if (value <= 0) return '—';
  if (scenarioCode === 'song_xining_v2' || scenarioCode === 'ming_wanli') {
    return `第 ${value} 月`;
  }
  return `第 ${value} 季`;
}
