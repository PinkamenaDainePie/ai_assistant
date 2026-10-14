# -*- coding: utf-8 -*-
"""
固定开局指标（战役初始盘面）。

与 frontend/game/mockData.ts 中 mockNationState 六维展示对齐；
国库按前端约定：UI 0–100 对应 treasury_balance = ui * 30000（两）。

可通过环境变量 NUMERIC_USE_FIXED_INITIAL=0 关闭（仍用表格推算 init_state）。
"""
from __future__ import annotations

import os
from typing import Dict

from .types import QuarterState

# 默认开启固定开局；设为 0/false/no 则沿用 QuarterEngine.init_state() 表格推算
USE_FIXED_INITIAL_METRICS: bool = os.getenv(
    "NUMERIC_USE_FIXED_INITIAL", "1"
).strip().lower() not in ("0", "false", "no")

# UI treasury 48 → 与 frontend nationMetricsToApiPayload 一致
_TREASURY_UI = 48.0

FIXED_INITIAL_METRICS: Dict[str, float] = {
    "treasury_balance": _TREASURY_UI * 30000.0,
    "inner_treasury_balance": 900000.0,
    "public_support": 55.0,
    "unrest": 28.0,
    "fiscal_pressure": 30.0,
    "disaster_index": 18.0,
    "tax_completion_index": 42.0,
    "tax_intensity": 52.0,
    "army_morale": 62.0,
    "army_supply": 62.0,
    "navy_morale": 62.0,
    "navy_supply": 62.0,
    "revolt_risk": 35.0,
    "corruption": 38.0,
    "authority": 60.0,
}


def apply_fixed_initial_metrics(state: QuarterState) -> None:
    """用固定常量覆盖当前 state.metrics（用于新会话开局）。"""
    for k, v in FIXED_INITIAL_METRICS.items():
        state.metrics[str(k)] = round(float(v), 4)
