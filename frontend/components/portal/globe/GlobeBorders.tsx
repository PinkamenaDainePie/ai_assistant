'use client';

import React, { useMemo } from 'react';
import * as THREE from 'three';
import {
  createSphericalBorderTubeGeometry,
  createSphericalPolygonGeometry,
  densifyRing,
  parseBorderGeoJson,
} from '@/game/globeGeo';
import { SONG_ERA_BORDERS } from '@/game/data/song-era-borders';

type BorderRegionProps = {
  id: string;
  color: string;
  ring: [number, number][];
  radius: number;
  selected: boolean;
  onSelect: (id: string) => void;
};

function BorderRegion({ id, color, ring, radius, selected, onSelect }: BorderRegionProps) {
  const denseRing = useMemo(() => densifyRing(ring, 3), [ring]);
  const fillGeometry = useMemo(() => createSphericalPolygonGeometry(denseRing, radius, 0.004), [denseRing, radius]);
  const borderGeometry = useMemo(
    () => createSphericalBorderTubeGeometry(ring, radius, 0.0065, selected ? 0.001 : 0.00075),
    [ring, radius, selected],
  );

  return (
    <group>
      <mesh
        geometry={fillGeometry}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'auto';
        }}
      >
        <meshBasicMaterial
          color={color}
          transparent
          opacity={selected ? 0.38 : 0.18}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh geometry={borderGeometry} renderOrder={2}>
        <meshBasicMaterial
          color={selected ? '#1a1a1a' : color}
          transparent
          opacity={selected ? 0.92 : 0.82}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

type GlobeBordersProps = {
  radius: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export const GlobeBorders: React.FC<GlobeBordersProps> = ({ radius, selectedId, onSelect }) => {
  const borders = useMemo(() => parseBorderGeoJson(SONG_ERA_BORDERS), []);

  return (
    <group>
      {borders.map((border) => (
        <BorderRegion
          key={border.id}
          id={border.id}
          color={border.color}
          ring={border.ring}
          radius={radius}
          selected={selectedId === border.id}
          onSelect={onSelect}
        />
      ))}
    </group>
  );
};
