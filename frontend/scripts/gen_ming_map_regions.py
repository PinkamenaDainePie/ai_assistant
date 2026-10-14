#!/usr/bin/env python3
"""Generate mingMapRegions.ts from ming_map_regions_raw.txt."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = Path(__file__).resolve().parent / "ming_map_regions_raw.txt"
OUT_PATH = ROOT / "game" / "map" / "mingMapRegions.ts"

REGIONS = [
    ("beizhili", "北直隶", "北直隶"),
    ("liaodong", "辽东", "辽东"),
    ("shandong", "山东", "山东"),
    ("shanxi", "山西", "山西"),
    ("henan", "河南", "河南"),
    ("shaanxi", "陕西", "陕西"),
    ("nanzhili", "南直隶", "南直隶"),
    ("zhejiang", "浙江", "浙江"),
    ("jiangxi", "江西", "江西"),
    ("fujian", "福建", "福建"),
    ("huguang", "湖广", "湖广"),
    ("sichuan", "四川", "四川"),
    ("guangdong", "广东", "广东"),
    ("guangxi", "广西", "广西"),
    ("yunnan", "云南", "云南"),
    ("guizhou", "贵州", "贵州"),
]

PAIR_RE = re.compile(r"\(\s*(\d+)\s*[,，]\s*(\d+)\s*\)")


def compute_polygon_centroid(points: list[tuple[int, int]]) -> tuple[int, int]:
    if not points:
        return 0, 0
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    n = len(points)
    return round(sx / n), round(sy / n)


def parse_points(block: str) -> list[tuple[int, int]]:
    return [(int(x), int(y)) for x, y in PAIR_RE.findall(block)]


def ts_point(x: int, y: int) -> str:
    return f"{{ x: {x}, y: {y} }}"


def emit_region(region_id: str, name: str, points: list[tuple[int, int]]) -> str:
    cx, cy = compute_polygon_centroid(points)
    pts = ",\n      ".join(ts_point(x, y) for x, y in points)
    return f"""  {{
    id: '{region_id}',
    name: '{name}',
    type: 'province',
    points: [
      {pts}
    ],
    centroid: {{ x: {cx}, y: {cy} }},
    enabled: true,
  }}"""


def main() -> None:
    text = RAW_PATH.read_text(encoding="utf-8")
    by_key = {key: text.find(key) for _rid, _name, key in REGIONS}
    for _rid, _name, key in REGIONS:
        if by_key[key] < 0:
            raise ValueError(f"Missing region marker: {key}")
    regions_ts: list[str] = []
    for region_id, name, key in REGIONS:
        pos = by_key[key]
        next_pos = len(text)
        for other in by_key.values():
            if other > pos:
                next_pos = min(next_pos, other)
        block = text[pos:next_pos]
        points = parse_points(block)
        if not points:
            raise ValueError(f"No points for {region_id}")
        regions_ts.append(emit_region(region_id, name, points))
    out = (
        "import type { MapRegion } from './mapTypes';\n\n"
        "/** 万历十五省 + 辽东多边形（由 scripts/gen_ming_map_regions.py 生成） */\n"
        "/** 底图 1448×1086；x_pct=cx/1448*100, y_pct=cy/1086*100 */\n"
        "export const mingMapRegions: MapRegion[] = [\n"
        + ",\n".join(regions_ts)
        + "\n];\n"
    )
    OUT_PATH.write_text(out, encoding="utf-8")
    print("Wrote", OUT_PATH)


if __name__ == "__main__":
    main()
