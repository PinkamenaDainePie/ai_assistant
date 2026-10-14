'use client';

import React from 'react';
import type { MapRegion } from '@/game/map/mapTypes';
import { mingSalvagePathTransform } from '@/game/ming/mingMapDisplay';
import { pointsToSvgPolygonPoints } from '@/game/map/mapUtils';
import {
  MAP_REGION_DEFAULT_FILL,
  MAP_REGION_DEFAULT_STROKE,
  MAP_REGION_HOVER_FILL,
  MAP_REGION_HOVER_STROKE,
  MAP_REGION_SELECTED_FILL,
  MAP_REGION_SELECTED_STROKE,
} from '@/game/map/mapConstants';

interface MapRegionLayerProps {
  regions: MapRegion[];
  hoveredRegionId: string | null;
  selectedRegionId: string | null;
  onHoverRegion: (regionId: string | null) => void;
  onSelectRegion: (regionId: string) => void;
  getRegionStyle?: (regionId: string) =>
    | { fill?: string; stroke?: string; opacity?: number }
    | undefined;
  /** 万历水墨底图：低对比描边，选中/hover 用淡绿高亮 */
  inkWashMode?: boolean;
}

function regionInteractionProps(
  region: MapRegion,
  enabled: boolean,
  polygonOpacity: number,
  onHoverRegion: (regionId: string | null) => void,
  onSelectRegion: (regionId: string) => void,
) {
  return {
    vectorEffect: 'non-scaling-stroke' as const,
    style: {
      cursor: enabled ? 'pointer' : 'not-allowed',
      opacity: enabled ? polygonOpacity : 0.4,
      transition: 'fill 0.15s ease, stroke 0.15s ease, opacity 0.15s ease',
    },
    onPointerDown: (e: React.PointerEvent) => {
      e.stopPropagation();
    },
    onMouseEnter: () => {
      if (!enabled) return;
      onHoverRegion(region.id);
    },
    onMouseLeave: () => {
      if (!enabled) return;
      onHoverRegion(null);
    },
    onClick: (event: React.MouseEvent) => {
      event.stopPropagation();
      if (!enabled) return;
      onSelectRegion(region.id);
    },
  };
}

export function MapRegionLayer({
  regions,
  hoveredRegionId,
  selectedRegionId,
  onHoverRegion,
  onSelectRegion,
  getRegionStyle,
  inkWashMode = false,
}: MapRegionLayerProps) {
  const salvageTransform = mingSalvagePathTransform();

  return (
    <g data-layer="regions">
      {regions.map((region) => {
        const isHovered = hoveredRegionId === region.id;
        const isSelected = selectedRegionId === region.id;
        const enabled = region.enabled !== false;
        const custom = getRegionStyle?.(region.id);

        let fill = custom?.fill ?? region.color ?? MAP_REGION_DEFAULT_FILL;
        let stroke = custom?.stroke ?? MAP_REGION_DEFAULT_STROKE;
        let strokeWidth = inkWashMode ? 1.2 : 2;
        let polygonOpacity = custom?.opacity ?? 1;

        if (isHovered) {
          if (inkWashMode) {
            fill = 'rgba(180, 150, 80, 0.28)';
            stroke = 'rgba(120, 100, 60, 0.65)';
            strokeWidth = 1.4;
          } else {
            fill = MAP_REGION_HOVER_FILL;
            stroke = MAP_REGION_HOVER_STROKE;
            strokeWidth = 3;
          }
          polygonOpacity = 1;
        }

        if (isSelected) {
          if (inkWashMode) {
            fill = 'rgba(120, 170, 90, 0.22)';
            stroke = 'rgba(245, 235, 190, 0.9)';
            strokeWidth = 2;
          } else {
            fill = MAP_REGION_SELECTED_FILL;
            stroke = MAP_REGION_SELECTED_STROKE;
            strokeWidth = 4;
          }
          polygonOpacity = 1;
        }

        const interaction = regionInteractionProps(
          region,
          enabled,
          polygonOpacity,
          onHoverRegion,
          onSelectRegion,
        );

        if (region.svgPaths?.length) {
          return (
            <g key={region.id} transform={salvageTransform} {...interaction}>
              {region.svgPaths.map((d, idx) => (
                <path
                  key={`${region.id}-${idx}`}
                  d={d}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                />
              ))}
            </g>
          );
        }

        return (
          <polygon
            key={region.id}
            points={pointsToSvgPolygonPoints(region.points)}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            {...interaction}
          />
        );
      })}
    </g>
  );
}
