'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type Position = { left: number; top: number };

export function useDraggablePanel(resetKey?: string) {
  const panelRef = useRef<HTMLElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originLeft: number;
    originTop: number;
  } | null>(null);
  const [pos, setPos] = useState<Position | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    setPos(null);
    dragRef.current = null;
    setDragging(false);
  }, [resetKey]);

  const clamp = useCallback((left: number, top: number) => {
    const el = panelRef.current;
    const w = el?.offsetWidth ?? 320;
    const h = el?.offsetHeight ?? 120;
    const maxLeft = Math.max(8, window.innerWidth - w - 8);
    const maxTop = Math.max(8, window.innerHeight - h - 8);
    return {
      left: Math.min(maxLeft, Math.max(8, left)),
      top: Math.min(maxTop, Math.max(8, top)),
    };
  }, []);

  const endDrag = useCallback((pointerId: number) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== pointerId) return;
    dragRef.current = null;
    setDragging(false);
  }, []);

  useEffect(() => {
    if (!dragging) return;

    const onMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== e.pointerId) return;
      setPos(
        clamp(
          drag.originLeft + e.clientX - drag.startX,
          drag.originTop + e.clientY - drag.startY,
        ),
      );
    };

    const onUp = (e: PointerEvent) => {
      endDrag(e.pointerId);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
  }, [dragging, clamp, endDrag]);

  const onDragHandlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if ((e.target as HTMLElement).closest('button')) return;
      const el = panelRef.current;
      if (!el) return;
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const originLeft = pos?.left ?? rect.left;
      const originTop = pos?.top ?? rect.top;
      if (!pos) setPos({ left: originLeft, top: originTop });
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originLeft,
        originTop,
      };
      setDragging(true);
    },
    [pos],
  );

  const dragHandleProps = {
    onPointerDown: onDragHandlePointerDown,
    style: {
      cursor: dragging ? 'grabbing' : 'grab',
      touchAction: 'none' as const,
      userSelect: 'none' as const,
    },
  };

  return { panelRef, dragHandleProps, pos, dragging };
}
