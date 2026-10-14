/** 约 11 世纪东亚核心政权财税与经济概况（配合 song-era-borders 国界 id） */

export type WorldPolityProfile = {
  id: string;
  name: string;
  periodLabel: string;
  lat: number;
  lng: number;
  markerColor: string;
  regime: string;
  relationToSong: string;
  fiscalSystem: {
    title: string;
    revenue: string[];
    currency: string;
    institutions: string[];
  };
  economy: {
    trade: string;
    population: string;
    highlights: string[];
  };
  compareWest?: string;
};

export const WORLD_POLITIES: WorldPolityProfile[] = [
  {
    id: 'song',
    name: '北宋',
    periodLabel: '神宗熙宁年间（约 1070）',
    lat: 30,
    lng: 115,
    markerColor: '#7c3aed',
    regime: '中央集权帝制',
    relationToSong: '本课程核心研究对象',
    fiscalSystem: {
      title: '两税法遗制 + 高度商业化的国家财政',
      revenue: ['两税（田亩与丁庸折纳）', '商税、关市税', '盐铁茶酒专卖（榷货）', '漕运、和籴与常平仓'],
      currency: '铜钱为主；四川交子为早期纸币；钱陌制复杂',
      institutions: ['三司', '诸路转运司', '市舶司', '榷场（对辽、西夏）'],
    },
    economy: {
      trade: '大运河与东南海贸；江南为财赋重心',
      population: '约六千万至一亿量级（学界估算）',
      highlights: ['商业化程度高', '纸币萌芽', '熙宁新法期财政实验密集'],
    },
  },
  {
    id: 'liao',
    name: '辽',
    periodLabel: '圣宗—兴宗年间（约 1070）',
    lat: 46,
    lng: 118,
    markerColor: '#2563eb',
    regime: '游牧—定居二元帝国',
    relationToSong: '北方强邻；澶渊之盟后榷场互市',
    fiscalSystem: {
      title: '南北面官分治 + 租赋与畜牧税',
      revenue: ['田租、户税', '畜牧与渔猎贡纳', '榷场互市税', '属国贡赋'],
      currency: '宋钱、自铸钱与实物并行',
      institutions: ['南北面官制', '榷场（对宋）'],
    },
    economy: {
      trade: '与宋、西夏、草原部族多边贸易',
      population: '游牧与定居人口并存',
      highlights: ['燕云农业区为税源', '骑兵动员成本嵌入财政'],
    },
  },
  {
    id: 'xixia',
    name: '西夏',
    periodLabel: '惠宗—崇宗年间（约 1070）',
    lat: 37,
    lng: 103,
    markerColor: '#eab308',
    regime: '党项贵族国家',
    relationToSong: '西北边患与榷场伙伴',
    fiscalSystem: {
      title: '土地、畜牧与榷场贸易并重',
      revenue: ['田亩与畜牧税', '榷场互市', '盐池专卖'],
      currency: '自铸钱与宋钱并用',
      institutions: ['三司（西夏）', '榷场'],
    },
    economy: {
      trade: '茶马互市、河西走廊通道',
      population: '党项与汉、吐蕃等族杂居',
      highlights: ['盐池专卖', '对宋依赖榷场获茶帛'],
    },
  },
  {
    id: 'dali',
    name: '大理',
    periodLabel: '段氏统治（约 1070）',
    lat: 24,
    lng: 101,
    markerColor: '#16a34a',
    regime: '地方王国',
    relationToSong: '西南朝贡与茶马贸易',
    fiscalSystem: {
      title: '地方贡赋 + 盐井与马匹贸易',
      revenue: ['田赋与徭役', '盐井专卖', '马匹出口', '朝贡交换'],
      currency: '贝币、银、实物与宋钱并用',
      institutions: ['地方土司式管理', '盐井官营'],
    },
    economy: {
      trade: '西南丝路、茶马古道节点',
      population: '洱海周边为核心区',
      highlights: ['盐利为支柱', '马匹出口'],
    },
  },
  {
    id: 'tubo',
    name: '吐蕃诸部',
    periodLabel: '分裂诸部（约 1070）',
    lat: 31,
    lng: 91,
    markerColor: '#a855f7',
    regime: '部落联盟与地方政权',
    relationToSong: '西南、西北间接往来；茶马通道',
    fiscalSystem: {
      title: '部落贡纳 + 畜牧与贸易',
      revenue: ['畜牧税与贡纳', '盐、马匹贸易', '寺院经济'],
      currency: '实物、贝币与宋钱并用',
      institutions: ['部落首领', '寺院领'],
    },
    economy: {
      trade: '青唐茶马、对宋夏转口',
      population: '高原牧区为主，精确数字难考',
      highlights: ['马匹与皮毛输出', '寺院占有大量资源'],
    },
  },
  {
    id: 'goryeo',
    name: '高丽',
    periodLabel: '文宗—睿宗年间（约 1070）',
    lat: 39,
    lng: 127,
    markerColor: '#06b6d4',
    regime: '朝贡王国',
    relationToSong: '朝贡贸易；受辽、宋双重影响',
    fiscalSystem: {
      title: '田柴科 + 贡赋与商税',
      revenue: ['田柴科', '商税、关市', '朝贡与回赐'],
      currency: '自铸钱与宋钱并用',
      institutions: ['中央六部', '市舶'],
    },
    economy: {
      trade: '对宋输出人参、皮毛；输入丝绸瓷器',
      population: '半岛约数百万量级',
      highlights: ['农业与手工业并重', '朝贡体系嵌入外交'],
    },
  },
  {
    id: 'japan',
    name: '日本',
    periodLabel: '平安时代（约 1070）',
    lat: 36,
    lng: 137,
    markerColor: '#ef4444',
    regime: '律令遗制 + 庄园制',
    relationToSong: '间接贸易；宋钱大量流入',
    fiscalSystem: {
      title: '庄园制下租庸调残存',
      revenue: ['庄园贡纳', '关市税（有限）', '院政与寺社领'],
      currency: '宋钱为主要流通货币',
      institutions: ['太政官（名义）', '庄园领主', '博多港'],
    },
    economy: {
      trade: '宋日贸易经博多；输入丝绸、瓷器',
      population: '约数百万至千万量级',
      highlights: ['庄园制削弱中央税基', '宋钱改变货币生态'],
    },
  },
  {
    id: 'dai_viet',
    name: '大越',
    periodLabel: '李朝（约 1070）',
    lat: 19.5,
    lng: 105,
    markerColor: '#22c55e',
    regime: '独立地方王朝',
    relationToSong: '南方边陲；朝贡与边贸',
    fiscalSystem: {
      title: '田赋、人头与地方贡纳',
      revenue: ['田亩税', '丁税与徭役', '盐铁', '对宋朝贡'],
      currency: '铜钱、实物与本地货币并用',
      institutions: ['中央六部', '地方州府'],
    },
    economy: {
      trade: '红河三角洲稻作；与宋、占城海贸',
      population: '核心区人口密集',
      highlights: ['稻作与水利', '军费占比高'],
    },
  },
  {
    id: 'champa',
    name: '占城',
    periodLabel: '占城国（约 1070）',
    lat: 14,
    lng: 108,
    markerColor: '#f97316',
    regime: '印度化王国',
    relationToSong: '南海朝贡与香料贸易',
    fiscalSystem: {
      title: '贡赋 + 港口抽分',
      revenue: ['田赋', '港口贸易抽分', '朝贡（对宋）'],
      currency: '金银、实物与外来铜钱',
      institutions: ['王廷', '港口商馆'],
    },
    economy: {
      trade: '香料、象牙、南海航线节点',
      population: '沿海与河谷为主',
      highlights: ['朝贡贸易繁荣', '与宋、大越并立南海'],
    },
  },
  {
    id: 'pagan',
    name: '蒲甘',
    periodLabel: '蒲甘王朝（约 1070）',
    lat: 20,
    lng: 96,
    markerColor: '#b45309',
    regime: '佛教王国',
    relationToSong: '间接往来；西南陆路贸易',
    fiscalSystem: {
      title: '土地税 + 寺院经济',
      revenue: ['田赋', '寺院田产', '宝石与贸易'],
      currency: '银币、实物为主',
      institutions: ['王廷', '寺院'],
    },
    economy: {
      trade: '伊洛瓦底江流域；宝石、稻作',
      population: '缅甸中部为核心',
      highlights: ['佛教寺院占有大量土地', '与大理、宋间接贸易'],
    },
  },
  {
    id: 'khmer',
    name: '高棉',
    periodLabel: '吴哥时期（约 1070）',
    lat: 12,
    lng: 103,
    markerColor: '#84cc16',
    regime: '印度化帝国',
    relationToSong: '间接认知；中南半岛贸易网络',
    fiscalSystem: {
      title: '贡赋 + 水利农业财政',
      revenue: ['田赋（水利稻作）', '劳役', '属国贡纳'],
      currency: '实物与贵金属并用',
      institutions: ['王廷', '地方官吏'],
    },
    economy: {
      trade: '湄公河流域；与占城、大越竞争南海影响',
      population: '吴哥周边为核心',
      highlights: ['水利稻作支撑国家', '寺院与王权并重'],
    },
  },
];

export function getPolityById(id: string): WorldPolityProfile | undefined {
  return WORLD_POLITIES.find((p) => p.id === id);
}
