import { useCallback, useEffect, useMemo, useRef } from 'react';

export const COURT_CHAT_STREAM_DELAYS: Record<number, number> = {
  1: 170,
  2: 120,
  3: 85,
  4: 45,
  5: 0,
};

const LS_KEY = 'courtChatStreamSpeed';

export function normalizeCourtChatStreamSpeed(value: number): number {
  return Math.min(5, Math.max(1, Math.round(value)));
}

export function loadCourtChatStreamSpeed(): number {
  if (typeof window === 'undefined') return 3;
  const saved = Number(localStorage.getItem(LS_KEY) || '3');
  return Number.isFinite(saved) ? normalizeCourtChatStreamSpeed(saved) : 3;
}

export function saveCourtChatStreamSpeedLocal(speed: number) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(LS_KEY, String(normalizeCourtChatStreamSpeed(speed)));
}

export function useCourtChatDeltaQueue(streamSpeed: number) {
  const speed = normalizeCourtChatStreamSpeed(streamSpeed);
  const delay = COURT_CHAT_STREAM_DELAYS[speed] ?? 85;
  const queueRef = useRef<Array<{ speaker: string; delta: string }>>([]);
  const timerRef = useRef<number | null>(null);
  const appendRef = useRef<(speaker: string, delta: string) => void>(() => undefined);

  const drain = useCallback(() => {
    const next = queueRef.current.shift();
    if (next) appendRef.current(next.speaker, next.delta);
    if (queueRef.current.length) {
      timerRef.current = window.setTimeout(drain, delay);
    } else {
      timerRef.current = null;
    }
  }, [delay]);

  const queueDelta = useCallback(
    (speaker: string, delta: string, append: (speaker: string, delta: string) => void) => {
      if (!speaker || !delta) return;
      appendRef.current = append;
      queueRef.current.push({ speaker, delta });
      if (timerRef.current === null) {
        timerRef.current = window.setTimeout(drain, delay);
      }
    },
    [delay, drain],
  );

  const flush = useCallback((append: (speaker: string, delta: string) => void) => {
    appendRef.current = append;
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    while (queueRef.current.length) {
      const next = queueRef.current.shift();
      if (next) append(next.speaker, next.delta);
    }
  }, []);

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      queueRef.current = [];
    },
    [],
  );

  return useMemo(() => ({ queueDelta, flush, delay }), [queueDelta, flush, delay]);
}
