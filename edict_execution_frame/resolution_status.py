# -*- coding: utf-8 -*-
"""resolution_status / ambiguity 判定（与 task_resolver 阈值配合）。"""
from __future__ import annotations

from edict_execution_frame.resolution_thresholds import (
    AUTO_COMPLETED_TASK_MAX,
    DOMAIN_CLARIFY_MAX,
    TASK_CLARIFY_MAX,
    TASK_FALLBACK_CLARIFY_MAX,
)
from edict_execution_frame.task_resolver import task_ambiguity_high


def decide_resolution_status(
    *,
    task_confidence: float,
    task_is_fallback: bool,
    domain_confidence: float,
    executor_is_defaulted: bool,
    duration_is_defaulted: bool,
    top1_task_conf: float,
    second_task_conf: float,
    top1_score: int = 0,
    second_score: int = 0,
) -> str:
    """
    Returns: resolved | auto_completed | needs_clarification
    """
    amb = task_ambiguity_high(
        top1_task_conf,
        second_task_conf,
        top1_score=top1_score,
        second_score=second_score,
    )

    if float(task_confidence) < TASK_CLARIFY_MAX:
        return "needs_clarification"
    if float(domain_confidence) < DOMAIN_CLARIFY_MAX:
        return "needs_clarification"
    if task_is_fallback and float(task_confidence) < TASK_FALLBACK_CLARIFY_MAX:
        return "needs_clarification"
    if amb:
        return "needs_clarification"
    if (float(task_confidence) < AUTO_COMPLETED_TASK_MAX) and (
        bool(duration_is_defaulted) or bool(executor_is_defaulted)
    ):
        return "auto_completed"
    return "resolved"


def ambiguity_label(
    *,
    top1_task_conf: float,
    second_task_conf: float,
    top1_score: int = 0,
    second_score: int = 0,
) -> str:
    if task_ambiguity_high(
        top1_task_conf,
        second_task_conf,
        top1_score=top1_score,
        second_score=second_score,
    ):
        return "high"
    if top1_task_conf < 0.62 or (top1_score > 0 and top1_score == second_score):
        return "low"
    return "none"
