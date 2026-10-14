import type { TaskRow } from './taskPoolDisplay';
import { isCrossQuarterTask, taskDisplaySubtitle } from './taskPoolDisplay';

export type TaskDetailSection = {
  title: string;
  lines: string[];
};

export type TaskDetailView = {
  id: string;
  title: string;
  subtitle: string;
  statusLabel: string;
  description: string;
  sections: TaskDetailSection[];
};

const STATUS_ZH: Record<string, string> = {
  active: '进行中',
  pending: '待解决',
  completed: '已完成',
  failed: '未达成',
  partial: '有进展',
};

const RESOLUTION_ZH: Record<string, string> = {
  objectives: '指标达成',
  delegation: '诏书委派',
  edict_execution: '跨季承办',
  campaign_story: '主线剧情',
};

const CATEGORY_ZH: Record<string, string> = {
  finance: '财政',
  military: '军事',
  internal_affairs: '内政',
  faction: '朝局',
  fiscal: '财政',
  personnel: '人事',
  agriculture: '农政',
  livelihood: '民生',
  edict_execution: '诏令承办',
};

function fmtQuarter(q: unknown): string | null {
  const n = Number(q);
  if (!Number.isFinite(n) || n <= 0) return null;
  return `第 ${n} 季`;
}

function formatEffectList(items: unknown, empty = '—'): string[] {
  if (!Array.isArray(items) || items.length === 0) return [empty];
  return items.map((item) => {
    if (!item || typeof item !== 'object') return String(item);
    const row = item as Record<string, unknown>;
    const type = String(row.type ?? '');
    const key = String(row.key ?? '');
    const value = row.value;
    if (type === 'stat_change' || type === 'stat_at_least' || type === 'stat_at_most') {
      const sign = typeof value === 'number' && value >= 0 ? '+' : '';
      return `${key} ${sign}${value ?? ''}`.trim();
    }
    if (type === 'stat_reduce_by') {
      return `${key} 至少降低 ${String(value ?? '')}`;
    }
    return [type, key, value].filter(Boolean).join(' · ');
  });
}

function buildEdictExecutionSection(t: TaskRow): TaskDetailSection | null {
  const em = (t.edict_execution as Record<string, unknown>) || {};
  const lines: string[] = [];
  const executor = String(em.display_executor_zh ?? '').trim();
  if (executor) lines.push(`承办：${executor}`);
  const phasesTotal = Math.max(1, Number(em.phases_total ?? 1));
  const phaseIndex = Math.max(0, Number(em.phase_index ?? 0));
  lines.push(`阶段进度：${phaseIndex + 1} / ${phasesTotal}`);
  const domain = String(em.domain ?? t.category ?? '').trim();
  const taskKey = String(em.task_key ?? t.template_id ?? '').trim();
  if (domain || taskKey) lines.push(`关联诏令：${domain}/${taskKey}`);
  const command = String(em.normalized_command_zh ?? '').trim();
  if (command) lines.push(`诏令摘要：${command}`);
  return lines.length > 0 ? { title: '承办详情', lines } : null;
}

function buildDelegationSection(t: TaskRow): TaskDetailSection | null {
  const d = (t.delegation as Record<string, unknown>) || {};
  const lines: string[] = [];
  const phases = Math.max(1, Number(d.phases_total ?? 1));
  const phase = Math.max(0, Number(d.phase_index ?? 0));
  lines.push(`委派进度：${phase + 1} / ${phases}`);
  const hint = String(d.hint_zh ?? d.summary_zh ?? '').trim();
  if (hint) lines.push(hint);
  return lines.length > 0 ? { title: '委派详情', lines } : null;
}

export function buildTaskDetailView(
  t: TaskRow,
  currentQuarter: number,
  yearLabel: string,
): TaskDetailView {
  const id = String(t.task_id ?? t.template_id ?? t.title ?? 'task');
  const title = String(t.title || t.template_id || '未命名任务');
  const assigned = fmtQuarter(t.assigned_quarter);
  const deadline = fmtQuarter(t.deadline_quarter);
  const subtitleParts = [yearLabel, assigned ? `下达 ${assigned}` : null, deadline ? `期限 ${deadline}` : null].filter(
    Boolean,
  );
  const status = String(t.status ?? 'active').toLowerCase();
  const resolution = String(t.resolution_kind ?? 'objectives');
  const category = String(t.category ?? '');

  const sections: TaskDetailSection[] = [
    {
      title: '任务概况',
      lines: [
        `类型：${CATEGORY_ZH[category] || category || '朝政'}`,
        `结算方式：${RESOLUTION_ZH[resolution] || resolution}`,
        isCrossQuarterTask(t) ? '性质：跨季任务' : `所属季度：第 ${currentQuarter || '-'} 季`,
        taskDisplaySubtitle(t) ? `进度：${taskDisplaySubtitle(t)}` : '进度：本季推进',
      ],
    },
    {
      title: '完成目标',
      lines: formatEffectList(t.objectives, '按剧情或指标推进，详见任务说明。'),
    },
    {
      title: '完成奖励',
      lines: formatEffectList(t.rewards, '暂无明确奖励条目。'),
    },
    {
      title: '失败/怠政代价',
      lines: [
        ...formatEffectList(t.penalties, ''),
        ...formatEffectList(t.stall_penalties_per_quarter, ''),
      ].filter(Boolean),
    },
  ];

  if (sections[3].lines.length === 0) {
    sections[3].lines = ['逾期未推进将累积朝局压力。'];
  }

  const edictSection = buildEdictExecutionSection(t);
  if (edictSection) sections.splice(1, 0, edictSection);
  const delegationSection = buildDelegationSection(t);
  if (delegationSection) sections.splice(1, 0, delegationSection);

  const campaignMeta = (t.campaign_meta as Record<string, unknown>) || {};
  const storyOwner = String(campaignMeta.story_owner_zh ?? campaignMeta.owner_zh ?? '').trim();
  if (storyOwner) {
    sections.push({ title: '剧情关联', lines: [`主理：${storyOwner}`] });
  }

  const description =
    String(t.description ?? '').trim() ||
    '暂无详细说明。可通过颁布相关诏令、完成季度重心与朝局事件推进此任务。';

  return {
    id,
    title,
    subtitle: subtitleParts.join(' · ') || yearLabel,
    statusLabel: STATUS_ZH[status] || RESOLUTION_ZH[resolution] || '待解决',
    description,
    sections: sections.filter((s) => s.lines.length > 0),
  };
}

export function taskRowKey(t: TaskRow, index: number): string {
  return String(t.task_id ?? t.template_id ?? `task-${index}`);
}
