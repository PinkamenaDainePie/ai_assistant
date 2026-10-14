#!/usr/bin/env python3
"""Sync ming map from salvage mapPaths.ts — original SVG paths + pixel centroids."""
from __future__ import annotations

import json
import re
from pathlib import Path

from svg.path import parse_path

ROOT = Path(__file__).resolve().parents[2]
MAP_PATHS = ROOT / "ming-salvage-sim-main" / "web" / "src" / "mapPaths.ts"
RAW_PATH = Path(__file__).resolve().parent / "ming_map_regions_raw.txt"
REGIONS_TS = ROOT / "frontend" / "game" / "map" / "mingMapRegions.ts"
EXTERNAL_TS = ROOT / "frontend" / "game" / "map" / "mingMapExternalRegions.ts"
WEB_APP = ROOT / "ming-salvage-sim-main" / "web_app.py"

MAP_VIEW_BOX = (840.0, 82.0, 276.0, 206.0)
OUT_W, OUT_H = 1448, 1086

PROVINCES = [
    ("beizhili", "北直隶"),
    ("liaodong", "辽东"),
    ("shandong", "山东"),
    ("shanxi", "山西"),
    ("henan", "河南"),
    ("shaanxi", "陕西"),
    ("nanzhili", "南直隶"),
    ("zhejiang", "浙江"),
    ("jiangxi", "江西"),
    ("fujian", "福建"),
    ("huguang", "湖广"),
    ("sichuan", "四川"),
    ("guangdong", "广东"),
    ("guangxi", "广西"),
    ("yunnan", "云南"),
    ("guizhou", "贵州"),
]

LIAODONG_SOURCE_IDS = ("jianzhou", "shenyang_liaoyang")

# mapPaths REGION_PATH_GROUPS 中除省 + 辽东外的邻区
EXTRA_REGION_GROUPS = [
    ("korea", "朝鲜"),
    ("taiwan", "台湾"),
    ("nurgan", "奴儿干"),
    ("mongol_chahar", "蒙古察哈尔"),
    ("jianzhou", "建州"),
    ("shenyang_liaoyang", "沈阳辽阳"),
]

# mapPaths EXTERNAL_PATH_GROUPS（外邦 polygon，path id 见 UNMAPPED_PLAYABLE_PATHS）
EXTERNAL_GROUPS = [
    ("outer_mongolia", "漠北诸部", ["Buryatia", "Tuva", "Trans_Baikal"]),
    ("western_regions", "西域诸部", ["Dzungaria", "Tianshan"]),
    ("tibet", "乌思藏 / 青海", ["Qinghai", "Ngari", "Lhasa"]),
    ("amur_frontier", "黑龙江北境", ["Sakhalin"]),
    ("japan", "日本", ["Hokkaido", "Tohoku", "Kanto", "Chubu", "Kansai", "Chugoku", "Shikoku", "Kyushu"]),
    ("southwest_frontier", "安南 / 越南", ["Tonkin", "Annam", "Laos", "Mekong"]),
]

PAIR_RE = re.compile(r"\(\s*(\d+)\s*[,，]\s*(\d+)\s*\)")


def svg_to_pixel(sx: float, sy: float) -> tuple[float, float]:
    vb_x, vb_y, vb_w, vb_h = MAP_VIEW_BOX
    return ((sx - vb_x) * OUT_W / vb_w, (sy - vb_y) * OUT_H / vb_h)


def pct(cx: float, cy: float) -> tuple[float, float]:
    return (round(cx / OUT_W * 100, 2), round(cy / OUT_H * 100, 2))


def _load_ts_array(text: str, marker: str) -> list[dict]:
    eq = text.index("=", text.index(marker))
    start = text.index("[", eq)
    depth = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(text[start:end])


def load_region_path_groups() -> list[dict]:
    text = MAP_PATHS.read_text(encoding="utf-8")
    return _load_ts_array(text, "export const REGION_PATH_GROUPS")


