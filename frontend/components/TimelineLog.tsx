import React from 'react';
import { useGameStore } from '../game/store';

export const TimelineLog: React.FC = () => {
  const logs = useGameStore((s) => s.logs);

  return (
    <div
      style={{
        height: 90,
        borderTop: '1px solid rgba(255,215,0,0.2)',
        background:
          'linear-gradient(90deg, #120e0c 0, #0a0a0c 100%)',
        padding: '8px 16px',
        overflowX: 'auto',
        whiteSpace: 'nowrap',
        fontSize: 12,
        color: '#f5f5f5',
      }}
    >
      {logs.map((log) => (
        <div
          key={log.id}
          style={{
            display: 'inline-block',
            minWidth: 180,
            padding: '6px 8px',
            marginRight: 8,
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.3)',
            background: 'rgba(0,0,0,0.4)',
            verticalAlign: 'top',
          }}
        >
          <div
            style={{
              color: '#ffebc1',
              marginBottom: 2,
              fontWeight: 600,
            }}
          >
            第{log.turn}回 · {log.timeLabel}
          </div>
          <div
            style={{
              marginBottom: 2,
              color: '#ddd',
            }}
          >
            {log.summary}
          </div>
          <div style={{ color: '#aaa' }}>
            {log.metricChanges.map((m, idx) => (
              <span key={idx} style={{ marginRight: 4 }}>
                {m.metric}:{m.delta > 0 ? `+${m.delta}` : m.delta}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

