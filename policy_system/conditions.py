# -*- coding: utf-8 -*-
"""国策图因果条件：任务状态 + 数值快照（不依赖诏书 playbook）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from policy_system.schemas import PolicyTreeState


def metric_val(metrics: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    v = (metrics or {}).get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_task_target(target: str) -> Optional[str]:
    t = str(target or "").strip()
    if not t.startswith("task:"):
        return None
    tid = t.split(":", 1)[1].strip()
    return tid or None


@dataclass
class PolicyTaskView:
    template_id: str
    status: str
    assigned_quarter: int
    deadline_quarter: int
    overdue_quarters: int = 0
    objectives_met_ratio: float = 0.0


def _objective_met(obj: Dict[str, Any], metrics: Mapping[str, Any]) -> bool:
    t = str(obj.get("type") or "").strip()
    key = str(obj.get("key") or "").strip()
    if t == "stat_at_least":
        return metric_val(metrics, key) >= float(obj.get("value") or 0.0)
    if t == "stat_at_most":
        return metric_val(metrics, key) <= float(obj.get("value") or 0.0)
    if t == "stat_reduce_by":
        base = float(obj.get("baseline_value") or metric_val(metrics, key))
        delta = float(obj.get("value") or 0.0)
        return metric_val(metrics, key) <= (base - delta)
    return False


def build_task_views(
    tasks: Sequence[Any],
    *,
    quarter_index: int,
    metrics: Mapping[str, Any],
) -> Dict[str, PolicyTaskView]:
    """按 template_id 聚合任务视图（同模板取逾期最长的一条）。"""
    q = int(quarter_index)
    views: Dict[str, PolicyTaskView] = {}
    for raw in tasks or []:
        tid = str(getattr(raw, "template_id", None) or (raw.get("template_id") if isinstance(raw, dict) else "") or "").strip()
        if not tid:
            continue
        status = str(getattr(raw, "status", None) or (raw.get("status") if isinstance(raw, dict) else "") or "active").strip()
        aq = int(getattr(raw, "assigned_quarter", None) or (raw.get("assigned_quarter") if isinstance(raw, dict) else 0) or 0)
        dq = int(getattr(raw, "deadline_quarter", None) or (raw.get("deadline_quarter") if isinstance(raw, dict) else 0) or 0)
        objectives = list(
            getattr(raw, "objectives", None)
            or (raw.get("objectives") if isinstance(raw, dict) else None)
            or []
        )
        overdue = max(0, q - aq) if status == "active" else max(0, q - aq)
        if status == "failed":
            overdue = max(overdue, max(0, q - aq))
        met = sum(1 for obj in objectives if _objective_met(obj, metrics))
        ratio = (met / len(objectives)) if objectives else 0.0

        prev = views.get(tid)
        if prev is None or overdue > prev.overdue_quarters:
            views[tid] = PolicyTaskView(
                template_id=tid,
                status=status,
                assigned_quarter=aq,
                deadline_quarter=dq,
                overdue_quarters=overdue,
                objectives_met_ratio=ratio,
            )
    return views


def _metrics_all(cond: Mapping[str, Any], metrics: Mapping[str, Any], op: str) -> bool:
    bucket = cond.get(op) or {}
    if not isinstance(bucket, dict) or not bucket:
        return True
    for mk, threshold in bucket.items():
        val = metric_val(metrics, str(mk))
        if op == "metric_lt" and val >= float(threshold):
            return False
        if op == "metric_gte" and val < float(threshold):
            return False
        if op == "metric_lte" and val > float(threshold):
            return False
        if op == "metric_gt" and val <= float(threshold):
            return False
    return True


def _any_metric_lt(cond: Mapping[str, Any], metrics: Mapping[str, Any]) -> bool:
    bucket = cond.get("any_metric_lt") or {}
    if not isinstance(bucket, dict) or not bucket:
        return True
    return any(metric_val(metrics, str(mk)) < float(threshold) for mk, threshold in bucket.items())


def _task_cond_met(
    cond: Mapping[str, Any],
    *,
    task_view: Optional[PolicyTaskView],
) -> bool:
    if task_view is None:
        return False
    allowed = cond.get("task_status_in") or cond.get("task_status")
    if allowed:
        if isinstance(allowed, str):
            allowed = [allowed]
        if task_view.status not in allowed:
            return False
    overdue_min = int(cond.get("task_overdue_quarters_gte") or 0)
    if overdue_min and task_view.overdue_quarters < overdue_min:
        return False
    ratio_min = float(cond.get("objectives_met_ratio_gte") or 0.0)
    if ratio_min and task_view.objectives_met_ratio < ratio_min:
        return False
    return True


def condition_met(
    cond: Mapping[str, Any],
    *,
    tree: PolicyTreeState,
    flags: Mapping[str, Any],
    metrics: Mapping[str, Any],
    task_view: Optional[PolicyTaskView] = None,
) -> bool:
    """统一因果条件：节点/flag/指标/任务状态。"""
    c = cond or {}
    flag_req = c.get("flag_true")
    if flag_req and not flags.get(flag_req):
        return False
    flag_false = c.get("flag_false")
    if flag_false and flags.get(flag_false):
        return False

    node_req = c.get("node_status")
    node_id = c.get("node_id")
    if node_req and node_id:
        rt = tree.nodes.get(str(node_id))
        if rt is None or rt.status != str(node_req):
            return False
    node_status_in = c.get("node_status_in")
    if node_status_in and node_id:
        rt = tree.nodes.get(str(node_id))
        allowed = node_status_in if isinstance(node_status_in, list) else [node_status_in]
        if rt is None or rt.status not in allowed:
            return False
    prog_node = c.get("progress_gte_node")
    if prog_node:
        rt = tree.nodes.get(str(prog_node))
        prog_min = int(c.get("progress_gte") or 0)
        if rt is None or rt.progress < prog_min:
            return False

    if not _metrics_all(c, metrics, "metric_lt"):
        return False
    if not _metrics_all(c, metrics, "metric_gte"):
        return False
    if not _metrics_all(c, metrics, "metric_lte"):
        return False
    if not _metrics_all(c, metrics, "metric_gt"):
        return False
    if not _any_metric_lt(c, metrics):
        return False

    if any(k in c for k in ("task_status_in", "task_status", "task_overdue_quarters_gte", "objectives_met_ratio_gte")):
        if not _task_cond_met(c, task_view=task_view):
            return False

    return True
