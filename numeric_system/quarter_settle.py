# -*- coding: utf-8 -*-
"""诏书解析 + 合并 effects + 季度结算，供 CLI 与 HTTP 共用。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .edict_parser import parse_edict_to_effects
from .policy_pipeline import policy_candidate_mode_from_env, run_policy_candidate_pipeline
from scenario_system.song_locations import is_song_scenario
from task_system.delegation_hint import compute_delegation_hint
from task_system.edict_narrative import build_decree_narrative_pack

from .executor_modifiers import build_edict_executor_context
from .effects import (
    effects_from_debate_choice,
    effects_from_minister_advice,
    merge_effect_lists,
)
from .engine import QuarterEngine
from .loader import load_numeric_data
from .metric_schema import (
    clamp_effect_delta,
    maybe_autoscale_resource_delta,
    summarize_metric_schema,
)


def _normalize_effect_pool(
    effects: List[Dict[str, Any]],
    *,
    auto_scale_small_resource: bool = False,
) -> Dict[str, Any]:
    normalized: List[Dict[str, Any]] = []
    adjustments: List[Dict[str, Any]] = []
    dropped_count = 0
    for idx, e in enumerate(effects or []):
        if str(e.get("action", "")).strip() != "add_metric":
            normalized.append(e)
            continue
        key = str(e.get("key", "")).strip()
        if not key:
            dropped_count += 1
            adjustments.append({"index": idx, "type": "drop_empty_key"})
            continue
        try:
            value = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            dropped_count += 1
            adjustments.append({"index": idx, "type": "drop_bad_value", "key": key})
            continue
        value, warn_scale = maybe_autoscale_resource_delta(
            key,
            value,
            auto_scale_small_resource=auto_scale_small_resource,
        )
        if warn_scale:
            adjustments.append({"index": idx, **warn_scale})
        value, warn_clamp = clamp_effect_delta(key, value)
        if warn_clamp:
            adjustments.append({"index": idx, **warn_clamp})
        normalized.append({"action": "add_metric", "key": key, "value": round(value, 2)})
    return {
        "effects": normalized,
        "trace": {
            "adjustments": adjustments,
            "dropped_count": dropped_count,
            "auto_scale_small_resource": bool(auto_scale_small_resource),
            "metric_schema": summarize_metric_schema(),
        },
    }


WEAK_DELEGATION_EDICT_EFFECTS: List[Dict[str, Any]] = [
    {"action": "add_metric", "key": "treasury_balance", "value": -12000},
    {"action": "add_metric", "key": "fiscal_pressure", "value": 0.25},
]


def run_quarter_settle(
    root_dir: str,
    *,
    game_session_id: str = "",
    edict_text: str = "",
    edict_category: str = "other",
    quarters: int = 1,
    enable_layer3_llm: bool = True,
    debate_choice: str = "",
    event_effects_json: str = "",
    minister_name: str = "",
    minister_advice_text: str = "",
    edict_executor_name: str = "",
    edict_executor_abilities: Optional[Dict[str, Any]] = None,
    threshold_l1: float = 0.75,
    threshold_l2: float = 0.78,
    use_legacy_category_multiplier: bool = False,
    auto_scale_small_resource: bool = False,
    initial_metrics: Optional[Dict[str, Any]] = None,
    initial_flags: Optional[Dict[str, Any]] = None,
    initial_region_status: Optional[Dict[str, Any]] = None,
    initial_quarter_index: Optional[int] = None,
    policy_candidate_mode: Optional[str] = None,
    selected_candidate_id: str = "",
    session_id: str = "",
    data_root_for_campaign: str = "",
) -> Dict[str, Any]:
    data = load_numeric_data(root_dir)
    engine = QuarterEngine(data)
    state = engine.init_state()

    if initial_metrics:
        state.metrics.update(dict(initial_metrics))
    if initial_flags:
        state.flags.update(dict(initial_flags))
    if initial_region_status:
        state.region_status = {str(k): dict(v) for k, v in dict(initial_region_status).items()}
    if initial_quarter_index is not None:
        state.quarter_index = int(initial_quarter_index)

    executor_ctx = None
    if (edict_executor_name or "").strip() or (edict_executor_abilities or {}):
        executor_ctx = build_edict_executor_context(
            data.ministers,
            executor_name=edict_executor_name,
            abilities_override=edict_executor_abilities,
        )

    edict_parse = parse_edict_to_effects(
        edict_text,
        edict_category=edict_category,
        root_dir=root_dir,
        enable_layer3_llm=enable_layer3_llm,
        threshold_l1=threshold_l1,
        threshold_l2=threshold_l2,
        use_legacy_category_multiplier=use_legacy_category_multiplier,
        executor_context=executor_ctx,
    )
    pcm = (policy_candidate_mode or "").strip().lower() or policy_candidate_mode_from_env()
    if pcm == "parse_only":
        pcm = "shadow"
    parse_trace = edict_parse.get("trace") or {}
    legacy_edict_effects = edict_parse.get("effects", []) or []
    nlu_separated = bool(
        parse_trace.get("parser_mode_separated")
        or parse_trace.get("final_layer") == "nlu_separated"
    )
    policy_candidate_trace: Optional[Dict[str, Any]] = None
    edict_effects: List[Dict[str, Any]] = [] if nlu_separated else list(legacy_edict_effects)
    if pcm != "off":
        sm = {k: float(v) for k, v in dict(state.metrics).items() if isinstance(v, (int, float))}
        try:
            _frame, resolved, _sel, _rej, policy_candidate_trace = run_policy_candidate_pipeline(
                edict_text=edict_text,
                parse_trace=edict_parse.get("trace") or {},
                numeric_data=data,
                state_metrics=sm,
                legacy_effects=legacy_edict_effects,
                mode="select" if pcm == "select" else "shadow",
                selected_candidate_id=selected_candidate_id or "",
            )
        except Exception as exc:  # noqa: BLE001 — 管线失败时回退旧路径
            policy_candidate_trace = {
                "policy_candidate_mode": pcm,
                "error": str(exc),
                "select_applied": False,
            }
            resolved = []
        if pcm == "select" and policy_candidate_trace and not policy_candidate_trace.get("error") and resolved:
            edict_effects = list(resolved)
            policy_candidate_trace["select_applied"] = True
        elif policy_candidate_trace is not None and isinstance(policy_candidate_trace, dict):
            policy_candidate_trace.setdefault("select_applied", False)

    sm = {k: float(v) for k, v in dict(state.metrics).items() if isinstance(v, (int, float))}
    frame_trace: Dict[str, Any] = {}
    resolved_pack: Dict[str, Any] = {}
    task_path = ""
    final_frame = None
    try:
        from edict_execution_frame.pipeline import run_edict_frame_pipeline

        final_frame, frame_resolved, frame_trace, frame_applied = run_edict_frame_pipeline(
            edict_text=edict_text,
            edict_parse=edict_parse,
            numeric_data=data,
            state_metrics=sm,
            edict_executor_name=edict_executor_name or "",
        )
        resolved_pack = dict(frame_trace.get("resolved_pack") or {})
        task_path = str(resolved_pack.get("task_path") or "")
        if (resolved_pack.get("resolution_status") or "") == "needs_clarification":
            edict_effects = []
        elif frame_resolved and (
            frame_applied or (resolved_pack.get("resolution_status") or "") == "partial"
        ):
            edict_effects = list(frame_resolved)
    except Exception as exc:  # noqa: BLE001
        frame_trace = {"error": str(exc), "select_applied": False}

    delegation_hint = compute_delegation_hint(
        edict_text=edict_text, parse_trace=edict_parse.get("trace") or {}
    )
    if task_path == "legacy_delegation_only" and final_frame is not None:
        exn = (final_frame.executor.person_name or "").strip()
        if not exn and final_frame.executor.display_name_zh:
            exn = str(final_frame.executor.display_name_zh).strip()
        if exn:
            from task_system.delegation_hint import default_phases_total

            delegation_hint = {
                "mode": "named_delegation",
                "action_id": "anti_corruption",
                "executor_name": exn,
                "l3_intent": "strict_governance",
                "phases_total": max(
                    1,
                    min(5, int(getattr(final_frame.duration, "quarters", None) or default_phases_total())),
                ),
                "task_key": (final_frame.task.task_key or "strict_local_probe"),
            }
    if task_path in (
        "multi_quarter_delegated_edict_execution",
        "multi_quarter_edict_execution",
    ):
        delegation_hint = None
    elif (
        delegation_hint
        and delegation_hint.get("mode") == "named_delegation"
        and task_path != "legacy_delegation_only"
        and not task_path
    ):
        edict_effects = list(WEAK_DELEGATION_EDICT_EFFECTS)
    debate_effects = effects_from_debate_choice(debate_choice)

    event_effects: List[Dict[str, Any]] = []
    if (event_effects_json or "").strip():
        try:
            loaded = json.loads(event_effects_json)
            if isinstance(loaded, list):
                event_effects = loaded
        except json.JSONDecodeError:
            event_effects = []

    minister_effects: List[Dict[str, Any]] = []
    if (minister_name or "").strip() and (minister_advice_text or "").strip():
        hit = None
        for m in data.ministers:
            if m.name == minister_name.strip():
                hit = m
                break
        if hit is not None:
            minister_effects = effects_from_minister_advice(
                {
                    "name": hit.name,
                    "influence": hit.influence,
                    "stance": hit.stance,
                    "party": hit.party,
                },
                minister_advice_text,
            )

    merged_pool = merge_effect_lists(edict_effects, debate_effects, minister_effects, event_effects)
    normalized_pack = _normalize_effect_pool(
        merged_pool,
        auto_scale_small_resource=auto_scale_small_resource,
    )
    effect_pool = normalized_pack["effects"]

    # AgentFlow workflow call moved here (stage 1) so proposals can feed effect_pool before settle
    secondary_effects_report: Dict[str, Any] = {}
    war_arcs_snap: Dict[str, Any] = {}
    if (edict_text or "").strip() and final_frame is not None:
        try:
            from agent_flow.action_selector import (
                collect_edict_action_candidates,
                select_agent_a_actions,
            )

            exec_ctx_for_agent = dict((frame_trace or {}).get("execution_context") or {})
            candidates = collect_edict_action_candidates(
                exec_ctx_for_agent,
                resolved_pack,
                final_frame,
            )
            selected_tasks, agent_sel_trace = select_agent_a_actions(candidates)

            if selected_tasks:
                from agent_flow.service import run_secondary_effects_flow

                region_map_view: List[Dict[str, Any]] = []
                try:
                    from scenario_system.song_locations import build_region_map_view

                    region_map_view = build_region_map_view(state)
                except Exception:
                    pass
                sid = (session_id or "").strip()
                if sid and is_song_scenario(data_root=root_dir):
                    try:
                        from task_system.war_arc import war_arcs_snapshot

                        war_arcs_snap = war_arcs_snapshot(sid)
                    except Exception:
                        war_arcs_snap = {}

                first = selected_tasks[0]
                exec_ctx_for_agent["primary_task"] = {
                    "domain": str(first.get("domain") or ""),
                    "task_key": str(first.get("task_key") or ""),
                }
                exec_ctx_for_agent["agent_a_selected_tasks"] = list(selected_tasks)
                exec_ctx_for_agent["agent_a_selection"] = dict(agent_sel_trace)
                if isinstance(frame_trace, dict):
                    frame_trace["execution_context"] = exec_ctx_for_agent

                sec = run_secondary_effects_flow(
                    session_id=sid,
                    quarter_index=int(getattr(state, "quarter_index", 0) or 0),
                    edict_text=edict_text,
                    execution_context=exec_ctx_for_agent,
                    resolved_pack=dict(resolved_pack or {}),
                    metrics=dict(state.metrics),
                    flags=dict(state.flags),
                    game_session_id=(game_session_id or "").strip(),
                    region_status=dict(getattr(state, "region_status", {}) or {}),
                    region_map_view=region_map_view,
                    war_arcs=war_arcs_snap,
                    selected_tasks=selected_tasks,
                )
                secondary_effects_report = dict(sec or {})
            elif candidates:
                secondary_effects_report = {
                    "skipped": True,
                    "trace": {
                        "skipped": True,
                        "reason": "other_only_segments",
                        "agent_a_selection": agent_sel_trace,
                    },
                }
        except ImportError:
            pass

    # Convert agent proposals to effects and merge (guardrail first)
    agent_flow_report = secondary_effects_report if isinstance(secondary_effects_report, dict) else {}
    if agent_flow_report.get("proposals"):
        try:
            from agent_flow.proposals_io import proposals_to_effects
            from numeric_system.safety_guardrail import apply_safety_guardrail

            pt = dict((frame_trace or {}).get("execution_context") or {}).get("primary_task") or {}
            selected_for_prop = list(
                dict((frame_trace or {}).get("execution_context") or {}).get("agent_a_selected_tasks") or []
            )
            if selected_for_prop:
                prop_dom = str(selected_for_prop[0].get("domain") or "").strip()
            else:
                prop_dom = str(
                    pt.get("domain")
                    or getattr(getattr(final_frame, "task", None), "domain", "")
                    or ""
                ).strip()
            extra, prop_trace = proposals_to_effects(
                dict(agent_flow_report.get("proposals") or {}),
                domain=prop_dom,
                quarter_index=int(getattr(state, "quarter_index", 0) or 0),
                flags=dict(state.flags),
                war_arcs=war_arcs_snap,
            )
            safe_extra, guard_trace = apply_safety_guardrail(extra)
            effect_pool = list(effect_pool) + safe_extra
            agent_flow_report.setdefault("trace", {})
            if isinstance(agent_flow_report["trace"], dict):
                agent_flow_report["trace"]["proposals_apply"] = prop_trace
                agent_flow_report["trace"]["guardrail"] = guard_trace
        except Exception:
            pass

    reports: List[Dict[str, Any]] = []
    for _ in range(max(1, int(quarters))):
        report = engine.settle_quarter(state, effects=effect_pool)
        report["effects_preview"] = effect_pool
        reports.append(report)

    trace_in = edict_parse.get("trace") or {}
    ex_ctx = trace_in.get("executor_context") or {}
    if not isinstance(ex_ctx, dict):
        ex_ctx = {}
    hint_mode = (delegation_hint or {}).get("mode") or "none"
    if not delegation_hint:
        hint_mode = "none"
    decree_narrative = build_decree_narrative_pack(
        mode=str(hint_mode),
        action_id=str((delegation_hint or {}).get("action_id") or "anti_corruption"),
        executor_name=str((delegation_hint or {}).get("executor_name") or "").strip()
        or str(ex_ctx.get("name") or ""),
        abilities_zh=str(ex_ctx.get("abilities_zh") or ""),
        stance=str(ex_ctx.get("stance") or ""),
        party=str(ex_ctx.get("party") or ""),
        edict_category_zh=str(trace_in.get("edict_category_label_zh") or ""),
        edict_text=edict_text,
        named_enqueued=False,
    )

    edict_execution_input = {
        "final_frame": frame_trace.get("final_frame"),
        "final_frame_narrative": frame_trace.get("final_frame_narrative") or "",
        "resolved_pack": resolved_pack,
        "select_applied": bool(frame_trace.get("select_applied")),
        "task_path": task_path,
        "execution_context": frame_trace.get("execution_context") or {},
    }

    if is_song_scenario(data_root=root_dir):
        try:
            from task_system.song_minister_delegation import load_catalog

            load_catalog(ministers=data.ministers)
        except ImportError:
            pass

    return {
        "input": {
            "root_dir": root_dir,
            "edict_text": edict_text,
            "edict_category": edict_category,
            "enable_layer3_llm": bool(enable_layer3_llm),
            "edict_parse_trace": edict_parse.get("trace", {}),
            "debate_choice": debate_choice,
            "minister_name": minister_name,
            "minister_advice_text": minister_advice_text,
            "edict_executor_name": edict_executor_name,
            "edict_executor_abilities": dict(edict_executor_abilities or {}),
            "edict_executor_resolution": (edict_parse.get("trace") or {}).get(
                "executor_resolution"
            ),
            "delegation_hint": delegation_hint,
            "decree_narrative": decree_narrative,
            "event_effects_count": len(event_effects),
            "effect_normalization_trace": normalized_pack["trace"],
            "policy_candidate_trace": policy_candidate_trace,
            "edict_execution": edict_execution_input,
            "edict_execution_frame": frame_trace,
            "edict_frame_normalized_zh": frame_trace.get("final_frame_narrative") or "",
            "secondary_effects_report": secondary_effects_report,
        },
        "reports": reports,
        "final_state": {
            "quarter_index": state.quarter_index,
            "metrics": dict(state.metrics),
            "flags": dict(state.flags),
        },
    }

