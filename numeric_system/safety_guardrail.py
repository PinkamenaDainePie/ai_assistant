# -*- coding: utf-8 -*-
"""Unified guardrail for parsed effects."""
from typing import Any, Dict, List, Tuple

from .metric_schema import clamp_effect_delta, get_metric_meta

_ALLOWED_ACTIONS = {
    "add_metric",
    "add_regional_metric",
    "set_flag",
    # 结构化状态变更：允许任务反馈助手/事件/战弧 outcome 放权设置地区/大臣状态
    "set_region_status",
    "set_minister_status",
    "clear_region_status",
    "clear_minister_status",
}


def apply_safety_guardrail(
    effects: List[Dict[str, Any]],
    *,
    max_abs_multiplier: float = 1.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Validate and normalize effect list.
    Returns (safe_effects, guardrail_trace).
    """
    out: List[Dict[str, Any]] = []
    adjustments: List[Dict[str, Any]] = []
    dropped = 0
    for idx, e in enumerate(effects or []):
        action = str(e.get("action", "")).strip()
        if action not in _ALLOWED_ACTIONS:
            dropped += 1
            adjustments.append({"index": idx, "type": "drop_illegal_action", "action": action})
            continue
        if action in ("set_region_status", "set_minister_status", "clear_region_status", "clear_minister_status"):
            out.append(
                {
                    k: v
                    for k, v in e.items()
                    if k
                    in (
                        "action",
                        "region",
                        "status",
                        "disaster_kind",
                        "occupier",
                        "relief_pending",
                        "name",
                        "reason",
                        "last_office",
                        "since_quarter",
                        "source",
                    )
                    or not str(k).startswith("_")
                }
            )
            continue
        if action == "set_flag":
            flag = str(e.get("flag") or e.get("key") or "").strip()
            if not flag:
                dropped += 1
                adjustments.append({"index": idx, "type": "drop_missing_flag"})
                continue
            out.append(
                {
                    "action": "set_flag",
                    "flag": flag,
                    "value": bool(e.get("value", True)),
                    **({"source": e["source"]} if e.get("source") else {}),
                }
            )
            continue
        if action == "add_regional_metric":
            key = str(e.get("key", "")).strip()
            region = str(e.get("region") or "").strip()
            if not region or not key:
                dropped += 1
                adjustments.append({"index": idx, "type": "drop_regional_missing_scope"})
                continue
            meta = get_metric_meta(key)
            if meta is None:
                dropped += 1
                adjustments.append({"index": idx, "type": "drop_unknown_metric", "key": key})
                continue
            try:
                value = float(e.get("value", 0.0))
            except (TypeError, ValueError):
                dropped += 1
                adjustments.append({"index": idx, "type": "drop_bad_value", "key": key})
                continue
            if max_abs_multiplier > 0:
                value *= float(max_abs_multiplier)
            new_v, warn = clamp_effect_delta(key, value)
            if warn:
                adjustments.append({"index": idx, **warn})
            out.append(
                {
                    "action": "add_regional_metric",
                    "region": region,
                    "key": key,
                    "value": round(new_v, 2),
                    "scope_type": str(e.get("scope_type") or "route"),
                }
            )
            continue
        if action != "add_metric":
            dropped += 1
            adjustments.append({"index": idx, "type": "drop_unhandled_action", "action": action})
            continue
        key = str(e.get("key", "")).strip()
        meta = get_metric_meta(key)
        if meta is None:
            dropped += 1
            adjustments.append({"index": idx, "type": "drop_unknown_metric", "key": key})
            continue
        try:
            value = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            dropped += 1
            adjustments.append({"index": idx, "type": "drop_bad_value", "key": key})
            continue
        if max_abs_multiplier > 0:
            value *= float(max_abs_multiplier)
        new_v, warn = clamp_effect_delta(key, value)
        if warn:
            adjustments.append({"index": idx, **warn})
        out.append({"action": "add_metric", "key": key, "value": round(new_v, 2)})
    return out, {
        "input_count": len(effects or []),
        "output_count": len(out),
        "dropped_count": dropped,
        "adjustments": adjustments,
    }

