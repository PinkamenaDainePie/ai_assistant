# -*- coding: utf-8 -*-
"""Military category rules."""
from typing import Any, Dict, List, Tuple


def _add(key: str, value: float) -> Dict[str, Any]:
    return {"action": "add_metric", "key": key, "value": float(value)}


def run_rules(text: str, numeric_data: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _ = numeric_data
    t = text or ""
    effects: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    if any(k in t for k in ("募兵", "练兵", "扩军", "整军")):
        # military_raise_morale: army_morale target 65 (default ~60)
        effects += [_add("army_morale", 6.0), _add("authority", 2.0), _add("unrest", -1.5)]
        hits.append({"rule": "recruit_train", "evidence": "募兵/练兵/扩军"})
    if any(k in t for k in ("军饷", "补饷", "军需")):
        effects += [_add("army_supply", 3.0), _add("treasury_balance", -20000.0)]
        hits.append({"rule": "supply_pay", "evidence": "军饷/军需"})
    if any(k in t for k in ("海防", "水师", "战船")):
        effects += [_add("navy_morale", 2.0), _add("navy_supply", 2.0)]
        hits.append({"rule": "navy", "evidence": "海防/水师/战船"})
    return effects, hits

