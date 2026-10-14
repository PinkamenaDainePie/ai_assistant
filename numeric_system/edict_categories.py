# -*- coding: utf-8 -*-
"""诏书板块归一化与可选遗留乘子。"""
import os
from typing import Any, Dict, List, Sequence, Tuple

_METRIC_KEYS = (
    "treasury_balance",
    "inner_treasury_balance",
    "public_support",
    "unrest",
    "fiscal_pressure",
)

_CATEGORY_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "military": {
        "treasury_balance": 1.12,
        "inner_treasury_balance": 1.06,
        "public_support": 0.93,
        "unrest": 1.10,
        "fiscal_pressure": 1.12,
    },
    "internal": {
        "treasury_balance": 1.04,
        "inner_treasury_balance": 1.02,
        "public_support": 1.10,
        "unrest": 1.12,
        "fiscal_pressure": 1.04,
    },
    "diplomacy": {
        "treasury_balance": 1.08,
        "inner_treasury_balance": 1.00,
        "public_support": 1.02,
        "unrest": 0.92,
        "fiscal_pressure": 1.00,
    },
    "other": {k: 1.0 for k in _METRIC_KEYS},
}

_CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "military": ("军", "兵", "募兵", "扩军", "练兵", "边防", "军饷", "海防", "战船"),
    "internal": ("内政", "赋税", "田亩", "赈济", "吏治", "户部", "减税", "免税", "加税", "钱粮", "徭役"),
    "diplomacy": ("外交", "邦交", "和议", "互市", "通商", "使节", "盟约", "册封"),
}


def normalize_edict_category(raw: Any) -> str:
    v = str(raw or "").strip().lower()
    if v in ("military", "军"):
        return "military"
    if v in ("internal", "内政"):
        return "internal"
    if v in ("diplomacy", "外交"):
        return "diplomacy"
    if "军" in str(raw):
        return "military"
    if "内政" in str(raw):
        return "internal"
    if "外交" in str(raw):
        return "diplomacy"
    return "other"


def _keyword_categories(text: str) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    scored: List[Tuple[str, int]] = []
    for cid, words in _CATEGORY_KEYWORDS.items():
        score = sum(1 for w in words if w in t)
        if score > 0:
            scored.append((cid, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]


def normalize_edict_categories(primary: Any, text: str = "") -> List[str]:
    out: List[str] = []
    p = normalize_edict_category(primary)
    if p != "other":
        out.append(p)
    for c in _keyword_categories(text):
        if c not in out:
            out.append(c)
    if not out:
        out = ["other"]
    return out


def select_primary_category(candidates: Sequence[str]) -> str:
    for c in candidates or []:
        n = normalize_edict_category(c)
        if n != "other":
            return n
    return "other"


def category_label_zh(category: str) -> str:
    c = normalize_edict_category(category)
    return {"military": "军", "internal": "内政", "diplomacy": "外交", "other": "其他"}.get(c, "其他")


def apply_category_to_effects(
    effects: List[Dict[str, Any]],
    category: str,
    *,
    use_legacy_multiplier: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    c = normalize_edict_category(category)
    multipliers = _CATEGORY_MULTIPLIERS.get(c, _CATEGORY_MULTIPLIERS["other"])
    env_use_multiplier = (os.getenv("PARSER_USE_LEGACY_CATEGORY_MULTIPLIER") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    use_multiplier = bool(use_legacy_multiplier or env_use_multiplier)
    if not use_multiplier:
        return list(effects or []), {
            "enabled": False,
            "resolved_id": c,
            "label_zh": category_label_zh(c),
            "multipliers": multipliers,
        }
    out: List[Dict[str, Any]] = []
    for e in effects or []:
        if str(e.get("action", "")).strip() != "add_metric":
            out.append(e)
            continue
        key = str(e.get("key", "")).strip()
        val = float(e.get("value") or 0.0)
        out.append({**e, "value": round(val * float(multipliers.get(key, 1.0)), 2)})
    return out, {
        "enabled": True,
        "resolved_id": c,
        "label_zh": category_label_zh(c),
        "multipliers": multipliers,
    }

