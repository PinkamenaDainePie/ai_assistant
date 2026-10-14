# -*- coding: utf-8 -*-
"""执行者槽位：双人 / 单人具名 / 机构默认。"""
from __future__ import annotations

import re
from typing import Optional, Set

from edict_execution_frame.domain_catalog import DomainTaskRow
from edict_execution_frame.explicitness import extract_dual_ministers_in_text, extract_named_person_in_text
from edict_execution_frame.schemas import ExecutorSpec

_DEPT_FROM_TEXT = re.compile(r"(?:命|敕)\s*(工部|兵部|户部|吏部|礼部|刑部|都察院)")


def _trace_executor_name(trace: dict) -> str:
    ex = trace.get("executor_resolution") or {}
    if isinstance(ex, dict):
        return str(ex.get("name") or "").strip()
    return ""


def resolve_executor(
    *,
    edict_text: str,
    parse_trace: dict,
    task_row: DomainTaskRow,
    edict_executor_name: str = "",
    minister_names: Optional[Set[str]] = None,
    explicitness_class: str,
) -> ExecutorSpec:
    names = minister_names or set()
    dual = extract_dual_ministers_in_text(edict_text or "", names)
    if len(dual) == 2:
        disp = "%s与%s" % (dual[0], dual[1])
        return ExecutorSpec(
            mode="dual_person",
            display_name_zh=disp,
            person_name="",
            person_names=list(dual),
            institution_key="",
            is_inferred=False,
        )

    name = (edict_executor_name or "").strip()
    if not name:
        name = _trace_executor_name(parse_trace or {})
    if not name:
        name = extract_named_person_in_text(edict_text or "", names)
    if not name and names:
        text = edict_text or ""
        for cand in sorted(names, key=len, reverse=True):
            if cand and cand in text:
                name = cand
                break
    if not name:
        loose = re.search(
            r"命\s*([\u4e00-\u9fff]{2,4})(?=赴|前往|巡抚|督|监理)",
            edict_text or "",
        )
        if loose:
            name = loose.group(1).strip()
    if not name:
        purge = re.search(
            r"(?:黜|罢|夺|削)(?:黜|罢|免)?\s*([\u4e00-\u9fff]{2,4})",
            edict_text or "",
        )
        if purge:
            cand = purge.group(1).strip()
            if (
                cand in names
                and 2 <= len(cand) <= 3
                and cand not in {"不肖", "奸臣", "贪吏", "冗官", "猾吏", "不才", "小人"}
            ):
                name = cand

    if name and name in names:
        return ExecutorSpec(
            mode="person",
            display_name_zh=name,
            person_name=name,
            person_names=[name],
            institution_key="",
            is_inferred=False,
        )
    if name and name not in names:
        return ExecutorSpec(
            mode="person",
            display_name_zh=name,
            person_name=name,
            person_names=[name],
            institution_key="",
            is_inferred=False,
        )

    dm = _DEPT_FROM_TEXT.search(edict_text or "")
    if dm:
        dept = dm.group(1)
        return ExecutorSpec(
            mode="institution",
            display_name_zh=dept,
            person_name="",
            person_names=[],
            institution_key=task_row.task_key,
            is_inferred=False,
        )

    inst = task_row.default_executor_zh or "内阁与部院"
    inferred = explicitness_class in ("C", "D")
    return ExecutorSpec(
        mode="institution",
        display_name_zh=inst,
        person_name="",
        person_names=[],
        institution_key=task_row.task_key,
        is_inferred=inferred,
    )
