# -*- coding: utf-8 -*-
"""北宋大臣委托模版：从 大臣.xlsx 加载的 Minister 列表生成/读取配置。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from numeric_system.types import Minister

_CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "song_minister_delegation.json"
_CACHE: Optional[Dict[str, Any]] = None

_PARTY_BACKLASH = {
    "新党": 1.15,
    "旧党": 1.12,
    "中立派": 1.0,
    "武臣": 0.95,
}


def _minister_entry(m: Minister) -> Dict[str, Any]:
    internal = float(m.ability_internal or 50.0)
    finance = float(m.ability_finance or 50.0)
    military = float(m.ability_military or 50.0)
    diplomacy = float(m.ability_diplomacy or 50.0)
    inf = float(m.influence or 50.0)
    party = (m.party or "").strip() or "中立派"
    preferred: List[str] = ["anti_corruption"]
    if finance >= 75:
        preferred.append("fiscal")
    if internal >= 80:
        preferred.insert(0, "anti_corruption")
    if military >= 75:
        preferred.append("military")
    return {
        "name": m.name.strip(),
        "office": m.office or "",
        "party": party,
        "stance": m.stance or "",
        "influence": inf,
        "ability_weights": {
            "integrity": round(internal / 100.0, 3),
            "governance": round((0.55 * internal + 0.45 * finance) / 100.0, 3),
            "political_power": round(inf / 100.0, 3),
            "execution": round((0.4 * internal + 0.35 * military + 0.25 * diplomacy) / 100.0, 3),
        },
        "party_backlash_multiplier": _PARTY_BACKLASH.get(party, 1.0),
        "anti_corruption_bias": round(
            (0.5 * internal + 0.3 * finance + 0.2 * inf) / 100.0,
            3,
        ),
        "preferred_domains": preferred[:4],
        "phase_narrative_style": party,
    }


def build_catalog_from_ministers(ministers: List[Minister]) -> Dict[str, Any]:
    entries = []
    for m in ministers or []:
        nm = (m.name or "").strip()
        if not nm:
            continue
        entries.append(_minister_entry(m))
    entries.sort(key=lambda x: float(x.get("anti_corruption_bias") or 0), reverse=True)
    return {"version": 1, "scenario": "song", "ministers": entries}


def write_catalog(ministers: List[Minister]) -> Path:
    cat = build_catalog_from_ministers(ministers)
    _CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CATALOG_PATH.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
    return _CATALOG_PATH


def load_catalog(*, ministers: Optional[List[Minister]] = None, refresh: bool = False) -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE
    if ministers:
        cat = build_catalog_from_ministers(ministers)
        try:
            write_catalog(ministers)
        except OSError:
            pass
        _CACHE = cat
        return cat
    if _CATALOG_PATH.is_file():
        _CACHE = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        return _CACHE
    _CACHE = {"version": 1, "ministers": []}
    return _CACHE


def get_minister_profile(name: str, *, ministers: Optional[List[Minister]] = None) -> Optional[Dict[str, Any]]:
    nm = (name or "").strip()
    if not nm:
        return None
    cat = load_catalog(ministers=ministers)
    for row in cat.get("ministers") or []:
        if str(row.get("name") or "").strip() == nm:
            return dict(row)
    if ministers:
        for m in ministers:
            if (m.name or "").strip() == nm:
                return _minister_entry(m)
    return None


def abilities_from_profile(
    profile: Dict[str, Any],
    executor_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """合并大臣表模版与 runtime executor_ctx。"""
    w = dict(profile.get("ability_weights") or {})
    if executor_ctx:
        ab = executor_ctx.get("abilities") or {}
        if isinstance(ab, dict) and ab:
            internal = float(ab.get("internal", 50.0)) / 100.0
            military = float(ab.get("military", 50.0)) / 100.0
            finance = float(ab.get("finance", 50.0)) / 100.0
            inf = float(executor_ctx.get("influence", profile.get("influence", 50.0))) / 100.0
            return {
                "integrity": max(0.0, min(1.0, internal)),
                "governance": max(0.0, min(1.0, 0.5 * internal + 0.5 * finance)),
                "political_power": max(0.0, min(1.0, inf)),
                "execution": max(0.0, min(1.0, military)),
            }
    return {k: max(0.0, min(1.0, float(v))) for k, v in w.items()}


def compute_A_with_weights(abilities: Dict[str, float], weights: Dict[str, float]) -> float:
    if not weights:
        from task_system.delegation_resolver import compute_A_anti_corruption

        return compute_A_anti_corruption(abilities)
    total = 0.0
    wsum = 0.0
    for k, wf in weights.items():
        try:
            w = float(wf)
        except (TypeError, ValueError):
            continue
        if w <= 0:
            continue
        total += float(abilities.get(k, 0.5)) * w
        wsum += w
    if wsum <= 0:
        return 0.5
    return total / wsum


def party_bias_adjustment(profile: Optional[Dict[str, Any]], metrics: Dict[str, float]) -> float:
    """党争环境下新/旧党承办肃贪的额外难度项（加到 D 侧）。"""
    if not profile:
        return 0.0
    mult = float(profile.get("party_backlash_multiplier") or 1.0)
    if mult <= 1.0:
        return 0.0
    from task_system.metric_alignment import metric_value

    unr = float(metric_value(metrics, "unrest", 30.0)) / 100.0
    return min(0.12, 0.04 * (mult - 1.0) * (0.5 + unr))


def top_ministers_for_anti_corruption(
    ministers: List[Minister],
    *,
    limit: int = 5,
    exclude: Optional[set] = None,
) -> List[Minister]:
    ex = exclude or set()
    pool = [m for m in ministers if (m.name or "").strip() and m.name not in ex]
    cat = load_catalog(ministers=ministers if pool else None)
    bias_by_name = {
        str(r.get("name") or ""): float(r.get("anti_corruption_bias") or 0)
        for r in (cat.get("ministers") or [])
    }

    def score(m: Minister) -> float:
        return bias_by_name.get(m.name, float(m.ability_internal or 0) / 100.0)

    pool.sort(key=score, reverse=True)
    return pool[:limit]