def load_unmapped_paths() -> dict[str, str]:
    text = MAP_PATHS.read_text(encoding="utf-8")
    items = _load_ts_array(text, "export const UNMAPPED_PLAYABLE_PATHS")
    return {item["id"]: item["d"] for item in items if item.get("id") and item.get("d")}


def resolve_external_path_ds(path_ids: list[str], unmapped: dict[str, str]) -> list[str]:
    return [unmapped[pid] for pid in path_ids if pid in unmapped]


def parse_existing_raw() -> dict[str, list[tuple[int, int]]]:
    if not RAW_PATH.exists():
        return {}
    text = RAW_PATH.read_text(encoding="utf-8")
    out: dict[str, list[tuple[int, int]]] = {}
    for region_id, name in PROVINCES:
        pos = text.find(name)
        if pos < 0:
            continue
        next_pos = len(text)
        for _rid, n in PROVINCES:
            p = text.find(n)
            if p > pos:
                next_pos = min(next_pos, p)
        pts = [(int(x), int(y)) for x, y in PAIR_RE.findall(text[pos:next_pos])]
        if pts:
            out[region_id] = pts
    return out


def sample_path_points(d: str, steps: int = 48) -> list[tuple[float, float]]:
    path = parse_path(d)
    if len(path) == 0 or path.length(error=1e-3) <= 0:
        return []
    out: list[tuple[float, float]] = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        pt = path.point(t)
        out.append((pt.real, pt.imag))
    return out


def region_svg_path_ds(group: dict) -> list[str]:
    return [str(item.get("d", "")) for item in group.get("paths", []) if item.get("d")]


def resolve_path_ds(region_id: str, groups_by_id: dict[str, dict]) -> list[str]:
    group = groups_by_id.get(region_id)
    if group:
        return region_svg_path_ds(group)
    if region_id == "liaodong":
        path_ds: list[str] = []
        for src in LIAODONG_SOURCE_IDS:
            g = groups_by_id.get(src)
            if g:
                path_ds.extend(region_svg_path_ds(g))
        return path_ds
    return []


def pixel_centroid_from_paths(path_ds: list[str], steps: int = 48) -> tuple[int, int]:
    pixel_pts: list[tuple[float, float]] = []
    for d in path_ds:
        for sx, sy in sample_path_points(d, steps=steps):
            pixel_pts.append(svg_to_pixel(sx, sy))
    if not pixel_pts:
        return 0, 0
    cx = sum(p[0] for p in pixel_pts) / len(pixel_pts)
    cy = sum(p[1] for p in pixel_pts) / len(pixel_pts)
    return int(round(cx)), int(round(cy))


def fallback_points_from_paths(path_ds: list[str], steps: int = 24) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for d in path_ds:
        for sx, sy in sample_path_points(d, steps=steps):
            px, py = svg_to_pixel(sx, sy)
            pt = (int(round(px)), int(round(py)))
            if not out or out[-1] != pt:
                out.append(pt)
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out


def points_centroid(points: list[tuple[int, int]]) -> tuple[int, int]:
    unique = points[:-1] if len(points) > 1 and points[0] == points[-1] else points
    if not unique:
        return 0, 0
    sx = sum(p[0] for p in unique)
    sy = sum(p[1] for p in unique)
    n = len(unique)
    return round(sx / n), round(sy / n)


def _emit_region_block(
    region_id: str,
    name: str,
    *,
    kind: str,
    path_ds: list[str],
    preserved: dict[str, list[tuple[int, int]]],
) -> tuple[str, tuple[int, int]]:
    if path_ds:
        cx, cy = pixel_centroid_from_paths(path_ds)
        points = fallback_points_from_paths(path_ds)
        paths_literal = ",\n      ".join(json.dumps(d, ensure_ascii=False) for d in path_ds)
        svg_block = f"    svgPaths: [\n      {paths_literal}\n    ],\n"
    elif region_id in preserved:
        points = preserved[region_id]
        cx, cy = points_centroid(points)
        svg_block = ""
    else:
        raise ValueError(f"Missing salvage path group: {region_id}")

    pts_ts = ",\n      ".join(f"{{ x: {x}, y: {y} }}" for x, y in points)
    block = f"""  {{
    id: '{region_id}',
    name: '{name}',
    type: 'province',
    kind: '{kind}',
{svg_block}    points: [
      {pts_ts}
    ],
    centroid: {{ x: {cx}, y: {cy} }},
    enabled: true,
  }}"""
    return block, (cx, cy)


