import type { PlaythroughRecord } from './classroomApi';
import { parsePlaythroughSummary } from './playthroughSummary';

export type ClassPlaythroughStats = {
  studentCount: number;
  playthroughCount: number;
  finishedCount: number;
  inProgressCount: number;
  completionRate: number;
  pendingReviewCount: number;
};

export type StudentGradeSummary = {
  userId: string;
  studentName: string;
  studentId: string;
  playthroughCount: number;
  finishedCount: number;
  highestScore: number | null;
  reviewedCount: number;
  pendingReviewCount: number;
};

export function officialScore(record: PlaythroughRecord): number | null {
  if (record.status !== 'finished') return null;
  if (record.teacher_review_score != null) return record.teacher_review_score;
  return parsePlaythroughSummary(record.summary_json).score;
}

export function isPendingReview(record: PlaythroughRecord): boolean {
  return record.status === 'finished' && record.teacher_review_score == null;
}

export function computeClassStats(items: PlaythroughRecord[]): ClassPlaythroughStats {
  const students = new Set(items.map((i) => i.user_id));
  const finished = items.filter((i) => i.status === 'finished');
  return {
    studentCount: students.size,
    playthroughCount: items.length,
    finishedCount: finished.length,
    inProgressCount: items.filter((i) => i.status === 'in_progress').length,
    completionRate: items.length ? Math.round((finished.length / items.length) * 100) : 0,
    pendingReviewCount: finished.filter((i) => i.teacher_review_score == null).length,
  };
}

export function computeStudentGradeSummaries(items: PlaythroughRecord[]): StudentGradeSummary[] {
  const byUser = new Map<string, PlaythroughRecord[]>();
  for (const item of items) {
    const list = byUser.get(item.user_id) || [];
    list.push(item);
    byUser.set(item.user_id, list);
  }

  return Array.from(byUser.entries())
    .map(([userId, rows]) => {
      const finished = rows.filter((r) => r.status === 'finished');
      const scores = finished
        .map((r) => officialScore(r))
        .filter((s): s is number => s != null);
      return {
        userId,
        studentName: rows[0]?.student_name || '—',
        studentId: rows[0]?.student_id || '—',
        playthroughCount: rows.length,
        finishedCount: finished.length,
        highestScore: scores.length ? Math.max(...scores) : null,
        reviewedCount: finished.filter((r) => r.teacher_review_score != null).length,
        pendingReviewCount: finished.filter((r) => r.teacher_review_score == null).length,
      };
    })
    .sort(
      (a, b) =>
        a.studentId.localeCompare(b.studentId, 'zh-CN') ||
        a.studentName.localeCompare(b.studentName, 'zh-CN'),
    );
}

export function formatPercent(n: number): string {
  return `${n}%`;
}
