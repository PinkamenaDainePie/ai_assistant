# -*- coding: utf-8 -*-
"""LLM Layer3 DSL schema (whitelist) for edict parsing."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


ALLOWED_DEGREES = ("slightly", "moderately", "heavily")


@dataclass(frozen=True)
class LlmIntentDsl:
    intent: str
    degree: str = "moderately"


def extract_json_object_text(raw_text: str) -> str:
    """从 LLM 原文抽取 JSON 对象字符串（容忍 markdown 代码块与前后缀）。"""
    t = (raw_text or "").strip()
    if not t:
        return ""
    fence = _JSON_FENCE_RE.search(t)
    if fence:
        t = fence.group(1).strip()
    if t.startswith("{") and t.endswith("}"):
        return t
    mobj = _JSON_OBJECT_RE.search(t)
    return mobj.group(0).strip() if mobj else t


def build_intent_whitelist(intent_catalog: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for item in intent_catalog or []:
        intent = str(item.get("intent", "")).strip()
        if intent:
            out.append(intent)
    return sorted(set(out))


def parse_llm_dsl_json(
    raw_text: str,
    *,
    allowed_intents: Optional[List[str]] = None,
) -> Tuple[Optional[LlmIntentDsl], Dict[str, Any]]:
    trace: Dict[str, Any] = {
        "raw_text_preview": (raw_text or "")[:400],
        "parsed": None,
        "error": "",
        "degree_provided": False,
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

    intent = str(obj.get("intent", "")).strip()
    trace["degree_provided"] = "degree" in obj
    degree = str(obj.get("degree", "moderately")).strip().lower()
    if not intent:
        trace["error"] = "missing_intent"
        return None, trace
    if allowed_intents and intent not in set(allowed_intents):
        trace["error"] = "intent_not_allowed"
        trace["parsed"] = {"intent": intent, "degree": degree}
        return None, trace
    if degree not in ALLOWED_DEGREES:
        degree = "moderately"
    dsl = LlmIntentDsl(intent=intent, degree=degree)
    trace["parsed"] = {"intent": dsl.intent, "degree": dsl.degree}
    return dsl, trace


def apply_degree_hint(
    dsl: LlmIntentDsl,
    *,
    degree_hint: str,
    degree_provided: bool,
    parse_error: str,
) -> Tuple[LlmIntentDsl, Dict[str, Any]]:
    trace: Dict[str, Any] = {
        "degree_hint": degree_hint or "",
        "degree_provided": bool(degree_provided),
        "parse_error": parse_error or "",
        "applied": False,
    }
    hint = str(degree_hint or "").strip().lower()
    if degree_provided:
        return dsl, trace
    if hint not in ALLOWED_DEGREES:
        return dsl, trace
    out = LlmIntentDsl(intent=dsl.intent, degree=hint)
    trace["applied"] = True
    return out, trace

