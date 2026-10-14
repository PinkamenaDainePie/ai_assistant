# -*- coding: utf-8 -*-
"""组装 API / 日志用 trace。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from edict_execution_frame.schemas import EdictExecutionFrame, FrameBuildTrace


def frame_to_dict(frame: EdictExecutionFrame) -> Dict[str, Any]:
    return frame.model_dump()


def build_frame_trace(
    *,
    mode: str,
    explicitness_class: str,
    original_text: str = "",
    final_frame: Optional[EdictExecutionFrame],
    resolved_effects: List[Dict[str, Any]],
    resolved_pack: Optional[Dict[str, Any]] = None,
    final_frame_narrative: str = "",
    select_applied: bool,
    internal_candidates: Optional[List[EdictExecutionFrame]] = None,
    rejected: Optional[List[Dict[str, Any]]] = None,
    priority_trace: Optional[List[str]] = None,
    admissibility_notes: Optional[List[str]] = None,
    auto_completion_notes_zh: str = "",
    error: str = "",
    execution_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rp = dict(resolved_pack or {})
    ft = FrameBuildTrace(
        mode=mode,
        explicitness_class=explicitness_class,
        original_text=original_text or "",
        final_frame=frame_to_dict(final_frame) if final_frame else None,
        final_frame_narrative=final_frame_narrative or (final_frame.normalized_command_zh if final_frame else ""),
        resolved_effects=list(resolved_effects or []),
        resolved_pack=rp,
        select_applied=bool(select_applied),
        internal_candidates=[frame_to_dict(x) for x in internal_candidates] if internal_candidates else None,
        rejected=rejected,
        priority_trace=priority_trace,
        admissibility_notes=admissibility_notes,
        error=error or "",
    )
    d = ft.model_dump()
    if auto_completion_notes_zh:
        d["auto_completion_notes_zh"] = auto_completion_notes_zh
    if execution_context is not None:
        d["execution_context"] = execution_context
    return d
