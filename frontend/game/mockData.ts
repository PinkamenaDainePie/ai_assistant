import {
  NationState,
  Character,
  CourtEvent,
  Memorial,
  LogEntry,
} from './types';

/**
 * 每局开局应从该快照克隆再合并后端数值，避免沿用上局盘面。
 * 六维数值与后端 `numeric_system/fixed_initial_metrics.py` 中 FIXED_INITIAL_METRICS 对齐。
 */
export const mockNationState: NationState = {
  dynasty: '北宋',
  reignTitle: '熙宁',
  yearLabel: '熙宁二年 春',
  metrics: [
    { key: 'treasury', label: '国库储备', value: 48 },
    { key: 'taxStability', label: '税收稳定', value: 42 },
    { key: 'publicSupport', label: '民心', value: 55 },
    { key: 'scholarSupport', label: '士大夫支持', value: 38 },
    { key: 'emperorTrust', label: '皇帝信任', value: 60 },
    { key: 'externalPressure', label: '边患压力', value: 35 },
  ],
};

export function cloneInitialNationState(): NationState {
  return {
    ...mockNationState,
    metrics: mockNationState.metrics.map((m) => ({ ...m })),
  };
}

export const mockCharacters: Character[] = [
  {
    id: 'emperor',
    name: '宋神宗',
    title: '皇帝',
    faction: 'emperor',
    ideologyTags: ['锐意进取', '倚重新法'],
    avatarColor: '#b8860b',
    brief: '年轻而有改革欲望，但在祖宗法度与现实压力之间摇摆。',
  },
  {
    id: 'wanganshi',
    name: '王安石',
    title: '参知政事',
    faction: 'reformer',
    ideologyTags: ['理财', '重农抑商', '新法派'],
    avatarColor: '#c41e3a',
    brief: '坚信通过新法可以富国强兵，对反对声音不甚妥协。',
  },
  {
    id: 'simaguang',
    name: '司马光',
    title: '枢密副使',
    faction: 'conservative',
    ideologyTags: ['祖宗成法', '谨慎', '稳健财政'],
    avatarColor: '#666666',
    brief: '强调循序渐进，忧虑激进改革会动摇社稷根本。',
  },
];

export const mockCurrentEvent: CourtEvent = {
  id: 'event-001',
  title: '新法议——青苗法试行',
  summary:
    '天下多岁歉，农户乏本，市中高利贷猖獗。王安石请行青苗法，以官贷代私贷，既济农又利国。',
  speakers: [
    {
      characterId: 'wanganshi',
      text: '今民乏本，而富室乘之厚取其息，久之必生大患。请行青苗之法，以官本济之。',
    },
    {
      characterId: 'simaguang',
      text: '官与民争利，非长久之计。且下情难尽知，恐州县因循，反为民害。',
    },
    {
      characterId: 'emperor',
      text: '新法关乎社稷，卿等所言，朕皆记之。然终须一决，朕当何取舍？',
    },
  ],
  options: [
    {
      id: 'opt-1',
      label: '大范围推行青苗法',
      description: '急行新法于诸路，集中调度国用，以救时艰。',
      effects: [
        { metric: 'treasury', delta: 8 },
        { metric: 'taxStability', delta: 5 },
        { metric: 'publicSupport', delta: -4 },
        { metric: 'scholarSupport', delta: -6 },
      ],
      hint: '短期内国用充盈，但地方执行不一，易激化矛盾。',
    },
    {
      id: 'opt-2',
      label: '择数州试行，渐推诸路',
      description: '先选部分财赋要区试行，察其利弊，再图全面推行。',
      effects: [
        { metric: 'treasury', delta: 3 },
        { metric: 'taxStability', delta: 2 },
        { metric: 'publicSupport', delta: 1 },
        { metric: 'scholarSupport', delta: -2 },
      ],
      hint: '进取而不失稳健，利于观察实际效果。',
    },
    {
      id: 'opt-3',
      label: '暂缓推行，先整饬地方吏治',
      description: '以为法不在多，在于人。先治吏再论新法。',
      effects: [
        { metric: 'treasury', delta: -2 },
        { metric: 'taxStability', delta: -1 },
        { metric: 'publicSupport', delta: 3 },
        { metric: 'scholarSupport', delta: 4 },
      ],
      hint: '短期财政承压，但或可换取更稳固的政治基础。',
    },
  ],
  relatedMemorialId: 'mem-001',
};

export const mockMemorials: Memorial[] = [
  {
    id: 'mem-001',
    title: '江南转运司奏青苗本钱不足，请益帑藏',
    author: '江南东路转运使',
    fromRegion: '江南东路',
    urgency: 'high',
    status: 'unread',
    abstract: '本路比岁歉收，青苗本钱多靠折借他项，恐伤正供，请速议。',
  },
  {
    id: 'mem-002',
    title: '京畿诸县申民间怨声渐起',
    author: '京畿转运司',
    fromRegion: '京畿',
    urgency: 'medium',
    status: 'read',
    abstract: '有言青苗催科太急，州县以完额为急，未能恤民情状。',
  },
];

export const mockLogs: LogEntry[] = [
  {
    id: 'log-1',
    turn: 1,
    timeLabel: '熙宁二年 正月',
    summary: '议行青苗法于江南、两浙试验。',
    metricChanges: [
      { metric: 'treasury', delta: 3 },
      { metric: 'scholarSupport', delta: -2 },
    ],
  },
];

