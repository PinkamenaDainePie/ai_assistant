# -*- coding: utf-8 -*-
"""归一化诏书解释句。"""
from __future__ import annotations

from edict_execution_frame.schemas import EdictExecutionFrame


def build_normalized_command_zh(frame: EdictExecutionFrame) -> str:
    ex = frame.executor.display_name_zh or "有司"
    task = frame.task.title_zh or "政务"
    q = int(frame.duration.quarters or 1)
    loc = getattr(frame, "location", None)
    where = ""
    if loc is not None and (getattr(loc, "mode", "") or "") in ("explicit", "inferred"):
        name = (getattr(loc, "location_name_zh", "") or getattr(loc, "source_text", "") or "").strip()
        if name:
            where = f"在「{name}」"
    if where:
        return f"派 {ex} {where} 做 {task} 花 {q} 季"
    return f"派 {ex} 做 {task} 花 {q} 季"


def apply_normalized_line(frame: EdictExecutionFrame) -> EdictExecutionFrame:
    line = build_normalized_command_zh(frame)
    data = frame.model_dump()
    data["normalized_command_zh"] = line
    return EdictExecutionFrame(**data)
