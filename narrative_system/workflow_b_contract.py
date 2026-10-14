# -*- coding: utf-8 -*-
"""Workflow B（Agent B）ADP content JSON 契约校验。"""
from __future__ import annotations

from typing import Any, Dict, List

_REQUIRED_TOP_KEYS = frozenset(
    {
        "memorial_id",
        "game_session_id",
        "session_id",
        "reporting_quarter_index",
        "quarter_label_zh",
        "style",
        "settlement_summary",
    }
)

_REQUIRED_SUMMARY_KEYS = frozenset(
    {
        "reporting_quarter_index",
        "quarter_label_zh",
        "edict_issued",
        "edict_text",
        "quarter_edict_actions",
        "agent_a_selection",
        "metrics_delta",
        "settled_tasks",
        "agent_narrative_bundle",
    }
)

_ACTION_ROW_KEYS = frozenset(
    {
        "index",
        "domain",
        "task_key",
        "text",
        "action_tier",
        "status",
        "agent_a_selected",
    }
)


def validate_workflow_b_content(obj: Dict[str, Any]) -> List[str]:
    """返回契约违规说明；空列表表示通过。"""
    errors: List[str] = []
    missing_top = _REQUIRED_TOP_KEYS - set(obj.keys())
    if missing_top:
        errors.append("顶层缺少字段: %s" % ", ".join(sorted(missing_top)))

    settlement = obj.get("settlement_summary")
    if not isinstance(settlement, dict):
        errors.append("settlement_summary 必须是 object")
        return errors

    missing_sum = _REQUIRED_SUMMARY_KEYS - set(settlement.keys())
    if missing_sum:
        errors.append("settlement_summary 缺少字段: %s" % ", ".join(sorted(missing_sum)))

    actions = settlement.get("quarter_edict_actions")
    if not isinstance(actions, list):
        errors.append("quarter_edict_actions 必须是 array")
    elif settlement.get("edict_issued") and not actions:
        errors.append("edict_issued=true 时 quarter_edict_actions 不应为空")

    for i, row in enumerate(actions or []):
        if not isinstance(row, dict):
            errors.append("quarter_edict_actions[%s] 不是 object" % i)
            continue
        miss = _ACTION_ROW_KEYS - set(row.keys())
        if miss:
            errors.append("quarter_edict_actions[%s] 缺少: %s" % (i, ", ".join(sorted(miss))))
        tier = str(row.get("action_tier") or "")
        if tier not in ("contest", "counter", "other"):
            errors.append("quarter_edict_actions[%s].action_tier 非法: %r" % (i, tier))

    alias = settlement.get("settled_tasks_this_quarter")
    if alias is not None and alias != settlement.get("settled_tasks"):
        errors.append("settled_tasks_this_quarter 应与 settled_tasks 一致")

    return errors
