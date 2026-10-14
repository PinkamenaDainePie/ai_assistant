# -*- coding: utf-8 -*-
"""农业 playbook → outcome 摘要与延迟风险种子（表驱动）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

AGRICULTURE_PLAYBOOK_OUTCOMES: Dict[str, Dict[str, Any]] = {
    "spring_encourage_farming": {
        "narrative_seed_zh": "劝课农桑令下，州县督导；须防虚报与扰农。",
        "delayed_risk_seeds": [
            {"id": "false_farming_report", "weight": 0.18, "domain": "agriculture"},
            {"id": "disturb_spring_planting", "weight": 0.14, "domain": "agriculture"},
        ],
    },
    "irrigation_or_land_improvement": {
        "narrative_seed_zh": "农田水利兴工，膏腴可期；征发与工期延误之患须察。",
        "delayed_risk_seeds": [
            {"id": "irrigation_project_delay", "weight": 0.2, "domain": "agriculture"},
            {"id": "corvee_dispute_irrigation", "weight": 0.16, "domain": "agriculture"},
        ],
    },
    "mulberry_silk_promotion": {
        "narrative_seed_zh": "广植桑麻、课以蚕事，丝课可期；须防夺稻过甚、粮价波动。",
        "delayed_risk_seeds": [
            {"id": "food_security_sericulture", "weight": 0.22, "domain": "agriculture"},
            {"id": "sericulture_overreach", "weight": 0.15, "domain": "agriculture"},
        ],
    },
    "spring_grain_lending": {
        "narrative_seed_zh": "春前给散贷种，备春耕之急；须防吏胥抑勒与误期。",
        "delayed_risk_seeds": [
            {"id": "spring_lending_abuse", "weight": 0.2, "domain": "agriculture"},
            {"id": "spring_timing_slip", "weight": 0.14, "domain": "agriculture"},
        ],
    },
}


def build_agriculture_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = AGRICULTURE_PLAYBOOK_OUTCOMES.get(task_key) or {}
    if not row:
        return {}, [], ""
    seeds = list(row.get("delayed_risk_seeds") or [])
    nar = str(row.get("narrative_seed_zh") or "")
    if location_name_zh and nar:
        nar = f"（地：{location_name_zh}）{nar}"
    immediate = {
        "playbook_id": task_key,
        "domain": "agriculture",
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]
        ),
        "summary_zh": "农政承办效果已按 playbook 与地点修正结算。",
    }
    return immediate, seeds, nar
