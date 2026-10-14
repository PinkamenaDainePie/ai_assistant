# -*- coding: utf-8 -*-
"""地点 / 目标对象槽位（R7–R10，P1）；affects_numbers 由本模块计算，禁止 LLM 直填。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.clarification import (
    evaluate_playbook_slot_issues,
    get_target_entity_slot_policy,
    merge_slot_issues_into_frame_state,
)
from edict_execution_frame.spatial_scope import (
    enrich_spatial_task_meta,
    evaluate_spatial_location_issues,
    get_scope_contract,
)
from edict_execution_frame.hostile_profiles import merge_modifier_dicts
from edict_execution_frame.location_profiles import LOCATION_PROFILES, clamp_location_modifier
from edict_execution_frame.schemas import EdictExecutionFrame, LocationSlot, TargetEntitySlot

try:
    from scenario_system.song_locations import is_song_scenario, song_location_aliases
except ImportError:
    is_song_scenario = lambda **_: False  # type: ignore
    song_location_aliases = lambda: []  # type: ignore

from edict_execution_frame.personnel_clarification import evaluate_personnel_issues
from edict_execution_frame.hostile_entity import (
    build_military_effect_scope,
    evaluate_hostile_entity_issues,
    extract_target_entity_from_text,
    hostile_modifier_for_frame,
)

_LOCATION_ALIASES: List[Tuple[str, str]] = [
    ("黄河", "yellow_river"),
    ("山东", "shandong"),
    ("江南", "jiangnan"),
    ("辽东", "liaodong"),
    ("边防", "liaodong"),
    ("山寨", "mountain_region_generic"),
    ("天下", "empire_wide"),
    ("全国", "empire_wide"),
]
_LOCATION_ALIASES.sort(key=lambda x: len(x[0]), reverse=True)


def _active_location_aliases() -> List[Tuple[str, str]]:
    base = list(_LOCATION_ALIASES)
    if is_song_scenario():
        seen = {a[1] for a in base}
        for needle, lid in song_location_aliases():
            if lid not in seen or needle not in {x[0] for x in base}:
                base.append((needle, lid))
        base.sort(key=lambda x: len(x[0]), reverse=True)
    return base

_PLAYBOOK_KEY_FMT = "{dom}:{tk}"

# §6.A 摘要（P1 与文档一致；缺省为 narrative-only）
_DEFAULT_POLICY: Dict[str, Any] = {
    "required": False,
    "unknown_behavior": "no_modifier",
    "allowed_scope_types": [
        "province",
        "prefecture",
        "county",
        "empire_wide",
        "river_segment",
        "border_region",
        "mountain_region",
        "foreign_polity",
        "route",
        "unknown",
    ],
    "affects": {
        "difficulty": False,
        "risk_tags": False,
        "effect_tiers": False,
        "narrative": True,
    },
}

_HIGH: Dict[str, Any] = {
    **_DEFAULT_POLICY,
    "allowed_scope_types": [
        "province",
        "prefecture",
        "county",
        "river_segment",
        "border_region",
        "mountain_region",
        "empire_wide",
        "route",
        "unknown",
    ],
    "affects": {"difficulty": True, "risk_tags": True, "effect_tiers": True, "narrative": True},
}
_MID: Dict[str, Any] = {
    **_DEFAULT_POLICY,
    "affects": {"difficulty": True, "risk_tags": True, "effect_tiers": False, "narrative": True},
}
_LOW: Dict[str, Any] = {
    **_DEFAULT_POLICY,
    "affects": {"difficulty": False, "risk_tags": False, "effect_tiers": False, "narrative": True},
}

PLAYBOOK_LOCATION_POLICIES: Dict[str, Dict[str, Any]] = {
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="strict_local_probe"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="routine_audit"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="reform_audit_sansi"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="market_monopoly_graft"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="river_work_embezzle"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="hidden_land_gentry"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="relief_grain_embezzle"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="anti_corruption", tk="memorial_screen_impeachment"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="agriculture", tk="spring_encourage_farming"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="agriculture", tk="irrigation_or_land_improvement"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="agriculture", tk="mulberry_silk_promotion"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="agriculture", tk="spring_grain_lending"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="disaster_relief", tk="open_granary_relief"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="disaster_relief", tk="tax_remission_relief"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="disaster_relief", tk="dispatch_imperial_commissioner"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="disaster_relief", tk="local_official_relief"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="abolish_state_monopoly"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="tax_collection_push"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="increase_tax_levy"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="reduce_court_spending"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="expand_state_monopoly"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="corvee_commutation"): _MID,
    _PLAYBOOK_KEY_FMT.format(dom="fiscal", tk="equalized_transport"): _HIGH,
    _PLAYBOOK_KEY_FMT.format(dom="military", tk="border_readiness"): {
        **_HIGH,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": ["route", "border_region", "prefecture"],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="military", tk="campaign_against"): {
        **_HIGH,
        "target_entity_contract": {"required_level": "soft_required"},
    },
    _PLAYBOOK_KEY_FMT.format(dom="diplomacy", tk="tributary_stability"): {
        **_DEFAULT_POLICY,
        "allowed_scope_types": ["foreign_polity", "border_region", "empire_wide", "unknown"],
        "affects": {"difficulty": False, "risk_tags": True, "effect_tiers": False, "narrative": True},
    },
    _PLAYBOOK_KEY_FMT.format(dom="personnel", tk="official_evaluation"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="personnel", tk="merit_appointment"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="personnel", tk="censure_and_removal"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="engineering", tk="river_dike_repair"): {
        **_HIGH,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": [
                "route",
                "prefecture",
                "river_segment",
                "mountain_region",
                "province",
            ],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="public_order", tk="bandit_suppression"): {
        **_HIGH,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": [
                "route",
                "prefecture",
                "county",
                "mountain_region",
                "border_region",
            ],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="public_order", tk="patrol_order"): {
        **_HIGH,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": ["route", "prefecture", "county"],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="public_order", tk="mountain_bandit_campaign"): {
        **_HIGH,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": ["route", "mountain_region", "prefecture"],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="public_order", tk="urban_order"): {
        **_MID,
        "scope_contract": {
            "required_level": "soft_required",
            "acceptable_scope_types": ["route", "prefecture", "province"],
            "missing_behavior": "clarify_or_warn",
        },
    },
    _PLAYBOOK_KEY_FMT.format(dom="general", tk="steady_governance"): _LOW,
    _PLAYBOOK_KEY_FMT.format(dom="general", tk="local_governance_cleanup"): _MID,
}

def _pb_key(domain: str, task_key: str) -> str:
    return _PLAYBOOK_KEY_FMT.format(dom=domain or "general", tk=task_key or "")


def get_location_policy(domain: str, task_key: str) -> Dict[str, Any]:
    return dict(PLAYBOOK_LOCATION_POLICIES.get(_pb_key(domain, task_key)) or _DEFAULT_POLICY)


def get_target_entity_policy(domain: str, task_key: str) -> Dict[str, Any]:
    return dict(get_target_entity_slot_policy(domain, task_key))


def _span_in_reserved(start: int, end: int, reserved: List[Tuple[int, int]]) -> bool:
    for a, b in reserved:
        if not (end <= a or start >= b):
            return True
    return False


def extract_location_from_text(
    text: str,
    reserved: Optional[List[Tuple[int, int]]] = None,
) -> LocationSlot:
    """公开槽位提取入口（供 nlu_layer 调用）。"""
    return _extract_location(text, reserved or [])


def _extract_location(text: str, reserved: List[Tuple[int, int]]) -> LocationSlot:
    t = text or ""
    for needle, lid in _active_location_aliases():
        idx = t.find(needle)
        if idx < 0:
            continue
        if _span_in_reserved(idx, idx + len(needle), reserved):
            continue
        prof = LOCATION_PROFILES.get(lid) or {}
        st = str(prof.get("scope_type") or "unknown")
        return LocationSlot(
            mode="explicit",
            location_id=lid,
            location_name_zh=str(prof.get("name_zh") or needle),
            scope_type=st,
            source_text=needle,
            confidence=0.88,
            affects_numbers=False,
        )
    # R8: 常见未收录地名（仅叙事）
    inferred = ["江右", "河套", "宣府"]
    for needle in inferred:
        idx = t.find(needle)
        if idx >= 0 and not _span_in_reserved(idx, idx + len(needle), reserved):
            return LocationSlot(
                mode="inferred",
                location_id="",
                location_name_zh=needle,
                scope_type="unknown",
                source_text=needle,
                confidence=0.55,
                affects_numbers=False,
            )
    return LocationSlot()


def _compute_affects_numbers(loc: LocationSlot, policy: Dict[str, Any]) -> bool:
    if (loc.mode or "") == "unknown" or not (loc.location_id or "").strip():
        return False
    if loc.location_id not in LOCATION_PROFILES:
        return False
    aff = policy.get("affects") or {}
    if not (
        bool(aff.get("difficulty"))
        or bool(aff.get("risk_tags"))
        or bool(aff.get("effect_tiers"))
    ):
        return False
    allowed = set(policy.get("allowed_scope_types") or [])
    st = (loc.scope_type or "unknown").strip()
    if allowed and st not in allowed and st != "unknown":
        return False
    if st == "unknown" and "unknown" not in allowed:
        # inferred 地名 unknown scope：不改数值
        return False
    return True


def _build_location_modifier_applied(domain: str, location_id: str) -> Dict[str, Any]:
    prof = LOCATION_PROFILES.get(location_id) or {}
    mods = prof.get("modifiers") or {}
    raw = mods.get(domain) or {}
    return dict(clamp_location_modifier(raw)) if raw else {}


def apply_location_target_to_frame(fr: EdictExecutionFrame, *, edict_text: str) -> EdictExecutionFrame:
    """装配 location / target_entity、R9、modifier trace；不改 domain/task_key。"""
    text = edict_text or ""
    dom = (fr.task.domain or "general").strip()
    tk = (fr.task.task_key or "").strip()
    te, spans = extract_target_entity_from_text(text)
    loc = _extract_location(text, spans)
    policy = get_location_policy(dom, tk)
    preliminary = _compute_affects_numbers(loc, policy)
    mod_applied: Dict[str, Any] = {}
    if preliminary and (loc.location_id or "").strip():
        mod_applied = _build_location_modifier_applied(dom, loc.location_id)
    if (te.entity_id or "").strip():
        hmod = hostile_modifier_for_frame(dom, tk, te.entity_id)
        mod_applied = merge_modifier_dicts(mod_applied, hmod)
        preliminary = preliminary or bool(hmod)
    affects_final = preliminary and bool(mod_applied)
    loc = loc.model_copy(update={"affects_numbers": bool(affects_final)})

    meta = dict(fr.task_meta or {})
    meta["location_policy"] = policy
    meta["target_entity_policy"] = get_target_entity_policy(dom, tk)
    meta["location_modifier_applied"] = mod_applied
    meta["hostile_modifier_applied"] = (
        hostile_modifier_for_frame(dom, tk, te.entity_id) if (te.entity_id or "").strip() else {}
    )
    meta["target_entity_row"] = {
        "entity_id": te.entity_id,
        "entity_name_zh": te.entity_name_zh,
        "entity_kind": te.entity_kind,
    }
    meta["location_resolution"] = {
        "r7_no_location_ok": (loc.mode == "unknown"),
        "r8_inferred_no_profile": (loc.mode == "inferred" and not loc.location_id),
        "r10_applied": bool(mod_applied),
    }
    if dom == "military":
        meta["effect_scope"] = build_military_effect_scope(
            loc_id=loc.location_id or "",
            loc_name_zh=loc.location_name_zh or loc.source_text or "",
            loc_scope_type=loc.scope_type or "",
            target_entity=te,
        )

    slot_issues = evaluate_playbook_slot_issues(
        edict_text=text, domain=dom, task_key=tk, target_entity=te
    )
    slot_issues = list(slot_issues) + evaluate_hostile_entity_issues(
        edict_text=text, domain=dom, task_key=tk, target_entity=te
    )
    slot_issues = list(slot_issues) + evaluate_spatial_location_issues(
        edict_text=text, domain=dom, task_key=tk, location=loc
    )
    slot_issues = list(slot_issues) + evaluate_personnel_issues(
        edict_text=text,
        domain=dom,
        task_key=tk,
        executor=fr.executor,
    )
    meta = enrich_spatial_task_meta(
        edict_text=text,
        domain=dom,
        task_key=tk,
        location=loc,
        base_meta=meta,
    )
    if get_scope_contract(dom, tk):
        meta["location_resolution"]["spatial_task"] = True
        meta["location_resolution"]["scope_confidence"] = meta.get("scope_confidence")
    rstatus = fr.resolution_status or "resolved"
    clar = list(fr.clarification_options or [])
    blocked = list(fr.blocked_reasons or [])
    rstatus, blocked, clar, issue_dicts = merge_slot_issues_into_frame_state(
        slot_issues,
        domain=dom,
        task_key=tk,
        current_status=rstatus,
        existing_blocked=blocked,
        existing_clar=clar,
    )
    meta["clarification_issues"] = issue_dicts

    updates: Dict[str, Any] = {
        "location": loc,
        "target_entity": te,
        "task_meta": meta,
        "resolution_status": rstatus,
        "clarification_options": clar,
        "blocked_reasons": blocked,
    }
    if rstatus == "needs_clarification":
        updates["normalized_command_zh"] = ""
    return fr.model_copy(update=updates)


def merge_risk_tags_from_modifier(frame: EdictExecutionFrame) -> EdictExecutionFrame:
    """将 location_modifier_applied.risk_tags_add 并入 frame.risk_tags（表驱动，P1）。"""
    meta = frame.task_meta or {}
    mod = meta.get("location_modifier_applied") or {}
    add = list(mod.get("risk_tags_add") or [])
    if not add:
        return frame
    risk = list(frame.risk_tags or [])
    for rt in add:
        if rt and rt not in risk:
            risk.append(rt)
    return frame.model_copy(update={"risk_tags": risk})
