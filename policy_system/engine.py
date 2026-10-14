# -*- coding: utf-8 -*-
"""国策图引擎：bootstrap、主线完成、因果推进（任务+数值）、playbook 导出、季末 tick。"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Set

from policy_system.catalog import get_xining_catalog, parse_playbook_target
from policy_system.conditions import (
    build_task_views,
    condition_met,
    metric_val,
    parse_task_target,
)
from policy_system.schemas import (
    PolicyEdgeDef,
    PolicyGraphCatalog,
    PolicyNodeUpdate,
    PolicyTreeState,
    PolicyTreeTickResult,
)
from policy_system.state import read_policy_tree, write_policy_tree


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


class PolicyTreeEngine:
    def __init__(self, catalog: Optional[PolicyGraphCatalog] = None) -> None:
        self.catalog = catalog or get_xining_catalog()

    def _requires_met(
        self,
        tree: PolicyTreeState,
        target_id: str,
        *,
        flags: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        task_views: Optional[Dict[str, Any]] = None,
        quarter_index: int = 0,
    ) -> bool:
        for edge in self.catalog.edges:
            if edge.edge_type != "requires" or edge.to_id != target_id:
                continue
            src = edge.from_id
            cond = edge.condition or {}
            if src in self.catalog.nodes:
                rt = tree.nodes.get(src)
                if rt is None:
                    return False
                allowed = cond.get("node_status_in") or ["active", "completed"]
                if isinstance(allowed, str):
                    allowed = [allowed]
                if rt.status not in allowed:
                    return False
                prog_min = int(cond.get("progress_gte") or 0)
                if rt.progress < prog_min:
                    return False
            elif not flags.get(src):
                return False
        return True

    def _risk_edge_active(
        self,
        edge: PolicyEdgeDef,
        tree: PolicyTreeState,
        *,
        flags: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> bool:
        src = edge.from_id
        rt = tree.nodes.get(src)
        if rt is None or rt.status not in ("active", "completed"):
            return False
        cond = edge.condition or {}
        cond = dict(cond)
        cond["node_id"] = src
        cond["node_status_in"] = cond.get("node_status_in") or ["active", "completed"]
        prog_min = int(cond.get("progress_gte") or 0)
        if rt.progress < prog_min:
            return False
        return condition_met(cond, tree=tree, flags=flags, metrics=metrics)

    def _advances_should_skip(
        self,
        tree: PolicyTreeState,
        target_id: str,
        effect: Dict[str, Any],
    ) -> bool:
        rt = tree.nodes.get(target_id)
        if rt is None:
            return False
        intended = str(effect.get("set_status") or "").strip()
        if rt.status in ("completed", "failed", "suspended"):
            return True
        if intended and rt.status == intended:
            return True
        return False

    def _apply_advances_effect(
        self,
        state_obj: Any,
        tree: PolicyTreeState,
        edge: PolicyEdgeDef,
        result: PolicyTreeTickResult,
        *,
        task_template: str = "",
    ) -> None:
        target = edge.to_id
        if target not in self.catalog.nodes:
            return
        effect = edge.effect or {}
        once = effect.get("once", True)
        if once and self._advances_should_skip(tree, target, effect):
            return

        trt = tree.get(target)
        ndef = self.catalog.nodes[target]
        new_status = str(effect.get("set_status") or "").strip()
        if new_status:
            trt.status = new_status
            result.node_updates.append(
                PolicyNodeUpdate(node_id=target, status=new_status, reason="advances:%s" % edge.id)
            )
        if effect.get("progress") is not None:
            trt.progress = min(ndef.progress_max, int(effect.get("progress") or 0))
            result.node_updates.append(
                PolicyNodeUpdate(
                    node_id=target,
                    progress=trt.progress,
                    reason="advances:%s" % edge.id,
                )
            )
        delta = int(effect.get("progress_delta") or 0)
        if delta != 0:
            trt.progress = max(0, min(ndef.progress_max, trt.progress + delta))
            if delta > 0 and trt.status in ("locked", "available"):
                trt.status = "active"
            elif delta < 0 and trt.progress <= 0 and trt.status == "active":
                trt.status = "locked"
            result.node_updates.append(
                PolicyNodeUpdate(
                    node_id=target,
                    progress_delta=delta,
                    progress=trt.progress,
                    status=trt.status,
                    reason="advances:%s" % edge.id,
                )
            )
            if (
                delta > 0
                and trt.progress >= ndef.progress_max
                and trt.status not in ("failed", "suspended")
            ):
                trt.status = "completed"
                result.node_updates.append(
                    PolicyNodeUpdate(node_id=target, status="completed", reason="advances_progress_max")
                )

        flag_key = str(effect.get("set_flag") or "").strip()
        if flag_key:
            state_obj.flags[flag_key] = True
            result.flags_delta[flag_key] = True

        src_status = str(effect.get("source_task_set_status") or "").strip()
        if src_status and task_template:
            result.task_status_updates.append(
                {"template_id": task_template, "status": src_status, "edge_id": edge.id}
            )

        result.advances_fired.append(
            {
                "edge_id": edge.id,
                "from": edge.from_id,
                "to": target,
                "task_template": task_template,
            }
        )

    def evaluate_advances(
        self,
        state_obj: Any,
        *,
        quarter_index: int,
        active_tasks: Optional[Sequence[Any]] = None,
        settled_tasks: Optional[Sequence[Any]] = None,
    ) -> PolicyTreeTickResult:
        """任务状态 + 数值因果推进节点（非诏书 playbook）。"""
        tree = read_policy_tree(state_obj)
        metrics = dict(getattr(state_obj, "metrics", None) or {})
        flags = dict(getattr(state_obj, "flags", None) or {})
        result = PolicyTreeTickResult()

        all_tasks = list(active_tasks or []) + list(settled_tasks or [])
        task_views = build_task_views(all_tasks, quarter_index=int(quarter_index), metrics=metrics)

        for edge in self.catalog.edges:
            if edge.edge_type != "advances":
                continue
            task_tid = parse_task_target(edge.from_id)
            if not task_tid:
                continue
            tv = task_views.get(task_tid)
            if not condition_met(
                edge.condition or {},
                tree=tree,
                flags=flags,
                metrics=metrics,
                task_view=tv,
            ):
                continue
            if not self._requires_met(
                tree,
                edge.to_id,
                flags=flags,
                metrics=metrics,
                task_views=task_views,
                quarter_index=quarter_index,
            ):
                continue
            self._apply_advances_effect(
                state_obj,
                tree,
                edge,
                result,
                task_template=task_tid,
            )

        write_policy_tree(state_obj, tree)
        return result

    def bootstrap(
        self,
        state_obj: Any,
        *,
        completed_main_ids: Optional[Set[str]] = None,
    ) -> PolicyTreeTickResult:
        """从 flags + 已完成主线重建节点状态。"""
        tree = read_policy_tree(state_obj)
        flags = dict(getattr(state_obj, "flags", None) or {})
        completed = set(completed_main_ids or [])
        result = PolicyTreeTickResult()

        for nid, ndef in self.catalog.nodes.items():
            rt = tree.get(nid)
            if ndef.kind == "milestone":
                if nid in completed:
                    rt.status = "completed"
                    rt.progress = 100
                elif rt.status in ("", "locked"):
                    rt.status = ndef.initial_status or "available"
            elif ndef.kind in ("reform", "risk", "auto") and ndef.linked_flag:
                if flags.get(ndef.linked_flag):
                    if rt.status in ("locked", "available", ""):
                        rt.status = "active"
                        result.node_updates.append(
                            PolicyNodeUpdate(node_id=nid, status="active", reason="bootstrap_flag")
                        )
                    if rt.progress < 100 and rt.status not in ("completed", "failed", "suspended"):
                        rt.status = "active"
                elif rt.status in ("", "locked"):
                    rt.status = "locked"
            elif ndef.kind == "risk" and flags.get(nid):
                if rt.status in ("locked", "available", ""):
                    rt.status = "active"
                    result.node_updates.append(
                        PolicyNodeUpdate(node_id=nid, status="active", reason="bootstrap_risk_flag")
                    )

        write_policy_tree(state_obj, tree)
        return result

    def on_milestone_completed(
        self,
        state_obj: Any,
        main_id: str,
    ) -> PolicyTreeTickResult:
        tree = read_policy_tree(state_obj)
        result = PolicyTreeTickResult()
        mid = str(main_id or "").strip()
        if not mid or mid not in self.catalog.nodes:
            write_policy_tree(state_obj, tree)
            return result

        mrt = tree.get(mid)
        mrt.status = "completed"
        mrt.progress = 100
        result.node_updates.append(
            PolicyNodeUpdate(node_id=mid, status="completed", progress=100, reason="milestone_done")
        )

        for edge in self.catalog.edges:
            if edge.edge_type != "completes" or edge.from_id != mid:
                continue
            target = edge.to_id
            if target not in self.catalog.nodes:
                continue
            trt = tree.get(target)
            trt.status = "active"
            trt.progress = max(trt.progress, 1)
            result.node_updates.append(
                PolicyNodeUpdate(node_id=target, status="active", reason="completes_edge")
            )
            flag_key = str((edge.effect or {}).get("set_flag") or target)
            if flag_key:
                state_obj.flags[flag_key] = True
                result.flags_delta[flag_key] = True

        write_policy_tree(state_obj, tree)
        return result

    def on_task_settled(
        self,
        state_obj: Any,
        *,
        domain: str = "",
        task_key: str = "",
        result_status: str = "",
    ) -> PolicyTreeTickResult:
        """已弃用：诏书 playbook 不再推进国策节点。保留空实现以兼容旧调用。"""
        write_policy_tree(state_obj, read_policy_tree(state_obj))
        return PolicyTreeTickResult()

    def export_unlocked_playbooks(
        self,
        state_obj: Any,
    ) -> List[Dict[str, str]]:
        tree = read_policy_tree(state_obj)
        flags = dict(getattr(state_obj, "flags", None) or {})
        playbooks: List[Dict[str, str]] = []

        for edge in self.catalog.edges:
            if edge.edge_type != "unlocks":
                continue
            src = edge.from_id
            if src not in self.catalog.nodes:
                continue
            rt = tree.nodes.get(src)
            if rt is None:
                continue
            cond = edge.condition or {}
            allowed_status = cond.get("node_status_in") or [cond.get("node_status") or "active"]
            if isinstance(allowed_status, str):
                allowed_status = [allowed_status]
            if rt.status not in allowed_status:
                continue
            flag_req = cond.get("flag_true")
            if flag_req and not flags.get(flag_req):
                continue
            pb = parse_playbook_target(edge.to_id)
            if pb:
                playbooks = _merge_playbooks(playbooks, [pb])

        return playbooks

    def tick_quarter_end(
        self,
        state_obj: Any,
        *,
        quarter_index: int,
        session_id: str = "",
        active_tasks: Optional[Sequence[Any]] = None,
    ) -> PolicyTreeTickResult:
        """季末：因果推进 + 被动效果 + risk 候选。"""
        tree = read_policy_tree(state_obj)
        metrics = dict(getattr(state_obj, "metrics", None) or {})
        result = PolicyTreeTickResult()

        advances = self.evaluate_advances(
            state_obj,
            quarter_index=int(quarter_index),
            active_tasks=active_tasks,
        )
        result.node_updates.extend(advances.node_updates)
        result.flags_delta.update(advances.flags_delta)
        result.advances_fired.extend(advances.advances_fired)
        result.task_status_updates.extend(advances.task_status_updates)
        tree = read_policy_tree(state_obj)

        for nid, ndef in self.catalog.nodes.items():
            if ndef.kind == "milestone":
                continue
            rt = tree.nodes.get(nid)
            if rt is None or rt.status not in ("active", "completed"):
                continue
            if ndef.passive_effects_per_quarter:
                result.passive_effects.extend(list(ndef.passive_effects_per_quarter))

        flags = dict(getattr(state_obj, "flags", None) or {})
        for edge in self.catalog.edges:
            if edge.edge_type != "risk_triggers":
                continue
            if not self._risk_edge_active(edge, tree, flags=flags, metrics=metrics):
                continue
            seed_src = "%s:%s:%s" % (session_id, quarter_index, edge.id)
            roll = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16) % 10000 / 10000.0
            if roll < float(edge.probability or 0.0):
                result.risk_event_candidates.append(
                    {
                        "edge_id": edge.id,
                        "from_node": edge.from_id,
                        "target": edge.to_id,
                        "roll": round(roll, 4),
                        "probability": edge.probability,
                    }
                )

        result.unlocked_playbooks = self.export_unlocked_playbooks(state_obj)
        write_policy_tree(state_obj, tree)
        return result

    def build_snapshot(self, state_obj: Any) -> Dict[str, Any]:
        from policy_system.state import policy_tree_snapshot

        tree = read_policy_tree(state_obj)
        snap = policy_tree_snapshot(tree, catalog_nodes=self.catalog.nodes)
        snap["unlocked_playbooks"] = self.export_unlocked_playbooks(state_obj)
        return snap


def get_policy_engine() -> PolicyTreeEngine:
    return PolicyTreeEngine(get_xining_catalog())
