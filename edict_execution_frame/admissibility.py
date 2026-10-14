# -*- coding: utf-8 -*-
"""可执行政务计划：时长、指标键、具名大臣存在性。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from edict_execution_frame.domain_catalog import canonical_metric_key, normalize_effect_profile_keys
from edict_execution_frame.schemas import EdictExecutionFrame
from numeric_system.metric_schema import METRIC_SCHEMA
from numeric_system.types import NumericData


def validate_frame(
    frame: EdictExecutionFrame,
    numeric_data: NumericData,
    *,
    minister_status: Optional[Dict[str, Any]] = None,
    region_status: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    q = int(frame.duration.quarters or 0)
    if q < 1 or q > 5:
        reasons.append("bad_duration")

    prof = normalize_effect_profile_keys(frame.expected_effect_profile or {})
    if not prof:
        reasons.append("empty_effect_profile")
    for key in prof:
        ck = canonical_metric_key(key)
        if ck not in METRIC_SCHEMA:
            reasons.append("unknown_metric:%s" % ck)

    ms = minister_status or {}
    if frame.executor.mode == "person":
        pn = (frame.executor.person_name or "").strip()
        if pn:
            found = any(str(getattr(m, "name", "")).strip() == pn for m in (numeric_data.ministers or []))
            if not found:
                reasons.append("minister_not_in_roster:%s" % pn)
            else:
                st = (ms.get(pn) or {}).get("status") or "active"
                if st != "active":
                    reasons.append("minister_not_active:%s:%s" % (pn, st))

    if frame.executor.mode == "dual_person":
        names = frame.executor.person_names or []
        roster = {str(getattr(m, "name", "") or "").strip() for m in (numeric_data.ministers or [])}
        roster.discard("")
        for pn in names:
            if pn and pn not in roster:
                reasons.append("minister_not_in_roster:%s" % pn)
            elif pn:
                st = (ms.get(pn) or {}).get("status") or "active"
                if st != "active":
                    reasons.append("minister_not_active:%s:%s" % (pn, st))

    # 地区 occupied 不可控：对赈灾/工程/治安类拒或标记（调用方可据此降级）
    rs = region_status or {}
    loc = frame.location or None
    if loc and getattr(loc, "location_id", None):
        rid = str(getattr(loc, "location_id") or "").strip()
        rentry = rs.get(rid) or {}
        if str(rentry.get("status") or "normal") == "occupied":
            dom = (frame.task.domain or "").strip().lower()
            if dom in ("disaster_relief", "engineering", "public_order", "military"):
                reasons.append("region_not_controllable:occupied:%s" % rid)

    return (len(reasons) == 0), reasons


def partition_admissible(
    frames: List[EdictExecutionFrame],
    numeric_data: NumericData,
    *,
    minister_status: Optional[Dict[str, Any]] = None,
    region_status: Optional[Dict[str, Any]] = None,
) -> Tuple[List[EdictExecutionFrame], List[Dict[str, Any]]]:
    ok: List[EdictExecutionFrame] = []
    rejected: List[Dict[str, Any]] = []
    for fr in frames:
        good, r = validate_frame(fr, numeric_data, minister_status=minister_status, region_status=region_status)
        if good:
            ok.append(fr)
        else:
            rejected.append({"frame_id": fr.frame_id, "reasons": r, "normalized": fr.normalized_command_zh})
    return ok, rejected
