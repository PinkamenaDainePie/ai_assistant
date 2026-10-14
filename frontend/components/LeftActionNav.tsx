import React from 'react';
import { useGameStore } from '../game/store';

interface NavItem {
  key: string;
  label: string;
}

const navItems: NavItem[] = [
  { key: 'court', label: '朝会' },
  { key: 'memorials', label: '奏折' },
  { key: 'intel', label: '情报' },
  { key: 'tasks', label: '任务' },
];

export const LeftActionNav: React.FC = () => {
  const openMemorialDrawer = useGameStore((s) => s.openMemorialDrawer);
  const toggleTaskPanel = useGameStore((s) => s.toggleTaskPanel);
  const isTaskPanelOpen = useGameStore((s) => s.ui.isTaskPanelOpen);

  const handleClick = (key: string) => {
    if (key === 'memorials') {
      openMemorialDrawer();
    }
    if (key === 'tasks') {
      toggleTaskPanel();
    }
  };

  return (
    <div
      style={{
        width: 56,
        height: '100%',
        background:
          'linear-gradient(180deg, #151017 0, #0a080b 60%, #050507 100%)',
        borderRight: '1px solid rgba(255,215,0,0.2)',
        paddingTop: 16,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
      }}
    >
      {navItems.map((item) => (
        <button
          key={item.key}
          onClick={() => handleClick(item.key)}
          style={{
            width: 40,
            height: 40,
            borderRadius: 999,
            border:
              item.key === 'tasks' && isTaskPanelOpen
                ? '1px solid rgba(255,215,0,0.85)'
                : '1px solid rgba(255,215,0,0.35)',
            background:
              item.key === 'tasks' && isTaskPanelOpen
                ? 'radial-gradient(circle at 30% 20%, rgba(255,215,0,0.35), rgba(10,8,12,0.9))'
                : 'radial-gradient(circle at 30% 20%, #343034, #151017)',
            color: '#f5f5f5',
            cursor: 'pointer',
            fontSize: 12,
            letterSpacing: '0.08em',
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
};

