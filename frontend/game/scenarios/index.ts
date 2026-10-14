/**
 * 场景注册表（前端）
 *
 * 每个场景是一个独立模块，包含 nationState / characters / memorials / logs / mapImage。
 * 新增场景只需：
 *   1. 创建 <scenario_id>.ts 并导出上述字段
 *   2. 在 SCENARIOS 中追加一条记录（含 runtimeKind）
 */
import { Character, LogEntry, Memorial, NationState } from '../types';

export type RuntimeKind = 'quarter' | 'salvage';

export type ScenarioId = 'song_xining' | 'song_xining_v2' | 'ming_wanli';

export type MapRegionProfile = 'song' | 'ming';

export interface ScenarioData {
  id: ScenarioId;
  runtimeKind: RuntimeKind;
  labelZh: string;
  descriptionZh: string;
  /** 后端表格根目录（相对项目根，如 biaoge/song）；salvage 场景可为空 */
  dataRoot: string;
  /** 与 ming-salvage-sim content/scenarios/ 目录名一致 */
  salvageScenarioId?: string;
  /** salvage 场景菜单副标题（可选） */
  salvageMenuSubtitle?: string;
  /**
   * 是否出现在剧本选择列表。默认 true。
   * 经典季度 `song_xining` 已下架入口，仍保留注册以便旧存档/教师记录解析。
   */
  listed?: boolean;
  mapRegionProfile?: MapRegionProfile;
  mapWidth?: number;
  mapHeight?: number;
  nationState: NationState;
  characters: Character[];
  memorials: Memorial[];
  logs: LogEntry[];
  mapImage: string;
}

import * as songXining from './song_xining';
import * as songXiningV2 from './song_xining_v2';
import * as mingWanli from './ming_wanli';

export const SCENARIOS: Record<string, ScenarioData> = {
  song_xining: {
    id: 'song_xining',
    runtimeKind: 'quarter',
    listed: false,
    labelZh: '熙宁变法（经典·已下架）',
    descriptionZh:
      '熙宁元年春，宋神宗即位求治，议变祖宗之法。\n在财政困窘、边患频仍的北宋中期，权衡改革步伐与政局稳定。',
    dataRoot: 'biaoge/song',
    mapRegionProfile: 'song',
    nationState: songXining.nationState,
    characters: songXining.characters,
    memorials: songXining.memorials,
    logs: songXining.logs,
    mapImage: songXining.mapImage,
  },
  song_xining_v2: {
    id: 'song_xining_v2',
    runtimeKind: 'salvage',
    salvageScenarioId: 'song_xining_v2',
    salvageMenuSubtitle: '新引擎 · 月度推演',
    labelZh: '熙宁变法',
    descriptionZh:
      '熙宁元年，王安石主持青苗、市易、方田诸新法。\n在财政困窘、边患频仍的北宋中期，以月度模拟体验变法推进。',
    dataRoot: '',
    mapRegionProfile: 'song',
    mapWidth: songXiningV2.mapWidth,
    mapHeight: songXiningV2.mapHeight,
    nationState: songXiningV2.nationState,
    characters: songXiningV2.characters,
    memorials: songXiningV2.memorials,
    logs: songXiningV2.logs,
    mapImage: songXiningV2.mapImage,
  },
  ming_wanli: {
    id: 'ming_wanli',
    runtimeKind: 'salvage',
    salvageScenarioId: 'ming_wanli',
    salvageMenuSubtitle: '月度推演',
    labelZh: '万历改革',
    descriptionZh:
      '万历初年，张居正以内阁首辅身份主持考成法与一条鞭法改革。\n在吏治积弊、财政危机的明代中期，推动制度革新。',
    dataRoot: 'biaoge/ming',
    mapRegionProfile: 'ming',
    mapWidth: mingWanli.mapWidth,
    mapHeight: mingWanli.mapHeight,
    nationState: mingWanli.nationState,
    characters: mingWanli.characters,
    memorials: mingWanli.memorials,
    logs: mingWanli.logs,
    mapImage: mingWanli.mapImage,
  },
};

