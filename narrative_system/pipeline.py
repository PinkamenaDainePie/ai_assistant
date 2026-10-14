# -*- coding: utf-8 -*-
"""季度纪要渲染入口。"""
from __future__ import annotations

from typing import Any, Dict

from narrative_system.quarter_adp import quarter_narrative_adp_enabled, render_adp_memorial
from narrative_system.quarter_llm import quarter_narrative_mode, render_llm_memorial
from narrative_system.schemas import QuarterSettlementSummary
from narrative_system.summary_builder import build_quarter_settlement_summary
from narrative_system.template_narrative import render_template_memorial


def render_quarter_memorial(
    summary: QuarterSettlementSummary,
    *,
    game_session_id: str = "",
    session_id: str = "",
) -> Dict[str, Any]:
    gs_id = (game_session_id or session_id or "").strip()
    sid = (session_id or gs_id or "").strip()

    if quarter_narrative_adp_enabled():
        try:
            pack = render_adp_memorial(summary, game_session_id=gs_id, session_id=sid)
            pack["quarter_label_zh"] = summary.quarter_label_zh
            pack["reporting_quarter_index"] = summary.reporting_quarter_index
            return pack
        except Exception:
            pass

    mode = quarter_narrative_mode()
    if mode == "template":
        pack = render_template_memorial(summary)
    else:
        pack = render_llm_memorial(summary)
    pack["quarter_label_zh"] = summary.quarter_label_zh
    pack["reporting_quarter_index"] = summary.reporting_quarter_index
    return pack


def build_and_render_quarter_memorial(**kwargs: Any) -> Dict[str, Any]:
    render_kwargs = {
        "game_session_id": str(kwargs.get("game_session_id") or ""),
        "session_id": str(kwargs.get("session_id") or ""),
    }
    summary_kwargs = dict(kwargs)
    summary_kwargs.pop("game_session_id", None)
    summary = build_quarter_settlement_summary(**summary_kwargs)
    memorial = render_quarter_memorial(summary, **render_kwargs)
    memorial["settlement_summary"] = summary.to_dict()
    return memorial
