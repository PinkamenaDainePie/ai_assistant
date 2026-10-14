# -*- coding: utf-8 -*-
"""季度朝政纪要：模板 fallback（无 LLM）。"""
from __future__ import annotations

from typing import Any, Dict, List

from narrative_system.schemas import QuarterSettlementSummary


def _headline_from_summary(summary: QuarterSettlementSummary) -> str:
    parts: List[str] = []
    for nb in summary.node_briefs[:2]:
        if nb.delta_progress >= 8:
            parts.append("%s推进" % nb.title_zh)
        elif nb.status == "active" and nb.progress >= 20:
            parts.append(nb.title_zh)
    if summary.edict_issued and summary.edict_summary_zh:
        snippet = summary.edict_summary_zh[:14].replace("【", "").replace("】", "")
        if snippet and snippet not in parts:
            parts.insert(0, snippet)
    for t in summary.settled_tasks[:2]:
        title = str(t.get("title") or "").strip()
        if title and len(parts) < 2:
            parts.append(title[:10])
    if summary.pending_event.get("title"):
        parts.append(str(summary.pending_event["title"])[:12])
    while len(parts) < 2:
        if summary.crisis_metrics:
            parts.append("%s告急" % summary.crisis_metrics[0])
            break
        parts.append("朝局依循旧章")
        break
    return "，".join(parts[:2])


def render_template_memorial(summary: QuarterSettlementSummary) -> Dict[str, Any]:
    headline = _headline_from_summary(summary)
    title = "%s朝政纪要——%s" % (summary.quarter_label_zh, headline)

    lines: List[str] = ["朝政纪要", ""]
    if summary.edict_issued:
        lines.append(
            "本季陛下颁诏行事。%s"
            % (summary.edict_summary_zh or "诏书已下达，诸司遵行。")
        )
        actions = list(getattr(summary, "quarter_edict_actions", None) or [])
        if actions:
            lines.append("")
            lines.append("本季诏令分项：")
            for row in actions[:8]:
                if str(row.get("status") or "") == "needs_clarification":
                    continue
                text = str(row.get("text") or row.get("task_key") or row.get("domain") or "").strip()
                tier = str(row.get("action_tier") or "")
                if text:
                    suffix = "（%s）" % tier if tier else ""
                    lines.append("· %s%s" % (text[:80], suffix))
    else:
        lines.append("本季陛下未颁新诏，朝局依循既定之势自然演化。")
    lines.append("")

    bundle = getattr(summary, "agent_narrative_bundle", {}) or {}
    if bundle and (bundle.get("explanation_zh") or bundle.get("main_risk_zh")):
        lines.append("本季诏令引发的朝野博弈与次生影响：%s 风险等级：%s。" % (
            (bundle.get("explanation_zh") or "")[:120],
            bundle.get("risk_level") or "低"
        ))
        if bundle.get("main_risk_zh"):
            lines.append("主要风险：%s" % bundle.get("main_risk_zh"))
        lines.append("")

    sec = 1
    if summary.settled_tasks:
        lines.append("%s、本季要务结算" % _zh_num(sec))
        sec += 1
        for t in summary.settled_tasks[:6]:
            title_t = str(t.get("title") or "要务")
            res = str(t.get("result") or "")
            nar = str(t.get("narrative_zh") or "").strip()
            line = "· %s：%s" % (title_t, res or "已结案")
            if nar:
                line += "。%s" % nar[:120]
            lines.append(line)
        lines.append("")

    if summary.metrics_delta:
        lines.append("%s、指标异动" % _zh_num(sec))
        sec += 1
        for m in summary.metrics_delta[:6]:
            lines.append(
                "· %s：%.0f→%.0f"
                % (m.label_zh, m.value_from, m.value_to)
            )
        lines.append("")

    if summary.node_briefs:
        lines.append("%s、制度推行" % _zh_num(sec))
        sec += 1
        for nb in summary.node_briefs[:4]:
            extra = ""
            if nb.delta_progress:
                extra = "（本季推进 %+d）" % nb.delta_progress
            lines.append(
                "· %s：%s，进度 %d%s"
                % (nb.title_zh, nb.status, nb.progress, extra)
            )
        lines.append("")

    for nar in summary.auto_fact_narratives[:2]:
        lines.append(nar)
        lines.append("")

    if summary.pending_event.get("title"):
        lines.append(
            "边报：%s。%s"
            % (
                summary.pending_event.get("title"),
                (summary.pending_event.get("description") or "")[:160],
            )
        )
        lines.append("")

    lines.append("%s、后续局势研判" % _zh_num(sec))
    for o in summary.outlook[:5]:
        lines.append("· %s" % o.hint_zh)
    if not summary.outlook:
        lines.append("· 诸务照常，惟宜观民心与府库之消长。")

    body = "\n".join(lines).strip()
    highlights = [headline]
    if summary.edict_issued:
        highlights.append("本季颁诏")
    for nb in summary.node_briefs[:2]:
        if nb.delta_progress >= 10:
            highlights.append(nb.title_zh)

    return {
        "title_zh": title,
        "headline_zh": headline,
        "body_zh": body,
        "summary_zh": body[:280] + ("…" if len(body) > 280 else ""),
        "highlights_zh": highlights[:4],
        "mode": "template",
    }


def _zh_num(n: int) -> str:
    return ("", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十")[min(n, 10)]
