# -*- coding: utf-8 -*-
"""Internal affairs category rules."""
from typing import Any, Dict, List, Tuple


def _add(key: str, value: float) -> Dict[str, Any]:
    return {"action": "add_metric", "key": key, "value": float(value)}


def run_rules(text: str, numeric_data: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _ = numeric_data
    t = text or ""
    effects: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    if any(k in t for k in ("减税", "免税", "蠲免")):
        # finance_relieve_tax: tax_intensity reduce_by 2 (template) — keep edict delta ≥2
        effects += [
            _add("public_support", 2.0),
            _add("tax_intensity", -3.0),
            _add("treasury_balance", -18000.0),
        ]
        hits.append({"rule": "tax_relief", "evidence": "减税/免税/蠲免"})
    if any(k in t for k in ("加税", "加征")):
        effects += [_add("treasury_balance", 18000.0), _add("public_support", -1.5), _add("tax_intensity", 2.0)]
        hits.append({"rule": "tax_raise", "evidence": "加税/加征"})
    if any(k in t for k in ("赈济", "开仓", "抚恤")):
        # internal_stabilize_order: unrest reduce_by 3
        effects += [
            _add("public_support", 2.5),
            _add("unrest", -3.0),
            _add("treasury_balance", -25000.0),
        ]
        hits.append({"rule": "relief", "evidence": "赈济/开仓/抚恤"})
    if any(k in t for k in ("吏治", "肃贪", "整饬")):
        # internal_reduce_corruption & internal_restore_authority reachability
        effects += [
            _add("corruption", -4.0),
            _add("authority", 6.0),
            _add("public_support", 1.0),
            _add("unrest", -1.5),
        ]
        hits.append({"rule": "governance", "evidence": "吏治/肃贪/整饬"})

    # Governance/harshness reduces revolt risk (for military_reduce_revolt).
    if any(k in t for k in ("严禁", "严查", "重惩", "从宽", "安抚")):
        if "从宽" in t or "安抚" in t:
            effects += [_add("revolt_risk", -2.0), _add("unrest", -1.0)]
            hits.append({"rule": "mercy_revolt", "evidence": "从宽/安抚"})
        else:
            effects += [_add("revolt_risk", -3.0), _add("authority", 1.0)]
            hits.append({"rule": "severe_revolt", "evidence": "严禁/严查/重惩"})
    return effects, hits

