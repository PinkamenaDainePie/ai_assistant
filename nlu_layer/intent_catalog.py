# -*- coding: utf-8 -*-
"""诏书意图目录（数据驱动）；effects 仅供 legacy 数值路径，NLU 不消费。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# 与 edict_execution_frame.domain_catalog._INTENT_DOMAIN_HINT 对齐（仅强映射）
INTENT_DOMAIN_HINT: Dict[str, str] = {
    "strict_governance": "anti_corruption",
    "disaster_relief": "disaster_relief",
    "tax_relief": "fiscal",
    "welfare": "disaster_relief",
}

INTENT_CATALOG: List[Dict[str, Any]] = [
    {
        "intent": "allocate_funds",
        "categories": ("internal", "diplomacy", "other"),
        "phrases": ["给他们发", "拨给", "拨银", "拨款", "赈银", "发五万两"],
        "effects": [("treasury_balance", -60000), ("public_support", 1.0), ("unrest", -0.8)],
    },
    {
        "intent": "tax_relief",
        "categories": ("internal", "other"),
        "phrases": ["蠲免赋税", "减税", "免税", "宽征", "停征", "减免钱粮", "减免徭役"],
        "effects": [("treasury_balance", -100000), ("public_support", 3.0), ("unrest", -2.0)],
    },
    {
        "intent": "raise_tax",
        "categories": ("internal", "other"),
        "phrases": ["加税", "加派", "加征", "增税", "增征"],
        "effects": [("treasury_balance", 100000), ("public_support", -3.0), ("unrest", 2.0)],
    },
    {
        "intent": "inner_spending",
        "categories": ("internal", "other"),
        "phrases": ["内帑", "内库", "内府"],
        "effects": [("inner_treasury_balance", -80000), ("public_support", 0.5)],
    },
    {
        "intent": "strict_governance",
        "categories": ("internal", "other", "military"),
        "phrases": ["严查", "整饬", "肃贪", "严禁横敛", "清查田亩"],
        "effects": [("treasury_balance", 70000), ("public_support", -0.5), ("unrest", 1.0)],
    },
    {
        "intent": "disaster_relief",
        "categories": ("internal", "other"),
        "phrases": ["赈济", "赈灾", "开仓", "救灾", "救济饥民", "给散", "抚恤灾民"],
        "effects": [("treasury_balance", -70000), ("public_support", 3.0), ("unrest", -3.0)],
    },
    {
        "intent": "welfare",
        "categories": ("internal", "other"),
        "phrases": ["抚恤", "恩恤", "赐赈", "赈恤"],
        "effects": [("treasury_balance", -50000), ("public_support", 2.0), ("unrest", -1.0)],
    },
    {
        "intent": "military_expand",
        "categories": ("military", "other"),
        "phrases": ["募兵", "扩军", "练兵", "增兵", "补饷", "边备"],
        "effects": [("treasury_balance", -120000), ("fiscal_pressure", 1.2), ("unrest", 0.6)],
    },
    {
        "intent": "military_downsize",
        "categories": ("military", "other"),
        "phrases": ["裁军", "撤兵", "减兵", "汰兵"],
        "effects": [("treasury_balance", 80000), ("unrest", 1.0)],
    },
    {
        "intent": "navy_ops",
        "categories": ("military", "diplomacy", "other"),
        "phrases": ["水师", "造船", "海防", "海军", "战船"],
        "effects": [("treasury_balance", -120000), ("fiscal_pressure", 0.8)],
    },
    {
        "intent": "peace_and_trade",
        "categories": ("diplomacy", "other"),
        "phrases": ["和议", "修好", "互市", "通商", "罢兵", "通好"],
        "effects": [("public_support", 1.2), ("unrest", -1.2), ("fiscal_pressure", -0.6)],
    },
    {
        "intent": "diplomacy_tribute",
        "categories": ("diplomacy", "other"),
        "phrases": ["纳贡", "岁币", "进贡", "赐赉", "赏赉", "和亲", "册封"],
        "effects": [("treasury_balance", -80000), ("fiscal_pressure", 0.6), ("public_support", -0.4)],
    },
    {
        "intent": "mixed_military_internal",
        "categories": ("military", "internal", "other"),
        "phrases": ["边备不可废", "军民两安", "增练乡兵", "减免钱粮", "减免徭役"],
        "effects": [("treasury_balance", -90000), ("public_support", 1.0), ("fiscal_pressure", 0.8)],
    },
]

# 板块关键词 → 领域提示（原 L1 领域信号，不产数值）
DOMAIN_KEYWORD_HINTS: List[Tuple[str, str]] = [
    ("灾区", "disaster_relief"),
    ("灾荒", "disaster_relief"),
    ("赈", "disaster_relief"),
    ("饥", "disaster_relief"),
    ("水患", "disaster_relief"),
    ("堤防", "engineering"),
    ("河工", "engineering"),
    ("肃贪", "anti_corruption"),
    ("贪墨", "anti_corruption"),
    ("吏治", "anti_corruption"),
    ("讨伐", "military"),
    ("进兵", "military"),
    ("边防", "military"),
    ("和议", "diplomacy"),
    ("通商", "diplomacy"),
    ("河工", "engineering"),
    ("堤防", "engineering"),
    ("劝农", "agriculture"),
    ("农桑", "agriculture"),
]

QA_INTENT_RULES: List[Dict[str, Any]] = [
    {"id": "draft_decree", "patterns": [r"(拟诏|草诏|诏书|圣旨|该怎么写)"]},
    {"id": "predict_effect", "patterns": [r"(后果|数值|会如何|预测)"]},
    {"id": "compare_policy", "patterns": [r"(比较|还是|孰优)"]},
    {"id": "recommend_policy", "patterns": [r"(该不该|是否|宜否|当否|如何处置|怎么办|卿以为)"]},
    {"id": "challenge_policy", "patterns": [r"(质疑|不妥|过急|过缓)"]},
    {"id": "explain_state", "patterns": [r"(局势|国情|为何|何以至此)"]},
]

QA_DOMAIN_RULES: List[Tuple[str, str]] = [
    (r"(贪|腐|吏治|肃清)", "anti_corruption"),
    (r"(军|兵|边防)", "military"),
    (r"(税|赋|国库|钱粮)", "treasury"),
    (r"(灾|赈|饥)", "disaster_relief"),
]


def domain_hint_for_intent(intent_id: str) -> str:
    return INTENT_DOMAIN_HINT.get((intent_id or "").strip(), "general")
