import type { MapPixelPoint } from './mapTypes';

export function pointsToSvgPolygonPoints(points: MapPixelPoint[]): string {
  return points.map((p) => `${p.x},${p.y}`).join(' ');
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
