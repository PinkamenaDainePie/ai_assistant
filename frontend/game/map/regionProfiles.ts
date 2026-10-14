export type RegionProfile = {
  description: string;
  populationWan: number;
  defenseLevel: number;
  terrain: string;
  focusTags: string[];
};

export const SONG_REGION_PROFILES: Record<string, RegionProfile> = {
  hebei: {
    description:
      '燕云以南屏障，边关烽燧相望。岁赋多供军需，边防与屯田并重；辽境压力常悬，是北疆第一要路。',
    populationWan: 320,
    defenseLevel: 8,
    terrain: '平原关塞',
    focusTags: ['边防', '屯田', '漕运'],
  },
  hedong: {
    description:
      '表里山河，控扼河东。煤铁盐利并出，亦为御辽侧翼；然地近边患，军镇与转运司事务繁剧。',
    populationWan: 280,
    defenseLevel: 7,
    terrain: '高原关隘',
    focusTags: ['盐铁', '边防', '转运'],
  },
  yongxingjun: {
    description:
      '关中形胜，渭水贯流。京畿西屏，屯粮备边；青苗、均输诸政在此试行时，关辅民情最为瞩目。',
    populationWan: 260,
    defenseLevel: 7,
    terrain: '关中平原',
    focusTags: ['青苗', '屯粮', '关中'],
  },
  qinfeng: {
    description:
      '秦陇襟喉，连接关中与河西。西夏扰边频繁，茶马互市与军需转运并重，边患压力常年偏高。',
    populationWan: 180,
    defenseLevel: 8,
    terrain: '陇右山地',
    focusTags: ['西夏', '茶马', '边防'],
  },
  jingji: {
    description:
      '京师所在，百司云集。漕运、盐铁、国用所系；新法推行与台谏论政皆由此枢机辐射诸路。',
    populationWan: 420,
    defenseLevel: 9,
    terrain: '京畿平原',
    focusTags: ['新法', '台谏', '国用'],
  },
  jingdong: {
    description:
      '齐鲁旧域，盐铁之利厚。漕运枢纽，农桑殷实；亦为新法推行与豪强博弈交织之地。',
    populationWan: 380,
    defenseLevel: 6,
    terrain: '平原滨海',
    focusTags: ['盐铁', '漕运', '豪强'],
  },
  jingxi: {
    description:
      '荆襄上游，连接中原与巴蜀。水陆转运便利，堤防与仓储为要；灾荒之年常需赈济调拨。',
    populationWan: 340,
    defenseLevel: 5,
    terrain: '江汉平原',
    focusTags: ['赈济', '仓储', '转运'],
  },
  jinghubei: {
    description:
      '鄂岳之间，控长江中游。兵家必争，水军与粮道所系；与荆南、淮南互有呼应。',
    populationWan: 290,
    defenseLevel: 6,
    terrain: '江湖丘陵',
    focusTags: ['水军', '粮道', '转运'],
  },
  jinghunan: {
    description:
      '湖湘腹地，稻作丰饶。然山民与洞蛮杂处，羁縻与经界之议时见；变法推行亦遇地方阻力。',
    populationWan: 310,
    defenseLevel: 5,
    terrain: '丘陵湖泽',
    focusTags: ['经界', '稻作', '羁縻'],
  },
  huainan: {
    description:
      '淮水南北，盐漕并重。连接中原与江南，灾伤与河工常在此交汇；青苗催科尤为敏感。',
    populationWan: 350,
    defenseLevel: 6,
    terrain: '淮河流域',
    focusTags: ['河工', '盐漕', '青苗'],
  },
  jiangnandong: {
    description:
      '江东财赋之区，丝帛盐利甲于天下。新法试行最早，亦是最早引发士绅议论之地。',
    populationWan: 480,
    defenseLevel: 5,
    terrain: '水乡平原',
    focusTags: ['财赋', '丝帛', '新法'],
  },
  jiangnanxi: {
    description:
      '江右内陆，林矿并富。经界与青苗推行时，山区丈量与胥吏催科矛盾尤为突出。',
    populationWan: 360,
    defenseLevel: 4,
    terrain: '丘陵山地',
    focusTags: ['经界', '青苗', '矿利'],
  },
  liangzhe: {
    description:
      '两浙沿海，市舶与盐场并盛。赋税重地，亦为新法派官监盐、均输调度的重点所在。',
    populationWan: 520,
    defenseLevel: 5,
    terrain: '沿海平原',
    focusTags: ['市舶', '盐场', '均输'],
  },
  fujian: {
    description:
      '闽地多山，海商活跃。盐铁与茶法并重，山区经界不易；与广南、两浙有海上贸易往来。',
    populationWan: 240,
    defenseLevel: 4,
    terrain: '山海交错',
    focusTags: ['茶法', '海商', '经界'],
  },
  guangdong: {
    description:
      '广南东路，岭南门户。市舶与盐铁之利厚，远离中原，诏令传达稍迟；蛮夷杂处，经略与赈济需并重。',
    populationWan: 220,
    defenseLevel: 5,
    terrain: '岭南滨海',
    focusTags: ['市舶', '经略', '盐铁'],
  },
  guangxi: {
    description:
      '广南西路，羁縻诸洞。边患与瘴疠并起，军需转运艰难；为西南经略与互市要区。',
    populationWan: 160,
    defenseLevel: 4,
    terrain: '岭南山地',
    focusTags: ['羁縻', '互市', '瘴疠'],
  },
  lizhou: {
    description:
      '川北门户，栈道险峻。连接关中与巴蜀，军粮转运与边防屯戍为常年要务。',
    populationWan: 140,
    defenseLevel: 6,
    terrain: '栈道山地',
    focusTags: ['栈道', '军粮', '边防'],
  },
  chengdufu: {
    description:
      '蜀中平原，天府之国。丝帛盐铁并富，相对远离边患；然新法推行仍牵动蜀地士绅与漕运。',
    populationWan: 380,
    defenseLevel: 6,
    terrain: '成都平原',
    focusTags: ['丝帛', '盐铁', '蜀地'],
  },
  zizhou: {
    description:
      '川东盐井密布，漕运入峡。盐铁之利厚，亦为巴蜀与荆湖转运节点。',
    populationWan: 200,
    defenseLevel: 5,
    terrain: '盐井丘陵',
    focusTags: ['盐铁', '漕运', '盐井'],
  },
  kuizhou: {
    description:
      '三峡咽喉，控扼巴蜀东出。水险路狭，军需与商货皆经于此；边事稍缓而转运常繁。',
    populationWan: 120,
    defenseLevel: 7,
    terrain: '三峡险隘',
    focusTags: ['三峡', '转运', '关隘'],
  },
};

export const REGION_STATUS_ZH: Record<string, string> = {
  normal: '平常',
  disaster: '受灾',
  occupied: '沦陷',
  revolt: '动荡',
};
