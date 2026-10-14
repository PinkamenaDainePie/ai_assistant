# -*- coding: utf-8 -*-
"""SemanticFrame → 若干 PolicyActionCandidate（规则模板为主）。"""
from __future__ import annotations

import re
from typing import List

from .policy_ir import PolicyActionCandidate, SemanticFrame

_slug_safe = re.compile(r"[^a-zA-Z0-9_\u4e00-\u9fff]+")


def _slug(s: str) -> str:
    t = _slug_safe.sub("_", (s or "").strip()).strip("_")
    return t[:48] or "candidate"


def generate_policy_candidates(
    *,
    semantic_frame: SemanticFrame,
    edict_text: str,
) -> List[PolicyActionCandidate]:
    """生成 3～6 个候选；首版以模板为主。"""
    text = (edict_text or "").strip()
    if semantic_frame.domain == "anti_corruption":
        return _gen_anti_corruption(semantic_frame, text)
    return _gen_generic(semantic_frame, text)


def _gen_anti_corruption(frame: SemanticFrame, text: str) -> List[PolicyActionCandidate]:
    base = _slug(text)[:20] or "anti"
    out: List[PolicyActionCandidate] = []

    out.append(
        PolicyActionCandidate(
            candidate_id=f"{base}_default_routine",
            source="edict",
            domain="anti_corruption",
            action_type="default_machine",
            title_zh="交由有司按例清查",
            summary_zh="御史台与户部循例照刷，不强调名臣出面；积弊稍抑而反弹有限。",
            executor="",
            executor_mode="default_officials",
            intensity="medium",
            policy_style="moderate",
            target_metrics=["corruption", "fiscal_pressure", "authority"],
            expected_effect_profile={
                "corruption": "down_small",
                "fiscal_pressure": "up_small",
                "authority": "neutral",
            },
            risk_tags=["low_efficiency"],
        )
    )
    out.append(
        PolicyActionCandidate(
            candidate_id=f"{base}_strict_bureaucracy",
            source="edict",
            domain="anti_corruption",
            action_type="default_machine",
            title_zh="严行查办地方贪墨",
            summary_zh="通饬州县限期自陈，违者参劾；肃贪较力，然胥吏与豪强阻力上升。",
            executor="",
            executor_mode="default_officials",
            intensity="high",
            policy_style="strict",
            target_metrics=["corruption", "unrest", "fiscal_pressure", "authority"],
            expected_effect_profile={
                "corruption": "down_medium",
                "fiscal_pressure": "up_medium",
                "unrest": "up_small",
                "authority": "up_small",
            },
            risk_tags=["bureaucratic_resistance"],
        )
    )

    hint = (frame.executor_hint or "").strip()
    if hint:
        out.append(
            PolicyActionCandidate(
                candidate_id=f"{base}_named_{_slug(hint)}",
                source="edict",
                domain="anti_corruption",
                action_type="named_execution",
                title_zh=f"命{hint}主理肃贪",
                summary_zh=f"责成{hint}亲裁案牍，威势较足；成效可期，弹劾与地方怨谤亦随之。",
                executor=hint,
                executor_mode="single",
                intensity="high",
                policy_style="strict",
                target_metrics=["corruption", "treasury_balance", "authority", "unrest"],
                expected_effect_profile={
                    "corruption": "down_strong",
                    "treasury_balance": "up_small",
                    "authority": "up_medium",
                    "unrest": "up_small",
                },
                risk_tags=["court_impeachment", "local_elite_backlash"],
            )
        )
    else:
        out.append(
            PolicyActionCandidate(
                candidate_id=f"{base}_named_placeholder",
                source="edict",
                domain="anti_corruption",
                action_type="named_execution",
                title_zh="简拔清廉重臣专领一案",
                summary_zh="请陛下于朝中点名能员，专责查办；未点名前仅作预备。",
                executor="",
                executor_mode="single",
                intensity="medium",
                policy_style="institutional",
                target_metrics=["corruption", "authority"],
                expected_effect_profile={
                    "corruption": "down_medium",
                    "authority": "up_small",
                },
                risk_tags=["pending_executor"],
            )
        )

    # 缓和路径
    out.append(
        PolicyActionCandidate(
            candidate_id=f"{base}_soft_audit",
            source="edict",
            domain="anti_corruption",
            action_type="default_machine",
            title_zh="先清账册、缓施刑罚",
            summary_zh="以勾销积欠、澄清吏案为先，不骤兴大狱；腐败缓降，民怨亦较平。",
            executor="",
            executor_mode="default_officials",
            intensity="low",
            policy_style="soft",
            target_metrics=["corruption", "public_support", "fiscal_pressure"],
            expected_effect_profile={
                "corruption": "down_small",
                "public_support": "up_small",
                "fiscal_pressure": "up_small",
            },
            risk_tags=["slow_progress"],
        )
    )

    # 与 frame 强度对齐的变体（凑足数量且增加差异）
    if frame.intensity == "high":
        out.append(
            PolicyActionCandidate(
                candidate_id=f"{base}_shock_campaign",
                source="edict",
                domain="anti_corruption",
                action_type="default_machine",
                title_zh="雷厉风行、限期揭帖",
                summary_zh="诏书中已有峻急之意，地方震慑强而反噬风险高。",
                executor="",
                executor_mode="default_officials",
                intensity="high",
                policy_style="strict",
                target_metrics=["corruption", "unrest", "revolt_risk"],
                expected_effect_profile={
                    "corruption": "down_strong",
                    "unrest": "up_medium",
                    "revolt_risk": "up_small",
                },
                risk_tags=["social_tension"],
            )
        )

    return out[:6]


def _gen_generic(frame: SemanticFrame, text: str) -> List[PolicyActionCandidate]:
    base = _slug(text)[:20] or "gen"
    dom = frame.domain or "general"
    return [
        PolicyActionCandidate(
            candidate_id=f"{base}_steady",
            source="edict",
            domain=dom,
            action_type="default_machine",
            title_zh="稳步推行政务",
            summary_zh="就现有诏意作常规落实，不另起炉灶。",
            executor="",
            executor_mode="default_officials",
            intensity="medium",
            policy_style="moderate",
            target_metrics=["public_support", "fiscal_pressure"],
            expected_effect_profile={
                "public_support": "up_small",
                "fiscal_pressure": "neutral",
            },
            risk_tags=[],
        ),
        PolicyActionCandidate(
            candidate_id=f"{base}_lean",
            source="edict",
            domain=dom,
            action_type="default_machine",
            title_zh="节用宽政",
            summary_zh="略抑征敛、安抚舆情，国库略减而民心稍固。",
            executor="",
            executor_mode="default_officials",
            intensity="low",
            policy_style="soft",
            target_metrics=["treasury_balance", "public_support", "fiscal_pressure"],
            expected_effect_profile={
                "treasury_balance": "down_small",
                "public_support": "up_small",
                "fiscal_pressure": "down_small",
            },
            risk_tags=[],
        ),
    ]
