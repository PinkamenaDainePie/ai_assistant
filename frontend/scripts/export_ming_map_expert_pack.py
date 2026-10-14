#!/usr/bin/env python3
"""Export Ming map vector coords for external artists (SVG + JSON + editable txt)."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = Path(__file__).resolve().parent / "ming_map_regions_raw.txt"
PACK_DIR = Path(__file__).resolve().parent / "ming_map_expert"
BASE_MAP = ROOT / "frontend" / "public" / "maps" / "china_ming_wanli.png"
SALVAGE_SVG = ROOT / "ming-salvage-sim-main" / "web" / "public" / "playable_map.svg"

OUT_W, OUT_H = 1448, 1086

REGIONS = [
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

MARKERS_PCT = {
    "liaodong_theater": (62.25, 33.03),
    "dongjiang": (77.0, 36.09),
    "xuan_da": (53.73, 44.57),
    "shanhaiguan": (56.77, 47.88),
}

PCT_LINE_RE = re.compile(r"pct=\(([0-9.]+),\s*([0-9.]+)\)")
REGION_ID_IN_LINE_RE = re.compile(r"\((\w+)\)：")

PAIR_RE = re.compile(r"\(\s*(\d+)\s*[,，]\s*(\d+)\s*\)")


def centroid(points: list[tuple[int, int]]) -> tuple[int, int]:
    n = len(points)
    return round(sum(p[0] for p in points) / n), round(sum(p[1] for p in points) / n)


def parse_markers_from_raw() -> dict[str, tuple[float, float]]:
    """Parse synced centroids from ming_map_regions_raw.txt (same source as web_app region_positions)."""
    text = RAW_PATH.read_text(encoding="utf-8")
    name_to_id = {name: rid for rid, name in REGIONS}
    out: dict[str, tuple[float, float]] = {}
    for line in text.splitlines():
        if "pct=" not in line or line.strip().startswith("#"):
            continue
        pct_m = PCT_LINE_RE.search(line)
        if not pct_m:
            continue
        xp, yp = float(pct_m.group(1)), float(pct_m.group(2))
        id_m = REGION_ID_IN_LINE_RE.search(line)
        if id_m:
            out[id_m.group(1)] = (xp, yp)
            continue
        name = line.split("：", 1)[0].strip()
        if name in name_to_id:
            out[name_to_id[name]] = (xp, yp)
    out.update(MARKERS_PCT)
    return out


def parse_raw() -> dict[str, list[tuple[int, int]]]:
    text = RAW_PATH.read_text(encoding="utf-8")
    out: dict[str, list[tuple[int, int]]] = {}
    for region_id, name in REGIONS:
        pos = text.find(name)
        if pos < 0:
            raise ValueError(f"Missing region: {name}")
        next_pos = len(text)
        for _rid, n in REGIONS:
            p = text.find(n)
            if p > pos:
                next_pos = min(next_pos, p)
        out[region_id] = [(int(x), int(y)) for x, y in PAIR_RE.findall(text[pos:next_pos])]
    return out


def pct_to_pixel(x_pct: float, y_pct: float) -> tuple[float, float]:
    return round(x_pct / 100 * OUT_W, 2), round(y_pct / 100 * OUT_H, 2)


def write_svg(regions: dict[str, list[tuple[int, int]]], markers_pct: dict[str, tuple[float, float]]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{OUT_W}" height="{OUT_H}" viewBox="0 0 {OUT_W} {OUT_H}">',
        '  <!-- 底图：与 regions_overlay.svg 同目录的 china_ming_wanli.png -->',
        f'  <image href="china_ming_wanli.png" width="{OUT_W}" height="{OUT_H}" />',
        '  <g id="provinces" fill="rgba(255,80,80,0.15)" stroke="#c0392b" stroke-width="2">',
    ]
    for region_id, name in REGIONS:
        pts = regions[region_id]
        attr = " ".join(f"{x},{y}" for x, y in pts)
        lines.append(f'    <polygon id="{region_id}" data-name="{name}" points="{attr}" />')
    lines.append("  </g>")
    lines.append('  <g id="centroids" fill="#1a5276" font-family="sans-serif" font-size="14">')
    for region_id, name in REGIONS:
        cx, cy = centroid(regions[region_id])
        lines.append(f'    <circle cx="{cx}" cy="{cy}" r="4" fill="#2980b9" />')
        lines.append(f'    <text x="{cx + 6}" y="{cy + 4}">{name}</text>')
    lines.append("  </g>")
    lines.append('  <g id="markers" fill="#27ae60" stroke="#1e8449" stroke-width="1">')
    for mid, (xp, yp) in markers_pct.items():
        px, py = pct_to_pixel(xp, yp)
        lines.append(f'    <circle id="marker_{mid}" cx="{px}" cy="{py}" r="6" fill="#27ae60" />')
    lines.append("  </g>")
    lines.append("</svg>")
    (PACK_DIR / "regions_overlay.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    regions = parse_raw()
    markers_pct = parse_markers_from_raw()

    region_json = {
        "canvas": {"width": OUT_W, "height": OUT_H, "origin": "top-left", "unit": "pixel"},
        "note": "Edit regions_editable.txt then run: python frontend/scripts/gen_ming_map_regions.py",
        "regions": [],
    }
    for region_id, name in REGIONS:
        pts = [{"x": x, "y": y} for x, y in regions[region_id]]
        cx, cy = centroid(regions[region_id])
        region_json["regions"].append(
            {
                "id": region_id,
                "name": name,
                "points": pts,
                "centroid": {"x": cx, "y": cy},
                "centroid_pct": {"x_pct": round(cx / OUT_W * 100, 2), "y_pct": round(cy / OUT_H * 100, 2)},
            }
        )
    (PACK_DIR / "regions.json").write_text(json.dumps(region_json, ensure_ascii=False, indent=2), encoding="utf-8")

    markers = {
        "canvas": {"width": OUT_W, "height": OUT_H},
        "note": "Green circles on map UI; x_pct/y_pct used by salvage API",
        "markers": [],
    }
    for mid, (xp, yp) in markers_pct.items():
        px, py = pct_to_pixel(xp, yp)
        markers["markers"].append({"id": mid, "x_pct": xp, "y_pct": yp, "x": px, "y": py})
    (PACK_DIR / "markers.json").write_text(json.dumps(markers, ensure_ascii=False, indent=2), encoding="utf-8")

    editable = RAW_PATH.read_text(encoding="utf-8")
    header = (
        "# 万历地图省界 — 专家编辑版\n"
        "# 画布：1448 × 1086 像素，原点左上角 (0,0)\n"
        "# 格式：省名：\\n(x, y) (x, y) ...\\n\n"
        "# 完成后交回此文件，或覆盖 frontend/scripts/ming_map_regions_raw.txt\n"
        "# 导入命令：python frontend/scripts/gen_ming_map_regions.py\n\n"
    )
    (PACK_DIR / "regions_editable.txt").write_text(header + editable.split("\n", 4)[-1], encoding="utf-8")

    write_svg(regions, markers_pct)

    if BASE_MAP.exists():
        dest = PACK_DIR / "china_ming_wanli.png"
        if not dest.exists() or dest.stat().st_mtime < BASE_MAP.stat().st_mtime:
            shutil.copy2(BASE_MAP, dest)

    if SALVAGE_SVG.exists():
        dest = PACK_DIR / "reference_playable_map.svg"
        if not dest.exists():
            shutil.copy2(SALVAGE_SVG, dest)

    print(f"Wrote expert pack to {PACK_DIR}")


if __name__ == "__main__":
    main()
