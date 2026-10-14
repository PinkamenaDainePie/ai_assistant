# -*- coding: utf-8 -*-
"""Workflow C：结局总结 ADP 调用与 EndingSummaryReport 解析。"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from agent_flow.adp_client import AdpClientError, call_adp_workflow_sse
from agent_flow.config import ENDING_SUMMARY_BOT_APP_KEY


def ending_summary_adp_enabled() -> bool:
    return bool((ENDING_SUMMARY_BOT_APP_KEY or "").strip())


def normalize_ending_summary_report(obj: Any) -> Dict[str, Any]:
    """解包 ADP 结束节点：Output.Output / result / output / 直出。"""
    if not isinstance(obj, dict):
        raise AdpClientError("EndingSummaryReport 输出不是 JSON 对象")

    def _unwrap(payload: Dict[str, Any]) -> Dict[str, Any]:
        outer = payload.get("Output")
        if isinstance(outer, dict):
            inner = outer.get("Output")
            if isinstance(inner, dict):
                return dict(inner)
            return dict(outer)
        result = payload.get("result")
        if isinstance(result, dict):
            return dict(result)
        output = payload.get("output")
        if isinstance(output, dict):
            merged = dict(output)
            for key in ("ending_id", "ending_type", "_adp_trace"):
                if key in payload and key not in merged:
                    merged[key] = payload[key]
            return merged
        return dict(payload)

    report = _unwrap(obj)
    if any(k in report for k in ("score", "sections", "life_chronicle_zh", "title_zh")):
        return report
    sections = report.get("sections")
    if isinstance(sections, dict):
        return report
    return report


def build_workflow_c_content(request: Dict[str, Any]) -> str:
    """Workflow C 输入：整包 JSON 字符串（写入 HTTP content）。"""
    body = dict(request or {})
    gs_id = str(body.get("game_session_id") or body.get("session_id") or "").strip()
    if gs_id:
        body["game_session_id"] = gs_id
    body.setdefault("style", "epilogue")
    body.setdefault("max_total_chars", 4500)
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def call_ending_summary_sse(
    request: Dict[str, Any],
    *,
    game_session_id: str = "",
    session_id: str = "",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """调用 ADP Workflow C，返回 EndingSummaryReport dict。"""
    app_key = (ENDING_SUMMARY_BOT_APP_KEY or "").strip()
    if not app_key:
        raise AdpClientError("ENDING_SUMMARY_BOT_APP_KEY 未配置")
    gs = (game_session_id or request.get("game_session_id") or "").strip()
    sid = (session_id or request.get("session_id") or gs or "").strip()
    content = build_workflow_c_content(request)
    raw = call_adp_workflow_sse(
        bot_app_key=app_key,
        content=content,
        game_session_id=gs,
        session_id=sid,
        request_id=request_id,
        normalize=normalize_ending_summary_report,
        workflow_label="ending_summary",
    )
    raw.setdefault("ending_id", request.get("ending_id") or "")
    trace = dict(raw.get("_adp_trace") or {})
    trace["workflow"] = "ending_summary"
    raw["_adp_trace"] = trace
    return raw


def _sections_from_report(report: Dict[str, Any]) -> Dict[str, str]:
    sections = report.get("sections")
    if isinstance(sections, dict):
        return {str(k): str(v or "") for k, v in sections.items()}
    legacy = {
        "life_chronicle_zh": str(report.get("life_chronicle_zh") or ""),
        "ending_scene_zh": str(report.get("ending_scene_zh") or ""),
        "merits_demerits_zh": str(report.get("merits_demerits_zh") or ""),
        "temple_name_zh": str(report.get("temple_name_zh") or ""),
        "future_projection_zh": str(report.get("future_projection_zh") or ""),
    }
    if any(legacy.values()):
        return legacy
    return {}


def ending_report_to_pack(
    report: Dict[str, Any],
    *,
    request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """将 ADP 输出转为 API / 前端沿用的 ending pack。"""
    req = dict(request or {})
    verdict = dict(req.get("ending_verdict") or {})
    epilogue = dict(verdict.get("epilogue") or {})
    sections = _sections_from_report(report)

    title = str(report.get("title_zh") or epilogue.get("title_zh") or verdict.get("reason_zh") or "").strip()
    score_raw = report.get("score")
    try:
        score = int(score_raw) if score_raw is not None else 0
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    summary_parts = [
        sections.get("life_chronicle_zh", ""),
        sections.get("ending_scene_zh", ""),
    ]
    summary_zh = str(report.get("summary_zh") or "").strip()
    if not summary_zh:
        summary_zh = "\n\n".join(p for p in summary_parts if p)[:800]

    highlights = report.get("highlights_zh")
    if not isinstance(highlights, list):
        highlights = []

    pack: Dict[str, Any] = {
        "ending_id": str(report.get("ending_id") or req.get("ending_id") or ""),
        "ending_type": str(report.get("ending_type") or verdict.get("kind") or ""),
        "score": score,
        "score_label_zh": str(report.get("score_label_zh") or ""),
        "title_zh": title,
        "summary_zh": summary_zh,
        "sections": sections,
        "highlights_zh": [str(x) for x in highlights[:8]],
        "history_compare_zh": str(report.get("history_compare_zh") or ""),
        "tone": str(report.get("tone") or ""),
        "mode": "adp",
    }
    trace = dict(report.get("_adp_trace") or {})
    if trace:
        pack["adp_trace"] = trace
    return pack


def render_template_ending_summary(request: Dict[str, Any]) -> Dict[str, Any]:
    """ADP 未配置或失败时的模板降级。"""
    verdict = dict(request.get("ending_verdict") or {})
    epilogue = dict(verdict.get("epilogue") or {})
    title = str(epilogue.get("title_zh") or verdict.get("reason_zh") or "战役收束")
    summary = str(epilogue.get("summary_zh") or verdict.get("reason_zh") or "")
    chapters = list(request.get("quarter_chapters") or [])
    highlights = []
    for ch in chapters[-5:]:
        if isinstance(ch, dict):
            h = str(ch.get("title_zh") or ch.get("summary_zh") or "")[:80]
            if h:
                highlights.append(h)

    return {
        "ending_id": request.get("ending_id") or "",
        "ending_type": verdict.get("kind") or "",
        "score": 50,
        "score_label_zh": "收束",
        "title_zh": title,
        "summary_zh": summary,
        "sections": {
            "life_chronicle_zh": summary,
            "ending_scene_zh": "",
            "merits_demerits_zh": "",
            "temple_name_zh": "",
            "future_projection_zh": "",
        },
        "highlights_zh": highlights[:5],
        "history_compare_zh": "",
        "tone": "ambiguous",
        "mode": "template",
    }


def _report_has_body(report: Dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    if report.get("score") is not None:
        return True
    sections = report.get("sections")
    if isinstance(sections, dict) and any(str(v or "").strip() for v in sections.values()):
        return True
    for key in ("life_chronicle_zh", "ending_scene_zh", "merits_demerits_zh", "body_zh", "summary_zh"):
        if str(report.get(key) or "").strip():
            return True
    return bool(str(report.get("title_zh") or "").strip())


def build_and_render_ending_summary(
    session_id: str,
    *,
    game_session_id: str = "",
    root_dir: str = "",
    campaign_end: Optional[Dict[str, Any]] = None,
    scenario_id: str = "",
    event_service: Any = None,
    state_obj: Any = None,
    client_quarter_chapters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """组装输入并渲染结局总结（ADP 优先，失败降级 template）。"""
    from narrative_system.ending_builder import build_ending_summary_request

    request = build_ending_summary_request(
        session_id,
        game_session_id=game_session_id,
        root_dir=root_dir,
        campaign_end=campaign_end,
        scenario_id=scenario_id,
        event_service=event_service,
        state_obj=state_obj,
        client_quarter_chapters=client_quarter_chapters,
    )
    if ending_summary_adp_enabled():
        try:
            report = call_ending_summary_sse(
                request,
                game_session_id=game_session_id,
                session_id=session_id,
            )
            if _report_has_body(report):
                pack = ending_report_to_pack(report, request=request)
                pack["request"] = request
                return pack
        except Exception:
            pass
    pack = render_template_ending_summary(request)
    pack["request"] = request
    return pack
