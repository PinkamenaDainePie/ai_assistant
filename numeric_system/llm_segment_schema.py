# -*- coding: utf-8 -*-
"""多域诏书 LLM 分段 DSL：解析与 catalog 白名单校验。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from numeric_system.llm_intent_schema import ALLOWED_DEGREES, extract_json_object_text


@dataclass(frozen=True)
class LlmEdictSegment:
    domain: str
    text: str
    task_key: str = ""
    degree: str = "moderately"


# domain → legacy L3 intent（模型未填 intent 时兜底）
_DOMAIN_TO_L3_INTENT: Dict[str, str] = {
    "anti_corruption": "strict_governance",
    "disaster_relief": "disaster_relief",
    "fiscal": "tax_relief",
    "military": "military_expand",
    "diplomacy": "peace_and_trade",
}


@dataclass
class LlmMultiSegmentDsl:
    segments: List[LlmEdictSegment] = field(default_factory=list)
    intent: str = ""
    overall_degree: str = ""


def derive_legacy_intent(dsl: LlmMultiSegmentDsl) -> Tuple[str, str]:
    """从统一语义计划推导 L3 兼容 intent + degree。"""
    intent = (dsl.intent or "").strip()
    degree = (dsl.overall_degree or "").strip().lower()
    if degree not in ALLOWED_DEGREES and dsl.segments:
        degree = (dsl.segments[0].degree or "moderately").strip().lower()
    if degree not in ALLOWED_DEGREES:
        degree = "moderately"
    if intent and intent not in ("none", "unspecified"):
        return intent, degree
    if dsl.segments:
        dom = (dsl.segments[0].domain or "").strip().lower()
        mapped = _DOMAIN_TO_L3_INTENT.get(dom, "")
        if mapped:
            return mapped, degree
    return "none", degree


def parse_llm_multi_segment_json(
    raw_text: str,
    *,
    allowed_domains: Optional[Set[str]] = None,
    allowed_playbooks: Optional[Set[Tuple[str, str]]] = None,
    allowed_intents: Optional[Set[str]] = None,
    max_segments: int = 3,
) -> Tuple[Optional[LlmMultiSegmentDsl], Dict[str, Any]]:
    """解析统一语义计划 JSON（segments + 可选 intent/degree）；task_key 可选。"""
    trace: Dict[str, Any] = {
        "raw_text_preview": (raw_text or "")[:600],
        "parsed": None,
        "error": "",
        "rejected_segments": [],
    }
    t = extract_json_object_text(raw_text)
    if not t:
        trace["error"] = "empty_text"
        return None, trace
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        trace["error"] = "invalid_json"
        return None, trace
    if not isinstance(obj, dict):
        trace["error"] = "not_json_object"
        return None, trace

    raw_segments = obj.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        trace["error"] = "missing_segments"
        return None, trace

    out: List[LlmEdictSegment] = []
    domains = allowed_domains or set()
    playbooks = allowed_playbooks or set()

    for idx, item in enumerate(raw_segments[: max(1, int(max_segments))]):
        if not isinstance(item, dict):
            trace["rejected_segments"].append({"index": idx, "reason": "not_object"})
            continue
        domain = str(item.get("domain") or "").strip().lower()
        text = str(item.get("text") or item.get("text_span") or "").strip()
        task_key = str(item.get("task_key") or "").strip()
        degree = str(item.get("degree") or "moderately").strip().lower()
        if degree not in ALLOWED_DEGREES:
            degree = "moderately"
        if not domain:
            trace["rejected_segments"].append({"index": idx, "reason": "missing_domain"})
            continue
        if domains and domain not in domains:
            trace["rejected_segments"].append({"index": idx, "reason": "domain_not_allowed", "domain": domain})
            continue
        if not text:
            trace["rejected_segments"].append({"index": idx, "reason": "missing_text", "domain": domain})
            continue
        if task_key and playbooks and (domain, task_key) not in playbooks:
            trace["rejected_segments"].append(
                {"index": idx, "reason": "task_key_not_allowed", "domain": domain, "task_key": task_key}
            )
            task_key = ""
        out.append(LlmEdictSegment(domain=domain, text=text, task_key=task_key, degree=degree))

    if not out:
        trace["error"] = "no_valid_segments"
        return None, trace

    intent = str(obj.get("intent") or "").strip()
    intents = allowed_intents or set()
    if intent and intents and intent not in intents:
        trace.setdefault("warnings", []).append({"field": "intent", "reason": "not_in_whitelist", "value": intent})
        intent = ""
    degree_top = str(obj.get("degree") or obj.get("overall_degree") or "").strip().lower()
    if degree_top and degree_top not in ALLOWED_DEGREES:
        trace.setdefault("warnings", []).append({"field": "degree", "reason": "invalid", "value": degree_top})
        degree_top = ""

    dsl = LlmMultiSegmentDsl(segments=out, intent=intent, overall_degree=degree_top)
    leg_intent, leg_degree = derive_legacy_intent(dsl)
    trace["parsed"] = {
        "segment_count": len(out),
        "intent": leg_intent,
        "degree": leg_degree,
        "segments": [
            {"domain": s.domain, "task_key": s.task_key, "text_preview": s.text[:80], "degree": s.degree}
            for s in out
        ],
    }
    return dsl, trace
