# -*- coding: utf-8 -*-
"""PolicyActionCandidate → add_metric effects（本地公式 + 护栏）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .policy_ir import EffectProfileTier, PolicyActionCandidate
from .safety_guardrail import apply_safety_guardrail
from .types import NumericData


def _tier_base(tier: str) -> float:
    """状态类指标大致步长（0–100）；国库用 liang 另行缩放。"""
    try:
        et = EffectProfileTier(str(tier).strip())
    except ValueError:
        return 0.0
    m = {
        EffectProfileTier.down_strong: -5.5,
        EffectProfileTier.down_medium: -3.5,
        EffectProfileTier.down_small: -2.0,
        EffectProfileTier.neutral: 0.0,
        EffectProfileTier.up_small: 1.5,
        EffectProfileTier.up_medium: 3.0,
        EffectProfileTier.up_strong: 5.0,
    }
    return float(m.get(et, 0.0))


def _intensity_scale(intensity: str) -> float:
    return {"low": 0.65, "medium": 1.0, "high": 1.35}.get(str(intensity or "medium"), 1.0)


def _executor_multiplier(data: NumericData, executor_name: str) -> float:
    name = (executor_name or "").strip()
    if not name:
        return 1.0
    for m in data.ministers or []:
        if str(getattr(m, "name", "")).strip() == name:
            internal = float(getattr(m, "ability_internal", 50.0))
            fin = float(getattr(m, "ability_finance", 50.0))
            return 1.0 + (internal + fin) / 200.0 * 0.25
    return 1.0


def _treasury_from_tier(tier: str, scale: float) -> float:
    """国库变动（liang）；tier 正负与增减一致。"""
    base = _tier_base(tier)
    if abs(base) < 0.01:
        return 0.0
    return round(base * 2200.0 * scale, 0)


def resolve_candidate_to_effects(
    candidate: PolicyActionCandidate,
    *,
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    scale = _intensity_scale(candidate.intensity)
    ex_mul = _executor_multiplier(numeric_data, candidate.executor)
    effects: List[Dict[str, Any]] = []
    profile = candidate.expected_effect_profile or {}

    for logical_key, tier in profile.items():
        key = str(logical_key or "").strip()
        if not key:
            continue
        if key == "treasury_balance":
            v = _treasury_from_tier(tier, scale * ex_mul)
            if abs(v) > 0.5:
                effects.append({"action": "add_metric", "key": key, "value": float(v)})
            continue

        base = _tier_base(tier) * scale
        if key == "corruption":
            base *= ex_mul
        if abs(base) < 0.05:
            continue
        effects.append({"action": "add_metric", "key": key, "value": round(base, 2)})

    safe, guard = apply_safety_guardrail(effects)
    meta = {
        "candidate_id": candidate.candidate_id,
        "domain": candidate.domain,
        "guardrail_trace": guard,
    }
    return safe, meta
