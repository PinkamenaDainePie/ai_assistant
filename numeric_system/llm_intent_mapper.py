# -*- coding: utf-8 -*-
"""Map LLM DSL intent+degree into project-native effects."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .llm_intent_schema import LlmIntentDsl


_DEGREE_SCALE = {
    "slightly": 0.7,
    "moderately": 1.0,
    "heavily": 1.3,
}


def _make_effect(key: str, value: float) -> Dict[str, Any]:
    return {"action": "add_metric", "key": key, "value": round(float(value), 2)}


def build_intent_effect_templates(intent_catalog: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, float]]]:
    out: Dict[str, List[Tuple[str, float]]] = {}
    for item in intent_catalog or []:
        intent = str(item.get("intent", "")).strip()
        if not intent:
            continue
        tpl: List[Tuple[str, float]] = []
        for pair in item.get("effects") or []:
            try:
                k, v = pair
                tpl.append((str(k), float(v)))
            except (TypeError, ValueError):
                continue
        out[intent] = tpl
    return out


def map_dsl_to_effects(
    dsl: LlmIntentDsl,
    *,
    templates: Dict[str, List[Tuple[str, float]]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    scale = float(_DEGREE_SCALE.get(dsl.degree, 1.0))
    base = templates.get(dsl.intent) or []
    effects: List[Dict[str, Any]] = []
    for key, value in base:
        effects.append(_make_effect(key, value * scale))
    return effects, {
        "intent": dsl.intent,
        "degree": dsl.degree,
        "scale": scale,
        "template_size": len(base),
    }

