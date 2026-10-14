'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import type { SalvageMapNode } from '../../../game/ming/salvageStateTypes';
import type { ScenarioId } from '../../../game/scenarios';
import { getPlayerPowerId, getScenario } from '../../../game/scenarios';
import {
  getMapDimensionsForScenario,
  getMapFitModeForScenario,
  getMapImageForScenario,
  getMapRegionsForScenario,
  getExternalMapRegionsForScenario,
} from '../../../game/map/scenarioMap';
import { resolveSalvageMapNode } from '../../../game/map/resolveSalvageMapNode';
import { salvageRegionIdForSongMap } from '../../../game/map/songSalvageRegionMap';
import {
  EXTERNAL_MAP_COLOR,
  EXTERNAL_MAP_OPACITY,
  getMingRegionMapStyle,
  pctToMapPixel,
  SALVAGE_REGION_PATH_NEIGHBOR_IDS,
  THEATER_ONLY_REGION_IDS,
  UNREST_MAP_COLOR,
} from '../../../game/ming/mingMapDisplay';
import { mingFetchMap } from '../../../lib/mingApi';
import { MapViewport } from '../../map/MapViewport';
import { MapRegionLayer } from '../../map/MapRegionLayer';
import { MapLabelLayer } from '../../map/MapLabelLayer';
import { MingMapIntelPanel } from './MingMapIntelPanel';
import type { MingSalvageIssue } from '../../../game/ming/mingTurnPhase';
import type { SalvageRegion } from '../../../game/ming/salvageStateTypes';
import { useDraggablePanel } from '../../../hooks/useDraggablePanel';

type Props = {
  scenarioId?: ScenarioId;
  mapNodes?: SalvageMapNode[];
  salvageRegions?: SalvageRegion[];
  issues?: MingSalvageIssue[];
  onOpenSituation?: () => void;
};

