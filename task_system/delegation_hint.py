# -*- coding: utf-8 -*-
"""从诏书解析 trace + 原文推断：默认行政机器 vs 具名委派下季结算。"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

# 与 INTENT_CATALOG strict_governance 语义对齐的首发行动
ANTI_CORRUPTION_KW = re.compile(
    r"(肃贪|反贪|整治贪|贪官|贪吏|吏治腐败|整饬吏治|严查.*贪|清查.*贪)"
)


def _extract_l3_intent(trace: Dict[str, Any]) -> str:
    for st in reversed(trace.get("stages") or []):
        if not isinstance(st, dict):
            continue
        if st.get("layer") != "layer3_llm":
            continue
        dsl = st.get("dsl") or {}
        if isinstance(dsl, dict):
            intent = str(dsl.get("intent") or "").strip()
            if intent:
                return intent
    return ""


def default_phases_total() -> int:
    raw = (os.getenv("DELEGATION_PHASES_TOTAL") or "1").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 1
    return max(1, min(5, n))


def compute_delegation_hint(
    *,
    edict_text: str,
    parse_trace: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    未命中肃贪类：返回 None。
    命中且具名承办：mode=named_delegation（弱当季数值 + 入队 + 下季/多阶段结算）。
    命中但无具名：mode=default_machine（全量诏书数值 + 弱因果叙事轨，不入队）。
    """
    trace = parse_trace or {}
    ex = trace.get("executor_resolution") or {}
    name = str(ex.get("name") or "").strip()

    intent = _extract_l3_intent(trace)
    text = (edict_text or "").strip()

    anti = False
    if intent == "strict_governance":
        anti = True
    if ANTI_CORRUPTION_KW.search(text):
        anti = True

    if not anti:
        return None

    if name:
        return {
            "mode": "named_delegation",
            "action_id": "anti_corruption",
            "executor_name": name,
            "l3_intent": intent,
            "phases_total": default_phases_total(),
        }
    return {
        "mode": "default_machine",
        "action_id": "anti_corruption",
        "executor_name": "",
        "l3_intent": intent,
    }
