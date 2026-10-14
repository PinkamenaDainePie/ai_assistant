# -*- coding: utf-8 -*-
"""槽位提取：地点、敌对、承办、时长、财政信号（不含数值结算）。"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from edict_execution_frame.explicitness import (
    duration_explicit_from_text,
    extract_dual_ministers_in_text,
    extract_named_person_in_text,
)
from edict_execution_frame.hostile_entity import extract_target_entity_from_text
from edict_execution_frame.location_slot import extract_location_from_text
from nlu_layer.schemas import SlotFill

_FISCAL_AMOUNT = re.compile(
    r"(拨银|拨款|发银|赈银|给.*?银)([^，。；]*)|([一二三四五六七八九十百千万两\d]+)\s*两"
)
_FISCAL_ACTION = re.compile(r"(拨银|拨款|加税|蠲免|免税|减税|加征|赈银|内帑)")


def _slot_from_location(loc) -> Optional[SlotFill]:
    if not loc or (loc.mode or "") == "unknown":
        return None
    val = {
        "location_id": str(getattr(loc, "location_id", "") or ""),
        "location_name_zh": str(getattr(loc, "location_name_zh", "") or ""),
        "scope_type": str(getattr(loc, "scope_type", "") or ""),
    }
    src = str(getattr(loc, "source_text", "") or "")
    span = (0, 0)
    return SlotFill(
        name="location",
        value=val,
        span=span,
        confidence=float(getattr(loc, "confidence", 0.0) or 0.0),
        mode=str(getattr(loc, "mode", "unknown") or "unknown"),
    )


def _slot_from_target(te) -> Optional[SlotFill]:
    if not te or not (getattr(te, "entity_id", "") or getattr(te, "entity_name_zh", "")):
        return None
    val = {
        "entity_id": str(getattr(te, "entity_id", "") or ""),
        "entity_name_zh": str(getattr(te, "entity_name_zh", "") or ""),
        "entity_kind": str(getattr(te, "entity_kind", "") or ""),
    }
    return SlotFill(
        name="target_entity",
        value=val,
        span=(0, 0),
        confidence=float(getattr(te, "confidence", 0.0) or 0.0),
        mode=str(getattr(te, "mode", "unknown") or "unknown"),
    )


def extract_edict_slots(
    text: str,
    *,
    minister_names: Optional[Set[str]] = None,
    executor_name: str = "",
    executor_source: str = "none",
) -> Dict[str, SlotFill]:
    t = text or ""
    names = minister_names or set()
    slots: Dict[str, SlotFill] = {}

    te, spans = extract_target_entity_from_text(t)
    te_slot = _slot_from_target(te)
    if te_slot:
        slots["target_entity"] = te_slot

    loc = extract_location_from_text(t, reserved=spans)
    loc_slot = _slot_from_location(loc)
    if loc_slot:
        slots["location"] = loc_slot

    dual = extract_dual_ministers_in_text(t, names)
    if len(dual) == 2:
        slots["executor"] = SlotFill(
            name="executor",
            value={"mode": "dual_person", "person_names": dual},
            confidence=0.9,
            mode="explicit",
        )
    else:
        ex_name = (executor_name or "").strip()
        if not ex_name:
            ex_name = extract_named_person_in_text(t, names)
        if ex_name:
            slots["executor"] = SlotFill(
                name="executor",
                value={"mode": "person", "person_name": ex_name, "source": executor_source},
                confidence=0.88 if executor_source == "api" else 0.82,
                mode="explicit" if executor_source == "api" else ("explicit" if "命" in t else "inferred"),
            )

    q, explicit = duration_explicit_from_text(t)
    if explicit and q is not None:
        slots["duration"] = SlotFill(
            name="duration",
            value={"quarters": int(q)},
            confidence=0.9,
            mode="explicit",
        )
    else:
        slots["duration"] = SlotFill(
            name="duration",
            value={"quarters": None},
            confidence=0.4,
            mode="unknown",
        )

    fm = _FISCAL_ACTION.search(t)
    if fm:
        slots["fiscal_signal"] = SlotFill(
            name="fiscal_signal",
            value={"action": fm.group(0)},
            confidence=0.75,
            mode="explicit",
        )
    am = _FISCAL_AMOUNT.search(t)
    if am:
        raw = (am.group(2) or am.group(3) or "").strip()
        if raw:
            slots["fiscal_amount_hint"] = SlotFill(
                name="fiscal_amount_hint",
                value={"raw_text": raw},
                confidence=0.6,
                mode="explicit",
            )

    return slots


def extract_qa_slots(
    question: str,
    *,
    minister_name: str = "",
    minister_display_name: str = "",
) -> Dict[str, SlotFill]:
    nm = (minister_display_name or minister_name or "").strip()
    slots: Dict[str, SlotFill] = {}
    if nm:
        slots["requested_minister"] = SlotFill(
            name="requested_minister",
            value=nm,
            confidence=0.85,
            mode="explicit",
        )
    q = question or ""
    if "王安石" in q or "wang_anshi" in q.lower():
        slots["requested_minister"] = SlotFill(
            name="requested_minister",
            value="王安石",
            confidence=0.9,
            mode="explicit",
        )
    return slots
