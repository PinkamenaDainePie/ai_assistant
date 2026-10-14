# -*- coding: utf-8 -*-
"""动作流 DST 与次生影响结构化 IR。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ActionRef(BaseModel):
    """本轮被分析的主动作（诏书/任务/事件择一）。"""

    model_config = ConfigDict(extra="ignore")

    action_kind: str = "edict"
    domain: str = ""
    task_key: str = ""
    edict_text: str = ""
    frame_id: str = ""
    resolution_status: str = ""
    primary_task: Dict[str, str] = Field(default_factory=dict)


class UserAction(BaseModel):
    """玩家侧动作（诏书提交、选项、委派等）。"""

    model_config = ConfigDict(extra="ignore")

    channel: str = "edict"
    raw_text: str = ""
    choice_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemAction(BaseModel):
    """系统侧已裁决动作（resolver / simulation 产出摘要）。"""

    model_config = ConfigDict(extra="ignore")

    action_type: str = "resolve_edict"
    summary_zh: str = ""
    applied_effect_keys: List[str] = Field(default_factory=list)
    task_path: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyNodeView(BaseModel):
    id: str = ""
    title_zh: str = ""
    status: str = ""
    progress: int = 0


class ActionFlowState(BaseModel):
    """DST：动作推演上下文（非大臣聊天历史）。"""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    quarter_index: int = 0
    active_node_id: Optional[str] = None
    task_state: List[Dict[str, Any]] = Field(default_factory=list)
    policy_nodes: List[PolicyNodeView] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    flags: Dict[str, Any] = Field(default_factory=dict)
    last_edict_text: str = ""
    former_action: str = ""
    last_user_action: Optional[UserAction] = None
    last_system_action: Optional[SystemAction] = None
    last_primary_action: Optional[ActionRef] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActorResponseSketch(BaseModel):
    """「他人回应」草案：派系/大臣/地方反应，供叙事或下季事件参考。"""

    actor_id: str = ""
    actor_label_zh: str = ""
    stance: str = ""
    response_zh: str = ""
    pressure_tags: List[str] = Field(default_factory=list)


class SecondaryPressure(BaseModel):
    key: str = ""
    label_zh: str = ""
    region_id: str = ""
    magnitude: str = "medium"
    narrative_zh: str = ""


class AgentFlowProposals(BaseModel):
    """Workflow A 可落地提案（由 quarter_settle 校验后并入 effect_pool）。"""

    model_config = ConfigDict(extra="ignore")

    metric_deltas: List[Dict[str, Any]] = Field(default_factory=list)
    flag_mutations: List[Dict[str, Any]] = Field(default_factory=list)
    # 战争场景：地区状态变更（仅 military 域或战弧激活时落地）
    state_effects: List[Dict[str, Any]] = Field(default_factory=list)


class SecondaryEffectsReport(BaseModel):
    """agent-flow 终端输出：次生影响提案（须由模拟层校验后落地）。"""

    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    quarter_index: int = 0
    primary_action: ActionRef = Field(default_factory=ActionRef)
    secondary_signals: List[str] = Field(default_factory=list)
    secondary_pressures: List[SecondaryPressure] = Field(default_factory=list)
    actor_responses: List[ActorResponseSketch] = Field(default_factory=list)
    delayed_risk_seeds: List[Dict[str, Any]] = Field(default_factory=list)
    narrative_seed_zh: str = ""
    proposals: AgentFlowProposals = Field(default_factory=AgentFlowProposals)
    trace: Dict[str, Any] = Field(default_factory=dict)
