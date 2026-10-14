/** 门户静态内容：财税史图谱节点、中西比较维度 */

export type AtlasNode = {
  id: string;
  era: string;
  title: string;
  year: string;
  summary: string;
  tone: 'purple' | 'blue' | 'green' | 'gold' | 'pink';
};

export const ATLAS_TIMELINE: AtlasNode[] = [
  {
    id: 'well_field',
    era: '先秦',
    title: '井田与贡赋',
    year: '前4世纪',
    summary: '土地国有观念与劳役贡纳，奠定早期财政伦理。',
    tone: 'green',
  },
  {
    id: 'salt_iron',
    era: '汉',
    title: '盐铁专卖',
    year: '前119',
    summary: '国家垄断关键物资，开启「干预 vs 放任」之辩。',
    tone: 'gold',
  },
  {
    id: 'liangshui',
    era: '唐',
    title: '两税法',
    year: '780',
    summary: '由人头转向资产与货币税，税源货币化关键一步。',
    tone: 'blue',
  },
  {
    id: 'xining',
    era: '宋',
    title: '熙宁新法',
    year: '1069',
    summary: '青苗、免役、市易、方田——商业财政与强兵并举。',
    tone: 'purple',
  },
  {
    id: 'yitiao',
    era: '明',
    title: '一条鞭法',
    year: '1581',
    summary: '赋役合一、银粮并收，简化征管链条。',
    tone: 'pink',
  },
];

export type CompareRow = {
  dimension: string;
  china: string;
  west: string;
};

export const COMPARE_ROWS: CompareRow[] = [
  {
    dimension: '财政汲取',
    china: '田赋、商税、榷货与漕运统筹；宋代高度商业化。',
    west: '罗马税赋、贡赋与军团供给；城邦商业信贷较早。',
  },
  {
    dimension: '货币信用',
    china: '铜钱、交子与钱陌制；国家与市场并用。',
    west: '贵金属有限；信贷多依托商业网络而非统一纸币。',
  },
  {
    dimension: '战争动员',
    china: '西北边饷、保甲保马；财政与军事深度绑定。',
    west: '军团给养与地方包税；扩张成本影响帝国财政结构。',
  },
  {
    dimension: '治理逻辑',
    china: '与士大夫共治天下；改革常系于朝局博弈。',
    west: '元老、教会与商业精英多元制衡（因地区而异）。',
  },
];

export const TUTOR_QUICK_PROMPTS = [
  '两税法与租庸调有何根本不同？',
  '熙宁变法「理财」与「聚敛」如何区分？',
  '宋代财政为何被称为「商业性财政」？',
  '中西比较：国家能力来自哪里？',
];

export const DIALOGUE_QUICK_PROMPTS = [
  '青苗法的财政逻辑与社会风险何在？',
  '与司马光分歧的核心是什么？',
  '均输、市易如何理解？',
];