def emit_regions_ts(
    groups_by_id: dict[str, dict],
    preserved: dict[str, list[tuple[int, int]]],
) -> dict[str, tuple[int, int]]:
    centroids: dict[str, tuple[int, int]] = {}
    blocks: list[str] = []
    for region_id, name in PROVINCES:
        path_ds = resolve_path_ds(region_id, groups_by_id)
        block, (cx, cy) = _emit_region_block(
            region_id, name, kind="province", path_ds=path_ds, preserved=preserved
        )
        centroids[region_id] = (cx, cy)
        blocks.append(block)

    out = (
        "import type { MapRegion } from './mapTypes';\n\n"
        "/** 万历十五省 + 辽东（由 scripts/sync_ming_map_from_salvage.py 从 mapPaths.ts 生成） */\n"
        "/** svgPaths = salvage viewBox 840 82 276 206；底图 1448×1086 */\n"
        "export const mingMapRegions: MapRegion[] = [\n"
        + ",\n".join(blocks)
        + "\n];\n"
    )
    REGIONS_TS.write_text(out, encoding="utf-8")
    return centroids


def emit_external_regions_ts(
    groups_by_id: dict[str, dict],
    unmapped: dict[str, str],
    preserved: dict[str, list[tuple[int, int]]],
) -> dict[str, tuple[int, int]]:
    centroids: dict[str, tuple[int, int]] = {}
    blocks: list[str] = []

    for region_id, name in EXTRA_REGION_GROUPS:
        path_ds = region_svg_path_ds(groups_by_id[region_id]) if region_id in groups_by_id else []
        block, (cx, cy) = _emit_region_block(
            region_id, name, kind="external", path_ds=path_ds, preserved=preserved
        )
        centroids[region_id] = (cx, cy)
        blocks.append(block)

    for region_id, name, path_ids in EXTERNAL_GROUPS:
        path_ds = resolve_external_path_ds(path_ids, unmapped)
        block, (cx, cy) = _emit_region_block(
            region_id, name, kind="external", path_ds=path_ds, preserved=preserved
        )
        centroids[region_id] = (cx, cy)
        blocks.append(block)

    out = (
        "import type { MapRegion } from './mapTypes';\n\n"
        "/** 邻区 + 外邦（由 scripts/sync_ming_map_from_salvage.py 从 mapPaths.ts 生成） */\n"
        "export const mingMapExternalRegions: MapRegion[] = [\n"
        + ",\n".join(blocks)
        + "\n];\n"
    )
    EXTERNAL_TS.write_text(out, encoding="utf-8")
    return centroids


