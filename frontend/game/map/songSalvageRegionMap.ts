/**
 * 北宋路分（mapRegions.ts）→ salvage 盘面 region id（regions.json）映射。
 * 引擎盘面仍用晚明 geographic id，宋图多边形 id 不同，点击需经此表解析。
 */
export const SONG_MAP_TO_SALVAGE_REGION: Record<string, string> = {
  jingji: 'beizhili',
  hebei: 'beizhili',
  hedong: 'shanxi',
  yongxingjun: 'shaanxi',
  qinfeng: 'shaanxi',
  jingdong: 'shandong',
  jingxi: 'henan',
  huainan: 'nanzhili',
  jinghubei: 'huguang',
  jinghunan: 'huguang',
  kuizhou: 'huguang',
  jiangnandong: 'nanzhili',
  jiangnanxi: 'jiangxi',
  liangzhe: 'zhejiang',
  fujian: 'fujian',
  guangdong: 'guangdong',
  guangxi: 'guangxi',
  lizhou: 'sichuan',
  chengdufu: 'sichuan',
  zizhou: 'sichuan',
};

export function salvageRegionIdForSongMap(mapRegionId: string): string {
  return SONG_MAP_TO_SALVAGE_REGION[mapRegionId] ?? mapRegionId;
}
