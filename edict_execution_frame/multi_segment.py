# -*- coding: utf-8 -*-
"""多域诏书：LLM 分段 → 多 EdictExecutionFrame → 合并执行。"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.domain_catalog import (
    build_playbook_whitelist_for_llm,
    catalog_domain_ids,
    catalog_playbook_keys,
    lookup_task_row,
    normalize_effect_profile_keys,
    select_task_row_for_domain,
    slug_frame_id,
)
from edict_execution_frame.duration_resolver import bump_duration_for_person_task, resolve_duration
from edict_execution_frame.executor_resolver import resolve_executor
from edict_execution_frame.explicitness import classify_edict_explicitness, duration_explicit_from_text, get_l3_intent
from edict_execution_frame.frame_builder import enrich_frame_with_resolution, _minister_names
from edict_execution_frame.location_slot import apply_location_target_to_frame
from edict_execution_frame.narrative_builder import apply_normalized_line
from edict_execution_frame.provincial_delegate import enhance_executor_for_location_delegate
from edict_execution_frame.resolver import resolve_frame_to_effects_and_tasks
from edict_execution_frame.schemas import EdictExecutionFrame, TaskSpec
from agent_flow.action_selector import classify_action_tier
from numeric_system.llm_intent_schema import build_intent_whitelist
from numeric_system.llm_segment_schema import (
    LlmEdictSegment,
    LlmMultiSegmentDsl,
    derive_legacy_intent,
    parse_llm_multi_segment_json,
)
from nlu_layer.intent_catalog import INTENT_CATALOG
from numeric_system.semantic_frame_extract import extract_semantic_frame_from_trace
from numeric_system.types import NumericData


def multi_domain_llm_enabled() -> bool:
    raw = (os.getenv("EDICT_MULTI_DOMAIN_LLM") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def unified_semantic_llm_enabled() -> bool:
    """L3 意图与多域分段合并为一次 LLM（默认随多域开启）。"""
    raw = os.getenv("EDICT_UNIFIED_SEMANTIC_LLM")
    if raw is not None:
        return raw.strip().lower() not in ("0", "false", "no", "off")
    return multi_domain_llm_enabled()


def should_skip_standalone_l3() -> bool:
    """parse 阶段不再单独调 L3；意图由统一语义 LLM 或 fallback 写入 trace。"""
    return unified_semantic_llm_enabled() and multi_domain_llm_enabled()


def _degree_to_intensity(degree: str) -> str:
    d = (degree or "").strip().lower()
    if d == "heavily":
        return "high"
    if d == "slightly":
        return "low"
    return "medium"


def _http_config() -> Dict[str, Any]:
    from numeric_system.edict_parser import _l3_http_config

    return _l3_http_config()


def _build_segment_prompt(edict_text: str, whitelist: List[Dict[str, str]]) -> str:
    wl_json = json.dumps(whitelist, ensure_ascii=False, separators=(",", ":"))
    intent_list = build_intent_whitelist(INTENT_CATALOG)
    intents_csv = ",".join(intent_list)
    return (
        "你是诏书统一语义解析器：同时完成【整诏意图归类】与【多域分段+playbook】。\n"
        "你必须只输出一个 JSON 对象，不要输出解释。\n"
        "JSON 结构：\n"
        '{"intent":"意图id","degree":"slightly|moderately|heavily",'
        '"segments":[{"domain":"领域id","task_key":"playbook键","text":"该段原文摘句","degree":"slightly|moderately|heavily"}]}\n'
        "规则：\n"
        "1. intent 表示整诏主意图，必须从下列白名单选一；多域诏书选最主要的一条。\n"
        f"   intent 白名单：{intents_csv}\n"
        "2. degree 表示整诏总体力度；各 segment 可另有 degree。\n"
        "3. 若诏书只涉及一个领域，segments 仍只含 1 条。\n"
        "4. 若涉及军事与内政/财政/赈灾等不同领域，必须拆成多条 segment，每条 text 必须是诏书原文的子串。\n"
        "5. domain 与 task_key 必须来自下方 playbook 白名单；不确定 task_key 时可省略，但 domain 必填。\n"
        "6. 不要编造白名单外的 intent/domain/task_key。\n"
        "7. 你只输出归类与分段，不裁定成败、不改数值。\n"
        f"playbook 白名单：{wl_json}\n"
        f"输入诏书：{edict_text.strip()}"
    )


def _allowed_intent_set() -> set:
    return set(build_intent_whitelist(INTENT_CATALOG))


def inject_l3_from_unified_semantic(
    trace: Dict[str, Any],
    dsl: LlmMultiSegmentDsl,
    *,
    confidence: float = 0.78,
) -> None:
    """将统一语义计划写入 trace，供 get_l3_intent / NLU 消费（替代独立 L3 调用）。"""
    intent, degree = derive_legacy_intent(dsl)
    if not intent or intent == "none":
        return
    l3_trace: Dict[str, Any] = {
        "layer": "layer3_llm",
        "hits": [{"source": "unified_semantic_llm", "segment_count": len(dsl.segments)}],
        "confidence": confidence,
        "dsl": {"intent": intent, "degree": degree},
        "effects_suppressed": True,
        "unified_semantic": True,
    }
    stages = trace.setdefault("stages", [])
    if not isinstance(stages, list):
        trace["stages"] = []
        stages = trace["stages"]
    stages.append(l3_trace)
    from nlu_layer.pipeline import merge_l3_into_nlu_trace

    merge_l3_into_nlu_trace(trace, l3_trace)
    trace["unified_semantic_l3"] = {"intent": intent, "degree": degree}


def _fallback_standalone_l3(
    edict_text: str,
    trace: Dict[str, Any],
    *,
    edict_category_hint_zh: str = "",
) -> None:
    """统一 LLM 失败且 parse 已跳过 L3 时，补一次旧 L3。"""
    if get_l3_intent(trace):
        return
    from numeric_system.edict_parser import _layer3_llm

    _effects, l3_trace = _layer3_llm(edict_text, edict_category_hint_zh=edict_category_hint_zh)
    l3_trace["effects_suppressed"] = True
    l3_trace["fallback_after_unified_failed"] = True
    stages = trace.setdefault("stages", [])
    if isinstance(stages, list):
        stages.append(l3_trace)
    from nlu_layer.pipeline import merge_l3_into_nlu_trace

    merge_l3_into_nlu_trace(trace, l3_trace)


def call_llm_for_edict_segments(edict_text: str) -> Tuple[Optional[LlmMultiSegmentDsl], Dict[str, Any]]:
    trace: Dict[str, Any] = {
        "layer": "unified_semantic_llm",
        "hits": [],
        "confidence": 0.0,
        "dsl": None,
        "dsl_parse_trace": None,
        "latency_ms": 0.0,
    }
    text = (edict_text or "").strip()
    if not text:
        trace["hits"].append({"reason": "empty_text"})
        return None, trace

    override = (os.getenv("LLM_SEGMENT_OVERRIDE_JSON") or "").strip()
    if override:
        t0 = time.perf_counter()
        dsl, dsl_trace = parse_llm_multi_segment_json(
            override,
            allowed_domains=catalog_domain_ids(),
            allowed_playbooks=catalog_playbook_keys(),
            allowed_intents=_allowed_intent_set(),
        )
        trace["dsl_parse_trace"] = dsl_trace
        trace["dsl"] = dsl_trace.get("parsed")
        trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        if not dsl:
            trace["hits"].append({"reason": "override_parse_failed"})
            return None, trace
        trace["confidence"] = 0.85
        trace["hits"].append({"override_used": True, "segment_count": len(dsl.segments)})
        return dsl, trace

    http_cfg = _http_config()
    api_key = str(http_cfg.get("api_key") or "").strip()
    if not api_key:
        trace["hits"].append({"reason": "no_api_key"})
        return None, trace

    whitelist = build_playbook_whitelist_for_llm()
    prompt = _build_segment_prompt(text, whitelist)
    url = str(http_cfg.get("base_url") or "").rstrip("/") + "/chat/completions"
    payload = {
        "model": str(http_cfg.get("model") or "qwen-plus"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 600,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=float(http_cfg.get("timeout_sec") or 120)) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        obj = json.loads(raw)
        content = str(
            (((obj.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
        ).strip()
    except Exception as exc:  # noqa: BLE001
        trace["hits"].append({"reason": "http_error", "error": str(exc)})
        trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return None, trace

    trace["raw_output_preview"] = content[:800]
    trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    dsl, dsl_trace = parse_llm_multi_segment_json(
        content,
        allowed_domains=catalog_domain_ids(),
        allowed_playbooks=catalog_playbook_keys(),
        allowed_intents=_allowed_intent_set(),
    )
    trace["dsl_parse_trace"] = dsl_trace
    trace["dsl"] = dsl_trace.get("parsed")
    if not dsl:
        trace["hits"].append({"reason": "dsl_parse_failed", "error": dsl_trace.get("error")})
        return None, trace
    trace["confidence"] = 0.8 if len(dsl.segments) > 1 else 0.72
    trace["hits"].append({"segment_count": len(dsl.segments), "unified": True})
    leg_intent, _ = derive_legacy_intent(dsl)
    if leg_intent and leg_intent != "none":
        trace["hits"].append({"legacy_intent": leg_intent})
    return dsl, trace


def _resolve_row_for_segment(segment: LlmEdictSegment) -> Tuple[Any, str]:
    row = lookup_task_row(segment.domain, segment.task_key) if segment.task_key else None
    if row is None:
        row = select_task_row_for_domain(segment.domain, segment.text)
    note = ""
    if segment.task_key and row.task_key != segment.task_key:
        note = f"task_key 已校正为 {row.task_key}"
    return row, note


def build_frame_for_segment(
    *,
    segment: LlmEdictSegment,
    full_edict_text: str,
    parse_trace: Dict[str, Any],
    numeric_data: NumericData,
    edict_executor_name: str,
    explicitness_class: str,
    segment_index: int,
) -> EdictExecutionFrame:
    trace = dict(parse_trace or {})
    trace["multi_segment_index"] = segment_index
    trace["multi_segment_text"] = segment.text
    names = _minister_names(numeric_data)
    domain = segment.domain
    row, row_note = _resolve_row_for_segment(segment)
    seg_text = segment.text.strip() or full_edict_text
    ex = resolve_executor(
        edict_text=seg_text,
        parse_trace=trace,
        task_row=row,
        edict_executor_name=edict_executor_name,
        minister_names=names,
        explicitness_class=explicitness_class,
    )
    dur = resolve_duration(seg_text, row, explicitness_class, domain=domain)
    _, dur_explicit = duration_explicit_from_text(seg_text)
    if ex.mode in ("person", "dual_person") and dur_explicit:
        dur = bump_duration_for_person_task(dur, explicitness_class=explicitness_class, min_quarters=1)
    prof = normalize_effect_profile_keys(dict(row.expected_effect_profile))
    tid = slug_frame_id(seg_text, f"{row.task_key}_s{segment_index}")
    action_type = row.action_type
    if ex.mode == "person":
        action_type = "named_execution"
    notes: List[str] = []
    if row_note:
        notes.append(row_note)
    notes.append("LLM 多域分段承办")
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
        intensity=_degree_to_intensity(segment.degree),
        expected_effect_profile=prof,
        confidence=0.72,
        is_auto_completed=True,
        completion_notes_zh="；".join(notes),
        metadata={
            "action_type": action_type,
            "multi_segment": True,
            "segment_index": segment_index,
            "segment_text": seg_text,
        },
    )
    fr = apply_normalized_line(fr)
    fr = apply_location_target_to_frame(fr, edict_text=seg_text)
    ex2 = enhance_executor_for_location_delegate(
        edict_text=seg_text,
        task_row=row,
        executor=fr.executor,
        ministers=list(numeric_data.ministers or []),
        location=fr.location,
        domain=domain,
        target_entity=fr.target_entity,
    )
    if ex2.mode == "person" and ex2.person_name:
        fr = fr.model_copy(update={"executor": ex2})
    llm_task_conf = 0.78 if (segment.task_key or "").strip() else None
    return enrich_frame_with_resolution(
        fr,
        edict_text=seg_text,
        parse_trace=trace,
        task_row_confidence=llm_task_conf,
        task_row_fallback=False if llm_task_conf is not None else None,
    )


def resolve_multi_segment_frames(
    frames: List[EdictExecutionFrame],
    *,
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    merged_effects: List[Dict[str, Any]] = []
    merged_tasks: List[Dict[str, Any]] = []
    segment_packs: List[Dict[str, Any]] = []
    narratives: List[str] = []
    resolved_count = 0
    clarify_count = 0

    for idx, frame in enumerate(frames):
        pack = resolve_frame_to_effects_and_tasks(
            frame,
            numeric_data=numeric_data,
            state_metrics=state_metrics,
        )
        status = str(pack.get("resolution_status") or "")
        if status == "needs_clarification":
            clarify_count += 1
            segment_packs.append(
                {
                    "index": idx,
                    "domain": frame.task.domain,
                    "task_key": frame.task.task_key,
                    "status": status,
                    "effects_count": 0,
                    "action_tier": classify_action_tier(frame.task.domain, frame.task.task_key),
                }
            )
            continue
        resolved_count += 1
        effects = list(pack.get("current_effects") or [])
        tasks = list(pack.get("created_tasks") or [])
        merged_effects.extend(effects)
        merged_tasks.extend(tasks)
        nar = str(pack.get("narrative") or frame.normalized_command_zh or "").strip()
        if nar:
            narratives.append(nar)
        segment_packs.append(
            {
                "index": idx,
                "domain": frame.task.domain,
                "task_key": frame.task.task_key,
                "status": status or "resolved",
                "effects_count": len(effects),
                "task_path": pack.get("task_path") or "",
                "action_tier": classify_action_tier(frame.task.domain, frame.task.task_key),
            }
        )

    if resolved_count > 0 and clarify_count > 0:
        primary_status = "partial"
    elif resolved_count > 0:
        primary_status = "resolved"
    elif clarify_count > 0:
        primary_status = "needs_clarification"
    else:
        primary_status = "resolved"

    first_path = segment_packs[0].get("task_path") if segment_packs else ""
    resolved_pack = {
        "current_effects": merged_effects,
        "created_tasks": merged_tasks,
        "narrative": "；".join(narratives),
        "task_path": "multi_domain_edict_execution" if len(frames) > 1 else first_path,
        "resolution_status": primary_status,
        "ambiguity_status": "none" if primary_status != "needs_clarification" else "high",
        "clarification_options": [],
        "delegation_blocked_reasons": [],
        "delegation_mode": "multi_segment",
        "segment_packs": segment_packs,
    }
    return merged_effects, merged_tasks, resolved_pack


def try_multi_segment_edict_pipeline(
    *,
    edict_text: str,
    edict_parse: Dict[str, Any],
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
    edict_executor_name: str = "",
) -> Optional[
    Tuple[EdictExecutionFrame, List[Dict[str, Any]], Dict[str, Any], bool, List[EdictExecutionFrame]]
]:
    if not multi_domain_llm_enabled():
        return None
    dsl, llm_trace = call_llm_for_edict_segments(edict_text)
    base_trace = edict_parse.get("trace") or {}
    if isinstance(base_trace, dict):
        trace = dict(base_trace)
    else:
        trace = {}
    trace["multi_domain_llm"] = llm_trace
    trace["unified_semantic_llm"] = llm_trace
    if isinstance(edict_parse, dict):
        edict_parse["trace"] = trace
    if not dsl or not dsl.segments:
        if should_skip_standalone_l3():
            cat_zh = str(trace.get("edict_category_label_zh") or "").strip()
            _fallback_standalone_l3(edict_text or "", trace, edict_category_hint_zh=cat_zh)
            if isinstance(edict_parse, dict):
                edict_parse["trace"] = trace
        return None

    inject_l3_from_unified_semantic(
        trace,
        dsl,
        confidence=float(llm_trace.get("confidence") or 0.78),
    )
    if isinstance(edict_parse, dict):
        edict_parse["trace"] = trace
    segments = list(dsl.segments)

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
    from edict_execution_frame.domain_catalog import resolve_domain_from_semantic_and_text

    sem_pre = extract_semantic_frame_from_trace(edict_text or "", trace)
    domain_pre = resolve_domain_from_semantic_and_text(
        trace_domain=str(sem_pre.domain or trace.get("edict_category") or "general"),
        l3_intent=get_l3_intent(trace),
        edict_text=edict_text or "",
    )
    cls = classify_edict_explicitness(
        edict_text or "",
        trace,
        edict_executor_name=edict_executor_name,
        minister_names=names,
        resolved_domain=domain_pre,
    )

    frames: List[EdictExecutionFrame] = []
    for idx, seg in enumerate(segments):
        frames.append(
            build_frame_for_segment(
                segment=seg,
                full_edict_text=edict_text,
                parse_trace=trace,
                numeric_data=numeric_data,
                edict_executor_name=edict_executor_name,
                explicitness_class=cls,
                segment_index=idx,
            )
        )

    merged_effects, _merged_tasks, resolved_pack = resolve_multi_segment_frames(
        frames,
        numeric_data=numeric_data,
        state_metrics=state_metrics,
    )
    primary = frames[0]
    applied = bool(merged_effects) and resolved_pack.get("resolution_status") != "needs_clarification"
    trace_extras = {
        "multi_domain": True,
        "segment_count": len(frames),
        "segments": [
            {
                "domain": f.task.domain,
                "task_key": f.task.task_key,
                "text": (f.metadata or {}).get("segment_text", ""),
                "action_tier": classify_action_tier(f.task.domain, f.task.task_key),
            }
            for f in frames
        ],
        "resolved_pack": resolved_pack,
    }
    return primary, merged_effects, trace_extras, applied, frames
