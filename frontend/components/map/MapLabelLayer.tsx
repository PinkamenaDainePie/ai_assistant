'use client';

import React from 'react';
import type { MapRegion } from '@/game/map/mapTypes';

interface MapLabelLayerProps {
  regions: MapRegion[];
  hoveredRegionId: string | null;
  selectedRegionId: string | null;
}

export function MapLabelLayer({
  regions,
  hoveredRegionId,
  selectedRegionId,
}: MapLabelLayerProps) {
  return (
    <g data-layer="labels" style={{ pointerEvents: 'none' }}>
      {regions.map((region) => {
        const isHovered = hoveredRegionId === region.id;
        const isSelected = selectedRegionId === region.id;
        const fontSize = isSelected ? 26 : isHovered ? 24 : 21;

        return (
          <text
            key={region.id}
            x={region.centroid.x}
            y={region.centroid.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={fontSize}
            fontWeight={isSelected ? 800 : 700}
            fill={isSelected ? '#fff3bf' : '#ffe7a3'}
            stroke="rgba(0,0,0,0.75)"
            strokeWidth={4}
            paintOrder="stroke fill"
            style={{ userSelect: 'none' }}
          >
            {region.name}
          </text>
        );
      })}
    </g>
  );
}
