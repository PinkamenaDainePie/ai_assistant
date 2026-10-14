# -*- coding: utf-8 -*-
"""工程/治安：空间任务型域 — scope 契约、子类型、scope_confidence、地点澄清。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.clarification import ClarificationIssue, playbook_key
from edict_execution_frame.schemas import LocationSlot

SPATIAL_DOMAINS = frozenset({"engineering", "public_order"})

# 空间任务型域（无空间对象则承办不完整）
SPATIAL_TASK_PLAYBOOKS = frozenset(
    {
        playbook_key("engineering", "river_dike_repair"),
        playbook_key("public_order", "bandit_suppression"),
        playbook_key("public_order", "patrol_order"),
        playbook_key("public_order", "mountain_bandit_campaign"),
        playbook_key("public_order", "urban_order"),
        playbook_key("military", "border_readiness"),
    }
)


def is_spatial_domain(domain: str) -> bool:
    return (domain or "").strip() in SPATIAL_DOMAINS

SCOPE_CONTRACT: Dict[str, Any] = {
    "required_level": "soft_required",
    "acceptable_scope_types": [
        "route",
        "province",
        "prefecture",
        "county",
        "river_segment",
        "border_region",
        "mountain_region",
    ],
    "missing_behavior": "clarify_or_warn",
}

_OVERBROAD = re.compile(r"(天下|宇内|诸路|四海|海内|举国|全境)")

_ENGINEERING_SUBTYPE_KWS: Dict[str, Tuple[str, ...]] = {
    "river_dike": ("黄河", "河堤", "堤防", "决口", "河工", "防汛", "岁修", "堤岸", "河患"),
    "road_bridge": ("驿道", "桥梁", "栈道", "道路", "通道", "津渡"),
    "city_fortification": ("城墙", "城防", "外城", "关隘", "城楼"),
}

_ORDER_SUBTYPE_KWS: Dict[str, Tuple[str, ...]] = {
    "mountain_bandit": ("山寨", "险阻", "沿山", "洞蛮", "山地", "山林"),
    "urban_order": ("京师", "坊市", "夜禁", "盗窃", "开封", "汴京"),
    "patrol_order": ("巡缉", "缉盗", "保甲", "巡捕"),
    "bandit_suppression": ("剿匪", "剿捕", "盗贼", "匪患", "靖安", "剿讨"),
}

_TASK_SIGNAL_KWS: Dict[str, Tuple[str, ...]] = {
    playbook_key("military", "border_readiness"): (
        "边防",
        "边患",
        "整军",
        "军备",
        "备边",
        "戍边",
    ),
    playbook_key("engineering", "river_dike_repair"): (
        "堤防",
        "河工",
        "修缮",
        "黄河",
        "岁修",
        "河患",
        "防汛",
        "堤",
    ),
    playbook_key("public_order", "bandit_suppression"): (
        "剿",
        "盗",
        "匪",
        "靖安",
        "治安",
        "缉",
    ),
}

_CLARIFY_MSG = {
    playbook_key("engineering", "river_dike_repair"): (
        "请指明修缮哪一路、哪一府州，或哪段河工（如河北路、黄河堤段）。"
    ),
    playbook_key("public_order", "bandit_suppression"): (
        "请指明剿捕盗匪的路分、州县或山地区域（如荆湖南路、山寨一带）。"
    ),
    playbook_key("military", "border_readiness"): (
        "请指明整饬边防的路分或边区（如秦凤路、永兴军路、河北路）。"
    ),
}


def is_spatial_task_playbook(domain: str, task_key: str) -> bool:
    if is_spatial_domain(domain):
        return True
    return playbook_key(domain, task_key) in SPATIAL_TASK_PLAYBOOKS


def get_scope_contract(domain: str, task_key: str) -> Optional[Dict[str, Any]]:
    if not is_spatial_task_playbook(domain, task_key):
        return None
    return dict(SCOPE_CONTRACT)


def infer_engineering_subtype(edict_text: str) -> str:
    t = edict_text or ""
    for sub, kws in _ENGINEERING_SUBTYPE_KWS.items():
        if any(k in t for k in kws):
            return sub
    return "river_dike"


def infer_order_subtype(edict_text: str) -> str:
    t = edict_text or ""
    for sub, kws in _ORDER_SUBTYPE_KWS.items():
        if any(k in t for k in kws):
            return sub
    return "bandit_suppression"


def _has_task_signal(edict_text: str, domain: str, task_key: str) -> bool:
    kws = _TASK_SIGNAL_KWS.get(playbook_key(domain, task_key)) or ()
    t = edict_text or ""
    return any(k in t for k in kws)


def is_overbroad_scope_text(edict_text: str) -> bool:
    return bool(_OVERBROAD.search(edict_text or ""))


def location_scope_satisfied(loc: LocationSlot, *, edict_text: str = "") -> bool:
    if (loc.location_id or "").strip():
        return True
    if (loc.mode or "") in ("explicit", "inferred") and (loc.location_name_zh or loc.source_text or "").strip():
        if re.search(r"(路|州|军|府|县|京)", (loc.location_name_zh or loc.source_text or "")):
            return True
    if "黄河" in (edict_text or "") and (loc.scope_type or "") == "river_segment":
        return True
    if "黄河" in (edict_text or "") and (loc.location_id or "") == "yellow_river":
        return True
    return False


def compute_scope_confidence(
    *,
    loc: LocationSlot,
    edict_text: str,
    overbroad: bool,
) -> str:
    """high | medium | low"""
    if overbroad:
        return "low"
    if not location_scope_satisfied(loc, edict_text=edict_text):
        return "low"
    if (loc.location_id or "").strip() and (loc.confidence or 0) >= 0.8:
        st = (loc.scope_type or "").strip()
        if st in ("route", "province", "prefecture", "river_segment"):
            return "high"
        return "medium"
    if (loc.location_id or "") == "yellow_river" or "黄河" in (edict_text or ""):
        return "medium"
    if (loc.mode or "") == "inferred":
        return "medium"
    return "low"


def build_effect_scope(
    *,
    loc: LocationSlot,
    edict_text: str,
    domain: str,
) -> Dict[str, Any]:
    """区域化效果锚点；结算层可读，避免拍平为全国指标。"""
    t = edict_text or ""
    scope: Dict[str, Any] = {"type": "unknown", "id": "", "labels": []}
    if (loc.location_id or "").strip():
        scope["type"] = (loc.scope_type or "route").strip() or "route"
        scope["id"] = loc.location_id.strip()
        if loc.location_name_zh:
            scope["labels"].append(loc.location_name_zh)
    elif (loc.location_name_zh or "").strip():
        scope["type"] = "inferred_region"
        scope["id"] = ""
        scope["labels"].append(loc.location_name_zh.strip())
    if "黄河" in t:
        scope["river"] = "yellow_river"
        if scope["type"] == "unknown":
            scope["type"] = "river_segment"
    if domain == "engineering" and scope.get("river") == "yellow_river" and scope.get("id") == "hebei":
        scope["composite"] = "hebei_yellow_river"
    return scope


def _domain_has_task_signal(edict_text: str, domain: str) -> bool:
    from edict_execution_frame.domain_catalog import DOMAIN_TASK_CATALOG, _score_row

    for row in DOMAIN_TASK_CATALOG.get((domain or "").strip()) or []:
        if _score_row(edict_text or "", row, domain=domain)[0] > 0:
            return True
    return False


def evaluate_spatial_location_issues(
    *,
    edict_text: str,
    domain: str,
    task_key: str,
    location: LocationSlot,
) -> List[ClarificationIssue]:
    if not is_spatial_task_playbook(domain, task_key):
        return []
    if not _has_task_signal(edict_text, domain, task_key) and not _domain_has_task_signal(
        edict_text, domain
    ):
        return []
    pb = playbook_key(domain, task_key)
    issues: List[ClarificationIssue] = []
    overbroad = is_overbroad_scope_text(edict_text)
    satisfied = location_scope_satisfied(location, edict_text=edict_text)

    if overbroad:
        issues.append(
            ClarificationIssue(
                code="OVERBROAD_SCOPE",
                field="location",
                severity="error",
                blocks_execution=True,
                blocks_numbers=True,
                message_zh="诏意过宽（天下/诸路等），请改指明具体路分、河段或州县。",
                candidate_values=[],
            )
        )
        return issues

    if not satisfied:
        msg = _CLARIFY_MSG.get(pb) or "请补充施行地点（路分、府州或河段）。"
        issues.append(
            ClarificationIssue(
                code="MISSING_LOCATION",
                field="location",
                severity="error",
                blocks_execution=True,
                blocks_numbers=True,
                message_zh=msg,
                candidate_values=[],
            )
        )
    return issues


def enrich_spatial_task_meta(
    *,
    edict_text: str,
    domain: str,
    task_key: str,
    location: LocationSlot,
    base_meta: Dict[str, Any],
) -> Dict[str, Any]:
    meta = dict(base_meta or {})
    if not is_spatial_task_playbook(domain, task_key):
        return meta
    contract = get_scope_contract(domain, task_key) or {}
    overbroad = is_overbroad_scope_text(edict_text)
    conf = compute_scope_confidence(loc=location, edict_text=edict_text, overbroad=overbroad)
    meta["location_policy"] = {**(meta.get("location_policy") or {}), "scope_contract": contract}
    meta["scope_contract"] = contract
    meta["location_required"] = True
    meta["scope_confidence"] = conf
    meta["effect_scope"] = build_effect_scope(loc=location, edict_text=edict_text, domain=domain)
    if domain == "engineering":
        meta["engineering_subtype"] = infer_engineering_subtype(edict_text)
    if domain == "public_order":
        meta["order_subtype"] = infer_order_subtype(edict_text)
    if overbroad:
        meta["scope_overbroad"] = True
    return meta
