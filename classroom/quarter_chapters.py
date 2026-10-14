# -*- coding: utf-8 -*-
"""Playthrough 季度总结解析与合并。"""
from __future__ import annotations

from typing import Any, Dict, List

from narrative_system.session_archive import (
    find_quarter_chapters_by_game_session_id,
    get_quarter_chapters,
    merge_quarter_chapter_lists,
)


def merge_quarter_chapters(
    existing: List[Dict[str, Any]] | None,
    incoming: List[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """合并 DB 已有与 PATCH 上报的季度总结。"""
    base = [dict(x) for x in (existing or []) if isinstance(x, dict)]
    extra = [dict(x) for x in (incoming or []) if isinstance(x, dict)]
    if not extra:
        return base
    return merge_quarter_chapter_lists(base, extra)


def resolve_playthrough_quarter_chapters(
    row: Any,
) -> List[Dict[str, Any]]:
    """DB → campaign_session_id 归档 → game_session_id 扫描。"""
    stored = getattr(row, "quarter_chapters_json", None) or []
    if isinstance(stored, list) and stored:
        return merge_quarter_chapter_lists([], stored)

    campaign_sid = str(getattr(row, "campaign_session_id", "") or "").strip()
    if campaign_sid:
        archived = get_quarter_chapters(campaign_sid)
        if archived:
            return archived

    game_sid = str(getattr(row, "game_session_id", "") or "").strip()
    if game_sid:
        found = find_quarter_chapters_by_game_session_id(game_sid)
        if found:
            return found

    return []
