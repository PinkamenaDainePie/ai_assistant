'use client';

import React from 'react';
import type { MingHudDrawerKey } from '../../game/ming/salvageStateTypes';

type NavItem = {
  key: Exclude<MingHudDrawerKey, 'none'>;
  label: string;
  title: string;
};

function buildItems(isSong: boolean): NavItem[] {
  const regionLabel = isSong ? '诸路' : '省份';
  return [
    { key: 'court', label: '朝堂', title: '朝堂·召见大臣' },
    { key: 'appointment', label: '吏部', title: '官员任免' },
    { key: 'region', label: regionLabel, title: isSong ? '诸路列表' : '省份列表' },
    { key: 'army', label: '兵部', title: '军队列表' },
    { key: 'economy', label: '户部', title: '经济面板' },
    { key: 'building', label: '工部', title: '营造与工役' },
    { key: 'court', label: '礼部', title: '礼部（朝堂）' },
    // { key: 'harem', label: '后宫', title: '后宫' }, // 暂隐藏
    { key: 'goal', label: '目标', title: '长期目标' },
  ];
}

function visibleItems(isSong: boolean, showLongGoals: boolean): NavItem[] {
  const items = buildItems(isSong);
  return showLongGoals ? items : items.filter((item) => item.key !== 'goal');
}

type Props = {
  active: MingHudDrawerKey;
  onToggle: (key: Exclude<MingHudDrawerKey, 'none'>) => void;
  /** 嵌入右侧 EdgeDockRail，不使用 fixed 定位 */
  embedded?: boolean;
  /** 万历专属「长期目标」海报；熙宁 v2 等场景可关闭 */
  showLongGoals?: boolean;
  /** 北宋场景：右侧「诸路」替代「省份」 */
  isSong?: boolean;
};

const circleBtn = (isActive: boolean, is礼部: boolean): React.CSSProperties => ({
  width: 40,
  height: 40,
  flexShrink: 0,
  padding: 0,
  borderRadius: '50%',
  border: isActive
    ? '1px solid rgba(255,215,0,0.85)'
    : '1px solid rgba(255,215,0,0.3)',
  background: isActive
    ? 'radial-gradient(circle at 50% 35%, rgba(255,215,0,0.28), rgba(20,12,8,0.95))'
    : 'radial-gradient(circle at 50% 35%, rgba(60,40,25,0.85), rgba(12,8,10,0.98))',
  color: isActive ? '#ffd700' : '#ddd',
  cursor: 'pointer',
  writingMode: 'vertical-rl',
  fontSize: is礼部 ? 11 : 12,
  fontWeight: is礼部 ? 500 : 700,
  letterSpacing: '0.12em',
  opacity: is礼部 ? 0.88 : 1,
  boxShadow: isActive
    ? '0 0 10px rgba(255,215,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08)'
    : 'inset 0 1px 0 rgba(255,255,255,0.05)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

export const MingRightHudNav: React.FC<Props> = ({
  active,
  onToggle,
  embedded,
  showLongGoals = true,
  isSong = false,
}) => (
  <nav
    aria-label="部院导航"
    style={
      embedded
        ? {
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 6,
            padding: '10px 4px',
            boxSizing: 'border-box',
            background: 'linear-gradient(180deg, rgba(12,10,12,0.96), rgba(5,4,6,0.98))',
            borderLeft: '1px solid rgba(255,215,0,0.2)',
            justifyContent: 'center',
          }
        : {
            position: 'fixed',
            right: 8,
            top: '42%',
            transform: 'translateY(-50%)',
            zIndex: 1100,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 6,
            width: 48,
          }
    }
  >
    {visibleItems(isSong, showLongGoals).map((item, idx) => {
      const isActive = active === item.key && item.label !== '礼部';
      const is礼部 = item.label === '礼部';
      return (
        <button
          key={`${item.key}-${idx}`}
          type="button"
          title={item.title}
          aria-label={item.title}
          onClick={() => onToggle(item.key)}
          style={circleBtn(isActive, is礼部)}
        >
          {item.label}
        </button>
      );
    })}
  </nav>
);
