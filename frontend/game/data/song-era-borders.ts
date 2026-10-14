import type { BorderGeoJson } from '@/game/globeGeo';

/**
 * 约 11 世纪东亚核心政权粗略国界（示意，非精确 GIS）。
 * 坐标 [lng, lat]，参考宋辽西夏大理并存格局；适合 3D 地球视觉展示。
 */
export const SONG_ERA_BORDERS: BorderGeoJson = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { id: 'song', name: '北宋', color: '#7c3aed', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [104.2, 21.8], [107.5, 21.4], [110.0, 20.4], [112.5, 21.2], [115.0, 22.5],
          [118.5, 24.0], [120.8, 27.5], [121.8, 31.0], [121.5, 34.0], [120.2, 36.5],
          [118.5, 37.2], [116.5, 37.5], [114.0, 36.9], [111.5, 36.2], [109.5, 35.7],
          [107.8, 35.4], [106.0, 34.6], [105.0, 33.2], [103.8, 31.8], [102.7, 30.0],
          [102.2, 28.3], [103.0, 25.8], [104.2, 21.8],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'liao', name: '辽', color: '#2563eb', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [106.0, 38.8], [109.5, 39.8], [113.5, 40.4], [116.2, 40.1], [118.5, 39.5],
          [121.8, 40.4], [124.5, 41.8], [127.0, 43.5], [130.5, 45.2], [132.0, 47.8],
          [129.5, 50.5], [125.5, 52.5], [120.0, 53.2], [114.0, 51.8], [108.5, 49.5],
          [104.0, 46.5], [101.5, 43.2], [102.5, 40.5], [106.0, 38.8],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'xixia', name: '西夏', color: '#eab308', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [97.0, 37.2], [100.0, 39.0], [103.0, 40.4], [106.5, 40.0], [108.8, 38.5],
          [108.3, 36.5], [106.2, 35.0], [103.5, 34.6], [100.8, 35.4], [98.2, 36.0],
          [97.0, 37.2],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'dali', name: '大理', color: '#16a34a', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [97.5, 21.5], [99.8, 21.0], [102.5, 21.8], [104.0, 23.5], [104.0, 25.5],
          [102.5, 27.5], [100.0, 28.5], [97.8, 27.0], [96.5, 24.8], [97.5, 21.5],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'tubo', name: '吐蕃诸部', color: '#a855f7', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [78.0, 29.0], [82.0, 31.0], [87.0, 32.5], [92.5, 33.5], [98.5, 34.5],
          [102.5, 33.0], [103.0, 30.0], [100.0, 28.5], [95.0, 27.5], [90.0, 27.0],
          [84.0, 27.5], [80.0, 28.0], [78.0, 29.0],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'goryeo', name: '高丽', color: '#06b6d4', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [124.5, 37.8], [126.0, 36.0], [128.0, 35.0], [129.5, 36.2], [130.2, 38.5],
          [129.2, 41.5], [127.0, 42.4], [125.0, 40.8], [124.5, 37.8],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'japan', name: '日本', color: '#ef4444', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [129.5, 31.0], [131.5, 30.8], [134.0, 32.5], [136.5, 34.0], [139.0, 35.0],
          [141.5, 38.5], [142.5, 41.5], [140.5, 43.5], [137.5, 40.5], [135.0, 37.0],
          [132.0, 34.0], [130.0, 32.5], [129.5, 31.0],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'dai_viet', name: '大越', color: '#22c55e', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [102.0, 20.5], [104.0, 21.8], [106.5, 21.8], [108.0, 20.8], [107.8, 18.8],
          [106.5, 17.0], [104.8, 17.5], [103.0, 18.8], [102.0, 20.5],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'champa', name: '占城', color: '#f97316', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [106.5, 16.8], [108.5, 16.5], [109.5, 14.5], [109.2, 12.0], [108.2, 10.5],
          [106.8, 11.5], [106.2, 14.0], [106.5, 16.8],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'pagan', name: '蒲甘', color: '#b45309', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [92.5, 16.0], [94.5, 14.5], [97.5, 15.0], [99.5, 18.0], [99.0, 22.5],
          [97.0, 25.0], [94.5, 24.0], [93.0, 21.0], [92.5, 16.0],
        ]],
      },
    },
    {
      type: 'Feature',
      properties: { id: 'khmer', name: '高棉', color: '#84cc16', approx: true },
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [100.0, 10.0], [102.5, 9.5], [105.5, 10.5], [107.0, 12.0], [106.0, 14.5],
          [104.0, 15.5], [101.0, 15.0], [99.5, 13.0], [100.0, 10.0],
        ]],
      },
    },
  ],
};
