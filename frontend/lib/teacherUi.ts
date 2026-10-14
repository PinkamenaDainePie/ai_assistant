export function formatTeacherTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export function playthroughStatusClass(status: string): string {
  if (status === 'finished') return 'ui-badge ui-badge--success';
  if (status === 'in_progress') return 'ui-badge ui-badge--info';
  if (status === 'abandoned') return 'ui-badge ui-badge--muted';
  return 'ui-badge';
}
