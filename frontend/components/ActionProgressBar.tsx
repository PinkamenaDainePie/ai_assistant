'use client';

import React from 'react';
import { createPortal } from 'react-dom';
import {
  type LoadingKind,
  useSimulatedProgress,
} from '../game/actionProgress';

type ActionProgressBarProps = {
  active: boolean;
  kind?: LoadingKind;
  /** 浅色背景（诏书面板内） */
  variant?: 'light' | 'dark';
  className?: string;
};

export const ActionProgressBar: React.FC<ActionProgressBarProps> = ({
  active,
  kind = 'general',
  variant = 'dark',
  className,
}) => {
  const { progress, label } = useSimulatedProgress(active, kind);
  const light = variant === 'light';

  if (!active && progress === 0) return null;

  return (
    <div
      className={className}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(progress)}
      aria-label={label}
      style={{
        width: '100%',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 12,
          marginBottom: 8,
          fontSize: variant === 'light' ? 14 : 13,
          color: light ? '#5c4030' : '#e8dcc0',
        }}
      >
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span
          style={{
            fontSize: 12,
            color: light ? '#8a7060' : '#b8a888',
            fontVariantNumeric: 'tabular-nums',
            flexShrink: 0,
          }}
        >
          {Math.round(progress)}%
        </span>
      </div>
      <div
        className="action-progress-track"
        data-variant={variant}
        style={{
          height: variant === 'light' ? 8 : 6,
          borderRadius: 999,
          overflow: 'hidden',
          background: light
            ? 'rgba(90,55,20,0.12)'
            : 'rgba(255,215,0,0.1)',
          border: light
            ? '1px solid rgba(90,55,20,0.18)'
            : '1px solid rgba(255,215,0,0.15)',
        }}
      >
        <div
          className="action-progress-fill"
          style={{
            height: '100%',
            width: `${progress}%`,
            borderRadius: 999,
            transition: 'width 280ms ease-out',
            background: light
              ? 'linear-gradient(90deg, #8b6914, #c41e3a 55%, #ffd700)'
              : 'linear-gradient(90deg, #8b6914, #c41e3a 50%, #ffd700)',
            boxShadow: light
              ? '0 0 8px rgba(196,30,58,0.25)'
              : '0 0 10px rgba(255,215,0,0.35)',
          }}
        />
      </div>
    </div>
  );
};

type ActionProgressOverlayProps = {
  active: boolean;
  kind?: LoadingKind;
  title?: string;
  variant?: 'light' | 'dark';
};

/** 全屏或面板内遮罩 + 进度条 */
export const ActionProgressOverlay: React.FC<ActionProgressOverlayProps> = ({
  active,
  kind = 'general',
  title,
  variant = 'dark',
}) => {
  const light = variant === 'light';

  if (!active) return null;

  return (
    <div
      className="action-progress-overlay"
      data-variant={variant}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 5,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: light
          ? 'rgba(248, 240, 220, 0.82)'
          : 'rgba(8, 6, 10, 0.78)',
        backdropFilter: 'blur(4px)',
        borderRadius: light ? 8 : 0,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 420,
          padding: light ? '28px 24px' : '24px 20px',
          borderRadius: 12,
          border: light
            ? '1px solid rgba(90,55,20,0.25)'
            : '1px solid rgba(255,215,0,0.28)',
          background: light
            ? 'rgba(255, 252, 245, 0.95)'
            : 'rgba(18, 14, 10, 0.92)',
          boxShadow: light
            ? '0 8px 32px rgba(80,50,20,0.12)'
            : '0 12px 40px rgba(0,0,0,0.45)',
        }}
      >
        <div
          style={{
            textAlign: 'center',
            marginBottom: 20,
            color: light ? '#3d2818' : '#ffd700',
            fontWeight: 700,
            fontSize: light ? 20 : 18,
            letterSpacing: '0.12em',
          }}
        >
          {title || (kind === 'decree' ? '诏书颁行' : '朝政处置')}
        </div>
        <ActionProgressBar active={active} kind={kind} variant={variant} />
        <div
          style={{
            marginTop: 14,
            textAlign: 'center',
            fontSize: 12,
            color: light ? '#9a8878' : '#a89888',
            lineHeight: 1.5,
          }}
        >
          {kind === 'decree'
            ? '三省六部与朝臣正在落实诏令，请稍候'
            : '正在汇总本季朝政…'}
        </div>
      </div>
    </div>
  );
};

/** 经典季度场景点击「开始游戏」时的全屏进度遮罩 */
export const StartGameProgressOverlay: React.FC<{ active: boolean }> = ({ active }) => {
  if (!active || typeof document === 'undefined') return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="开局加载"
      aria-busy="true"
      className="start-game-progress-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 19999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'rgba(4, 3, 6, 0.82)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        style={{
          width: 'min(480px, 92vw)',
          padding: '32px 28px',
          borderRadius: 14,
          border: '1px solid rgba(255,215,0,0.35)',
          background: 'rgba(14, 11, 16, 0.96)',
          boxShadow: '0 16px 48px rgba(0,0,0,0.55)',
        }}
      >
        <div
          style={{
            textAlign: 'center',
            marginBottom: 22,
            color: '#ffd700',
            fontWeight: 700,
            fontSize: 22,
            letterSpacing: '0.2em',
          }}
        >
          开局准备
        </div>
        <ActionProgressBar active={active} kind="start_game" variant="dark" />
        <div
          style={{
            marginTop: 16,
            textAlign: 'center',
            fontSize: 13,
            color: '#a89888',
            lineHeight: 1.6,
          }}
        >
          正在载入熙宁朝局与首季要务，请稍候
        </div>
      </div>
    </div>,
    document.body,
  );
};

/** 点击「下季」时的全屏进度遮罩 */
export const NextQuarterProgressOverlay: React.FC<{ active: boolean }> = ({ active }) => {
  if (!active || typeof document === 'undefined') return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="进入下季"
      aria-busy="true"
      className="next-quarter-progress-overlay"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 19999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'rgba(4, 3, 6, 0.82)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        style={{
          width: 'min(480px, 92vw)',
          padding: '32px 28px',
          borderRadius: 14,
          border: '1px solid rgba(255,215,0,0.35)',
          background: 'rgba(14, 11, 16, 0.96)',
          boxShadow: '0 16px 48px rgba(0,0,0,0.55)',
        }}
      >
        <div
          style={{
            textAlign: 'center',
            marginBottom: 22,
            color: '#ffd700',
            fontWeight: 700,
            fontSize: 22,
            letterSpacing: '0.2em',
          }}
        >
          进入下季
        </div>
        <ActionProgressBar active={active} kind="next_quarter" variant="dark" />
        <div
          style={{
            marginTop: 16,
            textAlign: 'center',
            fontSize: 13,
            color: '#a89888',
            lineHeight: 1.6,
          }}
        >
          时令推移，刷新要务与朝政纪要，请稍候
        </div>
      </div>
    </div>,
    document.body,
  );
};
