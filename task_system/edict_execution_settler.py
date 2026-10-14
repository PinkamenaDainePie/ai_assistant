# -*- coding: utf-8 -*-
"""诏书 edict_execution 跨季结算（表驱动 + 大臣能力缩放）。"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from edict_execution_frame.regional_effects import apply_regional_scope_to_effects
from numeric_system.safety_guardrail import apply_safety_guardrail
from numeric_system.types import Minister

from .edict_execution_ability import composite_ability_for_preview, scale_effects_by_ability
from .metric_alignment import metric_value
from .task_reward_resolver import TaskRewardResolver

_AC_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_DOMAIN_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def _anti_corruption_catalog() -> Dict[str, Any]:
    global _AC_CATALOG_CACHE
    if _AC_CATALOG_CACHE is None:
        p = Path(__file__).resolve().parent / "catalog" / "song_anti_corruption_settlement.json"
        _AC_CATALOG_CACHE = json.loads(p.read_text(encoding="utf-8"))
    return _AC_CATALOG_CACHE


def _domain_catalog() -> Dict[str, Any]:
    global _DOMAIN_CATALOG_CACHE
    if _DOMAIN_CATALOG_CACHE is None:
        p = Path(__file__).resolve().parent / "catalog" / "domain_edict_settlement.json"
        _DOMAIN_CATALOG_CACHE = json.loads(p.read_text(encoding="utf-8"))
    return _DOMAIN_CATALOG_CACHE


def _playbook_row(domain: str, task_key: str) -> Dict[str, Any]:
    dom = (domain or "general").strip()
    tk = (task_key or "").strip()
    if dom == "anti_corruption":
        row = (_anti_corruption_catalog().get("playbooks") or {}).get(tk)
        if isinstance(row, dict):
            return row
    cat = _domain_catalog()
    row = (cat.get("playbooks") or {}).get(tk)
    if isinstance(row, dict):
        return row
    defaults = cat.get("domain_defaults") or {}
    fallback = defaults.get(dom) or defaults.get("general") or {}
    return dict(fallback) if isinstance(fallback, dict) else {}


def _sigmoid(x: float) -> float:
    if x >= 20.0:
        return 1.0
    if x <= -20.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _tier_from_p(p: float) -> str:
    if p >= 0.62:
        return "success"
    if p >= 0.42:
        return "partial"
    if p >= 0.22:
        return "failure"
    return "backlash"


def phase_narrative_for(domain: str, task_key: str, phase_index: int, phases_total: int) -> str:
    pbs = _playbook_row(domain, task_key)
    lines = list(pbs.get("phase_narratives") or [])
    if not lines:
        return "承办进行中（第%d/%d季）" % (phase_index + 1, phases_total)
    idx = min(phase_index, len(lines) - 1)
    return str(lines[idx])


def _items_for_tier(domain: str, task_key: str, tier: str) -> List[Dict[str, Any]]:
    pbs = _playbook_row(domain, task_key)
    tiers = pbs.get("effect_tiers") or {}
    items = tiers.get(tier) or []
    return list(items) if isinstance(items, list) else []


def _difficulty_base(domain: str, metrics: Dict[str, float], loc_diff: float) -> float:
    dom = (domain or "general").strip()
    if dom == "anti_corruption":
        cor = float(metric_value(metrics, "corruption", 40.0))
        unr = float(metric_value(metrics, "unrest", 30.0))
        return 52.0 + cor * 0.18 + unr * 0.08 + loc_diff
    if dom == "disaster_relief":
        di = float(metric_value(metrics, "disaster_index", 45.0))
        sup = float(metric_value(metrics, "public_support", 50.0))
        return 48.0 + di * 0.12 + max(0.0, 55.0 - sup) * 0.1 + loc_diff
    if dom == "military":
        mor = float(metric_value(metrics, "army_morale", 55.0))
        return 50.0 + max(0.0, 60.0 - mor) * 0.15 + loc_diff
    if dom == "fiscal":
        fp = float(metric_value(metrics, "fiscal_pressure", 45.0))
        return 50.0 + fp * 0.12 + loc_diff
    if dom == "agriculture":
        di = float(metric_value(metrics, "disaster_index", 45.0))
        sup = float(metric_value(metrics, "public_support", 50.0))
        return 46.0 + di * 0.08 + max(0.0, 52.0 - sup) * 0.08 + loc_diff
    if dom == "engineering":
        di = float(metric_value(metrics, "disaster_index", 40.0))
        return 48.0 + di * 0.1 + loc_diff * 0.85
    if dom == "public_order":
        unr = float(metric_value(metrics, "unrest", 35.0))
        return 47.0 + unr * 0.12 + loc_diff * 0.75
    return 50.0 + loc_diff * 0.5


class EdictExecutionSettler:
    @staticmethod
    def settle(
        *,
        edict_meta: Dict[str, Any],
        metrics: Dict[str, float],
        ministers: Optional[Sequence[Minister]],
        session_id: str,
        task_instance_id: str,
        quarter_index: int,
        phase_index: int,
        phases_total: int,
        is_final_phase: bool,
    ) -> Dict[str, Any]:
        domain = str(edict_meta.get("domain") or "general").strip()
        tk = str(edict_meta.get("task_key") or "steady_governance").strip()

        if not is_final_phase:
            return {
                "result": "edict_execution_phase",
                "success": False,
                "applied_effects": [],
                "narrative_zh": phase_narrative_for(domain, tk, phase_index, phases_total),
                "phase": True,
            }

        preview = {
            "ability_weights_minister": dict(edict_meta.get("ability_weights_minister") or {}),
            "executors": list(edict_meta.get("executor_names") or []),
            "executor": str(edict_meta.get("display_executor_zh") or ""),
        }
        ability = float(edict_meta.get("executor_composite_ability") or 0)
        if ability <= 0 and ministers:
            ability = composite_ability_for_preview(preview, ministers)

        loc_diff = float(edict_meta.get("location_difficulty_delta") or 0)
        difficulty = _difficulty_base(domain, metrics, loc_diff)

        A = ability / 100.0 if ability > 1.5 else float(ability)
        D = min(0.95, difficulty / 100.0)
        raw_p = _sigmoid(4.0 * (A - D))
        seed = (hash((session_id, task_instance_id, quarter_index, domain, tk)) % (2**32)) & 0xFFFFFFFF
        rng = random.Random(seed)
        p = 0.8 * raw_p + 0.2 * rng.random()
        tier = _tier_from_p(p)

        raw_items = _items_for_tier(domain, tk, tier)
        raw_effects = TaskRewardResolver.stat_change_items_to_effects(raw_items)
        scaled = scale_effects_by_ability(raw_effects, ability=ability, difficulty=difficulty)
        effect_scope = dict(edict_meta.get("effect_scope") or {})
        scoped, regional_trace = apply_regional_scope_to_effects(
            scaled,
            effect_scope=effect_scope,
            domain=domain,
        )
        safe, guard = apply_safety_guardrail(scoped)
        return {
            "result": tier,
            "success": tier in ("success", "partial"),
            "applied_effects": safe,
            "guardrail_trace": guard,
            "narrative_zh": "诏书承办%s：%s" % (edict_meta.get("title_zh") or "政务", tier),
            "outcome_detail": {
                "p_final": round(p, 4),
                "A": round(A, 4),
                "D": round(D, 4),
                "domain": domain,
                "task_key": tk,
                "regional_effect_split": regional_trace,
                "effect_scope": effect_scope,
            },
        }
