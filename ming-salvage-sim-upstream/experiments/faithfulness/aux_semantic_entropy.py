# -*- coding: utf-8 -*-
"""P2 auxiliary: Semantic Entropy placeholder (NOT a primary metric).

Formal ablation conclusions must use P0 live/narr from score.py.
Wire Farquhar et al. (Nature 2024) SE here only for correlation / appendix analysis.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def estimate_semantic_entropy(
    samples: List[str],
    *,
    impl: str = "stub",
) -> Dict[str, Any]:
    """Return a SE-like dict. Stub returns None score until a real impl is plugged in."""
    if impl != "stub":
        raise NotImplementedError(f"SE impl {impl!r} not bundled; keep P0 metrics primary")
    return {
        "metric": "semantic_entropy",
        "role": "P2_auxiliary",
        "n_samples": len(samples),
        "entropy": None,
        "note": "Not for primary claims; see score.score_row / score_narrative",
    }


def score_row_aux_se(row: dict, samples: Optional[List[str]] = None) -> Dict[str, Any]:
    texts = samples or []
    if not texts:
        report = row.get("player_report") or row.get("report") or ""
        if report:
            texts = [report]
    return estimate_semantic_entropy(texts)
