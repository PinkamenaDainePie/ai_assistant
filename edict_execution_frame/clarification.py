# -*- coding: utf-8 -*-
"""Playbook 槽位要求 → ClarificationIssue（替代散落 R9 词表）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from edict_execution_frame.schemas import EdictExecutionFrame, TargetEntitySlot


@dataclass
class ClarificationIssue:
    code: str
    field: str
    severity: str  # error | warning
    blocks_execution: bool
    blocks_numbers: bool
    message_zh: str
    candidate_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "severity": self.severity,
            "blocks_execution": self.blocks_execution,
            "blocks_numbers": self.blocks_numbers,
            "message_zh": self.message_zh,
            "candidate_values": list(self.candidate_values or []),
        }


def playbook_key(domain: str, task_key: str) -> str:
    return f"{domain or 'general'}:{task_key or ''}"


# slot_name -> spec；missing_behavior=clarify_if_keywords 时需命中 keywords 且槽位空才澄清
PLAYBOOK_SLOT_REQUIREMENTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    playbook_key("military", "campaign_against"): {
        "target_entity": {
            "missing_behavior": "clarify_if_keywords",
            "keywords": ["讨伐", "征讨", "开战", "进兵", "攻伐", "击贼"],
        }
    },
    playbook_key("diplomacy", "tributary_stability"): {
        "target_entity": {
            "missing_behavior": "clarify_if_keywords",
            "keywords": ["处置外事", "和议", "册封"],
        }
    },
}


def _target_entity_satisfied(te: TargetEntitySlot) -> bool:
    return bool((te.entity_name_zh or "").strip() or (te.entity_id or "").strip())


def evaluate_playbook_slot_issues(
    *,
    edict_text: str,
    domain: str,
    task_key: str,
    target_entity: TargetEntitySlot,
) -> List[ClarificationIssue]:
    """表驱动：无 playbook 配置则空列表。"""
    spec_all = PLAYBOOK_SLOT_REQUIREMENTS.get(playbook_key(domain, task_key)) or {}
    if not spec_all:
        return []
    t = edict_text or ""
    issues: List[ClarificationIssue] = []

    te_spec = spec_all.get("target_entity") or {}
    mb = str(te_spec.get("missing_behavior") or "")
    if mb == "clarify_if_keywords":
        kws = list(te_spec.get("keywords") or [])
        if any(k and k in t for k in kws) and not _target_entity_satisfied(target_entity):
            issues.append(
                ClarificationIssue(
                    code="MISSING_TARGET_ENTITY",
                    field="target_entity",
                    severity="error",
                    blocks_execution=True,
                    blocks_numbers=True,
                    message_zh="请补充讨伐或外交对象（部族、邦国或具体目标）。",
                    candidate_values=[],
                )
            )
    return issues


def get_target_entity_slot_policy(domain: str, task_key: str) -> Dict[str, Any]:
    """供 task_meta / 调试：当前 playbook 对外邦槽位的策略摘要。"""
    spec = (PLAYBOOK_SLOT_REQUIREMENTS.get(playbook_key(domain, task_key)) or {}).get("target_entity") or {}
    if not spec:
        return {"required_mode": "none", "keywords": []}
    return {
        "required_mode": str(spec.get("missing_behavior") or "none"),
        "keywords": list(spec.get("keywords") or []),
    }


def merge_slot_issues_into_frame_state(
    issues: List[ClarificationIssue],
    *,
    domain: str,
    task_key: str,
    current_status: str,
    existing_blocked: List[str],
    existing_clar: List[Dict[str, Any]],
) -> Tuple[str, List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """若有 blocks_execution，置 needs_clarification 并合并澄清项。"""
    blocked = list(existing_blocked or [])
    clar = list(existing_clar or [])
    dicts = [i.to_dict() for i in issues]
    rstatus = current_status or "resolved"
    blocking = [i for i in issues if i.blocks_execution]
    for iss in blocking:
        if rstatus in ("resolved", "auto_completed"):
            rstatus = "needs_clarification"
        if "playbook_slot_requirement" not in blocked:
            blocked.append("playbook_slot_requirement")
        if iss.code == "MISSING_TARGET_ENTITY" and "missing_target_entity_r9" not in blocked:
            blocked.append("missing_target_entity_r9")
        if iss.code == "MISSING_LOCATION" and "missing_location_scope" not in blocked:
            blocked.append("missing_location_scope")
        if iss.code == "OVERBROAD_SCOPE" and "overbroad_scope" not in blocked:
            blocked.append("overbroad_scope")
        if iss.code == "MISSING_HOSTILE_ENTITY" and "missing_hostile_entity" not in blocked:
            blocked.append("missing_hostile_entity")
    if blocking and not clar:
        clar = [
            {
                "domain": domain,
                "task_key": task_key,
                "label_zh": blocking[0].message_zh,
            }
        ]
    return rstatus, blocked, clar, dicts
