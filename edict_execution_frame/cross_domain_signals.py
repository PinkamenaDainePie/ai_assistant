# -*- coding: utf-8 -*-
"""复合句：次要意图仅进 trace，不改变主域裁决（与专家 multi_intent_policy 一致）。"""
from __future__ import annotations

from typing import Any, Dict, List

# 赈灾侧显性词（与 catalog 关键词部分重叠，用于 secondary 检测）
_DR_SIGNAL = (
    "开仓",
    "赈济",
    "赈灾",
    "蠲免",
    "免赋",
    "抚恤",
    "救灾",
    "救济",
    "饥荒",
    "流民",
    "钦差",
    "巡抚",
    "就地赈",
    "放粮",
    "发仓",
    "灾荒",
    "水患",
    "大旱",
)

# 肃贪侧显性词
_AC_SIGNAL = (
    "肃贪",
    "反贪",
    "贪墨",
    "严查",
    "清查",
    "亏空",
    "侵吞",
    "严办",
    "查办",
    "贪腐",
    "吏治腐败",
    "贪官",
    "整饬吏治",
)

_RELIEF_FUNDS = ("赈银", "赈粮", "赈款")


def _has_any(text: str, needles: tuple) -> bool:
    t = text or ""
    return any(n and n in t for n in needles)


def infer_cross_domain_signals(
    edict_text: str,
    *,
    domain: str,
    task_key: str,
    resolution_status: str,
) -> Dict[str, Any]:
    """仅对 anti_corruption / disaster_relief 主域填充 secondary_signals（稳定、无随机）。"""
    dom = (domain or "").strip()
    tk = (task_key or "").strip()
    t = edict_text or ""
    has_dr = _has_any(t, _DR_SIGNAL)
    has_ac = _has_any(t, _AC_SIGNAL)
    has_rf = _has_any(t, _RELIEF_FUNDS)

    secondary: List[str] = []
    if dom == "anti_corruption":
        if has_dr:
            secondary.append("disaster_relief")
        if has_rf:
            secondary.append("relief_funds")
    elif dom == "disaster_relief":
        if has_ac:
            secondary.append("anti_corruption")

    # 去重保序
    seen = set()
    deduped = []
    for s in secondary:
        if s not in seen:
            seen.add(s)
            deduped.append(s)

    return {
        "primary_task": {"domain": dom, "task_key": tk},
        "secondary_signals": deduped,
        "multi_intent_policy": "single_primary_trace_only_no_secondary_effects",
        "resolution_status_echo": (resolution_status or "").strip() or "resolved",
    }
