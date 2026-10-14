# -*- coding: utf-8 -*-
"""候选可执行性过滤（admissible political action）。"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .metric_schema import METRIC_SCHEMA
from .policy_ir import PolicyActionCandidate
from .types import NumericData


def _minister_names(data: NumericData) -> Set[str]:
    return {str(getattr(m, "name", "") or "").strip() for m in (data.ministers or []) if str(getattr(m, "name", "") or "").strip()}


def filter_policy_candidates(
    *,
    candidates: List[PolicyActionCandidate],
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
) -> Tuple[List[PolicyActionCandidate], List[Dict[str, Any]]]:
    accepted: List[PolicyActionCandidate] = []
    rejected: List[Dict[str, Any]] = []
    names = _minister_names(numeric_data)

    for c in candidates:
        reasons: List[str] = []
        for mk in c.target_metrics:
            key = str(mk or "").strip()
            if key and key not in METRIC_SCHEMA:
                reasons.append(f"unknown_metric:{key}")

        ex = (c.executor or "").strip()
        if ex and ex not in names:
            reasons.append("executor_not_found")

        if c.action_type == "named_execution" and c.intensity == "high":
            try:
                tb = float(state_metrics.get("treasury_balance", 0.0))
            except (TypeError, ValueError):
                tb = 0.0
            if tb < -500_000 and c.domain in ("military", "infrastructure"):
                reasons.append("insufficient_treasury")

        if c.candidate_id.endswith("_named_placeholder") and not ex:
            reasons.append("placeholder_without_executor")

        if reasons:
            rejected.append({"candidate_id": c.candidate_id, "reasons": reasons})
        else:
            accepted.append(c)

    return accepted, rejected
