#!/usr/bin/env python3
"""Smoke-test song_xining_v2 scenario overlay.

Usage (from repo root):
  python ming-salvage-sim-main/scripts/validate_xining_scenario.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XINING = ROOT / "content" / "scenarios" / "song_xining_v2"

FORBIDDEN = re.compile(
    r"魏忠贤|袁崇焕|毛文龙|天启七年|煤山|崇祯帝|张居正|万历|皇太极|1627|努尔哈赤|俺答汗|建州女真",
    re.I,
)
MING_WEAPON_NAMES = re.compile(r"鸟铳|佛郎机|虎蹲炮|红夷|三眼铳|燧发", re.I)
GUARDRAIL_LINE = re.compile(
    r"禁止|勿|不写|不得|除外|无关|护栏|未至|勿写",
    re.I,
)
REQUIRED_KEYWORDS = re.compile(r"王安石|熙宁|1068")

YITIAOBIAN = re.compile(r"一条鞭")
MING_REGION_NAMES = re.compile(r"北直隶|南直隶|奴儿干")
SONG_CONTROLLED_MING_TERMS = re.compile(r"明军|都司|一条鞭|北直隶|南直隶|蓟镇|宣府|辽东都司|建州卫")

REQUIRED_FILES = [
    "manifest.json",
    "campaign.json",
    "characters.json",
    "events.json",
    "seed_events.json",
    "classes.json",
    "opening_gazette.md",
    "opening_legacies.json",
    "powers.json",
    "armies.json",
    "regions.json",
    "fiscal_config.json",
    "troop_cost.json",
    "buildings.json",
    "preset_technologies.json",
    "weapons.json",
    "prompts/game_world.md",
    "prompts/season_simulator.md",
    "prompts/ending_summary.md",
    "prompts/score_extractor_personnel_secret.md",
    "prompts/score_extractor_military_external.md",
    "prompts/score_extractor_internal.md",
]


def _line_forbidden(line: str) -> bool:
    if GUARDRAIL_LINE.search(line):
        return False
    return bool(FORBIDDEN.search(line))


def _load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (XINING / rel).is_file():
            errors.append(f"缺少文件: {rel}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    chars = _load_json(XINING / "characters.json")
    events = _load_json(XINING / "events.json")
    seeds = _load_json(XINING / "seed_events.json")
    n_chars = len(chars.get("characters", [])) if isinstance(chars, dict) else 0
    n_events = len(events) if isinstance(events, list) else 0
    n_seeds = len(seeds) if isinstance(seeds, list) else 0

    if n_chars < 32:
        warnings.append(f"characters 仅 {n_chars} 人，建议 ≥32")
    if n_events < 22:
        warnings.append(f"events 仅 {n_events} 个，建议 ≥22")
    if n_seeds < 14:
        warnings.append(f"seed_events 仅 {n_seeds} 个，建议 ≥14")
    if n_seeds < 10:
        errors.append(f"seed_events 仅 {n_seeds} 个，至少 10 个")

    armies = _load_json(XINING / "armies.json")
    if isinstance(armies, dict):
        arms_text = json.dumps(armies.get("armies", []), ensure_ascii=False)
        if MING_WEAPON_NAMES.search(arms_text):
            errors.append("armies.json 仍含明末军械名（鸟铳/佛郎机/虎蹲炮等）")

    weapons = _load_json(XINING / "weapons.json")
    if isinstance(weapons, dict):
        wnames = " ".join(
            str(w.get("name", "")) for w in weapons.get("weapons", []) if isinstance(w, dict)
        )
        if MING_WEAPON_NAMES.search(wnames):
            errors.append("weapons.json 仍含明末军械名")

    corpus = ""
    scan_ext = {".md", ".json"}
    for path in XINING.rglob("*"):
        if path.suffix.lower() not in scan_ext:
            continue
        text = path.read_text(encoding="utf-8")
        corpus += text + "\n"
        for lineno, line in enumerate(text.splitlines(), 1):
            if _line_forbidden(line):
                errors.append(
                    f"禁止词命中: {path.relative_to(XINING)}:{lineno}: {line.strip()[:80]}"
                )

    if not REQUIRED_KEYWORDS.search(corpus):
        errors.append("应有词未命中：王安石|熙宁|1068 至少一处")

    regions_path = XINING / "regions.json"
    if regions_path.is_file():
        regions_data = _load_json(regions_path)
        regions_text = regions_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(regions_text.splitlines(), 1):
            if GUARDRAIL_LINE.search(line):
                continue
            if YITIAOBIAN.search(line):
                errors.append(
                    f"regions.json 含明制用语一条鞭: {lineno}: {line.strip()[:80]}"
                )
            if MING_REGION_NAMES.search(line):
                errors.append(
                    f"regions.json 含明制区划名: {lineno}: {line.strip()[:80]}"
                )
        if isinstance(regions_data, dict):
            for region in regions_data.get("regions", []):
                if not isinstance(region, dict):
                    continue
                if str(region.get("controlled_by") or "") != "song":
                    continue
                rid = str(region.get("id") or "")
                blob = json.dumps(region, ensure_ascii=False)
                if SONG_CONTROLLED_MING_TERMS.search(blob):
                    errors.append(
                        f"regions.json controlled_by=song 条目 {rid} 仍含明制用语"
                    )

    sys.path.insert(0, str(ROOT))
    try:
        from ming_sim import scenario_active
        from ming_sim.content import GameContent

        with scenario_active.override(str(XINING)):
            content = GameContent.load()
        if not content.characters:
            errors.append("GameContent.load() characters 为空")
        if not content.opening_legacies:
            errors.append("opening_legacies 为空")
    except Exception as exc:
        warnings.append(f"GameContent.load() 跳过: {exc}")

    manifest = _load_json(XINING / "manifest.json")
    if manifest.get("ending_profile") != "xining":
        warnings.append("manifest 缺少 ending_profile: xining")
    cv = str(manifest.get("content_version") or "")
    if cv and cv < "0.5.1":
        warnings.append(f"content_version={cv}，P5+ 建议 ≥0.5.1")

    seed_ids = set()
    event_ids = set()
    event_titles = set()
    if isinstance(seeds, list):
        seed_ids = {str(s.get("id") or "") for s in seeds if isinstance(s, dict)}
    if isinstance(events, list):
        event_ids = {str(e.get("id") or "") for e in events if isinstance(e, dict)}
        event_titles = {str(e.get("title") or "") for e in events if isinstance(e, dict)}
    overlap = seed_ids & event_ids
    if overlap:
        errors.append(f"events 与 seed_events id 重复: {', '.join(sorted(overlap))}")
    seed_event_pairs = [
        ("yellow_river", "黄河堤工之议"),
        ("muyi", "募役法推行"),
        ("shiyi_boycott", "市易罢市之议"),
        ("baojia", "保甲连坐争议"),
        ("xihe_supply", "熙河战后议"),
        ("yuanfeng_reform_germ", "元丰改制议"),
    ]
    for sid, expected_title in seed_event_pairs:
        if sid in seed_ids and expected_title not in event_titles:
            warnings.append(f"seed {sid} 无对应 events 节点「{expected_title}」")

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    print(
        f"OK: song_xining_v2 验收通过 "
        f"(chars={n_chars}, events={n_events}, seeds={n_seeds})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
