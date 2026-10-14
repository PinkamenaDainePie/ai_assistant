# -*- coding: utf-8 -*-
"""指标中文名（季度纪要展示）。"""
from __future__ import annotations

METRIC_LABEL_ZH = {
    "treasury_balance": "国库",
    "inner_treasury_balance": "内帑",
    "public_support": "民心",
    "unrest": "动乱",
    "fiscal_pressure": "财政压力",
    "army_morale": "军心",
    "army_supply": "军需",
    "revolt_risk": "叛乱风险",
    "corruption": "贪腐",
    "authority": "权威",
    "tax_completion_index": "征管指数",
    "tax_intensity": "税负强度",
    "disaster_index": "灾异指数",
}


def metric_label_zh(key: str) -> str:
    return METRIC_LABEL_ZH.get(str(key or "").strip(), str(key or ""))
