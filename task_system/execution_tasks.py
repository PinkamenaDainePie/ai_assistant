# -*- coding: utf-8 -*-
"""通用诏书跨季任务（非 legacy 肃贪 delegation）。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Sequence

from .edict_execution_ability import composite_ability_for_preview
from .task_models import TaskInstance


def build_edict_execution_task_instance(
    *,
    preview: Dict[str, Any],
    assigned_quarter: int,
    metrics_snapshot: Dict[str, float],
    edict_summary: str = "",
    executor_context_snapshot: Optional[Dict[str, Any]] = None,
    ministers: Optional[Sequence[Any]] = None,
) -> TaskInstance:
    """preview 来自 resolver 的 created_tasks 单条 dict。"""
    domain = str(preview.get("domain") or "general")
    task_key = str(preview.get("task_key") or "task")
    disp = str(preview.get("display_executor_zh") or "").strip() or "有司"
    title_zh = str(preview.get("title_zh") or preview.get("normalized_command_zh") or "诏书任务")
    phases_total = max(1, min(5, int(preview.get("phases_total") or 1)))
    aq = int(assigned_quarter)
    frame_id = str(preview.get("frame_id") or "").strip() or str(uuid.uuid4())[:12]
    inst_id = str(uuid.uuid4())
    comp_ab = round(composite_ability_for_preview(preview, ministers), 2)
    ex_names = list(preview.get("executors") or [])
    if not ex_names and str(preview.get("executor") or "").strip():
        ex_names = [str(preview.get("executor") or "").strip()]
    return TaskInstance(
        instance_id=inst_id,
        template_id="edict_execution_%s_%s" % (domain, task_key),
        title="诏书承办：%s" % title_zh,
        description=(edict_summary or "").strip()[:240] or title_zh,
        category="edict_execution",
        status="active",
        assigned_quarter=aq,
        deadline_quarter=aq + phases_total,
        objectives=[],
        rewards=[],
        penalties=[],
        source="edict_execution_frame",
        resolution_kind="edict_execution",
        delegation={},
        edict_execution={
            "frame_id": frame_id,
            "domain": domain,
            "task_key": task_key,
            "title_zh": title_zh,
            "display_executor_zh": disp,
            "normalized_command_zh": str(preview.get("normalized_command_zh") or ""),
            "phases_total": phases_total,
            "phase_index": 0,
            "risk_tags": list(preview.get("risk_tags") or []),
            "expected_effect_profile": dict(preview.get("expected_effect_profile") or {}),
            "intensity": str(preview.get("intensity") or "medium"),
            "metrics_snapshot": dict(metrics_snapshot or {}),
            "executor_context_snapshot": dict(executor_context_snapshot or {}),
            "is_delegated": bool(preview.get("is_delegated")),
            "execution_mode": str(preview.get("execution_mode") or "institutional"),
            "narrative_mode": str(preview.get("narrative_mode") or "delegated_execution"),
            "ability_weights_minister": dict(preview.get("ability_weights_minister") or {}),
            "executor_names": ex_names,
            "task_confidence": float(preview.get("task_confidence") or 0.55),
            "explicitness": str(preview.get("explicitness") or ""),
            "completion_notes_zh": str(preview.get("completion_notes_zh") or ""),
            "is_auto_completed": bool(preview.get("is_auto_completed")),
            "executor_composite_ability": comp_ab,
            "location_difficulty_delta": int(preview.get("location_difficulty_delta") or 0),
            "effect_scope": dict(preview.get("effect_scope") or {}),
            "scope_confidence": str(preview.get("scope_confidence") or ""),
            "order_subtype": str(preview.get("order_subtype") or ""),
            "engineering_subtype": str(preview.get("engineering_subtype") or ""),
            "ability_weights_minister": dict(preview.get("ability_weights_minister") or {}),
            "playbook_variant": str(preview.get("playbook_variant") or ""),
            "playbook_variant_label_zh": str(preview.get("playbook_variant_label_zh") or ""),
        },
    )
