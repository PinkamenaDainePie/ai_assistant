'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRequireAuth } from '../../../components/auth/AuthProvider';
import {
  fetchTeacherClasses,
  fetchTeacherPlaythroughs,
  type ClassInfo,
} from '../../../lib/classroomApi';
import {
  computeClassStats,
  formatPercent,
  type ClassPlaythroughStats,
} from '../../../lib/teacherPlaythroughStats';

type ClassRow = {
  info: ClassInfo;
  stats: ClassPlaythroughStats;
};

export default function TeacherOverviewPage() {
  const { ready, user } = useRequireAuth(['teacher']);
  const [rows, setRows] = useState<ClassRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      setLoading(true);
      setError('');
      try {
        const classes = await fetchTeacherClasses();
        const loaded = await Promise.all(
          classes.map(async (info) => {
            const items = await fetchTeacherPlaythroughs({ class_id: info.id });
            return { info, stats: computeClassStats(items) };
          }),
        );
        setRows(loaded);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready]);

  const totals = useMemo(() => {
    const agg = rows.reduce(
      (acc, row) => ({
        studentCount: acc.studentCount + row.stats.studentCount,
        playthroughCount: acc.playthroughCount + row.stats.playthroughCount,
        finishedCount: acc.finishedCount + row.stats.finishedCount,
        inProgressCount: acc.inProgressCount + row.stats.inProgressCount,
        pendingReviewCount: acc.pendingReviewCount + row.stats.pendingReviewCount,
      }),
      {
        studentCount: 0,
        playthroughCount: 0,
        finishedCount: 0,
        inProgressCount: 0,
        pendingReviewCount: 0,
      },
    );
    return {
      ...agg,
      completionRate: agg.playthroughCount
        ? Math.round((agg.finishedCount / agg.playthroughCount) * 100)
        : 0,
      classCount: rows.length,
    };
  }, [rows]);

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-console-lead">{user?.name} · 各班级游玩与评阅概况</p>

      <section className="ui-console-stats">
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.classCount}</div>
          <div className="ui-stat-card__label">班级数</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.playthroughCount}</div>
          <div className="ui-stat-card__label">记录总数</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{formatPercent(totals.completionRate)}</div>
          <div className="ui-stat-card__label">完成率</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{totals.pendingReviewCount}</div>
          <div className="ui-stat-card__label">待评</div>
        </div>
      </section>

      {error ? (
        <p className="ui-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="ui-panel">
        <div className="ui-panel__head">
          <h2 className="ui-panel__title">班级概览</h2>
          {loading ? <span className="ui-muted">加载中…</span> : null}
        </div>
        <div className="ui-table-wrap ui-table-wrap--flat">
          <table className="ui-table">
            <thead>
              <tr>
                <th>班级</th>
                <th>学期</th>
                <th>参与学生</th>
                <th>记录数</th>
                <th>已完成</th>
                <th>进行中</th>
                <th>完成率</th>
                <th>待评</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !loading ? (
                <tr>
                  <td colSpan={9} className="ui-table__empty">
                    暂无班级数据
                  </td>
                </tr>
              ) : (
                rows.map(({ info, stats }) => (
                  <tr key={info.id}>
                    <td>{info.name}</td>
                    <td>{info.semester || '—'}</td>
                    <td>{stats.studentCount}</td>
                    <td>{stats.playthroughCount}</td>
                    <td>{stats.finishedCount}</td>
                    <td>{stats.inProgressCount}</td>
                    <td>{formatPercent(stats.completionRate)}</td>
                    <td>
                      {stats.pendingReviewCount > 0 ? (
                        <strong>{stats.pendingReviewCount}</strong>
                      ) : (
                        stats.pendingReviewCount
                      )}
                    </td>
                    <td>
                      <Link className="ui-link" href={`/teacher?class_id=${info.id}`}>
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
