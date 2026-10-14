'use client';

import React, { useEffect, useState } from 'react';
import type { Character } from '../game/types';
import { buildMingMinisterCharacters } from '../game/scenarios/mingMinisterRoster';

const SONG_PORTRAIT_DIR = '/portraits/song';
const MING_PORTRAIT_DIR = '/portraits/ming';
const MING_PORTRAIT_IDS = new Set(buildMingMinisterCharacters().map((c) => c.id));

export function resolveCharacterPortraitUrl(character: Character): string {
  if (character.avatarUrl) return character.avatarUrl;
  const dir = MING_PORTRAIT_IDS.has(character.id) ? MING_PORTRAIT_DIR : SONG_PORTRAIT_DIR;
  return `${dir}/${character.id}.png`;
}

type CharacterPortraitProps = {
  character: Character;
  className?: string;
  size?: number;
  fontSize?: number;
  /** 门户浅色 / 游戏深色边框 */
  variant?: 'portal' | 'game';
};

export const CharacterPortrait: React.FC<CharacterPortraitProps> = ({
  character,
  className,
  size = 32,
  fontSize = 14,
  variant = 'portal',
}) => {
  const [imgFailed, setImgFailed] = useState(false);
  const src = resolveCharacterPortraitUrl(character);

  useEffect(() => {
    setImgFailed(false);
  }, [character.id, src]);

  if (!imgFailed) {
    const imgClass =
      className ??
      (variant === 'portal'
        ? 'portal-dialogue__avatar portal-dialogue__avatar--img'
        : undefined);
    return (
      <img
        className={imgClass}
        src={src}
        alt={character.name}
        onError={() => setImgFailed(true)}
        style={
          variant === 'game'
            ? {
                width: size,
                height: size,
                borderRadius: '50%',
                objectFit: 'cover',
                border: '1px solid rgba(255,215,0,0.5)',
                flexShrink: 0,
              }
            : undefined
        }
      />
    );
  }

  if (variant === 'portal') {
    return (
      <div className="portal-dialogue__avatar" style={{ backgroundColor: character.avatarColor || '#888' }}>
        {character.name.slice(0, 1)}
      </div>
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: character.avatarColor || '#444',
        border: '1px solid rgba(255,215,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {character.name.slice(0, 2)}
    </div>
  );
};
