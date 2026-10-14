# -*- coding: utf-8 -*-
"""时长槽位：显式季数优先；未写明时农业默认三季（春耕—秋收），其余默认一季。"""
from __future__ import annotations

from edict_execution_frame.domain_catalog import DomainTaskRow
from edict_execution_frame.explicitness import duration_explicit_from_text
from edict_execution_frame.schemas import DurationSpec

# 农政一载三季：春劝课 → 夏督耕 → 秋收汇奏（未写季数时的域默认）
_DOMAIN_DEFAULT_QUARTERS = {
    "agriculture": 3,
}


def default_quarters_for_domain(domain: str) -> int:
    return max(1, min(5, int(_DOMAIN_DEFAULT_QUARTERS.get((domain or "").strip(), 1))))


def resolve_duration(
    edict_text: str,
    task_row: DomainTaskRow,
    explicitness_class: str,  # noqa: ARG001  保留签名兼容
    *,
    domain: str = "",
) -> DurationSpec:
    """显式「N季」优先；否则按域默认（农业 3，其它 1）。"""
    q, explicit = duration_explicit_from_text(edict_text or "")
    if explicit and q is not None:
        return DurationSpec(quarters=max(1, min(5, int(q))), is_inferred=False)
    dom = (domain or "").strip()
    return DurationSpec(quarters=default_quarters_for_domain(dom), is_inferred=True)


def bump_duration_for_person_task(
    base: DurationSpec,
    *,
    explicitness_class: str,  # noqa: ARG001
    min_quarters: int = 2,
) -> DurationSpec:
    """仅当诏书已写明季数时，具名承办可沿用该时长（不再暗抬季数）。"""
    if base.is_inferred:
        return base
    q = max(int(base.quarters or 1), int(min_quarters))
    return DurationSpec(quarters=min(5, q), is_inferred=False)
