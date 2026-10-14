import React, { useEffect, useMemo, useState } from 'react';
import { useGameStore } from '../game/store';
import {
  getConsultableCharacters,
  resolveApiCharacterId,
} from '../game/consultCharacters';
import type { Character } from '../game/types';
import { CharacterPortrait } from './CharacterPortrait';
import { CharacterNameTooltip } from './CharacterNameTooltip';
import { postChat } from '../lib/renwuApi';

const panelShell: React.CSSProperties = {
  position: 'fixed',
  right: 72,
  top: 72,
  width: 320,
  maxHeight: '70vh',
  borderRadius: 10,
  background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 60%, #050508 100%)',
  color: '#f5f5f5',
  display: 'flex',
  flexDirection: 'column',
  padding: 12,
  border: '1px solid rgba(255,215,0,0.6)',
  boxShadow: '0 0 18px rgba(0,0,0,0.8)',
  zIndex: 1100,
};

function CharacterAvatar({
  character,
  size = 40,
  fontSize = 13,
}: {
  character: Character;
  size?: number;
  fontSize?: number;
}) {
  return <CharacterPortrait character={character} variant="game" size={size} fontSize={fontSize} />;
}

const CONSULT_PAGE_SIZE = 6;

function ConsultCharacterPicker({
  characters,
  onSelect,
  onClose,
}: {
  characters: Character[];
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(characters.length / CONSULT_PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageStart = safePage * CONSULT_PAGE_SIZE;
  const pageCharacters = characters.slice(pageStart, pageStart + CONSULT_PAGE_SIZE);

  useEffect(() => {
    setPage(0);
  }, [characters.length]);

  useEffect(() => {
    if (page > totalPages - 1) {
      setPage(Math.max(0, totalPages - 1));
    }
  }, [page, totalPages]);

  return (
    <div style={panelShell}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <div style={{ fontSize: 15, fontWeight: 700, color: '#ffebc1' }}>择臣问策</div>
        <button
          type="button"
          onClick={onClose}
          title="关闭"
          aria-label="关闭问策"
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
          }}
        >
          ×
        </button>
      </div>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 12, lineHeight: 1.5 }}>
        请选择一位大臣向其请教（共 {characters.length} 位）。头像资源可后续替换为立绘。
      </div>
      {characters.length === 0 ? (
        <div style={{ fontSize: 13, color: '#666', padding: '12px 0' }}>
          当前剧本暂无可问策人物。
        </div>
      ) : (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 12,
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              paddingBottom: 4,
            }}
          >
            {pageCharacters.map((c) => (
              <CharacterNameTooltip key={c.id} name={c.name} brief={c.brief} title={c.title}>
              <button
                type="button"
                onClick={() => onSelect(c.id)}
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
                <CharacterAvatar character={c} size={56} fontSize={15} />
                <div style={{ fontSize: 13, fontWeight: 600, color: '#ffebc1' }}>{c.name}</div>
                <div style={{ fontSize: 10, color: '#aaa', textAlign: 'center', lineHeight: 1.3 }}>
                  {c.title}
                </div>
              </button>
              </CharacterNameTooltip>
            ))}
          </div>
          {totalPages > 1 ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                marginTop: 10,
                paddingTop: 10,
                borderTop: '1px solid rgba(255,215,0,0.15)',
                flexShrink: 0,
              }}
            >
              <button
                type="button"
                disabled={safePage <= 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                style={{
                  border: '1px solid rgba(255,215,0,0.35)',
                  borderRadius: 6,
                  background: safePage <= 0 ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.35)',
                  color: safePage <= 0 ? '#555' : '#ffebc1',
                  fontSize: 12,
                  padding: '4px 10px',
                  cursor: safePage <= 0 ? 'default' : 'pointer',
                }}
              >
                上一页
              </button>
              <span style={{ fontSize: 12, color: '#aaa', minWidth: 56, textAlign: 'center' }}>
                {safePage + 1} / {totalPages}
              </span>
              <button
                type="button"
                disabled={safePage >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                style={{
                  border: '1px solid rgba(255,215,0,0.35)',
                  borderRadius: 6,
                  background:
                    safePage >= totalPages - 1 ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.35)',
                  color: safePage >= totalPages - 1 ? '#555' : '#ffebc1',
                  fontSize: 12,
                  padding: '4px 10px',
                  cursor: safePage >= totalPages - 1 ? 'default' : 'pointer',
                }}
              >
                下一页
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function ConsultCharacterChat({
  character,
  onBack,
  onClose,
}: {
  character: Character;
  onBack: () => void;
  onClose: () => void;
}) {
  const [question, setQuestion] = useState('');
  const [lastQ, setLastQ] = useState<string | null>(null);
  const [lastA, setLastA] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const characterApiId = resolveApiCharacterId(character);

  useEffect(() => {
    setQuestion('');
    setLastQ(null);
    setLastA(null);
    setLoading(false);
  }, [character.id]);

  const handleAsk = async () => {
    if (!question.trim() || !characterApiId) return;
    setLoading(true);
    setLastQ(question);
    const q = question;
    setQuestion('');
    try {
      const data = await postChat({
        character_id: characterApiId,
        message: q,
      });
      setLastA(data.reply || '（无回复）');
    } catch (err) {
      const detail =
        err instanceof Error && err.message ? `\n${err.message}` : '';
      const isUnreachable =
        err instanceof Error &&
        (/无法连接后端|Failed to fetch|NetworkError|网络请求失败/i.test(err.message) ||
          (/fetch/i.test(err.message) && /failed/i.test(err.message)));
      const isHttpApi =
        err instanceof Error && /API \/chat failed: \d{3}/.test(err.message);
      const prefix = isUnreachable
        ? '（未能连上后端）请确认 API 已启动、端口与 NEXT_PUBLIC_API_BASE_URL / 代理一致后重试。'
        : isHttpApi
          ? '（后端已响应但处理失败）请查看下方具体原因；常见为 Ollama/大模型超时、模型名错误或通义 Key 无效。'
          : '（请求失败）请检查 API 服务与网络后重试。';
      setLastA(`${prefix}${detail}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={panelShell}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: 8,
          gap: 6,
        }}
      >
        <button
          type="button"
          onClick={onBack}
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
        <CharacterAvatar character={character} size={40} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, color: '#ffebc1' }}>
            {character.name} · {character.title}
          </div>
          <div style={{ fontSize: 12, color: '#aaa', marginTop: 2 }}>
            立场：{character.ideologyTags.join(' / ')}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          title="关闭"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#f5f5f5',
            cursor: 'pointer',
            fontSize: 16,
          }}
        >
          ×
        </button>
      </div>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
        你可以就当前情势向其请教，例如「若暂缓新法，诸路财用可支撑几时？」。
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 120,
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.1)',
          padding: 8,
          background: 'rgba(0,0,0,0.35)',
          fontSize: 13,
          overflowY: 'auto',
        }}
      >
        {lastQ ? (
          <>
            <div style={{ marginBottom: 6, color: '#aaa' }}>你：</div>
            <div style={{ marginBottom: 10, color: '#f5f5f5' }}>{lastQ}</div>
            <div style={{ marginBottom: 6, color: '#aaa' }}>{character.name}：</div>
            <div style={{ color: '#ffebc1' }}>
              {loading ? '正在斟酌对策……' : lastA}
            </div>
          </>
        ) : (
          <div style={{ color: '#666' }}>尚无对话记录。</div>
        )}
      </div>

      <div style={{ marginTop: 8 }}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入你要请教的问题……"
          style={{
            width: '100%',
            height: 60,
            borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.2)',
            background: 'rgba(0,0,0,0.6)',
            color: '#f5f5f5',
            fontSize: 13,
            padding: 6,
            resize: 'none',
            boxSizing: 'border-box',
          }}
        />
        <button
          type="button"
          onClick={() => {
            void handleAsk();
          }}
          disabled={loading || !characterApiId}
          style={{
            marginTop: 6,
            width: '100%',
            padding: '6px 10px',
            borderRadius: 6,
            border: 'none',
            background: 'linear-gradient(90deg, #b8860b, #c41e3a)',
            color: '#1b1010',
            fontWeight: 600,
            cursor: loading || !characterApiId ? 'not-allowed' : 'pointer',
            fontSize: 13,
            opacity: loading || !characterApiId ? 0.6 : 1,
          }}
        >
          {loading ? '请稍候…' : '请其进言'}
        </button>
      </div>
    </div>
  );
}

export const AIDialogPanel: React.FC = () => {
  const { characters, ui, closeAIDialog, selectAIDialogCharacter, backAIDialogPicker } =
    useGameStore((s) => ({
      characters: s.characters,
      ui: s.ui,
      closeAIDialog: s.closeAIDialog,
      selectAIDialogCharacter: s.selectAIDialogCharacter,
      backAIDialogPicker: s.backAIDialogPicker,
    }));

  const consultable = useMemo(() => getConsultableCharacters(characters), [characters]);
  const focusChar = useMemo(() => {
    if (!ui.aiDialogCharacterId) return null;
    return characters.find((c) => c.id === ui.aiDialogCharacterId) ?? null;
  }, [characters, ui.aiDialogCharacterId]);

  if (!ui.isAIDialogOpen) return null;

  if (!focusChar) {
    return (
      <ConsultCharacterPicker
        characters={consultable}
        onSelect={selectAIDialogCharacter}
        onClose={closeAIDialog}
      />
    );
  }

  return (
    <ConsultCharacterChat
      character={focusChar}
      onBack={backAIDialogPicker}
      onClose={closeAIDialog}
    />
  );
};
