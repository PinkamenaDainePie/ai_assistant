# -*- coding: utf-8 -*-
"""九域执行帧编排：parse trace → frame → resolved effects。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.execution_context import build_execution_context
from edict_execution_frame.frame_builder import build_final_execution_frame
from edict_execution_frame.multi_segment import try_multi_segment_edict_pipeline
from edict_execution_frame.resolver import resolve_frame_to_effects_and_tasks
from edict_execution_frame.trace import build_frame_trace
from edict_execution_frame.schemas import EdictExecutionFrame
from numeric_system.types import NumericData


def _append_frame_log(obj: Dict[str, Any]) -> None:
    path = (os.getenv("EDICT_FRAME_LOG_PATH") or "").strip()
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def run_edict_frame_pipeline(
    *,
    edict_text: str,
    edict_parse: Dict[str, Any],
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
    edict_executor_name: str = "",
    include_debug: bool = False,
) -> Tuple[Optional[EdictExecutionFrame], List[Dict[str, Any]], Dict[str, Any], bool]:
    """
    Returns:
        final_frame,
        resolved_effects,
        trace_dict,
        select_applied
    """
    if (edict_text or "").strip():
        multi = try_multi_segment_edict_pipeline(
            edict_text=edict_text,
            edict_parse=edict_parse,
            numeric_data=numeric_data,
            state_metrics=state_metrics,
            edict_executor_name=edict_executor_name,
        )
        if multi is not None:
            final, resolved, trace_extras, select_applied, all_frames = multi
            resolved_pack = dict(trace_extras.get("resolved_pack") or {})
            resolved_pack.setdefault("current_effects", resolved)
            narrative_line = str(resolved_pack.get("narrative") or final.normalized_command_zh or "")
            exec_ctx = build_execution_context(
                final,
                edict_text=edict_text or "",
                resolve_meta=resolved_pack.get("resolve_meta") if isinstance(resolved_pack.get("resolve_meta"), dict) else {},
            )
            if isinstance(exec_ctx, dict):
                exec_ctx["multi_domain_segments"] = trace_extras.get("segments")
            mode = "multi_domain" if int(trace_extras.get("segment_count") or 0) > 1 else "select"
            trace = build_frame_trace(
                mode=mode,
                explicitness_class=final.explicitness_class,
                original_text=edict_text or "",
                final_frame=final,
                resolved_effects=resolved,
                resolved_pack=resolved_pack,
                final_frame_narrative=narrative_line,
                select_applied=select_applied,
                internal_candidates=None,
                rejected=None,
                priority_trace=[f"multi_domain_llm:segments={trace_extras.get('segment_count')}"],
                admissibility_notes=None,
                auto_completion_notes_zh=getattr(final, "completion_notes_zh", "") or "",
                error="",
                execution_context=exec_ctx,
            )
            trace.update({k: v for k, v in trace_extras.items() if k != "resolved_pack"})
            if include_debug:
                trace["all_segment_frames"] = [f.model_dump() for f in all_frames]
            _append_frame_log(
                {
                    "kind": "edict_execution_frame",
                    "mode": mode,
                    "frame_id": final.frame_id,
                    "explicitness": final.explicitness_class,
                    "select_applied": select_applied,
                    "task_path": resolved_pack.get("task_path"),
                    "segment_count": trace_extras.get("segment_count"),
                }
            )
            return final, resolved, trace, select_applied

    final, prio, internal, rejected = build_final_execution_frame(
        edict_text=edict_text,
        edict_parse=edict_parse,
        numeric_data=numeric_data,
        edict_executor_name=edict_executor_name,
        include_internal_debug=include_debug,
    )

    pack = resolve_frame_to_effects_and_tasks(
        final,
        numeric_data=numeric_data,
        state_metrics=state_metrics,
    )
    resolved = list(pack.get("current_effects") or [])
    resolved_pack = {
        "current_effects": resolved,
        "created_tasks": list(pack.get("created_tasks") or []),
        "narrative": pack.get("narrative") or "",
        "event_seeds": list(pack.get("event_seeds") or []),
        "task_path": pack.get("task_path") or "",
        "resolve_meta": pack.get("resolve_meta") or {},
        "resolution_status": pack.get("resolution_status") or "",
        "ambiguity_status": pack.get("ambiguity_status") or "",
        "clarification_options": list(pack.get("clarification_options") or []),
        "delegation_blocked_reasons": list(pack.get("delegation_blocked_reasons") or []),
        "delegation_mode": pack.get("delegation_mode") or "",
    }

    select_applied = bool(resolved)
    narrative_line = final.normalized_command_zh or ""
    exec_ctx = build_execution_context(
        final,
        edict_text=edict_text or "",
        resolve_meta=resolved_pack.get("resolve_meta") if isinstance(resolved_pack.get("resolve_meta"), dict) else {},
    )

    trace = build_frame_trace(
        mode="select",
        explicitness_class=final.explicitness_class,
        original_text=edict_text or "",
        final_frame=final,
        resolved_effects=resolved,
        resolved_pack=resolved_pack,
        final_frame_narrative=narrative_line,
        select_applied=select_applied,
        internal_candidates=internal,
        rejected=rejected or None,
        priority_trace=prio,
        admissibility_notes=None,
        auto_completion_notes_zh=getattr(final, "completion_notes_zh", "") or "",
        error="",
        execution_context=exec_ctx,
    )
    if not include_debug:
        trace.pop("internal_candidates", None)
        trace.pop("rejected", None)

    _append_frame_log(
        {
            "kind": "edict_execution_frame",
            "mode": "select",
            "frame_id": final.frame_id,
            "explicitness": final.explicitness_class,
            "select_applied": select_applied,
            "task_path": resolved_pack.get("task_path"),
        }
    )
    return final, resolved, trace, select_applied
