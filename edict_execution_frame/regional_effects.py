# -*- coding: utf-8 -*-
"""按 effect_scope 将空间域效果拆为区域指标 + 少量全国溢出。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# 全国 spillover 比例（区域为主、全国为辅）
_REGIONAL_SPILLOVER = 0.25

# 宜区域化的指标（工程/治安）
_REGIONAL_LOCAL_KEYS = frozenset(
    {
        "unrest",
        "revolt_risk",
        "disaster_index",
        "public_support",
        "corruption",
        "army_supply",
        "army_morale",
    }
)

_SPATIAL_DOMAINS = frozenset({"engineering", "public_order", "military"})


def regional_metric_storage_key(region_id: str, metric_key: str) -> str:
    """存入 state.metrics 的扁平键（无需改 QuarterState 结构）。"""
    rid = (region_id or "unknown").strip().replace(":", "_")
    mk = (metric_key or "").strip()
    return "regional__%s__%s" % (rid, mk)


def region_id_from_effect_scope(effect_scope: Dict[str, Any]) -> str:
    if not effect_scope:
        return ""
    if (effect_scope.get("hostile") or "").strip():
        return str(effect_scope["hostile"]).strip()
    if (effect_scope.get("composite") or "").strip():
        return str(effect_scope["composite"]).strip()
    if (effect_scope.get("id") or "").strip():
        return str(effect_scope["id"]).strip()
    if (effect_scope.get("river") or "").strip():
        return str(effect_scope["river"]).strip()
    labels = effect_scope.get("labels") or []
    if labels:
        return "label_%s" % str(labels[0]).strip()
    return ""


def should_apply_regional_scope(domain: str, effect_scope: Dict[str, Any]) -> bool:
    dom = (domain or "").strip()
    if dom not in _SPATIAL_DOMAINS:
        return False
    return bool(region_id_from_effect_scope(effect_scope))


def apply_regional_scope_to_effects(
    effects: List[Dict[str, Any]],
    *,
    effect_scope: Dict[str, Any],
    domain: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """将 add_metric 中区域敏感项拆为 add_regional_metric + 全国 spillover。"""
    region = region_id_from_effect_scope(effect_scope or {})
    trace: Dict[str, Any] = {
        "applied": False,
        "region_id": region,
        "domain": domain,
        "splits": [],
    }
    if not should_apply_regional_scope(domain, effect_scope or {}):
        return list(effects or []), trace

    trace["applied"] = True
    out: List[Dict[str, Any]] = []
    for e in effects or []:
        if not isinstance(e, dict):
            continue
        action = str(e.get("action") or "").strip()
        if action != "add_metric":
            out.append(dict(e))
            continue
        key = str(e.get("key") or "").strip()
        try:
            val = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            val = 0.0
        if key in _REGIONAL_LOCAL_KEYS and region:
            out.append(
                {
                    "action": "add_regional_metric",
                    "region": region,
                    "key": key,
                    "value": round(val, 2),
                    "scope_type": str(effect_scope.get("type") or "route"),
                }
            )
            spill = round(val * _REGIONAL_SPILLOVER, 2)
            if abs(spill) >= 1e-6:
                out.append({"action": "add_metric", "key": key, "value": spill})
            trace["splits"].append(
                {"key": key, "regional_value": round(val, 2), "national_spillover": spill}
            )
        else:
            out.append(dict(e))
    return out, trace
