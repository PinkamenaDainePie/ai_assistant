# -*- coding: utf-8 -*-
"""delayed_risk_seeds → session 压力队列（最小实现，供下季事件加权）。"""
from __future__ import annotations

from typing import Any, Dict, List

_PRESSURE: Dict[str, List[Dict[str, Any]]] = {}


def append_risk_seeds(session_id: str, seeds: List[Dict[str, Any]], *, quarter_index: int) -> None:
    sid = (session_id or "").strip()
    if not sid or not seeds:
        return
    bucket = _PRESSURE.setdefault(sid, [])
    for s in seeds:
        if not isinstance(s, dict):
            continue
        bucket.append(
            {
                "id": str(s.get("id") or ""),
                "weight": float(s.get("weight") or 0.1),
                "domain": str(s.get("domain") or ""),
                "queued_quarter": int(quarter_index),
            }
        )


def pop_due_pressures(session_id: str, quarter_index: int) -> List[Dict[str, Any]]:
    sid = (session_id or "").strip()
    if not sid:
        return []
    bucket = list(_PRESSURE.get(sid) or [])
    due = [x for x in bucket if int(x.get("queued_quarter") or 0) < int(quarter_index)]
    remain = [x for x in bucket if x not in due]
    _PRESSURE[sid] = remain
    return due


def get_event_tag_boost(session_id: str, quarter_index: int) -> List[str]:
    """将到期压力转为事件标签提示（供 EventService 扩展）。"""
    tags = []
    for p in pop_due_pressures(session_id, quarter_index):
        pid = str(p.get("id") or "").strip()
        if pid:
            tags.append("pressure:%s" % pid)
    return tags


def clear_session(session_id: str) -> None:
    _PRESSURE.pop((session_id or "").strip(), None)
