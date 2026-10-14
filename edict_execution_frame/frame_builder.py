# -*- coding: utf-8 -*-
"""槽位抽取与单帧组装（非 D / D 之前共用）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from edict_execution_frame.admissibility import partition_admissible
from edict_execution_frame.completion_priority import pick_first_admissible
from edict_execution_frame.domain_catalog import (
    effective_ability_weights,
    logical_weights_to_minister_weights,
    normalize_effect_profile_keys,
    resolve_domain_from_semantic_and_text,
    select_task_row_for_domain,
    slug_frame_id,
)
from edict_execution_frame.duration_resolver import (
    bump_duration_for_person_task,
    resolve_duration,
)
from edict_execution_frame.explicitness import duration_explicit_from_text
from edict_execution_frame.provincial_delegate import enhance_executor_for_location_delegate
from edict_execution_frame.executor_resolver import resolve_executor
from edict_execution_frame.explicitness import classify_edict_explicitness, get_l3_intent
from edict_execution_frame.completion_candidates import generate_internal_candidates
from edict_execution_frame.location_slot import apply_location_target_to_frame, merge_risk_tags_from_modifier
from edict_execution_frame.narrative_builder import apply_normalized_line
from edict_execution_frame.resolution_status import ambiguity_label, decide_resolution_status
from edict_execution_frame.schemas import EdictExecutionFrame, TaskSpec
from edict_execution_frame.fiscal_clarification import (
    FISCAL_VAGUE_DEFAULT_CONFIDENCE,
    fiscal_vague_default_row,
    is_fiscal_goal_vague,
)
from edict_execution_frame.task_resolver import (
    TaskResolutionResult,
    build_clarification_options,
    clarification_candidates_diverse,
    rank_rows_for_domain,
    resolve_task_for_domain,
)
from numeric_system.semantic_frame_extract import extract_semantic_frame_from_trace
from numeric_system.types import NumericData

_STRONG_TASK_SIGNAL = re.compile(
    r"(开仓|赈济|赈灾|黄河|堤防|边防|整饬边防|考课|任免|抚驭|朝贡|肃贪|贪墨|反贪|贪腐|严查|彻查|清查|剿匪|劝课|清厘|河工|修缮|农田水利|陂塘|改稻为桑|植桑|春前给散|贷种|备春耕|逋欠|追比|加派|市易|免役|均输|裁冗|榷盐)"
)
_VAGUE_ROUTINE = re.compile(r"(料理地方事务|妥善处置|整顿诸务|诸务|料理.+事务)")
_LEGACY_ELIGIBLE_TASK_KEYS = frozenset({"strict_local_probe"})


def _compute_legacy_eligible(fr: EdictExecutionFrame) -> bool:
    if (fr.task.domain or "").strip() != "anti_corruption":
        return False
    if (fr.task.task_key or "").strip() not in _LEGACY_ELIGIBLE_TASK_KEYS:
        return False
    if (fr.executor.mode or "") != "person":
        return False
    if (fr.resolution_status or "") == "needs_clarification":
        return False
    return True


def _minister_names(data: NumericData) -> Set[str]:
    return {str(getattr(m, "name", "") or "").strip() for m in (data.ministers or []) if getattr(m, "name", None)}


def _domain_confidence(domain: str, edict_text: str, sem_confidence: float, l3_intent: str) -> float:
    from edict_execution_frame.domain_catalog import _INTENT_DOMAIN_HINT

    if _INTENT_DOMAIN_HINT.get((l3_intent or "").strip()) == domain:
        return 0.88
    ranked = rank_rows_for_domain(domain, edict_text)
    top_sc = ranked[0][1] if ranked else 0
    base = float(sem_confidence or 0.55)
    if top_sc >= 6:
        return round(min(0.95, max(base, 0.78)), 3)
    if top_sc >= 3:
        return round(min(0.9, max(base, 0.68)), 3)
    if top_sc > 0:
        return round(min(0.85, max(base, 0.58)), 3)
    return round(max(0.4, base * 0.85), 3)


def enrich_frame_with_resolution(
    fr: EdictExecutionFrame,
    *,
    edict_text: str,
    parse_trace: Dict[str, Any],
    task_row_confidence: Optional[float] = None,
    task_row_fallback: Optional[bool] = None,
) -> EdictExecutionFrame:
    """写入 resolution_status、置信度、澄清项与 task_meta。"""
    text = edict_text or ""
    trace = parse_trace or {}
    fiscal_vague = is_fiscal_goal_vague(text)
    if fiscal_vague:
        dom = "fiscal"
        row_vague = fiscal_vague_default_row()
        tres = TaskResolutionResult(
            domain="fiscal",
            row=row_vague,
            confidence=FISCAL_VAGUE_DEFAULT_CONFIDENCE,
            is_fallback=False,
            candidates=[],
        )
    else:
        dom = fr.task.domain or "general"
        tres = resolve_task_for_domain(dom, text)
    if task_row_confidence is not None:
        tres = TaskResolutionResult(
            domain=tres.domain,
            row=tres.row,
            confidence=float(task_row_confidence),
            is_fallback=bool(task_row_fallback if task_row_fallback is not None else tres.is_fallback),
            candidates=tres.candidates,
        )
    sem = extract_semantic_frame_from_trace(text, trace)
    intent = get_l3_intent(trace)
    dom_conf = _domain_confidence(dom, text, float(sem.confidence or 0.55), intent)
    if fiscal_vague:
        dom_conf = max(float(dom_conf), 0.58)
    ex_def = bool(fr.executor.is_inferred)
    dur_def = bool(fr.duration.is_inferred)
    ex_conf = 0.52 if ex_def else 0.86
    dur_conf = 0.48 if dur_def else 0.88

    ranked = rank_rows_for_domain(dom, text)
    top1_sc = ranked[0][1] if ranked else 0
    second_sc = ranked[1][1] if len(ranked) > 1 else 0
    if fiscal_vague:
        c0 = float(tres.confidence)
        c1 = 0.0
        top1_sc = 3
        second_sc = 0
    else:
        c0 = tres.candidates[0].confidence if tres.candidates else tres.confidence
        c1 = tres.candidates[1].confidence if len(tres.candidates) > 1 else 0.0

    rstatus = decide_resolution_status(
        task_confidence=float(tres.confidence),
        task_is_fallback=bool(tres.is_fallback),
        domain_confidence=dom_conf,
        executor_is_defaulted=ex_def,
        duration_is_defaulted=dur_def,
        top1_task_conf=float(c0),
        second_task_conf=float(c1),
        top1_score=int(top1_sc),
        second_score=int(second_sc),
    )
    amb = ambiguity_label(top1_task_conf=float(c0), second_task_conf=float(c1), top1_score=top1_sc, second_score=second_sc)

    clar: List[Dict[str, Any]] = []
    blocked: List[str] = []

    if _VAGUE_ROUTINE.search(text) and not _STRONG_TASK_SIGNAL.search(text):
        rstatus = "needs_clarification"

    if fiscal_vague:
        rstatus = "auto_completed"
        amb = "low"
        blocked.append("fiscal_goal_vague_default")

    # 肃贪 + L3 严治：不因同域两条 catalog 的歧义度误判为澄清（legacy 双轨需稳定入 legacy resolver）
    if (
        dom == "anti_corruption"
        and (intent or "").strip() == "strict_governance"
        and rstatus == "needs_clarification"
        and float(tres.confidence) >= 0.52
    ):
        rstatus = "resolved"
        amb = "low"

    if rstatus == "needs_clarification" and not clar:
        clar = build_clarification_options(clarification_candidates_diverse(text, max_items=3))
        blocked.append("vague_or_ambiguous_task")

    row = fiscal_vague_default_row() if fiscal_vague else tres.row
    log_w = effective_ability_weights(dom, row)
    minister_w = logical_weights_to_minister_weights(log_w)
    meta = {
        "delegate_allowed": bool(getattr(row, "delegate_allowed", True)),
        "min_task_confidence": float(getattr(row, "min_task_confidence", 0.62)),
        "narrative_mode": str(getattr(row, "narrative_mode", "delegated_execution")),
        "ability_weights_logical": log_w,
        "ability_weights_minister": minister_w,
        "task_risk_tags": list(getattr(row, "task_risk_tags", ()) or ()),
        "delegate_route": str(getattr(row, "delegate_route", None) or "mixed"),
    }
    if fiscal_vague:
        meta["fiscal_goal_vague_default"] = True
        meta["fiscal_default_task_key"] = row.task_key
    if dom == "disaster_relief":
        meta["playbook_resolution_mode"] = "catalog_fallback" if tres.is_fallback else "keyword_explicit"
    risk = list(fr.risk_tags or [])
    for rt in meta["task_risk_tags"]:
        if rt not in risk:
            risk.append(rt)

    notes = [x for x in (fr.completion_notes_zh or "").split("；") if x.strip()]
    if fiscal_vague and not any("清厘积欠" in x for x in notes):
        notes.append("理财目标未明示手段，按清厘积欠推定承办")
    if rstatus == "auto_completed" and not any("自动补齐" in x for x in notes):
        notes.append("未明示槽位处已按目录与语境自动补齐")
    comp = "；".join(notes) if notes else (fr.completion_notes_zh or "")

    fr_out = fr.model_copy(
        update={
            "task": TaskSpec(domain=dom, task_key=row.task_key, title_zh=row.title_zh),
            "expected_effect_profile": normalize_effect_profile_keys(dict(row.expected_effect_profile)),
            "risk_tags": risk,
            "resolution_status": rstatus,
            "ambiguity_status": amb,
            "domain_confidence": dom_conf,
            "task_confidence": float(tres.confidence),
            "executor_confidence": ex_conf,
            "duration_confidence": dur_conf,
            "clarification_options": clar,
            "blocked_reasons": blocked,
            "task_meta": meta,
            "is_auto_completed": fr.is_auto_completed or (rstatus == "auto_completed"),
            "completion_notes_zh": comp or fr.completion_notes_zh,
        }
    )
    fr_out = apply_location_target_to_frame(fr_out, edict_text=text)
    fr_out = merge_risk_tags_from_modifier(fr_out)
    if (fr_out.resolution_status or "") == "needs_clarification":
        fr_out = fr_out.model_copy(update={"normalized_command_zh": ""})
    else:
        fr_out = apply_normalized_line(fr_out)
    fr_out = fr_out.model_copy(update={"legacy_eligible": _compute_legacy_eligible(fr_out)})
    return fr_out


def _single_path_frame(
    *,
    edict_text: str,
    parse_trace: Dict[str, Any],
    numeric_data: NumericData,
    edict_executor_name: str,
    explicitness_class: str,
) -> EdictExecutionFrame:
    trace = parse_trace or {}
    names = _minister_names(numeric_data)
    sem = extract_semantic_frame_from_trace(edict_text or "", trace)
    intent = get_l3_intent(trace)
    domain = resolve_domain_from_semantic_and_text(
        trace_domain=str(sem.domain or trace.get("edict_category") or "general"),
        l3_intent=intent,
        edict_text=edict_text or "",
    )
    tres = resolve_task_for_domain(domain, edict_text or "")
    row = tres.row
    ex = resolve_executor(
        edict_text=edict_text or "",
        parse_trace=trace,
        task_row=row,
        edict_executor_name=edict_executor_name,
        minister_names=names,
        explicitness_class=explicitness_class,
    )
    dur = resolve_duration(edict_text or "", row, explicitness_class, domain=domain)
    _, dur_explicit = duration_explicit_from_text(edict_text or "")
    if ex.mode in ("person", "dual_person") and dur_explicit:
        dur = bump_duration_for_person_task(dur, explicitness_class=explicitness_class, min_quarters=1)
    prof = normalize_effect_profile_keys(dict(row.expected_effect_profile))
    tid = slug_frame_id(edict_text or "", row.task_key)
    action_type = row.action_type
    if ex.mode == "person" and "named" in (action_type or ""):
        pass
    elif ex.mode == "person":
        action_type = "named_execution"
    elif ex.mode == "dual_person":
        action_type = "named_execution"
    notes: List[str] = []
    if dur.is_inferred:
        notes.append("时长依目录或语境补齐")
    if ex.is_inferred:
        notes.append("承办依领域默认补齐")
    fr = EdictExecutionFrame(
        frame_id=tid,
        explicitness_class=explicitness_class,
        executor=ex,
        task=TaskSpec(domain=domain, task_key=row.task_key, title_zh=row.title_zh),
        duration=dur,
        intensity=str(sem.intensity or "medium"),
        expected_effect_profile=prof,
        confidence=float(sem.confidence or 0.55),
        is_auto_completed=bool(notes),
        completion_notes_zh="；".join(notes),
        metadata={"action_type": action_type, "l3_intent": intent},
    )
    fr = apply_normalized_line(fr)
    fr = apply_location_target_to_frame(fr, edict_text=edict_text or "")
    ex2 = enhance_executor_for_location_delegate(
        edict_text=edict_text or "",
        task_row=row,
        executor=fr.executor,
        ministers=list(numeric_data.ministers or []),
        location=fr.location,
        domain=domain,
        target_entity=fr.target_entity,
    )
    notes_loc = list(fr.completion_notes_zh.split("；") if fr.completion_notes_zh else [])
    if ex2.mode == "person" and ex2.is_inferred and ex2.person_name:
        if not any("路分" in x for x in notes_loc):
            notes_loc.append("路分遣命，依大臣表推举承办")
        fr = fr.model_copy(
            update={
                "executor": ex2,
                "completion_notes_zh": "；".join([x for x in notes_loc if x.strip()]),
                "is_auto_completed": True,
            }
        )
    elif ex2.mode == "person" and ex2.person_name and not ex2.is_inferred:
        fr = fr.model_copy(update={"executor": ex2})
    return enrich_frame_with_resolution(fr, edict_text=edict_text or "", parse_trace=trace)


def fallback_steady_frame(
    *,
    edict_text: str,
    explicitness_class: str,
    numeric_data: NumericData,
    parse_trace: Dict[str, Any],
    edict_executor_name: str,
) -> EdictExecutionFrame:
    """全部候选被拒时的安全单帧。"""
    names = _minister_names(numeric_data)
    row = select_task_row_for_domain("general", edict_text or "")
    ex = resolve_executor(
        edict_text=edict_text or "",
        parse_trace=parse_trace or {},
        task_row=row,
        edict_executor_name=edict_executor_name,
        minister_names=names,
        explicitness_class=explicitness_class,
    )
    dur = resolve_duration(edict_text or "", row, explicitness_class, domain="general")
    tid = slug_frame_id(edict_text or "", row.task_key)
    notes_fb: List[str] = []
    if dur.is_inferred:
        notes_fb.append("时长默认")
    if ex.is_inferred:
        notes_fb.append("承办默认")
    fr = EdictExecutionFrame(
        frame_id=tid,
        explicitness_class=explicitness_class,
        executor=ex,
        task=TaskSpec(domain="general", task_key=row.task_key, title_zh=row.title_zh),
        duration=dur,
        intensity="medium",
        expected_effect_profile=normalize_effect_profile_keys(dict(row.expected_effect_profile)),
        confidence=0.4,
        is_auto_completed=bool(notes_fb),
        completion_notes_zh="；".join(notes_fb),
        metadata={"source": "fallback_steady"},
    )
    fr = apply_normalized_line(fr)
    return enrich_frame_with_resolution(
        fr,
        edict_text=edict_text or "",
        parse_trace=parse_trace or {},
        task_row_confidence=0.38,
        task_row_fallback=True,
    )


def build_final_execution_frame(
    *,
    edict_text: str,
    edict_parse: Dict[str, Any],
    numeric_data: NumericData,
    edict_executor_name: str = "",
    include_internal_debug: bool = False,
) -> Tuple[EdictExecutionFrame, List[str], Optional[List[EdictExecutionFrame]], List[Dict[str, Any]]]:
    """
    Returns:
      final_frame, priority_trace, internal_candidates (only if D and debug), rejected list
    """
    trace = edict_parse.get("trace") or {}
    names = _minister_names(numeric_data)
    from nlu_layer.pipeline import ensure_nlu_in_trace

    ex_pre = trace.get("executor_resolution") or {}
    ensure_nlu_in_trace(
        trace,
        edict_text or "",
        minister_names=names,
        executor_name=str((ex_pre.get("name") if isinstance(ex_pre, dict) else "") or "").strip(),
        executor_source=str((ex_pre.get("source") if isinstance(ex_pre, dict) else "") or "none"),
    )
    sem_pre = extract_semantic_frame_from_trace(edict_text or "", trace)
    intent_pre = get_l3_intent(trace)
    domain_pre = resolve_domain_from_semantic_and_text(
        trace_domain=str(sem_pre.domain or trace.get("edict_category") or "general"),
        l3_intent=intent_pre,
        edict_text=edict_text or "",
    )
    cls = classify_edict_explicitness(
        edict_text or "",
        trace,
        edict_executor_name=edict_executor_name,
        minister_names=names,
        resolved_domain=domain_pre,
    )
    prio: List[str] = ["explicitness=%s" % cls]

    internal: Optional[List[EdictExecutionFrame]] = None
    rejected: List[Dict[str, Any]] = []

    if cls == "D" and domain_pre in ("engineering", "public_order"):
        single_spatial = _single_path_frame(
            edict_text=edict_text or "",
            parse_trace=trace,
            numeric_data=numeric_data,
            edict_executor_name=edict_executor_name,
            explicitness_class=cls,
        )
        ok_sp, rej_sp = partition_admissible([single_spatial], numeric_data)
        rejected.extend(rej_sp)
        picked_sp = pick_first_admissible(ok_sp)
        if picked_sp is not None:
            prio.append("spatial_domain_single_path:%s" % domain_pre)
            return picked_sp, prio, None, rejected

    if cls == "D":
        sem = sem_pre
        domain = domain_pre
        raw = generate_internal_candidates(
            edict_text=edict_text or "",
            domain=domain,
            numeric_data=numeric_data,
            intensity=str(sem.intensity or "medium"),
        )
        if include_internal_debug:
            internal = [apply_normalized_line(r) for r in raw]
        normalized = [apply_normalized_line(r) for r in raw]
        ok_list, part_rej = partition_admissible(normalized, numeric_data)
        rejected.extend(part_rej)
        picked_d = pick_first_admissible(ok_list)
        if picked_d is not None:
            prio.append("picked_internal:%s" % picked_d.frame_id)
            picked_enriched = enrich_frame_with_resolution(
                picked_d,
                edict_text=edict_text or "",
                parse_trace=trace,
            )
            return picked_enriched, prio, internal, rejected
        fb = fallback_steady_frame(
            edict_text=edict_text or "",
            explicitness_class=cls,
            numeric_data=numeric_data,
            parse_trace=trace,
            edict_executor_name=edict_executor_name,
        )
        prio.append("fallback_after_internal_all_rejected")
        return fb, prio, internal, rejected

    single = _single_path_frame(
        edict_text=edict_text or "",
        parse_trace=trace,
        numeric_data=numeric_data,
        edict_executor_name=edict_executor_name,
        explicitness_class=cls,
    )
    ok_list, rej = partition_admissible([single], numeric_data)
    rejected.extend(rej)
    picked = pick_first_admissible(ok_list)
    if picked is not None:
        prio.append("single_path_admissible")
        return picked, prio, None, rejected

    fb = fallback_steady_frame(
        edict_text=edict_text or "",
        explicitness_class=cls,
        numeric_data=numeric_data,
        parse_trace=trace,
        edict_executor_name=edict_executor_name,
    )
    prio.append("single_path_rejected_using_fallback")
    return fb, prio, None, rejected
