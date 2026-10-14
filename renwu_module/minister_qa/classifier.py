# -*- coding: utf-8 -*-
"""玩家问题类型分类（nlu_layer QA 通道）。"""
from __future__ import annotations

from typing import Any, Dict

from nlu_layer.pipeline import run_qa_nlu


def classify_question(
    question: str,
    minister_name: str = "",
    minister_display_name: str = "",
) -> Dict[str, Any]:
    nlu = run_qa_nlu(
        question,
        minister_name=minister_name,
        minister_display_name=minister_display_name,
    )
    nm = (minister_display_name or minister_name or "").strip()
    req_slot = (nlu.slots or {}).get("requested_minister")
    if req_slot and req_slot.value:
        nm = str(req_slot.value)
    out: Dict[str, Any] = {
        "question_type": nlu.intent.intent_id or "general",
        "domain": nlu.intent.domain_hint or "general",
        "requested_minister": nm,
        "nlu": nlu.to_trace_dict(),
    }
    return out
