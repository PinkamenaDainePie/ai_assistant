'use client';

import React, { Suspense, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useAuth, useRequireAuth } from '../../components/auth/AuthProvider';
import {
  fetchTeacherClasses,
  fetchTeacherPlaythroughs,
  type ClassInfo,
  type PlaythroughRecord,
} from '../../lib/classroomApi';
import {
  formatPlaythroughStatus,
  formatScenarioLabel,
  formatPlaythroughProgress,
} from '../../game/scenarioLabels';
import { formatOfficialPlaythroughScoreLabel } from '../../lib/playthroughSummary';
import { formatTeacherTime, playthroughStatusClass } from '../../lib/teacherUi';

function statusClass(status: string): string {
  return playthroughStatusClass(status);
}

function formatTime(iso: string | null | undefined): string {
  return formatTeacherTime(iso);
}

function TeacherDashboardContent() {
  const searchParams = useSearchParams();
  const initialClassId = searchParams.get('class_id');
  const { ready, user } = useRequireAuth(['teacher']);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [classId, setClassId] = useState<number | ''>(() => {
    if (initialClassId && /^\d+$/.test(initialClassId)) return Number(initialClassId);
    return '';
  });
  const [status, setStatus] = useState<string>('');
  const [items, setItems] = useState<PlaythroughRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      try {
        const cls = await fetchTeacherClasses();
        setClasses(cls);
        if (classId === '' && cls.length === 1) setClassId(cls[0].id);
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
          status: status || undefined,
        });
        setItems(list);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载记录失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready, classId, status]);

  const stats = useMemo(() => {
    const students = new Set(items.map((i) => i.user_id)).size;
    const finished = items.filter((i) => i.status === 'finished').length;
    const inProgress = items.filter((i) => i.status === 'in_progress').length;
    return { total: items.length, students, finished, inProgress };
  }, [items]);

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-console-lead">{user?.name} · 班级学生游玩数据</p>

      <section className="ui-console-stats">
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.total}</div>
          <div className="ui-stat-card__label">记录总数</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.students}</div>
          <div className="ui-stat-card__label">参与学生</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.finished}</div>
          <div className="ui-stat-card__label">已完成</div>
        </div>
        <div className="ui-stat-card">
          <div className="ui-stat-card__value">{stats.inProgress}</div>
          <div className="ui-stat-card__label">进行中</div>
        </div>
      </section>

      <section className="ui-panel">
        <div className="ui-panel__head">
          <h2 className="ui-panel__title">筛选</h2>
        </div>
        <div className="ui-toolbar">
          <div className="ui-field ui-field--inline">
            <label className="ui-label" htmlFor="filter-class">
              班级
            </label>
            <select
              id="filter-class"
              className="ui-select"
              value={classId}
              onChange={(e) => setClassId(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <option value="">全部班级</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="ui-field ui-field--inline">
            <label className="ui-label" htmlFor="filter-status">
              状态
            </label>
            <select
              id="filter-status"
              className="ui-select"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">全部</option>
              <option value="in_progress">进行中</option>
              <option value="finished">已完成</option>
              <option value="abandoned">已放弃</option>
            </select>
          </div>
        </div>
      </section>

      {error ? (
        <p className="ui-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="ui-panel">
        <div className="ui-panel__head">
          <h2 className="ui-panel__title">游玩记录</h2>
          {loading ? <span className="ui-muted">加载中…</span> : null}
        </div>
        <div className="ui-table-wrap ui-table-wrap--flat">
          <table className="ui-table">
            <thead>
              <tr>
                <th>学生</th>
                <th>学号</th>
                <th>剧本</th>
                <th>状态</th>
                <th>进度</th>
                <th>正式评分</th>
                <th>开始时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={8} className="ui-table__empty">
                    暂无游玩记录
                  </td>
                </tr>
              ) : (
                items.map((row) => (
                  <tr key={row.id}>
                    <td>{row.student_name || '—'}</td>
                    <td>{row.student_id || '—'}</td>
                    <td>{formatScenarioLabel(row.scenario_code)}</td>
                    <td>
                      <span className={statusClass(row.status)}>
                        {formatPlaythroughStatus(row.status)}
                      </span>
                    </td>
                    <td>{formatPlaythroughProgress(row.scenario_code, row.current_quarter)}</td>
                    <td>{formatOfficialPlaythroughScoreLabel(row)}</td>
                    <td>{formatTime(row.started_at)}</td>
                    <td>
                      <Link className="ui-link" href={`/teacher/playthroughs/${row.id}`}>
                        查看
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

export default function TeacherDashboardPage() {
  return (
    <Suspense fallback={<p className="ui-muted">加载中…</p>}>
      <TeacherDashboardContent />
    </Suspense>
  );
}
