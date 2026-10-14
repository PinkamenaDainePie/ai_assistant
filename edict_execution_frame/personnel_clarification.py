# -*- coding: utf-8 -*-
"""人事 playbook：擢用/黜罢须具名（叙事层校验，不改大臣表官职）。"""
from __future__ import annotations

import re
from typing import List

from edict_execution_frame.clarification import ClarificationIssue
from edict_execution_frame.schemas import EdictExecutionFrame, ExecutorSpec

_MERIT_KW = ("擢用", "除授", "拜为", "拜", "权知", "出任", "署理", "平章事", "参政", "同中书")
_CENSURE_KW = ("黜罢", "罢黜", "夺职", "削职", "编窜", "夺官", "罢相", "罢其官")
_CENSURE_NAME = re.compile(
    r"(?:黜|罢|夺|革|削)(?:黜|罢|免)?\s*([\u4e00-\u9fff]{2,4})"
)
_ORDER_NAME = re.compile(r"命\s*([\u4e00-\u9fff]{2,4})")
_GENERIC_CENSURE_TARGETS = frozenset(
    {"不肖", "不肖之臣", "奸臣", "贪吏", "冗官", "猾吏", "不才", "小人", "权臣"}
)

_PERSONNEL_NAMED_PLAYBOOKS = frozenset({"merit_appointment", "censure_and_removal"})


def _executor_has_named_person(ex: ExecutorSpec) -> bool:
    if (ex.mode or "") in ("person", "dual_person"):
        if (ex.person_name or "").strip():
            return True
        if ex.person_names:
            return any(str(n or "").strip() for n in ex.person_names)
    return False


def _loose_named_in_text(edict_text: str) -> bool:
    t = edict_text or ""
    if _ORDER_NAME.search(t):
        return True
    m = _CENSURE_NAME.search(t)
    if m:
        cand = m.group(1).strip()
        if cand and cand not in _GENERIC_CENSURE_TARGETS and 2 <= len(cand) <= 3:
            return True
    return False


def evaluate_personnel_issues(
    *,
    edict_text: str,
    domain: str,
    task_key: str,
    executor: ExecutorSpec,
) -> List[ClarificationIssue]:
    dom = (domain or "").strip()
    tk = (task_key or "").strip()
    if dom != "personnel" or tk not in _PERSONNEL_NAMED_PLAYBOOKS:
        return []
    t = edict_text or ""
    if tk == "merit_appointment":
        if not any(k in t for k in _MERIT_KW) and not _ORDER_NAME.search(t):
            return []
        msg = "请指明擢用或除授的臣僚姓名（如命王安石权知政事）。"
    else:
        if not any(k in t for k in _CENSURE_KW) and not _CENSURE_NAME.search(t):
            return []
        msg = "请指明黜罢或夺职的对象（如黜罢章惇、命台谏纠劾某臣）。"
    if _executor_has_named_person(executor) or _loose_named_in_text(t):
        return []
    return [
        ClarificationIssue(
            code="MISSING_APPOINTMENT_TARGET",
            field="executor",
            severity="error",
            blocks_execution=True,
            blocks_numbers=True,
            message_zh=msg,
            candidate_values=[],
        )
    ]
