#!/usr/bin/env python3
"""Export china_ming_wanli.png from salvage terrain aligned to ming_map_regions_raw.txt."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SALVAGE_PUBLIC = ROOT / "ming-salvage-sim-main" / "web" / "public"
TERRAIN_PATH = SALVAGE_PUBLIC / "ming-1627-terrain-map.png"
OUT_PATH = ROOT / "frontend" / "public" / "maps" / "china_ming_wanli.png"
RAW_PATH = Path(__file__).resolve().parent / "ming_map_regions_raw.txt"

# Salvage map.tsx / mapPaths.ts constants
MAP_VIEW_BOX = (840.0, 82.0, 276.0, 206.0)
DEFAULT_TERRAIN_TRANSFORM = (840.22, 83.48, 276.0, 206.0)
OUT_WIDTH = 1448
OUT_HEIGHT = 1086

PAIR_RE = re.compile(r"\(\s*(\d+)\s*[,，]\s*(\d+)\s*\)")


def svg_to_pixel(svg_x: float, svg_y: float) -> tuple[float, float]:
    vb_x, vb_y, vb_w, vb_h = MAP_VIEW_BOX
    return (
        (svg_x - vb_x) * OUT_WIDTH / vb_w,
        (svg_y - vb_y) * OUT_HEIGHT / vb_h,
    )


def pixel_to_svg(px: float, py: float) -> tuple[float, float]:
    vb_x, vb_y, vb_w, vb_h = MAP_VIEW_BOX
    return (
        px * vb_w / OUT_WIDTH + vb_x,
        py * vb_h / OUT_HEIGHT + vb_y,
    )


def cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Match SVG preserveAspectRatio=xMidYMid slice."""
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    nw = max(1, int(round(iw * scale)))
    nh = max(1, int(round(ih * scale)))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def region_centroids(raw_text: str) -> dict[str, tuple[float, float]]:
    region_keys = [
        "北直隶", "辽东", "山东", "山西", "河南", "陕西", "南直隶", "浙江",
        "江西", "福建", "湖广", "贵州", "云南", "广西", "广东",
    ]
    by_key = {key: raw_text.find(key) for key in region_keys}
    out: dict[str, tuple[float, float]] = {}
    for key in region_keys:
        pos = by_key[key]
        if pos < 0:
            continue
        next_pos = len(raw_text)
        for other in by_key.values():
            if other > pos:
                next_pos = min(next_pos, other)
        pts = [(int(x), int(y)) for x, y in PAIR_RE.findall(raw_text[pos:next_pos])]
        if not pts:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out[key] = (cx, cy)
    return out


def export_map() -> None:
    if not TERRAIN_PATH.is_file():
        raise FileNotFoundError(f"Missing terrain asset: {TERRAIN_PATH}")

    terrain = Image.open(TERRAIN_PATH).convert("RGB")
    tx, ty, tw, th = DEFAULT_TERRAIN_TRANSFORM
    vb_x, vb_y, vb_w, vb_h = MAP_VIEW_BOX

    dest_w = int(round(tw * OUT_WIDTH / vb_w))
    dest_h = int(round(th * OUT_HEIGHT / vb_h))
    dest_x = int(round((tx - vb_x) * OUT_WIDTH / vb_w))
    dest_y = int(round((ty - vb_y) * OUT_HEIGHT / vb_h))

    terrain_layer = cover_resize(terrain, dest_w, dest_h)

    canvas = Image.new("RGB", (OUT_WIDTH, OUT_HEIGHT), (245, 240, 230))
    canvas.paste(terrain_layer, (dest_x, dest_y))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PATH, format="PNG", optimize=True)
    print(f"Wrote {OUT_PATH} ({OUT_WIDTH}x{OUT_HEIGHT})")
    print(
        f"Terrain slice: src={terrain.size} dest=({dest_x},{dest_y},{dest_w},{dest_h}) "
        f"transform=({tx},{ty},{tw},{th}) viewBox={MAP_VIEW_BOX}"
    )

    raw = RAW_PATH.read_text(encoding="utf-8")
    centroids = region_centroids(raw)
    xs = [c[0] for c in centroids.values()]
    ys = [c[1] for c in centroids.values()]
    print(f"Polygon centroids in canvas: x=[{min(xs):.0f},{max(xs):.0f}] y=[{min(ys):.0f},{max(ys):.0f}]")
    for name in ("河南", "北直隶", "广东", "云南"):
        if name in centroids:
            cx, cy = centroids[name]
            sx, sy = pixel_to_svg(cx, cy)
            print(f"  {name}: pixel=({cx:.0f},{cy:.0f}) svg=({sx:.1f},{sy:.1f})")


if __name__ == "__main__":
    try:
        export_map()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
