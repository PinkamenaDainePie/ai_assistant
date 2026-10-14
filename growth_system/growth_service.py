# -*- coding: utf-8 -*-
"""
Growth System (成长系统) service.

Responsibilities (MVP):
1) At quarter start, after player chooses 3 priorities, compute available points
   for the next quarter and persist them for the session.
2) Validate player skill allocations and persist skill levels.
3) At quarter settle, convert skill levels into numeric-system effects.

It does not decide API timing; endpoints will call into this service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


GrowthTreeKey = str
GrowthPointKey = str


class GrowthTree:
    MILITARY: GrowthTreeKey = "military"
    MANAGEMENT: GrowthTreeKey = "management"
    POLITICS: GrowthTreeKey = "politics"
    SCHOLARSHIP: GrowthTreeKey = "scholarship"

    ALL: Tuple[GrowthTreeKey, ...] = (
        MILITARY,
        MANAGEMENT,
        POLITICS,
        SCHOLARSHIP,
    )

    # UI-facing zh labels (kept here for consistent mapping).
    LABEL_ZH: Dict[GrowthTreeKey, str] = {
        MILITARY: "军事",
        MANAGEMENT: "管理",
        POLITICS: "政治",
        SCHOLARSHIP: "学识",
    }


class GrowthPoint:
    GENERIC: GrowthPointKey = "generic"
    ALL: Tuple[GrowthPointKey, ...] = (
        GrowthTree.MILITARY,
        GrowthTree.MANAGEMENT,
        GrowthTree.POLITICS,
        GrowthTree.SCHOLARSHIP,
        GENERIC,
    )


@dataclass(frozen=True)
class GrowthAllocation:
    """
    Allocated points to each growth tree for a specific quarter.
    """

    points_by_tree: Dict[GrowthTreeKey, float]


class GrowthService:
    """
    In-memory session state.

    NOTE: In production, this should be backed by persistence.
    """

    def __init__(self) -> None:
        # focus choice made at end of previous quarter; applies to next quarter index
        self.pending_focus: Dict[str, Dict[int, List[GrowthTreeKey]]] = {}
        # computed points for the given next quarter index
        self.available_points: Dict[str, Dict[int, Dict[GrowthPointKey, int]]] = {}
        # cumulative skill levels across all quarters
        self.skill_levels_total: Dict[str, Dict[GrowthTreeKey, float]] = {}
        self.scheme_version: Dict[str, int] = {}
        self.SCHEME_VERSION: int = 2

        # Expert table thresholds: L1 default open, L2>=3, L3>=8, L4>=15, L5>=25.
        # We treat "no investment yet" as treeLevel=0 to keep soft-bias meaningful.
        self.TREELEVEL_THRESHOLDS: List[Tuple[int, int]] = [
            (1, 1),
            (3, 2),
            (8, 3),
            (15, 4),
            (25, 5),
        ]

        # Skill catalog (nodes definition) loaded from JSON next to this module.
        # This makes the frontend skill tree nodes driven by backend data (source of truth).
        self._skill_catalog: Optional[Dict[str, Any]] = None
        self._catalog_path = Path(__file__).resolve().parent / "skill_catalog.json"

    def _get_or_create_nested_list(self, root: Dict[str, Dict[int, List[GrowthTreeKey]]], session_id: str) -> Dict[int, List[GrowthTreeKey]]:
        if session_id not in root:
            root[session_id] = {}
        return root[session_id]

    def _get_or_create_nested_points(self, root: Dict[str, Dict[int, Dict[GrowthPointKey, int]]], session_id: str) -> Dict[int, Dict[GrowthPointKey, int]]:
        if session_id not in root:
            root[session_id] = {}
        return root[session_id]

    def _ensure_scheme(self, session_id: str) -> None:
        sid = str(session_id or "").strip() or ""
        if not sid:
            return
        if int(self.scheme_version.get(sid, 0)) == int(self.SCHEME_VERSION):
            return
        # Reset growth state when switching point mechanism.
        self.pending_focus[sid] = {}
        self.available_points[sid] = {}
        self.skill_levels_total[sid] = {t: 0.0 for t in GrowthTree.ALL}
        self.scheme_version[sid] = int(self.SCHEME_VERSION)

    def _get_or_create_skill_total_table(
        self,
        root: Dict[str, Dict[GrowthTreeKey, float]],
        session_id: str,
    ) -> Dict[GrowthTreeKey, float]:
        if session_id not in root:
            root[session_id] = {t: 0.0 for t in GrowthTree.ALL}
        else:
            for t in GrowthTree.ALL:
                root[session_id].setdefault(t, 0.0)
        return root[session_id]

    def choose_focus(self, *, session_id: str, quarter_index: int, focus_trees: List[GrowthTreeKey]) -> Dict[str, Any]:
        """
        Player chooses exactly 3 priorities among 4 trees.

        quarter_index: the NEXT quarter index where points will be computed.
        """
        sid = str(session_id or "").strip() or ""
        if not sid:
            raise ValueError("session_id_required")
        self._ensure_scheme(sid)

        unique: List[GrowthTreeKey] = []
        seen: Set[GrowthTreeKey] = set()
        for t in focus_trees or []:
            tt = str(t or "").strip()
            if tt in GrowthTree.ALL and tt not in seen:
                seen.add(tt)
                unique.append(tt)

        if len(unique) != 3:
            raise ValueError("focus_must_select_3_distinct_trees")

        table = self._get_or_create_nested_list(self.pending_focus, sid)
        table[int(quarter_index)] = unique
        return {"ok": True, "session_id": sid, "quarter_index": int(quarter_index), "focus_trees": unique}

    def get_pending_focus(self, *, session_id: str, quarter_index: int) -> List[GrowthTreeKey]:
        sid = str(session_id or "").strip() or ""
        if not sid:
            return []
        q = int(quarter_index)
        table = self.pending_focus.get(sid) or {}
        focus = list(table.get(q, []) or [])
        if len(focus) == 3:
            return focus
        # 兼容旧版 API：季末选重心误写入当前季 q，而加点读取的是 q。
        legacy = list(table.get(q - 1, []) or [])
        if len(legacy) == 3:
            return legacy
        return focus

    def compute_available_points(
        self,
        *,
        session_id: str,
        quarter_index: int,
        metrics: Dict[str, float],
        flags: Optional[Dict[str, bool]] = None,
        settled_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[GrowthPointKey, int]:
        """
        Compute available points for skill allocation in the given quarter.
        """
        sid = str(session_id or "").strip() or ""
        if not sid:
            raise ValueError("session_id_required")
        self._ensure_scheme(sid)

        q = int(quarter_index)
        focus = self.get_pending_focus(session_id=sid, quarter_index=q)
        # Strict behavior: only compute points after the player has chosen
        # 3 priorities for this next quarter.
        if len(focus) != 3:
            points_table = self._get_or_create_nested_points(self.available_points, sid)
            zero_table = {t: 0 for t in GrowthPoint.ALL}
            points_table[q] = dict(zero_table)
            return dict(zero_table)
        out: Dict[GrowthPointKey, int] = {t: 0 for t in GrowthPoint.ALL}
        for t in focus:
            out[t] = 2
        task_bonus = self._compute_generic_bonus_from_settled_results(settled_results)
        event_bonus = self._compute_generic_bonus_from_flags(flags)
        out[GrowthPoint.GENERIC] = 1 + min(2, task_bonus + event_bonus)

        # persist for validation later
        points_table = self._get_or_create_nested_points(self.available_points, sid)
        points_table[q] = dict(out)
        return dict(out)

    def get_available_points(self, *, session_id: str, quarter_index: int) -> Dict[GrowthPointKey, int]:
        sid = str(session_id or "").strip() or ""
        if not sid:
            return {t: 0 for t in GrowthPoint.ALL}
        self._ensure_scheme(sid)
        current = dict((self.available_points.get(sid) or {}).get(int(quarter_index), {}) or {})
        normalized = {t: int(current.get(t, 0)) for t in GrowthPoint.ALL}
        return normalized

    def allocate_skills(
        self,
        *,
        session_id: str,
        quarter_index: int,
        allocation: Dict[GrowthTreeKey, float],
    ) -> Dict[str, Any]:
        """
        allocation: per-tree point amounts the player invests this quarter.
        Enforced rule: unselected trees get 0, total must not exceed available points.
        """
        sid = str(session_id or "").strip() or ""
        if not sid:
            raise ValueError("session_id_required")
        self._ensure_scheme(sid)
        q = int(quarter_index)

        focus = self.get_pending_focus(session_id=sid, quarter_index=q)
        if len(focus) != 3:
            raise ValueError("focus_not_chosen_for_quarter")

        avail = self.get_available_points(session_id=sid, quarter_index=q)
        # normalize allocation keys
        clean: Dict[GrowthTreeKey, float] = {t: 0.0 for t in GrowthTree.ALL}
        for t, v in (allocation or {}).items():
            tt = str(t or "").strip()
            if tt in GrowthTree.ALL:
                try:
                    clean[tt] = float(v)
                except (TypeError, ValueError):
                    clean[tt] = 0.0

        # Unselected trees must be 0.
        for t in GrowthTree.ALL:
            if t not in focus and abs(float(clean.get(t, 0.0))) > 1e-9:
                raise ValueError(f"tree_not_selected_must_be_zero:{t}")

        # Total cannot exceed available points under "tree first, generic fallback".
        total = 0.0
        generic_left = float(avail.get(GrowthPoint.GENERIC, 0))
        for t in focus:
            pt = float(clean.get(t, 0.0))
            if pt < -1e-9:
                raise ValueError("allocation_must_be_non_negative")
            total += pt
            tree_left = float(avail.get(t, 0))
            if pt <= tree_left + 1e-9:
                continue
            need_generic = pt - tree_left
            if need_generic - generic_left > 1e-9:
                raise ValueError(f"allocation_exceeds_tree_plus_generic:{t}")
            generic_left -= need_generic

        # Accumulate skill levels across quarters.
        totals = self._get_or_create_skill_total_table(self.skill_levels_total, sid)
        for t in GrowthTree.ALL:
            totals[t] = float(totals.get(t, 0.0)) + float(clean.get(t, 0.0))

        # Consume wallet for this quarter to prevent double-spend.
        remaining: Dict[GrowthPointKey, int] = {k: int(v) for k, v in avail.items()}
        generic_pool = float(remaining.get(GrowthPoint.GENERIC, 0))
        for t in GrowthTree.ALL:
            spend = float(clean.get(t, 0.0))
            tree_pool = float(remaining.get(t, 0))
            consume_tree = min(tree_pool, spend)
            remaining[t] = int(round(tree_pool - consume_tree))
            spill = spend - consume_tree
            if spill > 1e-9:
                generic_pool = max(0.0, generic_pool - spill)
        remaining[GrowthPoint.GENERIC] = int(round(generic_pool))
        self._get_or_create_nested_points(self.available_points, sid)[q] = dict(remaining)

        return {
            "ok": True,
            "session_id": sid,
            "quarter_index": q,
            "skill_levels": dict(totals),
            "total_allocated": total,
            "remaining_points": dict(remaining),
        }

    def _compute_generic_bonus_from_settled_results(
        self,
        settled_results: Optional[List[Dict[str, Any]]],
    ) -> int:
        out = 0
        for row in settled_results or []:
            if not isinstance(row, dict):
                continue
            result = str(row.get("result", "")).lower()
            if result in ("success", "succeeded", "completed", "pass"):
                out += 1
            elif bool(row.get("success")):
                out += 1
        return max(0, out)

    def _compute_generic_bonus_from_flags(
        self,
        flags: Optional[Dict[str, bool]],
    ) -> int:
        out = 0
        for k, v in (flags or {}).items():
            if not v:
                continue
            kk = str(k or "").lower()
            if kk.startswith("growth_generic_bonus"):
                out += 1
        return max(0, out)

    def get_skill_levels(self, *, session_id: str, quarter_index: int) -> Dict[GrowthTreeKey, float]:
        """
        Backward-compatible getter.

        quarter_index is ignored because skills are cumulative.
        """
        sid = str(session_id or "").strip() or ""
        if not sid:
            return {t: 0.0 for t in GrowthTree.ALL}
        return dict((self.skill_levels_total.get(sid) or {}) or {t: 0.0 for t in GrowthTree.ALL})

    def get_tree_levels(self, *, session_id: str) -> Dict[GrowthTreeKey, int]:
        """
        Convert cumulative skill points into discrete tree levels (0..5).
        """
        totals = self.get_skill_levels(session_id=session_id, quarter_index=0)
        out: Dict[GrowthTreeKey, int] = {t: 0 for t in GrowthTree.ALL}
        for t in GrowthTree.ALL:
            pts = float(totals.get(t, 0.0))
            lvl = 0
            for threshold_pts, threshold_lvl in self.TREELEVEL_THRESHOLDS:
                if pts >= threshold_pts:
                    lvl = threshold_lvl
            out[t] = int(lvl)
        return out

    def get_skill_catalog(self) -> Dict[str, Any]:
        """
        Return the skill tree node catalog (source of truth for UI nodes).
        The catalog defines per-tree nodes (id, name, cost, max_level, flavor effects),
        level thresholds, and honest summaries of what investing in each tree actually impacts
        in the numeric simulation (via build_growth_effects).

        Frontend should fetch /growth/skill_catalog and drive the skill tree UI from this
        instead of hardcoding nodes, so that descriptions, costs, and structure stay in sync
        with backend investment model.
        """
        if self._skill_catalog is not None:
            return self._skill_catalog
        try:
            if self._catalog_path.is_file():
                data = json.loads(self._catalog_path.read_text(encoding="utf-8"))
                self._skill_catalog = data
                return data
        except Exception:
            pass
        # Fallback: minimal empty catalog so UI doesn't crash.
        return {
            "version": 0,
            "trees": {},
            "tree_level_thresholds": self.TREELEVEL_THRESHOLDS,
            "notes": "catalog load failed; using backend defaults only"
        }

    def build_growth_effects(
        self,
        *,
        session_id: str,
        quarter_index: int,
        metrics: Dict[str, float],
        flags: Optional[Dict[str, bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert current-quarter skill levels into numeric-system effects (add_metric).

        quarter_index here represents the quarter that is ending now.
        Effects will be applied by numeric engine to advance from this quarter to next.
        """
        sid = str(session_id or "").strip() or ""
        if not sid:
            return []
        q = int(quarter_index)
        totals = self.get_skill_levels(session_id=sid, quarter_index=q)
        if not any(float(totals.get(t, 0.0)) > 1e-9 for t in GrowthTree.ALL):
            return []

        # MVP: effects scale with allocated points, then clamped by numeric-system effect normalization.
        # Keep deltas relatively small to avoid saturating all clamps.
        # Tree speed coefficients (调慢B + 第1轮平衡):
        # military 0.6 / management 0.4 / politics 0.5 / scholarship 0.3
        B_MIL = 0.6
        B_MGR = 0.4
        B_POL = 0.5
        B_SCH = 0.3

        m_mil = float(totals.get(GrowthTree.MILITARY, 0.0)) * B_MIL
        m_mgr = float(totals.get(GrowthTree.MANAGEMENT, 0.0)) * B_MGR
        m_pol = float(totals.get(GrowthTree.POLITICS, 0.0)) * B_POL
        m_sch = float(totals.get(GrowthTree.SCHOLARSHIP, 0.0)) * B_SCH

        effects: List[Dict[str, Any]] = []

        def add_metric_effect(key: str, delta: float) -> None:
            delta_f = float(delta)
            if abs(delta_f) < 1e-9:
                return
            effects.append({"action": "add_metric", "key": str(key), "value": round(delta_f, 2)})

        # Soft cap for positive public support growth from growth system:
        # when support is already high, reduce further positive gains.
        cur_public_support = float(metrics.get("public_support", 50.0))
        support_gain_mul = 0.7 if cur_public_support > 70.0 else 1.0

        # Military: raise army morale; lower revolt risk.
        add_metric_effect("army_morale", +min(8.0, m_mil * 0.10))
        add_metric_effect("revolt_risk", -min(8.0, m_mil * 0.10))

        # Management: reduce fiscal pressure; slightly improve public support and treasury.
        add_metric_effect("fiscal_pressure", -min(8.0, m_mgr * 0.10))
        add_metric_effect("public_support", +min(8.0, m_mgr * 0.06) * support_gain_mul)
        # treasury_balance is a resource with big clamp bounds; keep conservative.
        add_metric_effect("treasury_balance", +min(300000.0, m_mgr * 8000.0))

        # Politics: increase authority; decrease corruption and unrest.
        # Soft floor decay:
        # When corruption/unrest already low (<20), halve further reduction
        # to avoid flattening the game too early.
        cur_corruption = float(metrics.get("corruption", 50.0))
        cur_unrest = float(metrics.get("unrest", 25.0))
        decay_corruption = 0.5 if cur_corruption < 20.0 else 1.0
        decay_unrest = 0.5 if cur_unrest < 20.0 else 1.0

        add_metric_effect("authority", +min(8.0, m_pol * 0.10))
        add_metric_effect("corruption", -min(8.0, m_pol * 0.10) * decay_corruption)
        add_metric_effect("unrest", -min(8.0, m_pol * 0.06) * decay_unrest)

        # Scholarship: improve tax completion; reduce tax intensity and unrest.
        add_metric_effect("tax_completion_index", +min(8.0, m_sch * 0.10))
        add_metric_effect("tax_intensity", -min(8.0, m_sch * 0.08))
        # Round-2 tuning: slightly reduce scholarship -> public_support speed.
        add_metric_effect("public_support", +min(8.0, m_sch * 0.045) * support_gain_mul)

        return effects

    def _compute_tree_needs(
        self, *, metrics: Dict[str, float], flags: Optional[Dict[str, bool]] = None
    ) -> Dict[GrowthTreeKey, float]:
        """
        Need score (>=0) for each tree based on current metrics.
        Higher score => more points should go there (if selected).
        """
        fl = flags or {}
        # base needs from numeric-system metrics (all are 0..100 except treasury_balance).
        army_morale = float(metrics.get("army_morale", 60.0))
        revolt_risk = float(metrics.get("revolt_risk", 35.0))
        fiscal_pressure = float(metrics.get("fiscal_pressure", 30.0))
        public_support = float(metrics.get("public_support", 50.0))
        authority = float(metrics.get("authority", 50.0))
        corruption = float(metrics.get("corruption", 50.0))
        unrest = float(metrics.get("unrest", 25.0))
        tax_completion_index = float(metrics.get("tax_completion_index", 80.0))

        need_mil = (100.0 - army_morale) * 0.6 + revolt_risk * 0.4
        need_manage = fiscal_pressure * 0.6 + (100.0 - public_support) * 0.4
        need_politics = (100.0 - authority) * 0.5 + corruption * 0.5
        need_sch = (100.0 - tax_completion_index) * 0.6 + unrest * 0.4

        def buff_mul(tree: GrowthTreeKey) -> float:
            # Optional generic buffs controlled by flags: "growth_buff_<tree>".
            base = 1.0
            f = str(tree)
            for k, v in (fl or {}).items():
                if not v:
                    continue
                kk = str(k or "").lower()
                if kk == f"growth_buff_{f}":
                    base *= 1.15
            return base

        return {
            GrowthTree.MILITARY: max(0.0, need_mil) * buff_mul(GrowthTree.MILITARY),
            GrowthTree.MANAGEMENT: max(0.0, need_manage) * buff_mul(GrowthTree.MANAGEMENT),
            GrowthTree.POLITICS: max(0.0, need_politics) * buff_mul(GrowthTree.POLITICS),
            GrowthTree.SCHOLARSHIP: max(0.0, need_sch) * buff_mul(GrowthTree.SCHOLARSHIP),
        }

    def _pick_top3_need(self, *, metrics: Dict[str, float], flags: Optional[Dict[str, bool]] = None) -> List[GrowthTreeKey]:
        needs = self._compute_tree_needs(metrics=metrics, flags=flags)
        ranked = sorted(GrowthTree.ALL, key=lambda t: float(needs.get(t, 0.0)), reverse=True)
        return [ranked[0], ranked[1], ranked[2]]


# Alias exports used by older code-gen patterns.
GrowthTreeKey = GrowthTreeKey

