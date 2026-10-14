# -*- coding: utf-8 -*-
"""从 templates + campaign_xining_main 聚合季末惩罚表（校验/文档镜像）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .campaign_catalog import all_main_defs, reload_campaign_catalog
from .metric_alignment import canonical_metric_key
from .task_repository import TaskRepository

_CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "task_quarter_penalties.json"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# war_arc 主线：stall 由 drift_effects_per_quarter 在运行时 alias
_WAR_ARC_STALL_FROM_DRIFT = frozenset(
    {"main_wangshao_hehuang", "main_song_viet_war_1075"}
)


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for x in items or []:
        if str(x.get("type") or "") != "stat_change":
            continue
        key = canonical_metric_key(x.get("key"))
        if not key:
            continue
        out.append({"type": "stat_change", "key": key, "value": float(x.get("value") or 0.0)})
    return out


def collect_authoritative_penalties() -> Dict[str, Dict[str, Any]]:
    """权威源：templates/*.json + campaign_xining_main.json。"""
    reload_campaign_catalog()
    repo = TaskRepository(_TEMPLATES_DIR)
    entries: Dict[str, Dict[str, Any]] = {}

    for tpl in repo.list_templates():
        entries[tpl.id] = {
            "title": tpl.title,
            "source": "template",
            "stall_penalties_per_quarter": _normalize_items(list(tpl.stall_penalties_per_quarter or [])),
            "penalties": _normalize_items(list(tpl.penalties or [])),
            "mandatory": bool(tpl.mandatory),
            "duration": int(tpl.duration),
        }

    for defn in all_main_defs():
        stall = _normalize_items(list(defn.stall_penalties_per_quarter or []))
        drift = _normalize_items(list(defn.drift_effects_per_quarter or []))
        meta: Dict[str, Any] = {
            "title": defn.title,
            "source": "campaign_main",
            "stall_penalties_per_quarter": stall,
            "penalties": _normalize_items(list(defn.penalties or [])),
            "duration": int(defn.duration or 1),
            "resolution_kind": str(defn.resolution_kind or "objectives"),
        }
        if defn.id in _WAR_ARC_STALL_FROM_DRIFT:
            meta["stall_alias"] = "drift_effects_per_quarter"
            meta["drift_effects_per_quarter"] = drift
            if not stall:
                meta["stall_penalties_per_quarter"] = []
        entries[defn.id] = meta

    return entries


def build_mirror_document() -> Dict[str, Any]:
    entries = collect_authoritative_penalties()
    return {
        "version": 1,
        "schema": {
            "stall_penalties_per_quarter": "季末怠政：assigned_quarter <= Q < deadline 且未完成",
            "penalties": "逾期失败：Q >= deadline_quarter 且未完成，任务移出 active",
            "stall_alias": "war_arc 主线 stall 运行时读 drift_effects_per_quarter",
        },
        "entries": entries,
    }


def write_mirror_catalog(path: Optional[Path] = None) -> Path:
    target = path or _CATALOG_PATH
    doc = build_mirror_document()
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def validate_penalties_catalog(
    *,
    expected_ids: Optional[Set[str]] = None,
) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    """返回 (errors, entries)。"""
    entries = collect_authoritative_penalties()
    errors: List[str] = []

    if expected_ids is not None:
        missing = expected_ids - set(entries.keys())
        extra = set(entries.keys()) - expected_ids
        for mid in sorted(missing):
            errors.append(f"missing entry: {mid}")
        for eid in sorted(extra):
            errors.append(f"unexpected entry: {eid}")

    for tid, row in entries.items():
        rk = str(row.get("resolution_kind") or "")
        stall_alias = str(row.get("stall_alias") or "")
        stall = list(row.get("stall_penalties_per_quarter") or [])
        drift = list(row.get("drift_effects_per_quarter") or [])
        expire = list(row.get("penalties") or [])

        has_stall = bool(stall) or stall_alias == "drift_effects_per_quarter" and bool(drift)
        if not has_stall and rk != "delegation":
            errors.append(f"{tid}: missing stall_penalties_per_quarter (or drift alias)")
        if not expire and rk not in ("campaign_story",):
            # campaign_story 也应有 expire；全部主线已补齐
            if tid.startswith("main_") or row.get("source") == "template":
                if not expire:
                    errors.append(f"{tid}: missing expire penalties")

        for label, items in (("stall", stall), ("expire", expire), ("drift", drift)):
            for idx, it in enumerate(items):
                if not canonical_metric_key(it.get("key")):
                    errors.append(f"{tid}: bad {label} metric at index {idx}")

    return errors, entries
