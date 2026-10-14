# -*- coding: utf-8 -*-
"""Parse ending-summary LLM output (JSON with score, or legacy plain text)."""

from __future__ import annotations

import json
import re
from typing import Optional, Tuple


def _score_label_zh(score: int) -> str:
    if score >= 90:
        return "卓异"
    if score >= 80:
        return "上"
    if score >= 70:
        return "良"
    if score >= 60:
        return "中"
    if score >= 45:
        return "平"
    return "不足"


def parse_ending_summary_llm_output(raw: str) -> Tuple[str, Optional[int], str]:
    text = (raw or "").strip()
    if not text:
        return "", None, ""

    candidate = text
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)```\s*$", text, flags=re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()

    if candidate.startswith("{"):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                summary = str(data.get("summary_zh") or data.get("summary") or "").strip()
                score_raw = data.get("score")
                score: Optional[int] = None
                if score_raw is not None:
                    score = max(0, min(100, int(score_raw)))
                label = str(data.get("score_label_zh") or "").strip()
                if score is not None and not label:
                    label = _score_label_zh(score)
                if summary or score is not None:
                    return summary or text, score, label
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return text, None, ""