export function getScenario(id: string): ScenarioData | undefined {
  return SCENARIOS[id];
}

/** 剧本选择页可选列表（已下架入口不出现） */
export function listScenarios(): ScenarioData[] {
  return Object.values(SCENARIOS).filter((s) => s.listed !== false);
}

export function getScenarioRuntime(id: ScenarioId | null | undefined): RuntimeKind | null {
  if (!id) return null;
  return getScenario(id)?.runtimeKind ?? null;
}

export function isSalvageScenario(id: ScenarioId | string | null | undefined): boolean {
  return getScenarioRuntime(id as ScenarioId | null) === 'salvage';
}

export function resolveSalvageScenarioId(id: ScenarioId): string {
  const scenario = getScenario(id);
  if (!scenario) return id;
  return scenario.salvageScenarioId || id;
}

/** 解析传给 FastAPI 的 root_dir（可用 .env 覆盖为绝对路径） */
export function resolveScenarioDataRoot(scenarioId: ScenarioId | null | undefined): string {
  if (!scenarioId) return '';
  const scenario = getScenario(scenarioId);
  if (!scenario) return '';
  if (typeof window !== 'undefined') {
    const envKey =
      scenarioId === 'song_xining'
        ? process.env.NEXT_PUBLIC_SONG_DATA_ROOT
        : process.env.NEXT_PUBLIC_MING_DATA_ROOT;
    if (envKey?.trim()) return envKey.trim().replace(/\\/g, '/');
  }
  return scenario.dataRoot;
}

/** salvage 盘面 player_power_id / controlled_by 判定 */
export function getPlayerPowerId(scenarioId: ScenarioId | string | null | undefined): string {
  return resolvePlayerPowerId({ scenarioId });
}

/** 多信号合并判定玩家势力（防 scenarioId 与后端激活剧本不一致） */
export function resolvePlayerPowerId(opts?: {
  scenarioId?: ScenarioId | string | null;
  salvageScenarioId?: string | null;
  dynasty?: string | null;
  gameYear?: number | null;
}): string {
  const sid = (opts?.scenarioId || opts?.salvageScenarioId || '').trim();
  if (sid === 'song_xining_v2' || sid === 'song_xining') return 'song';
  const dynasty = (opts?.dynasty || '').trim();
  if (dynasty.includes('宋')) return 'song';
  const year = Number(opts?.gameYear);
  if (Number.isFinite(year) && year >= 1068 && year <= 1086) return 'song';
  return 'ming';
}

export function isPlayerControlledRegion(
  controlledBy: string | undefined | null,
  scenarioId: ScenarioId | string | null | undefined,
): boolean {
  const power = (controlledBy || getPlayerPowerId(scenarioId)).trim();
  return power === getPlayerPowerId(scenarioId);
}

export function cloneScenarioNationState(scenarioId: ScenarioId): NationState {
  const scenario = getScenario(scenarioId);
  if (!scenario) return { dynasty: '', reignTitle: '', yearLabel: '', metrics: [] };
  const ns = scenario.nationState;
  return {
    ...ns,
    metrics: ns.metrics.map((m) => ({ ...m })),
  };
}

/** salvage 目录 id → 前端 ScenarioId */
export function resolveFrontendScenarioFromSalvageId(salvageId: string): ScenarioId {
  const direct = getScenario(salvageId);
  if (direct) return direct.id;
  for (const scenario of Object.values(SCENARIOS)) {
    if (scenario.salvageScenarioId === salvageId) return scenario.id;
  }
  return 'ming_wanli';
}

export function labelSalvageScenario(salvageId: string): string {
  return getScenario(resolveFrontendScenarioFromSalvageId(salvageId))?.labelZh || salvageId;
}
