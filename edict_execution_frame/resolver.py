# -*- coding: utf-8 -*-
"""EdictExecutionFrame → effects + 可选跨季任务占位 dict。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.domain_outcomes import build_domain_outcome_meta
from edict_execution_frame.domain_catalog import normalize_effect_profile_keys
from edict_execution_frame.disaster_outcomes import build_disaster_outcome_meta
from edict_execution_frame.location_effect_merge import (
    apply_difficulty_scale_to_effects,
    apply_location_modifier_to_resolution_pipeline,
)
from edict_execution_frame.regional_effects import apply_regional_scope_to_effects
from edict_execution_frame.resolution_thresholds import DELEGATED_MIN_TASK_CONFIDENCE
from edict_execution_frame.schemas import EdictExecutionFrame
from numeric_system.candidate_resolver import resolve_candidate_to_effects
from numeric_system.policy_ir import PolicyActionCandidate
from numeric_system.safety_guardrail import apply_safety_guardrail
from numeric_system.types import NumericData

_MULTI_QUARTER_WEAK_SCALE = 0.42


def _personnel_appointee_zh(
    frame: EdictExecutionFrame, ministers: Optional[Any]
) -> Tuple[str, str]:
    """叙事用：具名臣僚与表内官职（不修改 roster）。"""
    ex = frame.executor
    name = ""
    if (ex.mode or "") in ("person", "dual_person"):
        name = (ex.person_name or "").strip()
        if not name and ex.person_names:
            name = str(ex.person_names[0] or "").strip()
    if not name:
        return "", ""
    office = ""
    for m in ministers or []:
        if str(getattr(m, "name", "") or "").strip() == name:
            office = str(getattr(m, "office", "") or "").strip()
            break
    return name, office


def _location_trace_for_resolve_meta(frame: EdictExecutionFrame) -> Dict[str, Any]:
    tm = frame.task_meta or {}
    return {
        "location": frame.location.model_dump(),
        "target_entity": frame.target_entity.model_dump(),
        "location_modifier_applied": dict(tm.get("location_modifier_applied") or {}),
        "location_resolution": dict(tm.get("location_resolution") or {}),
    }


def should_create_delegated_edict_task(frame: EdictExecutionFrame) -> Tuple[bool, List[str]]:
    """具名人物承办 + 可入队的多季 edict_execution（含肃贪，与赈济等同路径）。"""
    reasons: List[str] = []
    if frame is None:
        return False, ["missing_frame"]
    if (frame.resolution_status or "") == "needs_clarification":
        return False, ["needs_clarification"]
    dom = (frame.task.domain or "").strip()
    if not dom or dom == "unknown":
        return False, ["unknown_domain"]
    if not (frame.task.task_key or "").strip():
        return False, ["missing_task_key"]
    tconf = float(getattr(frame, "task_confidence", 1.0) or 0.0)
    if tconf < DELEGATED_MIN_TASK_CONFIDENCE:
        reasons.append("low_task_confidence")
        return False, reasons
    meta = frame.task_meta or {}
    if meta.get("delegate_allowed") is False:
        return False, ["delegate_not_allowed"]
    ex_mode = getattr(frame.executor, "mode", None)
    if ex_mode not in ("person", "dual_person"):
        return False, ["not_named_delegation"]
    q = int(getattr(frame.duration, "quarters", None) or 0)
    if not q:
        return False, ["missing_duration"]
    if q <= 1:
        return False, ["single_quarter_no_task_needed"]
    return True, []


def frame_to_policy_candidate(frame: EdictExecutionFrame) -> PolicyActionCandidate:
    meta = frame.metadata or {}
    action_type = str(meta.get("action_type") or "").strip()
    if not action_type:
        action_type = "named_execution" if frame.executor.mode in ("person", "dual_person") else "default_machine"
    cid = (frame.frame_id or "edict_frame").strip() or "edict_frame"
    ex_mode = "single" if frame.executor.mode in ("person", "dual_person") else "default_officials"
    ex_name = ""
    if frame.executor.mode == "person":
        ex_name = frame.executor.person_name or ""
    elif frame.executor.mode == "dual_person" and frame.executor.person_names:
        ex_name = frame.executor.person_names[0]
    return PolicyActionCandidate(
        candidate_id=cid,
        source="edict",
        domain=frame.task.domain or "general",
        action_type=action_type,
        title_zh=frame.task.title_zh or "政务",
        summary_zh=frame.normalized_command_zh or "",
        executor=ex_name,
        executor_mode=ex_mode,
        intensity=str(frame.intensity or "medium"),
        policy_style="moderate",
        target_metrics=list((frame.expected_effect_profile or {}).keys()),
        expected_effect_profile=normalize_effect_profile_keys(frame.expected_effect_profile or {}),
        risk_tags=list(frame.risk_tags or []),
    )


def _scale_add_metric_effects(effects: List[Dict[str, Any]], factor: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in effects or []:
        if not isinstance(e, dict):
            continue
        action = str(e.get("action") or "").strip()
        if action not in ("add_metric", "add_regional_metric"):
            out.append(dict(e))
            continue
        try:
            v = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            v = 0.0
        out.append({**e, "value": round(v * factor, 2)})
    safe, _g = apply_safety_guardrail(out)
    return safe


def _base_preview_fields(frame: EdictExecutionFrame) -> Dict[str, Any]:
    meta = frame.task_meta or {}
    return {
        "kind": "edict_execution",
        "frame_id": frame.frame_id,
        "domain": frame.task.domain,
        "task_key": frame.task.task_key,
        "title_zh": frame.task.title_zh,
        "display_executor_zh": frame.executor.display_name_zh,
        "normalized_command_zh": frame.normalized_command_zh,
        "phases_total": int(frame.duration.quarters or 1),
        "risk_tags": list(frame.risk_tags or []),
        "expected_effect_profile": normalize_effect_profile_keys(frame.expected_effect_profile or {}),
        "intensity": str(frame.intensity or "medium"),
        "task_confidence": float(getattr(frame, "task_confidence", 0.55) or 0.0),
        "explicitness": frame.explicitness_class,
        "is_auto_completed": bool(frame.is_auto_completed),
        "completion_notes_zh": frame.completion_notes_zh or "",
        "ability_weights_minister": dict(meta.get("ability_weights_minister") or {}),
        "narrative_mode": str(meta.get("narrative_mode") or "delegated_execution"),
        "delegate_route": str(meta.get("delegate_route") or "mixed"),
        "playbook_variant": str(meta.get("playbook_variant") or ""),
        "playbook_variant_label_zh": str(meta.get("playbook_variant_label_zh") or ""),
        "effect_scope": dict(meta.get("effect_scope") or {}),
        "scope_confidence": str(meta.get("scope_confidence") or ""),
        "engineering_subtype": str(meta.get("engineering_subtype") or ""),
        "order_subtype": str(meta.get("order_subtype") or ""),
        "location_difficulty_delta": int(
            (meta.get("location_modifier_applied") or {}).get("difficulty_delta") or 0
        ),
    }


def build_institutional_edict_execution_preview(frame: EdictExecutionFrame) -> Dict[str, Any]:
    prev = _base_preview_fields(frame)
    prev.update(
        {
            "is_delegated": False,
            "execution_mode": "institutional",
            "executor": "",
            "executors": [],
        }
    )
    return prev


def build_delegated_edict_execution_preview(frame: EdictExecutionFrame) -> Dict[str, Any]:
    prev = _base_preview_fields(frame)
    ex = frame.executor
    if ex.mode == "dual_person" and ex.person_names:
        mode = "delegated_dual"
        names = list(ex.person_names)
        primary = names[0] if names else ""
    else:
        mode = "delegated_person"
        primary = (ex.person_name or "").strip()
        names = [primary] if primary else []
    prev.update(
        {
            "is_delegated": True,
            "execution_mode": mode,
            "executor": primary,
            "executors": names,
        }
    )
    return prev


def resolve_frame_to_effects_and_tasks(
    frame: EdictExecutionFrame,
    *,
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
) -> Dict[str, Any]:
    narrative = frame.normalized_command_zh or ""
    event_seeds: List[Dict[str, Any]] = []

    def _pack(
        *,
        task_path: str,
        current_effects: List[Dict[str, Any]],
        created_tasks: List[Dict[str, Any]],
        resolve_meta: Dict[str, Any],
        delegation_blocked_reasons: List[str] | None = None,
        delegation_mode: str = "",
    ) -> Dict[str, Any]:
        rm = dict(resolve_meta or {})
        rm.update(_location_trace_for_resolve_meta(frame))
        return {
            "current_effects": current_effects,
            "created_tasks": created_tasks,
            "narrative": narrative,
            "event_seeds": event_seeds,
            "resolve_meta": {**rm, "task_path": task_path},
            "task_path": task_path,
            "resolution_status": getattr(frame, "resolution_status", "resolved") or "resolved",
            "ambiguity_status": getattr(frame, "ambiguity_status", "none") or "none",
            "clarification_options": list(getattr(frame, "clarification_options", None) or []),
            "delegation_blocked_reasons": list(delegation_blocked_reasons or []),
            "delegation_mode": delegation_mode,
        }

    if (frame.resolution_status or "") == "needs_clarification":
        return _pack(
            task_path="ambiguous_needs_clarification",
            current_effects=[],
            created_tasks=[],
            resolve_meta={"reason": "needs_clarification"},
        )

    cand = frame_to_policy_candidate(frame)
    tm = frame.task_meta or {}
    loc_mod = dict(tm.get("location_modifier_applied") or {})
    aff = bool(getattr(frame.location, "affects_numbers", False))
    merged_prof, loc_scale, loc_merge_trace = apply_location_modifier_to_resolution_pipeline(
        base_profile=dict(cand.expected_effect_profile or {}),
        location_modifier_applied=loc_mod,
        affects_numbers=aff,
    )
    cand = cand.model_copy(
        update={
            "expected_effect_profile": merged_prof,
            "target_metrics": list(merged_prof.keys()),
        }
    )
    full_eff, meta = resolve_candidate_to_effects(
        cand,
        numeric_data=numeric_data,
        state_metrics=state_metrics,
    )
    full_eff, diff_scale_trace = apply_difficulty_scale_to_effects(full_eff, loc_scale)
    dom_f = frame.task.domain or ""
    tk_f = frame.task.task_key or ""
    effect_scope = dict(tm.get("effect_scope") or {})
    full_eff, regional_trace = apply_regional_scope_to_effects(
        full_eff,
        effect_scope=effect_scope,
        domain=dom_f,
    )
    meta = {
        **meta,
        "location_effect_merge": loc_merge_trace,
        "location_difficulty_scale_trace": diff_scale_trace,
        "effect_scope": effect_scope,
        "regional_effect_split": regional_trace,
    }
    loc_n = (frame.location.location_name_zh or frame.location.source_text or "").strip()
    te_meta = frame.task_meta or {}
    hostile_zh = str(
        (te_meta.get("target_entity_row") or {}).get("entity_name_zh")
        or getattr(frame.target_entity, "entity_name_zh", "")
        or ""
    ).strip()
    ap_name, ap_office = (
        _personnel_appointee_zh(frame, numeric_data.ministers if numeric_data else None)
        if dom_f == "personnel"
        else ("", "")
    )
    imm, seeds, nar = build_domain_outcome_meta(
        domain=str(dom_f),
        task_key=str(tk_f),
        effects=full_eff,
        location_name_zh=loc_n,
        hostile_name_zh=hostile_zh,
        appointee_name_zh=ap_name,
        appointee_office_zh=ap_office,
    )
    pv = str((frame.task_meta or {}).get("playbook_variant") or "").strip()
    if pv:
        meta["playbook_variant"] = pv
        meta["playbook_variant_label_zh"] = str(
            (frame.task_meta or {}).get("playbook_variant_label_zh") or ""
        ).strip()
    if imm or seeds or nar:
        meta["immediate_outcome"] = imm
        meta["delayed_risk_seeds"] = seeds
        meta["narrative_seed_zh"] = nar
    # 若 outcome 带 status_effect（人事黜罢/赐死），合并进 effects 让 engine 应用状态变更
    se = imm.get("status_effect") if isinstance(imm, dict) else None
    if isinstance(se, dict) and se.get("action") in ("set_minister_status", "set_region_status"):
        full_eff = list(full_eff) + [se]
    q = int(frame.duration.quarters or 1)

    if q <= 1:
        return _pack(
            task_path="single_quarter_effects",
            current_effects=full_eff,
            created_tasks=[],
            resolve_meta=meta,
        )

    weak_eff = _scale_add_metric_effects(full_eff, _MULTI_QUARTER_WEAK_SCALE)

    if (
        bool(getattr(frame, "legacy_eligible", False))
        and q > 1
        and (frame.resolution_status or "") in ("resolved", "auto_completed")
    ):
        return _pack(
            task_path="legacy_delegation_only",
            current_effects=weak_eff,
            created_tasks=[],
            resolve_meta={**meta, "legacy_eligible": True},
            delegation_mode="legacy_single",
        )

    ok_del, blocked = should_create_delegated_edict_task(frame)

    if ok_del and (frame.resolution_status or "") in ("resolved", "auto_completed"):
        prev = build_delegated_edict_execution_preview(frame)
        dm = "delegated_person" if frame.executor.mode == "person" else "delegated_dual"
        return _pack(
            task_path="multi_quarter_delegated_edict_execution",
            current_effects=weak_eff,
            created_tasks=[prev],
            resolve_meta=meta,
            delegation_blocked_reasons=[],
            delegation_mode=dm,
        )

    prev_i = build_institutional_edict_execution_preview(frame)
    return _pack(
        task_path="multi_quarter_edict_execution",
        current_effects=weak_eff,
        created_tasks=[prev_i],
        resolve_meta=meta,
        delegation_blocked_reasons=list(blocked),
        delegation_mode="institutional",
    )
