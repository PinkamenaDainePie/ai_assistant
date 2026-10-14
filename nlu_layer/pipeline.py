# -*- coding: utf-8 -*-
"""NLU 编排：L3 意图（覆盖关键词占位）+ 规则槽位 + 校验。"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set

from nlu_layer.intent_classifier import apply_l3_intent_override, classify_edict_intent, classify_qa_intent
from nlu_layer.schemas import NluResult
from nlu_layer.semantic_bridge import semantic_frame_from_nlu
from nlu_layer.slot_extractors import extract_edict_slots, extract_qa_slots
from nlu_layer.validator import validate_nlu_result


def run_edict_nlu(
    text: str,
    *,
    edict_category_ids: Optional[List[str]] = None,
    minister_names: Optional[Set[str]] = None,
    executor_name: str = "",
    executor_source: str = "none",
    l3_dsl: Optional[Dict[str, Any]] = None,
    l3_confidence: float = 0.0,
) -> NluResult:
    t0 = time.perf_counter()
    intent = classify_edict_intent(text, edict_category_ids)
    if l3_dsl:
        intent = apply_l3_intent_override(intent, l3_dsl=l3_dsl, l3_confidence=l3_confidence)
    slots = extract_edict_slots(
        text,
        minister_names=minister_names,
        executor_name=executor_name,
        executor_source=executor_source,
    )
    result = NluResult(
        channel="edict",
        raw_text=text or "",
        intent=intent,
        slots=slots,
        edict_category_ids=list(edict_category_ids or []),
    )
    ok, reasons = validate_nlu_result(result)
    result.validated = ok
    result.blocked_reasons = reasons
    _ = time.perf_counter() - t0
    return result


def run_qa_nlu(
    question: str,
    *,
    minister_name: str = "",
    minister_display_name: str = "",
) -> NluResult:
    intent = classify_qa_intent(
        question,
        minister_name=minister_name,
        minister_display_name=minister_display_name,
    )
    slots = extract_qa_slots(
        question,
        minister_name=minister_name,
        minister_display_name=minister_display_name,
    )
    result = NluResult(
        channel="qa",
        raw_text=question or "",
        intent=intent,
        slots=slots,
    )
    ok, reasons = validate_nlu_result(result)
    result.validated = ok
    result.blocked_reasons = reasons
    return result


def nlu_from_trace(trace: Dict[str, Any], *, edict_text: str = "") -> Optional[NluResult]:
    raw = (trace or {}).get("nlu")
    if not isinstance(raw, dict):
        return None
    return NluResult.from_trace_dict(raw, edict_text=edict_text)


def _l3_from_stages(trace: Dict[str, Any]) -> tuple:
    for st in reversed((trace or {}).get("stages") or []):
        if not isinstance(st, dict) or st.get("layer") != "layer3_llm":
            continue
        dsl = st.get("dsl") or {}
        conf = float(st.get("confidence") or 0.0)
        if isinstance(dsl, dict):
            return dsl, conf
    return {}, 0.0


def ensure_nlu_in_trace(
    trace: Dict[str, Any],
    edict_text: str,
    *,
    edict_category_ids: Optional[List[str]] = None,
    minister_names: Optional[Set[str]] = None,
    executor_name: str = "",
    executor_source: str = "none",
) -> Dict[str, Any]:
    """trace 无 nlu 时从正文 + stages 重建（兼容测试 mock trace）。"""
    if not isinstance(trace, dict):
        trace = {}
    if trace.get("nlu"):
        return trace
    ex = trace.get("executor_resolution") or {}
    if isinstance(ex, dict):
        if not executor_name:
            executor_name = str(ex.get("name") or "").strip()
        if executor_source == "none":
            executor_source = str(ex.get("source") or "none")
    cats = edict_category_ids
    if not cats:
        cats = list(trace.get("edict_categories") or [])
        if not cats and trace.get("edict_category"):
            cats = [str(trace.get("edict_category"))]
    l3_dsl, l3_conf = _l3_from_stages(trace)
    nlu = run_edict_nlu(
        edict_text,
        edict_category_ids=cats,
        minister_names=minister_names,
        executor_name=executor_name,
        executor_source=executor_source,
        l3_dsl=l3_dsl if l3_dsl else None,
        l3_confidence=l3_conf,
    )
    trace["nlu"] = nlu.to_trace_dict()
    return trace


def merge_l3_into_nlu_trace(trace: Dict[str, Any], l3_trace: Dict[str, Any]) -> None:
    if not isinstance(trace, dict):
        return
    raw = trace.get("nlu")
    edict_text = str((raw or {}).get("raw_text") or "")
    nlu = NluResult.from_trace_dict(raw, edict_text=edict_text) if isinstance(raw, dict) else None
    if nlu is None:
        return
    dsl = (l3_trace or {}).get("dsl") or {}
    conf = float((l3_trace or {}).get("confidence") or 0.0)
    if not isinstance(dsl, dict) or not dsl.get("intent"):
        return
    nlu.intent = apply_l3_intent_override(nlu.intent, l3_dsl=dsl, l3_confidence=conf)
    ok, reasons = validate_nlu_result(nlu)
    nlu.validated = ok
    nlu.blocked_reasons = reasons
    trace["nlu"] = nlu.to_trace_dict()


def build_semantic_frame_from_trace(
    edict_text: str,
    parse_trace: Dict[str, Any],
    *,
    minister_names: Optional[Set[str]] = None,
):
    trace = parse_trace if isinstance(parse_trace, dict) else {}
    ensure_nlu_in_trace(
        trace,
        edict_text,
        minister_names=minister_names,
    )
    nlu = nlu_from_trace(trace, edict_text=edict_text)
    if nlu is not None:
        return semantic_frame_from_nlu(nlu, edict_text, trace)
    from numeric_system.semantic_frame_extract import _legacy_semantic_frame_from_trace

    return _legacy_semantic_frame_from_trace(edict_text, trace)
