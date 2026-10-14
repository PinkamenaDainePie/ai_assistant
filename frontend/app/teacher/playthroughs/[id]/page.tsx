'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useRequireAuth } from '../../../../components/auth/AuthProvider';
import { PlaythroughSummaryPanel } from '../../../../components/classroom/PlaythroughSummaryPanel';
import { PlaythroughQuarterTimelinePanel } from '../../../../components/classroom/PlaythroughQuarterTimelinePanel';
import { TeacherReviewPanel } from '../../../../components/classroom/TeacherReviewPanel';
import { fetchTeacherPlaythrough, type PlaythroughRecord } from '../../../../lib/classroomApi';
import {
  formatPlaythroughStatus,
  formatScenarioLabel,
  formatPlaythroughProgress,
} from '../../../../game/scenarioLabels';
import { formatOfficialPlaythroughScoreLabel } from '../../../../lib/playthroughSummary';

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export default function TeacherPlaythroughDetailPage() {
  const params = useParams();
  const id = String(params?.id || '');
  const { ready } = useRequireAuth(['teacher']);
  const [record, setRecord] = useState<PlaythroughRecord | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ready || !id) return;
    void (async () => {
      try {
        const row = await fetchTeacherPlaythrough(id);
        setRecord(row);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败');
      }
    })();
  }, [ready, id]);

  if (!ready) {
    return <p className="ui-muted">加载中…</p>;
  }

  return (
    <>
      <p className="ui-back">
        <Link className="ui-link" href="/teacher">
          ← 返回列表
        </Link>
      </p>

      {error ? (
        <p className="ui-error" role="alert">
          {error}
        </p>
      ) : null}
      {!record && !error ? <p className="ui-muted">加载中…</p> : null}

      {record ? (
        <>
          <section className="ui-panel">
            <div className="ui-panel__head">
              <h2 className="ui-panel__title">游玩记录详情</h2>
            </div>
            <dl className="ui-dl">
              <dt>学生</dt>
              <dd>{record.student_name}</dd>
              <dt>学号</dt>
              <dd>{record.student_id || '—'}</dd>
              <dt>剧本</dt>
              <dd>{formatScenarioLabel(record.scenario_code)}</dd>
              <dt>状态</dt>
              <dd>{formatPlaythroughStatus(record.status)}</dd>
              <dt>进度</dt>
              <dd>{formatPlaythroughProgress(record.scenario_code, record.current_quarter)}</dd>
              <dt>正式评分</dt>
              <dd>{formatOfficialPlaythroughScoreLabel(record)}</dd>
              <dt>结局类型</dt>
              <dd>{record.ending_type || '—'}</dd>
              <dt>开始时间</dt>
              <dd>{formatTime(record.started_at)}</dd>
              <dt>结束时间</dt>
              <dd>{formatTime(record.finished_at)}</dd>
              <dt>会话 ID</dt>
              <dd>
                <code className="ui-code">{record.game_session_id}</code>
              </dd>
            </dl>
          </section>

          <TeacherReviewPanel record={record} onSaved={setRecord} />

          <PlaythroughQuarterTimelinePanel
            quarterChapters={record.quarter_chapters}
            scenarioCode={record.scenario_code}
            currentQuarter={record.current_quarter}
            status={record.status}
          />

          <section className="ui-panel">
            <div className="ui-panel__head">
              <h2 className="ui-panel__title">终局测评</h2>
            </div>
            <PlaythroughSummaryPanel
              summaryJson={record.summary_json}
              status={record.status}
              allowRawJson
            />
          </section>
        </>
      ) : null}
    </>
  );
}
