# -*- coding: utf-8 -*-
"""委派任务：能力 A、难度 D、sigmoid + 可控随机，映射为多档指标变化。"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from task_system.metric_alignment import metric_value
from numeric_system.safety_guardrail import apply_safety_guardrail

_OUTCOMES_CACHE: Optional[Dict[str, Any]] = None


def _outcomes_catalog() -> Dict[str, Any]:
    global _OUTCOMES_CACHE
    if _OUTCOMES_CACHE is None:
        p = Path(__file__).resolve().parent / "delegation_outcomes.json"
        _OUTCOMES_CACHE = json.loads(p.read_text(encoding="utf-8"))
    return _OUTCOMES_CACHE


def _sigmoid(x: float) -> float:
    if x >= 20.0:
        return 1.0
    if x <= -20.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_generic_abilities(metrics: Dict[str, float]) -> Dict[str, float]:
    """虚拟官员：朝廷腐败高压则能力基线下沉（0–1）。"""
    cor = _clamp01(metric_value(metrics, "corruption", 40.0) / 100.0)
    unr = _clamp01(metric_value(metrics, "unrest", 30.0) / 100.0)
    base = 0.52 - 0.22 * cor - 0.12 * unr
    return {
        "integrity": _clamp01(base),
        "governance": _clamp01(base + 0.04),
        "political_power": _clamp01(0.45 - 0.1 * cor),
        "execution": _clamp01(base + 0.02),
    }


def _executor_ctx_to_abilities(executor_ctx: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """将大臣四维（0–100）映射为专家向量的代理（0–1）。"""
    if not executor_ctx:
        return {}
    ab = executor_ctx.get("abilities") or {}
    if not isinstance(ab, dict):
        return {}
    internal = float(ab.get("internal", 50.0)) / 100.0
    military = float(ab.get("military", 50.0)) / 100.0
    finance = float(ab.get("finance", 50.0)) / 100.0
    inf = float(executor_ctx.get("influence", 50.0)) / 100.0
    return {
        "integrity": _clamp01(internal),
        "governance": _clamp01(0.5 * internal + 0.5 * finance),
        "political_power": _clamp01(inf),
        "execution": _clamp01(military),
    }


def compute_A_anti_corruption(abilities: Dict[str, float]) -> float:
    w = {"integrity": 0.35, "governance": 0.25, "political_power": 0.25, "execution": 0.15}
    return sum(float(abilities.get(k, 0.5)) * w[k] for k in w)


def compute_D_anti_corruption(metrics: Dict[str, float]) -> float:
    cor = _clamp01(metric_value(metrics, "corruption", 40.0) / 100.0)
    unr = _clamp01(metric_value(metrics, "unrest", 30.0) / 100.0)
    auth = 1.0 - _clamp01(metric_value(metrics, "authority", 55.0) / 100.0)
    fis = _clamp01(metric_value(metrics, "fiscal_pressure", 30.0) / 100.0)
    return _clamp01(0.38 * cor + 0.22 * unr + 0.22 * auth + 0.18 * fis)


def _blend_random(deterministic_p: float, rng: random.Random) -> float:
    r = rng.random()
    return 0.8 * deterministic_p + 0.2 * r


def _tier_from_p(p: float) -> str:
    if p >= 0.62:
        return "success"
    if p >= 0.42:
        return "partial"
    if p >= 0.22:
        return "failure"
    return "backlash"


def _raw_items_for_action(action_id: str, tier: str, task_key: str = "") -> List[Dict[str, Any]]:
    cat = _outcomes_catalog().get(action_id) or {}
    if task_key:
        sub = cat.get("by_task_key") or {}
        row = sub.get(task_key) if isinstance(sub, dict) else None
        if isinstance(row, dict):
            items = row.get(tier) or []
            if items:
                return list(items)
    items = cat.get(tier) or []
    return list(items) if isinstance(items, list) else []


def _items_to_effects(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from task_system.task_reward_resolver import TaskRewardResolver

    return TaskRewardResolver.stat_change_items_to_effects(items)


class DelegationResolver:
    @staticmethod
    def resolve(
        *,
        action_id: str,
        metrics: Dict[str, float],
        executor_ctx: Optional[Dict[str, Any]],
        session_id: str,
        task_instance_id: str,
        quarter_index: int,
        task_key: str = "",
    ) -> Dict[str, Any]:
        profile = None
        weight_override: Dict[str, float] = {}
        if action_id == "anti_corruption":
            if executor_ctx and str(executor_ctx.get("name") or "").strip():
                try:
                    from task_system.song_minister_delegation import (
                        abilities_from_profile,
                        compute_A_with_weights,
                        get_minister_profile,
                        party_bias_adjustment,
                    )

                    profile = get_minister_profile(str(executor_ctx.get("name") or ""))
                    if profile:
                        abilities = abilities_from_profile(profile, executor_ctx)
                        weight_override = dict(profile.get("ability_weights") or {})
                        A = compute_A_with_weights(abilities, weight_override)
                    else:
                        abilities = _executor_ctx_to_abilities(executor_ctx)
                        A = compute_A_anti_corruption(abilities)
                except ImportError:
                    abilities = _executor_ctx_to_abilities(executor_ctx)
                    A = compute_A_anti_corruption(abilities)
            else:
                abilities = compute_generic_abilities(metrics)
                A = compute_A_anti_corruption(abilities)
            D = compute_D_anti_corruption(metrics)
            try:
                from task_system.song_minister_delegation import party_bias_adjustment

                D = _clamp01(D + party_bias_adjustment(profile, metrics))
            except ImportError:
                pass
        else:
            abilities = compute_generic_abilities(metrics)
            A = compute_A_anti_corruption(abilities)
            D = compute_D_anti_corruption(metrics)

        B = 0.0
        raw_p = _sigmoid(4.0 * (A - D + B))
        seed = (hash((session_id, task_instance_id, quarter_index)) % (2**32)) & 0xFFFFFFFF
        rng = random.Random(seed)
        p = _blend_random(raw_p, rng)
        tier = _tier_from_p(p)
        raw_items = _raw_items_for_action(action_id, tier, task_key=task_key)
        raw_effects = _items_to_effects(raw_items)
        safe, guard = apply_safety_guardrail(raw_effects)
        return {
            "outcome": tier,
            "p_deterministic": round(raw_p, 4),
            "p_final": round(p, 4),
            "A": round(A, 4),
            "D": round(D, 4),
            "abilities_used": abilities,
            "effects": safe,
            "guardrail_trace": guard,
        }
