'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRequireAuth } from '../../../components/auth/AuthProvider';
import { TeacherClassFilter } from '../../../components/classroom/TeacherClassFilter';
import {
  fetchTeacherClasses,
  fetchTeacherPlaythroughs,
  type ClassInfo,
  type PlaythroughRecord,
} from '../../../lib/classroomApi';
import {
  formatScenarioLabel,
  formatPlaythroughProgress,
} from '../../../game/scenarioLabels';
import { formatOfficialPlaythroughScoreLabel } from '../../../lib/playthroughSummary';
import { isPendingReview } from '../../../lib/teacherPlaythroughStats';
import { formatTeacherTime } from '../../../lib/teacherUi';

export default function TeacherPendingPage() {
  const { ready, user } = useRequireAuth(['teacher']);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [classId, setClassId] = useState<number | ''>('');
  const [items, setItems] = useState<PlaythroughRecord[]>([]);
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
          status: 'finished',
        });
        setItems(list.filter(isPendingReview));
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready, classId]);

  const stats = useMemo(
    () => ({
      pending: items.length,
      students: new Set(items.map((i) => i.user_id)).size,
    }),
    [items],
  );

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-console-lead">{user?.name} · 已完成但尚未录入正式成绩</p>

      <section className="ui-console-stats">
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.pending}</div>
          <div className="ui-stat-card__label">待评记录</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.students}</div>
          <div className="ui-stat-card__label">涉及学生</div>
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
          <h2 className="ui-panel__title">待评列表</h2>
          {loading ? <span className="ui-muted">加载中…</span> : null}
        </div>
        <div className="ui-table-wrap ui-table-wrap--flat">
          <table className="ui-table">
            <thead>
              <tr>
                <th>学生</th>
                <th>学号</th>
                <th>剧本</th>
                <th>进度</th>
                <th>系统参考分</th>
                <th>结束时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={7} className="ui-table__empty">
                    暂无待评记录
                  </td>
                </tr>
              ) : (
                items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.student_name || '—'}</td>
                    <td>{row.student_id || '—'}</td>
                    <td>{formatScenarioLabel(row.scenario_code)}</td>
                    <td>{formatPlaythroughProgress(row.scenario_code, row.current_quarter)}</td>
                    <td>{formatOfficialPlaythroughScoreLabel(row)}</td>
                    <td>{formatTeacherTime(row.finished_at)}</td>
                    <td>
                      <Link className="ui-link" href={`/teacher/playthroughs/${row.id}`}>
                        去评分
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
