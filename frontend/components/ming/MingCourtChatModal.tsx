'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Character } from '../../game/types';
import type { MingCourtChatMessage } from '../../game/ming/mingTurnPhase';
import { MingFullscreenModal } from './MingFullscreenModal';
import { mingCourtChatStream, mingFetchCourtChatHistory, mingCourtChatSummary } from '../../lib/mingApi';
import { useCourtChatDeltaQueue } from '../../game/ming/mingCourtChatThrottle';
import { useMingStore } from '../../game/ming/mingStore';
import { mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

function canAttendCourtChat(name: string, office?: string, status?: string): boolean {
  const o = (office || '').trim();
  if (status !== 'active' || !o) return false;
  return !/(已故|罢居|罢闲|赋闲|致仕|养病|丁忧|归籍|在野)/.test(o);
}

type Props = {
  characters: Character[];
  onClose: () => void;
  onAfterChat?: () => void;
  onChooseDecision?: (option: string) => Promise<void>;
};

export const MingCourtChatModal: React.FC<Props> = ({
  characters,
  onClose,
  onAfterChat,
  onChooseDecision,
}) => {
  const roster = useMemo(
    () =>
      characters.filter(
        (c) => c.id !== 'emperor' && canAttendCourtChat(c.name, c.title, 'active'),
      ),
    [characters],
  );
  const [selected, setSelected] = useState<string[]>([]);
  const [history, setHistory] = useState<MingCourtChatMessage[]>([]);
  const [live, setLive] = useState<MingCourtChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [error, setError] = useState('');
  const courtChatStreamSpeed = useMingStore((s) => s.courtChatStreamSpeed);
  const setCourtChatStreamSpeed = useMingStore((s) => s.setCourtChatStreamSpeed);
  const { queueDelta, flush } = useCourtChatDeltaQueue(courtChatStreamSpeed);
  const abortRef = useRef<AbortController | null>(null);

  const appendLiveDelta = useCallback((speaker: string, delta: string) => {
    setLive((m) => {
      const idx = m.findIndex(
        (x, i) => i === m.length - 1 && x.role === 'minister' && x.speaker === speaker,
      );
      if (idx < 0) {
        return [...m, { role: 'minister', speaker, content: delta, displayContent: delta }];
      }
      const copy = [...m];
      const row = copy[idx];
      copy[idx] = {
        ...row,
        content: row.content + delta,
        displayContent: (row.displayContent || '') + delta,
      };
      return copy;
    });
  }, []);

  const summarize = async () => {
    const visibleMessages = [...history, ...live]
      .map((message) => ({
        role: message.role,
        speaker: message.speaker,
        content: (message.displayContent ?? message.content).trim(),
      }))
      .filter((message) => message.content);
    if (!visibleMessages.length || summaryBusy) {
      if (!visibleMessages.length) setError('当前没有可归纳的朝议内容。');
      return;
    }
    try {
      setSummaryBusy(true);
      setError('');
      const summaryMsg = await mingCourtChatSummary(visibleMessages);
      const row: MingCourtChatMessage = {
        role: (summaryMsg.role as MingCourtChatMessage['role']) || 'conclusion',
        speaker: summaryMsg.speaker,
        content: summaryMsg.content,
        displayContent: summaryMsg.displayContent,
        options: summaryMsg.options,
      };
      setLive((m) => [...m, row]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSummaryBusy(false);
    }
  };

  const chooseDecision = async (option: string) => {
    if (!option.trim() || !onChooseDecision || decisionBusy) return;
    try {
      setDecisionBusy(true);
      setError('');
      await onChooseDecision(option.trim());
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDecisionBusy(false);
    }
  };

  useEffect(() => {
    if (roster.length) setSelected(roster.slice(0, 4).map((c) => c.name));
  }, [roster]);

  useEffect(() => {
    let alive = true;
    void mingFetchCourtChatHistory()
      .then((data) => {
        if (alive && data.history?.length) setHistory(data.history);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  const toggleMinister = (name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  };

  const send = async () => {
    const message = input.trim();
    if (!message || busy) return;
    const speakers = selected.filter((n) => roster.some((c) => c.name === n));
    if (!speakers.length) {
      setError('请至少选择一位可参与朝议的大臣。');
      return;
    }
    const abort = new AbortController();
    abortRef.current = abort;
    setBusy(true);
    setError('');
    setInput('');
    const emperorMsg: MingCourtChatMessage = {
      role: 'emperor',
      speaker: '皇帝',
      content: message,
      displayContent: message,
    };
    setLive((m) => [...m, emperorMsg]);
    try {
      const data = await mingCourtChatStream(
        message,
        speakers,
        (event, payload) => {
          if (event === 'speaker') {
            const speaker = String(payload.speaker || '');
            setLive((m) => {
              const last = m[m.length - 1];
              if (last?.role === 'minister' && last.speaker === speaker && !last.content) return m;
              return [...m, { role: 'minister', speaker, content: '', displayContent: '' }];
            });
          } else if (event === 'delta') {
            const speaker = String(payload.speaker || '');
            const delta = String(payload.content || '');
            queueDelta(speaker, delta, appendLiveDelta);
          } else if (event === 'conclusion') {
            setLive((m) => [
              ...m,
              {
                role: 'conclusion',
                speaker: String(payload.speaker || '朝议结论'),
                content: String(payload.content || ''),
                displayContent: String(payload.content || ''),
                options: Array.isArray(payload.options)
                  ? (payload.options as string[])
                  : undefined,
              },
            ]);
          } else if (event === 'reply') {
            setLive((m) => [
              ...m,
              {
                role: (payload.role as MingCourtChatMessage['role']) || 'minister',
                speaker: String(payload.speaker || ''),
                content: String(payload.content || ''),
                displayContent: String(payload.content || ''),
              },
            ]);
          }
        },
        undefined,
        abort.signal,
      );
      flush(appendLiveDelta);
      if (data.history?.length) setHistory(data.history);
      setLive([]);
      onAfterChat?.();
    } catch (e) {
      if (!abort.signal.aborted) {
        setError(e instanceof Error ? e.message : String(e));
        setInput(message);
      }
    } finally {
      if (abortRef.current === abort) {
        abortRef.current = null;
        setBusy(false);
      }
    }
  };

  const displayMessages = [...history, ...live];

  return (
    <MingFullscreenModal
      wide
      title="廷议"
      subtitle="召集群臣共议国策（流式朝会）"
      onClose={onClose}
    >
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: '#aaa' }}>流式语速</span>
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={courtChatStreamSpeed}
          onChange={(e) => setCourtChatStreamSpeed(Number(e.target.value))}
          disabled={busy}
          style={{ flex: 1, minWidth: 120, maxWidth: 200 }}
        />
        <span style={{ fontSize: 11, color: '#888' }}>
          {courtChatStreamSpeed === 1
            ? '慢'
            : courtChatStreamSpeed === 5
              ? '最快'
              : courtChatStreamSpeed === 3
                ? '默认'
                : `${courtChatStreamSpeed}`}
        </span>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>出席大臣（多选）</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {roster.map((c) => {
            const on = selected.includes(c.name);
            return (
              <button
                key={c.id}
                type="button"
                style={{
                  ...mingOutlineBtn,
                  fontSize: 11,
                  borderColor: on ? 'rgba(255,215,0,0.8)' : 'rgba(255,215,0,0.25)',
                  background: on ? 'rgba(255,215,0,0.12)' : 'rgba(0,0,0,0.3)',
                }}
                onClick={() => toggleMinister(c.name)}
              >
                {c.name}
              </button>
            );
          })}
        </div>
      </div>

      <div
        style={{
          maxHeight: 320,
          overflowY: 'auto',
          marginBottom: 12,
          padding: 10,
          borderRadius: 8,
          border: '1px solid rgba(255,215,0,0.15)',
          background: 'rgba(0,0,0,0.25)',
        }}
      >
        {displayMessages.length === 0 ? (
          <p style={{ color: '#888', fontSize: 13 }}>尚无朝议记录，请输入议题开始廷议。</p>
        ) : (
          displayMessages.map((m, i) => (
            <div key={i} style={{ marginBottom: 10, fontSize: 13, lineHeight: 1.6 }}>
              <b style={{ color: m.role === 'emperor' ? '#ffd700' : m.role === 'conclusion' ? '#ffb74d' : '#ffe7a3' }}>
                {m.speaker}
              </b>
              <div style={{ color: '#ccc', marginTop: 2 }}>{m.displayContent || m.content}</div>
              {m.options?.length ? (
                <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {m.options.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      style={mingOutlineBtn}
                      disabled={decisionBusy || !onChooseDecision}
                      onClick={() => void chooseDecision(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>

      {error && <p style={{ color: '#e57373', fontSize: 12, marginBottom: 8 }}>{error}</p>}

      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="朕意：众卿以为边饷、漕运、吏治，当以何为先？"
        rows={3}
        disabled={busy}
        style={{
          width: '100%',
          padding: 8,
          background: 'rgba(0,0,0,0.35)',
          border: '1px solid rgba(255,215,0,0.2)',
          color: '#f5f5f5',
          borderRadius: 6,
          fontSize: 13,
          marginBottom: 8,
        }}
      />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" style={mingPrimaryBtn} disabled={busy || !input.trim()} onClick={() => void send()}>
          {busy ? '廷议进行中…' : '发旨廷议'}
        </button>
        <button
          type="button"
          style={mingOutlineBtn}
          disabled={summaryBusy || displayMessages.length === 0}
          onClick={() => void summarize()}
        >
          {summaryBusy ? '归纳中…' : '归纳廷议'}
        </button>
        {busy && (
          <button
            type="button"
            style={mingOutlineBtn}
            onClick={() => abortRef.current?.abort()}
          >
            停止
          </button>
        )}
      </div>
    </MingFullscreenModal>
  );
};
