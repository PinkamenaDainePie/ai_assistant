# -*- coding: utf-8 -*-
"""AI 助教智能体：GraphRAG 检索 + LLM 生成。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .config import (
    DASHSCOPE_API_BASE,
    DASHSCOPE_API_KEY,
    GRAPH_RAG_TOP_K,
    LLM_REQUEST_TIMEOUT,
    TUTOR_LLM_MODEL,
)
from .neo4j_store import format_graph_context, graph_retrieve, neo4j_status

TUTOR_SYSTEM = """你是《中国财税史》智慧课堂的 AI 助教。
你的职责是帮助学生梳理概念、建立时间线、比较中西视角，并澄清「理财」与「聚敛」等评价性概念。
要求：
- 用中立、清晰的教师口吻，不要扮演历史人物第一人称。
- 优先依据下方「GraphRAG 知识图谱上下文」作答；可适度补充通识，但勿编造无出处的具体数字或史料。
- 回答结构：先给出核心结论，再分点展开；若涉及比较，请点明维度。
- 若上下文不足，请明确说明并给出可进一步查阅的方向。
- 篇幅适中，避免空泛套话。"""


def _call_llm(messages: List[Dict[str, str]], api_key: str, base_url: str, model: str) -> str:
    """复用 OpenAI 兼容调用（与 renwu_module 一致）。"""
    import urllib.error
    import urllib.request

    timeout = LLM_REQUEST_TIMEOUT

    def _http() -> str:
        url = (base_url or "").rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 1200,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'sk-placeholder'}",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode("utf-8", errors="ignore")
            except Exception:
                raw = str(e)
            raise RuntimeError(f"LLM HTTPError: {e.code} {raw}") from e
        obj = json.loads(raw)
        choices = obj.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()

    try:
        from openai import OpenAI

        try:
            client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url, timeout=timeout)
        except TypeError:
            client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=1200,
        )
        choice = resp.choices[0] if resp.choices else None
        if not choice or not getattr(choice, "message", None):
            return ""
        return (choice.message.content or "").strip()
    except (ImportError, AttributeError):
        try:
            import openai

            openai.api_key = api_key or "sk-placeholder"
            openai.api_base = base_url
            chat_completion = getattr(openai, "ChatCompletion", None)
            if chat_completion is None:
                return _http()
            resp = chat_completion.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=1200,
            )
            choices = getattr(resp, "choices", None) or resp.get("choices", [])
            choice = choices[0] if choices else None
            if not choice:
                return ""
            msg = getattr(choice, "message", None) or choice.get("message", {})
            content = getattr(msg, "content", None) or (
                msg.get("content") if isinstance(msg, dict) else None
            )
            return (content or "").strip()
        except ImportError:
            return _http()


def _build_messages(
    user_message: str,
    graph_context: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    system = TUTOR_SYSTEM + "\n\n---\n\n" + graph_context
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for turn in chat_history or []:
        role = turn.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        content = (turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def tutor_reply(
    user_message: str,
    *,
    chat_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = GRAPH_RAG_TOP_K,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    GraphRAG + Neo4j 助教回复。

    返回:
      reply, graph_context, citations, retrieved_count, graph_backend, neo4j_status
    """
    api_key = api_key or DASHSCOPE_API_KEY
    base_url = base_url or DASHSCOPE_API_BASE
    model = model or TUTOR_LLM_MODEL

    retrieval = graph_retrieve(user_message, top_k=top_k)
    graph_context = format_graph_context(retrieval)

    citations = []
    for n in retrieval.get("nodes") or []:
        citations.append(
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "era": n.get("era"),
                "summary": (n.get("summary") or "")[:160],
            }
        )
    for c in retrieval.get("communities") or []:
        citations.append(
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "era": "主题社区",
                "summary": (c.get("summary") or "")[:160],
            }
        )

    if not api_key or (isinstance(api_key, str) and "placeholder" in api_key.lower()):
        return {
            "reply": (
                "未配置 LLM API Key，无法生成回答。"
                "请在项目根 `.env` 设置 DASHSCOPE_API_KEY 后重启后端。"
                f"\n\n（GraphRAG 已检索到 {len(citations)} 条图谱上下文，后端：{retrieval.get('backend', 'memory')}）"
            ),
            "graph_context": graph_context,
            "citations": citations,
            "retrieved_count": len(citations),
            "graph_backend": retrieval.get("backend", "memory"),
            "neo4j_status": neo4j_status(),
        }

    messages = _build_messages(user_message, graph_context, chat_history)
    reply_text = _call_llm(messages, api_key, base_url, model)

    return {
        "reply": reply_text or "（模型未返回内容）",
        "graph_context": graph_context,
        "citations": citations,
        "retrieved_count": len(citations),
        "graph_backend": retrieval.get("backend", "memory"),
        "neo4j_status": neo4j_status(),
    }
