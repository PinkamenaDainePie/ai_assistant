# -*- coding: utf-8 -*-
"""敌对势力槽位：解析、澄清、与地点修正合并。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from edict_execution_frame.clarification import ClarificationIssue
from edict_execution_frame.hostile_profiles import get_hostile_modifier, merge_modifier_dicts
from edict_execution_frame.schemas import TargetEntitySlot

try:
    from scenario_system.song_hostiles import is_song_scenario, song_hostile_entity_aliases
except ImportError:
    is_song_scenario = lambda **_: False  # type: ignore
    song_hostile_entity_aliases = lambda: []  # type: ignore

# 非宋场景兜底
_LEGACY_ENTITIES: List[Tuple[str, str, str, str]] = [
    ("女真", "nvzhen", "女真", "foreign_polity"),
    ("鞑靼", "dadan", "鞑靼", "foreign_polity"),
    ("瓦剌", "wala", "瓦剌", "foreign_polity"),
    ("朝鲜", "chaoxian", "朝鲜", "foreign_polity"),
]

_CAMPAIGN_CUE = re.compile(r"(讨伐|征讨|进兵|攻伐|开战|击贼|讨贼)")
_BORDER_CAMPAIGN_KW = ("讨伐", "征讨", "进兵", "攻伐", "开战", "击贼")


def active_hostile_aliases() -> List[Tuple[str, str, str, str]]:
    if is_song_scenario():
        return song_hostile_entity_aliases()
    out = list(_LEGACY_ENTITIES)
    out.sort(key=lambda x: len(x[0]), reverse=True)
    return out


def extract_target_entity_from_text(text: str) -> Tuple[TargetEntitySlot, List[Tuple[int, int]]]:
    t = text or ""
    spans: List[Tuple[int, int]] = []
    for needle, eid, name, kind in active_hostile_aliases():
        idx = t.find(needle)
        if idx >= 0:
            spans.append((idx, idx + len(needle)))
            return (
                TargetEntitySlot(
                    mode="explicit",
                    entity_id=eid,
                    entity_name_zh=name,
                    entity_kind=kind,
                    source_text=needle,
                    confidence=0.9,
                ),
                spans,
            )
    return TargetEntitySlot(), spans


def target_entity_ready(te: TargetEntitySlot) -> bool:
    return bool((te.entity_id or "").strip() or (te.entity_name_zh or "").strip())


def build_military_effect_scope(
    *,
    loc_id: str,
    loc_name_zh: str,
    loc_scope_type: str,
    target_entity: TargetEntitySlot,
) -> Dict[str, Any]:
    scope: Dict[str, Any] = {"type": "unknown", "id": "", "labels": []}
    if (target_entity.entity_id or "").strip():
        scope["hostile"] = target_entity.entity_id.strip()
        scope["type"] = "hostile_polity"
        scope["id"] = target_entity.entity_id.strip()
        if target_entity.entity_name_zh:
            scope["labels"].append(target_entity.entity_name_zh)
    if (loc_id or "").strip():
        scope["route"] = loc_id.strip()
        if loc_name_zh:
            scope["labels"].append(loc_name_zh)
        if scope["type"] == "unknown":
            scope["type"] = (loc_scope_type or "route").strip() or "route"
        if not scope.get("id"):
            scope["id"] = loc_id.strip()
    if scope.get("hostile") and scope.get("route"):
        scope["composite"] = "%s_%s" % (scope["route"], scope["hostile"])
    return scope


def evaluate_hostile_entity_issues(
    *,
    edict_text: str,
    domain: str,
    task_key: str,
    target_entity: TargetEntitySlot,
) -> List[ClarificationIssue]:
    if (domain or "").strip() != "military" or (task_key or "").strip() != "campaign_against":
        return []
    t = edict_text or ""
    if not any(k in t for k in _BORDER_CAMPAIGN_KW) and not _CAMPAIGN_CUE.search(t):
        return []
    if target_entity_ready(target_entity):
        return []
    return [
        ClarificationIssue(
            code="MISSING_HOSTILE_ENTITY",
            field="target_entity",
            severity="error",
            blocks_execution=True,
            blocks_numbers=True,
            message_zh="请指明讨伐或攻伐的敌对势力（如西夏、辽、吐蕃）。",
            candidate_values=[],
        )
    ]


def hostile_modifier_for_frame(domain: str, task_key: str, entity_id: str) -> Dict[str, Any]:
    return get_hostile_modifier(domain, task_key, entity_id)
