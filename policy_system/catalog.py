# -*- coding: utf-8 -*-
"""从熙宁战役 catalog 构建国策图（节点 + 边）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from policy_system.schemas import PolicyEdgeDef, PolicyGraphCatalog, PolicyNodeDef

_OVERRIDES_PATH = Path(__file__).resolve().parent / "catalog" / "policy_xining_overrides.json"
_CACHE: Optional[PolicyGraphCatalog] = None

_BRANCH_BY_FLAG = {
    "reform_mandate": "political",
    "wang_anshi_in_court": "political",
    "sansi_established": "fiscal_reform",
    "green_sprout_active": "fiscal_reform",
    "green_sprout_reform_failed": "fiscal_reform",
    "corvee_active": "fiscal_reform",
    "fiscal_reform_pack_active": "fiscal_reform",
    "shiyi_active": "fiscal_reform",
    "equalized_transport_active": "fiscal_reform",
    "fangtian_active": "fiscal_reform",
    "baojia_active": "military_reform",
    "baoma_active": "military_reform",
    "song_viet_war_active": "military_reform",
    "drought_crisis_resolved": "crisis",
    "wang_anshi_retired": "political_risk",
    "court_fierce_resistance": "conflict",
    "old_party_pressure": "conflict",
}


def playbook_target(domain: str, task_key: str) -> str:
    return "playbook:%s:%s" % (str(domain).strip(), str(task_key).strip())


def parse_event_target(target: str) -> Optional[str]:
    t = str(target or "").strip()
    if t.startswith("event:"):
        eid = t.split(":", 1)[1].strip()
    elif t.startswith("event_"):
        eid = t
    else:
        return None
    if not eid:
        return None
    if not eid.startswith("event_"):
        eid = "event_%s" % eid
    return eid


def parse_playbook_target(target: str) -> Optional[Dict[str, str]]:
    t = str(target or "").strip()
    if not t.startswith("playbook:"):
        return None
    parts = t.split(":", 2)
    if len(parts) != 3:
        return None
    dom, tk = parts[1].strip(), parts[2].strip()
    if not dom or not tk:
        return None
    return {"domain": dom, "task_key": tk}


def _load_overrides() -> Dict:
    if not _OVERRIDES_PATH.is_file():
        return {"edges": [], "node_titles_zh": {}}
    try:
        return json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"edges": [], "node_titles_zh": {}}


def _node_title_zh(nid: str, default: str, titles: Dict[str, str]) -> str:
    return str(titles.get(nid) or default or nid)


def build_xining_catalog() -> PolicyGraphCatalog:
    from task_system.campaign_catalog import (
        FLAG_PLAYBOOK_UNLOCKS,
        all_auto_facts,
        all_main_defs,
    )

    overrides = _load_overrides()
    title_map = dict(overrides.get("node_titles_zh") or {})

    nodes: Dict[str, PolicyNodeDef] = {}
    edges: List[PolicyEdgeDef] = []
    flag_ids: Set[str] = set()

    for main in all_main_defs():
        nodes[main.id] = PolicyNodeDef(
            id=main.id,
            title_zh=main.title,
            branch="milestone",
            kind="milestone",
            initial_status="available",
            linked_main_id=main.id,
            passive_effects_per_quarter=list(main.passive_effects_per_quarter or []),
        )
        for pb in main.allowed_edict_playbooks or []:
            dom = str(pb.get("domain") or "").strip()
            tk = str(pb.get("task_key") or "").strip()
            if not dom or not tk:
                continue
            edges.append(
                PolicyEdgeDef(
                    id="unlock_%s_%s_%s" % (main.id, dom, tk),
                    from_id=main.id,
                    to_id=playbook_target(dom, tk),
                    edge_type="unlocks",
                    condition={"node_status_in": ["active", "completed"]},
                )
            )
        for flag, val in (main.on_complete_flags or {}).items():
            if not val:
                continue
            flag_ids.add(str(flag))
            edges.append(
                PolicyEdgeDef(
                    id="complete_%s_%s" % (main.id, flag),
                    from_id=main.id,
                    to_id=str(flag),
                    edge_type="completes",
                    effect={"set_flag": str(flag)},
                )
            )

    for flag in sorted(flag_ids):
        nodes[flag] = PolicyNodeDef(
            id=flag,
            title_zh=_node_title_zh(flag, flag, title_map),
            branch=_BRANCH_BY_FLAG.get(flag, "reform"),
            kind="reform",
            initial_status="locked",
            linked_flag=flag,
        )

    for flag, playbooks in (FLAG_PLAYBOOK_UNLOCKS or {}).items():
        if flag not in nodes:
            nodes[flag] = PolicyNodeDef(
                id=flag,
                title_zh=_node_title_zh(flag, flag, title_map),
                branch=_BRANCH_BY_FLAG.get(flag, "reform"),
                kind="reform",
                initial_status="locked",
                linked_flag=flag,
            )
        for pb in playbooks or []:
            dom = str(pb.get("domain") or "").strip()
            tk = str(pb.get("task_key") or "").strip()
            if not dom or not tk:
                continue
            edges.append(
                PolicyEdgeDef(
                    id="flag_unlock_%s_%s_%s" % (flag, dom, tk),
                    from_id=flag,
                    to_id=playbook_target(dom, tk),
                    edge_type="unlocks",
                    condition={"node_status": "active", "flag_true": flag},
                )
            )

    for fact in all_auto_facts():
        fid = str(fact.id or "").strip()
        if not fid:
            continue
        nodes[fid] = PolicyNodeDef(
            id=fid,
            title_zh=_node_title_zh(fid, fid, title_map),
            branch="auto",
            kind="auto",
            initial_status="locked",
            passive_effects_per_quarter=list(fact.passive_effects_per_quarter or []),
        )
        req = fact.requires_flags or {}
        if req:
            req_flag = next(iter(req.keys()), "")
            if req_flag:
                edges.append(
                    PolicyEdgeDef(
                        id="requires_%s_%s" % (fid, req_flag),
                        from_id=req_flag,
                        to_id=fid,
                        edge_type="requires",
                        condition={"flag_true": req_flag},
                    )
                )

    for flag_key in ("green_sprout_expanded", "old_party_pressure", "wang_anshi_leading_reform"):
        if flag_key not in nodes:
            nodes[flag_key] = PolicyNodeDef(
                id=flag_key,
                title_zh=_node_title_zh(flag_key, flag_key, title_map),
                branch=_BRANCH_BY_FLAG.get(flag_key, "reform"),
                kind="reform",
                initial_status="locked",
                linked_flag=flag_key,
            )

    for nobj in overrides.get("nodes") or []:
        if not isinstance(nobj, dict):
            continue
        nid = str(nobj.get("id") or "").strip()
        if not nid:
            continue
        nodes[nid] = PolicyNodeDef(
            id=nid,
            title_zh=_node_title_zh(nid, str(nobj.get("title_zh") or nid), title_map),
            branch=str(nobj.get("branch") or _BRANCH_BY_FLAG.get(nid, "general")),
            kind=str(nobj.get("kind") or "risk"),
            initial_status=str(nobj.get("initial_status") or "locked"),
            linked_flag=str(nobj.get("linked_flag") or nid),
            passive_effects_per_quarter=list(nobj.get("passive_effects_per_quarter") or []),
            progress_max=int(nobj.get("progress_max") or 100),
        )

    for obj in overrides.get("edges") or []:
        if not isinstance(obj, dict):
            continue
        eid = str(obj.get("id") or "").strip()
        frm = str(obj.get("from") or obj.get("from_id") or "").strip()
        to = str(obj.get("to") or obj.get("to_id") or "").strip()
        et = str(obj.get("type") or obj.get("edge_type") or "").strip()
        if eid and frm and to and et:
            edges.append(
                PolicyEdgeDef(
                    id=eid,
                    from_id=frm,
                    to_id=to,
                    edge_type=et,
                    condition=dict(obj.get("condition") or {}),
                    effect=dict(obj.get("effect") or {}),
                    probability=float(obj.get("probability") or 0.0),
                )
            )

    return PolicyGraphCatalog(scenario="song_xining", nodes=nodes, edges=edges)


def get_xining_catalog() -> PolicyGraphCatalog:
    global _CACHE
    if _CACHE is None:
        _CACHE = build_xining_catalog()
    return _CACHE


def reload_catalog() -> PolicyGraphCatalog:
    global _CACHE
    _CACHE = build_xining_catalog()
    return _CACHE
