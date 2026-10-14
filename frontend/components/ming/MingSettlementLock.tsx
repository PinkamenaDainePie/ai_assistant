'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

type Props = {
  active: boolean;
  stage: string;
  thinking: string;
  narrative: string;
  onCancel?: () => void;
};

export const MingSettlementLock: React.FC<Props> = ({ active, stage, thinking, narrative, onCancel }) => {
  const thinkRef = useRef<HTMLDivElement>(null);
  const narrRef = useRef<HTMLDivElement>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsedSec(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active]);

  useEffect(() => {
    if (!active) return;
    const block = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener('keydown', block, true);
    return () => window.removeEventListener('keydown', block, true);
  }, [active]);

  useEffect(() => {
    if (thinkRef.current) thinkRef.current.scrollTop = thinkRef.current.scrollHeight;
  }, [thinking]);

  useEffect(() => {
    if (narrRef.current) narrRef.current.scrollTop = narrRef.current.scrollHeight;
  }, [narrative]);

  if (!active || typeof document === 'undefined') return null;

  const stageHint =
    stage === '数值推演结算'
      ? '档房核账中，钱粮、地方、军务落账，请稍候。'
      : stage
        ? `当前：${stage}`
        : '朝廷推演钱粮、地方、军务，请勿操作。';

  const waitingHint =
    !thinking && !narrative
      ? elapsedSec < 15
        ? '正在连接推演引擎…'
        : '若长时间无「邸报房推敲」或「月末奏章」输出，请检查 LLM API 配置，或取消后重试。'
      : '';

  return createPortal(
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label="月末结算"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 19000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'rgba(4, 3, 6, 0.88)',
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        className="ming-scroll"
        style={{
          width: 'min(560px, 94vw)',
          maxHeight: '85vh',
          padding: '28px 24px',
          borderRadius: 14,
          border: '1px solid rgba(255,215,0,0.35)',
          background: 'rgba(14, 11, 16, 0.97)',
          boxShadow: '0 16px 48px rgba(0,0,0,0.55)',
          overflow: 'auto',
        }}
      >
        <h2
          style={{
            margin: '0 0 8px',
            textAlign: 'center',
            color: '#ffd700',
            fontSize: 22,
            letterSpacing: '0.12em',
          }}
        >
          月末结算中
        </h2>
        <p style={{ textAlign: 'center', color: '#a89888', fontSize: 13, lineHeight: 1.6, marginBottom: 8 }}>
          {stageHint}
        </p>
        {waitingHint ? (
          <p style={{ textAlign: 'center', color: '#887766', fontSize: 12, lineHeight: 1.5, marginBottom: 12 }}>
            {waitingHint}
            {elapsedSec > 0 ? `（已等待 ${elapsedSec}s）` : ''}
          </p>
        ) : (
          <p style={{ textAlign: 'center', color: '#666', fontSize: 11, marginBottom: 12 }}>
            已等待 {elapsedSec}s
          </p>
        )}

        {thinking && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: '#d4af37', marginBottom: 6 }}>邸报房推敲</div>
            <div
              ref={thinkRef}
              className="ming-scroll"
              style={{
                maxHeight: 120,
                overflowY: 'auto',
                padding: 10,
                borderRadius: 8,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(255,215,0,0.12)',
                fontSize: 12,
                lineHeight: 1.6,
                color: '#999',
                whiteSpace: 'pre-wrap',
              }}
            >
              {thinking}
            </div>
          </div>
        )}

        {narrative && (
          <div>
            <div style={{ fontSize: 11, color: '#d4af37', marginBottom: 6 }}>月末奏章（流式）</div>
            <div
              ref={narrRef}
              className="ming-scroll"
              style={{
                maxHeight: 220,
                overflowY: 'auto',
                padding: 10,
                borderRadius: 8,
                background: 'rgba(0,0,0,0.35)',
                border: '1px solid rgba(255,215,0,0.12)',
                fontSize: 13,
                lineHeight: 1.7,
                color: '#ddd',
                whiteSpace: 'pre-wrap',
              }}
            >
              {narrative}
            </div>
          </div>
        )}

        {onCancel ? (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <button
              type="button"
              onClick={onCancel}
              style={{
                padding: '8px 18px',
                borderRadius: 8,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'rgba(0,0,0,0.35)',
                color: '#ccc',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              取消结算
            </button>
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
};
