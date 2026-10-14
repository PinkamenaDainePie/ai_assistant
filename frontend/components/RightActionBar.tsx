import React from 'react';
import { useGameStore } from '../game/store';

export const RightActionBar: React.FC = () => {
  const {
    gamePhase,
    currentQuarter,
    decreePublished,
    seasonStartSkillPending,
    loading,
    loadingKind,
    openAIDialog,
    handleOpenDecree,
    handleOpenSkillAllocation,
    handleNextQuarter,
  } = useGameStore((s) => ({
    gamePhase: s.gamePhase,
    currentQuarter: s.currentQuarter,
    decreePublished: s.decreePublished,
    seasonStartSkillPending: s.seasonStartSkillPending,
    loading: s.loading,
    loadingKind: s.loadingKind,
    openAIDialog: s.openAIDialog,
    handleOpenDecree: s.handleOpenDecree,
    handleOpenSkillAllocation: s.handleOpenSkillAllocation,
    handleNextQuarter: s.handleNextQuarter,
  }));

  const primaryLabel =
    gamePhase === 'QUARTER_MAIN'
      ? '诏书'
      : gamePhase === 'QUARTER_SETTLEMENT'
        ? '下季'
        : null;

  const handlePrimary = async () => {
    if (gamePhase === 'QUARTER_MAIN') {
      handleOpenDecree();
      return;
    }
    if (gamePhase === 'QUARTER_SETTLEMENT') {
      await handleNextQuarter();
    }
  };

  const canOpenSkillAllocation =
    gamePhase === 'QUARTER_MAIN' &&
    currentQuarter >= 2 &&
    !decreePublished &&
    seasonStartSkillPending;

  const nextQuarterLoading = loading && loadingKind === 'next_quarter';

  return (
    <div
      style={{
        width: 56,
        height: '100%',
        boxSizing: 'border-box',
        background:
          'linear-gradient(180deg, #151017 0, #0a080b 60%, #050507 100%)',
        borderLeft: '1px solid rgba(255,215,0,0.2)',
        paddingTop: 16,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <button
        onClick={openAIDialog}
        style={{
          width: 40,
          height: 40,
          borderRadius: 999,
          border: '1px solid rgba(255,215,0,0.9)',
          background: 'radial-gradient(circle at 30% 20%, #ffd700, #c41e3a)',
          color: '#1b1010',
          fontSize: 13,
          cursor: 'pointer',
        }}
        title="人物 AI 问答"
      >
        问策
      </button>
      {primaryLabel && (
        <button
          onClick={() => {
            void handlePrimary();
          }}
          disabled={loading}
          style={{
            width: 40,
            height: 40,
            borderRadius: 999,
            border: nextQuarterLoading
              ? '1px solid rgba(255,215,0,0.75)'
              : '1px solid rgba(255,215,0,0.4)',
            background: nextQuarterLoading
              ? 'radial-gradient(circle at 30% 20%, #5a4020, #2a1810)'
              : 'radial-gradient(circle at 30% 20%, #343034, #151017)',
            color: '#f5f5f5',
            fontSize: nextQuarterLoading ? 10 : 12,
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading && !nextQuarterLoading ? 0.6 : 1,
          }}
          title={nextQuarterLoading ? '正在进入下季…' : '当前阶段主操作'}
        >
          {nextQuarterLoading ? '…' : primaryLabel}
        </button>
      )}
      {canOpenSkillAllocation && (
        <button
          onClick={handleOpenSkillAllocation}
          disabled={loading}
          style={{
            width: 40,
            height: 40,
            borderRadius: 999,
            border: '1px solid rgba(120,180,255,0.6)',
            background: 'radial-gradient(circle at 30% 20%, #6aa8ff, #24385d)',
            color: '#f0f4ff',
            fontSize: 11,
            cursor: 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
          title="打开技能加点"
        >
          技能
        </button>
      )}
    </div>
  );
};

