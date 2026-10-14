# -*- coding: utf-8 -*-
"""季度朝政纪要 LLM：headline + 正文（只读 QuarterSettlementSummary）。"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from narrative_system.schemas import QuarterSettlementSummary
from narrative_system.template_narrative import render_template_memorial

_FEW_SHOT_TITLE = "崇祯元年秋季朝政纪要——北疆惊变察哈尔败，鲁豫水退隐患深"


def quarter_narrative_mode() -> str:
    return (os.getenv("QUARTER_NARRATIVE_MODE") or "llm").strip().lower()


def quarter_narrative_model() -> str:
    return (os.getenv("QUARTER_NARRATIVE_LLM_MODEL") or os.getenv("DEFAULT_LLM_MODEL") or "qwen-turbo").strip()


def _summary_for_prompt(summary: QuarterSettlementSummary) -> str:
    payload = summary.to_dict()
    payload.pop("war_arcs", None)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_llm_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _call_quarter_llm(messages: List[Dict[str, str]]) -> str:
    from renwu_module.config import DASHSCOPE_API_BASE, DASHSCOPE_API_KEY
    from renwu_module.persona import _call_llm

    return _call_llm(
        messages,
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_API_BASE,
        model=quarter_narrative_model(),
    )


def _build_messages(summary: QuarterSettlementSummary, *, step: str) -> List[Dict[str, str]]:
    data = _summary_for_prompt(summary)
    if step == "headline":
        user = (
            "根据下列【季度结算摘要】写标题副句 headline_zh。\n"
            "要求：两个并列大事，用中文逗号连接（如「A，B」），每项须能在摘要中找到依据；"
            "不得编造摘要中没有的制度、战役、人物或精确数字。\n"
            "参考格式示例：%s\n"
            "只输出 JSON：{\"headline_zh\": \"...\"}\n\n"
            "【季度结算摘要】\n%s"
        ) % (_FEW_SHOT_TITLE.split("——", 1)[-1], data)
    else:
        user = (
            "根据下列【季度结算摘要】撰写完整《朝政纪要》正文 body_zh。\n"
            "体例：史官奏报；开篇说明本季是否颁诏；分「一、二、…」叙述本季大事；"
            "若 settlement_summary 含 quarter_edict_actions，须逐条覆盖其中 status 非 needs_clarification 的诏令分项"
            "（other 写制度/物政落地，agent_a_selected 为 true 的 contest/counter 段融入 agent_narrative_bundle）；"
            "指标须写为 X→Y；最后一节为「后续局势研判」，仅用 outlook 字段，"
            "语气用「预计」「或」「望早筹谋」。\n"
            "特别注意：若存在 agent_narrative_bundle，请将其中的 contest/counter 对手反馈、risk_level、main_risk_zh、engine_hints.affected_systems 自然融入相应「一、二…」段落，作为诏令引发的朝野博弈与次生影响。\n"
            "不得编造摘要外的事实或数值。若已提供 headline_zh，标题与之呼应。\n"
            "只输出 JSON：{\"body_zh\": \"...\", \"highlights_zh\": [\"...\"]}\n\n"
            "【季度结算摘要】\n%s"
        ) % data
    return [
        {
            "role": "system",
            "content": (
                "你是宋代史官，撰写皇帝阅览的朝政纪要（熙宁变法语境）。"
                "只根据给定 JSON 事实写作，不输出 gameplay 指令或 effects。"
            ),
        },
        {"role": "user", "content": user},
    ]


def render_llm_memorial(summary: QuarterSettlementSummary) -> Dict[str, Any]:
    fallback = render_template_memorial(summary)
    if quarter_narrative_mode() == "template":
        return fallback
    if not (os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip():
        out = dict(fallback)
        out["mode"] = "template_no_api_key"
        return out

    headline = fallback["headline_zh"]
    try:
        h_raw = _call_quarter_llm(_build_messages(summary, step="headline"))
        h_obj = _parse_llm_json(h_raw)
        if h_obj and str(h_obj.get("headline_zh") or "").strip():
            headline = str(h_obj["headline_zh"]).strip()
    except Exception:
        pass

    title = "%s朝政纪要——%s" % (summary.quarter_label_zh, headline)
    body = fallback["body_zh"]
    highlights = list(fallback.get("highlights_zh") or [])
    try:
        b_raw = _call_quarter_llm(_build_messages(summary, step="body"))
        b_obj = _parse_llm_json(b_raw)
        if b_obj:
            if str(b_obj.get("body_zh") or "").strip():
                body = str(b_obj["body_zh"]).strip()
            hl = b_obj.get("highlights_zh")
            if isinstance(hl, list) and hl:
                highlights = [str(x) for x in hl[:4]]
    except Exception:
        pass

    return {
        "title_zh": title,
        "headline_zh": headline,
        "body_zh": body,
        "summary_zh": body[:320] + ("…" if len(body) > 320 else ""),
        "highlights_zh": highlights,
        "mode": "llm",
    }
