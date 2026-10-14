# -*- coding: utf-8 -*-
"""Candidate scoring and merge policies for edict parsing."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ScoreWeights:
    layer_confidence: float = 0.55
    category_consistency: float = 0.15
    evidence_strength: float = 0.20
    effect_sanity: float = 0.10


def _bounded(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _evidence_score(candidate: Dict[str, Any]) -> float:
    evidence = candidate.get("evidence") or {}
    hit_count = int(evidence.get("hit_count") or 0)
    return _bounded(hit_count / 6.0)


def _category_score(candidate: Dict[str, Any], expected_categories: List[str]) -> float:
    cates = candidate.get("categories") or []
    if not cates or not expected_categories:
        return 0.5
    return 1.0 if any(c in expected_categories for c in cates) else 0.2


def _effect_sanity_score(candidate: Dict[str, Any]) -> float:
    effects = candidate.get("effects") or []
    if not effects:
        return 0.0
    legal = 0
    for e in effects:
        if str(e.get("action", "")).strip() == "add_metric":
            legal += 1
    return _bounded(legal / max(1, len(effects)))


def score_candidates(
    candidates: List[Dict[str, Any]],
    *,
    expected_categories: Optional[List[str]] = None,
    weights: ScoreWeights = ScoreWeights(),
) -> List[Dict[str, Any]]:
    expected_categories = expected_categories or []
    scored: List[Dict[str, Any]] = []
    for c in candidates or []:
        conf = _bounded(float(c.get("confidence") or 0.0))
        cate = _category_score(c, expected_categories)
        ev = _evidence_score(c)
        san = _effect_sanity_score(c)
        total = (
            weights.layer_confidence * conf
            + weights.category_consistency * cate
            + weights.evidence_strength * ev
            + weights.effect_sanity * san
        )
        c2 = dict(c)
        c2["score"] = round(total, 6)
        c2["score_breakdown"] = {
            "layer_confidence": round(conf, 6),
            "category_consistency": round(cate, 6),
            "evidence_strength": round(ev, 6),
            "effect_sanity": round(san, 6),
        }
        scored.append(c2)
    scored.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return scored


def merge_effects_weighted(
    scored_candidates: List[Dict[str, Any]],
    *,
    top_k: int = 2,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    picked = list(scored_candidates or [])[: max(1, top_k)]
    if not picked:
        return [], {"picked": [], "merged_by": "none"}

    acc: Dict[str, float] = {}
    trace_picked: List[Dict[str, Any]] = []
    total_w = 0.0
    for item in picked:
        w = float(item.get("score") or 0.0)
        if w <= 0:
            continue
        total_w += w
        trace_picked.append(
            {
                "layer": item.get("layer"),
                "score": round(w, 6),
                "effect_count": len(item.get("effects") or []),
            }
        )
        for e in item.get("effects") or []:
            if str(e.get("action", "")).strip() != "add_metric":
                continue
            key = str(e.get("key", "")).strip()
            if not key:
                continue
            val = float(e.get("value") or 0.0)
            acc[key] = acc.get(key, 0.0) + val * w

    if total_w <= 0:
        return [], {"picked": trace_picked, "merged_by": "weighted_average", "total_weight": 0.0}

    out = [{"action": "add_metric", "key": k, "value": round(v / total_w, 2)} for k, v in acc.items()]
    out.sort(key=lambda x: x["key"])
    return out, {
        "picked": trace_picked,
        "merged_by": "weighted_average",
        "total_weight": round(total_w, 6),
    }

