'use client';

import React, { useCallback, useEffect, useState } from 'react';

const POSTERS = [
  { src: '/ui/ming/long-goals/long_goal_ming.jpg', alt: '长期目标：让大明再续二百年' },
  { src: '/ui/ming/long-goals/long_goal_tech.jpg', alt: '长期目标：科技树与文明延续' },
  { src: '/ui/ming/long-goals/long_goal_modernity.jpg', alt: '长期目标：从王朝危机到现代文明' },
];

type Props = {
  onClose: () => void;
};

export const MingLongGoalsModal: React.FC<Props> = ({ onClose }) => {
  const [index, setIndex] = useState(0);
  const goPrev = useCallback(
    () => setIndex((i) => (i + POSTERS.length - 1) % POSTERS.length),
    [],
  );
  const goNext = useCallback(() => setIndex((i) => (i + 1) % POSTERS.length), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [goPrev, goNext, onClose]);

  const poster = POSTERS[index];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="大明长期目标"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 19500,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.82)',
      }}
    >
      <button
        type="button"
        aria-label="关闭"
        onClick={onClose}
        style={{
          position: 'absolute',
          top: 16,
          right: 20,
          border: 'none',
          background: 'transparent',
          color: '#fff',
          fontSize: 28,
          cursor: 'pointer',
        }}
      >
        ×
      </button>
      <button type="button" aria-label="上一张" onClick={goPrev} style={navBtn('left')}>
        ‹
      </button>
      <figure style={{ margin: 0, maxWidth: 'min(900px, 88vw)', maxHeight: '80vh' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={poster.src}
          alt={poster.alt}
          style={{ width: '100%', height: 'auto', maxHeight: '80vh', objectFit: 'contain', borderRadius: 8 }}
        />
      </figure>
      <button type="button" aria-label="下一张" onClick={goNext} style={navBtn('right')}>
        ›
      </button>
      <div style={{ position: 'absolute', bottom: 24, display: 'flex', gap: 8 }}>
        {POSTERS.map((_, i) => (
          <button
            key={i}
            type="button"
            aria-label={`第 ${i + 1} 张`}
            onClick={() => setIndex(i)}
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              border: 'none',
              background: i === index ? '#ffd700' : 'rgba(255,255,255,0.35)',
              cursor: 'pointer',
            }}
          />
        ))}
      </div>
    </div>
  );
};

function navBtn(side: 'left' | 'right'): React.CSSProperties {
  return {
    position: 'absolute',
    [side]: 16,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 44,
    height: 44,
    borderRadius: '50%',
    border: '1px solid rgba(255,215,0,0.4)',
    background: 'rgba(0,0,0,0.5)',
    color: '#ffd700',
    fontSize: 28,
    cursor: 'pointer',
  } as React.CSSProperties;
}
