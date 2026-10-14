import { Character, LogEntry, Memorial, NationState } from '../types';
import { buildMingMinisterCharacters } from './mingMinisterRoster';

/**
 * 明代万历元年 — 课程门户预览（进局后以 salvage API 四国指为准）。
 */
export const nationState: NationState = {
  dynasty: '明',
  reignTitle: '万历',
  yearLabel: '万历元年 正月',
  metrics: [
    { key: 'treasury', label: '国库', value: 100 },
    { key: 'innerTreasury', label: '内库', value: 200 },
    { key: 'publicSupport', label: '民心', value: 50 },
    { key: 'emperorTrust', label: '皇威', value: 20 },
  ],
};

/** 与 zhangjuzheng_personas.json 全量对齐（皇帝不可问策） */
export const characters: Character[] = [
  {
    id: 'emperor',
    name: '万历帝',
    title: '皇帝',
    faction: 'emperor',
    ideologyTags: ['年幼冲主', '倚重首辅'],
    avatarColor: '#b8860b',
    consultable: false,
    brief: '年幼登基，政务委于首辅张居正，颇受其教导。',
  },
  ...buildMingMinisterCharacters(),
];

export const memorials: Memorial[] = [
  {
    id: 'mem-ming-001',
    title: '户部奏太仓银两告急',
    author: '户部尚书',
    fromRegion: '京师',
    urgency: 'high',
    status: 'unread',
    abstract: '太仓积储已不足三月用度，各省催解迟缓，请亟发上谕督催。',
  },
  {
    id: 'mem-ming-002',
    title: '御史奏各省拖欠考成甚众',
    author: '都察院',
    fromRegion: '各省',
    urgency: 'medium',
    status: 'unread',
    abstract: '新行考成法未满一载，各省因循者众，请严申处置。',
  },
];

export const logs: LogEntry[] = [
  {
    id: 'log-ming-1',
    turn: 1,
    timeLabel: '万历元年 正月',
    summary: '张居正奏请推行考成法，整饬官员问责。',
    metricChanges: [
      { metric: 'scholarSupport', delta: -3 },
      { metric: 'emperorTrust', delta: 2 },
    ],
  },
];

/** 万历朝疆域图（1448×1086） */
export const mapImage = '/maps/china_ming_wanli.png';
export const mapWidth = 1448;
export const mapHeight = 1086;
