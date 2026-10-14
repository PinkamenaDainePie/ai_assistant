# -*- coding: utf-8 -*-
"""Lightweight text normalization for edict parsing."""
import re
from typing import Dict, Tuple

_SYNONYMS = {
    "稍增": "略增",
    "增强一点": "略增",
    "提高一点": "略增",
    "略微增加": "略增",
    "稍微降低": "略降",
    "减少一点": "略降",
}

_DEGREE_MAP = [
    (r"(大幅|显著|大力)", "heavily"),
    (r"(适度|中等|稳步)", "moderately"),
    (r"(稍微|略|一点)", "slightly"),
]


def normalize_edict_text(text: str) -> Tuple[str, Dict[str, object]]:
    raw = (text or "").strip()
    if not raw:
        return "", {"synonym_replacements": [], "degree_hint": ""}
    s = raw
    repl = []
    for src, dst in _SYNONYMS.items():
        if src in s:
            s = s.replace(src, dst)
            repl.append({"from": src, "to": dst})

    s = re.sub(r"\s+", " ", s).strip()
    degree_hint = ""
    for pat, hint in _DEGREE_MAP:
        if re.search(pat, s):
            degree_hint = hint
            break

    return s, {"synonym_replacements": repl, "degree_hint": degree_hint}

