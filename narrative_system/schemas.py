# -*- coding: utf-8 -*-
"""QuarterSettlementSummary — 季度结算摘要 IR（叙事层唯一输入）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MetricDelta:
    key: str
    label_zh: str
    value_from: float
    value_to: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label_zh": self.label_zh,
            "from": round(self.value_from, 2),
            "to": round(self.value_to, 2),
            "delta": round(self.value_to - self.value_from, 2),
        }


@dataclass
class NodeBrief:
    id: str
    title_zh: str
    status: str
    progress: int
    delta_progress: int = 0
    branch: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title_zh": self.title_zh,
            "status": self.status,
            "progress": self.progress,
            "delta_progress": self.delta_progress,
            "branch": self.branch,
        }


@dataclass
class OutlookItem:
    kind: str
    hint_zh: str
    ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"kind": self.kind, "hint_zh": self.hint_zh}
        if self.ref:
            d["ref"] = self.ref
        return d


@dataclass
class QuarterSettlementSummary:
    """上一玩家季的权威事实包；叙事 LLM 只读此结构。"""

    reporting_quarter_index: int
    quarter_label_zh: str
    new_quarter_label_zh: str = ""

    edict_issued: bool = False
    edict_text: str = ""
    edict_summary_zh: str = ""
    decree_track: str = ""

    node_briefs: List[NodeBrief] = field(default_factory=list)
    metrics_delta: List[MetricDelta] = field(default_factory=list)
    settled_tasks: List[Dict[str, Any]] = field(default_factory=list)
    auto_fact_narratives: List[str] = field(default_factory=list)
    pending_event: Dict[str, Any] = field(default_factory=dict)
    new_tasks: List[Dict[str, Any]] = field(default_factory=list)
    outlook: List[OutlookItem] = field(default_factory=list)
    war_arcs: Dict[str, Any] = field(default_factory=dict)
    crisis_metrics: List[str] = field(default_factory=list)

    # AgentFlow integration (stage 1): proposals and narrative seeds only; no WorldState mutation
    agent_actions: List[Dict[str, Any]] = field(default_factory=list)
    agent_proposed_deltas: List[MetricDelta] = field(default_factory=list)
    agent_narrative_bundle: Dict[str, Any] = field(default_factory=dict)
    # Agent B：本季全部诏书动作 + Agent A 入参选取 trace
    quarter_edict_actions: List[Dict[str, Any]] = field(default_factory=list)
    agent_a_selection: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reporting_quarter_index": self.reporting_quarter_index,
            "quarter_label_zh": self.quarter_label_zh,
            "new_quarter_label_zh": self.new_quarter_label_zh,
            "edict_issued": self.edict_issued,
            "edict_text": self.edict_text,
            "edict_summary_zh": self.edict_summary_zh,
            "decree_track": self.decree_track,
            "node_briefs": [n.to_dict() for n in self.node_briefs],
            "metrics_delta": [m.to_dict() for m in self.metrics_delta],
            "settled_tasks": list(self.settled_tasks),
            "auto_fact_narratives": list(self.auto_fact_narratives),
            "pending_event": dict(self.pending_event),
            "new_tasks": list(self.new_tasks),
            "outlook": [o.to_dict() for o in self.outlook],
            "war_arcs": dict(self.war_arcs),
            "crisis_metrics": list(self.crisis_metrics),
            "agent_actions": list(self.agent_actions),
            "agent_proposed_deltas": [m.to_dict() for m in self.agent_proposed_deltas],
            "agent_narrative_bundle": dict(self.agent_narrative_bundle),
            "quarter_edict_actions": list(self.quarter_edict_actions),
            "agent_a_selection": dict(self.agent_a_selection),
        }
