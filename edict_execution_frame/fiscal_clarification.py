# -*- coding: utf-8 -*-
"""财政「充实国用」类模糊诏：策略 B — 默认按清厘积欠推定，低置信 auto_completed。"""
from __future__ import annotations

import re

from edict_execution_frame.domain_catalog import DOMAIN_TASK_CATALOG, DomainTaskRow

_FISCAL_GOAL_VAGUE = re.compile(
    r"(充实国用|国用不足|府库空虚|财计困乏|财用不给|边费浩繁.*财|经费不继|理财之法|设法补足|宽筹岁入|宜速为措置|措置国用)"
)

FISCAL_VAGUE_DEFAULT_TASK_KEY = "tax_collection_push"
FISCAL_VAGUE_DEFAULT_CONFIDENCE = 0.55


def is_fiscal_goal_vague(edict_text: str) -> bool:
    t = (edict_text or "").strip()
    if not t or not _FISCAL_GOAL_VAGUE.search(t):
        return False
    if re.search(
        r"(钱粮|逋欠|积欠|旧欠|追比|清厘|催征|完纳|赋役|税课|岁课|加派|加征|市易|免役|均输|裁冗|榷|罢市易|停市易)",
        t,
    ):
        return False
    from edict_execution_frame.frame_builder import _STRONG_TASK_SIGNAL

    return not bool(_STRONG_TASK_SIGNAL.search(t))


def fiscal_vague_default_row() -> DomainTaskRow:
    for row in DOMAIN_TASK_CATALOG.get("fiscal") or []:
        if row.task_key == FISCAL_VAGUE_DEFAULT_TASK_KEY:
            return row
    return DOMAIN_TASK_CATALOG["fiscal"][0]
