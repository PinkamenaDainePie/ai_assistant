# -*- coding: utf-8 -*-
"""国策因果触发的任务状态回写。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence


def apply_policy_task_status_updates(
    active_tasks: Sequence[Any],
    updates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """将 policy_tree.task_status_updates 应用到活跃任务列表。"""
    applied: List[Dict[str, Any]] = []
    if not updates:
        return applied
    for upd in updates:
        tid = str(upd.get("template_id") or "").strip()
        new_status = str(upd.get("status") or "").strip()
        if not tid or not new_status:
            continue
        for task in active_tasks or []:
            if str(getattr(task, "template_id", "") or "").strip() != tid:
                continue
            if str(getattr(task, "status", "") or "").strip() == new_status:
                continue
            task.status = new_status
            applied.append({"template_id": tid, "status": new_status, "edge_id": upd.get("edge_id")})
    return applied
