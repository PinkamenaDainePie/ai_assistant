# -*- coding: utf-8 -*-
"""EdictExecutionFrame：诏书归一后的唯一执行框架（Python 3.7 兼容，不用 typing.Literal）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutorSpec(BaseModel):
    """承办方：机构、具名单人、或双人臣工。"""

    model_config = ConfigDict(extra="ignore")

    mode: str = Field(
        default="institution",
        description="institution|person|dual_person",
    )
    display_name_zh: str = ""
    person_name: str = Field(default="", description="单人时非空；双人时常为空")
    person_names: List[str] = Field(default_factory=list, description="双人时点两名，顺序与诏书一致")
    institution_key: str = Field(default="", description="内部 slug，可为空")
    is_inferred: bool = False


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str = ""
    task_key: str = ""
    title_zh: str = ""


class DurationSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quarters: int = Field(default=1, ge=1, le=5)
    is_inferred: bool = False


class LocationSlot(BaseModel):
    """可选地点槽位；affects_numbers 须由 resolver 计算（见 location_slot.apply_location_target_to_frame）。"""

    model_config = ConfigDict(extra="ignore")

    mode: str = Field(default="unknown", description="unknown|explicit|inferred")
    location_id: str = ""
    location_name_zh: str = ""
    scope_type: str = Field(default="unknown", description="province|river_segment|…")
    source_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    affects_numbers: bool = False


class TargetEntitySlot(BaseModel):
    """讨伐 / 外邦等目标对象；与 LocationSlot 可共存（v0.2.1）。"""

    model_config = ConfigDict(extra="ignore")

    mode: str = Field(default="unknown", description="unknown|explicit|inferred")
    entity_id: str = ""
    entity_name_zh: str = ""
    entity_kind: str = Field(default="", description="war_target|foreign_polity|vassal|other")
    source_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EdictExecutionFrame(BaseModel):
    """唯一对外主 IR：派谁 / 做什么 / 花多久。"""

    model_config = ConfigDict(extra="ignore")

    frame_id: str = ""
    explicitness_class: str = Field(default="D", description="A|B|C|D")
    executor: ExecutorSpec = Field(default_factory=ExecutorSpec)
    task: TaskSpec = Field(default_factory=TaskSpec)
    duration: DurationSpec = Field(default_factory=DurationSpec)
    intensity: str = Field(default="medium", description="low|medium|high")
    risk_tags: List[str] = Field(default_factory=list)
    expected_effect_profile: Dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    normalized_command_zh: str = ""
    is_auto_completed: bool = Field(default=False, description="是否由系统自动补全槽位")
    completion_notes_zh: str = Field(default="", description="自动补全说明（可追溯）")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    legacy_eligible: bool = Field(
        default=False,
        description="单人具名肃贪可走 legacy_delegation_only（与 edict_execution 互斥）",
    )
    # 解析门控（通用委托 + 澄清）
    resolution_status: str = Field(
        default="resolved",
        description="resolved|auto_completed|needs_clarification",
    )
    ambiguity_status: str = Field(default="none", description="none|low|high")
    domain_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    task_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    executor_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    duration_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    clarification_options: List[Dict[str, Any]] = Field(default_factory=list)
    blocked_reasons: List[str] = Field(default_factory=list)
    task_meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="catalog 委托元信息：ability_weights、narrative_mode、risk_tags 等",
    )
    location: LocationSlot = Field(default_factory=LocationSlot)
    target_entity: TargetEntitySlot = Field(default_factory=TargetEntitySlot)


class FrameBuildTrace(BaseModel):
    """调试与 shadow 轨迹；内部候选默认不返回给前端。"""

    model_config = ConfigDict(extra="ignore")

    mode: str = ""
    explicitness_class: str = ""
    original_text: str = ""
    final_frame: Optional[Dict[str, Any]] = None
    final_frame_narrative: str = ""
    resolved_effects: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_pack: Dict[str, Any] = Field(default_factory=dict)
    select_applied: bool = False
    internal_candidates: Optional[List[Dict[str, Any]]] = None
    rejected: Optional[List[Dict[str, Any]]] = None
    priority_trace: Optional[List[str]] = None
    admissibility_notes: Optional[List[str]] = None
    error: str = ""
