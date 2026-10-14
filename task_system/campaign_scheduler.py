# -*- coding: utf-8 -*-
"""熙宁战役主线调度：按年季刷 main_*、逾期 drift、被动 reform、诏书白名单。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Set

from numeric_system.engine import QuarterEngine

from scenario_system.xining_calendar import quarter_to_campaign

from .campaign_catalog import (
    FLAG_PLAYBOOK_UNLOCKS,
    CampaignMainDef,
    all_auto_facts,
    get_main_def,
    main_id_for_slot,
)
from .campaign_session import (
    defer_conditional_main,
    get_applied_auto_fact_ids,
    get_completed_main_ids,
    is_main_completed,
    mark_auto_fact_applied,
    mark_main_completed,
    pop_deferred_conditional_mains,
)
from .war_arc import (
    init_war_arc_for_main,
    resolve_war_arc_on_main_complete,
    tick_war_arcs,
    war_arcs_snapshot,
)
from .metric_alignment import metric_value
from .task_models import TaskInstance
from .task_reward_resolver import TaskRewardResolver

CAMPAIGN_LOAD_CAP = 6


def is_campaign_main_task(task: TaskInstance) -> bool:
    return str(getattr(task, "source", "") or "") == "campaign_main" or str(
        getattr(task, "category", "") or ""
    ) == "campaign_main"


def counts_toward_campaign_cap(task: TaskInstance) -> bool:
    rk = str(getattr(task, "resolution_kind", "objectives") or "objectives")
    if rk in ("edict_execution", "delegation"):
        return False
    return True


def _playbook_key(pb: Dict[str, str]) -> str:
    return "%s:%s" % (str(pb.get("domain") or "").strip(), str(pb.get("task_key") or "").strip())


def _merge_playbooks(
    base: List[Dict[str, str]],
    extra: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    seen: Set[str] = {_playbook_key(x) for x in base}
    out = list(base)
    for pb in extra or []:
        k = _playbook_key(pb)
        if k not in seen and pb.get("domain") and pb.get("task_key"):
            seen.add(k)
            out.append({"domain": str(pb["domain"]), "task_key": str(pb["task_key"])})
    return out


def materialize_main_instance(
    defn: CampaignMainDef,
    *,
    quarter_index: int,
    metrics: Dict[str, float],
) -> TaskInstance:
    objectives: List[Dict[str, Any]] = []
    for obj in defn.objectives or []:
        x = dict(obj)
        if str(x.get("type") or "") == "stat_reduce_by":
            k = str(x.get("key") or "")
            x["baseline_value"] = metric_value(metrics, k, 0.0)
        objectives.append(x)
    duration = max(1, int(defn.duration or 1))
    meta = {
        "main_id": defn.id,
        "on_complete_flags": dict(defn.on_complete_flags or {}),
        "passive_effects_per_quarter": list(defn.passive_effects_per_quarter or []),
        "drift_effects_per_quarter": list(defn.drift_effects_per_quarter or []),
        "drift_event_tags": list(defn.drift_event_tags or []),
        "allowed_edict_playbooks": list(defn.allowed_edict_playbooks or []),
        "drift_streak": 0,
    }
    return TaskInstance(
        instance_id=str(uuid.uuid4()),
        template_id=defn.id,
        title=defn.title,
        description=defn.description,
        category=defn.category,
        status="active",
        assigned_quarter=int(quarter_index),
        deadline_quarter=int(quarter_index) + duration,
        objectives=objectives,
        rewards=list(defn.rewards or []),
        penalties=list(defn.penalties or []),
        stall_penalties_per_quarter=list(defn.stall_penalties_per_quarter or []),
        source="campaign_main",
        resolution_kind=str(defn.resolution_kind or "objectives"),
        campaign_meta=meta,
    )


def _spawn_conditions_met(
    defn: CampaignMainDef,
    *,
    flags: Dict[str, Any],
    metrics: Dict[str, float],
) -> bool:
    if str(defn.spawn_mode or "scheduled") != "conditional":
        return True
    conds = list(defn.spawn_conditions or [])
    if not conds:
        return True
    flags_ok = True
    stat_ok = True
    has_stat_cond = False
    for c in conds:
        t = str(c.get("type") or "")
        if t == "flag_true":
            if not flags.get(str(c.get("key") or "")):
                flags_ok = False
        elif t == "any_stat_at_least":
            has_stat_cond = True
            keys = [str(x) for x in (c.get("keys") or [])]
            thr = float(c.get("value") or 0.0)
            if not any(metric_value(metrics, k, 0.0) >= thr for k in keys):
                stat_ok = False
    if has_stat_cond:
        return flags_ok and stat_ok
    return flags_ok


def _try_spawn_main(
    session_id: str,
    main_id: str,
    quarter_index: int,
    existing: List[TaskInstance],
    metrics: Dict[str, float],
    flags: Dict[str, Any],
) -> List[TaskInstance]:
    if not main_id or is_main_completed(session_id, main_id):
        return []
    active_ids = {t.template_id for t in existing if is_campaign_main_task(t)}
    if main_id in active_ids:
        return []
    defn = get_main_def(main_id)
    if defn is None:
        return []
    if not _spawn_conditions_met(defn, flags=flags, metrics=metrics):
        defer_conditional_main(session_id, main_id)
        return []
    return [materialize_main_instance(defn, quarter_index=quarter_index, metrics=metrics)]


def spawn_mains_for_quarter(
    session_id: str,
    quarter_index: int,
    existing: List[TaskInstance],
    metrics: Dict[str, float],
    flags: Optional[Dict[str, Any]] = None,
) -> List[TaskInstance]:
    fl: Dict[str, Any] = flags if isinstance(flags, dict) else dict(flags or {})
    out: List[TaskInstance] = []
    cq = quarter_to_campaign(quarter_index)
    scheduled_id = main_id_for_slot(cq.reign_year, cq.season)
    if scheduled_id:
        out.extend(_try_spawn_main(session_id, scheduled_id, quarter_index, existing + out, metrics, fl))
    for deferred_id in pop_deferred_conditional_mains(session_id):
        out.extend(_try_spawn_main(session_id, deferred_id, quarter_index, existing + out, metrics, fl))
    for task in out:
        init_war_arc_for_main(
            session_id,
            task.template_id,
            quarter_index,
            flags=fl,
        )
    return out


def apply_auto_facts(
    session_id: str,
    quarter_index: int,
    *,
    flags: Dict[str, Any],
    metrics: Dict[str, float],
    engine: QuarterEngine,
    state_obj: Any,
) -> List[Dict[str, Any]]:
    """C 类既定事实：到季且条件满足时自动结算一次。"""
    resolver = TaskRewardResolver()
    applied = get_applied_auto_fact_ids(session_id)
    traces: List[Dict[str, Any]] = []
    q = int(quarter_index)
    for fact in all_auto_facts():
        if fact.id in applied:
            continue
        if q < int(fact.earliest_quarter_index or 1):
            continue
        if not all(bool(flags.get(k)) == bool(v) for k, v in (fact.requires_flags or {}).items()):
            continue
        if fact.requires_any_stat_at_least:
            if not any(
                metric_value(metrics, str(k), 0.0) >= float(v)
                for k, v in fact.requires_any_stat_at_least.items()
            ):
                continue
        for k, v in (fact.sets_flags or {}).items():
            state_obj.flags[str(k)] = bool(v)
            flags[str(k)] = bool(v)
        mark_auto_fact_applied(session_id, fact.id)
        traces.append(
            {
                "fact_id": fact.id,
                "narrative_zh": fact.narrative_zh,
                "sets_flags": dict(fact.sets_flags or {}),
                "applied_effects": [],
            }
        )
    return traces


def apply_campaign_new_quarter_effects(
    session_id: str,
    quarter_index: int,
    *,
    flags: Dict[str, Any],
    metrics: Dict[str, float],
    engine: QuarterEngine,
    state_obj: Any,
    active_tasks: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """进新季后统一结算一次：C 类触发 → 主线被动 → C 类持续被动。"""
    auto_traces = apply_auto_facts(
        session_id,
        quarter_index,
        flags=flags,
        metrics=metrics,
        engine=engine,
        state_obj=state_obj,
    )
    passive_traces = apply_passive_reform_effects(
        flags=dict(state_obj.flags),
        engine=engine,
        state_obj=state_obj,
        session_id=session_id,
    )
    auto_passive_traces = apply_active_auto_fact_passives(
        session_id,
        engine=engine,
        state_obj=state_obj,
    )
    war_traces = tick_war_arcs(
        session_id,
        int(quarter_index),
        metrics=dict(state_obj.metrics),
    )
    policy_tick: Dict[str, Any] = {}
    try:
        from policy_system.engine import get_policy_engine
        from task_system.campaign_session import get_completed_main_ids

        policy_engine = get_policy_engine()
        policy_engine.bootstrap(state_obj, completed_main_ids=get_completed_main_ids(session_id))
        policy_tick = policy_engine.tick_quarter_end(
            state_obj,
            quarter_index=int(quarter_index),
            session_id=session_id,
            active_tasks=active_tasks,
        ).to_dict()
        if active_tasks is not None and policy_tick.get("task_status_updates"):
            from policy_system.task_mutations import apply_policy_task_status_updates

            policy_tick["applied_task_status_updates"] = apply_policy_task_status_updates(
                active_tasks,
                list(policy_tick.get("task_status_updates") or []),
            )
        if policy_tick.get("passive_effects"):
            resolver = TaskRewardResolver()
            eff = resolver.stat_change_items_to_effects(policy_tick.get("passive_effects") or [])
            if eff:
                engine.apply_effects(state_obj, eff)
                policy_tick["applied_passive_effects"] = eff
    except ImportError:
        policy_tick = {}
    return {
        "auto_facts": auto_traces,
        "passive_reform": passive_traces,
        "auto_passive": auto_passive_traces,
        "war_arcs": war_traces,
        "war_arcs_snapshot": war_arcs_snapshot(session_id),
        "policy_tree": policy_tick,
    }


def apply_active_auto_fact_passives(
    session_id: str,
    *,
    engine: QuarterEngine,
    state_obj: Any,
) -> List[Dict[str, Any]]:
    """已触发的 C 类事实：每季被动 effects。"""
    resolver = TaskRewardResolver()
    applied = get_applied_auto_fact_ids(session_id)
    traces: List[Dict[str, Any]] = []
    for fact in all_auto_facts():
        if fact.id not in applied or not fact.passive_effects_per_quarter:
            continue
        eff = resolver.stat_change_items_to_effects(fact.passive_effects_per_quarter)
        if eff:
            engine.apply_effects(state_obj, eff)
            traces.append({"fact_id": fact.id, "applied_effects": eff})
    return traces


def collect_allowed_edict_playbooks(
    active_tasks: List[TaskInstance],
    flags: Dict[str, Any],
    *,
    state_obj: Any = None,
) -> List[Dict[str, str]]:
    playbooks: List[Dict[str, str]] = []
    for t in active_tasks or []:
        if not is_campaign_main_task(t):
            continue
        meta = dict(getattr(t, "campaign_meta", None) or {})
        playbooks = _merge_playbooks(playbooks, list(meta.get("allowed_edict_playbooks") or []))
    for flag, val in (flags or {}).items():
        if val and flag in FLAG_PLAYBOOK_UNLOCKS:
            playbooks = _merge_playbooks(playbooks, FLAG_PLAYBOOK_UNLOCKS[flag])
    if state_obj is not None:
        try:
            from policy_system.engine import get_policy_engine

            playbooks = _merge_playbooks(
                playbooks,
                get_policy_engine().export_unlocked_playbooks(state_obj),
            )
        except ImportError:
            pass
    return playbooks


def is_playbook_allowed(
    playbooks: List[Dict[str, str]],
    *,
    domain: str,
    task_key: str,
) -> bool:
    dom = str(domain or "").strip()
    tk = str(task_key or "").strip()
    if not dom or not tk:
        return False
    for pb in playbooks or []:
        if str(pb.get("domain") or "").strip() == dom and str(pb.get("task_key") or "").strip() == tk:
            return True
    return False


def apply_overdue_drift(
    active_tasks: List[TaskInstance],
    quarter_index: int,
    *,
    engine: QuarterEngine,
    state_obj: Any,
) -> List[Dict[str, Any]]:
    """对逾期仍未完成的主线施加 drift_effects_per_quarter。"""
    q = int(quarter_index)
    resolver = TaskRewardResolver()
    traces: List[Dict[str, Any]] = []
    for t in active_tasks or []:
        if not is_campaign_main_task(t) or str(t.status) != "active":
            continue
        if int(t.assigned_quarter) >= q:
            continue
        meta = dict(getattr(t, "campaign_meta", None) or {})
        drift = list(meta.get("drift_effects_per_quarter") or [])
        if not drift:
            continue
        eff = resolver.stat_change_items_to_effects(drift)
        if eff:
            engine.apply_effects(state_obj, eff)
        meta["drift_streak"] = int(meta.get("drift_streak") or 0) + 1
        t.campaign_meta = meta
        traces.append(
            {
                "template_id": t.template_id,
                "title": t.title,
                "drift_streak": meta["drift_streak"],
                "applied_effects": eff,
            }
        )
    return traces


def apply_passive_reform_effects(
    *,
    flags: Dict[str, Any],
    engine: QuarterEngine,
    state_obj: Any,
    session_id: str,
) -> List[Dict[str, Any]]:
    """已完成主线 flags 触发的每季被动 effects。"""
    resolver = TaskRewardResolver()
    traces: List[Dict[str, Any]] = []
    completed = get_completed_main_ids(session_id)
    for mid in completed:
        defn = get_main_def(mid)
        if defn is None or not defn.passive_effects_per_quarter:
            continue
        active_flag = any(flags.get(k) for k in (defn.on_complete_flags or {}))
        if not active_flag and defn.on_complete_flags:
            continue
        eff = resolver.stat_change_items_to_effects(defn.passive_effects_per_quarter)
        if eff:
            engine.apply_effects(state_obj, eff)
            traces.append({"main_id": mid, "applied_effects": eff})
    return traces


def on_main_task_completed(
    session_id: str,
    template_id: str,
    state_obj: Any,
) -> Dict[str, Any]:
    """主线完成：记入 history 并写入 flags。"""
    defn = get_main_def(template_id)
    if defn is None:
        return {}
    mark_main_completed(session_id, template_id)
    applied: Dict[str, bool] = {}
    for k, v in (defn.on_complete_flags or {}).items():
        state_obj.flags[str(k)] = bool(v)
        applied[str(k)] = bool(v)
    arc_out = resolve_war_arc_on_main_complete(
        session_id,
        template_id,
        flags=state_obj.flags,
        metrics=dict(getattr(state_obj, "metrics", {}) or {}),
        state_obj=state_obj,
        quarter_index=int(getattr(state_obj, "quarter_index", 0) or 0),
    )
    if arc_out:
        for k, v in (arc_out.get("flags") or {}).items():
            state_obj.flags[str(k)] = bool(v)
            applied[str(k)] = bool(v)
    policy_trace: Dict[str, Any] = {}
    try:
        from policy_system.engine import get_policy_engine

        policy_trace = get_policy_engine().on_milestone_completed(state_obj, template_id).to_dict()
    except ImportError:
        policy_trace = {}
    return {
        "main_id": template_id,
        "flags": applied,
        "war_arc": arc_out,
        "policy_tree": policy_trace,
    }


def campaign_cap_load(active_tasks: List[TaskInstance], *, pending_event: bool = False) -> int:
    n = sum(1 for t in (active_tasks or []) if counts_toward_campaign_cap(t))
    if pending_event:
        n += 1
    return n


def random_fill_slots(active_tasks: List[TaskInstance], *, pending_event: bool = False) -> int:
    return max(0, CAMPAIGN_LOAD_CAP - campaign_cap_load(active_tasks, pending_event=pending_event))


_TAXONOMY_EVENT_TAGS: Optional[Dict[str, List[str]]] = None


def _taxonomy_event_tag_index() -> Dict[str, List[str]]:
    global _TAXONOMY_EVENT_TAGS
    if _TAXONOMY_EVENT_TAGS is not None:
        return _TAXONOMY_EVENT_TAGS
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parent / "catalog" / "campaign_xining_taxonomy.json"
    out: Dict[str, List[str]] = {}
    if path.is_file():
        try:
            tax = json.loads(path.read_text(encoding="utf-8"))
            for row in list(tax.get("tier_B_choice_events") or []):
                eid = str(row.get("event_id") or "").strip()
                if not eid:
                    continue
                out[eid] = [str(x) for x in (row.get("boost_tags") or []) if str(x).strip()]
        except (OSError, json.JSONDecodeError):
            out = {}
    _TAXONOMY_EVENT_TAGS = out
    return out


def _collect_drift_tag_boosts(
    active_tasks: List[TaskInstance],
    quarter_index: int,
) -> Dict[str, float]:
    boosts: Dict[str, float] = {}
    q = int(quarter_index)
    for t in active_tasks or []:
        if not is_campaign_main_task(t) or str(t.status) != "active":
            continue
        if int(t.assigned_quarter) >= q:
            continue
        meta = dict(getattr(t, "campaign_meta", None) or {})
        streak = max(1, int(meta.get("drift_streak") or 0))
        for tag in meta.get("drift_event_tags") or []:
            tg = str(tag).strip()
            if tg:
                boosts[tg] = boosts.get(tg, 0.0) + 1.25 * float(streak)
    return boosts


def build_campaign_event_roll_context(
    session_id: str,
    quarter_index: int,
    active_tasks: List[TaskInstance],
    *,
    policy_tick: Optional[Dict[str, Any]] = None,
    flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """国策 risk + 主线逾期 drift → 事件 roll 加权（仅后端）。"""
    del session_id  # reserved for future session-scoped boosts
    boost_events: Dict[str, float] = {}
    boost_tags = _collect_drift_tag_boosts(active_tasks, quarter_index)

    try:
        from policy_system.catalog import parse_event_target
    except ImportError:
        parse_event_target = None  # type: ignore

    for cand in (policy_tick or {}).get("risk_event_candidates") or []:
        target = str(cand.get("target") or "").strip()
        eid = parse_event_target(target) if parse_event_target else ""
        if not eid and target.startswith("event:"):
            eid = target.split(":", 1)[1].strip()
        if eid:
            boost_events[eid] = max(boost_events.get(eid, 0.0), 10.0)

    tag_index = _taxonomy_event_tag_index()
    for eid, mult in list(boost_events.items()):
        for tg in tag_index.get(eid) or []:
            boost_tags[tg] = max(boost_tags.get(tg, 0.0), mult * 0.15)

    return {
        "era_tags": ["song", "xining"],
        "flags": {str(k): bool(v) for k, v in (flags or {}).items()},
        "boost_event_weights": boost_events,
        "boost_tags": boost_tags,
    }
