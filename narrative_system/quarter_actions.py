# -*- coding: utf-8 -*-
"""本季诏书动作列表：供 Agent B（Workflow B）读取全部分段。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def _segment_text_from_context(
    exec_ctx: Dict[str, Any],
    *,
    index: int,
    domain: str,
    task_key: str,
) -> str:
    multi = list(exec_ctx.get("multi_domain_segments") or [])
    if 0 <= index < len(multi):
        row = multi[index]
        if isinstance(row, dict):
            t = str(row.get("text") or "").strip()
            if t:
                return t
    for row in multi:
        if not isinstance(row, dict):
            continue
        if str(row.get("domain") or "").strip() == domain and str(row.get("task_key") or "").strip() == task_key:
            t = str(row.get("text") or "").strip()
            if t:
                return t
    return ""


def _selected_keys(agent_a_selection: Optional[Dict[str, Any]]) -> Set[Tuple[int, str, str]]:
    keys: Set[Tuple[int, str, str]] = set()
    for row in (agent_a_selection or {}).get("selected") or []:
        if not isinstance(row, dict):
            continue
        keys.add(
            (
                int(row.get("index") if row.get("index") is not None else -1),
                str(row.get("domain") or "").strip(),
                str(row.get("task_key") or "").strip(),
            )
        )
    return keys


def build_quarter_edict_actions(
    *,
    resolved_pack: Optional[Dict[str, Any]] = None,
    execution_context: Optional[Dict[str, Any]] = None,
    player_pack: Optional[Dict[str, Any]] = None,
    agent_flow_report: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    组装本季全部诏书动作（Agent B 分项依据）。
    优先 player_pack 存档；否则从 resolved_pack + execution_context 现场组装。
    """
    stored = list((player_pack or {}).get("quarter_edict_actions") or [])
    if stored:
        out = [dict(r) for r in stored if isinstance(r, dict)]
        _apply_agent_a_flags(out, agent_flow_report)
        return out

    exec_ctx = dict(execution_context or {})
    pack = dict(resolved_pack or {})
    agent_sel = _agent_a_selection_from_report(agent_flow_report)
    selected_keys = _selected_keys(agent_sel)

    from agent_flow.action_selector import classify_action_tier

    out: List[Dict[str, Any]] = []
    segment_packs = list(pack.get("segment_packs") or [])
    if segment_packs:
        for row in segment_packs:
            if not isinstance(row, dict):
                continue
            dom = str(row.get("domain") or "").strip()
            if not dom:
                continue
            idx = int(row.get("index") if row.get("index") is not None else len(out))
            tk = str(row.get("task_key") or "").strip()
            tier = str(row.get("action_tier") or "").strip().lower()
            if tier not in ("contest", "counter", "other"):
                tier = classify_action_tier(dom, tk)
            out.append(
                {
                    "index": idx,
                    "domain": dom,
                    "task_key": tk,
                    "text": _segment_text_from_context(exec_ctx, index=idx, domain=dom, task_key=tk),
                    "action_tier": tier,
                    "status": str(row.get("status") or "resolved"),
                    "effects_count": int(row.get("effects_count") or 0),
                    "task_path": str(row.get("task_path") or ""),
                    "agent_a_selected": (idx, dom, tk) in selected_keys,
                }
            )
        return out

    # 单域：从 execution_context.primary_task 或 final_frame 合成一条
    pt = dict(exec_ctx.get("primary_task") or {})
    dom = str(pt.get("domain") or "").strip()
    tk = str(pt.get("task_key") or "").strip()
    if not dom:
        ff = dict(pack.get("final_frame") or {})
        if not ff and isinstance(exec_ctx.get("final_frame"), dict):
            ff = dict(exec_ctx.get("final_frame") or {})
        task = dict(ff.get("task") or {})
        dom = str(task.get("domain") or "").strip()
        tk = str(task.get("task_key") or "").strip()
    if dom:
        tier = classify_action_tier(dom, tk)
        out.append(
            {
                "index": 0,
                "domain": dom,
                "task_key": tk,
                "text": "",
                "action_tier": tier,
                "status": str(pack.get("resolution_status") or "resolved"),
                "effects_count": len(list(pack.get("current_effects") or [])),
                "task_path": str(pack.get("task_path") or ""),
                "agent_a_selected": (0, dom, tk) in selected_keys,
            }
        )
    return out


def _agent_a_selection_from_report(agent_flow_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    report = dict(agent_flow_report or {})
    trace = dict(report.get("trace") or {})
    sel = dict(trace.get("agent_a_selection") or {})
    if sel:
        return sel
    exec_ctx = dict(report.get("execution_context") or {})
    return dict(exec_ctx.get("agent_a_selection") or {})


def _apply_agent_a_flags(
    actions: List[Dict[str, Any]],
    agent_flow_report: Optional[Dict[str, Any]],
) -> None:
    sel = _agent_a_selection_from_report(agent_flow_report)
    selected_keys = _selected_keys(sel)
    if not selected_keys:
        return
    for row in actions:
        idx = int(row.get("index") if row.get("index") is not None else -1)
        dom = str(row.get("domain") or "").strip()
        tk = str(row.get("task_key") or "").strip()
        row["agent_a_selected"] = (idx, dom, tk) in selected_keys


def build_quarter_edict_actions_from_settle(
    *,
    resolved_pack: Dict[str, Any],
    execution_context: Dict[str, Any],
    agent_flow_report: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """结算当下组装并写入 player_quarter_pack 的快照。"""
    return build_quarter_edict_actions(
        resolved_pack=resolved_pack,
        execution_context=execution_context,
        agent_flow_report=agent_flow_report,
    )


def agent_a_selection_for_summary(agent_flow_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return _agent_a_selection_from_report(agent_flow_report)
