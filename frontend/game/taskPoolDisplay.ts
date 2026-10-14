/** 任务池展示：跨季诏书/委派任务置顶，避免被 slice(0,3) 挤出视野 */

export type TaskRow = Record<string, unknown>;

const CROSS_QUARTER_KINDS = new Set(['edict_execution', 'delegation']);

export function isCrossQuarterTask(t: TaskRow): boolean {
  const kind = String(t.resolution_kind ?? '').trim();
  const cat = String(t.category ?? '').trim();
  return CROSS_QUARTER_KINDS.has(kind) || cat === 'edict_execution';
}

export function sortTasksForDisplay(tasks: TaskRow[]): TaskRow[] {
  const cross: TaskRow[] = [];
  const rest: TaskRow[] = [];
  for (const t of tasks) {
    if (isCrossQuarterTask(t)) cross.push(t);
    else rest.push(t);
  }
  return [...cross, ...rest];
}

export const GAME_PHASE_ZH: Record<string, string> = {
  HOME: '选场景',
  QUARTER_MAIN: '朝政',
  DECREE_MODAL: '拟诏',
  EVENT_RESOLUTION: '事件',
  FOCUS_SELECTION: '季度重心',
  QUARTER_SETTLEMENT: '季末结算',
  SKILL_ALLOCATION: '技能加点',
  GAME_END: '终局',
  CAMPAIGN_MILESTONE: '里程碑收束',
};

export function taskDisplaySubtitle(t: TaskRow): string | null {
  const kind = String(t.resolution_kind ?? '');
  if (kind === 'edict_execution') {
    const em = (t.edict_execution as Record<string, unknown>) || {};
    const phasesTotal = Math.max(
      1,
      Number(em.phases_total ?? 0) ||
        Math.max(1, Number(t.deadline_quarter ?? 0) - Number(t.assigned_quarter ?? 0)),
    );
    const phaseIndex = Math.max(0, Number(em.phase_index ?? 0));
    const executor = String(em.display_executor_zh ?? '').trim();
    const parts = [`跨季承办 ${phaseIndex + 1}/${phasesTotal} 季`];
    if (executor) parts.push(executor);
    return parts.join(' · ');
  }
  if (kind === 'delegation') {
    const d = (t.delegation as Record<string, unknown>) || {};
    const phases = Math.max(1, Number(d.phases_total ?? 1));
    const phase = Math.max(0, Number(d.phase_index ?? 0));
    return `委派任务 ${phase + 1}/${phases} 季`;
  }
  return null;
}
