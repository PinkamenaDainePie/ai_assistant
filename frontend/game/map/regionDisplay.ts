import type { NationMetric } from '../types';
import type { MapRegion } from './mapTypes';
import { MING_REGION_PROFILES } from './mingRegionProfiles';
import { REGION_STATUS_ZH, SONG_REGION_PROFILES, type RegionProfile } from './regionProfiles';

export type RegionDetailMetric = {
  label: string;
  value: string;
  tone?: 'good' | 'warn' | 'neutral';
};

export type RegionDetailView = {
  id: string;
  name: string;
  dynasty: string;
  description: string;
  statusLabel: string;
  metrics: RegionDetailMetric[];
  focusTags: string[];
};

type RegionStatusEntry = {
  status?: string;
  status_hint_zh?: string;
  visible?: boolean;
};

function clamp(n: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, n));
}

function hashSeed(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i += 1) {
    h = (h * 31 + id.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function readNationMetric(metrics: NationMetric[], key: string): number {
  return metrics.find((m) => m.key === key)?.value ?? 50;
}

function defaultProfile(regionId: string, regionName: string): RegionProfile {
  const seed = hashSeed(regionId);
  return {
    description: `${regionName}为当前版图一路分，暂无更详档案。可通过颁布诏令、赈济与边防任务影响该路局势。`,
    populationWan: 120 + (seed % 280),
    defenseLevel: 3 + (seed % 6),
    terrain: '待考',
    focusTags: ['朝政', '转运'],
  };
}

function toneByValue(v: number, invert = false): RegionDetailMetric['tone'] {
  if (invert) {
    if (v >= 70) return 'warn';
    if (v <= 35) return 'good';
    return 'neutral';
  }
  if (v >= 65) return 'good';
  if (v <= 35) return 'warn';
  return 'neutral';
}

function profileForRegion(regionId: string, regionName: string, dynasty: string): RegionProfile {
  if (dynasty === '明') {
    return MING_REGION_PROFILES[regionId] ?? defaultProfile(regionId, regionName);
  }
  return SONG_REGION_PROFILES[regionId] ?? defaultProfile(regionId, regionName);
}

export function buildRegionDetailView(args: {
  region: MapRegion;
  dynasty: string;
  nationMetrics: NationMetric[];
  regionStatus?: Record<string, RegionStatusEntry>;
}): RegionDetailView {
  const { region, dynasty, nationMetrics, regionStatus } = args;
  const profile = profileForRegion(region.id, region.name, dynasty);
  const seed = hashSeed(region.id);
  const statusEntry = regionStatus?.[region.id];
  const statusKey = String(statusEntry?.status ?? 'normal');
  const statusLabel =
    String(statusEntry?.status_hint_zh ?? '').trim() ||
    REGION_STATUS_ZH[statusKey] ||
    '平常';

  const publicBase = readNationMetric(nationMetrics, 'publicSupport');
  const borderBase = readNationMetric(nationMetrics, 'externalPressure');
  const publicSupport = clamp(
    Math.round(publicBase + (seed % 17) - 8 + (statusKey === 'disaster' ? -18 : 0)),
  );
  const unrest = clamp(
    Math.round(
      100 -
        publicSupport +
        (statusKey === 'occupied' ? 35 : 0) +
        (statusKey === 'disaster' ? 22 : 0) +
        borderBase * 0.08,
    ),
  );

  let disasterLabel = '无';
  let disasterTone: RegionDetailMetric['tone'] = 'good';
  if (statusKey === 'disaster') {
    disasterLabel = '灾伤';
    disasterTone = 'warn';
  } else if (statusKey === 'occupied') {
    disasterLabel = '敌占';
    disasterTone = 'warn';
  } else if (seed % 11 === 0) {
    disasterLabel = '局部歉收';
    disasterTone = 'neutral';
  }

  const metrics: RegionDetailMetric[] = [
    { label: '人口', value: `${profile.populationWan} 万`, tone: 'neutral' },
    { label: '民心', value: `${publicSupport}`, tone: toneByValue(publicSupport) },
    { label: '动乱', value: `${unrest}`, tone: toneByValue(unrest, true) },
    { label: '城防等级', value: `${profile.defenseLevel}`, tone: 'neutral' },
    { label: '当前灾害', value: disasterLabel, tone: disasterTone },
    { label: '区位', value: profile.terrain, tone: 'neutral' },
  ];

  if (statusEntry?.visible === false) {
    return {
      id: region.id,
      name: region.name,
      dynasty,
      description: '此地局势未明，情报尚未传至中枢。请先遣使巡视或待奏报到达。',
      statusLabel: '情报未明',
      metrics: [
        { label: '状态', value: statusLabel, tone: 'warn' },
        { label: '可见度', value: '模糊', tone: 'neutral' },
      ],
      focusTags: [],
    };
  }

  return {
    id: region.id,
    name: region.name,
    dynasty,
    description: region.description || profile.description,
    statusLabel,
    metrics,
    focusTags: profile.focusTags,
  };
}
