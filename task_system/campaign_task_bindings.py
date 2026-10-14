# -*- coding: utf-8 -*-
"""熙宁战役：任务模板 / 随机事件 ↔ 剧情阶段（owner）归属与当季可用窗口。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .campaign_catalog import all_main_defs, get_main_def
from .campaign_scheduler import is_campaign_main_task

_BINDINGS_PATH = Path(__file__).resolve().parent / "catalog" / "campaign_task_bindings.json"

_AMBIENT_OWNER = "ambient:court_routine"

_POLICY_FLAG_OWNERS: Dict[str, str] = {
    "green_sprout_active": "policy:green_sprout_active",
    "corvee_active": "policy:corvee_active",
    "fiscal_reform_pack_active": "policy:fiscal_reform_pack_active",
    "old_party_pressure": "policy:old_party_pressure",
    "song_viet_war_active": "policy:song_viet_war_active",
    "hehuang_arc_active": "policy:hehuang_arc_active",
}

_CACHE: Optional[Dict[str, Any]] = None


def reload_campaign_task_bindings() -> None:
    global _CACHE
    _CACHE = None


def _load() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not _BINDINGS_PATH.is_file():
        _CACHE = {"template_bindings": {}, "event_bindings": {}, "owner_labels_zh": {}}
        return _CACHE
    try:
        _CACHE = json.loads(_BINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _CACHE = {"template_bindings": {}, "event_bindings": {}, "owner_labels_zh": {}}
    return _CACHE


def get_template_binding(template_id: str) -> Optional[Dict[str, Any]]:
    tid = str(template_id or "").strip()
    if not tid:
        return None
    return dict((_load().get("template_bindings") or {}).get(tid) or None or {})


def get_event_binding(event_id: str) -> Optional[Dict[str, Any]]:
    eid = str(event_id or "").strip()
    if not eid:
        return None
    row = (_load().get("event_bindings") or {}).get(eid)
    return dict(row) if isinstance(row, dict) else None


def owner_label_zh(owner_id: str) -> str:
    labels = dict(_load().get("owner_labels_zh") or {})
    oid = str(owner_id or "").strip()
    if oid in labels:
        return str(labels[oid])
    main = get_main_def(oid)
    if main is not None:
        return main.title
    return oid


def _binding_eligible(
    binding: Dict[str, Any],
    *,
    active_owners: Set[str],
    quarter_index: int,
    flags: Dict[str, Any],
) -> bool:
    if not binding:
        return False
    q = int(quarter_index)
    q_min = int(binding.get("quarter_min") or 1)
    q_max = int(binding.get("quarter_max") or 40)
    if q < q_min or q > q_max:
        return False
    req = dict(binding.get("requires_flags") or {})
    for k, v in req.items():
        if bool(flags.get(str(k))) != bool(v):
            return False
    primary = str(binding.get("primary_owner") or "").strip()
    eligible = {str(x).strip() for x in (binding.get("eligible_owners") or []) if str(x).strip()}
    if primary:
        eligible.add(primary)
    if not eligible:
        eligible.add(_AMBIENT_OWNER)
    return bool(eligible & active_owners)


def template_eligible_for_campaign(
    template_id: str,
    *,
    active_owners: Set[str],
    quarter_index: int,
    flags: Optional[Dict[str, Any]] = None,
) -> bool:
    binding = get_template_binding(template_id)
    if not binding:
        return False
    return _binding_eligible(
        binding,
        active_owners=active_owners,
        quarter_index=quarter_index,
        flags=flags if isinstance(flags, dict) else {},
    )


def event_eligible_for_campaign(
    event_id: str,
    *,
    active_owners: Set[str],
    quarter_index: int,
    flags: Optional[Dict[str, Any]] = None,
) -> bool:
    binding = get_event_binding(event_id)
    if not binding:
        return True
    return _binding_eligible(
        binding,
        active_owners=active_owners,
        quarter_index=quarter_index,
        flags=flags if isinstance(flags, dict) else {},
    )


def allowed_event_ids_for_campaign(
    *,
    active_owners: Set[str],
    quarter_index: int,
    flags: Optional[Dict[str, Any]] = None,
) -> Set[str]:
    fl = flags if isinstance(flags, dict) else {}
    out: Set[str] = set()
    for eid in (_load().get("event_bindings") or {}).keys():
        if event_eligible_for_campaign(
            str(eid),
            active_owners=active_owners,
            quarter_index=quarter_index,
            flags=fl,
        ):
            out.add(str(eid))
    return out


def primary_owner_for_template(template_id: str) -> str:
    binding = get_template_binding(template_id)
    if not binding:
        return ""
    return str(binding.get("primary_owner") or "").strip()


def resolve_active_story_owners(
    quarter_index: int,
    *,
    flags: Optional[Dict[str, Any]] = None,
    active_tasks: Optional[List[Any]] = None,
    completed_main_ids: Optional[Set[str]] = None,
) -> Set[str]:
    """本季剧情上下文：ambient + 未竟主线窗口 + 活跃 policy flag。"""
    q = int(quarter_index or 0)
    fl: Dict[str, Any] = dict(flags or {})
    completed = set(completed_main_ids or set())
    owners: Set[str] = {_AMBIENT_OWNER}

    active_main_ids: Set[str] = set()
    for t in active_tasks or []:
        if not is_campaign_main_task(t):
            continue
        if str(getattr(t, "status", "") or "") != "active":
            continue
        mid = str(getattr(t, "template_id", "") or "").strip()
        if mid:
            active_main_ids.add(mid)
            owners.add(mid)

    for main in all_main_defs():
        mid = str(main.id or "").strip()
        if not mid or mid in completed:
            continue
        sq = int(main.quarter_index or 0)
        if sq <= 0 or q < sq:
            continue
        grace = max(8, int(main.duration or 1) * 2)
        end_q = sq + max(int(main.duration or 1), 1) + grace
        if q > end_q and mid not in active_main_ids:
            continue
        if str(main.spawn_mode or "") == "conditional":
            if mid not in active_main_ids:
                from .campaign_scheduler import _spawn_conditions_met

                if not _spawn_conditions_met(main, flags=fl, metrics={}):
                    continue
        owners.add(mid)

    for flag_key, owner_id in _POLICY_FLAG_OWNERS.items():
        if fl.get(flag_key):
            owners.add(owner_id)

    return owners
