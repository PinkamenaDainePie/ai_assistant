import { MetricDeltaPreview, NationMetricKey } from './types';

type KeywordRule = {
  kw: string;
  deltas: Partial<Record<NationMetricKey, number>>;
  reason: string;
};

const RULES: KeywordRule[] = [
  // 财政/税务
  {
    kw: '清查',
    deltas: { treasury: 2, taxStability: 2, scholarSupport: -1 },
    reason: '清查多能增收，但易触动既得利益',
  },
  {
    kw: '裁撤',
    deltas: { treasury: 2, publicSupport: -1, scholarSupport: -1 },
    reason: '裁撤可省用度，但会得罪相关群体',
  },
  {
    kw: '蠲免',
    deltas: { publicSupport: 3, treasury: -3, taxStability: -1 },
    reason: '蠲免税赋得民心但伤国用',
  },
  {
    kw: '加税',
    deltas: { treasury: 4, publicSupport: -3, taxStability: -1 },
    reason: '加税增收但激起民怨',
  },
  {
    kw: '赈济',
    deltas: { publicSupport: 3, treasury: -2 },
    reason: '赈济稳民心但耗费财政',
  },

  // 吏治/管理
  {
    kw: '严禁',
    deltas: { taxStability: 2, scholarSupport: 1, publicSupport: 1 },
    reason: '严禁横征可稳税制并得清议',
  },
  {
    kw: '整饬吏治',
    deltas: { taxStability: 2, scholarSupport: 2, treasury: -1 },
    reason: '整饬吏治利长期但短期见效慢且耗精力',
  },
  {
    kw: '查办',
    deltas: { scholarSupport: 1, emperorTrust: 1, publicSupport: 1 },
    reason: '查办贪墨能换取舆论与上意',
  },

  // 军事/边患
  {
    kw: '练兵',
    deltas: { externalPressure: -3, treasury: -2, publicSupport: -1 },
    reason: '练兵能缓边患但耗财扰民',
  },
  {
    kw: '增饷',
    deltas: { externalPressure: -2, treasury: -3, publicSupport: -1 },
    reason: '增饷提军心但财政承压',
  },
  {
    kw: '修堡',
    deltas: { externalPressure: -2, treasury: -2 },
    reason: '修防御工事有利边防但费帑',
  },

  // 政治/党争（用士大夫支持与皇帝信任粗略代替）
  {
    kw: '从宽',
    deltas: { publicSupport: 2, scholarSupport: -1, emperorTrust: -1 },
    reason: '从宽可缓冲民怨但易被指软弱',
  },
  {
    kw: '重惩',
    deltas: { emperorTrust: 2, publicSupport: -2, scholarSupport: -1 },
    reason: '重惩立威但可能反噬舆情',
  },
  {
    kw: '试行',
    deltas: { taxStability: 1, scholarSupport: 1, treasury: 1 },
    reason: '试行更稳健，利于观察与渐进',
  },
  {
    kw: '暂缓',
    deltas: { publicSupport: 1, scholarSupport: 2, treasury: -1 },
    reason: '暂缓更符合稳健预期但财政压力上升',
  },
];

const clampDelta = (n: number) => Math.max(-12, Math.min(12, n));

export function scoreEdictText(text: string): MetricDeltaPreview[] {
  const t = (text ?? '').trim();
  if (!t) return [];

  const accum = new Map<NationMetricKey, { delta: number; reasons: string[] }>();
  const add = (metric: NationMetricKey, delta: number, reason: string) => {
    const cur = accum.get(metric) ?? { delta: 0, reasons: [] };
    cur.delta += delta;
    if (reason) cur.reasons.push(reason);
    accum.set(metric, cur);
  };

  // 规则命中：关键词出现次数会叠加（简单但好调参）
  for (const r of RULES) {
    const hits = t.split(r.kw).length - 1;
    if (hits <= 0) continue;
    for (const [metric, delta] of Object.entries(r.deltas)) {
      add(metric as NationMetricKey, (delta ?? 0) * hits, r.reason);
    }
  }

  // “强硬/温和”语气：影响皇帝信任与民心
  const hardWords = ['务必', '严令', '即刻', '速行', '重惩', '严惩', '不得'];
  const softWords = ['酌', '暂', '缓', '商议', '体恤', '可否'];
  const hard = hardWords.reduce((n, w) => n + (t.includes(w) ? 1 : 0), 0);
  const soft = softWords.reduce((n, w) => n + (t.includes(w) ? 1 : 0), 0);
  if (hard > soft) {
    add('emperorTrust', 1, '措辞偏强硬，更合上意但易招怨');
    add('publicSupport', -1, '措辞偏强硬，更合上意但易招怨');
  } else if (soft > hard) {
    add('publicSupport', 1, '措辞偏温和，更得人心但显得不够强势');
    add('emperorTrust', -1, '措辞偏温和，更得人心但显得不够强势');
  }

  // 把结果输出为可展示预览
  const result: MetricDeltaPreview[] = [];
  for (const [metric, v] of accum.entries()) {
    const d = clampDelta(v.delta);
    if (d === 0) continue;
    result.push({ metric, delta: d, reasons: v.reasons.slice(0, 3) });
  }
  // 稳定排序：正向在前更像“收益”，也方便玩家扫一眼
  result.sort((a, b) => b.delta - a.delta);
  return result;
}

