# -*- coding: utf-8 -*-
"""国策图 IR：节点定义、边定义、运行时状态、季度 tick 结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


NODE_STATUSES = frozenset(
    {"locked", "available", "active", "completed", "suspended", "failed"}
)

EDGE_TYPES = frozenset(
    {
        "requires",
        "unlocks",
        "contributes",
        "completes",
        "conflicts",
        "risk_triggers",
        "advances",
    }
)


@dataclass
class PolicyNodeDef:
    id: str
    title_zh: str
    branch: str = "general"
    kind: str = "reform"  # milestone | reform | auto | risk
    initial_status: str = "locked"
    linked_main_id: str = ""
    linked_flag: str = ""
    passive_effects_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    progress_max: int = 100


@dataclass
class PolicyEdgeDef:
    id: str
    from_id: str
    to_id: str
    edge_type: str
    condition: Dict[str, Any] = field(default_factory=dict)
    effect: Dict[str, Any] = field(default_factory=dict)
    probability: float = 0.0


@dataclass
class PolicyGraphCatalog:
    scenario: str
    nodes: Dict[str, PolicyNodeDef]
    edges: List[PolicyEdgeDef]


@dataclass
class PolicyNodeRuntime:
    status: str = "locked"
    progress: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "progress": int(self.progress)}

    @classmethod
    def from_dict(cls, raw: Any) -> "PolicyNodeRuntime":
        if not isinstance(raw, dict):
            return cls()
        st = str(raw.get("status") or "locked").strip()
        if st not in NODE_STATUSES:
            st = "locked"
        return cls(status=st, progress=int(raw.get("progress") or 0))


@dataclass
class PolicyTreeState:
    nodes: Dict[str, PolicyNodeRuntime] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {nid: rt.to_dict() for nid, rt in (self.nodes or {}).items()}

    @classmethod
    def from_dict(cls, raw: Any) -> "PolicyTreeState":
        out = cls()
        if not isinstance(raw, dict):
            return out
        for nid, val in raw.items():
            out.nodes[str(nid)] = PolicyNodeRuntime.from_dict(val)
        return out

    def get(self, node_id: str) -> PolicyNodeRuntime:
        nid = str(node_id or "").strip()
        if nid not in self.nodes:
            self.nodes[nid] = PolicyNodeRuntime()
        return self.nodes[nid]


@dataclass
class PolicyNodeUpdate:
    node_id: str
    status: str = ""
    progress_delta: int = 0
    progress: Optional[int] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"node_id": self.node_id}
        if self.status:
            d["status"] = self.status
        if self.progress_delta:
            d["progress_delta"] = self.progress_delta
        if self.progress is not None:
            d["progress"] = self.progress
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass
class PolicyTreeTickResult:
    node_updates: List[PolicyNodeUpdate] = field(default_factory=list)
    flags_delta: Dict[str, bool] = field(default_factory=dict)
    passive_effects: List[Dict[str, Any]] = field(default_factory=list)
    unlocked_playbooks: List[Dict[str, str]] = field(default_factory=list)
    risk_event_candidates: List[Dict[str, Any]] = field(default_factory=list)
    advances_fired: List[Dict[str, Any]] = field(default_factory=list)
    task_status_updates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_updates": [u.to_dict() for u in self.node_updates],
            "flags_delta": dict(self.flags_delta),
            "passive_effects": list(self.passive_effects),
            "unlocked_playbooks": list(self.unlocked_playbooks),
            "risk_event_candidates": list(self.risk_event_candidates),
            "advances_fired": list(self.advances_fired),
            "task_status_updates": list(self.task_status_updates),
        }
