export function formatMingClosedEffect(effect: Record<string, unknown> | null | undefined): string {
  if (!effect || typeof effect !== 'object') return '（无明细）';
  const parts: string[] = [];
  const metrics = effect.metrics as Record<string, number> | undefined;
  if (metrics && typeof metrics === 'object') {
    for (const [k, v] of Object.entries(metrics)) {
      parts.push(`${k} ${Number(v) >= 0 ? '+' : ''}${v}`);
    }
  }
  if (Array.isArray(effect.regions)) {
    parts.push(`地区变化 ${effect.regions.length} 项`);
  }
  if (Array.isArray(effect.buildings)) {
    parts.push(`建筑 ${effect.buildings.length} 项`);
  }
  if (Array.isArray(effect.departments)) {
    parts.push(`衙门 ${effect.departments.length} 项`);
  }
  if (Array.isArray(effect.technologies)) {
    parts.push(`科技 ${effect.technologies.length} 项`);
  }
  return parts.length ? parts.join(' · ') : '（效果已落地，详见邸报详明）';
}

export function isMingLongTermIssue(issue: { fail_condition?: string }): boolean {
  return /甲申|贯穿一朝|倾国之大计/.test(issue.fail_condition || '');
}

export function countMingDecreeIssues(issues: Array<{ origin_kind?: string; is_manual?: boolean }>): number {
  return issues.filter(
    (i) => i.origin_kind === 'decree' || (!i.origin_kind && i.is_manual),
  ).length;
}
