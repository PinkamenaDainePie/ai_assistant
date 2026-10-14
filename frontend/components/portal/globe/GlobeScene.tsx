'use client';

import { OrbitControls } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import React, { Suspense } from 'react';
import { WORLD_POLITIES } from '@/game/worldPolityProfiles';
import { GlobeBorders } from './GlobeBorders';
import { GlobeEarth } from './GlobeEarth';
import { GlobeMarker } from './GlobeMarker';

type GlobeSceneInnerProps = {
  selectedId: string | null;
  onSelect: (id: string) => void;
};

function GlobeSceneInner({ selectedId, onSelect }: GlobeSceneInnerProps) {
  const radius = 1;

  return (
    <>
      <ambientLight intensity={0.65} />
      <directionalLight position={[4, 2, 3]} intensity={1.2} />
      <directionalLight position={[-3, -1, -2]} intensity={0.3} />
      <group>
        <GlobeEarth radius={radius} />
        <GlobeBorders radius={radius} selectedId={selectedId} onSelect={onSelect} />
        {WORLD_POLITIES.map((polity) => (
          <GlobeMarker
            key={polity.id}
            polity={polity}
            radius={radius}
            selected={selectedId === polity.id}
            onSelect={onSelect}
          />
        ))}
      </group>
      <OrbitControls
        makeDefault
        enablePan={false}
        minDistance={1.8}
        maxDistance={4.2}
        rotateSpeed={0.45}
        autoRotate={!selectedId}
        autoRotateSpeed={0.25}
      />
    </>
  );
}

type GlobeSceneProps = {
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export const GlobeScene: React.FC<GlobeSceneProps> = ({ selectedId, onSelect }) => {
  return (
    <Canvas
      camera={{ position: [0, 0.3, 2.8], fov: 45 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => {
        gl.toneMappingExposure = 1.35;
      }}
      style={{
        background: 'radial-gradient(circle at 50% 42%, #1a2438 0%, #121a28 55%, #0d1218 100%)',
      }}
    >
      <Suspense fallback={null}>
        <GlobeSceneInner selectedId={selectedId} onSelect={onSelect} />
      </Suspense>
    </Canvas>
  );
};
