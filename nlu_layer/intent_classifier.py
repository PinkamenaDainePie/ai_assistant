# -*- coding: utf-8 -*-
"""意图分类：L3 覆盖前以领域关键词占位；槽位由规则提取。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from nlu_layer.intent_catalog import (
    DOMAIN_KEYWORD_HINTS,
    QA_DOMAIN_RULES,
    QA_INTENT_RULES,
    domain_hint_for_intent,
)
from nlu_layer.schemas import IntentPrediction

_DEGREE_TO_INTENSITY = {
    "slightly": "low",
    "moderately": "medium",
    "heavily": "high",
    "high": "high",
    "low": "low",
}


def sim_score(text: str, phrases: List[str]) -> float:
    """供 legacy L2 / 测试桩使用。"""
    t = (text or "").strip()
    if not t:
        return 0.0
    best = 0.0
    text_set = set(c for c in t if not c.isspace())
    if not text_set:
        return 0.0
    for p in phrases:
        p_set = set(c for c in p if not c.isspace())
        if not p_set:
            continue
        j = len(text_set & p_set) / float(len(text_set | p_set))
        if p in t:
            j += 0.25
        best = max(best, j)
    return min(1.0, best)


def _domain_keyword_hint(text: str) -> Tuple[str, float]:
    t = text or ""
    best_dom = "general"
    best_sc = 0.0
    for needle, dom in DOMAIN_KEYWORD_HINTS:
        if needle in t:
            sc = 0.62 + min(0.15, len(needle) * 0.02)
            if sc > best_sc:
                best_sc = sc
                best_dom = dom
    return best_dom, best_sc


def _domain_keyword_fallback(text: str) -> IntentPrediction:
    kw_dom, kw_sc = _domain_keyword_hint(text)
    if kw_sc > 0:
        return IntentPrediction(
            intent_id="unspecified",
            domain_hint=kw_dom,
            confidence=round(kw_sc, 4),
            source="domain_keyword",
            alternatives=[],
        )
    return IntentPrediction(
        intent_id="unspecified",
        domain_hint="general",
        confidence=0.35,
        source="domain_keyword",
        alternatives=[],
    )


def classify_edict_intent(
    text: str,
    edict_category_ids: Optional[List[str]] = None,
) -> IntentPrediction:
    _ = edict_category_ids
    return _domain_keyword_fallback(text or "")


def apply_l3_intent_override(
    base: IntentPrediction,
    *,
    l3_dsl: Optional[Dict[str, Any]] = None,
    l3_confidence: float = 0.0,
) -> IntentPrediction:
    dsl = l3_dsl or {}
    intent_id = str(dsl.get("intent") or "").strip()
    if not intent_id or intent_id == "none":
        return base
    degree = str(dsl.get("degree") or "moderately").strip().lower()
    intensity = _DEGREE_TO_INTENSITY.get(degree, "medium")
    dom = domain_hint_for_intent(intent_id)
    if dom == "general":
        dom = base.domain_hint or "general"
    conf = max(float(l3_confidence or 0.0), float(base.confidence or 0.0), 0.55)
    alts = list(base.alternatives or [])
    if base.intent_id and base.intent_id != intent_id:
        alts.insert(0, (base.intent_id, float(base.confidence or 0.0)))
    return IntentPrediction(
        intent_id=intent_id,
        domain_hint=dom,
        confidence=round(conf, 4),
        source="llm",
        alternatives=alts[:4],
        degree=degree if degree in ("slightly", "moderately", "heavily") else "moderately",
        intensity=intensity,
    )


def classify_qa_intent(
    question: str,
    *,
    minister_name: str = "",
    minister_display_name: str = "",
) -> IntentPrediction:
    q = (question or "").strip()
    low = q.lower()
    nm = (minister_display_name or minister_name or "").strip()
    intent_id = "general"
    for rule in QA_INTENT_RULES:
        for pat in rule.get("patterns") or []:
            if re.search(pat, q):
                intent_id = str(rule.get("id") or "general")
                break
        if intent_id != "general":
            break
    domain_hint = "general"
    for pat, dom in QA_DOMAIN_RULES:
        if re.search(pat, q):
            domain_hint = dom
            break
    if "wang_anshi" in low or "王安石" in q:
        nm = nm or "王安石"
    slots_note = nm
    _ = slots_note
    conf = 0.72 if intent_id != "general" else 0.45
    if domain_hint != "general":
        conf = max(conf, 0.68)
    return IntentPrediction(
        intent_id=intent_id,
        domain_hint=domain_hint,
        confidence=round(conf, 4),
        source="qa_rule",
    )
