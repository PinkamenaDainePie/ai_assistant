# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict

from numeric_system.metric_schema import METRIC_SCHEMA

# Keep legacy aliases so old templates/objectives still work.
_ALIAS = {
    "treasury": "treasury_balance",
    "inner_treasury": "inner_treasury_balance",
    "public_unrest": "unrest",
    "court_prestige": "authority",
    "army_supply_rate": "army_supply",
    "army_morale_rate": "army_morale",
    "navy_supply_rate": "navy_supply",
    "navy_morale_rate": "navy_morale",
}


def canonical_metric_key(raw_key: Any) -> str:
    k = str(raw_key or "").strip()
    if not k:
        return ""
    k2 = _ALIAS.get(k, k)
    return k2 if k2 in METRIC_SCHEMA else ""


def normalize_metric_key_inplace(obj: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        return obj
    k = canonical_metric_key(obj.get("key"))
    if k:
        obj["key"] = k
    return obj


def metric_value(metrics: Dict[str, float], raw_key: Any, default: float = 0.0) -> float:
    k = canonical_metric_key(raw_key)
    if not k:
        return float(default)
    return float(metrics.get(k, default))

