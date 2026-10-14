'use client';

import React from 'react';
import {
  getScenario,
  isSalvageScenario,
  listScenarios,
  type ScenarioId,
} from '../game/scenarios';
import { AtlasSlideIn } from './portal/globe/AtlasSlideIn';

interface ScenarioHomePanelProps {
  selectedId: ScenarioId | null;
  loading: boolean;
  error?: string;
  onSelect: (id: ScenarioId) => void;
  onStart: () => void;
  onContinue?: () => void;
  canContinue?: boolean;
  onBack?: () => void;
  onClearError?: () => void;
  /** salvage 剧本：隐藏 Continue/New，改显示进入独立菜单 */
  salvageMenuMode?: boolean;
  onEnterSalvageMenu?: () => void;
  /** @deprecated 使用 salvageMenuMode */
  mingMenuMode?: boolean;
  /** @deprecated 使用 onEnterSalvageMenu */
  onEnterMingMenu?: () => void;
}

export const ScenarioHomePanel: React.FC<ScenarioHomePanelProps> = ({
  selectedId,
  loading,
  error,
  onSelect,
  onStart,
  onContinue,
  canContinue = false,
  onBack,
  onClearError,
  salvageMenuMode = false,
  onEnterSalvageMenu,
  mingMenuMode = false,
  onEnterMingMenu,
}) => {
  const scenarios = listScenarios();
  const selectedScenario = selectedId ? getScenario(selectedId) : undefined;
  const enterSalvageMenu = onEnterSalvageMenu ?? onEnterMingMenu;
  const useSalvageMenu = salvageMenuMode || mingMenuMode;
  const isSalvageSelected = !!selectedId && isSalvageScenario(selectedId);

  return (
    <div
      className="scenario-home"
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 250,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
        padding: 24,
        background: 'rgba(5, 4, 6, 0.72)',
        backdropFilter: 'blur(4px)',
        pointerEvents: 'auto',
        overflow: 'hidden',
      }}
    >
      {onBack ? (
        <AtlasSlideIn animKey="scenario-back" delayMs={0} className="scenario-home__back-wrap">
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
            ← 返回课程首页
          </button>
        </AtlasSlideIn>
      ) : null}

      <AtlasSlideIn animKey="scenario-header" delayMs={40}>
        <div style={{ textAlign: 'center', maxWidth: 560 }}>
          <div
            style={{
              fontSize: 12,
              letterSpacing: '0.35em',
              color: 'rgba(212, 175, 55, 0.85)',
              marginBottom: 8,
            }}
          >
            选择历史剧本
          </div>
          <h1
            style={{
              margin: 0,
              fontSize: 28,
              fontWeight: 800,
              color: '#fff3d6',
            }}
          >
            财税史情景模拟
          </h1>
          <p style={{ margin: '10px 0 0', fontSize: 14, color: '#a8a29e', lineHeight: 1.6 }}>
            选定场景后开始游戏。当前可选「熙宁变法」「万历改革」，均为月度 Salvage 推演。
          </p>
        </div>
      </AtlasSlideIn>

      {error ? (
        <div
          style={{
            width: '100%',
            maxWidth: 640,
            padding: '10px 14px',
            borderRadius: 10,
            border: '1px solid rgba(248,113,113,0.55)',
            background: 'rgba(80,20,20,0.85)',
            color: '#fecaca',
            fontSize: 13,
            lineHeight: 1.5,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
          }}
        >
          <span>{error}</span>
          {onClearError ? (
            <button
              type="button"
              onClick={onClearError}
              style={{
                border: 'none',
                background: 'transparent',
                color: '#fca5a5',
                cursor: 'pointer',
                fontSize: 12,
                flexShrink: 0,
              }}
            >
              关闭
            </button>
          ) : null}
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 16,
          width: '100%',
          maxWidth: 640,
        }}
      >
        {scenarios.map((scenario, index) => {
          const selected = selectedId === scenario.id;
          return (
            <AtlasSlideIn
              key={scenario.id}
              animKey={`scenario-card-${scenario.id}`}
              delayMs={120 + index * 90}
            >
              <button
                type="button"
                onClick={() => onSelect(scenario.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '18px 20px',
                  borderRadius: 14,
                  border: selected
                    ? '2px solid rgba(255, 215, 0, 0.9)'
                    : '1px solid rgba(255, 215, 0, 0.35)',
                  background: selected
                    ? 'linear-gradient(145deg, rgba(60,45,20,0.95), rgba(25,18,10,0.98))'
                    : 'linear-gradient(145deg, rgba(30,22,14,0.9), rgba(12,10,8,0.95))',
                  color: '#f5f5f5',
                  cursor: 'pointer',
                  boxShadow: selected ? '0 0 24px rgba(255, 200, 80, 0.25)' : 'none',
                  transition: 'border 0.15s ease, box-shadow 0.15s ease',
                }}
              >
                <div style={{ fontSize: 11, color: 'rgba(212,175,55,0.8)', marginBottom: 6 }}>
                  {scenario.nationState.dynasty} · {scenario.nationState.reignTitle}
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#ffe7a3', marginBottom: 8 }}>
                  {scenario.labelZh}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    lineHeight: 1.55,
                    color: '#c4c4c4',
                    whiteSpace: 'pre-line',
                  }}
                >
                  {scenario.descriptionZh}
                </div>
              </button>
            </AtlasSlideIn>
          );
        })}
      </div>

      <AtlasSlideIn animKey={`scenario-start-${selectedId ?? 'none'}`} delayMs={320}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          {useSalvageMenu && isSalvageSelected && enterSalvageMenu ? (
            <button
              type="button"
              disabled={loading || !selectedId}
              onClick={enterSalvageMenu}
              style={{
                border: '1px solid rgba(255,215,0,0.7)',
                borderRadius: 10,
                padding: '12px 32px',
                color: '#111',
                fontWeight: 700,
                fontSize: 15,
                background: 'linear-gradient(90deg, #ffd700, #f5d280)',
                cursor: loading || !selectedId ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {`进入${selectedScenario?.labelZh ?? '剧本'}菜单`}
            </button>
          ) : (
            <>
              {isSalvageSelected && canContinue && onContinue ? (
                <button
                  type="button"
                  disabled={loading}
                  onClick={onContinue}
                  style={{
                    border: '1px solid rgba(255,215,0,0.55)',
                    borderRadius: 10,
                    padding: '12px 28px',
                    color: '#ffe7a3',
                    fontWeight: 700,
                    fontSize: 15,
                    background: 'rgba(0,0,0,0.45)',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? '载入中…' : '继续上局'}
                </button>
              ) : null}
              <button
                type="button"
                disabled={loading || !selectedId}
                onClick={onStart}
                style={{
                  border: '1px solid rgba(255,215,0,0.7)',
                  borderRadius: 10,
                  padding: '12px 32px',
                  color: '#111',
                  fontWeight: 700,
                  fontSize: 15,
                  background: selectedId
                    ? 'linear-gradient(90deg, #ffd700, #f5d280)'
                    : 'rgba(80,80,80,0.5)',
                  cursor: loading || !selectedId ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading
                  ? '开局中…'
                  : isSalvageSelected
                    ? canContinue
                      ? '开始新游戏'
                      : selectedScenario?.salvageMenuSubtitle
                        ? `开始${selectedScenario.salvageMenuSubtitle}`
                        : '开始月度模拟'
                    : selectedId
                      ? '开始游戏'
                      : '请先选择剧本'}
              </button>
            </>
          )}
        </div>
      </AtlasSlideIn>
    </div>
  );
};
