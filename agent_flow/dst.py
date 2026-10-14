# -*- coding: utf-8 -*-
"""DST：旧动作上下文 + 用户动作 + 系统动作 → 新上下文。"""
from __future__ import annotations

from datetime import datetime, timezone

from agent_flow.schemas import ActionFlowState, ActionRef, SystemAction, UserAction


def apply_action_dst(
    old: ActionFlowState,
    *,
    user_action: UserAction,
    system_action: Optional[SystemAction] = None,
    primary_action: Optional[ActionRef] = None,
) -> ActionFlowState:
    new = old.model_copy(deep=True)
    new.former_action = (
        str(old.last_system_action.action_type or "")
        if old.last_system_action is not None
        else ""
    )
    new.last_user_action = user_action
    if system_action is not None:
        new.last_system_action = system_action
    if primary_action is not None:
        new.last_primary_action = primary_action
        if primary_action.edict_text:
            new.last_edict_text = primary_action.edict_text
    new.updated_at = datetime.now(timezone.utc)
    return new
