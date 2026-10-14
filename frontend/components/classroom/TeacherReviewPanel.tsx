'use client';

import React, { useEffect, useState } from 'react';
import type { PlaythroughRecord } from '../../lib/classroomApi';
import { updateTeacherPlaythroughReview } from '../../lib/classroomApi';
import { formatPlaythroughScore, parsePlaythroughSummary } from '../../lib/playthroughSummary';

type Props = {
  record: PlaythroughRecord;
  onSaved: (updated: PlaythroughRecord) => void;
};

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export function TeacherReviewPanel({ record, onSaved }: Props) {
  const systemScore = formatPlaythroughScore({
    status: record.status,
    summary_json: record.summary_json,
  });
  const parsed = parsePlaythroughSummary(record.summary_json);

  const [score, setScore] = useState('');
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [savedHint, setSavedHint] = useState('');

  useEffect(() => {
    setScore(record.teacher_review_score != null ? String(record.teacher_review_score) : '');
    setComment(record.teacher_review_comment || '');
    setError('');
    setSavedHint('');
  }, [record.id, record.teacher_review_score, record.teacher_review_comment]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSavedHint('');
    const n = Number(score);
    if (!Number.isFinite(n) || n < 0 || n > 100) {
      setError('请输入 0–100 的整数分数');
      return;
    }
    setSaving(true);
    try {
      const updated = await updateTeacherPlaythroughReview(record.id, {
        score: Math.round(n),
        comment: comment.trim() || undefined,
      });
      onSaved(updated);
      setSavedHint('已保存正式成绩');
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="ui-panel">
      <div className="ui-panel__head">
        <h2 className="ui-panel__title">正式成绩（教师评语）</h2>
        {record.teacher_review_at ? (
          <span className="ui-muted">上次更新 {formatTime(record.teacher_review_at)}</span>
        ) : null}
      </div>

      <dl className="ui-dl ui-dl--compact">
        <dt>系统参考分</dt>
        <dd>
          {systemScore}
          {parsed.score != null && record.summary_json?.score_source ? (
            <span className="ui-muted">
              {' '}
              · {String(record.summary_json.score_source) === 'llm' ? 'LLM 终评' : '启发式'}
            </span>
          ) : null}
        </dd>
        <dt>当前正式分</dt>
        <dd>
          {record.teacher_review_score != null ? (
            <strong>{record.teacher_review_score}</strong>
          ) : (
            <span className="ui-muted">尚未录入</span>
          )}
        </dd>
      </dl>

      <form className="ui-form" onSubmit={(e) => void handleSubmit(e)}>
        <div className="ui-field">
          <label className="ui-label" htmlFor="teacher-score">
            分数（0–100）
          </label>
          <input
            id="teacher-score"
            className="ui-input"
            type="number"
            min={0}
            max={100}
            step={1}
            value={score}
            onChange={(e) => setScore(e.target.value)}
            placeholder="如 85"
            required
          />
        </div>
        <div className="ui-field">
          <label className="ui-label" htmlFor="teacher-comment">
            评语
          </label>
          <textarea
            id="teacher-comment"
            className="ui-input"
            style={{ minHeight: '6rem', resize: 'vertical' }}
            rows={4}
            maxLength={2000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="可选：对本局决策与终局的简短评语"
          />
        </div>
        {error ? (
          <p className="ui-error" role="alert">
            {error}
          </p>
        ) : null}
        {savedHint ? <p className="ui-muted">{savedHint}</p> : null}
        <button type="submit" className="ui-btn ui-btn--primary" disabled={saving}>
          {saving ? '保存中…' : '保存正式成绩'}
        </button>
      </form>
    </section>
  );
}
