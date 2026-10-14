'use client';

import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import React, { useRef } from 'react';
import * as THREE from 'three';
import { latLngToSphere } from '@/game/globeMath';
import type { WorldPolityProfile } from '@/game/worldPolityProfiles';

type GlobeMarkerProps = {
  polity: WorldPolityProfile;
  radius: number;
  selected: boolean;
  onSelect: (id: string) => void;
};

export const GlobeMarker: React.FC<GlobeMarkerProps> = ({ polity, radius, selected, onSelect }) => {
  const hitRef = useRef<THREE.Mesh>(null);
  const dotRef = useRef<THREE.Mesh>(null);
  const position = latLngToSphere(polity.lat, polity.lng, radius + 0.015);

  useFrame(({ clock }) => {
    if (!dotRef.current) return;
    const pulse = selected ? 1 + Math.sin(clock.elapsedTime * 3) * 0.12 : 1;
    dotRef.current.scale.setScalar(pulse * (selected ? 1.35 : 1));
  });

  return (
    <group position={position}>
      <mesh
        ref={hitRef}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(polity.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'auto';
        }}
      >
        <sphereGeometry args={[0.055, 12, 12]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
      <mesh ref={dotRef}>
        <sphereGeometry args={[0.012, 12, 12]} />
        <meshStandardMaterial
          color={polity.markerColor}
          emissive={polity.markerColor}
          emissiveIntensity={selected ? 0.9 : 0.4}
          roughness={0.35}
        />
      </mesh>
      {selected ? (
        <Html
          center
          distanceFactor={4}
          pointerEvents="none"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
          wrapperClass="portal-globe__label-wrap"
        >
          <div
            className="portal-globe__tag"
            style={{ '--tag-accent': polity.markerColor } as React.CSSProperties}
          >
            <span className="portal-globe__tag-dot" aria-hidden />
            <span className="portal-globe__tag-text">{polity.name}</span>
          </div>
        </Html>
      ) : null}
    </group>
  );
};
