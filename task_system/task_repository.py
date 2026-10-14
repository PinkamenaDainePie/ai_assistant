# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .metric_alignment import normalize_metric_key_inplace
from .task_models import TaskInstance, TaskTemplate


class TaskRepository:
    @staticmethod
    def _normalize_metric_keys(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for x in (items or []):
            d = dict(x or {})
            normalize_metric_key_inplace(d)
            out.append(d)
        return out

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._templates: List[TaskTemplate] = []
        self._session_active: Dict[str, List[TaskInstance]] = {}
        self._session_history: Dict[str, List[Dict[str, Any]]] = {}
        self._session_tasks_settled_quarter: Dict[str, int] = {}
        self._session_task_quarter_end: Dict[str, Dict[str, Any]] = {}
        self.reload_templates()

    def reload_templates(self) -> None:
        self._templates = []
        for fp in sorted(self.templates_dir.glob("*.json")):
            try:
                raw = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            for obj in (raw or []):
                try:
                    self._templates.append(
                        TaskTemplate(
                            id=str(obj.get("id") or "").strip(),
                            title=str(obj.get("title") or "").strip(),
                            description=str(obj.get("description") or "").strip(),
                            category=str(obj.get("category") or "other").strip(),
                            difficulty=str(obj.get("difficulty") or "normal").strip(),
                            trigger_conditions=self._normalize_metric_keys(list(obj.get("trigger_conditions") or [])),
                            objectives=self._normalize_metric_keys(list(obj.get("objectives") or [])),
                            rewards=self._normalize_metric_keys(list(obj.get("rewards") or [])),
                            penalties=self._normalize_metric_keys(list(obj.get("penalties") or [])),
                            stall_penalties_per_quarter=self._normalize_metric_keys(
                                list(obj.get("stall_penalties_per_quarter") or [])
                            ),
                            duration=max(1, int(obj.get("duration") or 1)),
                            priority=int(obj.get("priority") or 50),
                            tags=[str(x) for x in (obj.get("tags") or [])],
                            mandatory=bool(obj.get("mandatory") or False),
                            min_reign_year=int(obj.get("min_reign_year") or 0),
                        )
                    )
                except Exception:
                    continue
        self._templates = [x for x in self._templates if x.id and x.title and x.objectives]

    def list_templates(self) -> List[TaskTemplate]:
        return list(self._templates)

    def get_active_tasks(self, session_id: str) -> List[TaskInstance]:
        return list(self._session_active.get(session_id, []))

    def set_active_tasks(self, session_id: str, tasks: List[TaskInstance]) -> None:
        self._session_active[session_id] = list(tasks)

    def append_history(self, session_id: str, item: Dict[str, Any]) -> None:
        self._session_history.setdefault(session_id, []).append(item)

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._session_history.get(session_id, []))

    def get_tasks_settled_quarter(self, session_id: str) -> int:
        return int(self._session_tasks_settled_quarter.get(session_id, -1))

    def get_last_task_quarter_end(self, session_id: str) -> Dict[str, Any]:
        return dict(self._session_task_quarter_end.get(session_id) or {})

    def set_last_task_quarter_end(
        self,
        session_id: str,
        *,
        quarter_index: int,
        payload: Dict[str, Any],
    ) -> None:
        self._session_tasks_settled_quarter[session_id] = int(quarter_index)
        self._session_task_quarter_end[session_id] = dict(payload or {})

