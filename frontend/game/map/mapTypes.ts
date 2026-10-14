/** 地图几何点：基于底图像素坐标系（与 game/types 的 MapPoint 区分） */
export interface MapPixelPoint {
  x: number;
  y: number;
}

export type MapRegionType = 'route' | 'prefecture' | 'state' | 'city' | 'province' | 'custom';

export interface MapRegionMetric {
  label: string;
  value: string | number;
  unit?: string;
}

export interface MapRegion {
  id: string;
  name: string;
  type?: MapRegionType;
  /** 多边形顶点，基于底图像素坐标 */
  points: MapPixelPoint[];
  /** 标签锚点，基于底图像素坐标 */
  centroid: MapPixelPoint;
  description?: string;
  metrics?: MapRegionMetric[];
  enabled?: boolean;
  color?: string;
  /** 单条 SVG path（viewBox 坐标系，由层内 transform 映射到底图） */
  path?: string;
  /** salvage mapPaths 原版 path 列表（viewBox 840 82 276 206） */
  svgPaths?: string[];
  /** province = 大明省；external = 外邦/边地 polygon */
  kind?: 'province' | 'external';
}
