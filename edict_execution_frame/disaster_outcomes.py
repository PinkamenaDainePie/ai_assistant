# -*- coding: utf-8 -*-
"""赈灾 playbook → outcome 摘要与延迟风险种子（表驱动）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

DISASTER_PLAYBOOK_OUTCOMES: Dict[str, Dict[str, Any]] = {
    "open_granary_relief": {
        "narrative_seed_zh": "朝廷开仓调粮赈济，流民稍得喘息；须防仓胥克扣与道路阻滞。",
        "delayed_risk_seeds": [
            {"id": "relief_grain_embezzlement", "weight": 0.22, "domain": "disaster_relief"},
            {"id": "transport_delay_grain", "weight": 0.18, "domain": "disaster_relief"},
        ],
    },
    "tax_remission_relief": {
        "narrative_seed_zh": "诏蠲缓赋以纾民困，国用短期承压，地方完纳节奏将变。",
        "delayed_risk_seeds": [
            {"id": "fiscal_shortfall_after_remission", "weight": 0.2, "domain": "disaster_relief"},
            {"id": "local_underreport_disaster", "weight": 0.15, "domain": "disaster_relief"},
        ],
    },
    "dispatch_imperial_commissioner": {
        "narrative_seed_zh": "遣钦差督办赈务，事权既专，成功则民望归朝，败则党议与贪案易发。",
        "delayed_risk_seeds": [
            {"id": "commissioner_corruption_probe", "weight": 0.25, "domain": "disaster_relief"},
            {"id": "center_local_tension", "weight": 0.15, "domain": "disaster_relief"},
        ],
    },
    "local_official_relief": {
        "narrative_seed_zh": "责成地方就地赈济，省费而速；然吏治参差，瞒报与截留之患尤须察之。",
        "delayed_risk_seeds": [
            {"id": "local_coverup_disaster", "weight": 0.24, "domain": "disaster_relief"},
            {"id": "banditry_on_refugees", "weight": 0.16, "domain": "disaster_relief"},
        ],
    },
}


def build_disaster_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = DISASTER_PLAYBOOK_OUTCOMES.get(task_key) or {}
    if not row:
        return {}, [], ""
    seeds = list(row.get("delayed_risk_seeds") or [])
    nar = str(row.get("narrative_seed_zh") or "")
    if location_name_zh and nar:
        nar = f"（地：{location_name_zh}）{nar}"
    immediate = {
        "playbook_id": task_key,
        "effect_actions_count": len([e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]),
        "summary_zh": "当季赈务效果已按 playbook 与地点修正结算。",
    }
    return immediate, seeds, nar
