# -*- coding: utf-8 -*-
"""路分地点 + 遣命语境 → 具名大臣承办（财政/农业/赈灾等 provincial_delegate）。"""
from __future__ import annotations

import re
from typing import List, Optional, Set

from edict_execution_frame.domain_catalog import DomainTaskRow
from edict_execution_frame.explicitness import extract_named_person_in_text
from edict_execution_frame.hostile_entity import target_entity_ready
from edict_execution_frame.schemas import ExecutorSpec, LocationSlot, TargetEntitySlot
from numeric_system.types import Minister

_DELEGATION_CUE = re.compile(
    r"(赴|前往|巡抚|督理|监理|行在|就地|付之|付与|付予|遣|钦差|钦命|"
    r"命\s*[\u4e00-\u9fff]{2,4}\s*督|"
    r"督(?=[^。，；]{0,12}(路|州|军|府)))"
)
_LOCATION_DELEGATE_DOMAINS = frozenset(
    {
        "fiscal",
        "agriculture",
        "disaster_relief",
        "anti_corruption",
        "public_order",
        "engineering",
        "military",
    }
)

# 有路分/河段即可推举承办，不要求「遣/赴/督」等遣命词
_AUTO_DELEGATE_ON_LOCATION_DOMAINS = frozenset(
    {"engineering", "public_order", "military"}
)

_DOMAIN_ABILITY: dict = {
    "fiscal": "ability_finance",
    "agriculture": "ability_internal",
    "disaster_relief": "ability_internal",
    "anti_corruption": "ability_internal",
    "public_order": "ability_military",
    "engineering": "ability_internal",
    "military": "ability_military",
}


def has_location_delegation_cue(edict_text: str) -> bool:
    t = edict_text or ""
    if not _DELEGATION_CUE.search(t):
        return False
    return bool(re.search(r"(路|州|军|府|京|道)", t))


def location_ready(loc: LocationSlot) -> bool:
    if (loc.location_id or "").strip():
        return True
    if (loc.location_name_zh or "").strip() and loc.mode in ("explicit", "inferred"):
        return True
    return False


def top_ministers_for_domain(
    ministers: List[Minister],
    domain: str,
    *,
    limit: int = 3,
    exclude: Optional[Set[str]] = None,
    minister_status: Optional[Dict[str, Any]] = None,
) -> List[Minister]:
    ex = exclude or set()
    ms = minister_status or {}
    field = _DOMAIN_ABILITY.get((domain or "").strip(), "ability_internal")
    pool: List[Minister] = []
    for m in ministers:
        nm = (m.name or "").strip()
        if not nm or nm in ex:
            continue
        st = (ms.get(nm) or {}).get("status") or "active"
        if st != "active":
            continue
        pool.append(m)

    def score(m: Minister) -> float:
        return float(getattr(m, field, 0.0) or 0.0)

    pool.sort(key=score, reverse=True)
    return pool[:limit]


def enhance_executor_for_location_delegate(
    *,
    edict_text: str,
    task_row: DomainTaskRow,
    executor: ExecutorSpec,
    ministers: List[Minister],
    location: LocationSlot,
    domain: str,
    target_entity: Optional[TargetEntitySlot] = None,
    minister_status: Optional[Dict[str, Any]] = None,
) -> ExecutorSpec:
    """已有具名则保留；路分/敌对对象 + provincial 路由 → 补具名或表驱动人选。"""
    dom = (domain or "").strip()
    te = target_entity or TargetEntitySlot()
    if dom not in _LOCATION_DELEGATE_DOMAINS:
        return executor
    route = (task_row.delegate_route or "mixed").strip()
    if route not in ("provincial_delegate", "mixed", "imperial_commission"):
        return executor
    scope_ok = location_ready(location) or (
        dom == "military" and target_entity_ready(te)
    )
    if not scope_ok:
        return executor
    if dom not in _AUTO_DELEGATE_ON_LOCATION_DOMAINS and not has_location_delegation_cue(edict_text):
        return executor

    names = {(m.name or "").strip() for m in ministers if (m.name or "").strip()}
    if executor.mode in ("person", "dual_person") and (executor.person_name or executor.person_names):
        return executor.model_copy(update={"is_inferred": False})

    named = extract_named_person_in_text(edict_text or "", names)
    if not named:
        loose = re.search(
            r"命\s*([\u4e00-\u9fff]{2,4})(?=赴|前往|巡抚|督|监理)",
            edict_text or "",
        )
        if loose:
            named = loose.group(1).strip()
    if named:
        return ExecutorSpec(
            mode="person",
            display_name_zh=named,
            person_name=named,
            person_names=[named],
            institution_key="",
            is_inferred=named not in names,
        )

    if route == "central_direct":
        return executor

    pool = top_ministers_for_domain(ministers, dom, limit=1, minister_status=minister_status)
    if not pool:
        return executor
    m = pool[0]
    loc_zh = (location.location_name_zh or location.source_text or "").strip()
    foe_zh = (te.entity_name_zh or te.source_text or "").strip()
    if loc_zh and foe_zh:
        disp = "%s（赴%s御%s）" % (m.name.strip(), loc_zh, foe_zh)
    elif loc_zh:
        disp = "%s（赴%s）" % (m.name.strip(), loc_zh)
    elif foe_zh:
        disp = "%s（讨%s）" % (m.name.strip(), foe_zh)
    else:
        disp = m.name.strip()
    return ExecutorSpec(
        mode="person",
        display_name_zh=disp,
        person_name=m.name.strip(),
        person_names=[m.name.strip()],
        institution_key="",
        is_inferred=True,
    )
