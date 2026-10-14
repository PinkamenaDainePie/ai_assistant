import React from 'react';
import { useGameStore } from '../game/store';

export const CourtScenePanel: React.FC = () => {
  const { events, currentEventIndex, handleSelectEventOption, loading } = useGameStore((s) => ({
    events: s.events,
    currentEventIndex: s.currentEventIndex,
    handleSelectEventOption: s.handleSelectEventOption,
    loading: s.loading,
  }));
  const currentEvent = events[currentEventIndex];

  if (!currentEvent) {
    return (
      <div style={{ padding: 24, color: '#ccc' }}>
        暂无当前事件。
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        color: '#f5f5f5',
        background:
          'radial-gradient(circle at top, rgba(255,215,0,0.05) 0, #111 60%)',
      }}
    >
      <div style={{ marginBottom: 12 }}>
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: '#ffd700',
            letterSpacing: 2,
          }}
        >
          {currentEvent.title}
        </div>
        <div
          style={{
            marginTop: 8,
            color: '#d0c6aa',
            fontSize: 14,
            lineHeight: 1.6,
          }}
        >
          {currentEvent.description || '请在备选方案中选择一项处理。'}
        </div>
      </div>

      <div
        style={{
          padding: 12,
          borderRadius: 8,
          border: '1px solid rgba(255,215,0,0.3)',
          background:
            'linear-gradient(135deg, rgba(20,12,10,0.9), rgba(10,8,12,0.95))',
        }}
      >
        <div
          style={{
            marginBottom: 8,
            color: '#ffebc1',
            fontWeight: 600,
            fontSize: 14,
          }}
        >
          朕意如何？请选择你的批示：
        </div>
        <div
          style={{
            display: 'flex',
            gap: 12,
          }}
        >
          {currentEvent.choices.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                void handleSelectEventOption(opt.id);
              }}
              disabled={loading}
              style={{
                flex: 1,
                textAlign: 'left',
                borderRadius: 8,
                border: '1px solid rgba(255,215,0,0.3)',
                padding: 10,
                background: 'rgba(0,0,0,0.4)',
                color: '#f5f5f5',
                cursor: 'pointer',
                fontSize: 13,
              }}
              title={opt.effectsText.join(' / ')}
            >
              {opt.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

