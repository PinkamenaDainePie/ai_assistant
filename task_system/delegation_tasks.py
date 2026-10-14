# -*- coding: utf-8 -*-
"""诏书委派：生成挂起至下季结算的 TaskInstance。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from .task_models import TaskInstance


def build_delegation_task_instance(
    *,
    action_id: str,
    executor_display_name: str,
    assigned_quarter: int,
    metrics_snapshot: Dict[str, float],
    edict_summary: str = "",
    executor_context_snapshot: Optional[Dict[str, Any]] = None,
    phases_total: int = 1,
    task_key: str = "",
) -> TaskInstance:
    title = f"委派：{executor_display_name}（{action_id}）"
    desc = (edict_summary or "").strip()[:200]
    pt = max(1, min(5, int(phases_total or 1)))
    aq = int(assigned_quarter)
    return TaskInstance(
        instance_id=str(uuid.uuid4()),
        template_id=f"delegation_{action_id}",
        title=title,
        description=desc or title,
        category="delegation",
        status="active",
        assigned_quarter=aq,
        deadline_quarter=aq + pt,
        objectives=[],
        rewards=[],
        penalties=[],
        source="edict_delegation",
        resolution_kind="delegation",
        delegation={
            "action_id": action_id,
            "executor_name": executor_display_name,
            "task_key": (task_key or "").strip(),
            "metrics_snapshot": dict(metrics_snapshot or {}),
            "executor_context_snapshot": dict(executor_context_snapshot or {}),
            "phases_total": pt,
            "phase_index": 0,
        },
    )
