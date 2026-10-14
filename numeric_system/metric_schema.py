# -*- coding: utf-8 -*-
"""指标单位/边界元数据与 effect 归一化辅助。"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MetricMeta:
    key: str
    unit: str
    kind: str  # resource | state
    min_value: float
    max_value: float
    delta_min: float
    delta_max: float
    tiny_delta_hint: float = 0.0


METRIC_SCHEMA: Dict[str, MetricMeta] = {
    "treasury_balance": MetricMeta(
        key="treasury_balance",
        unit="liang",
        kind="resource",
        min_value=-1_000_000_000.0,
        max_value=1_000_000_000.0,
        delta_min=-300_000.0,
        delta_max=300_000.0,
        tiny_delta_hint=100.0,
    ),
    "inner_treasury_balance": MetricMeta(
        key="inner_treasury_balance",
        unit="liang",
        kind="resource",
        min_value=-1_000_000_000.0,
        max_value=1_000_000_000.0,
        delta_min=-300_000.0,
        delta_max=300_000.0,
        tiny_delta_hint=100.0,
    ),
    "public_support": MetricMeta(
        key="public_support",
        unit="points",
        kind="state",
        min_value=0.0,
        max_value=100.0,
        delta_min=-8.0,
        delta_max=8.0,
    ),
    "unrest": MetricMeta(
        key="unrest",
        unit="points",
        kind="state",
        min_value=0.0,
        max_value=100.0,
        delta_min=-8.0,
        delta_max=8.0,
    ),
    "fiscal_pressure": MetricMeta(
        key="fiscal_pressure",
        unit="points",
        kind="state",
        min_value=0.0,
        max_value=100.0,
        delta_min=-8.0,
        delta_max=8.0,
    ),
    "disaster_index": MetricMeta("disaster_index", "index", "state", 0.0, 100.0, -10.0, 10.0),
    "tax_completion_index": MetricMeta("tax_completion_index", "index", "state", 0.0, 100.0, -10.0, 10.0),
    "tax_intensity": MetricMeta("tax_intensity", "index", "state", 0.0, 100.0, -8.0, 8.0),
    "army_morale": MetricMeta("army_morale", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "army_supply": MetricMeta("army_supply", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "navy_morale": MetricMeta("navy_morale", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "navy_supply": MetricMeta("navy_supply", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "revolt_risk": MetricMeta("revolt_risk", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "corruption": MetricMeta("corruption", "points", "state", 0.0, 100.0, -8.0, 8.0),
    "authority": MetricMeta("authority", "points", "state", 0.0, 100.0, -8.0, 8.0),
}


def get_metric_meta(key: str) -> Optional[MetricMeta]:
    return METRIC_SCHEMA.get(str(key or "").strip())


def clamp_effect_delta(key: str, value: float) -> Tuple[float, Optional[Dict[str, Any]]]:
    meta = get_metric_meta(key)
    if meta is None:
        return float(value), None
    v = float(value)
    nv = max(meta.delta_min, min(meta.delta_max, v))
    if nv == v:
        return nv, None
    return nv, {
        "type": "delta_clamped",
        "key": key,
        "from": round(v, 4),
        "to": round(nv, 4),
        "bounds": [meta.delta_min, meta.delta_max],
    }


def maybe_autoscale_resource_delta(
    key: str, value: float, *, auto_scale_small_resource: bool
) -> Tuple[float, Optional[Dict[str, Any]]]:
    meta = get_metric_meta(key)
    if meta is None:
        return float(value), None
    v = float(value)
    if not auto_scale_small_resource:
        return v, None
    if meta.kind != "resource":
        return v, None
    if abs(v) <= 0.0 or abs(v) >= max(1.0, meta.tiny_delta_hint):
        return v, None
    scaled = v * 100.0
    return scaled, {
        "type": "tiny_resource_delta_scaled",
        "key": key,
        "from": round(v, 4),
        "to": round(scaled, 4),
        "hint": meta.tiny_delta_hint,
    }


def summarize_metric_schema() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for k in sorted(METRIC_SCHEMA.keys()):
        m = METRIC_SCHEMA[k]
        out.append(
            {
                "key": m.key,
                "unit": m.unit,
                "kind": m.kind,
                "delta_bounds": [m.delta_min, m.delta_max],
                "value_bounds": [m.min_value, m.max_value],
                "tiny_delta_hint": m.tiny_delta_hint,
            }
        )
    return out

