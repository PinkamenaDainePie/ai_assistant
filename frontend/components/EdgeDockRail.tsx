'use client';

import React from 'react';

export const RAIL_WIDTH = 56;
export const RAIL_EDGE_HIT = 18;

type Side = 'left' | 'right';

type Props = {
  side: Side;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  children: React.ReactNode;
  /** 展开后的栏宽（默认 56） */
  railWidth?: number;
};

export const EdgeDockRail: React.FC<Props> = ({
  side,
  open,
  onOpen,
  onClose,
  children,
  railWidth = RAIL_WIDTH,
}) => {
  const isLeft = side === 'left';
  const hiddenOffset = isLeft ? -railWidth : railWidth;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        [isLeft ? 'left' : 'right']: 0,
        width: open ? railWidth : RAIL_EDGE_HIT,
        overflow: 'hidden',
        zIndex: 140,
        transition: 'width 220ms ease',
      }}
      onMouseEnter={onOpen}
      onMouseLeave={onClose}
    >
      <div
        style={{
          width: railWidth,
          height: '100%',
          transform: open ? 'translateX(0)' : `translateX(${hiddenOffset}px)`,
          transition: 'transform 220ms ease',
        }}
      >
        {children}
      </div>
    </div>
  );
};
