'use client';

import React, { useState } from 'react';
import type { SalvageMinister } from './salvageStateTypes';
import { getMingSalvageAssetUrl } from '../../lib/mingApi';

export function getSalvageMinisterPortraitUrls(
  m: SalvageMinister,
  portraitPrefix = 'minister_',
): { primary: string; fallback?: string } {
  const isCustom = m.portrait_id?.startsWith('custom:');
  if (isCustom) {
    return {
      primary: getMingSalvageAssetUrl(
        `/portraits/custom/${encodeURIComponent(m.name)}?t=${encodeURIComponent(m.portrait_id!)}`,
      ),
    };
  }
  const primary = getMingSalvageAssetUrl(
    `/portraits/${portraitPrefix}${m.id ?? m.name}.png`,
  );
  const fallback =
    m.portrait_id ?
      getMingSalvageAssetUrl(`/portraits/${m.portrait_id}.png`)
    : undefined;
  return { primary, fallback };
}

const PLACEHOLDER_STYLE: React.CSSProperties = {
  borderRadius: 4,
  background: 'rgba(255,215,0,0.08)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#ffd700',
};

type Props = {
  minister: SalvageMinister;
  portraitPrefix?: string;
  width?: number;
  height?: number;
  fontSize?: number;
  style?: React.CSSProperties;
  className?: string;
};

export function SalvageMinisterPortrait({
  minister,
  portraitPrefix = 'minister_',
  width = 40,
  height = 48,
  fontSize = 16,
  style,
  className,
}: Props) {
  const { primary, fallback } = getSalvageMinisterPortraitUrls(minister, portraitPrefix);
  const [stage, setStage] = useState<'primary' | 'fallback' | 'placeholder'>(
    primary ? 'primary' : 'placeholder',
  );

  if (stage === 'placeholder') {
    return (
      <div
        className={className}
        style={{ ...PLACEHOLDER_STYLE, width, height, fontSize, ...style }}
      >
        {minister.name.slice(0, 1)}
      </div>
    );
  }

  const src = stage === 'primary' ? primary : fallback ?? '';

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className={className}
      src={src}
      alt={minister.name}
      style={{
        width,
        height,
        objectFit: 'cover',
        borderRadius: 4,
        display: 'block',
        ...style,
      }}
      onError={() => {
        if (stage === 'primary' && fallback) setStage('fallback');
        else setStage('placeholder');
      }}
    />
  );
}
