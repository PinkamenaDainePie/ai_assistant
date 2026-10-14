# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

from .metric_alignment import canonical_metric_key
from numeric_system.safety_guardrail import apply_safety_guardrail


class TaskRewardResolver:
    @staticmethod
    def stat_change_items_to_effects(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """供委派结算等复用：仅处理 type==stat_change。"""
        return TaskRewardResolver._to_effects(items)

    @staticmethod
    def _to_effects(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        effects: List[Dict[str, Any]] = []
        for x in (items or []):
            if str(x.get("type") or "") != "stat_change":
                continue
            key = canonical_metric_key(x.get("key"))
            value = float(x.get("value") or 0.0)
            if key:
                effects.append({"action": "add_metric", "key": key, "value": value})
        return effects

    def build_stall_effects(self, stall_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        raw = self._to_effects(stall_items or [])
        safe, trace = apply_safety_guardrail(raw)
        return {"effects": safe, "trace": trace}

    def build_effects_for_result(
        self,
        result: str,
        rewards: List[Dict[str, Any]],
        penalties: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if result == "completed":
            raw = self._to_effects(rewards)
        elif result in ("failed", "failed_expired"):
            raw = self._to_effects(penalties)
        else:
            raw = []
        safe, trace = apply_safety_guardrail(raw)
        return {"effects": safe, "trace": trace}
