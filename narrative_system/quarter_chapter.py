# -*- coding: utf-8 -*-
"""季度总结章节：从 Workflow B 奏报组装可归档结构。"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


def _str(v: Any, limit: int = 0) -> str:
    s = str(v or "").strip()
    if limit > 0 and len(s) > limit:
        return s[:limit] + "…"
    return s


def _list_str(items: Any, limit: int = 8) -> List[str]:
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for x in items[:limit]:
        s = _str(x)
        if s:
            out.append(s)
    return out


def compact_settlement_summary(raw: Any) -> Dict[str, Any]:
    """保留结局助手需要的结构化事实，去掉重复大字段。"""
    if not isinstance(raw, dict):
        return {}
    return {
        "reporting_quarter_index": int(raw.get("reporting_quarter_index") or 0),
        "quarter_label_zh": _str(raw.get("quarter_label_zh")),
        "new_quarter_label_zh": _str(raw.get("new_quarter_label_zh")),
        "edict_issued": bool(raw.get("edict_issued")),
        "edict_summary_zh": _str(raw.get("edict_summary_zh")),
        "edict_text": _str(raw.get("edict_text"), 2000),
        "decree_track": _str(raw.get("decree_track")),
        "node_briefs": list(raw.get("node_briefs") or [])[:12],
        "metrics_delta": list(raw.get("metrics_delta") or [])[:12],
        "auto_fact_narratives": _list_str(raw.get("auto_fact_narratives"), 6),
        "settled_tasks": [
            {
                "title": _str(t.get("title") if isinstance(t, dict) else t),
                "result": _str(t.get("result")) if isinstance(t, dict) else "",
                "narrative_zh": _str(t.get("narrative_zh"), 200) if isinstance(t, dict) else "",
            }
            for t in (raw.get("settled_tasks") or [])[:8]
            if isinstance(t, dict)
        ],
        "outlook": list(raw.get("outlook") or [])[:6],
        "war_arcs": dict(raw.get("war_arcs") or {}),
        "crisis_metrics": _list_str(raw.get("crisis_metrics"), 6),
    }


def build_quarter_chapter_from_memorial(
    memorial: Dict[str, Any],
    *,
    report: Optional[Dict[str, Any]] = None,
    game_session_id: str = "",
) -> Dict[str, Any]:
    """从 quarter/start 的 memorial pack 组装单季归档条目。"""
    mem = dict(memorial or {})
    rep = dict(report or {})
    settlement_raw = mem.get("settlement_summary")
    settlement = compact_settlement_summary(settlement_raw)
    rep_q = int(
        mem.get("reporting_quarter_index")
        or settlement.get("reporting_quarter_index")
        or rep.get("reporting_quarter_index")
        or 0
    )
    body = _str(mem.get("body_zh"))
    summary = _str(mem.get("summary_zh"))
    if not summary and body:
        summary = _str(body, 320)

    chapter: Dict[str, Any] = {
        "reporting_quarter_index": rep_q,
        "quarter_label_zh": _str(mem.get("quarter_label_zh") or settlement.get("quarter_label_zh")),
        "new_quarter_label_zh": _str(settlement.get("new_quarter_label_zh")),
        "title_zh": _str(mem.get("title_zh") or rep.get("title_zh")),
        "headline_zh": _str(mem.get("headline_zh") or rep.get("headline_zh")),
        "summary_zh": summary,
        "body_zh": body,
        "highlights_zh": _list_str(mem.get("highlights_zh") or rep.get("highlights_zh"), 6),
        "edict_summary_zh": _str(settlement.get("edict_summary_zh")),
        "edict_text": _str(settlement.get("edict_text")),
        "settled_tasks_zh": _list_str(mem.get("settled_tasks_zh"), 8),
        "metric_changes_zh": _list_str(mem.get("metric_changes_zh"), 8),
        "outlook_zh": _list_str(mem.get("outlook_zh"), 6),
        "narrative_mode": _str(mem.get("mode") or rep.get("narrative_mode") or "template"),
        "memorial_id": _str(mem.get("memorial_id")),
        "game_session_id": _str(game_session_id),
        "settlement_summary": settlement,
        "archived_at_ms": int(time.time() * 1000),
    }
    return chapter
