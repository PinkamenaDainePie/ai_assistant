# -*- coding: utf-8 -*-
"""诏书 edict_execution：大臣能力加权（映射到 numeric_system.Minister 字段）。"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


def _mget(m: Any, key: str, default: float = 50.0) -> float:
    try:
        v = getattr(m, key, None)
        if v is None and isinstance(m, dict):
            v = m.get(key)
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def compute_executor_ability(minister: Any, minister_weights: Dict[str, float]) -> float:
    """minister_weights 的 key 为 Minister 属性名（ability_internal 等）。"""
    if not minister_weights:
        return 50.0
    total = 0.0
    wsum = 0.0
    for key, w in minister_weights.items():
        try:
            wf = float(w)
        except (TypeError, ValueError):
            continue
        if wf <= 0:
            continue
        val = _mget(minister, str(key), 50.0)
        total += val * wf
        wsum += wf
    if wsum <= 0:
        return 50.0
    return total / wsum


def compute_joint_executor_ability(ministers: Sequence[Any], minister_weights: Dict[str, float]) -> float:
    if not ministers:
        return 50.0
    scores = [compute_executor_ability(m, minister_weights) for m in ministers]
    avg = sum(scores) / len(scores)
    synergy = min(8.0, max(0.0, float(len(scores) - 1)) * 4.0)
    return min(100.0, avg + synergy)


def find_ministers_by_names(ministers: Optional[Sequence[Any]], names: List[str]) -> List[Any]:
    out: List[Any] = []
    if not ministers or not names:
        return out
    name_set = {str(n).strip() for n in names if str(n).strip()}
    for m in ministers:
        nm = str(getattr(m, "name", "") or "").strip()
        if nm in name_set:
            out.append(m)
    return out


def composite_ability_for_preview(
    preview: Dict[str, Any],
    ministers: Optional[Sequence[Any]],
) -> float:
    """preview 含 ability_weights_minister（已映射到 Minister 字段）、executors / executor。"""
    w = dict(preview.get("ability_weights_minister") or {})
    if not w:
        return 55.0
    exs = list(preview.get("executors") or [])
    if not exs:
        one = str(preview.get("executor") or "").strip()
        if one:
            exs = [one]
    hits = find_ministers_by_names(ministers, [str(x).strip() for x in exs if str(x).strip()])
    if not hits:
        return 50.0
    if len(hits) == 1:
        return round(compute_executor_ability(hits[0], w), 2)
    return round(compute_joint_executor_ability(hits, w), 2)


def sigmoid_success_scale(ability: float, difficulty: float = 52.0, scale: float = 8.0) -> float:
    """0~1 附近，用于末季效果轻量缩放。"""
    x = (float(ability) - float(difficulty)) / max(1e-6, float(scale))
    return float(1.0 / (1.0 + math.exp(-x)))


def scale_effects_by_ability(
    effects: List[Dict[str, Any]],
    *,
    ability: float,
    difficulty: float = 52.0,
) -> List[Dict[str, Any]]:
    s = sigmoid_success_scale(ability, difficulty=difficulty)
    factor = 0.82 + min(0.38, s * 0.45)
    out: List[Dict[str, Any]] = []
    for e in effects or []:
        if not isinstance(e, dict):
            continue
        if str(e.get("action") or "") != "add_metric":
            out.append(dict(e))
            continue
        try:
            v = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            v = 0.0
        out.append({**e, "value": round(v * factor, 2)})
    return out
