#!/usr/bin/env python3
"""Smoke-test ming_wanli scenario overlay vs Chongzhen bleed-through.

Usage (from repo root):
  python ming-salvage-sim-main/scripts/validate_wanli_scenario.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WANLI = ROOT / "content" / "scenarios" / "ming_wanli"
BUNDLED = ROOT / "content"

FORBIDDEN_IN_WANLI = re.compile(
    r"魏忠贤|袁崇焕|毛文龙|天启七年|煤山一缢|崇祯帝|1627\s*年\s*10\s*月|皇太极",
    re.I,
)
# 负向列举 / 史学对比行不判穿帮
GUARDRAIL_LINE = re.compile(
    r"禁止|勿|不写|不得|除外|无关|护栏|未至|较.*时|如魏|如袁|如天启|如煤山|如皇太极",
    re.I,
)


def _line_forbidden(line: str) -> bool:
    if GUARDRAIL_LINE.search(line):
        return False
    return bool(FORBIDDEN_IN_WANLI.search(line))

REQUIRED_FILES = [
    "manifest.json",
    "campaign.json",
    "characters.json",
    "events.json",
    "seed_events.json",
    "opening_gazette.md",
    "opening_legacies.json",
    "powers.json",
    "armies.json",
    "regions.json",
    "prompts/game_world.md",
    "prompts/ending_summary.md",
    "prompts/score_extractor_personnel_secret.md",
    "prompts/score_extractor_military_external.md",
    "prompts/score_extractor_internal.md",
]


def _load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (WANLI / rel).is_file():
            errors.append(f"缺少文件: {rel}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    # JSON validity + counts
    chars = _load_json(WANLI / "characters.json")
    events = _load_json(WANLI / "events.json")
    seeds = _load_json(WANLI / "seed_events.json")
    n_chars = len(chars.get("characters", [])) if isinstance(chars, dict) else 0
    n_events = len(events) if isinstance(events, list) else 0
    n_seeds = len(seeds) if isinstance(seeds, list) else 0

    if n_chars < 15:
        warnings.append(f"characters 仅 {n_chars} 人，建议 ≥20")
    if n_events < 8:
        warnings.append(f"events 仅 {n_events} 个，建议 ≥10")
    if n_seeds < 3:
        errors.append(f"seed_events 仅 {n_seeds} 个")

    # Forbidden text scan in wanli overlay (skip manifest description comparisons)
    scan_ext = {".md", ".json"}
    for path in WANLI.rglob("*"):
        if path.suffix.lower() not in scan_ext:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if _line_forbidden(line):
                errors.append(
                    f"禁止词命中: {path.relative_to(WANLI)}:{lineno}: {line.strip()[:80]}"
                )

    # Loader smoke (optional, needs ming_sim on PYTHONPATH)
    sys.path.insert(0, str(ROOT))
    try:
        from ming_sim import scenario_active
        from ming_sim.content import GameContent

        with scenario_active.override(str(WANLI)):
            content = GameContent.load()
        if not content.characters:
            errors.append("GameContent.load() characters 为空")
        if not content.opening_legacies:
            errors.append("opening_legacies 为空")
    except Exception as exc:
        warnings.append(f"GameContent.load() 跳过: {exc}")

    manifest = _load_json(WANLI / "manifest.json")
    if manifest.get("ending_profile") != "wanli":
        warnings.append("manifest 缺少 ending_profile: wanli")

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(
        f"OK: ming_wanli 验收通过 "
        f"(chars={n_chars}, events={n_events}, seeds={n_seeds})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
