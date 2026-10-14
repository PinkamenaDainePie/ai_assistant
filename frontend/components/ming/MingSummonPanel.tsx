'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { Character } from '../../game/types';
import type {
  MingChatMessage,
  MingChatSuggestion,
  MingDirective,
  MingSecretOrder,
  MingTurnPhase,
} from '../../game/ming/mingTurnPhase';
import type { SalvageMinister } from '../../game/ming/salvageStateTypes';
import { SalvageMinisterPortrait } from '../../game/ming/SalvageMinisterPortrait';
import { mingCloseBtn, mingOutlineBtn, mingPanelShell, mingPrimaryBtn } from '../../game/ming/mingUiStyles';
import { useDraggablePanel } from '../../hooks/useDraggablePanel';
import { CharacterPortrait } from '../CharacterPortrait';
import { CharacterNameTooltip } from '../CharacterNameTooltip';

const PAGE_SIZE = 6;

/** 北宋召见卡：新党 / 旧党 / 中立 / 武臣 */
function songPartyLabel(c: Character, meta?: SalvageMinister | null): string {
  const fromMeta = (meta?.faction || '').trim();
  if (fromMeta.includes('新法') || fromMeta === '新党') return '新党';
  if (fromMeta.includes('旧')) return '旧党';
  if (fromMeta.includes('中立')) return '中立';
  if (fromMeta.includes('武')) return '武臣';
  const tag = (c.ideologyTags || []).find((t) =>
    ['新党', '旧党', '中立派', '武臣'].includes(t),
  );
  if (tag === '中立派') return '中立';
  if (tag) return tag;
  if (c.faction === 'reformer') return '新党';
  if (c.faction === 'conservative') return '旧党';
  return '中立';
}

function partyLabelColor(label: string): string {
  if (label === '新党') return '#e07070';
  if (label === '旧党') return '#6a9fd8';
  if (label === '武臣') return '#c9a227';
  return '#9a9a9a';
}

const summonShellStyle = (isChatView: boolean, pos: { left: number; top: number } | null): React.CSSProperties => ({
  ...mingPanelShell,
  width: isChatView ? 'min(560px, calc(100vw - 80px))' : 'min(480px, calc(100vw - 80px))',
  maxWidth: 'none',
  ...(isChatView
    ? { height: 'min(78vh, 720px)', maxHeight: 'min(78vh, 720px)' }
    : { maxHeight: 'calc(75vh - 40px)' }),
  ...(pos ? { left: pos.left, top: pos.top, right: 'auto' as const } : {}),
});

type Props = {
  open: boolean;
  phase: MingTurnPhase;
  characters: Character[];
  activeMinisterId: string | null;
  activeMinisterMeta: SalvageMinister | null;
  chatHistory: MingChatMessage[];
  chatSuggestions: MingChatSuggestion[];
  streamingReply: string;
  pendingUserMessage: string;
  chatNotice: string;
  chatBusy: boolean;
  ministerSecretOrders: MingSecretOrder[];
  pendingDirectives: MingDirective[];
  ministers?: SalvageMinister[];
  onClose: () => void;
  onSelectMinister: (id: string) => void;
  onClearMinister: () => void;
  onSendChat: (message: string) => void;
  onUndoChat: () => void;
  onConfirmDirective: (id: number) => void;
  onRejectDirective: (id: number) => void;
  onToggleFavorite: () => void;
  onArchiveMinister: () => void;
  onUploadPortrait: (file: File) => void;
  onCreateSecretOrder: (title: string, content: string) => void;
  onOpenEdict?: () => void;
};

