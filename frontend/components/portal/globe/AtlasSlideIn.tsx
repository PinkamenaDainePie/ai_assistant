'use client';

import React from 'react';

type AtlasSlideInProps = {
  /** 变化时重新触发从左向右划入 */
  animKey: string;
  children: React.ReactNode;
  className?: string;
  /** 错峰入场延迟（毫秒） */
  delayMs?: number;
};

/** 门户 / 游戏：内容切换或首次展示时自左向右滑入（纯 CSS）。 */
export const AtlasSlideIn: React.FC<AtlasSlideInProps> = ({
  animKey,
  children,
  className,
  delayMs = 0,
}) => (
  <div
    key={animKey}
    className={['portal-slide-in', className].filter(Boolean).join(' ')}
    style={delayMs > 0 ? { animationDelay: `${delayMs}ms` } : undefined}
  >
    {children}
  </div>
);
