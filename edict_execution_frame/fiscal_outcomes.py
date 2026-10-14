# -*- coding: utf-8 -*-
"""财政 playbook → outcome 摘要与延迟风险种子（表驱动）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

FISCAL_PLAYBOOK_OUTCOMES: Dict[str, Dict[str, Any]] = {
    "tax_collection_push": {
        "narrative_seed_zh": "清厘钱粮赋役，追比逋欠；豪强隐匿与吏胥拖延之患须察。",
        "delayed_risk_seeds": [
            {"id": "tax_resistance", "weight": 0.2, "domain": "fiscal"},
            {"id": "gentry_obstruction", "weight": 0.16, "domain": "fiscal"},
        ],
    },
    "increase_tax_levy": {
        "narrative_seed_zh": "加征加派以充国用，岁入可期而民怨易起。",
        "delayed_risk_seeds": [
            {"id": "popular_backlash_levy", "weight": 0.22, "domain": "fiscal"},
            {"id": "merchant_flight", "weight": 0.12, "domain": "fiscal"},
        ],
    },
    "reduce_court_spending": {
        "narrative_seed_zh": "裁冗节流，省费宽计；朝中供亿与冗支之阻不可忽视。",
        "delayed_risk_seeds": [
            {"id": "court_resistance_austerity", "weight": 0.16, "domain": "fiscal"},
            {"id": "service_disruption", "weight": 0.12, "domain": "fiscal"},
        ],
    },
    "expand_state_monopoly": {
        "narrative_seed_zh": "市易榷货，收息开源；商民怨与吏胥侵渔并见。",
        "delayed_risk_seeds": [
            {"id": "merchant_backlash_monopoly", "weight": 0.2, "domain": "fiscal"},
            {"id": "monopoly_abuse", "weight": 0.18, "domain": "fiscal"},
        ],
    },
    "corvee_commutation": {
        "narrative_seed_zh": "免役钱代，雇役均摊；户等不公与豪右避役须防。",
        "delayed_risk_seeds": [
            {"id": "levy_inequity", "weight": 0.18, "domain": "fiscal"},
            {"id": "elite_evasion_corvee", "weight": 0.16, "domain": "fiscal"},
        ],
    },
    "abolish_state_monopoly": {
        "narrative_seed_zh": "罢市易务，息商民怨；岁入或短绌，须另筹调剂。",
        "delayed_risk_seeds": [
            {"id": "revenue_gap_after_repeal", "weight": 0.2, "domain": "fiscal"},
            {"id": "merchant_lobby_pressure", "weight": 0.14, "domain": "fiscal"},
        ],
    },
    "equalized_transport": {
        "narrative_seed_zh": "均输漕贡，徙贵就贱；道里损耗与地方梗阻仍多。",
        "delayed_risk_seeds": [
            {"id": "transport_loss", "weight": 0.18, "domain": "fiscal"},
            {"id": "regional_friction_transport", "weight": 0.14, "domain": "fiscal"},
        ],
    },
}


def build_fiscal_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = FISCAL_PLAYBOOK_OUTCOMES.get(task_key) or {}
    if not row:
        return {}, [], ""
    seeds = list(row.get("delayed_risk_seeds") or [])
    nar = str(row.get("narrative_seed_zh") or "")
    if location_name_zh and nar:
        nar = f"（地：{location_name_zh}）{nar}"
    immediate = {
        "playbook_id": task_key,
        "domain": "fiscal",
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]
        ),
        "summary_zh": "财政承办效果已按 playbook 与地点修正结算。",
    }
    return immediate, seeds, nar
