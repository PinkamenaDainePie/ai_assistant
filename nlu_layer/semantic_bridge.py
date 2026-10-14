# -*- coding: utf-8 -*-
"""NluResult → SemanticFrame（下游 policy / frame 共用）。"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from numeric_system.policy_ir import SemanticFrame
from nlu_layer.schemas import NluResult

_ANTI_KW = re.compile(
    r"(肃贪|反贪|整治贪|贪官|贪吏|吏治腐败|整饬吏治|严查.*贪|清查.*贪)"
)


def _policy_style(intent_id: str) -> str:
    if intent_id == "strict_governance":
        return "strict"
    if intent_id in ("tax_relief", "welfare", "disaster_relief"):
        return "moderate"
    return "unknown"


def semantic_frame_from_nlu(
    nlu: NluResult,
    edict_text: str = "",
    parse_trace: Optional[Dict[str, Any]] = None,
) -> SemanticFrame:
    trace = parse_trace or {}
    intent_id = (nlu.intent.intent_id or "").strip() or "unspecified"
    text = (edict_text or nlu.raw_text or "").strip()
    anti = intent_id == "strict_governance" or bool(_ANTI_KW.search(text))

    executor_hint = ""
    ex_slot = (nlu.slots or {}).get("executor")
    if ex_slot and isinstance(ex_slot.value, dict):
        if ex_slot.value.get("person_name"):
            executor_hint = str(ex_slot.value.get("person_name"))
        elif ex_slot.value.get("person_names"):
            names = ex_slot.value.get("person_names") or []
            if names:
                executor_hint = str(names[0])
    if not executor_hint:
        ex = trace.get("executor_resolution") or {}
        if isinstance(ex, dict):
            executor_hint = str(ex.get("name") or "").strip()

    if anti:
        domain = "anti_corruption"
        target = "local_corruption"
    else:
        from edict_execution_frame.domain_catalog import resolve_domain_from_semantic_and_text

        domain = resolve_domain_from_semantic_and_text(
            trace_domain=str(trace.get("edict_category") or "general"),
            l3_intent=intent_id if nlu.intent.source == "llm" else "",
            edict_text=text,
        )
        target = ""

    dec = trace.get("decision_trace") or {}
    if isinstance(dec, dict) and dec.get("fallback_used"):
        conf = 0.45
    else:
        conf = max(0.35, min(0.95, float(nlu.intent.confidence or 0.55)))

    return SemanticFrame(
        domain=domain,
        intent=intent_id,
        target=target,
        intensity=str(nlu.intent.intensity or "medium"),
        executor_hint=executor_hint,
        policy_style=_policy_style(intent_id),
        time_scope="current_quarter",
        confidence=round(conf, 3),
        raw_notes=str((dec or {}).get("fallback_reason") or "")[:200],
    )
