# -*- coding: utf-8 -*-
"""任务槽位：catalog 行选择 + 候选列表与置信度（供澄清与入队门控）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from edict_execution_frame.domain_catalog import (
    DOMAIN_TASK_CATALOG,
    DomainTaskRow,
    _score_row,
    select_task_row_for_domain,
)
from edict_execution_frame.resolution_thresholds import AMBIGUITY_TOP1_LOW, AMBIGUITY_TOP1_TOP2_GAP


@dataclass
class TaskCandidate:
    domain: str
    row: DomainTaskRow
    score: int
    reason_zh: str
    confidence: float


@dataclass
class TaskResolutionResult:
    domain: str
    row: DomainTaskRow
    confidence: float
    is_fallback: bool
    candidates: List[TaskCandidate]


def _hits_for_row(text: str, row: DomainTaskRow) -> List[str]:
    t = text or ""
    return [kw for kw in row.keywords if kw and kw in t]


def _confidence_from_score(score: int, *, is_fallback: bool) -> float:
    if is_fallback:
        return 0.38
    base = 0.42 + min(0.48, float(score) * 0.045)
    return round(min(0.98, base), 3)


def rank_rows_for_domain(domain: str, edict_text: str) -> List[Tuple[DomainTaskRow, int, List[str]]]:
    rows = DOMAIN_TASK_CATALOG.get(domain) or DOMAIN_TASK_CATALOG["general"]
    text = edict_text or ""
    ranked: List[Tuple[DomainTaskRow, int, List[str]]] = []
    for row in rows:
        sc, _ = _score_row(text, row, domain=domain)
        hits = _hits_for_row(text, row)
        ranked.append((row, sc, hits))
    ranked.sort(key=lambda x: -x[1])
    return ranked


def resolve_task_for_domain(domain: str, edict_text: str) -> TaskResolutionResult:
    ranked = rank_rows_for_domain(domain, edict_text)
    best_row = select_task_row_for_domain(domain, edict_text)
    best_score, _ = _score_row(edict_text or "", best_row, domain=domain)
    hits0 = _hits_for_row(edict_text or "", best_row)
    second_score = 0
    for row, sc, _hits in ranked:
        if row.task_key != best_row.task_key:
            second_score = sc
            break
    is_fallback = best_score <= 0 and not any(hits0)
    conf = _confidence_from_score(best_score, is_fallback=is_fallback)
    # tie-break: if两条不同任务同分，略降置信
    if best_score > 0 and second_score == best_score:
        conf = round(max(0.35, conf - 0.08), 3)

    cands: List[TaskCandidate] = []
    for row, sc, hits in ranked[:5]:
        if sc <= 0 and row is not best_row:
            continue
        hz = "目录默认" if sc <= 0 else ("关键词：" + "、".join(hits[:5]) if hits else "语境弱匹配")
        cands.append(
            TaskCandidate(
                domain=domain,
                row=row,
                score=sc,
                reason_zh=hz,
                confidence=_confidence_from_score(sc, is_fallback=sc <= 0 and row is best_row),
            )
        )
    return TaskResolutionResult(
        domain=domain,
        row=best_row,
        confidence=conf,
        is_fallback=is_fallback,
        candidates=cands,
    )


def list_cross_domain_task_candidates(edict_text: str, *, max_items: int = 12) -> List[TaskCandidate]:
    """跨域扫描，用于澄清选项。"""
    text = edict_text or ""
    acc: List[TaskCandidate] = []
    for dom, rows in DOMAIN_TASK_CATALOG.items():
        for row in rows:
            sc, _ = _score_row(text, row, domain=dom)
            hits = _hits_for_row(text, row)
            if sc <= 0:
                continue
            hz = "关键词：" + "、".join(hits[:4]) if hits else "弱匹配"
            acc.append(
                TaskCandidate(
                    domain=dom,
                    row=row,
                    score=sc,
                    reason_zh=hz,
                    confidence=_confidence_from_score(sc, is_fallback=False),
                )
            )
    acc.sort(key=lambda c: (-c.score, -c.confidence))
    return acc[:max_items]


def build_clarification_options(
    task_candidates: List[TaskCandidate],
    *,
    max_items: int = 3,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in (task_candidates or [])[:max_items]:
        out.append(
            {
                "domain": c.domain,
                "task_key": c.row.task_key,
                "title_zh": c.row.title_zh,
                "reason_zh": c.reason_zh,
                "confidence": c.confidence,
            }
        )
    return out


def default_clarification_triplet() -> List[TaskCandidate]:
    """当正文几乎不匹配任何 catalog 关键词时的兜底澄清项。"""
    out: List[TaskCandidate] = []
    for dom, tkey, title, reason in (
        ("personnel", "official_evaluation", "考课与任免整肃", "人事考课方向"),
        ("general", "local_governance_cleanup", "地方吏治整饬", "吏治积弊方向"),
        ("fiscal", "tax_collection_push", "清厘赋役与积欠", "钱粮赋役方向"),
    ):
        rows = DOMAIN_TASK_CATALOG.get(dom) or []
        row = next((r for r in rows if r.task_key == tkey), rows[0] if rows else None)
        if row is None:
            continue
        out.append(
            TaskCandidate(
                domain=dom,
                row=row,
                score=0,
                reason_zh=reason,
                confidence=0.42,
            )
        )
    return out


def clarification_candidates_diverse(edict_text: str, *, max_items: int = 3) -> List[TaskCandidate]:
    allc = list_cross_domain_task_candidates(edict_text, max_items=24)
    picked: List[TaskCandidate] = []
    seen_dom = set()
    for c in allc:
        if c.domain in seen_dom:
            continue
        seen_dom.add(c.domain)
        picked.append(c)
        if len(picked) >= max_items:
            break
    if len(picked) < max_items:
        for d in default_clarification_triplet():
            if d.domain in seen_dom:
                continue
            seen_dom.add(d.domain)
            picked.append(d)
            if len(picked) >= max_items:
                break
    return picked[:max_items]


def task_ambiguity_high(
    top_conf: float,
    second_conf: float,
    *,
    top1_score: int = 0,
    second_score: int = 0,
) -> bool:
    if top_conf < AMBIGUITY_TOP1_LOW:
        return True
    if top1_score > second_score:
        return False
    if top1_score > 0 and second_score > 0 and top1_score == second_score:
        if (top_conf - second_conf) < AMBIGUITY_TOP1_TOP2_GAP:
            return True
    return False
