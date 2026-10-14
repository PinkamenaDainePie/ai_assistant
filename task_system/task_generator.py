# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import random
import uuid
from typing import Any, Dict, List, Optional, Sequence, Set

from .metric_alignment import metric_value
from .task_models import TaskInstance, TaskTemplate

# 第一季度固定三张（可按 env 覆盖）；不受触发条件过滤，保证开局一致。
_DEFAULT_QUARTER1_TEMPLATE_IDS: Sequence[str] = (
    "internal_restore_authority",
    "military_raise_morale",
    "faction_balance_court",
)


class TaskGenerator:
    _SOFT_ALPHA = 0.05

    _TREE_KEYS = ("military", "management", "politics", "scholarship")

    def _trigger_match(self, tpl: TaskTemplate, metrics: Dict[str, float]) -> bool:
        for c in (tpl.trigger_conditions or []):
            t = str(c.get("type") or "")
            k = str(c.get("key") or "")
            v = float(c.get("value") or 0.0)
            cur = metric_value(metrics, k, 0.0)
            if t == "stat_greater_than" and not (cur > v):
                return False
            if t == "stat_less_than" and not (cur < v):
                return False
            if t == "stat_at_least" and not (cur >= v):
                return False
            if t == "stat_at_most" and not (cur <= v):
                return False
        return True

    def _tpl_to_tree(self, tpl: TaskTemplate) -> Optional[str]:
        # Map a template to one growth tree using stable signals:
        # 1) Objectives about tax completion/intensity => scholarship
        # 2) Category => military/management/politics fallback
        obj_keys = {
            str(o.get("key") or "").strip()
            for o in (tpl.objectives or [])
            if isinstance(o, dict)
        }
        if "tax_completion_index" in obj_keys or "tax_intensity" in obj_keys:
            return "scholarship"

        cat = str(tpl.category or "").strip()
        if cat == "military":
            return "military"
        if cat in ("finance", "livelihood", "agriculture", "fiscal"):
            return "management"
        if cat in ("internal_affairs", "faction"):
            return "politics"
        return None

    def _weight(
        self,
        tpl: TaskTemplate,
        metrics: Dict[str, float],
        recently_used: Set[str],
        growth_levels: Optional[Dict[str, int]] = None,
    ) -> float:
        w = float(tpl.priority or 1)
        if tpl.id in recently_used:
            w *= 0.5
        if "财政" in tpl.tags and float(metrics.get("fiscal_pressure", 0.0)) > 60:
            w += 20
        if "民生" in tpl.tags and float(metrics.get("unrest", 0.0)) > 55:
            w += 20
        if "农政" in tpl.tags and float(metrics.get("disaster_index", 0.0)) > 22:
            w += 15
        if "农政" in tpl.tags and float(metrics.get("tax_completion_index", 100.0)) < 55:
            w += 12
        if "财政" in tpl.tags and float(metrics.get("fiscal_pressure", 0.0)) > 55:
            w += 14
        if "财政" in tpl.tags and float(metrics.get("tax_completion_index", 100.0)) < 52:
            w += 10
        if "军事" in tpl.tags and float(metrics.get("army_morale", 100.0)) < 60:
            w += 20

        # Soft bias from growth tree levels (0..5):
        # this nudges which templates are more likely, not a hard unlock.
        tree = self._tpl_to_tree(tpl)
        if tree and growth_levels:
            lvl = int(growth_levels.get(tree, 0) or 0)
            if lvl > 0:
                w *= (1.0 + self._SOFT_ALPHA * lvl)

        return max(0.0, w)

    def _quarter1_fixed_disabled(self) -> bool:
        return os.getenv("TASK_QUARTER1_FIXED_DISABLE", "").strip().lower() in ("1", "true", "yes")

    def _quarter1_fixed_template_ids(self) -> List[str]:
        raw = (os.getenv("TASK_QUARTER1_FIXED_IDS") or "").strip()
        if raw:
            return [x.strip() for x in raw.split(",") if x.strip()]
        return list(_DEFAULT_QUARTER1_TEMPLATE_IDS)

    def _materialize_instances(
        self,
        selected: Sequence[TaskTemplate],
        *,
        metrics: Dict[str, float],
        quarter_index: int,
        story_owner_by_template: Optional[Dict[str, str]] = None,
    ) -> List[TaskInstance]:
        out: List[TaskInstance] = []
        owner_map = dict(story_owner_by_template or {})
        for tpl in selected:
            objectives = []
            for obj in (tpl.objectives or []):
                x = dict(obj)
                if str(x.get("type") or "") == "stat_reduce_by":
                    k = str(x.get("key") or "")
                    x["baseline_value"] = metric_value(metrics, k, 0.0)
                objectives.append(x)
            story_owner = str(owner_map.get(tpl.id) or "").strip()
            campaign_meta: Dict[str, Any] = {}
            if story_owner:
                campaign_meta["story_owner"] = story_owner
                try:
                    from .campaign_task_bindings import owner_label_zh

                    campaign_meta["story_owner_label_zh"] = owner_label_zh(story_owner)
                except ImportError:
                    pass
            out.append(
                TaskInstance(
                    instance_id=str(uuid.uuid4()),
                    template_id=tpl.id,
                    title=tpl.title,
                    description=tpl.description,
                    category=tpl.category,
                    status="active",
                    assigned_quarter=int(quarter_index),
                    deadline_quarter=int(quarter_index) + max(1, int(tpl.duration)),
                    objectives=objectives,
                    rewards=list(tpl.rewards),
                    penalties=list(tpl.penalties),
                    stall_penalties_per_quarter=list(tpl.stall_penalties_per_quarter or []),
                    source="system",
                    campaign_meta=campaign_meta,
                )
            )
        return out

    def _filter_by_reign_year(
        self,
        templates: List[TaskTemplate],
        reign_year: int,
    ) -> List[TaskTemplate]:
        if not reign_year:
            return list(templates)
        return [t for t in templates if int(getattr(t, "min_reign_year", 0) or 0) <= reign_year]

    def generate(
        self,
        templates: List[TaskTemplate],
        *,
        metrics: Dict[str, float],
        quarter_index: int,
        recent_template_ids: List[str],
        growth_levels: Optional[Dict[str, int]] = None,
        reign_year: int = 0,
        skip_quarter1_fixed: bool = False,
    ) -> List[TaskInstance]:
        q = int(quarter_index)
        templates = self._filter_by_reign_year(templates, reign_year)
        if q == 1 and not skip_quarter1_fixed and not self._quarter1_fixed_disabled():
            by_id = {t.id: t for t in templates}
            fixed_ids = self._quarter1_fixed_template_ids()
            ordered = [by_id[i] for i in fixed_ids if i in by_id]
            if ordered:
                return self._materialize_instances(ordered, metrics=metrics, quarter_index=q)

        eligible = [t for t in templates if self._trigger_match(t, metrics)]
        eligible.sort(key=lambda t: (-int(t.priority or 0), str(t.id)))
        if not eligible:
            return []
        recent_set = set(recent_template_ids or [])
        mandatory = [t for t in eligible if t.mandatory]
        optional = [t for t in eligible if not t.mandatory]
        seed_base = int(os.getenv("TASK_RANDOM_SEED", "424242"))
        rng = random.Random(seed_base + int(quarter_index) * 1009)
        target_count = 3
        if float(metrics.get("revolt_risk", 0.0)) > 65 or float(metrics.get("fiscal_pressure", 0.0)) > 70:
            target_count = 5
        elif float(metrics.get("unrest", 0.0)) > 50:
            target_count = 4
        target_count = min(5, max(3, target_count))
        selected: List[TaskTemplate] = []
        if mandatory:
            selected.append(sorted(mandatory, key=lambda x: x.priority, reverse=True)[0])
        used_categories = {x.category for x in selected}
        pool = optional[:]
        while pool and len(selected) < target_count:
            weighted = [(x, self._weight(x, metrics, recent_set, growth_levels=growth_levels)) for x in pool]
            total = sum(w for _, w in weighted if w > 0)
            if total <= 0:
                break
            r = rng.random() * total
            acc = 0.0
            pick = None
            for x, w in weighted:
                if w <= 0:
                    continue
                acc += w
                if r <= acc:
                    pick = x
                    break
            if pick is None:
                break
            if pick.category in used_categories and len(selected) < 3:
                pool = [x for x in pool if x.id != pick.id]
                continue
            selected.append(pick)
            used_categories.add(pick.category)
            pool = [x for x in pool if x.id != pick.id]

        return self._materialize_instances(selected, metrics=metrics, quarter_index=int(quarter_index))

    def compute_target_pool_size(
        self,
        metrics: Dict[str, float],
        *,
        campaign_mode: bool = False,
        cap_slots: int = 0,
    ) -> int:
        """战役模式用 cap_slots；否则 3～5。"""
        if campaign_mode:
            return max(0, int(cap_slots))
        target_count = 3
        if float(metrics.get("revolt_risk", 0.0)) > 65 or float(metrics.get("fiscal_pressure", 0.0)) > 70:
            target_count = 5
        elif float(metrics.get("unrest", 0.0)) > 50:
            target_count = 4
        return min(5, max(3, target_count))

    def generate_fill(
        self,
        templates: List[TaskTemplate],
        *,
        metrics: Dict[str, float],
        quarter_index: int,
        recent_template_ids: List[str],
        growth_levels: Optional[Dict[str, int]] = None,
        exclude_template_ids: Set[str],
        max_add: int,
        used_categories: Set[str],
        base_count: int,
        reign_year: int = 0,
        skip_quarter1_fixed: bool = False,
        active_story_owners: Optional[Set[str]] = None,
        campaign_flags: Optional[Dict[str, Any]] = None,
    ) -> List[TaskInstance]:
        """
        在已有任务之上补位：仅挑选 trigger 满足且 template_id 不在 exclude 中的模板。
        用于「未完成任务保留，只在空位上按数值条件生成新任务」。
        """
        q = int(quarter_index)
        if max_add <= 0:
            return []
        templates = self._filter_by_reign_year(templates, reign_year)
        if q == 1 and skip_quarter1_fixed:
            pass
        ex = set(exclude_template_ids or set())
        eligible = [t for t in templates if t.id not in ex and self._trigger_match(t, metrics)]
        if active_story_owners:
            try:
                from .campaign_task_bindings import (
                    primary_owner_for_template,
                    template_eligible_for_campaign,
                )

                owners = set(active_story_owners)
                fl = dict(campaign_flags or {})
                eligible = [
                    t
                    for t in eligible
                    if template_eligible_for_campaign(
                        t.id,
                        active_owners=owners,
                        quarter_index=q,
                        flags=fl,
                    )
                ]
            except ImportError:
                pass
        if not eligible:
            return []
        recent_set = set(recent_template_ids or [])
        seed_base = int(os.getenv("TASK_RANDOM_SEED", "424242"))
        rng = random.Random(seed_base + q * 1009 + 17 + len(ex))
        used = set(used_categories or set())
        selected: List[TaskTemplate] = []
        mandatory = [t for t in eligible if t.mandatory]
        optional = [t for t in eligible if not t.mandatory]

        if mandatory and len(selected) < max_add:
            m = sorted(mandatory, key=lambda x: x.priority, reverse=True)[0]
            if not (m.category in used and base_count + len(selected) < 3):
                selected.append(m)
                used.add(m.category)

        pool = [t for t in optional if t.id not in {x.id for x in selected}]
        while pool and len(selected) < max_add:
            weighted = [(x, self._weight(x, metrics, recent_set, growth_levels=growth_levels)) for x in pool]
            total = sum(w for _, w in weighted if w > 0)
            if total <= 0:
                break
            r = rng.random() * total
            acc = 0.0
            pick = None
            for x, w in weighted:
                if w <= 0:
                    continue
                acc += w
                if r <= acc:
                    pick = x
                    break
            if pick is None:
                break
            if pick.category in used and base_count + len(selected) < 3:
                pool = [x for x in pool if x.id != pick.id]
                continue
            selected.append(pick)
            used.add(pick.category)
            pool = [x for x in pool if x.id != pick.id]

        owner_by_tpl: Dict[str, str] = {}
        if active_story_owners:
            try:
                from .campaign_task_bindings import primary_owner_for_template

                for t in selected:
                    owner_by_tpl[t.id] = primary_owner_for_template(t.id) or next(
                        iter(active_story_owners), ""
                    )
            except ImportError:
                pass
        return self._materialize_instances(
            selected,
            metrics=metrics,
            quarter_index=q,
            story_owner_by_template=owner_by_tpl,
        )

