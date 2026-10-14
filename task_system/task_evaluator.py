# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

from .metric_alignment import metric_value
from .task_models import TaskInstance


class TaskEvaluator:
    @staticmethod
    def _check_objective(obj: Dict[str, Any], metrics: Dict[str, float]) -> bool:
        t = str(obj.get("type") or "").strip()
        key = str(obj.get("key") or "").strip()
        if t == "stat_at_least":
            return metric_value(metrics, key, 0.0) >= float(obj.get("value") or 0.0)
        if t == "stat_at_most":
            return metric_value(metrics, key, 0.0) <= float(obj.get("value") or 0.0)
        if t == "stat_reduce_by":
            base = float(obj.get("baseline_value") or metric_value(metrics, key, 0.0))
            delta = float(obj.get("value") or 0.0)
            return metric_value(metrics, key, 0.0) <= (base - delta)
        return False

    def evaluate(
        self,
        task: TaskInstance,
        metrics: Dict[str, float],
        quarter_index: int,
        session_id: str = "",
    ) -> Dict[str, Any]:
        rk = str(getattr(task, "resolution_kind", "objectives") or "objectives")
        if rk == "campaign_story":
            meta = dict(getattr(task, "campaign_meta", None) or {})
            completed = bool(meta.get("story_edict_done"))
        elif rk == "war_arc":
            from .war_arc import war_arc_task_completed

            completed = war_arc_task_completed(
                session_id,
                list(task.objectives or []),
                metrics,
            )
        else:
            completed = all(self._check_objective(obj, metrics) for obj in (task.objectives or []))
        expired = int(quarter_index) >= int(task.deadline_quarter)
        if completed:
            return {"result": "completed", "completed": True, "expired": False}
        if expired:
            return {"result": "failed", "completed": False, "expired": True}
        return {"result": "active", "completed": False, "expired": False}

