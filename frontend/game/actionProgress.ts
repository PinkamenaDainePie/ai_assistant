import { useEffect, useRef, useState } from 'react';

export type LoadingKind =
  | 'none'
  | 'decree'
  | 'focus'
  | 'next_quarter'
  | 'start_game'
  | 'general';

export type ProgressStage = {
  /** 进度上限（0–100） */
  until: number;
  label: string;
};

export const DECREE_PROGRESS_STAGES: ProgressStage[] = [
  { until: 12, label: '起草诏书，送中书省…' },
  { until: 28, label: '三省同审，拟准施行…' },
  { until: 48, label: '下发各省，督促奉行…' },
  { until: 72, label: '朝臣议对，斟酌利弊…' },
  { until: 88, label: '汇总本季成效，核对簿籍…' },
  { until: 95, label: '即将完成…' },
];

export const FOCUS_PROGRESS_STAGES: ProgressStage[] = [
  { until: 35, label: '记录季度重心…' },
  { until: 70, label: '整理本季结算…' },
  { until: 92, label: '生成季末报告…' },
];

export const NEXT_QUARTER_PROGRESS_STAGES: ProgressStage[] = [
  { until: 18, label: '推移时令，进入下季…' },
  { until: 38, label: '刷新要务与朝局…' },
  { until: 58, label: '结算上季成效…' },
  { until: 78, label: '国史编纂官撰写朝政纪要…' },
  { until: 92, label: '即将开季…' },
];

/** 经典季度引擎（熙宁变法等）点击「开始游戏」 */
export const START_GAME_PROGRESS_STAGES: ProgressStage[] = [
  { until: 15, label: '加载朝局与册籍…' },
  { until: 35, label: '查阅户部国计与各路舆图…' },
  { until: 55, label: '列置本季要务与朝臣…' },
  { until: 75, label: '熙宁元年，静候开季…' },
  { until: 92, label: '即将临朝…' },
];

export function stagesForKind(kind: LoadingKind): ProgressStage[] {
  if (kind === 'decree') return DECREE_PROGRESS_STAGES;
  if (kind === 'focus') return FOCUS_PROGRESS_STAGES;
  if (kind === 'next_quarter') return NEXT_QUARTER_PROGRESS_STAGES;
  if (kind === 'start_game') return START_GAME_PROGRESS_STAGES;
  return [{ until: 90, label: '处理中…' }];
}

function labelForProgress(stages: ProgressStage[], progress: number): string {
  for (const stage of stages) {
    if (progress <= stage.until) return stage.label;
  }
  return stages[stages.length - 1]?.label || '处理中…';
}

/** 模拟进度：进行中缓升至 cap，结束时跳到 100% */
export function useSimulatedProgress(active: boolean, kind: LoadingKind) {
  const [progress, setProgress] = useState(0);
  const activeRef = useRef(active);
  const wasActiveRef = useRef(false);

  useEffect(() => {
    activeRef.current = active;
  }, [active]);

  useEffect(() => {
    if (!active) {
      if (wasActiveRef.current) {
        setProgress(100);
        const t = window.setTimeout(() => setProgress(0), 400);
        wasActiveRef.current = false;
        return () => window.clearTimeout(t);
      }
      setProgress(0);
      return;
    }

    wasActiveRef.current = true;
    setProgress(4);
    const stages = stagesForKind(kind);
    const cap = stages[stages.length - 1]?.until ?? 92;

    const tick = window.setInterval(() => {
      setProgress((prev) => {
        if (!activeRef.current) return prev;
        if (prev >= cap) return prev;
        const step = prev < 40 ? 2.2 : prev < 70 ? 1.1 : 0.45;
        return Math.min(cap, prev + step);
      });
    }, 280);

    return () => window.clearInterval(tick);
  }, [active, kind]);

  const stages = stagesForKind(kind);
  const label = labelForProgress(stages, progress);

  return { progress, label };
}
