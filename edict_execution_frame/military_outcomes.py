# -*- coding: utf-8 -*-
"""军事域 outcome 叙事（表驱动）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

_OUTCOME_SEEDS: Dict[str, Dict[str, Any]] = {
    "border_readiness": {
        "summary_zh": "边防整饬承办已按路分与边情修正结算。",
        "seeds": [{"id": "frontier_patrol_lapse", "weight": 0.12, "domain": "military"}],
    },
    "campaign_against": {
        "summary_zh": "出师讨伐承办已按敌对势力与战线修正结算。",
        "seeds": [
            {"id": "campaign_stalemate", "weight": 0.18, "domain": "military"},
            {"id": "supply_line_strain", "weight": 0.14, "domain": "military"},
        ],
    },
}


def build_military_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str = "",
    hostile_name_zh: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = _OUTCOME_SEEDS.get((task_key or "").strip()) or {}
    parts = []
    if hostile_name_zh:
        parts.append("对%s" % hostile_name_zh)
    if location_name_zh:
        parts.append("于%s" % location_name_zh)
    nar = "诏书军事承办推进中%s，季末将据成效汇奏。" % ("".join(parts) if parts else "")
    immediate = {
        "playbook_id": task_key,
        "domain": "military",
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") in ("add_metric", "add_regional_metric")]
        ),
        "summary_zh": str(row.get("summary_zh") or "军事承办效果已结算。"),
        "hostile_name_zh": hostile_name_zh,
    }
    seeds = list(row.get("seeds") or [])
    return immediate, seeds, nar
