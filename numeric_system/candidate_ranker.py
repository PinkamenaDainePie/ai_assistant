# -*- coding: utf-8 -*-
"""启发式多目标评分与简单排序。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .policy_ir import PolicyActionCandidate, SemanticFrame
from .types import Minister, NumericData


def _intensity_bonus(intensity: str) -> float:
    return {"low": 40.0, "medium": 60.0, "high": 80.0}.get(str(intensity or "medium"), 60.0)


def _minister_fit(m: Minister) -> float:
    """0–100 综合适配（肃贪向：内政+财政+影响）。"""
    internal = float(getattr(m, "ability_internal", 50.0))
    fin = float(getattr(m, "ability_finance", 50.0))
    inf = float(getattr(m, "influence", 50.0))
    return internal * 0.45 + fin * 0.30 + inf * 0.25


def score_candidate(
    *,
    candidate: PolicyActionCandidate,
    semantic_frame: SemanticFrame,
    state_metrics: Dict[str, float],
    numeric_data: NumericData,
) -> Tuple[float, Dict[str, Any]]:
    """返回总分与分解（便于 trace）。"""
    corruption = float(state_metrics.get("corruption", 40.0))
    unrest = float(state_metrics.get("unrest", 30.0))

    text_match = 55.0
    if candidate.domain == semantic_frame.domain:
        text_match += 25.0
    if candidate.intensity == semantic_frame.intensity:
        text_match += 10.0

    need_score = corruption if candidate.domain == "anti_corruption" else 50.0
    state_need = min(100.0, need_score * 0.8 + (100.0 - unrest) * 0.05)

    fit = 50.0
    ex = (candidate.executor or "").strip()
    if ex:
        for m in numeric_data.ministers or []:
            if str(getattr(m, "name", "")).strip() == ex:
                fit = _minister_fit(m)
                break
    else:
        fit = 48.0

    legal = 80.0 if candidate.target_metrics else 60.0
    narrative = 55.0 + min(20.0, len(candidate.summary_zh) / 8.0)

    risk_penalty = 5.0 * len(candidate.risk_tags or [])
    if "local_elite_backlash" in (candidate.risk_tags or []):
        risk_penalty += 8.0

    final = (
        text_match * 0.30
        + state_need * 0.25
        + fit * 0.20
        + legal * 0.15
        + narrative * 0.10
        - risk_penalty * 0.20
    )
    breakdown = {
        "text_match": round(text_match, 2),
        "state_need": round(state_need, 2),
        "minister_fit": round(fit, 2),
        "legality_proxy": round(legal, 2),
        "narrative_clarity": round(narrative, 2),
        "risk_penalty": round(risk_penalty, 2),
        "intensity_bonus_component": round(_intensity_bonus(candidate.intensity) * 0.05, 2),
    }
    final += _intensity_bonus(candidate.intensity) * 0.05
    return round(final, 4), breakdown


def rank_policy_candidates(
    *,
    candidates: List[PolicyActionCandidate],
    semantic_frame: SemanticFrame,
    state_metrics: Dict[str, float],
    numeric_data: NumericData,
) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, PolicyActionCandidate, Dict[str, Any]]] = []
    for c in candidates:
        total, br = score_candidate(
            candidate=c,
            semantic_frame=semantic_frame,
            state_metrics=state_metrics,
            numeric_data=numeric_data,
        )
        scored.append((total, c, br))
    scored.sort(key=lambda x: -x[0])
    return [
        {
            "candidate_id": c.candidate_id,
            "score": t,
            "breakdown": br,
        }
        for t, c, br in scored
    ]


def select_candidate(
    *,
    ranked_ids: List[str],
    candidates_by_id: Dict[str, PolicyActionCandidate],
    selected_candidate_id: str,
) -> PolicyActionCandidate:
    sid = (selected_candidate_id or "").strip()
    if sid and sid in candidates_by_id:
        return candidates_by_id[sid]
    for rid in ranked_ids or []:
        if rid in candidates_by_id:
            return candidates_by_id[rid]
    if not candidates_by_id:
        raise ValueError("no candidates to select")
    return next(iter(candidates_by_id.values()))
