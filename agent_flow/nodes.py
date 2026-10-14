# -*- coding: utf-8 -*-
"""LangGraph 节点：DST 更新 → 次生信号 → 机构化推演 → 他人回应草案。"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # type: ignore

from agent_flow.dst import apply_action_dst
from agent_flow.repository import ActionFlowRepository
from agent_flow.schemas import (
    ActionFlowState,
    ActionRef,
    ActorResponseSketch,
    SecondaryEffectsReport,
    SecondaryPressure,
    SystemAction,
    UserAction,
)


class SecondaryEffectsGraphState(TypedDict, total=False):
    session_id: str
    quarter_index: int
    edict_text: str
    execution_context: Dict[str, Any]
    resolved_pack: Dict[str, Any]
    metrics: Dict[str, Any]
    flags: Dict[str, Any]
    task_state: List[Dict[str, Any]]
    policy_nodes: List[Dict[str, Any]]
    action_flow_state: Dict[str, Any]
    report: Dict[str, Any]
    storage_backend: str
    error: str


def _primary_action_from_pack(
    *,
    edict_text: str,
    execution_context: Dict[str, Any],
    resolved_pack: Dict[str, Any],
) -> ActionRef:
    pt = dict(execution_context.get("primary_task") or {})
    meta = dict(resolved_pack.get("resolve_meta") or {})
    ff = dict(resolved_pack.get("final_frame") or {})
    task = dict(ff.get("task") or {})
    return ActionRef(
        action_kind="edict",
        domain=str(pt.get("domain") or task.get("domain") or ""),
        task_key=str(pt.get("task_key") or task.get("task_key") or ""),
        edict_text=(edict_text or "").strip(),
        frame_id=str(ff.get("frame_id") or ""),
        resolution_status=str(ff.get("resolution_status") or ""),
        primary_task={
            "domain": str(pt.get("domain") or ""),
            "task_key": str(pt.get("task_key") or ""),
        },
    )


def dst_update_node(state: SecondaryEffectsGraphState) -> SecondaryEffectsGraphState:
    sid = str(state.get("session_id") or "anonymous").strip()
    q = int(state.get("quarter_index") or 0)
    repo = ActionFlowRepository()
    existing = repo.get_state(sid)
    base = existing or ActionFlowState(session_id=sid, quarter_index=q)
    base.quarter_index = q
    base.metrics = dict(state.get("metrics") or {})
    base.flags = dict(state.get("flags") or {})
    base.task_state = list(state.get("task_state") or [])
    exec_ctx = dict(state.get("execution_context") or {})
    resolved = dict(state.get("resolved_pack") or {})
    primary = _primary_action_from_pack(
        edict_text=str(state.get("edict_text") or ""),
        execution_context=exec_ctx,
        resolved_pack=resolved,
    )
    user_action = UserAction(
        channel="edict",
        raw_text=str(state.get("edict_text") or ""),
        metadata={"primary_task": primary.primary_task},
    )
    sys_action = SystemAction(
        action_type="resolve_edict",
        summary_zh=str(resolved.get("task_path") or ""),
        task_path=str(resolved.get("task_path") or ""),
        metadata={"resolve_meta": dict(resolved.get("resolve_meta") or {})},
    )
    flow = apply_action_dst(
        base,
        user_action=user_action,
        system_action=sys_action,
        primary_action=primary,
    )
    repo.save_state(flow)
    return {
        **state,
        "action_flow_state": flow.model_dump(mode="json"),
        "storage_backend": repo.backend,
    }


def analyze_secondary_node(state: SecondaryEffectsGraphState) -> SecondaryEffectsGraphState:
    exec_ctx = dict(state.get("execution_context") or {})
    secondary = list(exec_ctx.get("secondary_signals") or [])
    flow_raw = dict(state.get("action_flow_state") or {})
    primary_raw = dict(flow_raw.get("last_primary_action") or {})
    primary = ActionRef.model_validate(primary_raw) if primary_raw else ActionRef()
    pressures: List[SecondaryPressure] = []
    actors: List[ActorResponseSketch] = []
    seeds: List[Dict[str, Any]] = []
    narrative_parts: List[str] = []

    dom = primary.domain or ""
    if "anti_corruption" in secondary:
        pressures.append(
            SecondaryPressure(
                key="local_audit_backlash",
                label_zh="地方清查反弹",
                magnitude="medium",
                narrative_zh="严察贪墨或激起胥吏怠政，须防阳奉阴违。",
            )
        )
        actors.append(
            ActorResponseSketch(
                actor_id="old_party",
                actor_label_zh="守旧诸公",
                stance="critical",
                response_zh="或上疏称苛察伤吏，求宽限施行。",
                pressure_tags=["court_resistance"],
            )
        )
    if "disaster_relief" in secondary or dom == "disaster_relief":
        pressures.append(
            SecondaryPressure(
                key="relief_leakage",
                label_zh="赈济渗漏",
                magnitude="medium",
                narrative_zh="赈粮转运途中恐有克扣，民心未稳。",
            )
        )
    if dom == "personnel":
        actors.append(
            ActorResponseSketch(
                actor_id="court_factions",
                actor_label_zh="朝中诸派",
                stance="watchful",
                response_zh="人事异动既起，各派或暗中串联，观望新命得失。",
                pressure_tags=["faction_friction"],
            )
        )
    if secondary:
        narrative_parts.append("诏令主域之外，尚有「%s」之次生波次。" % "、".join(secondary))
    if pressures:
        narrative_parts.append("机构承压：%s。" % "；".join(p.label_zh for p in pressures[:3]))

    meta = dict((state.get("resolved_pack") or {}).get("resolve_meta") or {})
    for s in list(meta.get("delayed_risk_seeds") or []):
        if isinstance(s, dict):
            seeds.append(dict(s))

    report = SecondaryEffectsReport(
        session_id=str(state.get("session_id") or ""),
        quarter_index=int(state.get("quarter_index") or 0),
        primary_action=primary,
        secondary_signals=secondary,
        secondary_pressures=pressures,
        actor_responses=actors,
        delayed_risk_seeds=seeds,
        narrative_seed_zh="".join(narrative_parts),
        trace={
            "multi_intent_policy": exec_ctx.get("multi_intent_policy"),
            "node": "analyze_secondary",
        },
    )
    return {**state, "report": report.model_dump(mode="json")}


def persist_node(state: SecondaryEffectsGraphState) -> SecondaryEffectsGraphState:
    raw = dict(state.get("report") or {})
    if not raw:
        return state
    report = SecondaryEffectsReport.model_validate(raw)
    ActionFlowRepository().save_run(report)
    return state
