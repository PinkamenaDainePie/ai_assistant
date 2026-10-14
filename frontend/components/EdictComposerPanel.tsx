'use client';

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { Noto_Serif_SC } from 'next/font/google';
import { useGameStore } from '../game/store';

/** 替换为自定义背景图：将图片放入 public/ui/edict/room-bg.jpg */
const EDICT_ROOM_BG = '/ui/edict/room-bg.jpg';

const edictFont = Noto_Serif_SC({
  weight: ['400', '600', '700'],
  subsets: ['latin'],
  display: 'swap',
});

const MAX_CHARS = 2000;

export const EdictComposerPanel: React.FC = () => {
  const {
    gamePhase,
    loading,
    error,
    handleSubmitDecree,
    cancelDecreeModal,
    clearError,
  } = useGameStore((s) => ({
    gamePhase: s.gamePhase,
    loading: s.loading,
    error: s.error,
    handleSubmitDecree: s.handleSubmitDecree,
    cancelDecreeModal: s.cancelDecreeModal,
    clearError: s.clearError,
  }));
  const [text, setText] = useState('');

  if (gamePhase !== 'DECREE_MODAL' || typeof document === 'undefined') return null;

  const handleClose = () => {
    clearError();
    cancelDecreeModal();
  };

  const handleSubmit = async () => {
    if (loading || !text.trim()) return;
    try {
      await handleSubmitDecree(text, 'other');
      setText('');
    } catch {
      /* 错误已写入 store.error */
    }
  };

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="拟诏面板"
      className={edictFont.className}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 20001,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding:
          'max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left))',
        boxSizing: 'border-box',
        backgroundColor: '#f2e6c8',
        overflow: 'hidden',
      }}
    >
      <div
        aria-hidden
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url(${EDICT_ROOM_BG})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'brightness(1.42) saturate(0.72) contrast(0.94)',
          transform: 'scale(1.02)',
        }}
      />
      <div
        aria-hidden
        style={{
          position: 'absolute',
          inset: 0,
          background: `
            linear-gradient(
              rgba(248, 240, 220, 0.45),
              rgba(242, 230, 200, 0.55)
            ),
            linear-gradient(180deg, rgba(248, 240, 220, 0.25) 0%, rgba(235, 224, 196, 0.35) 100%)
          `,
        }}
      />
      <button
        type="button"
        onClick={handleClose}
        aria-label="关闭诏书面板"
        title="关闭"
        style={{
          position: 'absolute',
          top: 'max(16px, env(safe-area-inset-top))',
          right: 'max(20px, env(safe-area-inset-right))',
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: '1px solid rgba(90,55,20,0.35)',
          background: 'rgba(255,248,235,0.82)',
          color: '#4a3525',
          fontSize: 20,
          lineHeight: 1,
          cursor: 'pointer',
          zIndex: 2,
        }}
      >
        ×
      </button>

      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          zIndex: 1,
          width: 'min(960px, 94vw)',
          maxHeight: 'min(820px, 88vh)',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 8,
          overflow: 'hidden',
          filter: 'drop-shadow(0 16px 48px rgba(0,0,0,0.55))',
          background: `
            linear-gradient(180deg, rgba(255,250,235,0.15) 0%, transparent 8%),
            repeating-linear-gradient(
              90deg,
              transparent,
              transparent 3px,
              rgba(180,150,100,0.04) 3px,
              rgba(180,150,100,0.04) 4px
            ),
            linear-gradient(180deg, #f8f0dc 0%, #f2e6c8 45%, #ebe0c4 100%)
          `,
          border: '1px solid rgba(200,170,120,0.45)',
          color: '#2a1810',
        }}
      >
        <main
          style={{
            flex: 1,
            minHeight: 0,
            padding: '24px 28px 16px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div className="edict-composer-textarea-wrap">
            <textarea
              className="edict-composer-textarea"
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
              maxLength={MAX_CHARS}
              placeholder="写下你的诏书大意，例如：着诸路转运司以青苗本钱代民间高利，仍严禁州县横敛……"
              style={{
                width: '100%',
                flex: 1,
                minHeight: 260,
                border: '1px solid rgba(120,80,40,0.35)',
                borderRadius: 4,
                background: 'rgba(255,252,245,0.85)',
                color: '#2a1810',
                fontSize: 15,
                lineHeight: 1.75,
                padding: '12px 14px 32px',
                resize: 'none',
                outline: 'none',
                boxShadow: 'inset 0 1px 4px rgba(80,50,20,0.08)',
                fontFamily: 'inherit',
              }}
            />
            <span
              style={{
                position: 'absolute',
                right: 10,
                bottom: 8,
                fontSize: 11,
                color: '#9a8878',
                pointerEvents: 'none',
              }}
            >
              {text.length}/{MAX_CHARS}
            </span>
          </div>

          {error && (
            <div
              style={{
                marginTop: 10,
                fontSize: 13,
                color: '#8b2020',
                padding: '6px 10px',
                borderRadius: 4,
                background: 'rgba(180,60,60,0.12)',
                border: '1px solid rgba(180,60,60,0.3)',
              }}
            >
              后端错误：{error}
            </div>
          )}
        </main>

        <footer
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '14px 28px 22px',
            borderTop: '1px solid rgba(120,80,40,0.22)',
            gap: 16,
          }}
        >
          <button
            type="button"
            onClick={handleClose}
            style={{
              padding: '8px 18px',
              borderRadius: 6,
              border: '1px solid rgba(90,55,20,0.45)',
              background: 'rgba(255,248,235,0.6)',
              color: '#5c4030',
              fontSize: 14,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            {loading ? '取消等待' : '收起'}
          </button>

          <button
            type="button"
            onClick={() => {
              void handleSubmit();
            }}
            disabled={loading || !text.trim()}
            style={{
              minWidth: 120,
              padding: '12px 20px',
              border: 'none',
              borderRadius: 4,
              background: loading || !text.trim() ? '#4a4a4a' : '#1a1008',
              color: loading || !text.trim() ? '#aaa' : '#f5ecd7',
              fontWeight: 700,
              fontSize: 16,
              letterSpacing: '0.25em',
              cursor: loading || !text.trim() ? 'not-allowed' : 'pointer',
              boxShadow:
                loading || !text.trim()
                  ? 'none'
                  : '0 4px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12)',
              transform: 'rotate(-1deg)',
              fontFamily: 'inherit',
            }}
          >
            {loading ? '颁行中…' : '颁布诏书'}
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
};
