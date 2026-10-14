'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRequireAuth } from '../../components/auth/AuthProvider';
import { UserAvatar, notifyProfileUpdated } from '../../components/auth/UserAvatar';
import {
  AVATAR_PRESETS,
  loadProfile,
  setAvatarCustom,
  setAvatarPreset,
  type AvatarPreset,
} from '../../lib/profileStorage';
import { fetchMyPlaythroughs, type PlaythroughRecord } from '../../lib/classroomApi';
import { PlaythroughDetailModal } from '../../components/classroom/PlaythroughDetailModal';
import {
  formatPlaythroughStatus,
  formatScenarioLabel,
  formatPlaythroughProgress,
} from '../../game/scenarioLabels';
import { formatPlaythroughScore } from '../../lib/playthroughSummary';

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="ui-stat-card">
      <div className="ui-stat-card__value">{value}</div>
      <div className="ui-stat-card__label">{label}</div>
    </div>
  );
}

export default function AccountPage() {
  const router = useRouter();
  const { ready, user } = useRequireAuth();
  const [records, setRecords] = useState<PlaythroughRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [preset, setPreset] = useState<AvatarPreset>('indigo');
  const [detailRecord, setDetailRecord] = useState<PlaythroughRecord | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!ready || !user) return;
    setPreset(loadProfile(user.id).preset || 'indigo');
    void (async () => {
      setLoading(true);
      setError('');
      try {
        const items = await fetchMyPlaythroughs();
        setRecords(items);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready, user]);

  const stats = useMemo(() => {
    const total = records.length;
    const finished = records.filter((r) => r.status === 'finished').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const completionRate = total > 0 ? Math.round((finished / total) * 100) : 0;
    return { total, finished, inProgress, completionRate };
  }, [records]);

  const byScenario = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of records) {
      map.set(r.scenario_code, (map.get(r.scenario_code) || 0) + 1);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [records]);

  const maxScenarioCount = byScenario[0]?.[1] || 1;

  const statusSlices = useMemo(() => {
    const finished = records.filter((r) => r.status === 'finished').length;
    const inProgress = records.filter((r) => r.status === 'in_progress').length;
    const other = records.length - finished - inProgress;
    return { finished, inProgress, other, total: records.length };
  }, [records]);

  const donutStyle = useMemo(() => {
    const t = statusSlices.total || 1;
    const fPct = (statusSlices.finished / t) * 100;
    const iPct = (statusSlices.inProgress / t) * 100;
    const oPct = 100 - fPct - iPct;
    return {
      background: `conic-gradient(
        #1b7f4b 0 ${fPct}%,
        #4d49c1 ${fPct}% ${fPct + iPct}%,
        #e0e0e0 ${fPct + iPct}% 100%
      )`,
    } as React.CSSProperties;
  }, [statusSlices]);

  const pickPreset = (id: AvatarPreset) => {
    if (!user) return;
    setAvatarPreset(user.id, id);
    setPreset(id);
    notifyProfileUpdated();
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;
    if (file.size > 512 * 1024) {
      setError('头像图片请小于 512KB');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result || '');
      setAvatarCustom(user.id, url);
      notifyProfileUpdated();
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-console-lead">{user?.email}</p>

      <section className="ui-panel ui-account-profile">
        <div className="ui-account-profile__avatar">
          <UserAvatar userId={user!.id} name={user!.name} size="lg" />
          <div>
            <h2 className="ui-account-profile__name">{user?.name}</h2>
            {user?.student_id ? (
              <p className="ui-account-profile__meta">学号 {user.student_id}</p>
            ) : null}
          </div>
        </div>

        <div className="ui-account-avatar-picker">
          <p className="ui-label">更换头像</p>
          <div className="ui-account-avatar-picker__row">
            {AVATAR_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`ui-avatar ui-avatar--${p.id} ui-avatar--pick${preset === p.id ? ' ui-avatar--pick-active' : ''}`}
                title={p.label}
                onClick={() => pickPreset(p.id)}
              >
                {(user?.name || '?').slice(0, 1)}
              </button>
            ))}
            <button
              type="button"
              className="ui-avatar ui-avatar--upload"
              title="上传图片"
              onClick={() => fileRef.current?.click()}
            >
              +
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="ui-sr-only"
              onChange={onFileChange}
            />
          </div>
        </div>
      </section>

      {error ? (
        <p className="ui-error" role="alert">
          {error}
        </p>
      ) : null}

      <section className="ui-console-stats">
        <StatCard label="总对局" value={stats.total} />
        <StatCard label="已完成" value={stats.finished} />
        <StatCard label="进行中" value={stats.inProgress} />
        <StatCard label="完成率" value={`${stats.completionRate}%`} />
      </section>

      <div className="ui-console-grid">
        <section className="ui-panel">
          <h2 className="ui-card__title">剧本分布</h2>
          {byScenario.length === 0 ? (
            <p className="ui-muted">暂无对局数据，去首页进入制度模拟吧。</p>
          ) : (
            <ul className="ui-bar-chart">
              {byScenario.map(([code, count]) => (
                <li key={code} className="ui-bar-chart__row">
                  <span className="ui-bar-chart__label">{formatScenarioLabel(code)}</span>
                  <div className="ui-bar-chart__track">
                    <div
                      className="ui-bar-chart__fill"
                      style={{ width: `${Math.round((count / maxScenarioCount) * 100)}%` }}
                    />
                  </div>
                  <span className="ui-bar-chart__value">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="ui-panel">
          <h2 className="ui-card__title">对局状态</h2>
          <div className="ui-donut-wrap">
            <div className="ui-donut" style={donutStyle}>
              <div className="ui-donut__hole">
                <span className="ui-donut__num">{statusSlices.total}</span>
                <span className="ui-donut__cap">对局</span>
              </div>
            </div>
            <ul className="ui-donut-legend">
              <li>
                <span className="ui-donut-legend__dot ui-donut-legend__dot--done" />
                已完成 {statusSlices.finished}
              </li>
              <li>
                <span className="ui-donut-legend__dot ui-donut-legend__dot--prog" />
                进行中 {statusSlices.inProgress}
              </li>
              <li>
                <span className="ui-donut-legend__dot ui-donut-legend__dot--other" />
                其他 {statusSlices.other}
              </li>
            </ul>
          </div>
        </section>
      </div>

      <section className="ui-panel ui-account-saves">
        <h2 className="ui-card__title">游玩存档</h2>
        {loading ? <p className="ui-muted">加载存档…</p> : null}
        {!loading && records.length === 0 ? (
          <p className="ui-muted">还没有存档记录。</p>
        ) : null}
        {!loading && records.length > 0 ? (
          <div className="ui-table-wrap ui-table-wrap--flat">
            <table className="ui-table">
              <thead>
                <tr>
                  <th>剧本</th>
                  <th>状态</th>
                  <th>进度</th>
                  <th>评分</th>
                  <th>结局</th>
                  <th>开始</th>
                  <th>结束</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.id}
                    className="ui-table__row--clickable"
                    onClick={() => setDetailRecord(r)}
                  >
                    <td>{formatScenarioLabel(r.scenario_code)}</td>
                    <td>{formatPlaythroughStatus(r.status)}</td>
                    <td>{formatPlaythroughProgress(r.scenario_code, r.current_quarter)}</td>
                    <td>{formatPlaythroughScore(r)}</td>
                    <td>{r.ending_type || '—'}</td>
                    <td>{formatTime(r.started_at)}</td>
                    <td>{formatTime(r.finished_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {!loading && records.length > 0 ? (
          <button
            type="button"
            className="ui-btn ui-btn--primary ui-account-continue"
            onClick={() => router.push('/')}
          >
            继续游戏
          </button>
        ) : null}
      </section>

      <PlaythroughDetailModal record={detailRecord} onClose={() => setDetailRecord(null)} />
    </>
  );
}
