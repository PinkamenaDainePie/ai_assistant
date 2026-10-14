import type { CSSProperties } from 'react';
import type { SalvageMapNode, SalvageRegion } from './salvageStateTypes';

export const MING_INK_FILL = 'rgba(180, 150, 80, 0.18)';
export const MING_INK_STROKE = 'rgba(90, 70, 40, 0.45)';
export const MING_INK_UNREST_FILL = 'rgba(184, 58, 49, 0.20)';
export const MING_INK_EXTERNAL_FILL = 'rgba(95, 99, 102, 0.22)';
export const MING_INK_HOVER_FILL = 'rgba(180, 150, 80, 0.28)';
export const MING_INK_HOVER_STROKE = 'rgba(120, 100, 60, 0.65)';
export const MING_INK_SELECTED_FILL = 'rgba(120, 170, 90, 0.22)';
export const MING_INK_SELECTED_STROKE = 'rgba(245, 235, 190, 0.9)';

/** @deprecated 使用 MING_INK_* 水墨配色 */
export const MING_MAP_COLOR = '#4f8a57';
export const UNREST_MAP_COLOR = '#b83a31';
export const EXTERNAL_MAP_COLOR = '#5f6366';
export const UNREST_DANGER_THRESHOLD = 60;
export const MING_MAP_OPACITY = 0.18;
export const EXTERNAL_MAP_OPACITY = 0.22;
export const THEATER_ONLY_REGION_IDS = new Set(['liaodong']);

/** salvage mapPaths REGION_PATH_GROUPS 中除省外的邻区（主图层、按 controlled_by 着色） */
export const SALVAGE_REGION_PATH_NEIGHBOR_IDS = new Set([
  'korea',
  'taiwan',
  'nurgan',
  'mongol_chahar',
  'jianzhou',
  'shenyang_liaoyang',
]);

/** salvage mapPaths viewBox → 万历底图 1448×1086 */
export const MING_SALVAGE_VIEWBOX = { x: 840, y: 82, w: 276, h: 206 } as const;
export const MING_MAP_PIXEL_SIZE = { w: 1448, h: 1086 } as const;

export function mingSalvagePathTransform(): string {
  const sx = MING_MAP_PIXEL_SIZE.w / MING_SALVAGE_VIEWBOX.w;
  const sy = MING_MAP_PIXEL_SIZE.h / MING_SALVAGE_VIEWBOX.h;
  const tx = -MING_SALVAGE_VIEWBOX.x * sx;
  const ty = -MING_SALVAGE_VIEWBOX.y * sy;
  return `matrix(${sx} 0 0 ${sy} ${tx} ${ty})`;
}

export function svgViewBoxToMapPixel(sx: number, sy: number): { x: number; y: number } {
  const scaleX = MING_MAP_PIXEL_SIZE.w / MING_SALVAGE_VIEWBOX.w;
  const scaleY = MING_MAP_PIXEL_SIZE.h / MING_SALVAGE_VIEWBOX.h;
  return {
    x: (sx - MING_SALVAGE_VIEWBOX.x) * scaleX,
    y: (sy - MING_SALVAGE_VIEWBOX.y) * scaleY,
  };
}

const POWER_ID_CN: Record<string, string> = {
  ming: '大明',
  song: '北宋',
  liao: '辽',
  xixia: '西夏',
  houjin: '后金',
  mongol: '蒙古',
  korea: '朝鲜',
  bandits: '流寇',
  dutch: '荷兰东印度公司',
  japan: '日本',
};

export function labelPower(id: string | undefined | null): string {
  if (!id) return '—';
  return POWER_ID_CN[id] || id;
}

export function pctToMapPixel(
  xPct: number,
  yPct: number,
  mapWidth: number,
  mapHeight: number,
): { x: number; y: number } {
  return {
    x: (xPct / 100) * mapWidth,
    y: (yPct / 100) * mapHeight,
  };
}

export function getMingRegionMapStyle(
  region: SalvageRegion | undefined,
  playerPower = 'ming',
): {
  fill: string;
  stroke: string;
  opacity: number;
} {
  const controlled = region?.controlled_by || playerPower;
  if (controlled !== playerPower) {
    return { fill: MING_INK_EXTERNAL_FILL, stroke: MING_INK_STROKE, opacity: 1 };
  }
  const unrest = region?.unrest ?? 0;
  if (unrest > UNREST_DANGER_THRESHOLD) {
    return { fill: MING_INK_UNREST_FILL, stroke: MING_INK_STROKE, opacity: 1 };
  }
  return { fill: MING_INK_FILL, stroke: MING_INK_STROKE, opacity: 1 };
}

export function getMapIntelStyle(node: SalvageMapNode): CSSProperties {
  const x = node.x ?? 50;
  const y = node.y ?? 50;
  const left = Math.min(82, Math.max(18, x));
  const horizontal = x > 66 ? '-100%' : x < 34 ? '0' : '-50%';
  const style: CSSProperties = {
    left: `${left}%`,
    transform: `translateX(${horizontal})`,
    maxHeight: 'calc(100vh - 24px)',
  };
  if (y > 50) {
    style.bottom = '12px';
    style.top = 'auto';
  } else {
    style.top = '12px';
    style.bottom = 'auto';
  }
  return style;
}

export function mapNodeTitle(node: SalvageMapNode): string {
  const display = node.region?.display_name?.trim();
  if (display) return display;
  if (node.region?.name) return node.region.name;
  if (node.label) return node.label;
  return node.id;
}
