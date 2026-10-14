const PROGRESS_LEVEL_CN: Record<string, string> = {
  verygood: '大进',
  good: '有进',
  normal: '平常',
  bad: '受挫',
  verybad: '大挫',
  resolved: '已成',
  failed: '败坏',
};

export function formatMingReportText(text: string): string {
  return String(text || '').replace(
    /(进展：\s*)([A-Za-z_]+)/g,
    (_, prefix: string, raw: string) => {
      const key = raw.toLowerCase();
      return `${prefix}${PROGRESS_LEVEL_CN[key] || raw}`;
    },
  );
}

export function formatMingDetailNarrative(text: string): string {
  let s = String(text || '');
  s = s.replace(/【圣意亲裁·结算优先】[^\n]*\n/, '── 本月圣意亲裁 ──\n');
  s = s.replace(/【[^】]*强制结算[^】]*】[^\n]*\n/, '── 钦定强制项 ──\n');
  s = s.replace(/<secret>\s*([\s\S]*?)\s*<\/secret>/g, (_, inner: string) => `【密】${inner}`);
  s = s.replace(/<\/?secret>/g, '');
  return formatMingReportText(s);
}
