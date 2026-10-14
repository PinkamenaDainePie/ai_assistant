import * as THREE from 'three';
import { latLngToSphere } from './globeMath';

export type BorderFeatureProperties = {
  id: string;
  name: string;
  color: string;
  approx?: boolean;
};

export type BorderGeoJson = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    properties: BorderFeatureProperties;
    geometry: {
      type: 'Polygon' | 'MultiPolygon';
      coordinates: number[][][] | number[][][][];
    };
  }>;
};

export type ParsedBorder = {
  id: string;
  name: string;
  color: string;
  /** 外环 [lng, lat][] */
  ring: [number, number][];
};

function ringFromGeometry(geometry: BorderGeoJson['features'][0]['geometry']): [number, number][] {
  if (geometry.type === 'Polygon') {
    const ring = geometry.coordinates[0] as [number, number][];
    return ring.map(([lng, lat]) => [lng, lat]);
  }
  const multi = geometry.coordinates[0][0] as [number, number][];
  return multi.map(([lng, lat]) => [lng, lat]);
}

export function parseBorderGeoJson(data: BorderGeoJson): ParsedBorder[] {
  return data.features.map((feature) => ({
    id: feature.properties.id,
    name: feature.properties.name,
    color: feature.properties.color,
    ring: ringFromGeometry(feature.geometry),
  }));
}

export function ringCentroid(ring: [number, number][]): { lat: number; lng: number } {
  let sumLat = 0;
  let sumLng = 0;
  const n = Math.max(ring.length - 1, 1);
  for (let i = 0; i < n; i += 1) {
    sumLng += ring[i][0];
    sumLat += ring[i][1];
  }
  return { lat: sumLat / n, lng: sumLng / n };
}

/** 在相邻顶点间插值，使边界线更平滑、更精细 */
export function densifyRing(ring: [number, number][], steps = 4): [number, number][] {
  if (ring.length < 2) return ring;
  const closed = ring.length > 2 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1];
  const source = closed ? ring.slice(0, -1) : ring;
  const result: [number, number][] = [];

  for (let i = 0; i < source.length; i += 1) {
    const [lng0, lat0] = source[i];
    const [lng1, lat1] = source[(i + 1) % source.length];
    for (let s = 0; s < steps; s += 1) {
      const t = s / steps;
      result.push([lng0 + (lng1 - lng0) * t, lat0 + (lat1 - lat0) * t]);
    }
  }

  if (closed || (ring.length > 2 && ring[0][0] === ring[ring.length - 1][0])) {
    result.push([result[0][0], result[0][1]]);
  }
  return result;
}

/** 球面多边形网格（扇形三角化，适用于简化国界） */
export function createSphericalPolygonGeometry(
  ring: [number, number][],
  radius: number,
  lift = 0.004,
): THREE.BufferGeometry {
  const surfaceRadius = radius + lift;
  const { lat: cLat, lng: cLng } = ringCentroid(ring);
  const center = latLngToSphere(cLat, cLng, surfaceRadius);

  const edgeCount = ring.length - 1;
  const positions: number[] = [];
  const indices: number[] = [];

  positions.push(center.x, center.y, center.z);

  for (let i = 0; i < edgeCount; i += 1) {
    const [lng, lat] = ring[i];
    const p = latLngToSphere(lat, lng, surfaceRadius);
    positions.push(p.x, p.y, p.z);
  }

  for (let i = 1; i < edgeCount; i += 1) {
    indices.push(0, i, i + 1);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

export function createSphericalLineGeometry(
  ring: [number, number][],
  radius: number,
  lift = 0.006,
): THREE.BufferGeometry {
  const surfaceRadius = radius + lift;
  const dense = densifyRing(ring, 5);
  const points = dense.map(([lng, lat]) => latLngToSphere(lat, lng, surfaceRadius));
  return new THREE.BufferGeometry().setFromPoints(points);
}

/** 细管状边界线（WebGL 原生 line 无法真正变细，改用细圆柱管） */
export function createSphericalBorderTubeGeometry(
  ring: [number, number][],
  radius: number,
  lift = 0.0065,
  tubeRadius = 0.00075,
): THREE.BufferGeometry {
  const surfaceRadius = radius + lift;
  const dense = densifyRing(ring, 6);
  const points = dense.map(([lng, lat]) => latLngToSphere(lat, lng, surfaceRadius));
  if (points.length < 2) {
    return new THREE.BufferGeometry();
  }
  const curve = new THREE.CatmullRomCurve3(points, true, 'centripetal', 0.35);
  const tubularSegments = Math.max(points.length * 8, 64);
  return new THREE.TubeGeometry(curve, tubularSegments, tubeRadius, 5, true);
}
