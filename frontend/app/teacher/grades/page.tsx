'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRequireAuth } from '../../../components/auth/AuthProvider';
import { TeacherClassFilter } from '../../../components/classroom/TeacherClassFilter';
import {
  fetchTeacherClasses,
  fetchTeacherPlaythroughs,
  type ClassInfo,
} from '../../../lib/classroomApi';
import { computeStudentGradeSummaries } from '../../../lib/teacherPlaythroughStats';

export default function TeacherGradesPage() {
  const { ready, user } = useRequireAuth(['teacher']);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [classId, setClassId] = useState<number | ''>('');
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchTeacherPlaythroughs>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      try {
        const cls = await fetchTeacherClasses();
        setClasses(cls);
        if (cls.length === 1) setClassId(cls[0].id);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载班级失败');
      }
    })();
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      setLoading(true);
      setError('');
      try {
        const list = await fetchTeacherPlaythroughs({
          class_id: classId === '' ? undefined : classId,
        });
        setItems(list);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready, classId]);

  const summaries = useMemo(() => computeStudentGradeSummaries(items), [items]);

  const totals = useMemo(
    () => ({
      students: summaries.length,
      reviewed: summaries.filter((s) => s.reviewedCount > 0).length,
      pending: summaries.reduce((n, s) => n + s.pendingReviewCount, 0),
    }),
    [summaries],
  );

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-console-lead">{user?.name} · 按学生汇总正式成绩</p>

      <section className="ui-console-stats">
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.students}</div>
          <div className="ui-stat-card__label">参与学生</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.reviewed}</div>
          <div className="ui-stat-card__label">已有教师评分</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.pending}</div>
          <div className="ui-stat-card__label">待评局数</div>
        </div>
      </section>

      <section className="ui-panel">
        <div className="ui-panel__head">
          <h2 className="ui-panel__title">筛选</h2>
        </div>
        <div className="ui-toolbar">
          <TeacherClassFilter classes={classes} classId={classId} onClassIdChange={setClassId} />
        </div>
      </section>

      {error ? (
        <p className="ui-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="ui-panel">
        <div className="ui-panel__head">
          <h2 className="ui-panel__title">成绩汇总</h2>
          {loading ? <span className="ui-muted">加载中…</span> : null}
        </div>
        <div className="ui-table-wrap ui-table-wrap--flat">
          <table className="ui-table">
            <thead>
              <tr>
                <th>学生</th>
                <th>学号</th>
                <th>局数</th>
                <th>已完成</th>
                <th>最高分</th>
                <th>已评局数</th>
                <th>待评局数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {summaries.length === 0 && !loading ? (
                <tr>
                  <td colSpan={8} className="ui-table__empty">
                    暂无学生数据
                  </td>
                </tr>
              ) : (
                summaries.map((row) => (
                  <tr key={row.userId}>
                    <td>{row.studentName}</td>
                    <td>{row.studentId}</td>
                    <td>{row.playthroughCount}</td>
                    <td>{row.finishedCount}</td>
                    <td>{row.highestScore != null ? row.highestScore : '—'}</td>
                    <td>{row.reviewedCount}</td>
                    <td>{row.pendingReviewCount > 0 ? row.pendingReviewCount : '—'}</td>
                    <td>
                      <Link className="ui-link" href={`/teacher?class_id=${classId || ''}`}>
                        查看记录
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
