# -*- coding: utf-8 -*-
"""Agent A 入参动作选取：按 contest / counter / other 分级，决定传几条分段。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agent_flow.object_classifier import MATERIAL_KIND, action_object_kind

ACTION_TIER_CONTEST = "contest"
ACTION_TIER_COUNTER = "counter"
ACTION_TIER_OTHER = "other"

# 人为动作域默认叙事层级（物/制度类 playbook 见下方覆盖 → other）
_DOMAIN_HUMAN_ACTION_TIER: Dict[str, str] = {
    "military": ACTION_TIER_CONTEST,
    "diplomacy": ACTION_TIER_CONTEST,
    "anti_corruption": ACTION_TIER_CONTEST,
    "public_order": ACTION_TIER_CONTEST,
    "personnel": ACTION_TIER_COUNTER,
    "fiscal": ACTION_TIER_COUNTER,
    "disaster_relief": ACTION_TIER_COUNTER,
    "general": ACTION_TIER_COUNTER,
}

# playbook 级覆盖（与 object_classifier 物/人划分对齐）
_PLAYBOOK_ACTION_TIER: Dict[Tuple[str, str], str] = {
    ("disaster_relief", "open_granary_relief"): ACTION_TIER_OTHER,
    ("disaster_relief", "tax_remission_relief"): ACTION_TIER_OTHER,
    ("fiscal", "reduce_court_spending"): ACTION_TIER_OTHER,
    ("fiscal", "expand_state_monopoly"): ACTION_TIER_OTHER,
    ("fiscal", "corvee_commutation"): ACTION_TIER_OTHER,
    ("fiscal", "equalized_transport"): ACTION_TIER_OTHER,
    ("fiscal", "abolish_state_monopoly"): ACTION_TIER_OTHER,
    ("agriculture", "spring_encourage_farming"): ACTION_TIER_OTHER,
    ("agriculture", "irrigation_or_land_improvement"): ACTION_TIER_OTHER,
    ("agriculture", "mulberry_silk_promotion"): ACTION_TIER_OTHER,
    ("agriculture", "spring_grain_lending"): ACTION_TIER_OTHER,
    ("engineering", "river_dike_repair"): ACTION_TIER_OTHER,
}


def classify_action_tier(domain: str, task_key: str = "") -> str:
    """将 domain/playbook 映射为 contest | counter | other。"""
    dom = str(domain or "").strip().lower()
    tk = str(task_key or "").strip().lower()
    if dom and tk:
        hit = _PLAYBOOK_ACTION_TIER.get((dom, tk))
        if hit:
            return hit
    if action_object_kind(dom, tk) == MATERIAL_KIND:
        return ACTION_TIER_OTHER
    return _DOMAIN_HUMAN_ACTION_TIER.get(dom, ACTION_TIER_COUNTER)


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


def collect_edict_action_candidates(
    execution_context: Optional[Dict[str, Any]],
    resolved_pack: Optional[Dict[str, Any]],
    final_frame: Any = None,
) -> List[Dict[str, Any]]:
    """从 resolved segment_packs 或单帧 final_frame 收集可裁决分段。"""
    exec_ctx = dict(execution_context or {})
    pack = dict(resolved_pack or {})
    out: List[Dict[str, Any]] = []

    segment_packs = list(pack.get("segment_packs") or [])
    if segment_packs:
        for row in segment_packs:
            if not isinstance(row, dict):
                continue
            if str(row.get("status") or "") == "needs_clarification":
                continue
            dom = str(row.get("domain") or "").strip()
            tk = str(row.get("task_key") or "").strip()
            if not dom:
                continue
            idx = int(row.get("index") if row.get("index") is not None else len(out))
            tier = str(row.get("action_tier") or "").strip().lower()
            if tier not in (ACTION_TIER_CONTEST, ACTION_TIER_COUNTER, ACTION_TIER_OTHER):
                tier = classify_action_tier(dom, tk)
            out.append(
                {
                    "index": idx,
                    "domain": dom,
                    "task_key": tk,
                    "text": _segment_text_from_context(exec_ctx, index=idx, domain=dom, task_key=tk),
                    "action_tier": tier,
                }
            )
        return out

    if final_frame is not None:
        task = getattr(final_frame, "task", None)
        dom = str(getattr(task, "domain", "") or "").strip()
        tk = str(getattr(task, "task_key", "") or "").strip()
        if dom:
            meta = getattr(final_frame, "metadata", None) or {}
            text = str(meta.get("segment_text") or "").strip() if isinstance(meta, dict) else ""
            out.append(
                {
                    "index": 0,
                    "domain": dom,
                    "task_key": tk,
                    "text": text,
                    "action_tier": classify_action_tier(dom, tk),
                }
            )
    return out


def _pick_one(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sorted(candidates, key=lambda c: int(c.get("index") or 0))[0]


def select_agent_a_actions(
    candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    选取传给 Agent A 的分段：
    - contest 与 counter 皆有 → 各选 1 条（最多 2 条）
    - 仅有 contest 或 counter → 选 1 条
    - 仅有 other → 不传（空列表）
    """
    trace: Dict[str, Any] = {
        "candidate_count": len(candidates or []),
        "candidates_by_tier": {},
    }
    if not candidates:
        trace["selection_mode"] = "no_candidates"
        return [], trace

    by_tier: Dict[str, List[Dict[str, Any]]] = {
        ACTION_TIER_CONTEST: [],
        ACTION_TIER_COUNTER: [],
        ACTION_TIER_OTHER: [],
    }
    for c in candidates:
        tier = str(c.get("action_tier") or ACTION_TIER_OTHER).strip().lower()
        if tier not in by_tier:
            tier = classify_action_tier(str(c.get("domain") or ""), str(c.get("task_key") or ""))
        by_tier[tier].append(c)

    trace["candidates_by_tier"] = {k: len(v) for k, v in by_tier.items()}

    contest_rows = by_tier[ACTION_TIER_CONTEST]
    counter_rows = by_tier[ACTION_TIER_COUNTER]

    selected: List[Dict[str, Any]] = []
    if contest_rows and counter_rows:
        selected = [_pick_one(contest_rows), _pick_one(counter_rows)]
        trace["selection_mode"] = "contest_and_counter"
    elif contest_rows:
        selected = [_pick_one(contest_rows)]
        trace["selection_mode"] = "contest_only"
    elif counter_rows:
        selected = [_pick_one(counter_rows)]
        trace["selection_mode"] = "counter_only"
    else:
        trace["selection_mode"] = "other_only_skip"

    selected = sorted(selected, key=lambda c: int(c.get("index") or 0))
    trace["selected"] = [
        {
            "index": c.get("index"),
            "domain": c.get("domain"),
            "task_key": c.get("task_key"),
            "action_tier": c.get("action_tier"),
        }
        for c in selected
    ]
    return selected, trace
