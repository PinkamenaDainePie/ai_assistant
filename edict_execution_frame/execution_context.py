# -*- coding: utf-8 -*-
"""解析帧之后的执行层快照（P2）：与 EdictExecutionFrame 分离，便于 trace。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from edict_execution_frame.cross_domain_signals import infer_cross_domain_signals
from edict_execution_frame.schemas import EdictExecutionFrame


def build_execution_context(
    frame: EdictExecutionFrame,
    *,
    edict_text: str = "",
    resolve_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tm = frame.task_meta or {}
    rm = dict(resolve_meta or {})
    cds = infer_cross_domain_signals(
        edict_text or "",
        domain=frame.task.domain or "",
        task_key=frame.task.task_key or "",
        resolution_status=frame.resolution_status or "",
    )
    return {
        "frame_id": frame.frame_id,
        "domain": frame.task.domain or "",
        "task_key": frame.task.task_key or "",
        "title_zh": frame.task.title_zh or "",
        "delegate_route": str(tm.get("delegate_route") or "mixed"),
        "location": frame.location.model_dump(),
        "target_entity": frame.target_entity.model_dump(),
        "clarification_issues": list(tm.get("clarification_issues") or []),
        "resolution_status": frame.resolution_status or "resolved",
        "execution_flags": {
            "is_auto_completed": bool(frame.is_auto_completed),
            "explicitness_class": frame.explicitness_class or "",
        },
        "scope_confidence": tm.get("scope_confidence"),
        "effect_scope": dict(tm.get("effect_scope") or {}),
        "engineering_subtype": tm.get("engineering_subtype"),
        "order_subtype": tm.get("order_subtype"),
        "location_required": tm.get("location_required"),
        "modifiers_summary": {
            "location_modifier_applied": bool((tm.get("location_modifier_applied") or {})),
            "location_resolution": dict(tm.get("location_resolution") or {}),
        },
        "primary_task": dict(cds.get("primary_task") or {}),
        "secondary_signals": list(cds.get("secondary_signals") or []),
        "multi_intent_policy": str(cds.get("multi_intent_policy") or ""),
        "resolve_meta_summary": {
            "task_path": rm.get("task_path"),
            "location_effect_merge": rm.get("location_effect_merge"),
            "immediate_outcome": rm.get("immediate_outcome"),
            "delayed_risk_seeds": rm.get("delayed_risk_seeds"),
            "narrative_seed_zh": rm.get("narrative_seed_zh"),
        },
        "original_text_snippet": (edict_text or "")[:200],
    }
