# -*- coding: utf-8 -*-
"""候选政务行动管线编排 + 环境开关。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .candidate_filter import filter_policy_candidates
from .candidate_generator import generate_policy_candidates
from .candidate_ranker import rank_policy_candidates, select_candidate
from .candidate_resolver import resolve_candidate_to_effects
from .candidate_trace import build_policy_candidate_trace
from .policy_ir import PolicyActionCandidate, SemanticFrame
from .semantic_frame_extract import extract_semantic_frame_from_trace
from .types import NumericData


def policy_candidate_mode_from_env() -> str:
    raw = (os.getenv("POLICY_CANDIDATE_MODE") or "shadow").strip().lower()
    if raw in ("off", "shadow", "select", "parse_only"):
        return raw
    return "shadow"


def _append_policy_log(obj: Dict[str, Any]) -> None:
    path = (os.getenv("POLICY_CANDIDATE_LOG_PATH") or "").strip()
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def run_policy_candidate_pipeline(
    *,
    edict_text: str,
    parse_trace: Dict[str, Any],
    numeric_data: NumericData,
    state_metrics: Dict[str, float],
    legacy_effects: List[Dict[str, Any]],
    mode: str,
    selected_candidate_id: str = "",
) -> Tuple[SemanticFrame, List[Dict[str, Any]], Optional[PolicyActionCandidate], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns:
      semantic_frame,
      resolved_effects (for selected / top-1),
      selected_candidate,
      rejected_list,
      trace_dict
    """
    frame = extract_semantic_frame_from_trace(edict_text, parse_trace)
    generated = generate_policy_candidates(semantic_frame=frame, edict_text=edict_text)
    accepted, rejected = filter_policy_candidates(
        candidates=generated,
        numeric_data=numeric_data,
        state_metrics=state_metrics,
    )
    if not accepted:
        trace = build_policy_candidate_trace(
            mode=mode,
            semantic_frame=frame,
            generated=generated,
            rejected=rejected,
            scores=[],
            selected=None,
            resolved_effects=[],
            legacy_effects=legacy_effects,
            state_metrics_subset={k: state_metrics.get(k) for k in ("corruption", "treasury_balance", "unrest")},
            select_applied=False,
        )
        return frame, [], None, rejected, trace

    scores = rank_policy_candidates(
        candidates=accepted,
        semantic_frame=frame,
        state_metrics=state_metrics,
        numeric_data=numeric_data,
    )
    by_id = {c.candidate_id: c for c in accepted}
    ranked_ids = [row["candidate_id"] for row in scores if row["candidate_id"] in by_id]
    selected = select_candidate(
        ranked_ids=ranked_ids,
        candidates_by_id=by_id,
        selected_candidate_id=selected_candidate_id,
    )
    resolved, _meta = resolve_candidate_to_effects(
        selected,
        numeric_data=numeric_data,
        state_metrics=state_metrics,
    )

    trace = build_policy_candidate_trace(
        mode=mode,
        semantic_frame=frame,
        generated=generated,
        rejected=rejected,
        scores=scores,
        selected=selected,
        resolved_effects=resolved,
        legacy_effects=legacy_effects,
        state_metrics_subset={k: state_metrics.get(k) for k in ("corruption", "treasury_balance", "unrest", "fiscal_pressure")},
        select_applied=False,
    )
    _append_policy_log(
        {
            "kind": "policy_candidate",
            "mode": mode,
            "selected_id": selected.candidate_id,
            "legacy_fp": trace.get("legacy_effects_fingerprint"),
            "resolved_fp": trace.get("resolved_effects_fingerprint"),
        }
    )
    return frame, resolved, selected, rejected, trace
