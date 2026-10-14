import React, { useEffect, useMemo, useState } from 'react';
import { useGameStore } from '../game/store';
import {
  GAME_PHASE_ZH,
  isCrossQuarterTask,
  sortTasksForDisplay,
  taskDisplaySubtitle,
} from '../game/taskPoolDisplay';
import { buildTaskDetailView, taskRowKey } from '../game/taskDetailDisplay';
import { TaskHistoryModal } from './TaskHistoryModal';
import { TaskDetailModal } from './TaskDetailModal';

export const TaskPanel: React.FC = () => {
  const {
    gamePhase,
    quarter,
    tasks,
    settled,
    focus,
    taskHistory,
    allowedEdictPlaybooks,
    warArcs,
    nationState,
    openTaskHistory,
    closeTaskHistory,
    closeTaskPanel,
    ui,
  } = useGameStore((s) => ({
    gamePhase: s.gamePhase,
    quarter: s.currentQuarter,
    tasks: s.currentTasks,
    settled: s.previousTaskResults,
    focus: s.selectedFocus,
    taskHistory: s.taskHistory,
    allowedEdictPlaybooks: s.allowedEdictPlaybooks,
    warArcs: s.warArcs,
    nationState: s.nationState,
    openTaskHistory: s.openTaskHistory,
    closeTaskHistory: s.closeTaskHistory,
    closeTaskPanel: s.closeTaskPanel,
    ui: s.ui,
  }));
  const [selectedTaskKey, setSelectedTaskKey] = useState<string | null>(null);

  useEffect(() => {
    if (!ui.isTaskPanelOpen) setSelectedTaskKey(null);
  }, [ui.isTaskPanelOpen]);

  const displayTasks = useMemo(() => sortTasksForDisplay(tasks), [tasks]);
  const crossCount = displayTasks.filter((t) => isCrossQuarterTask(t)).length;

  const selectedTask = useMemo(
    () =>
      displayTasks.find((t, idx) => taskRowKey(t, idx) === selectedTaskKey) ?? null,
    [displayTasks, selectedTaskKey],
  );

  const selectedDetail = useMemo(
    () =>
      selectedTask
        ? buildTaskDetailView(selectedTask, quarter, nationState.yearLabel)
        : null,
    [selectedTask, quarter, nationState.yearLabel],
  );

  if (!ui.isTaskPanelOpen) return null;

  return (
    <>
      <div
        className="panel-enter-up"
        style={{
          position: 'absolute',
          left: '50%',
          bottom: 12,
          transform: 'translateX(-50%)',
          minWidth: 520,
          maxWidth: 880,
          padding: '10px 14px',
          borderRadius: 10,
          background:
            'linear-gradient(90deg, rgba(10,6,4,0.95), rgba(25,15,10,0.95))',
          border: '1px solid rgba(255,215,0,0.6)',
          boxShadow: '0 0 16px rgba(0,0,0,0.7)',
          color: '#f5f5f5',
          fontSize: 13,
          zIndex: selectedTaskKey ? 120 : 130,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 4,
            gap: 8,
          }}
        >
          <div
            style={{
              fontWeight: 700,
              color: '#ffd700',
              fontSize: 14,
            }}
          >
            第{quarter || '-'}季度任务池（{tasks.length}
            {crossCount > 0 ? `，含跨季 ${crossCount}` : ''}）
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              type="button"
              onClick={() => {
                void openTaskHistory();
              }}
              style={{
                fontSize: 12,
                padding: '4px 10px',
                borderRadius: 6,
                border: '1px solid rgba(255,215,0,0.45)',
                background: 'rgba(40,30,20,0.9)',
                color: '#ffebc8',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              历史任务
            </button>
            <div
              style={{
                fontSize: 12,
                color: '#aaa',
              }}
            >
              当前阶段：{GAME_PHASE_ZH[gamePhase] || gamePhase}
            </div>
            <button
              type="button"
              onClick={closeTaskPanel}
              title="关闭任务池"
              aria-label="关闭任务池"
              style={{
                width: 26,
                height: 26,
                borderRadius: 6,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'rgba(0,0,0,0.35)',
                color: '#ffebc1',
                fontSize: 16,
                lineHeight: 1,
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              ×
            </button>
          </div>
        </div>
        <div
          style={{
            color: '#e0d8c0',
            lineHeight: 1.5,
            maxHeight: displayTasks.length > 4 ? 140 : undefined,
            overflowY: displayTasks.length > 4 ? 'auto' : undefined,
          }}
        >
          {tasks.length === 0 ? '尚无任务，请先点击“开始游戏”。' : null}
          {displayTasks.map((t, idx) => {
            const subtitle = taskDisplaySubtitle(t);
            const isCross = isCrossQuarterTask(t);
            const rowKey = taskRowKey(t, idx);
            const active = selectedTaskKey === rowKey;
            return (
              <button
                key={rowKey}
                type="button"
                className={`task-panel-item${active ? ' is-active' : ''}`}
                onClick={() => setSelectedTaskKey(rowKey)}
                style={{
                  marginBottom: 4,
                  paddingLeft: isCross ? 6 : 8,
                  borderLeft: isCross ? '2px solid rgba(255,215,0,0.55)' : undefined,
                }}
              >
                <span style={{ color: isCross ? '#ffe08a' : undefined }}>
                  {isCross ? '◆ ' : '- '}
                  {String(t.title || t.template_id || '未命名任务')}
                </span>
                {subtitle ? (
                  <span style={{ marginLeft: 6, fontSize: 11, color: '#a8c8ff' }}>{subtitle}</span>
                ) : null}
              </button>
            );
          })}
          {warArcs.length > 0 ? (
            <div
              style={{
                marginTop: 8,
                marginBottom: 6,
                padding: '8px 10px',
                borderRadius: 8,
                background: 'rgba(20,40,80,0.45)',
                border: '1px solid rgba(100,160,255,0.35)',
              }}
            >
              <div style={{ color: '#8fc0ff', fontWeight: 700, marginBottom: 6, fontSize: 12 }}>
                战役态势
              </div>
              {warArcs.map((arc) => (
                <div key={arc.arc_id} style={{ marginBottom: 6, fontSize: 11 }}>
                  <div style={{ color: '#e8dcc0' }}>
                    {arc.label_zh} · {arc.phase_label_zh || arc.phase_id}
                    {typeof arc.phase_quarter === 'number'
                      ? `（第 ${arc.phase_quarter + 1} 季）`
                      : ''}
                    {typeof arc.total_edict_contributions === 'number'
                      ? ` · 诏书 ${arc.total_edict_contributions}`
                      : ''}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 3, flexWrap: 'wrap' }}>
                    {Object.entries(arc.pressure || {}).map(([k, v]) => (
                      <span key={k} style={{ color: '#9ecfff' }}>
                        {k === 'supply_line'
                          ? '补给线'
                          : k === 'command_cohesion'
                            ? '军心'
                            : k === 'frontier_compliance'
                              ? '边地'
                              : k}
                        : {Math.round(Number(v))}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {allowedEdictPlaybooks.length > 0 ? (
            <div style={{ marginTop: 6, fontSize: 11, color: '#9ecfff' }}>
              本季可用诏令：
              {allowedEdictPlaybooks
                .map((p) => `${p.domain}/${p.task_key}`)
                .join('、')}
            </div>
          ) : null}
          <div style={{ marginTop: 6, color: '#bfb8a0' }}>
            上季结算：{settled.length} 项；重心：{focus.join(' / ') || '未选择'}
          </div>
        </div>
        <TaskHistoryModal
          open={ui.isTaskHistoryOpen}
          loading={ui.taskHistoryLoading}
          rows={taskHistory}
          onClose={closeTaskHistory}
        />
      </div>

      <TaskDetailModal
        open={Boolean(selectedTaskKey && selectedDetail)}
        detail={selectedDetail}
        onClose={() => setSelectedTaskKey(null)}
      />
    </>
  );
};
