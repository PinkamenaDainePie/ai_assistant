# -*- coding: utf-8 -*-
"""从 parse_edict_to_effects 的 trace 抽取 SemanticFrame（不调用 LLM）。"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .policy_ir import SemanticFrame

_ANTI_KW = re.compile(
    r"(肃贪|反贪|整治贪|贪官|贪吏|吏治腐败|整饬吏治|严查.*贪|清查.*贪)"
)


def _layer3_dsl(trace: Dict[str, Any]) -> Dict[str, Any]:
    for st in trace.get("stages") or []:
        if not isinstance(st, dict):
            continue
        if st.get("layer") != "layer3_llm":
            continue
        dsl = st.get("dsl")
        if isinstance(dsl, dict):
            return dsl
    return {}


def _degree_to_intensity(degree: str) -> str:
    d = (degree or "").strip().lower()
    if d in ("high", "强", "严厉"):
        return "high"
    if d in ("low", "弱", "轻"):
        return "low"
    return "medium"


def _intent_to_policy_style(intent: str) -> str:
    if intent == "strict_governance":
        return "strict"
    if intent in ("tax_relief", "welfare", "disaster_relief"):
        return "moderate"
    return "unknown"


def _legacy_semantic_frame_from_trace(
    edict_text: str,
    parse_trace: Dict[str, Any],
) -> SemanticFrame:
    trace = parse_trace or {}
    dsl = _layer3_dsl(trace)
    intent = str(dsl.get("intent") or "").strip() or "unspecified"
    degree = str(dsl.get("degree") or "").strip()
    intensity = _degree_to_intensity(degree)

    ex = trace.get("executor_resolution") or {}
    if not isinstance(ex, dict):
        ex = {}
    executor_hint = str(ex.get("name") or "").strip()

    text = (edict_text or "").strip()
    anti = intent == "strict_governance" or bool(_ANTI_KW.search(text))

    if anti:
        domain = "anti_corruption"
        target = "local_corruption"
    else:
        domain = str(trace.get("edict_category") or "general")
        target = ""

    l3_conf = 0.0
    for st in trace.get("stages") or []:
        if isinstance(st, dict) and st.get("layer") == "layer3_llm":
            try:
                l3_conf = float(st.get("confidence") or 0.0)
            except (TypeError, ValueError):
                l3_conf = 0.0
            break

    dec = trace.get("decision_trace") or {}
    if isinstance(dec, dict) and dec.get("fallback_used"):
        conf = 0.45
    else:
        conf = max(0.35, min(0.95, l3_conf or 0.55))

    return SemanticFrame(
        domain=domain,
        intent=intent,
        target=target,
        intensity=intensity,
        executor_hint=executor_hint,
        policy_style=_intent_to_policy_style(intent),
        time_scope="current_quarter",
        confidence=round(conf, 3),
        raw_notes=str((dec or {}).get("fallback_reason") or "")[:200],
    )


def extract_semantic_frame_from_trace(
    edict_text: str,
    parse_trace: Dict[str, Any],
) -> SemanticFrame:
    from nlu_layer.pipeline import build_semantic_frame_from_trace

    return build_semantic_frame_from_trace(edict_text, parse_trace or {})
