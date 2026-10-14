export type CourtPct = { px: number; py: number };

export const LEFT_ANCHOR = { near: { px: 0.077, py: 0.532 }, far: { px: 0.377, py: 0.066 } };
export const RIGHT_ANCHOR = { near: { px: 0.862, py: 0.532 }, far: { px: 0.558, py: 0.045 } };
export const COURT_SLOTS_PER_ROW = 10;
export const COURT_SLOT_STEP = 1 / (COURT_SLOTS_PER_ROW - 1);

export function courtSlots(): Array<CourtPct & { side: 'left' | 'right'; slot: number }> {
  const slots: Array<CourtPct & { side: 'left' | 'right'; slot: number }> = [];
  for (let i = 0; i < COURT_SLOTS_PER_ROW; i++) {
    const t = i / (COURT_SLOTS_PER_ROW - 1);
    slots.push({
      px: LEFT_ANCHOR.near.px + t * (LEFT_ANCHOR.far.px - LEFT_ANCHOR.near.px),
      py: LEFT_ANCHOR.near.py + t * (LEFT_ANCHOR.far.py - LEFT_ANCHOR.near.py),
      side: 'left',
      slot: i,
    });
    slots.push({
      px: RIGHT_ANCHOR.near.px + t * (RIGHT_ANCHOR.far.px - RIGHT_ANCHOR.near.px),
      py: RIGHT_ANCHOR.near.py + t * (RIGHT_ANCHOR.far.py - RIGHT_ANCHOR.near.py),
      side: 'right',
      slot: i,
    });
  }
  return slots;
}

export function snapToSlot(
  px: number,
  py: number,
  occupied: Set<string>,
  selfKey: string,
): CourtPct {
  const slots = courtSlots();
  let best: CourtPct | null = null;
  let bestDist = Infinity;
  for (const s of slots) {
    const key = `${s.side}:${s.slot}`;
    if (occupied.has(key) && key !== selfKey) continue;
    const d = Math.hypot(s.px - px, s.py - py);
    if (d < bestDist) {
      bestDist = d;
      best = s;
    }
  }
  return best ?? { px, py };
}

export function defaultCourtPct(index: number, total: number): CourtPct {
  const side = index < Math.ceil(total / 2) ? 'left' : 'right';
  const posInRow = side === 'left' ? index : index - Math.ceil(total / 2);
  const anchor = side === 'left' ? LEFT_ANCHOR : RIGHT_ANCHOR;
  const t = posInRow * COURT_SLOT_STEP;
  return {
    px: anchor.near.px + t * (anchor.far.px - anchor.near.px),
    py: anchor.near.py + t * (anchor.far.py - anchor.near.py),
  };
}

export function arrangeCourtPositions(
  names: string[],
  saved: Record<string, CourtPct>,
): Record<string, CourtPct> {
  const allSlots = courtSlots();
  const usedSlots = new Set<string>();
  const next: Record<string, CourtPct> = {};

  names.forEach((name, index) => {
    if (saved[name]) {
      const cur = saved[name];
      let best = allSlots.find((s) => !usedSlots.has(`${s.side}:${s.slot}`)) ?? allSlots[0];
      let bestD = Infinity;
      for (const s of allSlots) {
        const key = `${s.side}:${s.slot}`;
        if (usedSlots.has(key)) continue;
        const d = Math.hypot(s.px - cur.px, s.py - cur.py);
        if (d < bestD) {
          bestD = d;
          best = s;
        }
      }
      usedSlots.add(`${best.side}:${best.slot}`);
      next[name] = { px: best.px, py: best.py };
      return;
    }
    const slot = allSlots.find((s) => !usedSlots.has(`${s.side}:${s.slot}`));
    if (slot) {
      usedSlots.add(`${slot.side}:${slot.slot}`);
      next[name] = { px: slot.px, py: slot.py };
    } else {
      next[name] = defaultCourtPct(index, names.length);
    }
  });

  return next;
}
