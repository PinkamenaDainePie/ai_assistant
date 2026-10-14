'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  MAP_INITIAL_SCALE,
  MAP_MAX_SCALE,
  MAP_MIN_SCALE,
  type MapFitMode,
} from '@/game/map/mapConstants';
import { clamp } from '@/game/map/mapUtils';

interface MapViewportProps {
  imageWidth: number;
  imageHeight: number;
  fitMode?: MapFitMode;
  children: React.ReactNode;
}

interface DragState {
  dragging: boolean;
  startClientX: number;
  startClientY: number;
  startOffsetX: number;
  startOffsetY: number;
}

export function MapViewport({
  imageWidth,
  imageHeight,
  fitMode = 'contain',
  children,
}: MapViewportProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(MAP_INITIAL_SCALE);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const scaleRef = useRef(scale);
  const offsetRef = useRef(offset);
  scaleRef.current = scale;
  offsetRef.current = offset;

  const dragStateRef = useRef<DragState>({
    dragging: false,
    startClientX: 0,
    startClientY: 0,
    startOffsetX: 0,
    startOffsetY: 0,
  });

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return;
      const el = event.target as Element | null;
      if (el?.closest?.('polygon')) return;

      event.currentTarget.setPointerCapture(event.pointerId);
      setIsDragging(true);
      dragStateRef.current = {
        dragging: true,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startOffsetX: offsetRef.current.x,
        startOffsetY: offsetRef.current.y,
      };
    },
    [],
  );

  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragStateRef.current;
    if (!drag.dragging) return;

    const deltaX = event.clientX - drag.startClientX;
    const deltaY = event.clientY - drag.startClientY;

    setOffset({
      x: drag.startOffsetX + deltaX,
      y: drag.startOffsetY + deltaY,
    });
  }, []);

  const endDragging = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    dragStateRef.current.dragging = false;
    setIsDragging(false);
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const fitToContainer = () => {
      const cw = el.clientWidth;
      const ch = el.clientHeight;
      if (cw <= 0 || ch <= 0) return;
      const scaleW = cw / imageWidth;
      const scaleH = ch / imageHeight;
      const fitScale = fitMode === 'cover' ? Math.max(scaleW, scaleH) : Math.min(scaleW, scaleH);
      const nextScale = clamp(fitScale, MAP_MIN_SCALE, MAP_MAX_SCALE);
      setScale(nextScale);
      setOffset({
        x: (cw - imageWidth * nextScale) / 2,
        y: (ch - imageHeight * nextScale) / 2,
      });
    };

    fitToContainer();
    const observer = new ResizeObserver(fitToContainer);
    observer.observe(el);
    return () => observer.disconnect();
  }, [imageWidth, imageHeight, fitMode]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();

      const rect = el.getBoundingClientRect();
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;

      const zoomFactor = event.deltaY < 0 ? 1.12 : 0.88;
      const prevScale = scaleRef.current;
      const nextScale = clamp(prevScale * zoomFactor, MAP_MIN_SCALE, MAP_MAX_SCALE);
      if (nextScale === prevScale) return;

      const ox = offsetRef.current.x;
      const oy = offsetRef.current.y;
      const mapX = (mouseX - ox) / prevScale;
      const mapY = (mouseY - oy) / prevScale;
      const nextOffsetX = mouseX - mapX * nextScale;
      const nextOffsetY = mouseY - mapY * nextScale;

      setScale(nextScale);
      setOffset({ x: nextOffsetX, y: nextOffsetY });
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const transform = `translate(${offset.x}px, ${offset.y}px) scale(${scale})`;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        cursor: isDragging ? 'grabbing' : 'grab',
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={endDragging}
      onPointerCancel={endDragging}
    >
      <svg
        width={imageWidth}
        height={imageHeight}
        viewBox={`0 0 ${imageWidth} ${imageHeight}`}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          transform,
          transformOrigin: '0 0',
          willChange: 'transform',
          userSelect: 'none',
        }}
      >
        {children}
      </svg>
    </div>
  );
}
