'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

type CharacterNameTooltipProps = {
  name: string;
  brief?: string | null;
  title?: string | null;
  /** Hover delay before showing tooltip (ms). */
  delayMs?: number;
  className?: string;
  style?: React.CSSProperties;
  /**
   * Trigger element. Prefer wrapping the whole character card/row so hover
   * works on the entire box, not only the name text.
   */
  children: React.ReactElement;
};

/**
 * Delayed hover tooltip for obscure historical figures.
 * Attach to the entire character box (button/row), not just the name.
 */
export const CharacterNameTooltip: React.FC<CharacterNameTooltipProps> = ({
  name,
  brief,
  title,
  delayMs = 500,
  className,
  style,
  children,
}) => {
  const text = (brief || '').trim();
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timerRef.current != null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const hide = () => {
    clearTimer();
    setOpen(false);
  };

  const scheduleShow = () => {
    if (!text) return;
    clearTimer();
    timerRef.current = setTimeout(() => {
      const r = triggerRef.current?.getBoundingClientRect();
      if (!r) return;
      const width = 300;
      const left = Math.min(r.left, window.innerWidth - width - 8);
      const preferBelow = r.bottom + 8;
      const top =
        preferBelow + 200 > window.innerHeight ? Math.max(8, r.top - 8 - 160) : preferBelow;
      setPos({ left: Math.max(8, left), top });
      setOpen(true);
    }, delayMs);
  };

  useEffect(() => () => clearTimer(), []);

  const child = React.Children.only(children) as React.ReactElement<{
    onMouseEnter?: (e: React.MouseEvent) => void;
    onMouseLeave?: (e: React.MouseEvent) => void;
    onFocus?: (e: React.FocusEvent) => void;
    onBlur?: (e: React.FocusEvent) => void;
    className?: string;
    style?: React.CSSProperties;
    ref?: React.Ref<HTMLElement>;
  }>;

  const setRefs = (node: HTMLElement | null) => {
    triggerRef.current = node;
    const ref = (child as React.ReactElement & { ref?: React.Ref<HTMLElement> }).ref;
    if (typeof ref === 'function') ref(node);
    else if (ref && typeof ref === 'object') (ref as React.MutableRefObject<HTMLElement | null>).current = node;
  };

  const merged = React.cloneElement(child, {
    ref: setRefs,
    className: [child.props.className, className].filter(Boolean).join(' ') || undefined,
    style: { ...child.props.style, ...style, cursor: text ? 'help' : child.props.style?.cursor },
    onMouseEnter: (e: React.MouseEvent) => {
      scheduleShow();
      child.props.onMouseEnter?.(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      hide();
      child.props.onMouseLeave?.(e);
    },
    onFocus: (e: React.FocusEvent) => {
      scheduleShow();
      child.props.onFocus?.(e);
    },
    onBlur: (e: React.FocusEvent) => {
      hide();
      child.props.onBlur?.(e);
    },
  });

  return (
    <>
      {merged}
      {open && text && pos && typeof document !== 'undefined'
        ? createPortal(
            <div
              role="tooltip"
              style={{
                position: 'fixed',
                left: pos.left,
                top: pos.top,
                zIndex: 20000,
                width: 300,
                maxWidth: 'min(300px, calc(100vw - 16px))',
                maxHeight: 220,
                overflowY: 'auto',
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid rgba(255, 215, 0, 0.35)',
                background: 'rgba(14, 11, 16, 0.97)',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
                color: '#f0e6d2',
                fontSize: 12,
                lineHeight: 1.55,
                pointerEvents: 'none',
              }}
            >
              <div style={{ fontWeight: 700, color: '#ffd700', marginBottom: 4 }}>{name}</div>
              {title ? (
                <div style={{ color: '#aaa', fontSize: 11, marginBottom: 6 }}>{title}</div>
              ) : null}
              <div>{text}</div>
            </div>,
            document.body,
          )
        : null}
    </>
  );
};
