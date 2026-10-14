# -*- coding: utf-8 -*-
"""NLU 输出 catalog 白名单校验。"""
from __future__ import annotations

from typing import List, Tuple

from nlu_layer.intent_catalog import INTENT_CATALOG
from nlu_layer.schemas import NluResult

_QA_INTENTS = frozenset(
    {
        "general",
        "draft_decree",
        "predict_effect",
        "compare_policy",
        "recommend_policy",
        "challenge_policy",
        "explain_state",
    }
)

_EDICT_EXTRA = frozenset({"unspecified", "none"})


def _edict_whitelist() -> frozenset:
    ids = {str(item.get("intent") or "").strip() for item in INTENT_CATALOG}
    ids |= _EDICT_EXTRA
    return frozenset(x for x in ids if x)


def validate_nlu_result(result: NluResult) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    intent_id = (result.intent.intent_id or "").strip()
    if result.channel == "qa":
        if intent_id not in _QA_INTENTS:
            reasons.append("qa_intent_not_allowed:%s" % intent_id)
    else:
        if intent_id not in _edict_whitelist():
            reasons.append("edict_intent_not_allowed:%s" % intent_id)
    ok = not reasons
    return ok, reasons