def emit_raw_summary(
    centroids: dict[str, tuple[int, int]],
    external_centroids: dict[str, tuple[int, int]],
    groups_by_id: dict[str, dict],
    unmapped: dict[str, str],
) -> None:
    lines = [
        "# 万历地图 — 由 salvage mapPaths.ts 同步",
        "# 渲染使用 mingMapRegions.ts 内 svgPaths（原版 SVG path）",
        "",
    ]
    for region_id, name in PROVINCES:
        path_ds = resolve_path_ds(region_id, groups_by_id)
        cx, cy = centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        lines.append(f"{name}：paths={len(path_ds)} centroid=({cx}, {cy}) pct=({x_pct}, {y_pct})")
        lines.append("")
    lines.append("# --- 邻区 / 外邦 ---")
    lines.append("")
    for region_id, name in EXTRA_REGION_GROUPS:
        cx, cy = external_centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        path_n = len(region_svg_path_ds(groups_by_id[region_id])) if region_id in groups_by_id else 0
        lines.append(f"{name} ({region_id})：paths={path_n} centroid=({cx}, {cy}) pct=({x_pct}, {y_pct})")
        lines.append("")
    for region_id, name, path_ids in EXTERNAL_GROUPS:
        cx, cy = external_centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        path_n = len(resolve_external_path_ds(path_ids, unmapped))
        lines.append(f"{name} ({region_id})：paths={path_n} centroid=({cx}, {cy}) pct=({x_pct}, {y_pct})")
        lines.append("")
    RAW_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_web_app_positions(
    centroids: dict[str, tuple[int, int]],
    external_centroids: dict[str, tuple[int, int]],
) -> None:
    text = WEB_APP.read_text(encoding="utf-8")
    marker = "        region_positions = {"
    start = text.index(marker) + len(marker)
    end = text.index("\n        }", start)
    synced_ids = {rid for rid, _ in PROVINCES}
    synced_ids |= {rid for rid, _ in EXTRA_REGION_GROUPS}
    synced_ids |= {rid for rid, _name, *_ in EXTERNAL_GROUPS}

    entries = []
    for region_id, _name in PROVINCES:
        cx, cy = centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        entries.append(f'            "{region_id}": ({x_pct}, {y_pct}),')
    for region_id, _name in EXTRA_REGION_GROUPS:
        cx, cy = external_centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        entries.append(f'            "{region_id}": ({x_pct}, {y_pct}),')
    for region_id, _name, *_ in EXTERNAL_GROUPS:
        cx, cy = external_centroids[region_id]
        x_pct, y_pct = pct(cx, cy)
        entries.append(f'            "{region_id}": ({x_pct}, {y_pct}),')

    old_block = text[start:end]
    extra_lines = []
    for line in old_block.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'"(\w+)":\s*\(', line)
        if m and m.group(1) not in synced_ids:
            extra_lines.append(f"            {line.rstrip(',')},")
    new_block = "\n".join(entries + extra_lines)
    text = text[:start] + "\n" + new_block + text[end:]
    WEB_APP.write_text(text, encoding="utf-8")


def main() -> None:
    groups = {g["regionId"]: g for g in load_region_path_groups()}
    unmapped = load_unmapped_paths()
    preserved = parse_existing_raw()
    centroids = emit_regions_ts(groups, preserved)
    external_centroids = emit_external_regions_ts(groups, unmapped, preserved)
    emit_raw_summary(centroids, external_centroids, groups, unmapped)
    update_web_app_positions(centroids, external_centroids)
    print(f"Wrote {REGIONS_TS}")
    print(f"Wrote {EXTERNAL_TS}")
    print(f"Wrote summary {RAW_PATH}")
    print(f"Updated region_positions in {WEB_APP}")
    for rid in ["beizhili", "nanzhili", "zhejiang", "guangdong"]:
        cx, cy = centroids[rid]
        name = next(n for i, n in PROVINCES if i == rid)
        path_n = len(resolve_path_ds(rid, groups))
        print(f"  {name} ({rid}): {path_n} svg path(s), pixel=({cx},{cy}) pct={pct(cx, cy)}")
    for rid in ["korea", "taiwan", "japan", "outer_mongolia"]:
        cx, cy = external_centroids[rid]
        if rid in groups:
            path_n = len(region_svg_path_ds(groups[rid]))
        else:
            path_ids = next(pids for eid, _n, pids in EXTERNAL_GROUPS if eid == rid)
            path_n = len(resolve_external_path_ds(path_ids, unmapped))
        print(f"  external {rid}: {path_n} svg path(s), pixel=({cx},{cy}) pct={pct(cx, cy)}")


if __name__ == "__main__":
    main()
