# -*- coding: utf-8 -*-
"""候选政务行动管线 trace 组装。"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .policy_ir import PolicyActionCandidate, SemanticFrame


def effects_fingerprint(effects: List[Dict[str, Any]]) -> str:
    try:
        blob = json.dumps(effects or [], ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        blob = str(effects)
    return hashlib.sha256(blob.encode("utf-8", errors="ignore")).hexdigest()[:16]


def build_policy_candidate_trace(
    *,
    mode: str,
    semantic_frame: SemanticFrame,
    generated: List[PolicyActionCandidate],
    rejected: List[Dict[str, Any]],
    scores: List[Dict[str, Any]],
    selected: Optional[PolicyActionCandidate],
    resolved_effects: List[Dict[str, Any]],
    legacy_effects: List[Dict[str, Any]],
    state_metrics_subset: Optional[Dict[str, Any]] = None,
    select_applied: bool = False,
) -> Dict[str, Any]:
    return {
        "policy_candidate_mode": mode,
        "semantic_frame": semantic_frame.model_dump(),
        "policy_candidates": [c.model_dump() for c in generated],
        "rejected_candidates": rejected,
        "candidate_scores": scores,
        "selected_candidate": selected.model_dump() if selected else None,
        "resolved_effects": list(resolved_effects or []),
        "legacy_effects_fingerprint": effects_fingerprint(legacy_effects),
        "resolved_effects_fingerprint": effects_fingerprint(resolved_effects),
        "state_metrics_subset": dict(state_metrics_subset or {}),
        "select_applied": bool(select_applied),
    }
