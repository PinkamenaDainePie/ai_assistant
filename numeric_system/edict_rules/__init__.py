# -*- coding: utf-8 -*-
"""Category-pack rules for L1 parsing."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .diplomacy import run_rules as run_diplomacy_rules
from .internal import run_rules as run_internal_rules
from .military import run_rules as run_military_rules
from .other import run_rules as run_other_rules


def run_category_pack(
    text: str,
    _numeric_data: Any,  # kept for compatibility with old signature
    category_ids: Sequence[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    effects: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    categories = [str(c or "").strip() for c in (category_ids or [])]
    if not categories:
        categories = ["other"]

    for cid in categories:
        if cid == "military":
            e, h = run_military_rules(text, _numeric_data)
        elif cid == "internal":
            e, h = run_internal_rules(text, _numeric_data)
        elif cid == "diplomacy":
            e, h = run_diplomacy_rules(text, _numeric_data)
        else:
            e, h = run_other_rules(text, _numeric_data)
        effects.extend(e)
        hits.extend([{"category": cid, **x} for x in h])

    trace = {"categories": categories, "hits": hits, "fallback": True}
    return effects, trace

