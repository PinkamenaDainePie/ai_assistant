'use client';

import { useTexture } from '@react-three/drei';
import React, { useLayoutEffect } from 'react';
import * as THREE from 'three';

type GlobeEarthProps = {
  radius: number;
};

export const GlobeEarth: React.FC<GlobeEarthProps> = ({ radius }) => {
  const colorMap = useTexture('/textures/earth-day.jpg');

  useLayoutEffect(() => {
    colorMap.colorSpace = THREE.SRGBColorSpace;
    colorMap.anisotropy = 8;
  }, [colorMap]);

  return (
    <mesh>
      <sphereGeometry args={[radius, 96, 96]} />
      <meshBasicMaterial map={colorMap} />
    </mesh>
  );
};
