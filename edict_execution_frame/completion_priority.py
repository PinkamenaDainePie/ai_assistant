# -*- coding: utf-8 -*-
"""从可执行候选中选唯一帧（非 RL）：列表顺序即优先级。"""
from __future__ import annotations

from typing import List, Optional

from edict_execution_frame.schemas import EdictExecutionFrame


def pick_first_admissible(candidates: List[EdictExecutionFrame]) -> Optional[EdictExecutionFrame]:
    return candidates[0] if candidates else None
