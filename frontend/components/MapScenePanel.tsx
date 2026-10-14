'use client';

import React, { useMemo, useState } from 'react';
import {
  getMapDimensionsForScenario,
  getMapFitModeForScenario,
  getMapImageForScenario,
  getMapRegionsForScenario,
} from '../game/map/scenarioMap';
import { useGameStore } from '../game/store';
import type { NationState } from '../game/types';
import { buildRegionDetailView } from '../game/map/regionDisplay';
import { MapViewport } from './map/MapViewport';
import { MapRegionLayer } from './map/MapRegionLayer';
import { MapLabelLayer } from './map/MapLabelLayer';
import { MapMarkerLayer } from './map/MapMarkerLayer';
import { MapInfoCard } from './map/MapInfoCard';

type MapScenePanelProps = {
  scenarioIdOverride?: string | null;
  nationOverride?: NationState;
};

export const MapScenePanel: React.FC<MapScenePanelProps> = ({
  scenarioIdOverride,
  nationOverride,
}) => {
  const songStore = useGameStore((s) => ({
    scenarioId: s.scenarioId,
    nationState: s.nationState,
    regionStatus: s.regionStatus,
  }));
  const scenarioId = scenarioIdOverride ?? songStore.scenarioId;
  const nationState = nationOverride ?? songStore.nationState;
  const regionStatus = songStore.regionStatus;
  const mapRegions = useMemo(
    () => getMapRegionsForScenario(scenarioId),
    [scenarioId],
  );
  const mapSrc = getMapImageForScenario(scenarioId);
  const mapSize = useMemo(
    () => getMapDimensionsForScenario(scenarioId),
    [scenarioId],
  );
  const mapFitMode = getMapFitModeForScenario(scenarioId);

  const [hoveredRegionId, setHoveredRegionId] = useState<string | null>(null);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);

  const selectedRegion = useMemo(
    () => mapRegions.find((r) => r.id === selectedRegionId) ?? null,
    [selectedRegionId],
  );

  const regionDetail = useMemo(
    () =>
      selectedRegion
        ? buildRegionDetailView({
            region: selectedRegion,
            dynasty: nationState.dynasty,
            nationMetrics: nationState.metrics,
            regionStatus,
          })
        : null,
    [selectedRegion, nationState.dynasty, nationState.metrics, regionStatus],
  );

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        zIndex: 0,
        overflow: 'hidden',
        backgroundColor: '#0a0806',
      }}
    >
      <MapViewport
        imageWidth={mapSize.width}
        imageHeight={mapSize.height}
        fitMode={mapFitMode}
      >
        <image
          href={mapSrc}
          width={mapSize.width}
          height={mapSize.height}
          style={{ pointerEvents: 'none' }}
        />
        <MapRegionLayer
          regions={mapRegions}
          hoveredRegionId={hoveredRegionId}
          selectedRegionId={selectedRegionId}
          onHoverRegion={setHoveredRegionId}
          onSelectRegion={(id) =>
            setSelectedRegionId((prev) => (prev === id ? null : id))
          }
        />
        <MapLabelLayer
          regions={mapRegions}
          hoveredRegionId={hoveredRegionId}
          selectedRegionId={selectedRegionId}
        />
        <MapMarkerLayer />
      </MapViewport>
      <MapInfoCard detail={regionDetail} onClose={() => setSelectedRegionId(null)} />
    </div>
  );
};
