# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from numeric_system.engine import QuarterEngine
from scenario_system.xining_calendar import is_song_xining_campaign, quarter_to_campaign

from .campaign_catalog import campaign_random_exclude_template_ids
from .campaign_scheduler import (
    collect_allowed_edict_playbooks,
    counts_toward_campaign_cap,
    is_campaign_main_task,
    is_playbook_allowed,
    on_main_task_completed,
    random_fill_slots,
    spawn_mains_for_quarter,
)
from .campaign_session import set_allowed_edict_playbooks, set_campaign_label
from .delegation_resolver import DelegationResolver
from .edict_execution_settler import EdictExecutionSettler
from .edict_narrative import narrative_delegation_phase, narrative_delegation_resolution
from .task_evaluator import TaskEvaluator
from .task_generator import TaskGenerator
from .task_models import TaskInstance
from .task_repository import TaskRepository
from .task_reward_resolver import TaskRewardResolver


class TaskManager:
    def __init__(self, templates_dir: Path):
        self.repo = TaskRepository(templates_dir)
        self.evaluator = TaskEvaluator()
        self.generator = TaskGenerator()
        self.resolver = TaskRewardResolver()

    def append_delegation_task(self, session_id: str, task: TaskInstance) -> None:
        cur = list(self.repo.get_active_tasks(session_id))
        cur.append(task)
        self.repo.set_active_tasks(session_id, cur)

    def append_edict_execution_task(self, session_id: str, task: TaskInstance) -> None:
        self.append_delegation_task(session_id, task)

    def fulfill_campaign_story_edicts(
        self,
        session_id: str,
        *,
        domain: str,
        task_key: str,
        quarter_index: int,
    ) -> List[str]:
        """本季有效诏书命中主线白名单时，标记 campaign_story 可结算为完成。"""
        dom = str(domain or "").strip()
        tk = str(task_key or "").strip()
        if not dom or not tk:
            return []
        q = int(quarter_index)
        touched: List[str] = []
        active = list(self.repo.get_active_tasks(session_id))
        for t in active:
            if str(getattr(t, "resolution_kind", "") or "") != "campaign_story":
                continue
            if not is_campaign_main_task(t):
                continue
            meta = dict(getattr(t, "campaign_meta", None) or {})
            allowed = list(meta.get("allowed_edict_playbooks") or [])
            if not is_playbook_allowed(allowed, domain=dom, task_key=tk):
                continue
            if int(t.assigned_quarter) > q or int(t.deadline_quarter) < q:
                continue
            meta["story_edict_done"] = True
            t.campaign_meta = meta
            touched.append(str(t.template_id))
        if touched:
            self.repo.set_active_tasks(session_id, active)
        return touched

    def apply_campaign_quarter_effects(
        self,
        *,
        session_id: str,
        quarter_index: int,
        engine: QuarterEngine,
        state_obj: Any,
    ) -> Dict[str, Any]:
        """季末 drift 已并入 settle_tasks_at_quarter_end；此处保留接口兼容。"""
        _ = (session_id, quarter_index, engine, state_obj)
        return {"drift": []}

    @staticmethod
    def _stall_items_for_task(task: TaskInstance) -> List[Dict[str, Any]]:
        stall = list(getattr(task, "stall_penalties_per_quarter", None) or [])
        if stall:
            return stall
        rk = str(getattr(task, "resolution_kind", "") or "")
        if rk == "war_arc":
            meta = dict(getattr(task, "campaign_meta", None) or {})
            drift = list(meta.get("drift_effects_per_quarter") or [])
            if drift:
                return drift
        return []

    @staticmethod
    def _accumulate_metric_delta(
        acc: Dict[str, float],
        effects: List[Dict[str, Any]],
    ) -> None:
        for e in effects or []:
            if str(e.get("action") or "") != "add_metric":
                continue
            key = str(e.get("key") or "").strip()
            if not key:
                continue
            acc[key] = float(acc.get(key, 0.0)) + float(e.get("value") or 0.0)

    def settle_tasks_at_quarter_end(
        self,
        *,
        session_id: str,
        quarter_index: int,
        state_metrics: Dict[str, float],
        engine: QuarterEngine,
        state_obj: Any,
    ) -> Dict[str, Any]:
        """
        季末任务结算：completed → rewards；Q >= deadline → expire penalties + 移出；
        assigned <= Q < deadline 且未完成 → stall_penalties（war_arc 用 drift alias）。
        """
        qidx = int(quarter_index)
        if self.repo.get_tasks_settled_quarter(session_id) == qidx:
            cached = self.repo.get_last_task_quarter_end(session_id)
            if cached:
                return cached

        active = list(self.repo.get_active_tasks(session_id))
        next_active: List[TaskInstance] = []
        settled_instances: List[TaskInstance] = []
        stall_rows: List[Dict[str, Any]] = []
        completed_rows: List[Dict[str, Any]] = []
        failed_rows: List[Dict[str, Any]] = []
        still_active_rows: List[Dict[str, Any]] = []
        settled: List[Dict[str, Any]] = []
        metrics_delta: Dict[str, float] = {}

        for t in active:
            rk = str(getattr(t, "resolution_kind", "objectives") or "objectives")
            if rk in ("delegation", "edict_execution"):
                next_active.append(t)
                continue

            res = self.evaluator.evaluate(t, state_metrics, qidx, session_id=session_id)
            completed = bool(res.get("completed"))

            if completed:
                result = "completed"
                effects_pack = self.resolver.build_effects_for_result(
                    result, t.rewards, t.penalties
                )
                t.status = result
                settled_instances.append(t)
                if is_campaign_main_task(t):
                    on_main_task_completed(session_id, t.template_id, state_obj)
                self.repo.append_history(
                    session_id,
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "assigned_quarter": t.assigned_quarter,
                        "resolved_quarter": qidx,
                        "result": result,
                    },
                )
                target = completed_rows
            elif qidx >= int(t.deadline_quarter):
                result = "failed_expired"
                effects_pack = self.resolver.build_effects_for_result(
                    "failed_expired", t.rewards, t.penalties
                )
                t.status = "failed"
                settled_instances.append(t)
                self.repo.append_history(
                    session_id,
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "assigned_quarter": t.assigned_quarter,
                        "resolved_quarter": qidx,
                        "result": "failed",
                    },
                )
                target = failed_rows
            elif qidx >= int(t.assigned_quarter):
                result = "stall_penalty"
                effects_pack = self.resolver.build_stall_effects(self._stall_items_for_task(t))
                next_active.append(t)
                target = stall_rows
            else:
                next_active.append(t)
                still_active_rows.append(
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "deadline_quarter": t.deadline_quarter,
                    }
                )
                continue

            eff = effects_pack.get("effects") or []
            if eff:
                engine.apply_effects(state_obj, eff)
                state_metrics.update(dict(state_obj.metrics))
                self._accumulate_metric_delta(metrics_delta, eff)

            row = {
                "task_id": t.instance_id,
                "template_id": t.template_id,
                "title": t.title,
                "result": result,
                "applied_effects": eff,
                "guardrail_trace": effects_pack.get("trace") or {},
                "resolution_kind": rk,
            }
            target.append(row)
            settled.append(row)

        try:
            from policy_system.engine import get_policy_engine
            from policy_system.task_mutations import apply_policy_task_status_updates

            adv = get_policy_engine().evaluate_advances(
                state_obj,
                quarter_index=qidx,
                active_tasks=next_active,
                settled_tasks=settled_instances,
            )
            apply_policy_task_status_updates(next_active, adv.task_status_updates)
            apply_policy_task_status_updates(settled_instances, adv.task_status_updates)
        except ImportError:
            pass

        self.repo.set_active_tasks(session_id, next_active)

        for t in next_active:
            if any(x.get("task_id") == t.instance_id for x in still_active_rows):
                continue
            still_active_rows.append(
                {
                    "task_id": t.instance_id,
                    "template_id": t.template_id,
                    "title": t.title,
                    "deadline_quarter": t.deadline_quarter,
                }
            )

        payload = {
            "quarter_index": qidx,
            "stall": stall_rows,
            "completed": completed_rows,
            "failed_expired": failed_rows,
            "still_active": still_active_rows,
            "settled": settled,
            "metrics_delta_from_tasks": metrics_delta,
            "active_count": len(next_active),
        }
        self.repo.set_last_task_quarter_end(session_id, quarter_index=qidx, payload=payload)
        return payload

    def settle_previous_quarter_tasks(
        self,
        *,
        session_id: str,
        quarter_index: int,
        state_metrics: Dict[str, float],
        engine: QuarterEngine,
        state_obj: Any,
    ) -> Dict[str, Any]:
        active = self.repo.get_active_tasks(session_id)
        next_active = []
        settled_instances = []
        settled: List[Dict[str, Any]] = []
        for t in active:
            if getattr(t, "resolution_kind", "objectives") == "delegation":
                aq = int(t.assigned_quarter)
                qidx = int(quarter_index)
                if qidx < aq:
                    next_active.append(t)
                    settled.append(
                        {
                            "task_id": t.instance_id,
                            "template_id": t.template_id,
                            "title": t.title,
                            "result": "active",
                            "applied_effects": [],
                            "guardrail_trace": {},
                            "resolution_kind": "delegation",
                        }
                    )
                    continue

                dmeta = dict(t.delegation or {})
                action_id = str(dmeta.get("action_id") or "anti_corruption")
                snap = dmeta.get("executor_context_snapshot") or {}
                if not isinstance(snap, dict):
                    snap = {}
                exec_name = str(dmeta.get("executor_name") or "").strip()
                if exec_name and not str(snap.get("name") or "").strip():
                    snap = {**snap, "name": exec_name}
                exec_ctx = snap if str(snap.get("name") or "").strip() else None

                phases_total = max(1, int(dmeta.get("phases_total") or 1))
                phase_index = max(0, int(dmeta.get("phase_index") or 0))
                if phases_total > 1 and phase_index < phases_total - 1 and qidx >= aq:
                    stance = str(snap.get("stance") or "")
                    party = str(snap.get("party") or "")
                    nar = narrative_delegation_phase(
                        executor_name=exec_name or str(snap.get("name") or ""),
                        action_id=action_id,
                        phase_index=phase_index,
                        phases_total=phases_total,
                        stance=stance,
                        party=party,
                    )
                    dmeta["phase_index"] = phase_index + 1
                    t.delegation = dmeta
                    next_active.append(t)
                    settled.append(
                        {
                            "task_id": t.instance_id,
                            "template_id": t.template_id,
                            "title": t.title,
                            "result": "delegation_phase",
                            "success": False,
                            "applied_effects": [],
                            "guardrail_trace": {},
                            "resolution_kind": "delegation",
                            "narrative_zh": nar,
                            "delegation_detail": {
                                "phase_index": phase_index,
                                "phases_total": phases_total,
                                "phase": True,
                            },
                        }
                    )
                    continue

                pack = DelegationResolver.resolve(
                    action_id=action_id,
                    metrics=dict(state_metrics),
                    executor_ctx=exec_ctx,
                    session_id=session_id,
                    task_instance_id=t.instance_id,
                    quarter_index=qidx,
                    task_key=str(dmeta.get("task_key") or ""),
                )
                outcome = str(pack.get("outcome") or "failure")
                t.status = outcome
                eff = pack.get("effects") or []
                applied_keys: List[str] = []
                for e in eff or []:
                    if isinstance(e, dict) and str(e.get("action") or "") == "add_metric":
                        k = str(e.get("key") or "").strip()
                        if k:
                            applied_keys.append(k)
                stance = str(snap.get("stance") or "")
                party = str(snap.get("party") or "")
                narrative_zh = narrative_delegation_resolution(
                    outcome=outcome,
                    executor_name=exec_name or str(snap.get("name") or ""),
                    a_score=float(pack.get("A") or 0.0),
                    d_score=float(pack.get("D") or 0.0),
                    applied_keys=applied_keys,
                    stance=stance,
                    party=party,
                )
                if eff:
                    engine.apply_effects(state_obj, eff)
                    state_metrics.update(dict(state_obj.metrics))
                self.repo.append_history(
                    session_id,
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "assigned_quarter": t.assigned_quarter,
                        "resolved_quarter": quarter_index,
                        "result": outcome,
                        "delegation": True,
                    },
                )
                settled.append(
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "result": outcome,
                        "success": outcome in ("success", "partial"),
                        "applied_effects": eff,
                        "guardrail_trace": pack.get("guardrail_trace") or {},
                        "resolution_kind": "delegation",
                        "narrative_zh": narrative_zh,
                        "delegation_detail": {
                            "p_final": pack.get("p_final"),
                            "A": pack.get("A"),
                            "D": pack.get("D"),
                        },
                    }
                )
                continue

            if getattr(t, "resolution_kind", "objectives") == "edict_execution":
                aq = int(t.assigned_quarter)
                qidx = int(quarter_index)
                if qidx < aq:
                    next_active.append(t)
                    settled.append(
                        {
                            "task_id": t.instance_id,
                            "template_id": t.template_id,
                            "title": t.title,
                            "result": "active",
                            "applied_effects": [],
                            "guardrail_trace": {},
                            "resolution_kind": "edict_execution",
                        }
                    )
                    continue
                emeta = dict(getattr(t, "edict_execution", None) or {})
                phases_total = max(1, int(emeta.get("phases_total") or 1))
                phase_index = max(0, int(emeta.get("phase_index") or 0))
                is_final = phase_index >= phases_total - 1
                if phases_total > 1 and not is_final and qidx >= aq:
                    pack_ph = EdictExecutionSettler.settle(
                        edict_meta=emeta,
                        metrics=dict(state_metrics),
                        ministers=None,
                        session_id=session_id,
                        task_instance_id=t.instance_id,
                        quarter_index=qidx,
                        phase_index=phase_index,
                        phases_total=phases_total,
                        is_final_phase=False,
                    )
                    emeta["phase_index"] = phase_index + 1
                    t.edict_execution = emeta
                    next_active.append(t)
                    settled.append(
                        {
                            "task_id": t.instance_id,
                            "template_id": t.template_id,
                            "title": t.title,
                            "result": "edict_execution_phase",
                            "success": False,
                            "applied_effects": [],
                            "guardrail_trace": {},
                            "resolution_kind": "edict_execution",
                            "narrative_zh": pack_ph.get("narrative_zh") or "",
                        }
                    )
                    continue
                pack_ex = EdictExecutionSettler.settle(
                    edict_meta=emeta,
                    metrics=dict(state_metrics),
                    ministers=None,
                    session_id=session_id,
                    task_instance_id=t.instance_id,
                    quarter_index=qidx,
                    phase_index=phase_index,
                    phases_total=phases_total,
                    is_final_phase=True,
                )
                outcome = str(pack_ex.get("result") or "failure")
                t.status = outcome
                eff = pack_ex.get("applied_effects") or []
                if eff:
                    engine.apply_effects(state_obj, eff)
                    state_metrics.update(dict(state_obj.metrics))
                self.repo.append_history(
                    session_id,
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "assigned_quarter": t.assigned_quarter,
                        "resolved_quarter": quarter_index,
                        "result": outcome,
                        "edict_execution": True,
                    },
                )
                settled.append(
                    {
                        "task_id": t.instance_id,
                        "template_id": t.template_id,
                        "title": t.title,
                        "result": outcome,
                        "success": bool(pack_ex.get("success")),
                        "applied_effects": eff,
                        "guardrail_trace": pack_ex.get("guardrail_trace") or {},
                        "resolution_kind": "edict_execution",
                        "narrative_zh": pack_ex.get("narrative_zh") or "",
                    }
                )
                continue

        try:
            from policy_system.engine import get_policy_engine
            from policy_system.task_mutations import apply_policy_task_status_updates

            adv = get_policy_engine().evaluate_advances(
                state_obj,
                quarter_index=int(quarter_index),
                active_tasks=next_active,
                settled_tasks=settled_instances,
            )
            apply_policy_task_status_updates(next_active, adv.task_status_updates)
            apply_policy_task_status_updates(settled_instances, adv.task_status_updates)
        except ImportError:
            pass

        self.repo.set_active_tasks(session_id, next_active)
        return {"settled": settled, "active_count": len(next_active)}

    def _tasks_to_assign_payload(
        self,
        tasks: List[Any],
        history: List[Dict[str, Any]],
        *,
        campaign_label_zh: str = "",
        allowed_edict_playbooks: Optional[List[Dict[str, str]]] = None,
        active_story_owners: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "tasks": [
                {
                    "task_id": t.instance_id,
                    "template_id": t.template_id,
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "status": t.status,
                    "assigned_quarter": t.assigned_quarter,
                    "deadline_quarter": t.deadline_quarter,
                    "objectives": t.objectives,
                    "rewards": t.rewards,
                    "penalties": t.penalties,
                    "resolution_kind": getattr(t, "resolution_kind", "objectives"),
                    "delegation": getattr(t, "delegation", None) or {},
                    "edict_execution": dict(getattr(t, "edict_execution", None) or {}),
                    "source": getattr(t, "source", "system"),
                    "campaign_meta": dict(getattr(t, "campaign_meta", None) or {}),
                }
                for t in tasks
            ],
            "active_count": len(tasks),
            "history_tail": history[-10:],
            "campaign_label_zh": campaign_label_zh,
            "allowed_edict_playbooks": list(allowed_edict_playbooks or []),
            "active_story_owners": list(active_story_owners or []),
        }

    def generate_and_assign_tasks(
        self,
        *,
        session_id: str,
        quarter_index: int,
        state_metrics: Dict[str, float],
        growth_levels: Optional[Dict[str, int]] = None,
        data_root: str = "",
        scenario_id: str = "",
        pending_event: bool = False,
        flags: Optional[Dict[str, Any]] = None,
        state_obj: Any = None,
    ) -> Dict[str, Any]:
        history = self.repo.get_history(session_id)
        recent = [x.get("template_id", "") for x in history[-6:]]
        templates = self.repo.list_templates()
        existing = list(self.repo.get_active_tasks(session_id))
        q = int(quarter_index)
        campaign = is_song_xining_campaign(data_root=data_root, scenario_id=scenario_id)

        fl: Dict[str, Any] = flags if isinstance(flags, dict) else dict(flags or {})

        if campaign:
            cq = quarter_to_campaign(q)
            label_zh = cq.label_zh
            set_campaign_label(session_id, label_zh)

            # 保留所有未完成实例（含主线）
            combined = list(existing)
            spawned = spawn_mains_for_quarter(
                session_id, q, combined, state_metrics, flags=fl
            )
            if spawned:
                combined.extend(spawned)

            slots = random_fill_slots(combined, pending_event=pending_event)
            from task_system.campaign_session import get_completed_main_ids
            from task_system.campaign_task_bindings import resolve_active_story_owners

            story_owners = resolve_active_story_owners(
                q,
                flags=fl,
                active_tasks=combined,
                completed_main_ids=get_completed_main_ids(session_id),
            )
            if slots > 0:
                exclude_ids: Set[str] = (
                    {t.template_id for t in combined} | campaign_random_exclude_template_ids()
                )
                used_cats: Set[str] = {t.category for t in combined if counts_toward_campaign_cap(t)}
                cap_count = sum(1 for t in combined if counts_toward_campaign_cap(t))
                additional = self.generator.generate_fill(
                    templates,
                    metrics=state_metrics,
                    quarter_index=q,
                    recent_template_ids=recent,
                    growth_levels=growth_levels,
                    exclude_template_ids=exclude_ids,
                    max_add=slots,
                    used_categories=used_cats,
                    base_count=cap_count,
                    reign_year=cq.reign_year,
                    skip_quarter1_fixed=True,
                    active_story_owners=story_owners,
                    campaign_flags=fl,
                )
                combined.extend(additional)

            playbooks = collect_allowed_edict_playbooks(combined, fl, state_obj=state_obj)
            set_allowed_edict_playbooks(session_id, playbooks)
            self.repo.set_active_tasks(session_id, combined)
            payload = self._tasks_to_assign_payload(
                combined,
                history,
                campaign_label_zh=label_zh,
                allowed_edict_playbooks=playbooks,
                active_story_owners=sorted(story_owners),
            )
            if state_obj is not None:
                try:
                    from policy_system.engine import get_policy_engine
                    from task_system.campaign_session import get_completed_main_ids

                    pe = get_policy_engine()
                    pe.bootstrap(state_obj, completed_main_ids=get_completed_main_ids(session_id))
                except ImportError:
                    pass
            return payload

        # 非战役模式：沿用原逻辑
        if not existing:
            tasks = self.generator.generate(
                templates,
                metrics=state_metrics,
                quarter_index=quarter_index,
                recent_template_ids=recent,
                growth_levels=growth_levels,
            )
            self.repo.set_active_tasks(session_id, tasks)
            return self._tasks_to_assign_payload(tasks, history)

        target = self.generator.compute_target_pool_size(state_metrics)
        needed = max(0, target - len(existing))
        if needed == 0:
            self.repo.set_active_tasks(session_id, existing)
            return self._tasks_to_assign_payload(existing, history)

        exclude_ids = {t.template_id for t in existing}
        used_cats = {t.category for t in existing}
        additional = self.generator.generate_fill(
            templates,
            metrics=state_metrics,
            quarter_index=quarter_index,
            recent_template_ids=recent,
            growth_levels=growth_levels,
            exclude_template_ids=exclude_ids,
            max_add=needed,
            used_categories=used_cats,
            base_count=len(existing),
        )
        combined = existing + additional
        self.repo.set_active_tasks(session_id, combined)
        return self._tasks_to_assign_payload(combined, history)

    def get_session_tasks(self, session_id: str) -> Dict[str, Any]:
        active = self.repo.get_active_tasks(session_id)
        return {
            "active": [
                {
                    "task_id": t.instance_id,
                    "template_id": t.template_id,
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "status": t.status,
                    "assigned_quarter": t.assigned_quarter,
                    "deadline_quarter": t.deadline_quarter,
                    "objectives": t.objectives,
                    "resolution_kind": getattr(t, "resolution_kind", "objectives"),
                    "delegation": getattr(t, "delegation", None) or {},
                    "edict_execution": dict(getattr(t, "edict_execution", None) or {}),
                    "source": getattr(t, "source", "system"),
                    "campaign_meta": dict(getattr(t, "campaign_meta", None) or {}),
                }
                for t in active
            ],
            "history": self.repo.get_history(session_id),
        }
