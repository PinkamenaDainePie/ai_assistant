# -*- coding: utf-8 -*-
"""熙宁战役会话态：已完成主线、诏书白名单、季初待处理事件。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

_SESSION: Dict[str, Dict[str, Any]] = {}


def _bucket(session_id: str) -> Dict[str, Any]:
    sid = (session_id or "").strip()
    if not sid:
        return {}
    return _SESSION.setdefault(
        sid,
        {
            "completed_main_ids": set(),
            "allowed_edict_playbooks": [],
            "pending_event": None,
            "campaign_label_zh": "",
            "deferred_conditional_mains": set(),
            "applied_auto_fact_ids": set(),
            "l1_streaks": {"authority": 0, "viet_collapse": 0},
            "milestone_continue": False,
            "war_arcs": {},
        },
    )


def mark_main_completed(session_id: str, main_id: str) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["completed_main_ids"].add(str(main_id or "").strip())


def is_main_completed(session_id: str, main_id: str) -> bool:
    b = _SESSION.get((session_id or "").strip()) or {}
    return str(main_id or "").strip() in (b.get("completed_main_ids") or set())


def get_completed_main_ids(session_id: str) -> Set[str]:
    b = _SESSION.get((session_id or "").strip()) or {}
    return set(b.get("completed_main_ids") or set())


def set_allowed_edict_playbooks(session_id: str, playbooks: List[Dict[str, str]]) -> None:
    b = _bucket(session_id)
    b["allowed_edict_playbooks"] = list(playbooks or [])


def get_allowed_edict_playbooks(session_id: str) -> List[Dict[str, str]]:
    b = _SESSION.get((session_id or "").strip()) or {}
    return list(b.get("allowed_edict_playbooks") or [])


def set_pending_event(session_id: str, event: Any) -> None:
    b = _bucket(session_id)
    b["pending_event"] = event


def get_pending_event(session_id: str) -> Any:
    b = _SESSION.get((session_id or "").strip()) or {}
    return b.get("pending_event")


def set_campaign_label(session_id: str, label: str) -> None:
    b = _bucket(session_id)
    b["campaign_label_zh"] = str(label or "")


def get_campaign_label(session_id: str) -> str:
    b = _SESSION.get((session_id or "").strip()) or {}
    return str(b.get("campaign_label_zh") or "")


def defer_conditional_main(session_id: str, main_id: str) -> None:
    b = _bucket(session_id)
    if b is not None:
        b.setdefault("deferred_conditional_mains", set()).add(str(main_id or "").strip())


def pop_deferred_conditional_mains(session_id: str) -> Set[str]:
    b = _SESSION.get((session_id or "").strip()) or {}
    deferred = set(b.get("deferred_conditional_mains") or set())
    if b is not None:
        b["deferred_conditional_mains"] = set()
    return deferred


def mark_auto_fact_applied(session_id: str, fact_id: str) -> None:
    b = _bucket(session_id)
    if b is not None:
        b.setdefault("applied_auto_fact_ids", set()).add(str(fact_id or "").strip())


def get_applied_auto_fact_ids(session_id: str) -> Set[str]:
    b = _SESSION.get((session_id or "").strip()) or {}
    return set(b.get("applied_auto_fact_ids") or set())


def get_l1_streaks(session_id: str) -> Dict[str, int]:
    b = _SESSION.get((session_id or "").strip()) or {}
    raw = b.get("l1_streaks") or {}
    return {
        "authority": int(raw.get("authority") or 0),
        "viet_collapse": int(raw.get("viet_collapse") or 0),
    }


def set_l1_streaks(session_id: str, streaks: Dict[str, int]) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["l1_streaks"] = dict(streaks or {})


def is_milestone_continue(session_id: str) -> bool:
    b = _SESSION.get((session_id or "").strip()) or {}
    return bool(b.get("milestone_continue"))


def set_milestone_continue(session_id: str, value: bool = True) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["milestone_continue"] = bool(value)


def clear_session(session_id: str) -> None:
    _SESSION.pop((session_id or "").strip(), None)


def get_war_arcs(session_id: str) -> Dict[str, Dict[str, Any]]:
    b = _SESSION.get((session_id or "").strip()) or {}
    raw = b.get("war_arcs") or {}
    return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}


def get_war_arc(session_id: str, arc_id: str) -> Optional[Dict[str, Any]]:
    return get_war_arcs(session_id).get((arc_id or "").strip())


def set_war_arc(session_id: str, arc_id: str, state: Dict[str, Any]) -> None:
    b = _bucket(session_id)
    if b is not None:
        arcs = dict(b.get("war_arcs") or {})
        arcs[str(arc_id or "").strip()] = dict(state or {})
        b["war_arcs"] = arcs
