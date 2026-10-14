import React, { useMemo } from 'react';
import { useGameStore } from '../game/store';
import {
  buildQuarterChapterListItems,
  resolveQuarterChapterDetail,
} from '../game/quarterChapterDisplay';

export const MemorialReaderPanel: React.FC = () => {
  const { quarterChapters, ui, scenarioId, currentQuarter } = useGameStore((s) => ({
    quarterChapters: s.quarterChapters,
    ui: s.ui,
    scenarioId: s.scenarioId,
    currentQuarter: s.currentQuarter,
  }));

  const items = useMemo(
    () =>
      buildQuarterChapterListItems(quarterChapters, {
        scenarioId,
        currentQuarter,
      }),
    [quarterChapters, scenarioId, currentQuarter],
  );

  const activeId = ui.selectedQuarterChapterId || items[0]?.id;
  const detail = resolveQuarterChapterDetail(activeId, quarterChapters, {
    scenarioId,
    currentQuarter,
  });
  if (!detail) return null;

  return (
    <div
      style={{
        width: 260,
        margin: 12,
        padding: 10,
        borderRadius: 10,
        background:
          'linear-gradient(135deg, rgba(15,10,8,0.96), rgba(32,22,16,0.98))',
        border: '1px solid rgba(255,215,0,0.6)',
        boxShadow: '0 0 12px rgba(0,0,0,0.7)',
        color: '#f5f5f5',
        fontSize: 13,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 6,
        }}
      >
        <div
          style={{
            fontWeight: 700,
            color: '#ffebc1',
          }}
        >
          季度总结节要
        </div>
      </div>
      <div
        style={{
          marginBottom: 6,
          color: '#ffd700',
          fontWeight: 600,
        }}
      >
        {detail.title}
      </div>
      <div
        style={{
          fontSize: 12,
          color: '#c8c0a8',
          marginBottom: 4,
        }}
      >
        {detail.quarterLabel}
      </div>
      <div
        style={{
          fontSize: 12,
          color: '#ddd',
          lineHeight: 1.6,
        }}
      >
        {detail.headline || detail.body.slice(0, 160)}
      </div>
    </div>
  );
};