export const MingSummonPanel: React.FC<Props> = ({
  open,
  phase,
  characters,
  activeMinisterId,
  activeMinisterMeta,
  chatHistory,
  chatSuggestions,
  streamingReply,
  pendingUserMessage,
  chatNotice,
  chatBusy,
  ministerSecretOrders,
  pendingDirectives,
  ministers,
  onClose,
  onSelectMinister,
  onClearMinister,
  onSendChat,
  onUndoChat,
  onConfirmDirective,
  onRejectDirective,
  onToggleFavorite,
  onArchiveMinister,
  onUploadPortrait,
  onCreateSecretOrder,
  onOpenEdict,
}) => {
  const [page, setPage] = useState(0);
  const [chatInput, setChatInput] = useState('');
  const [secretOpen, setSecretOpen] = useState(false);
  const [secretTitle, setSecretTitle] = useState('');
  const [secretContent, setSecretContent] = useState('');
  const logRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const metaByName = useMemo(() => {
    const map = new Map<string, SalvageMinister>();
    for (const m of ministers || []) map.set(m.name, m);
    return map;
  }, [ministers]);

  const activeChar = useMemo(
    () => characters.find((c) => c.id === activeMinisterId) ?? null,
    [characters, activeMinisterId],
  );

  const canChat = phase === 'summoning' || phase === 'reviewing';
  const isChatView = !!(activeChar && canChat);
  const dragKey = `${open}-${isChatView ? activeMinisterId : 'roster'}`;
  const { panelRef, dragHandleProps, pos } = useDraggablePanel(dragKey);
  const totalPages = Math.max(1, Math.ceil(characters.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageChars = characters.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const canUndo = chatHistory.some((m) => m.role === 'minister');

  const displayMessages: MingChatMessage[] = [...chatHistory];
  if (pendingUserMessage) {
    displayMessages.push({ role: 'user', content: pendingUserMessage, pending: true });
  }
  if (streamingReply) {
    displayMessages.push({ role: 'minister', content: streamingReply, pending: true });
  }

  useEffect(() => {
    setPage(0);
  }, [characters.length]);

  useEffect(() => {
    if (!open) setChatInput('');
  }, [open, activeMinisterId]);

  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [displayMessages.length, chatNotice, chatBusy, streamingReply]);

  const send = (text?: string) => {
    const msg = (text ?? chatInput).trim();
    if (!msg || chatBusy) return;
    onSendChat(msg);
    if (text === undefined) setChatInput('');
  };

  const applySuggestion = (s: MingChatSuggestion) => {
    if (s.prefix) {
      setChatInput(s.text);
    } else {
      send(s.text);
    }
  };

  if (!open) return null;

  if (isChatView && activeChar) {
    return (
      <div ref={panelRef as React.RefObject<HTMLDivElement>} style={summonShellStyle(true, pos)} className="panel-enter-up">
        <div
          {...dragHandleProps}
          style={{
            ...dragHandleProps.style,
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
            marginBottom: 8,
          }}
        >
          <button
            type="button"
            onClick={onClearMinister}
            title="返回人物列表"
            style={{
              border: 'none',
              background: 'transparent',
              color: '#aaa',
              cursor: 'pointer',
              fontSize: 16,
              padding: '0 4px',
            }}
          >
            ←
          </button>
          {activeMinisterMeta?.portrait_id?.startsWith('custom:') ? (
            <SalvageMinisterPortrait
              minister={activeMinisterMeta}
              width={64}
              height={64}
              fontSize={16}
              style={{ borderRadius: '50%', border: '1px solid rgba(255,215,0,0.5)' }}
            />
          ) : (
            <CharacterPortrait character={activeChar} variant="game" size={64} fontSize={16} />
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, color: '#ffebc1' }}>
              {activeChar.name} · {activeMinisterMeta?.office || activeChar.title}
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 11,
                  color: partyLabelColor(songPartyLabel(activeChar, activeMinisterMeta)),
                  fontWeight: 600,
                }}
              >
                {songPartyLabel(activeChar, activeMinisterMeta)}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#888', marginTop: 2, lineHeight: 1.4 }}>
              {activeMinisterMeta?.summary || activeChar.brief}
            </div>
          </div>
          <button
            type="button"
            title={activeMinisterMeta?.favorite ? '取消收藏' : '收藏'}
            onClick={() => onToggleFavorite()}
            disabled={chatBusy}
            style={{ border: 'none', background: 'transparent', color: '#ffd700', cursor: 'pointer', fontSize: 18 }}
          >
            {activeMinisterMeta?.favorite ? '★' : '☆'}
          </button>
          <button type="button" onClick={onClose} title="关闭" style={mingCloseBtn}>
            ×
          </button>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
          <button type="button" style={{ ...mingOutlineBtn, fontSize: 11, padding: '4px 8px' }} disabled={chatBusy} onClick={() => fileRef.current?.click()}>
            换立绘
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUploadPortrait(f);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            style={{ ...mingOutlineBtn, fontSize: 11, padding: '4px 8px' }}
            disabled={chatBusy}
            onClick={() => setSecretOpen((v) => !v)}
          >
            下密令
          </button>
          {onOpenEdict ? (
            <button
              type="button"
              style={{ ...mingOutlineBtn, fontSize: 11, padding: '4px 8px', color: '#ffd700' }}
              disabled={chatBusy}
              onClick={onOpenEdict}
            >
              诏书草案
            </button>
          ) : null}
          {activeMinisterMeta?.origin === 'runtime' && activeMinisterMeta.status !== 'active' && (
            <button type="button" style={{ ...mingOutlineBtn, fontSize: 11, padding: '4px 8px' }} disabled={chatBusy} onClick={() => onArchiveMinister()}>
              归档
            </button>
          )}
        </div>

        {secretOpen && (
          <div style={{ marginBottom: 8, padding: 8, borderRadius: 8, border: '1px solid rgba(255,215,0,0.2)', background: 'rgba(0,0,0,0.3)' }}>
            <input
              value={secretTitle}
              onChange={(e) => setSecretTitle(e.target.value)}
              placeholder="密令标题（20字内）"
              maxLength={20}
              style={{ width: '100%', marginBottom: 6, padding: 6, fontSize: 12, background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.1)', color: '#eee', borderRadius: 4 }}
            />
            <textarea
              value={secretContent}
              onChange={(e) => setSecretContent(e.target.value)}
              placeholder="密令正文…"
              rows={2}
              style={{ width: '100%', marginBottom: 6, padding: 6, fontSize: 12, background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.1)', color: '#eee', borderRadius: 4 }}
            />
            <button
              type="button"
              style={{ ...mingPrimaryBtn, fontSize: 12, padding: '4px 10px' }}
              disabled={chatBusy || !secretTitle.trim() || !secretContent.trim()}
              onClick={() => {
                onCreateSecretOrder(secretTitle.trim(), secretContent.trim());
                setSecretTitle('');
                setSecretContent('');
                setSecretOpen(false);
              }}
            >
              密付
            </button>
          </div>
        )}

        {ministerSecretOrders.length > 0 && (
          <div style={{ marginBottom: 8, fontSize: 11, color: '#aaa' }}>
            <div style={{ color: '#d4af37', marginBottom: 4 }}>进行中密令</div>
            {ministerSecretOrders.map((o) => (
              <div key={o.id} style={{ marginBottom: 4, padding: 6, borderRadius: 6, background: 'rgba(0,0,0,0.25)' }}>
                <b style={{ color: '#ffe7a3' }}>{o.title}</b>
                {o.content && <div style={{ color: '#999', marginTop: 2 }}>{o.content}</div>}
              </div>
            ))}
          </div>
        )}

        <div
          ref={logRef}
          style={{
            flex: 1,
            minHeight: 160,
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)',
            padding: 8,
            background: 'rgba(0,0,0,0.35)',
            fontSize: 13,
            overflowY: 'auto',
            marginBottom: 8,
          }}
        >
          {displayMessages.length === 0 ? (
            <div style={{ color: '#666', fontSize: 12 }}>下问大臣，其答可自动转为拟旨草案。</div>
          ) : (
            displayMessages.map((m, i) => (
              <div key={i} style={{ marginBottom: 8, opacity: m.pending ? 0.85 : 1 }}>
                <div style={{ color: '#ffd700', fontSize: 11, marginBottom: 2 }}>
                  {m.role === 'user' ? '陛下' : activeChar.name}
                  {m.pending && chatBusy ? ' …' : ''}
                </div>
                <div style={{ color: '#ddd', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{m.content}</div>
              </div>
            ))
          )}
          {chatBusy && !streamingReply && !pendingUserMessage && (
            <div style={{ color: '#888', fontSize: 12 }}>{activeChar.name} 思索中…</div>
          )}
          {chatNotice && (
            <div style={{ color: '#ffb74d', fontSize: 12, marginTop: 6, padding: '6px 8px', borderRadius: 6, background: 'rgba(255,183,77,0.08)' }}>
              {chatNotice}
            </div>
          )}
        </div>

        {pendingDirectives.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            {pendingDirectives.map((d) => (
              <div
                key={d.id}
                style={{
                  marginBottom: 6,
                  padding: 8,
                  borderRadius: 6,
                  border: '1px solid rgba(255,183,77,0.35)',
                  background: 'rgba(255,183,77,0.06)',
                  fontSize: 12,
                }}
              >
                <div style={{ marginBottom: 6, lineHeight: 1.5 }}>
                  <b>#{d.id}</b> {d.text}
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="button" style={{ ...mingPrimaryBtn, flex: 1, fontSize: 11, padding: '4px 8px' }} disabled={chatBusy} onClick={() => onConfirmDirective(d.id)}>
                    准奏
                  </button>
                  <button type="button" style={{ ...mingOutlineBtn, flex: 1, fontSize: 11, padding: '4px 8px', color: '#faa' }} disabled={chatBusy} onClick={() => onRejectDirective(d.id)}>
                    驳回
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {chatSuggestions.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
            {chatSuggestions.map((s) => (
              <button
                key={`${s.label}-${s.text}`}
                type="button"
                disabled={chatBusy}
                title={s.prefix ? `填入：${s.text}` : s.text}
                onClick={() => applySuggestion(s)}
                style={{
                  ...mingOutlineBtn,
                  fontSize: 11,
                  padding: '4px 8px',
                  borderStyle: s.prefix ? 'dashed' : 'solid',
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}

        <textarea
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              send();
            }
          }}
          rows={2}
          placeholder="问军情、钱粮、地方，或命其拟旨… Enter 发送"
          disabled={chatBusy}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.35)',
            border: '1px solid rgba(255,215,0,0.2)',
            borderRadius: 6,
            color: '#f5f5f5',
            padding: 8,
            fontSize: 13,
            resize: 'vertical',
          }}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button type="button" disabled={chatBusy || !chatInput.trim()} onClick={() => send()} style={{ ...mingPrimaryBtn, flex: 1 }}>
            {chatBusy ? '候答…' : '宣问'}
          </button>
          <button type="button" disabled={chatBusy || !canUndo} onClick={onUndoChat} style={{ ...mingOutlineBtn, flex: '0 0 auto' }} title="撤回最后一轮召对">
            撤回
          </button>
        </div>
      </div>
    );
  }

  return (
    <div ref={panelRef as React.RefObject<HTMLDivElement>} style={summonShellStyle(false, pos)} className="panel-enter-up">
      <div
        {...dragHandleProps}
        style={{
          ...dragHandleProps.style,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <div style={{ fontSize: 15, fontWeight: 700, color: '#ffebc1' }}>择臣召见</div>
        <button type="button" onClick={onClose} title="关闭" style={mingCloseBtn}>
          ×
        </button>
      </div>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 12, lineHeight: 1.5 }}>
        {canChat ? `选择一位大臣召见问策（共 ${characters.length} 位）。` : '当前阶段不可召见，请等待颁诏结算。'}
      </div>

      {canChat && characters.length > 0 ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, overflowY: 'auto', paddingBottom: 4 }}>
            {pageChars.map((c) => {
              const meta = metaByName.get(c.name);
              const party = songPartyLabel(c, meta);
              return (
              <CharacterNameTooltip
                key={c.id}
                name={c.name}
                brief={meta?.summary || c.brief}
                title={`${meta?.office || c.title} · ${party}`}
              >
              <button
                type="button"
                onClick={() => onSelectMinister(c.id)}
                style={{
                  border: '1px solid rgba(255,215,0,0.25)',
                  borderRadius: 10,
                  background: 'rgba(0,0,0,0.35)',
                  padding: '10px 6px',
                  cursor: 'pointer',
                  color: '#f5f5f5',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {meta?.portrait_id?.startsWith('custom:') ? (
                  <SalvageMinisterPortrait
                    minister={meta}
                    width={64}
                    height={64}
                    fontSize={16}
                    style={{ borderRadius: '50%', border: '1px solid rgba(255,215,0,0.35)' }}
                  />
                ) : (
                  <CharacterPortrait character={c} variant="game" size={64} fontSize={16} />
                )}
                <div style={{ fontSize: 13, fontWeight: 600, color: '#ffebc1' }}>{c.name}</div>
                <div style={{ fontSize: 10, color: partyLabelColor(party), fontWeight: 600 }}>{party}</div>
                <div style={{ fontSize: 10, color: '#aaa', textAlign: 'center', lineHeight: 1.3 }}>{c.title}</div>
              </button>
              </CharacterNameTooltip>
              );
            })}
          </div>
          {totalPages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255,215,0,0.15)' }}>
              <button type="button" disabled={safePage <= 0} onClick={() => setPage((p) => Math.max(0, p - 1))} style={mingOutlineBtn}>
                上一页
              </button>
              <span style={{ fontSize: 12, color: '#aaa' }}>
                {safePage + 1} / {totalPages}
              </span>
              <button type="button" disabled={safePage >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} style={mingOutlineBtn}>
                下一页
              </button>
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 13, color: '#666', padding: '12px 0' }}>暂无可召见人物。</div>
      )}
    </div>
  );
};
