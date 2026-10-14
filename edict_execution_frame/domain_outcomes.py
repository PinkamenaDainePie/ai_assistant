# -*- coding: utf-8 -*-
"""九域 outcome 元数据（表驱动）；肃贪/赈灾专表，其余域通用模板。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from edict_execution_frame.agriculture_outcomes import build_agriculture_outcome_meta
from edict_execution_frame.fiscal_outcomes import build_fiscal_outcome_meta
from edict_execution_frame.anti_corruption_outcomes import build_anti_corruption_outcome_meta
from edict_execution_frame.disaster_outcomes import build_disaster_outcome_meta
from edict_execution_frame.military_outcomes import build_military_outcome_meta
from edict_execution_frame.personnel_outcomes import build_personnel_outcome_meta

_DOMAIN_SUMMARY_ZH: Dict[str, str] = {
    "agriculture": "农政承办效果已按 playbook 与地点修正结算。",
    "fiscal": "财政承办效果已按 playbook 与地点修正结算。",
    "military": "军政承办效果已按 playbook 与地点修正结算。",
    "diplomacy": "外交承办效果已按 playbook 与地点修正结算。",
    "personnel": "人事承办效果已按 playbook 与地点修正结算。",
    "engineering": "工役承办效果已按 playbook 与地点修正结算。",
    "public_order": "治安承办效果已按 playbook 与地点修正结算。",
    "general": "政务承办效果已按 playbook 与地点修正结算。",
}


def _generic_outcome_meta(
    *,
    domain: str,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    nar = "诏书承办推进中，季末将据成效汇奏。"
    summary = _DOMAIN_SUMMARY_ZH.get(domain) or _DOMAIN_SUMMARY_ZH["general"]
    if location_name_zh:
        nar = f"（地：{location_name_zh}）{nar}"
    immediate = {
        "playbook_id": task_key,
        "domain": domain,
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]
        ),
        "summary_zh": summary,
    }
    return immediate, [], nar


def build_domain_outcome_meta(
    *,
    domain: str,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str = "",
    hostile_name_zh: str = "",
    appointee_name_zh: str = "",
    appointee_office_zh: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    dom = (domain or "general").strip()
    if dom == "disaster_relief":
        return build_disaster_outcome_meta(
            task_key=task_key, effects=effects, location_name_zh=location_name_zh
        )
    if dom == "anti_corruption":
        return build_anti_corruption_outcome_meta(
            task_key=task_key, effects=effects, location_name_zh=location_name_zh
        )
    if dom == "agriculture":
        imm, seeds, nar = build_agriculture_outcome_meta(
            task_key=task_key, effects=effects, location_name_zh=location_name_zh
        )
        if imm:
            return imm, seeds, nar
    if dom == "fiscal":
        imm, seeds, nar = build_fiscal_outcome_meta(
            task_key=task_key, effects=effects, location_name_zh=location_name_zh
        )
        if imm:
            return imm, seeds, nar
    if dom == "military":
        imm, seeds, nar = build_military_outcome_meta(
            task_key=task_key,
            effects=effects,
            location_name_zh=location_name_zh,
            hostile_name_zh=hostile_name_zh,
        )
        return imm, seeds, nar
    if dom == "personnel":
        return build_personnel_outcome_meta(
            task_key=task_key,
            effects=effects,
            location_name_zh=location_name_zh,
            appointee_name_zh=appointee_name_zh,
            appointee_office_zh=appointee_office_zh,
        )
    return _generic_outcome_meta(
        domain=dom,
        task_key=task_key,
        effects=effects,
        location_name_zh=location_name_zh,
    )
