# -*- coding: utf-8 -*-
"""地点修正并入 expected_effect_profile / add_metric（表驱动，禁止 if location_id == …）。"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from edict_execution_frame.domain_catalog import normalize_effect_profile_keys
from edict_execution_frame.location_profiles import LOCATION_MODIFIER_LIMITS

# 与 numeric_system.policy_ir.EffectProfileTier 顺序一致（便于 up_one_step）
TIER_ORDER: Tuple[str, ...] = (
    "down_strong",
    "down_medium",
    "down_small",
    "neutral",
    "up_small",
    "up_medium",
    "up_strong",
)

# difficulty_delta → 对非国库指标的额外缩放（§12.2 落代码；系数保守）
_DIFF_K = 0.015


def _clamp_delta(d: int) -> int:
    cap = int(LOCATION_MODIFIER_LIMITS.get("max_abs_difficulty_delta") or 10)
    return max(-cap, min(cap, d))


def difficulty_scale_from_delta(difficulty_delta: int) -> float:
    d = _clamp_delta(int(difficulty_delta or 0))
    return 1.0 + float(d) * _DIFF_K


def bump_tier(current_tier: str, steps: int) -> str:
    cur = str(current_tier or "neutral").strip()
    if cur not in TIER_ORDER:
        cur = "neutral"
    idx = TIER_ORDER.index(cur)
    new_idx = max(0, min(len(TIER_ORDER) - 1, idx + int(steps)))
    return TIER_ORDER[new_idx]


def merge_effect_tier_modifier_row(
    base_profile: Dict[str, str],
    modifier_row: Dict[str, Any],
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    合并单行 effect tier 修正（success/partial/failure）。
    支持 up_one_step、down_one_step、或直接档位字面量（须为 EffectProfileTier 名）。
    """
    out = dict(base_profile or {})
    per_key: Dict[str, Any] = {}
    for key_raw, spec in (modifier_row or {}).items():
        key = str(key_raw or "").strip()
        if not key:
            continue
        spec_s = str(spec or "").strip()
        before = out.get(key) or "neutral"
        if spec_s == "up_one_step":
            after = bump_tier(before, 1)
        elif spec_s == "down_one_step":
            after = bump_tier(before, -1)
        else:
            after = spec_s
        out[key] = after
        per_key[key] = {"before": before, "after": after, "spec": spec_s}
    return out, {"per_key": per_key}


def merge_location_into_candidate_profile(
    base_profile: Dict[str, str],
    location_modifier_applied: Dict[str, Any],
    *,
    outcome_tier_key: str = "success",
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    将 LOCATION_PROFILES 已 clamp 的 modifier 并入 playbook profile。
    仅处理 effect_tier_modifiers[outcome_tier_key]；返回 normalize 前字典（调用方再 canonicalize）。
    """
    trace: Dict[str, Any] = {
        "outcome_tier_key": outcome_tier_key,
        "narrative_tokens": list((location_modifier_applied or {}).get("narrative_tokens") or []),
        "difficulty_delta": int((location_modifier_applied or {}).get("difficulty_delta") or 0),
        "effect_tier_merge": {},
    }
    etm = (location_modifier_applied or {}).get("effect_tier_modifiers") or {}
    if not isinstance(etm, dict):
        etm = {}
    row = etm.get(outcome_tier_key) or etm.get("success") or {}
    if not isinstance(row, dict):
        row = {}
    merged, sub = merge_effect_tier_modifier_row(base_profile, row)
    trace["effect_tier_merge"] = sub
    return merged, trace


def apply_difficulty_scale_to_effects(
    effects: List[Dict[str, Any]],
    scale: float,
    *,
    skip_keys: Set[str] | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """对 add_metric 数值乘 scale；国库等可跳过，避免与 tier 合并双重放大。"""
    if scale is None or abs(float(scale) - 1.0) < 1e-9:
        return list(effects or []), {"applied": False, "scale": 1.0}
    sk = skip_keys or {"treasury_balance"}
    trace_keys: Dict[str, Tuple[float, float]] = {}
    out: List[Dict[str, Any]] = []
    for e in effects or []:
        if not isinstance(e, dict):
            continue
        if str(e.get("action") or "") != "add_metric":
            out.append(dict(e))
            continue
        key = str(e.get("key") or "").strip()
        try:
            v = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            v = 0.0
        if key in sk:
            out.append(dict(e))
            continue
        nv = round(v * float(scale), 2)
        trace_keys[key] = (v, nv)
        out.append({**e, "value": nv})
    return out, {"applied": True, "scale": float(scale), "scaled_keys": trace_keys}


def apply_location_modifier_to_resolution_pipeline(
    *,
    base_profile: Dict[str, str],
    location_modifier_applied: Dict[str, Any],
    affects_numbers: bool,
) -> Tuple[Dict[str, str], float, Dict[str, Any]]:
    """
    返回：(merged_profile_normalized, difficulty_scale, merge_trace)。
    仅当 affects_numbers 时应用地点修正；否则原样 profile、scale=1。
    """
    if not affects_numbers:
        norm = normalize_effect_profile_keys(dict(base_profile or {}))
        return norm, 1.0, {"skipped": True, "reason": "affects_numbers_false"}

    mod = dict(location_modifier_applied or {})
    merged_raw, trace = merge_location_into_candidate_profile(
        dict(base_profile or {}),
        mod,
        outcome_tier_key="success",
    )
    norm = normalize_effect_profile_keys(merged_raw)
    delta = int(mod.get("difficulty_delta") or 0)
    scale = difficulty_scale_from_delta(delta) if delta else 1.0
    trace["difficulty_scale"] = scale
    return norm, scale, trace
