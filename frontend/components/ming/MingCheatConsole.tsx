'use client';

import React, { useEffect, useRef, useState } from 'react';
import { mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Props = {
  directive: string;
  onCommit: (text: string) => void;
  onClose: () => void;
};

export const MingCheatConsole: React.FC<Props> = ({ directive, onCommit, onClose }) => {
  const [draft, setDraft] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [history]);

  const submit = () => {
    const text = draft.trim();
    if (!text) return;
    onCommit(text);
    setHistory((h) => [...h, `> ${text}`, '  已挂载强制结算项，下次颁诏随结算生效（一次性）。']);
    setDraft('');
  };

  const clearMounted = () => {
    onCommit('');
    setHistory((h) => [...h, '  已清空强制结算项。']);
  };

  return (
    <div
      role="dialog"
      aria-label="天命控制台"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 25000,
        background: 'rgba(0,0,0,0.72)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 'min(640px, 96vw)',
          maxHeight: '80vh',
          borderRadius: 8,
          border: '1px solid #3a5f3a',
          background: '#0c100c',
          color: '#b8f0b8',
          fontFamily: 'Consolas, Monaco, monospace',
          fontSize: 13,
          boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '8px 12px',
            borderBottom: '1px solid #2a4a2a',
            background: '#141a14',
          }}
        >
          <span>tianming@ming-salvage:~$ 天命控制台</span>
          <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 18 }}>×</button>
        </div>
        <div ref={bodyRef} style={{ padding: 12, maxHeight: 280, overflowY: 'auto', lineHeight: 1.6 }}>
          <div style={{ color: '#6a9a6a', marginBottom: 6 }}>
            强制结算控制台。输入的指令将在下次颁诏时作为「既成事实」穿入结算。
          </div>
          <div style={{ color: '#6a9a6a', marginBottom: 8 }}>Enter 提交 · Shift+Enter 换行 · Ctrl+~ 关闭</div>
          {directive ? (
            <div style={{ color: '#ffb74d', marginBottom: 8 }}>● 当前已挂载：{directive}</div>
          ) : (
            <div style={{ color: '#6a9a6a', marginBottom: 8 }}>○ 当前无挂载项</div>
          )}
          {history.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, padding: '8px 12px', borderTop: '1px solid #2a4a2a' }}>
          <span style={{ color: '#52c41a' }}>&gt;</span>
          <textarea
            ref={inputRef}
            value={draft}
            rows={2}
            placeholder="例：国库增至九千万两，后金军覆灭"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.nativeEvent.isComposing || e.keyCode === 229) return;
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            style={{
              flex: 1,
              background: '#0a0e0a',
              border: '1px solid #2a4a2a',
              color: '#b8f0b8',
              borderRadius: 4,
              padding: 8,
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: 8, padding: '8px 12px' }}>
          <button type="button" style={mingPrimaryBtn} onClick={submit}>挂载</button>
          <button type="button" style={mingOutlineBtn} onClick={clearMounted}>清空挂载</button>
        </div>
      </div>
    </div>
  );
};
