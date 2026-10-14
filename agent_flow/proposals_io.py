# -*- coding: utf-8 -*-
"""Workflow A（Agent A）proposals 与 effect 互转；战争场景地区状态放权。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from scenario_system.song_locations import (
    REGION_STATUS_NORMAL,
    REGION_STATUS_OCCUPIED,
    get_song_location_catalog,
    normalize_route_id,
)

# Agent A 在军事域可提案的地区状态（战争专用）
_WAR_REGION_STATUSES = frozenset({REGION_STATUS_NORMAL, REGION_STATUS_OCCUPIED})
_MAX_WAR_REGION_EFFECTS_PER_TURN = 3


def enrich_workflow_a_payload(
    payload: Dict[str, Any],
    *,
    region_status: Optional[Dict[str, Any]] = None,
    region_map_view: Optional[List[Dict[str, Any]]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
    include_region_catalog: bool = True,
) -> Dict[str, Any]:
    """在原有 Workflow A 入参上追加地区/战弧上下文（ADP content JSON）。"""
    out = dict(payload)
    out["region_status"] = dict(region_status or {})
    out["region_map_view"] = list(region_map_view or [])
    out["war_arcs"] = dict(war_arcs or {})
    if include_region_catalog:
        out["region_catalog"] = get_song_location_catalog()
    return out


def _war_context_active(
    *,
    domain: str,
    flags: Optional[Dict[str, Any]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
) -> bool:
    dom = (domain or "").strip().lower()
    if dom == "military":
        return True
    fl = dict(flags or {})
    if any(
        fl.get(k)
        for k in (
            "hehuang_arc_active",
            "song_viet_war_active",
            "hehuang_outcome_collapse",
            "song_viet_outcome_collapse",
        )
    ):
        return True
    arcs = dict((war_arcs or {}).get("arcs") or {})
    return bool(arcs)


def proposals_to_effects(
    proposals: Dict[str, Any],
    *,
    domain: str = "",
    quarter_index: int = 0,
    flags: Optional[Dict[str, Any]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    将 ADP proposals 转为 quarter settle effect_pool 条目。
    返回 (effects, trace)。
    """
    prop = dict(proposals or {})
    effects: List[Dict[str, Any]] = []
    trace: Dict[str, Any] = {
        "metric_deltas": 0,
        "flag_mutations": 0,
        "state_effects_in": 0,
        "state_effects_out": 0,
        "state_effects_dropped": [],
    }

    try:
        from task_system.metric_alignment import canonical_metric_key
    except ImportError:
        canonical_metric_key = lambda k: k  # type: ignore

    for d in prop.get("metric_deltas") or []:
        if not isinstance(d, dict):
            continue
        k = d.get("key")
        if k and canonical_metric_key(str(k)):
            effects.append(
                {
                    "action": "add_metric",
                    "key": k,
                    "value": float(d.get("value", 0.0)),
                    "source": "agent_flow",
                }
            )
            trace["metric_deltas"] += 1

    for f in prop.get("flag_mutations") or []:
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        if key:
            effects.append(
                {
                    "action": "set_flag",
                    "flag": key,
                    "value": bool(f.get("value", True)),
                    "source": "agent_flow",
                }
            )
            trace["flag_mutations"] += 1

    war_ok = _war_context_active(domain=domain, flags=flags, war_arcs=war_arcs)
    raw_state = list(prop.get("state_effects") or [])
    trace["state_effects_in"] = len(raw_state)
    if not war_ok:
        for item in raw_state:
            trace["state_effects_dropped"].append(
                {"reason": "not_war_context", "item": item}
            )
        return effects, trace

    region_count = 0
    for item in raw_state:
        if not isinstance(item, dict):
            trace["state_effects_dropped"].append({"reason": "not_object", "item": item})
            continue
        action = str(item.get("action") or "").strip()
        if action not in ("set_region_status", "clear_region_status"):
            trace["state_effects_dropped"].append(
                {"reason": "war_agent_only_region_actions", "item": item}
            )
            continue
        if region_count >= _MAX_WAR_REGION_EFFECTS_PER_TURN:
            trace["state_effects_dropped"].append({"reason": "max_per_turn", "item": item})
            continue

        if action == "clear_region_status":
            region = normalize_route_id(str(item.get("region") or "")) or str(item.get("region") or "").strip()
            if not region:
                trace["state_effects_dropped"].append({"reason": "missing_region", "item": item})
                continue
            effects.append(
                {"action": "clear_region_status", "region": region, "source": "agent_flow"}
            )
            region_count += 1
            trace["state_effects_out"] += 1
            continue

        region = normalize_route_id(str(item.get("region") or "")) or str(item.get("region") or "").strip()
        if not region:
            trace["state_effects_dropped"].append({"reason": "missing_region", "item": item})
            continue
        status = str(item.get("status") or REGION_STATUS_NORMAL).strip()
        if status not in _WAR_REGION_STATUSES:
            trace["state_effects_dropped"].append(
                {"reason": "invalid_status_for_war", "status": status, "item": item}
            )
            continue
        occupier = str(item.get("occupier") or "").strip()
        if status == REGION_STATUS_OCCUPIED and not occupier:
            trace["state_effects_dropped"].append({"reason": "occupied_needs_occupier", "item": item})
            continue
        eff: Dict[str, Any] = {
            "action": "set_region_status",
            "region": region,
            "status": status,
            "source": "agent_flow",
        }
        if occupier:
            eff["occupier"] = occupier
        if item.get("since_quarter") is not None:
            eff["since_quarter"] = int(item.get("since_quarter"))
        else:
            eff["since_quarter"] = int(quarter_index or 0)
        effects.append(eff)
        region_count += 1
        trace["state_effects_out"] += 1

    return effects, trace
