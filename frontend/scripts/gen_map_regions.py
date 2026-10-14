#!/usr/bin/env python3
"""Generate mapRegions.ts from map_regions_raw.txt."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = Path(__file__).resolve().parent / "map_regions_raw.txt"
OUT_PATH = ROOT / "game" / "map" / "mapRegions.ts"

REGIONS = [
    ("hedong", "河东路", "河东路"),
    ("yongxingjun", "永兴军路", "永兴军路"),
    ("qinfeng", "秦凤路", "秦凤路"),
    ("lizhou", "利州路", "利州路"),
    ("chengdufu", "成都府路", "成都府路"),
    ("zizhou", "梓州路", "梓州路"),
    ("kuizhou", "夔州路", "夔州路"),
    ("guangxi", "广西路", "广西路"),
    ("guangdong", "广东路", "广东路"),
    ("fujian", "福建路", "福建路"),
    ("liangzhe", "两浙路", "两浙路"),
    ("huainan", "淮南路", "淮南路"),
    ("jingdong", "京东路", "京东路"),
    ("hebei", "河北路", "河北路"),
    ("jingji", "京畿", "京畿"),
    ("jingxi", "京西路", "京西路"),
    ("jinghubei", "荆湖北路", "荆湖北路"),
    ("jinghunan", "荆湖南路", "荆湖南路"),
    ("jiangnanxi", "江南西路", "江南西路"),
    ("jiangnandong", "江南东路", "江南东路"),
]

PAIR_RE = re.compile(r"(\d+)\s*[,，]\s*(\d+)")


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


def emit_region(region_id: str, name: str, points: list[tuple[int, int]], is_prefecture: bool) -> str:
    cx, cy = compute_polygon_centroid(points)
    region_type = "prefecture" if is_prefecture else "route"
    pts = ",\n      ".join(ts_point(x, y) for x, y in points)
    return f"""  {{
    id: '{region_id}',
    name: '{name}',
    type: '{region_type}',
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
    summary: list[str] = []
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
        summary.append(f"{region_id}: {len(points)}")
        regions_ts.append(emit_region(region_id, name, points, region_id == "jingji"))
    out = (
        "import type { MapRegion } from './mapTypes';\n\n"
        "/** 北宋路分区多边形（由 scripts/gen_map_regions.py 生成） */\n"
        "export const mapRegions: MapRegion[] = [\n"
        + ",\n".join(regions_ts)
        + "\n];\n"
    )
    OUT_PATH.write_text(out, encoding="utf-8")
    print("Wrote", OUT_PATH)
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
