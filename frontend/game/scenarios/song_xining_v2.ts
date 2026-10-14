import { Character, LogEntry, Memorial, NationState } from '../types';
import { buildSongMinisterCharacters } from './songMinisterRoster';

/**
 * 北宋熙宁变法（salvage v2）— 课程门户预览。
 * 进局后以 :8010 salvage 四国指为准。
 */
export const nationState: NationState = {
  dynasty: '北宋',
  reignTitle: '熙宁',
  yearLabel: '熙宁元年 正月',
  metrics: [
    { key: 'treasury', label: '国库', value: 100 },
    { key: 'innerTreasury', label: '内库', value: 200 },
    { key: 'publicSupport', label: '民心', value: 50 },
    { key: 'emperorTrust', label: '皇威', value: 20 },
  ],
};

export const characters: Character[] = [
  {
    id: 'emperor',
    name: '宋神宗',
    title: '皇帝',
    faction: 'emperor',
    ideologyTags: ['锐意进取', '倚重新法'],
    avatarColor: '#b8860b',
    consultable: false,
    brief: '1068 年亲政求治，倚重王安石主持变法。',
  },
  ...buildSongMinisterCharacters(),
];

export const memorials: Memorial[] = [
  {
    id: 'mem-song-v2-001',
    title: '江南转运司奏青苗本钱不足，请益帑藏',
    author: '江南东路转运使',
    fromRegion: '江南东路',
    urgency: 'high',
    status: 'unread',
    abstract: '本路比岁歉收，青苗本钱多靠折借他项，恐伤正供，请速议。',
  },
  {
    id: 'mem-song-v2-002',
    title: '枢密院言西北边饷续解迟滞',
    author: '枢密院',
    fromRegion: '陕西路',
    urgency: 'medium',
    status: 'unread',
    abstract: '延州、环庆诸路警耗未息，边军请饷疏叠至，请速议补发。',
  },
  {
    id: 'mem-song-v2-003',
    title: '户部奏岁币支给与河漕修浚并见',
    author: '户部',
    fromRegion: '京师',
    urgency: 'medium',
    status: 'unread',
    abstract: '岁币、边饷、漕运岁修并举，太仓储备恐不足三月，请定优先级。',
  },
];

export const logs: LogEntry[] = [
  {
    id: 'log-song-v2-1',
    turn: 1,
    timeLabel: '熙宁元年 正月',
    summary: '王安石入相，议行青苗法于诸路试验。',
    metricChanges: [
      { metric: 'treasury', delta: 2 },
      { metric: 'publicSupport', delta: -2 },
    ],
  },
];

export const mapImage = '/maps/china_north_song.png';
export const mapWidth = 1672;
export const mapHeight = 941;
