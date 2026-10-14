# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


TaskStatus = str


@dataclass(frozen=True)
class TaskTemplate:
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    trigger_conditions: List[Dict[str, Any]] = field(default_factory=list)
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    penalties: List[Dict[str, Any]] = field(default_factory=list)
    stall_penalties_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    duration: int = 1
    priority: int = 50
    tags: List[str] = field(default_factory=list)
    mandatory: bool = False
    min_reign_year: int = 0


@dataclass
class TaskInstance:
    instance_id: str
    template_id: str
    title: str
    description: str
    category: str
    status: TaskStatus
    assigned_quarter: int
    deadline_quarter: int
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    penalties: List[Dict[str, Any]] = field(default_factory=list)
    stall_penalties_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    source: str = "system"
    # objectives: 按指标判定；delegation: 诏书委派，下季概率结算
    resolution_kind: str = "objectives"
    delegation: Dict[str, Any] = field(default_factory=dict)
    edict_execution: Dict[str, Any] = field(default_factory=dict)
    # 熙宁主线：flags/drift/playbook 等表驱动元数据
    campaign_meta: Dict[str, Any] = field(default_factory=dict)

