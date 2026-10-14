/**
 * 默认地图图片路径（北宋场景 fallback）。
 * 运行时应优先从 store.scenarioId -> getScenario().mapImage 获取，
 * 以支持多场景地图切换。
 */
export const MAP_IMAGE_SRC_DEFAULT = '/maps/china_north_song.png';
/** @deprecated 使用 MAP_IMAGE_SRC_DEFAULT 或从场景包读取 */
export const MAP_IMAGE_SRC = MAP_IMAGE_SRC_DEFAULT;
export const MAP_IMAGE_WIDTH = 1672;
export const MAP_IMAGE_HEIGHT = 941;

export const MAP_MIN_SCALE = 0.6;
export const MAP_MAX_SCALE = 4;
export const MAP_INITIAL_SCALE = 1;

export const MAP_REGION_DEFAULT_FILL = 'rgba(212, 175, 55, 0.16)';
export const MAP_REGION_DEFAULT_STROKE = 'rgba(255, 230, 150, 0.45)';

export const MAP_REGION_HOVER_FILL = 'rgba(150, 150, 150, 0.48)';
export const MAP_REGION_HOVER_STROKE = 'rgba(255, 255, 255, 0.9)';

export const MAP_REGION_SELECTED_FILL = 'rgba(255, 184, 77, 0.45)';
export const MAP_REGION_SELECTED_STROKE = 'rgba(255, 220, 130, 1)';

export type MapFitMode = 'contain' | 'cover';
