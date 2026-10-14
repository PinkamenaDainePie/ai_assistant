'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { SalvageMinister } from '../../game/ming/salvageStateTypes';
import {
  arrangeCourtPositions,
  snapToSlot,
  type CourtPct,
} from '../../game/ming/mingCourtLayout';
import { mingFetchCourtLayout, mingSaveCourtLayout } from '../../lib/mingApi';
import { SalvageMinisterPortrait } from '../../game/ming/SalvageMinisterPortrait';

type Props = {
  ministers: SalvageMinister[];
  onOpenChat: (name: string) => void;
};

export const MingCourtPerspectivePanel: React.FC<Props> = ({ ministers, onOpenChat }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef<{
    name: string;
    pointerId: number;
    startMX: number;
    startMY: number;
    startPX: number;
    startPY: number;
  } | null>(null);
  const savedPosRef = useRef<Record<string, CourtPct> | null>(null);
  const didDrag = useRef(false);
  const suppressNextClick = useRef(false);

  const [positions, setPositions] = useState<Record<string, CourtPct>>({});
  const listKey = ministers.map((m) => m.name).join('|');

  useEffect(() => {
    let cancelled = false;
    const names = ministers.map((m) => m.name);

    const arrange = (saved: Record<string, CourtPct>) => {
      if (cancelled) return;
      setPositions(arrangeCourtPositions(names, saved));
    };

    if (savedPosRef.current !== null) {
      arrange(savedPosRef.current);
    } else {
      void mingFetchCourtLayout().then((saved) => {
        savedPosRef.current = saved;
        arrange(saved);
      });
    }

    return () => {
      cancelled = true;
    };
  }, [listKey, ministers]);

  const finishCourtDrag = useCallback((shouldSnap: boolean) => {
    const dragName = dragging.current?.name;
    if (dragName && shouldSnap) {
      setPositions((prev) => {
        const cur = prev[dragName];
        if (!cur) return prev;
        const occupied = new Set<string>();
        const snapped = snapToSlot(cur.px, cur.py, occupied, '');
        const next = { ...prev, [dragName]: snapped };
        savedPosRef.current = next;
        void mingSaveCourtLayout(next);
        return next;
      });
    } else if (savedPosRef.current) {
      void mingSaveCourtLayout(savedPosRef.current);
    }
    dragging.current = null;
    if (shouldSnap) {
      suppressNextClick.current = true;
      window.setTimeout(() => {
        suppressNextClick.current = false;
        didDrag.current = false;
      }, 0);
    } else {
      didDrag.current = false;
    }
  }, []);

  const onCourtPointerDown = (e: React.PointerEvent<HTMLButtonElement>, name: string) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const pos = positions[name] || { px: 0.5, py: 0.8 };
    dragging.current = {
      name,
      pointerId: e.pointerId,
      startMX: e.clientX,
      startMY: e.clientY,
      startPX: pos.px,
      startPY: pos.py,
    };
    didDrag.current = false;
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onCourtPointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const drag = dragging.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    const dx = e.clientX - drag.startMX;
    const dy = e.clientY - drag.startMY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didDrag.current = true;
    const el = containerRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    if (!width || !height) return;
    const npx = Math.max(0, Math.min(1, drag.startPX + dx / width));
    const npy = Math.max(0, Math.min(1, drag.startPY + dy / height));
    setPositions((prev) => {
      const next = { ...prev, [drag.name]: { px: npx, py: npy } };
      savedPosRef.current = next;
      return next;
    });
  };

  const onCourtPointerEnd = (e: React.PointerEvent<HTMLButtonElement>) => {
    const drag = dragging.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    finishCourtDrag(didDrag.current);
  };

  useEffect(() => {
    const cancelDrag = () => finishCourtDrag(false);
    window.addEventListener('blur', cancelDrag);
    window.addEventListener('contextmenu', cancelDrag);
    return () => {
      window.removeEventListener('blur', cancelDrag);
      window.removeEventListener('contextmenu', cancelDrag);
    };
  }, [finishCourtDrag]);

  if (!ministers.length) {
    return <p style={{ color: '#888', fontSize: 12, margin: '0 0 8px' }}>暂无内阁六部大臣。</p>;
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
        拖拽调整站位（松手自动吸附）
      </div>
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          height: 220,
          borderRadius: 8,
          border: '1px solid rgba(255,215,0,0.2)',
          background: 'linear-gradient(180deg, rgba(20,14,8,0.95) 0%, rgba(8,6,4,0.98) 100%)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 'auto 8% 8px',
            height: 2,
            background: 'linear-gradient(90deg, transparent, rgba(255,215,0,0.35), transparent)',
          }}
        />
        {ministers.map((m) => {
          const pct = positions[m.name];
          const perspScale = pct ? 0.38 + 0.62 * pct.py : 1;
          return (
            <button
              key={m.name}
              type="button"
              style={
                pct
                  ? {
                      position: 'absolute',
                      left: `${pct.px * 100}%`,
                      top: `${pct.py * 100}%`,
                      transform: `translate(-50%, -100%) scale(${perspScale.toFixed(3)})`,
                      transformOrigin: 'bottom center',
                      zIndex: Math.round(pct.py * 1000),
                      cursor: 'grab',
                      width: 56,
                      padding: 4,
                      border: '1px solid rgba(255,215,0,0.25)',
                      borderRadius: 6,
                      background: 'rgba(0,0,0,0.55)',
                      color: '#eee',
                      fontSize: 10,
                      textAlign: 'center',
                    }
                  : { visibility: 'hidden', position: 'absolute' }
              }
              onPointerDown={(e) => onCourtPointerDown(e, m.name)}
              onPointerMove={onCourtPointerMove}
              onPointerUp={onCourtPointerEnd}
              onPointerCancel={onCourtPointerEnd}
              onLostPointerCapture={() => {
                if (dragging.current) finishCourtDrag(didDrag.current);
              }}
              onClick={(e) => {
                if (suppressNextClick.current || didDrag.current) {
                  e.preventDefault();
                  return;
                }
                onOpenChat(m.name);
              }}
            >
              <SalvageMinisterPortrait
                minister={m}
                width={40}
                height={48}
                style={{ margin: '0 auto 2px' }}
              />
              <div style={{ fontWeight: 600, lineHeight: 1.2 }}>{m.name}</div>
              {m.office && (
                <div style={{ color: '#999', fontSize: 9, marginTop: 1 }}>{m.office}</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
