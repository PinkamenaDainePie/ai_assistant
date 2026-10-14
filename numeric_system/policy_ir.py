# -*- coding: utf-8 -*-
"""Typed IR：SemanticFrame + PolicyActionCandidate（LLM 不直接产出最终数值）。"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EffectProfileTier(str, Enum):
    down_strong = "down_strong"
    down_medium = "down_medium"
    down_small = "down_small"
    neutral = "neutral"
    up_small = "up_small"
    up_medium = "up_medium"
    up_strong = "up_strong"


class SemanticFrame(BaseModel):
    """诏书/问答语义框架（非数值）。"""

    domain: str = Field(
        ...,
        description="政务领域，如 anti_corruption、internal、general",
    )
    intent: str = Field(default="unspecified", description="与 L3 dsl.intent 或规则对齐的意图 id")
    target: str = Field(default="", description="作用对象简述，如 local_corruption")
    intensity: str = Field(default="medium", description="low|medium|high")
    executor_hint: str = Field(default="", description="承办人名或空")
    policy_style: str = Field(default="unknown", description="strict|moderate|soft|institutional|unknown")
    time_scope: str = Field(default="current_quarter", description="时间范围标签")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    raw_notes: str = Field(default="", description="调试附注")


class PolicyActionCandidate(BaseModel):
    """候选政务行动（定向量效果由 resolver 计算）。"""

    candidate_id: str
    source: str = Field(default="edict", description="edict|minister_advice")
    domain: str
    action_type: str = Field(default="policy_bundle", description="如 named_execution / default_machine")
    title_zh: str
    summary_zh: str = ""
    executor: str = ""
    executor_mode: str = Field(default="default_officials", description="default_officials|single|none")
    intensity: str = Field(default="medium")
    policy_style: str = Field(default="moderate")
    target_metrics: List[str] = Field(default_factory=list)
    expected_effect_profile: Dict[str, str] = Field(
        default_factory=dict,
        description="metric_key 或逻辑名 -> EffectProfileTier 值",
    )
    risk_tags: List[str] = Field(default_factory=list)
    convert_to: List[str] = Field(default_factory=lambda: ["effects", "narrative"])

    @field_validator("expected_effect_profile", mode="before")
    @classmethod
    def _coerce_profile(cls, v: Any) -> Dict[str, str]:
        if not isinstance(v, dict):
            return {}
        out: Dict[str, str] = {}
        for k, val in v.items():
            key = str(k or "").strip()
            if not key:
                continue
            out[key] = str(val or "").strip() or "neutral"
        return out


class AdviceCandidatePayload(BaseModel):
    """大臣问答 JSON 块中单条候选（与 PolicyActionCandidate 字段对齐子集）。"""

    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    domain: str = "general"
    action_type: str = "minister_advice"
    title_zh: str = ""
    summary_zh: str = ""
    executor: str = ""
    executor_mode: str = Field(default="single")
    intensity: str = Field(default="medium")
    policy_style: str = Field(default="moderate")
    target_metrics: List[str] = Field(default_factory=list)
    expected_effect_profile: Dict[str, str] = Field(default_factory=dict)
    risk_tags: List[str] = Field(default_factory=list)

    def to_policy_candidate(self) -> PolicyActionCandidate:
        return PolicyActionCandidate(
            candidate_id=self.candidate_id,
            source="minister_advice",
            domain=self.domain,
            action_type=self.action_type,
            title_zh=self.title_zh,
            summary_zh=self.summary_zh,
            executor=self.executor,
            executor_mode=self.executor_mode,
            intensity=self.intensity,
            policy_style=self.policy_style,
            target_metrics=list(self.target_metrics),
            expected_effect_profile=dict(self.expected_effect_profile),
            risk_tags=list(self.risk_tags),
        )


class MinisterAdviceLLMBlock(BaseModel):
    """要求 LLM 输出的 JSON 根结构。"""

    model_config = ConfigDict(extra="ignore")

    answer_zh: str = ""
    stance: Dict[str, Any] = Field(default_factory=dict)
    advice_candidates: List[AdviceCandidatePayload] = Field(default_factory=list)
