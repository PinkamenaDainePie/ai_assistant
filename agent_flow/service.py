# -*- coding: utf-8 -*-
"""动作次生影响 agent-flow 入口（不接 renwu_module 大臣对话）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_flow.adp_client import AdpClientError, adp_agent_flow_enabled, call_agent_flow_sse
from agent_flow.config import AGENT_FLOW_USE_LANGGRAPH
from agent_flow.graph import get_secondary_effects_graph, langgraph_available
from agent_flow.nodes import analyze_secondary_node, dst_update_node, persist_node
from agent_flow.schemas import ActionRef, SecondaryEffectsReport


def _run_local_secondary_effects(payload: Dict[str, Any]) -> Dict[str, Any]:
    if AGENT_FLOW_USE_LANGGRAPH and langgraph_available():
        out = get_secondary_effects_graph().invoke(payload)
        raw = dict(out.get("report") or {})
        if raw:
            return SecondaryEffectsReport.model_validate(raw).model_dump(mode="json")
        return SecondaryEffectsReport(
            session_id=str(payload.get("session_id") or ""),
            quarter_index=int(payload.get("quarter_index") or 0),
        ).model_dump(mode="json")

    s1 = dst_update_node(payload)
    s2 = analyze_secondary_node(s1)
    persist_node(s2)
    raw = dict(s2.get("report") or {})
    if raw:
        return SecondaryEffectsReport.model_validate(raw).model_dump(mode="json")
    return SecondaryEffectsReport(
        session_id=str(payload.get("session_id") or ""),
        quarter_index=int(payload.get("quarter_index") or 0),
    ).model_dump(mode="json")


def _resolve_selected_tasks(
    *,
    execution_context: Optional[Dict[str, Any]],
    resolved_pack: Optional[Dict[str, Any]],
    selected_tasks: Optional[List[Dict[str, Any]]],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    exec_ctx = dict(execution_context or {})
    if selected_tasks is not None:
        rows = [dict(r) for r in selected_tasks if isinstance(r, dict)]
        sel_trace = dict(exec_ctx.get("agent_a_selection") or {})
        if not sel_trace and rows:
            sel_trace = {"selection_mode": "explicit_selected_tasks", "selected": rows}
        return rows, sel_trace

    from agent_flow.action_selector import collect_edict_action_candidates, select_agent_a_actions

    candidates = collect_edict_action_candidates(exec_ctx, dict(resolved_pack or {}), None)
    return select_agent_a_actions(candidates)


def run_secondary_effects_flow(
    *,
    session_id: str,
    quarter_index: int,
    edict_text: str = "",
    execution_context: Optional[Dict[str, Any]] = None,
    resolved_pack: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    flags: Optional[Dict[str, Any]] = None,
    task_state: Optional[List[Dict[str, Any]]] = None,
    policy_nodes: Optional[List[Dict[str, Any]]] = None,
    game_session_id: str = "",
    region_status: Optional[Dict[str, Any]] = None,
    region_map_view: Optional[List[Dict[str, Any]]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
    selected_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    在诏书/动作已裁决之后运行：推演次生影响与他人回应草案。
    产出 AgentFlowReport dict（或 skip trace），不直接修改 WorldState。
    配置了 AGENT_FLOW_BOT_APP_KEY 时走腾讯云 ADP Workflow A；否则本地 stub。
    """
    exec_ctx = dict(execution_context or {})
    resolved = dict(resolved_pack or {})

    selected, sel_trace = _resolve_selected_tasks(
        execution_context=exec_ctx,
        resolved_pack=resolved,
        selected_tasks=selected_tasks,
    )
    if not selected:
        return SecondaryEffectsReport(
            session_id=(session_id or "anonymous").strip(),
            quarter_index=int(quarter_index),
            trace={
                "skipped": True,
                "reason": "no_contest_counter_actions",
                "agent_a_selection": sel_trace,
            },
        ).model_dump(mode="json")

    first = selected[0]
    dom = str(first.get("domain") or "").strip()
    tk = str(first.get("task_key") or "").strip()
    exec_ctx["primary_task"] = {"domain": dom, "task_key": tk}
    exec_ctx["agent_a_selected_tasks"] = list(selected)
    exec_ctx["agent_a_selection"] = dict(sel_trace)

    payload: Dict[str, Any] = {
        "game_session_id": (game_session_id or "").strip(),
        "session_id": (session_id or "anonymous").strip(),
        "quarter_index": int(quarter_index),
        "edict_text": edict_text or "",
        "execution_context": exec_ctx,
        "resolved_pack": resolved,
        "metrics": dict(metrics or {}),
        "flags": dict(flags or {}),
        "task_state": list(task_state or []),
        "policy_nodes": list(policy_nodes or []),
        "agent_a_selected_tasks": list(selected),
    }
    try:
        from agent_flow.proposals_io import enrich_workflow_a_payload

        payload = enrich_workflow_a_payload(
            payload,
            region_status=region_status,
            region_map_view=region_map_view,
            war_arcs=war_arcs,
        )
    except ImportError:
        pass

    if adp_agent_flow_enabled():
        try:
            report = call_agent_flow_sse(
                payload=payload,
                game_session_id=(game_session_id or "").strip(),
                session_id=(session_id or "anonymous").strip(),
            )
            trace = dict(report.get("trace") or {})
            trace["agent_a_selection"] = sel_trace
            report["trace"] = trace
            report.setdefault(
                "primary_action",
                ActionRef(domain=dom, task_key=tk, edict_text=edict_text or "").model_dump(mode="json"),
            )
            return report
        except AdpClientError as exc:
            local = _run_local_secondary_effects(payload)
            trace = dict(local.get("trace") or {})
            trace.update({"adp_error": str(exc), "adp_fallback": True, "agent_a_selection": sel_trace})
            local["trace"] = trace
            return local

    local = _run_local_secondary_effects(payload)
    trace = dict(local.get("trace") or {})
    trace["agent_a_selection"] = sel_trace
    local["trace"] = trace
    return local
