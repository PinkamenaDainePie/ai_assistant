# -*- coding: utf-8 -*-
"""九域动作对象分类：人为 → agent-flow；物 → 仅代码层结算。"""
from __future__ import annotations

from typing import Dict, Tuple

# 域级默认（未列 playbook 覆盖时继承）
DOMAIN_OBJECT_KIND_DEFAULT: Dict[str, str] = {
    "anti_corruption": "human",
    "personnel": "human",
    "military": "human",
    "diplomacy": "human",
    "public_order": "human",
    "general": "human",
    "agriculture": "material",
    "engineering": "material",
    "disaster_relief": "human",
    "fiscal": "material",
}

# playbook 级覆盖：赈灾开仓放粮、财政制度条贯等以「物/制度」为主
PLAYBOOK_OBJECT_KIND: Dict[Tuple[str, str], str] = {
    ("disaster_relief", "open_granary_relief"): "material",
    ("disaster_relief", "tax_remission_relief"): "material",
    ("fiscal", "tax_collection_push"): "human",
    ("fiscal", "increase_tax_levy"): "human",
    ("fiscal", "reduce_court_spending"): "material",
    ("fiscal", "expand_state_monopoly"): "material",
    ("fiscal", "corvee_commutation"): "material",
    ("fiscal", "equalized_transport"): "material",
    ("fiscal", "abolish_state_monopoly"): "material",
    ("agriculture", "spring_encourage_farming"): "material",
    ("agriculture", "irrigation_or_land_improvement"): "material",
    ("agriculture", "mulberry_silk_promotion"): "material",
    ("agriculture", "spring_grain_lending"): "material",
    ("engineering", "river_dike_repair"): "material",
}

HUMAN_KIND = "human"
MATERIAL_KIND = "material"


def action_object_kind(domain: str, task_key: str) -> str:
    dom = str(domain or "").strip()
    tk = str(task_key or "").strip()
    if dom and tk:
        hit = PLAYBOOK_OBJECT_KIND.get((dom, tk))
        if hit:
            return hit
    return DOMAIN_OBJECT_KIND_DEFAULT.get(dom, MATERIAL_KIND)


def requires_agent_flow(domain: str, task_key: str) -> bool:
    """人为对象动作：须走 agent-flow 评价次生影响（上有政策、下有对策）。"""
    return action_object_kind(domain, task_key) == HUMAN_KIND
