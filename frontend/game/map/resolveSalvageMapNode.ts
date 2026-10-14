import type { MapRegion } from './mapTypes';
import { salvageRegionIdForSongMap } from './songSalvageRegionMap';
import type { SalvageMapNode, SalvageRegion } from '../ming/salvageStateTypes';

/** 宋图路分点击 → 解析 salvage 节点（盘面 id 与多边形 id 不一致时合成） */
export function resolveSalvageMapNode(args: {
  mapRegionId: string;
  mapRegions: MapRegion[];
  mapWidth: number;
  mapHeight: number;
  nodeById: Map<string, SalvageMapNode>;
  salvageRegions: SalvageRegion[];
  playerPower: string;
}): SalvageMapNode | null {
  const { mapRegionId, mapRegions, mapWidth, mapHeight, nodeById, salvageRegions, playerPower } =
    args;
  const mapRegion = mapRegions.find((r) => r.id === mapRegionId);
  const salvageId = salvageRegionIdForSongMap(mapRegionId);

  const direct = nodeById.get(mapRegionId);
  if (
    direct?.region &&
    (direct.kind !== 'external' || (direct.region.controlled_by || playerPower) === playerPower)
  ) {
    return direct;
  }

  const salvageNode = nodeById.get(salvageId);
  const salvageRegion =
    salvageRegions.find((r) => r.id === salvageId) || salvageNode?.region || null;
  if (!salvageRegion && !salvageNode) return null;

  const region: SalvageRegion = {
    ...(salvageRegion || salvageNode!.region!),
    name:
      salvageRegion?.display_name ||
      mapRegion?.name ||
      salvageRegion?.name ||
      salvageNode?.region?.display_name ||
      salvageNode?.region?.name ||
      mapRegionId,
  };

  const cx = mapRegion?.centroid.x ?? 0;
  const cy = mapRegion?.centroid.y ?? 0;
  return {
    ...(salvageNode || {
      id: mapRegionId,
      kind: 'region',
      x: mapWidth > 0 ? (cx / mapWidth) * 100 : 50,
      y: mapHeight > 0 ? (cy / mapHeight) * 100 : 50,
      armies: [],
      buildings: [],
    }),
    id: mapRegionId,
    kind: 'region',
    region,
    armies: salvageNode?.armies || [],
    buildings: salvageNode?.buildings || [],
    risk:
      salvageNode?.risk ??
      Number(region.unrest ?? 0) +
        Number(region.military_pressure ?? 0) +
        (100 - Number(region.public_support ?? 50)),
  };
}
