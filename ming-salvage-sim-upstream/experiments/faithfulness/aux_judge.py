# -*- coding: utf-8 -*-
"""P2 auxiliary: WorldState-anchored LLM-as-Judge placeholder (NOT primary).

Bare unanchored judges are disallowed as primary scores (MERG).
If enabled later, rubric must cite decree + committed WorldState evidence.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def judge_faithfulness(
    *,
    decree: str,
    report: str,
    worldstate_excerpt: str = "",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Stub judge. Does not call any LLM."""
    _ = (decree, report, worldstate_excerpt, model)
    return {
        "metric": "llm_judge_anchored",
        "role": "P2_auxiliary",
        "score": None,
        "note": "Disabled by default; never replace P0 live/narr",
    }
