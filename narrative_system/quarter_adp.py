# -*- coding: utf-8 -*-
"""Workflow B：季度总结 ADP 调用与 MemorialReport 解析。"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from agent_flow.adp_client import AdpClientError, call_adp_workflow_sse, extract_from_workflow_outputs
from agent_flow.config import QUARTER_NARRATIVE_BOT_APP_KEY
from narrative_system.schemas import QuarterSettlementSummary


def quarter_narrative_adp_enabled() -> bool:
    return bool((QUARTER_NARRATIVE_BOT_APP_KEY or "").strip())


def normalize_memorial_report(obj: Any) -> Dict[str, Any]:
    """解包 ADP 结束节点多种外层：Output.Output / result / 直出。"""
    if not isinstance(obj, dict):
        raise AdpClientError("MemorialReport 输出不是 JSON 对象")
    outer = obj.get("Output")
    if isinstance(outer, dict):
        inner = outer.get("Output")
        if isinstance(inner, dict):
            return dict(inner)
        return dict(outer)
    result = obj.get("result")
    if isinstance(result, dict):
        return dict(result)
    if any(k in obj for k in ("title_zh", "body_zh", "headline_zh")):
        return dict(obj)
    return dict(obj)


def build_workflow_b_content(
    summary: QuarterSettlementSummary,
    *,
    game_session_id: str = "",
    session_id: str = "",
    memorial_id: str = "",
    style: str = "memorial",
) -> str:
    """Workflow B 输入：整包 JSON 字符串（写入 HTTP content / SYS.userQuery）。"""
    gs_id = (game_session_id or session_id or "").strip()
    sid = (session_id or gs_id or "anonymous").strip()
    rep_q = int(summary.reporting_quarter_index)
    mid = (memorial_id or "").strip() or "%s_q%s" % (gs_id or sid, rep_q)
    settlement = dict(summary.to_dict())
    settlement["settled_tasks_this_quarter"] = list(settlement.get("settled_tasks") or [])
    body = {
        "memorial_id": mid,
        "game_session_id": gs_id,
        "session_id": sid,
        "reporting_quarter_index": rep_q,
        "quarter_label_zh": summary.quarter_label_zh,
        "style": style or "memorial",
        "settlement_summary": settlement,
    }
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def call_quarter_narrative_sse(
    summary: QuarterSettlementSummary,
    *,
    game_session_id: str = "",
    session_id: str = "",
    memorial_id: str = "",
    style: str = "memorial",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """调用 ADP Workflow B，返回 MemorialReport dict。"""
    app_key = (QUARTER_NARRATIVE_BOT_APP_KEY or "").strip()
    if not app_key:
        raise AdpClientError("QUARTER_NARRATIVE_BOT_APP_KEY 未配置")
    content = build_workflow_b_content(
        summary,
        game_session_id=game_session_id,
        session_id=session_id,
        memorial_id=memorial_id,
        style=style,
    )
    raw = call_adp_workflow_sse(
        bot_app_key=app_key,
        content=content,
        game_session_id=game_session_id,
        session_id=session_id,
        request_id=request_id,
        normalize=normalize_memorial_report,
        workflow_label="quarter_narrative",
    )
    raw.setdefault("memorial_id", memorial_id or "")
    trace = dict(raw.get("_adp_trace") or {})
    trace["workflow"] = "quarter_narrative"
    raw["_adp_trace"] = trace
    return raw


def memorial_report_to_pack(report: Dict[str, Any], summary: QuarterSettlementSummary) -> Dict[str, Any]:
    """将 ADP MemorialReport 转为前端/ API 沿用的 memorial pack。"""
    title = str(report.get("title_zh") or "").strip()
    headline = str(report.get("headline_zh") or "").strip()
    body = str(report.get("body_zh") or "").strip()
    if not title and headline:
        title = "%s朝政纪要——%s" % (summary.quarter_label_zh, headline)
    if not body:
        body = str(report.get("summary_zh") or "").strip()
    summary_zh = str(report.get("summary_zh") or "").strip()
    if not summary_zh and body:
        summary_zh = body[:320] + ("…" if len(body) > 320 else "")
    highlights = report.get("highlights_zh")
    if not isinstance(highlights, list):
        highlights = []
    pack: Dict[str, Any] = {
        "memorial_id": str(report.get("memorial_id") or ""),
        "title_zh": title,
        "headline_zh": headline,
        "body_zh": body,
        "summary_zh": summary_zh,
        "highlights_zh": [str(x) for x in highlights[:6]],
        "causal_chains": list(report.get("causal_chains") or []),
        "settled_tasks_zh": list(report.get("settled_tasks_zh") or []),
        "agent_reactions_zh": list(report.get("agent_reactions_zh") or []),
        "metric_changes_zh": list(report.get("metric_changes_zh") or []),
        "personnel_changes_zh": list(report.get("personnel_changes_zh") or []),
        "outlook_zh": list(report.get("outlook_zh") or []),
        "quarter_label_zh": summary.quarter_label_zh,
        "reporting_quarter_index": summary.reporting_quarter_index,
        "mode": "adp",
    }
    trace = dict(report.get("_adp_trace") or {})
    if trace:
        pack["adp_trace"] = trace
    return pack


def render_adp_memorial(
    summary: QuarterSettlementSummary,
    *,
    game_session_id: str = "",
    session_id: str = "",
    memorial_id: str = "",
    style: str = "memorial",
) -> Dict[str, Any]:
    report = call_quarter_narrative_sse(
        summary,
        game_session_id=game_session_id,
        session_id=session_id,
        memorial_id=memorial_id,
        style=style,
    )
    return memorial_report_to_pack(report, summary)
