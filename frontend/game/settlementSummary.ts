/** 上季任务结算与诏书影响的展示用摘要（与后端 result / resolution_kind 对齐） */

export type TaskSettlementStats = {
  /** 上季季末结算处理过的记录条数（含仍进行中的任务） */
  lastQuarterSettled: number;
  /** 目标已达成（completed / success） */
  lastQuarterCompleted: number;
  /** 有进展但未结案（partial） */
  lastQuarterPartial: number;
  /** 仍在进行（active / edict_execution_phase） */
  lastQuarterInProgress: number;
  /** 未达成或反噬（failed / failure / backlash） */
  lastQuarterFailed: number;
  /** 季末怠政（stall_penalty） */
  lastQuarterStall: number;
  /** 当前任务池活跃条数 */
  currentPoolCount: number;
};

const COMPLETED_RESULTS = new Set(['completed', 'success']);
const PARTIAL_RESULTS = new Set(['partial']);
const IN_PROGRESS_RESULTS = new Set(['active', 'edict_execution_phase']);
const FAILED_RESULTS = new Set(['failed', 'failure', 'backlash', 'failed_expired']);
const STALL_RESULTS = new Set(['stall_penalty']);

function normalizeResult(row: Record<string, unknown>): string {
  return String(row.result ?? '').trim().toLowerCase();
}

export function summarizeTaskSettlement(
  previousResults: Array<Record<string, unknown>>,
  currentTasks: Array<Record<string, unknown>>,
): TaskSettlementStats {
  let lastQuarterCompleted = 0;
  let lastQuarterPartial = 0;
  let lastQuarterInProgress = 0;
  let lastQuarterFailed = 0;
  let lastQuarterStall = 0;

  for (const row of previousResults) {
    const r = normalizeResult(row);
    if (COMPLETED_RESULTS.has(r)) lastQuarterCompleted += 1;
    else if (PARTIAL_RESULTS.has(r)) lastQuarterPartial += 1;
    else if (STALL_RESULTS.has(r)) lastQuarterStall += 1;
    else if (IN_PROGRESS_RESULTS.has(r)) lastQuarterInProgress += 1;
    else if (FAILED_RESULTS.has(r)) lastQuarterFailed += 1;
    else if (r) lastQuarterInProgress += 1;
  }

  return {
    lastQuarterSettled: previousResults.length,
    lastQuarterCompleted,
    lastQuarterPartial,
    lastQuarterInProgress,
    lastQuarterFailed,
    lastQuarterStall,
    currentPoolCount: currentTasks.length,
  };
}

export function formatTaskSettlementLine(stats: TaskSettlementStats): string {
  if (stats.lastQuarterSettled === 0) {
    return '上季结算：无（开局或尚未点过「下季」）';
  }
  const parts = [
    `共 ${stats.lastQuarterSettled} 条`,
    `达成 ${stats.lastQuarterCompleted}`,
    stats.lastQuarterPartial > 0 ? `有进展 ${stats.lastQuarterPartial}` : null,
    `进行中 ${stats.lastQuarterInProgress}`,
    stats.lastQuarterFailed > 0 ? `未达成 ${stats.lastQuarterFailed}` : null,
    stats.lastQuarterStall > 0 ? `怠政 ${stats.lastQuarterStall}` : null,
  ].filter(Boolean);
  return `上季结算：${parts.join(' · ')}`;
}

export function formatCurrentPoolLine(stats: TaskSettlementStats): string {
  return `本季任务池：${stats.currentPoolCount} 条`;
}

type DecreeImpactInput = {
  decreeText?: string;
  decreePublished?: boolean;
  reports?: Array<Record<string, unknown>>;
  quarterReport?: Record<string, unknown>;
  delegationEnqueued?: {
    task_id?: string;
    title?: string;
    task_path?: string;
    phases_total?: number;
  } | null;
};