export const MingMapScenePanel: React.FC<Props> = ({
  scenarioId = 'ming_wanli',
  mapNodes: mapNodesProp,
  salvageRegions: salvageRegionsProp,
  issues = [],
  onOpenSituation,
}) => {
  const mapSrc = getMapImageForScenario(scenarioId);
  const mapSize = useMemo(() => getMapDimensionsForScenario(scenarioId), [scenarioId]);
  const mapFitMode = getMapFitModeForScenario(scenarioId);
  const scenarioMapRegions = useMemo(() => getMapRegionsForScenario(scenarioId), [scenarioId]);
  const externalMapRegions = useMemo(
    () => getExternalMapRegionsForScenario(scenarioId),
    [scenarioId],
  );
  const playerPower = getPlayerPowerId(scenarioId);
  const isSongMap = getScenario(scenarioId)?.mapRegionProfile === 'song';

  const [fetchedNodes, setFetchedNodes] = useState<SalvageMapNode[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [intelOpen, setIntelOpen] = useState(false);

  useEffect(() => {
    if (mapNodesProp?.length) return;
    let alive = true;
    void mingFetchMap()
      .then((out) => {
        if (alive && out.nodes?.length) setFetchedNodes(out.nodes);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [mapNodesProp?.length]);

  const mapNodes = mapNodesProp?.length ? mapNodesProp : fetchedNodes;

  const nodeById = useMemo(() => new Map(mapNodes.map((n) => [n.id, n])), [mapNodes]);

  const polygonRegionIds = useMemo(
    () => new Set([...scenarioMapRegions, ...externalMapRegions].map((r) => r.id)),
    [scenarioMapRegions, externalMapRegions],
  );

  const polygonRegions = useMemo(
    () =>
      scenarioMapRegions.filter((r) => {
        if (THEATER_ONLY_REGION_IDS.has(r.id)) return false;
        if (isSongMap) return true;
        const node = nodeById.get(r.id);
        if (node?.kind === 'external') return false;
        return true;
      }),
    [isSongMap, nodeById, scenarioMapRegions],
  );

  const neighborPolygonRegions = useMemo(
    () =>
      externalMapRegions.filter(
        (r) => SALVAGE_REGION_PATH_NEIGHBOR_IDS.has(r.id) && r.svgPaths?.length,
      ),
    [externalMapRegions],
  );

  const externalPolygonRegions = useMemo(
    () =>
      externalMapRegions.filter(
        (r) => !SALVAGE_REGION_PATH_NEIGHBOR_IDS.has(r.id) && r.svgPaths?.length,
      ),
    [externalMapRegions],
  );

  const drawablePolygonRegions = useMemo(
    () => [...polygonRegions, ...neighborPolygonRegions],
    [neighborPolygonRegions, polygonRegions],
  );

  const unmappedRegionNodes = useMemo(() => {
    if (isSongMap) return [];
    return mapNodes.filter(
      (n) => n.kind === 'region' && !polygonRegionIds.has(n.id) && n.x != null && n.y != null,
    );
  }, [isSongMap, mapNodes, polygonRegionIds]);

  const externalNodes = useMemo(() => {
    if (isSongMap) return [];
    return mapNodes.filter(
      (n) => n.kind === 'external' && !polygonRegionIds.has(n.id) && n.x != null && n.y != null,
    );
  }, [isSongMap, mapNodes, polygonRegionIds]);

  const theaterNodes = useMemo(() => {
    // 宋图用路分 polygon + salvage 映射；晚明校准的圆点/战区坐标会错位
    if (isSongMap) return [];
    return mapNodes.filter((n) => n.kind === 'theater' && n.x != null && n.y != null);
  }, [isSongMap, mapNodes]);

  const getRegionStyle = useCallback(
    (regionId: string) => {
      const salvageId = isSongMap ? salvageRegionIdForSongMap(regionId) : regionId;
      const node = nodeById.get(salvageId) || nodeById.get(regionId);
      if (!node?.region) return undefined;
      const { fill, stroke, opacity } = getMingRegionMapStyle(node.region, playerPower);
      return { fill, stroke, opacity };
    },
    [isSongMap, nodeById, playerPower],
  );

  const getExternalRegionStyle = useCallback(
    (regionId: string) => {
      const node = nodeById.get(regionId);
      if (node?.region) {
        const { fill, stroke, opacity } = getMingRegionMapStyle(node.region, playerPower);
        return { fill, stroke, opacity };
      }
      return {
        fill: EXTERNAL_MAP_COLOR,
        stroke: '#666',
        opacity: EXTERNAL_MAP_OPACITY,
      };
    },
    [nodeById, playerPower],
  );

  const selectNode = (id: string) => {
    setSelectedId(id);
    setIntelOpen(true);
  };

  const closeIntel = () => {
    setIntelOpen(false);
    setSelectedId(null);
  };

  const selectedNode = useMemo(() => {
    if (!intelOpen || !selectedId) return null;
    if (isSongMap) {
      return resolveSalvageMapNode({
        mapRegionId: selectedId,
        mapRegions: scenarioMapRegions,
        mapWidth: mapSize.width,
        mapHeight: mapSize.height,
        nodeById,
        salvageRegions: salvageRegionsProp || [],
        playerPower,
      });
    }
    return nodeById.get(selectedId) || null;
  }, [
    intelOpen,
    isSongMap,
    mapSize.height,
    mapSize.width,
    nodeById,
    playerPower,
    salvageRegionsProp,
    scenarioMapRegions,
    selectedId,
  ]);
  const highlightId = intelOpen ? selectedId : null;
  const {
    panelRef: issuesPanelRef,
    dragHandleProps: issuesDragHandleProps,
    pos: issuesPos,
  } = useDraggablePanel(`issues-${issues.length}`);

  return (
    <div
      className="ming-map-scene-root"
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        zIndex: 0,
        overflow: 'hidden',
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
          regions={drawablePolygonRegions}
          hoveredRegionId={hoveredId}
          selectedRegionId={highlightId}
          onHoverRegion={setHoveredId}
          onSelectRegion={selectNode}
          getRegionStyle={getRegionStyle}
          inkWashMode
        />
        <MapLabelLayer
          regions={drawablePolygonRegions}
          hoveredRegionId={hoveredId}
          selectedRegionId={highlightId}
        />

        <MapRegionLayer
          regions={externalPolygonRegions}
          hoveredRegionId={hoveredId}
          selectedRegionId={highlightId}
          onHoverRegion={setHoveredId}
          onSelectRegion={selectNode}
          getRegionStyle={getExternalRegionStyle}
          inkWashMode
        />

        <g data-layer="unmapped-region-markers">
          {unmappedRegionNodes.map((node) => {
            const { x, y } = pctToMapPixel(node.x!, node.y!, mapSize.width, mapSize.height);
            const selected = highlightId === node.id;
            const hovered = hoveredId === node.id;
            const style = getMingRegionMapStyle(node.region, playerPower);
            const label = node.region?.name || node.id;
            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  selectNode(node.id);
                }}
              >
                <circle
                  cx={x}
                  cy={y}
                  r={selected ? 22 : hovered ? 20 : 16}
                  fill={style.fill}
                  fillOpacity={style.opacity}
                  stroke={selected || hovered ? '#ffe6a3' : style.stroke}
                  strokeWidth={selected ? 2.5 : 1.5}
                  vectorEffect="non-scaling-stroke"
                />
                <text
                  x={x}
                  y={y - (selected ? 26 : 22)}
                  textAnchor="middle"
                  fill="#ffe7a3"
                  fontSize={11}
                  fontWeight={600}
                  style={{ pointerEvents: 'none', paintOrder: 'stroke' }}
                  stroke="#000"
                  strokeWidth={3}
                >
                  {label.split(' / ')[0]}
                </text>
                <title>{label}</title>
              </g>
            );
          })}
        </g>

        <g data-layer="external-nodes">
          {externalNodes.map((node) => {
            const { x, y } = pctToMapPixel(node.x!, node.y!, mapSize.width, mapSize.height);
            const selected = highlightId === node.id;
            const hovered = hoveredId === node.id;
            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  selectNode(node.id);
                }}
              >
                <circle
                  cx={x}
                  cy={y}
                  r={selected ? 28 : hovered ? 24 : 20}
                  fill={EXTERNAL_MAP_COLOR}
                  fillOpacity={EXTERNAL_MAP_OPACITY}
                  stroke={selected || hovered ? '#ffe6a3' : '#888'}
                  strokeWidth={selected ? 2.5 : 1.5}
                  vectorEffect="non-scaling-stroke"
                />
                <title>{node.region?.name || node.id}</title>
              </g>
            );
          })}
        </g>

        <g data-layer="theater-markers">
          {theaterNodes.map((node) => {
            const { x, y } = pctToMapPixel(node.x!, node.y!, mapSize.width, mapSize.height);
            const selected = highlightId === node.id;
            const hovered = hoveredId === node.id;
            const danger = (node.risk ?? 0) > 175;
            const fill = danger ? UNREST_MAP_COLOR : '#4f8a57';
            const label = node.label || node.region?.name || node.id;
            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  selectNode(node.id);
                }}
              >
                <circle
                  cx={x}
                  cy={y}
                  r={selected ? 22 : hovered ? 20 : 16}
                  fill={fill}
                  fillOpacity={0.85}
                  stroke={selected || hovered ? '#ffe6a3' : '#1a1a1a'}
                  strokeWidth={selected ? 2.5 : 1.5}
                  vectorEffect="non-scaling-stroke"
                />
                <text
                  x={x}
                  y={y - (selected ? 26 : 22)}
                  textAnchor="middle"
                  fill="#ffe7a3"
                  fontSize={11}
                  fontWeight={600}
                  style={{ pointerEvents: 'none', paintOrder: 'stroke' }}
                  stroke="#000"
                  strokeWidth={3}
                >
                  {label.split(' / ')[0]}
                </text>
                <title>{label}</title>
              </g>
            );
          })}
        </g>
      </MapViewport>

      {issues.length > 0 && (
        <div
          ref={issuesPanelRef as React.RefObject<HTMLDivElement>}
          style={{
            position: issuesPos ? 'fixed' : 'absolute',
            left: issuesPos?.left ?? 12,
            top: issuesPos?.top ?? 12,
            zIndex: 2,
            maxWidth: 'min(420px, 55vw)',
            borderRadius: 8,
            border: '1px solid rgba(255,215,0,0.35)',
            background: 'rgba(8,6,10,0.82)',
            color: '#ddd',
            fontSize: 11,
            lineHeight: 1.45,
            overflow: 'hidden',
          }}
        >
          <div
            {...issuesDragHandleProps}
            style={{
              ...issuesDragHandleProps.style,
              padding: '8px 10px 4px',
              color: '#ffd700',
              fontWeight: 600,
              fontSize: 12,
            }}
          >
            在办局势 · {issues.length}
          </div>
          <button
            type="button"
            onClick={onOpenSituation}
            style={{
              display: 'block',
              width: '100%',
              padding: '0 10px 8px',
              border: 'none',
              background: 'transparent',
              color: '#ddd',
              fontSize: 11,
              lineHeight: 1.45,
              cursor: onOpenSituation ? 'pointer' : 'default',
              textAlign: 'left',
            }}
          >
            {issues.slice(0, 3).map((issue) => (
              <div key={issue.id} style={{ marginBottom: 2 }}>
                <span style={{ color: '#ffe7a3' }}>{issue.title}</span>
                {issue.bar_value != null ? (
                  <span style={{ color: '#888', marginLeft: 6 }}>{issue.bar_value}</span>
                ) : null}
              </div>
            ))}
          </button>
        </div>
      )}

      {selectedNode && <MingMapIntelPanel node={selectedNode} onClose={closeIntel} />}
    </div>
  );
};
