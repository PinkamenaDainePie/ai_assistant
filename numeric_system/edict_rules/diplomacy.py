# -*- coding: utf-8 -*-
"""Diplomacy category rules."""
from typing import Any, Dict, List, Tuple


def _add(key: str, value: float) -> Dict[str, Any]:
    return {"action": "add_metric", "key": key, "value": float(value)}


def run_rules(text: str, numeric_data: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _ = numeric_data
    t = text or ""
    effects: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    if any(k in t for k in ("和议", "通好", "修好")):
        effects += [_add("revolt_risk", -1.0), _add("authority", 0.8)]
        hits.append({"rule": "peace", "evidence": "和议/通好/修好"})
    if any(k in t for k in ("互市", "通商", "开市")):
        effects += [_add("treasury_balance", 12000.0), _add("fiscal_pressure", -1.0)]
        hits.append({"rule": "trade", "evidence": "互市/通商/开市"})
    return effects, hits

