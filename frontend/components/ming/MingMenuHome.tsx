'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { getScenario, resolveSalvageScenarioId, type ScenarioId } from '../../game/scenarios';
import { mingFetchMenuStatus } from '../../lib/mingApi';
import type { MingSaveEntry } from '../../game/ming/mingTurnPhase';
import { useMingStore } from '../../game/ming/mingStore';
import { MingGameMenuModal } from './MingGameMenuModal';

type Props = {
  scenarioId: ScenarioId;
  onBack: () => void;
};

export const MingMenuHome: React.FC<Props> = ({ scenarioId, onBack }) => {
  const scenario = getScenario(scenarioId);
  const loading = useMingStore((s) => s.loading);
  const error = useMingStore((s) => s.error);
  const clearError = useMingStore((s) => s.clearError);
  const handleStartGame = useMingStore((s) => s.handleStartGame);
  const handleContinueGame = useMingStore((s) => s.handleContinueGame);
  const canContinueSalvageScenario = useMingStore((s) => s.canContinueSalvageScenario);
  const boundScenarioId = useMingStore((s) => s.boundScenarioId);
  const loadSave = useMingStore((s) => s.loadSave);
  const fetchMenuBootstrap = useMingStore((s) => s.fetchMenuBootstrap);

  const [hasApiKey, setHasApiKey] = useState(false);
  const [hasMainDb, setHasMainDb] = useState(false);
  const [saves, setSaves] = useState<MingSaveEntry[]>([]);
  const [scenarioName, setScenarioName] = useState('');
  const [showSaves, setShowSaves] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [bootBusy, setBootBusy] = useState(true);

  const refreshStatus = useCallback(async () => {
    setBootBusy(true);
    try {
      const salvageId = resolveSalvageScenarioId(scenarioId);
      const status = await mingFetchMenuStatus(salvageId);
      setHasApiKey(status.has_api_key);
      setHasMainDb(status.has_main_db);
      setSaves(status.saves ?? []);
      setScenarioName(status.active_scenario?.name ?? scenario?.labelZh ?? '剧本');
      await fetchMenuBootstrap();
    } catch {
      /* ignore */
    } finally {
      setBootBusy(false);
    }
  }, [fetchMenuBootstrap, scenario?.labelZh, scenarioId]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const onLoadSave = async (name: string) => {
    setShowSaves(false);
    try {
      await loadSave(name);
    } catch {
      /* store sets error */
    }
  };

  const canContinue = canContinueSalvageScenario(scenarioId);

  const btnStyle = (primary = false): React.CSSProperties => ({
    width: '100%',
    padding: '12px 20px',
    borderRadius: 10,
    border: primary ? '1px solid rgba(255,215,0,0.85)' : '1px solid rgba(255,215,0,0.4)',
    background: primary
      ? 'linear-gradient(90deg, #ffd700, #f5d280)'
      : 'rgba(0,0,0,0.45)',
    color: primary ? '#111' : '#ffe7a3',
    fontWeight: 700,
    fontSize: 15,
    cursor: loading || bootBusy ? 'not-allowed' : 'pointer',
    opacity: loading || bootBusy ? 0.55 : 1,
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 260,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
        padding: 24,
        background: 'rgba(5, 4, 6, 0.92)',
        backdropFilter: 'blur(6px)',
        pointerEvents: 'auto',
      }}
    >
      <button
        type="button"
        onClick={onBack}
        style={{
          position: 'absolute',
          top: 20,
          left: 24,
          border: '1px solid rgba(255,215,0,0.35)',
          borderRadius: 8,
          padding: '8px 14px',
          background: 'rgba(0,0,0,0.45)',
          color: '#e8dcc0',
          fontSize: 13,
          cursor: 'pointer',
        }}
      >
        ← 返回选剧本
      </button>

      <div style={{ textAlign: 'center', maxWidth: 480 }}>
        <div style={{ fontSize: 12, letterSpacing: '0.35em', color: 'rgba(212,175,55,0.85)', marginBottom: 8 }}>
          {scenario?.salvageMenuSubtitle ?? '月度推演'}
        </div>
        <h1 style={{ margin: 0, fontSize: 32, fontWeight: 800, color: '#fff3d6' }}>
          {scenario?.labelZh ?? '历史剧本'}
        </h1>
        <p style={{ margin: '10px 0 0', fontSize: 14, color: '#a8a29e' }}>
          {scenarioName}
          {scenario?.nationState.reignTitle ? ` · ${scenario.nationState.reignTitle}` : ''}
        </p>
      </div>

      {!hasApiKey && (
        <div
          style={{
            maxWidth: 400,
            padding: '10px 14px',
            borderRadius: 8,
            border: '1px solid rgba(251,191,36,0.5)',
            background: 'rgba(60,40,10,0.6)',
            color: '#fde68a',
            fontSize: 13,
          }}
        >
          尚未配置 API。请先在「游戏设置 → LLM」中填写接口。
        </div>
      )}

      {error && (
        <div
          style={{
            maxWidth: 400,
            width: '100%',
            padding: '10px 14px',
            borderRadius: 8,
            border: '1px solid rgba(248,113,113,0.55)',
            background: 'rgba(80,20,20,0.85)',
            color: '#fecaca',
            fontSize: 13,
            display: 'flex',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <span>{error}</span>
          <button type="button" onClick={clearError} style={{ border: 'none', background: 'transparent', color: '#fca5a5', cursor: 'pointer' }}>
            关闭
          </button>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', maxWidth: 320 }}>
        <button
          type="button"
          style={btnStyle(true)}
          disabled={!hasApiKey || loading || bootBusy}
          onClick={() => void handleStartGame()}
        >
          {loading ? '开局中…' : '开始新游戏'}
        </button>
        <button
          type="button"
          style={btnStyle()}
          disabled={!hasApiKey || !canContinue || loading || bootBusy}
          title={
            !hasMainDb
              ? '无上次进度'
              : !canContinue && boundScenarioId
                ? '主进度属于其他剧本，请切换剧本或开始新游戏'
                : ''
          }
          onClick={() => void handleContinueGame()}
        >
          {loading ? '载入中…' : '继续上局'}
        </button>
        <button
          type="button"
          style={btnStyle()}
          disabled={!hasApiKey || loading || bootBusy || !saves.length}
          onClick={() => setShowSaves(true)}
        >
          加载存档{saves.length ? ` (${saves.length})` : ''}
        </button>
        <button
          type="button"
          style={btnStyle()}
          disabled={loading || bootBusy}
          onClick={() => setShowSettings(true)}
        >
          游戏设置
        </button>
      </div>

      {bootBusy && <p style={{ color: '#888', fontSize: 12 }}>读取菜单状态…</p>}

      {showSaves && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 300,
            background: 'rgba(0,0,0,0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
          onClick={() => setShowSaves(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 420,
              maxHeight: '70vh',
              overflowY: 'auto',
              padding: 20,
              borderRadius: 12,
              border: '1px solid rgba(255,215,0,0.35)',
              background: 'rgba(12,10,8,0.98)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ margin: '0 0 12px', color: '#ffd700', fontSize: 18 }}>加载存档</h2>
            {!saves.length ? (
              <p style={{ color: '#888' }}>暂无存档。</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {saves.map((s) => (
                  <li key={s.name} style={{ marginBottom: 8 }}>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => void onLoadSave(s.name)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid rgba(255,215,0,0.25)',
                        background: 'rgba(0,0,0,0.35)',
                        color: '#eee',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>{s.label || s.name}</div>
                      <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                        {s.label && s.label !== s.name ? `${s.name} · ` : ''}
                        {new Date(s.mtime * 1000).toLocaleString('zh-CN')}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button
              type="button"
              onClick={() => setShowSaves(false)}
              style={{ marginTop: 12, padding: '8px 16px', cursor: 'pointer' }}
            >
              关闭
            </button>
          </div>
        </div>
      )}

      {showSettings && (
        <MingGameMenuModal
          onClose={() => {
            setShowSettings(false);
            void refreshStatus();
          }}
          onAfterLoad={() => setShowSettings(false)}
          onExitToMenu={() => setShowSettings(false)}
        />
      )}
    </div>
  );
};
