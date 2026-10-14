# -*- coding: utf-8 -*-
"""从 mapRegions.ts 生成 SONG_ROUTES 片段（开发用，勿直接覆盖 hand-tuned modifiers）。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TS = ROOT / "frontend" / "game" / "map" / "mapRegions.ts"


def main() -> None:
    text = TS.read_text(encoding="utf-8")
    ids = re.findall(r"id:\s*'([^']+)'", text)
    names = re.findall(r"name:\s*'([^']+)'", text)
    pairs = list(zip(ids, names))
    print("# %d routes" % len(pairs))
    for rid, nz in pairs:
        print('    ("%s", "%s"),' % (rid, nz))


if __name__ == "__main__":
    main()
