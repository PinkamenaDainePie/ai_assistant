'use client';

import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';

type Props = {
  regionWarning?: string;
};

export const MingRegionWarningHover: React.FC<Props> = ({ regionWarning }) => {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  if (!regionWarning?.trim()) return null;

  const show = () => {
    const r = triggerRef.current?.getBoundingClientRect();
    if (r) setPos({ left: r.left, top: r.bottom + 6 });
    setOpen(true);
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onMouseEnter={show}
        onMouseLeave={() => setOpen(false)}
        onFocus={show}
        onBlur={() => setOpen(false)}
        style={{
          padding: '2px 10px',
          borderRadius: 999,
          border: open ? '1px solid rgba(250,173,20,0.65)' : '1px solid rgba(250,173,20,0.35)',
          background: open ? 'rgba(250,173,20,0.12)' : 'rgba(250,173,20,0.06)',
          color: '#faad14',
          cursor: 'default',
          fontSize: 12,
          flexShrink: 0,
        }}
      >
        地区警讯
      </button>
      {open && pos && typeof document !== 'undefined' &&
        createPortal(
          <div
            role="tooltip"
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
            style={{
              position: 'fixed',
              left: pos.left,
              top: pos.top,
              zIndex: 20000,
              width: 'min(520px, calc(100vw - 24px))',
              maxHeight: 'min(320px, 50vh)',
              overflowY: 'auto',
              padding: '12px 14px',
              borderRadius: 10,
              border: '1px solid rgba(250,173,20,0.45)',
              background: 'linear-gradient(180deg, #1a1410 0, #0d0b10 100%)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.55)',
              fontSize: 12,
              lineHeight: 1.6,
              color: '#faad14',
            }}
          >
            {regionWarning}
          </div>,
          document.body,
        )}
    </>
  );
};
