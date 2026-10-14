export function formatMoney(value: number): string {
  const abs = Math.abs(value);
  const text =
    abs > 0 && abs < 1
      ? `${Number((abs * 10000).toFixed(2))}两`
      : `${Number(abs.toFixed(4))}万两`;
  return value < 0 ? `欠${text}` : text;
}

export function formatSignedMoney(value: number): string {
  if (value < 0) return `-${Math.abs(value)}万两`;
  return `${value > 0 ? '+' : ''}${formatMoney(value)}`;
}

export function regionMonthlyTax(region: { tax_per_turn?: number; tax_actual?: number }): number {
  const base = region.tax_actual ?? region.tax_per_turn ?? 0;
  return Math.max(0, Math.round(base));
}

export function unrestTone(unrest: number): string {
  if (unrest >= 70) return '#f5222d';
  if (unrest >= 45) return '#faad14';
  return '#52c41a';
}
