import { getScenario } from '../scenarios';
import {
  MAP_IMAGE_HEIGHT,
  MAP_IMAGE_SRC_DEFAULT,
  MAP_IMAGE_WIDTH,
  type MapFitMode,
} from './mapConstants';
import { mapRegions } from './mapRegions';
import { mingMapRegions } from './mingMapRegions';
import { mingMapExternalRegions } from './mingMapExternalRegions';
import type { MapRegion } from './mapTypes';

export function getMapRegionsForScenario(scenarioId: string | null | undefined): MapRegion[] {
  const profile = scenarioId ? getScenario(scenarioId)?.mapRegionProfile : undefined;
  if (profile === 'ming') return mingMapRegions;
  return mapRegions;
}

export function getExternalMapRegionsForScenario(scenarioId: string | null | undefined): MapRegion[] {
  const profile = scenarioId ? getScenario(scenarioId)?.mapRegionProfile : undefined;
  if (profile === 'ming') return mingMapExternalRegions;
  return [];
}

export function getMapImageForScenario(scenarioId: string | null | undefined): string {
  if (scenarioId) {
    const scenario = getScenario(scenarioId);
    if (scenario?.mapImage) return scenario.mapImage;
  }
  return MAP_IMAGE_SRC_DEFAULT;
}

export function getMapDimensionsForScenario(
  scenarioId: string | null | undefined,
): { width: number; height: number } {
  const scenario = scenarioId ? getScenario(scenarioId) : undefined;
  if (scenario?.mapWidth && scenario?.mapHeight) {
    return { width: scenario.mapWidth, height: scenario.mapHeight };
  }
  return { width: MAP_IMAGE_WIDTH, height: MAP_IMAGE_HEIGHT };
}

export function getMapFitModeForScenario(
  _scenarioId: string | null | undefined,
): MapFitMode {
  // 水墨底图用 contain，避免 cover 裁剪导致 hex/圆点错位
  return 'contain';
}
