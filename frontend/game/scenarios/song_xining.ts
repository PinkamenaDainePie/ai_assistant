import { Character, LogEntry, Memorial, NationState } from '../types';
import { buildSongMinisterCharacters } from './songMinisterRoster';

/** 北宋熙宁元年春 开局国家状态（与后端 fixed_initial_metrics.py 对齐） */
export const nationState: NationState = {
  dynasty: '北宋',
  reignTitle: '熙宁',
  yearLabel: '熙宁元年 春',
  metrics: [
    { key: 'treasury', label: '国库储备', value: 48 },
    { key: 'taxStability', label: '税收稳定', value: 42 },
    { key: 'publicSupport', label: '民心', value: 55 },
    { key: 'scholarSupport', label: '士大夫支持', value: 38 },
    { key: 'emperorTrust', label: '皇帝信任', value: 60 },
    { key: 'externalPressure', label: '边患压力', value: 35 },
  ],
};

/** 与 scenario_system/profiles.py character_ids（21 名大臣）对齐 */
export const characters: Character[] = [
  {
    id: 'emperor',
    name: '宋神宗',
    title: '皇帝',
    faction: 'emperor',
    ideologyTags: ['锐意进取', '倚重新法'],
    avatarColor: '#b8860b',
    consultable: false,
    brief: '年轻而有改革欲望，但在祖宗法度与现实压力之间摇摆。',
  },
  ...buildSongMinisterCharacters(),
];

export const memorials: Memorial[] = [
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

export const logs: LogEntry[] = [
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

export const mapImage = '/maps/china_north_song.png';