export function buildDecreeImpactLines(input: DecreeImpactInput): string[] {
  const text = (input.decreeText || '').trim();
  if (!input.decreePublished && !text) {
    return ['本季未发诏'];
  }

  const lines: string[] = [];
  const qr = input.quarterReport || {};
  const narrative = qr.decree_narrative as { summary_zh?: string; segments?: string[] } | undefined;
  if (narrative?.summary_zh) {
    lines.push(String(narrative.summary_zh));
  } else if (typeof qr.edict_frame_normalized_zh === 'string' && qr.edict_frame_normalized_zh.trim()) {
    lines.push(qr.edict_frame_normalized_zh.trim());
  }

  const reports = input.reports || [];
  const appliedTotal = reports.reduce(
    (sum, r) => sum + Number(r.applied_effects_count ?? 0),
    0,
  );

  const execFrame = qr.edict_execution_frame as Record<string, unknown> | undefined;
  const resolvedPack =
    (execFrame?.resolved_pack as Record<string, unknown> | undefined) ||
    ((qr.edict_execution as Record<string, unknown> | undefined)?.resolved_pack as
      | Record<string, unknown>
      | undefined);
  const segmentPacks = (resolvedPack?.segment_packs || []) as Array<Record<string, unknown>>;
  if (segmentPacks.length > 0) {
    lines.push(`多域诏书：共 ${segmentPacks.length} 段`);
    for (const seg of segmentPacks) {
      const dom = String(seg.domain || '—');
      const tk = String(seg.task_key || '—');
      const st = String(seg.status || '—');
      const n = Number(seg.effects_count ?? 0);
      lines.push(`· ${dom}/${tk}：${st}${n > 0 ? `（${n} 项即时效果）` : ''}`);
    }
  }

  if (appliedTotal > 0) {
    lines.push(`诏书即时结算：已施加 ${appliedTotal} 项效果`);
  }

  const enq = input.delegationEnqueued;
  if (enq && (enq.title || enq.task_id)) {
    const phases = enq.phases_total ? `，共 ${enq.phases_total} 季` : '';
    lines.push(`跨季承办已入队：${enq.title || enq.task_id}${phases}（季末「下季」推进）`);
  } else if (text && appliedTotal === 0 && lines.length === 0) {
    lines.push('本季诏书已登记，无即时数值项或未入队跨季任务');
  }

  if (text && lines.length === 0) {
    const snippet = text.length > 48 ? `${text.slice(0, 48)}…` : text;
    lines.push(`诏书：${snippet}`);
  }

  return lines.length > 0 ? lines : ['无'];
}

type TaskQuarterEndPayload = {
  stall?: Array<Record<string, unknown>>;
  completed?: Array<Record<string, unknown>>;
  failed_expired?: Array<Record<string, unknown>>;
};

export function formatTaskQuarterEndLines(
  taskQuarterEnd?: Record<string, unknown> | null,
): string[] {
  const pack = (taskQuarterEnd || {}) as TaskQuarterEndPayload;
  const stall = pack.stall || [];
  const completed = pack.completed || [];
  const failed = pack.failed_expired || [];
  if (!stall.length && !completed.length && !failed.length) {
    return ['本季任务季末：无结算项（或任务已在当季达成）'];
  }
  const lines: string[] = [];
  if (stall.length) {
    lines.push(`怠政 ${stall.length} 条（季末未完成，已扣点）`);
    for (const row of stall.slice(0, 4)) {
      lines.push(`· ${String(row.title || row.template_id || '任务')}：怠政`);
    }
  }
  if (completed.length) {
    lines.push(`本季达成 ${completed.length} 条`);
    for (const row of completed.slice(0, 3)) {
      lines.push(`· ${String(row.title || row.template_id || '任务')}：完成`);
    }
  }
  if (failed.length) {
    lines.push(`逾期失败 ${failed.length} 条（已移出任务池并整包惩罚）`);
    for (const row of failed.slice(0, 4)) {
      lines.push(`· ${String(row.title || row.template_id || '任务')}：逾期`);
    }
  }
  return lines;
}
