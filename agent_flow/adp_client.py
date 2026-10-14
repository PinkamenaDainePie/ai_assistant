# -*- coding: utf-8 -*-
"""腾讯云 ADP 旧版 HTTP SSE 客户端（Workflow A / B 共用传输层）。"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent_flow.config import AGENT_FLOW_BOT_APP_KEY, AGENT_FLOW_SSE_TIMEOUT, AGENT_FLOW_SSE_URL

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")
_WORKFLOW_REPLY_METHODS = {16, 17, 18, 23}
class AdpClientError(Exception):
    """ADP 调用或解析失败。"""


def _normalize_session_id(game_session_id: str, session_id: str) -> str:
    for candidate in (game_session_id, session_id, "anonymous"):
        sid = (candidate or "").strip()
        if sid and _SESSION_ID_RE.match(sid):
            return sid
    return str(uuid.uuid4())


def build_workflow_a_content(payload: Dict[str, Any]) -> str:
    """将 Workflow A 约定字段序列化为 JSON 字符串（写入 HTTP content / SYS.userQuery）。

    标准字段见 agent_flow/AGENT_A_IO.md；地区/战弧字段由 enrich_workflow_a_payload 注入。
    """
    body = {
        "game_session_id": payload.get("game_session_id") or "",
        "session_id": payload.get("session_id") or "",
        "quarter_index": int(payload.get("quarter_index") or 0),
        "edict_text": payload.get("edict_text") or "",
        "execution_context": dict(payload.get("execution_context") or {}),
        "resolved_pack": dict(payload.get("resolved_pack") or {}),
        "metrics": dict(payload.get("metrics") or {}),
        "flags": dict(payload.get("flags") or {}),
        "task_state": list(payload.get("task_state") or []),
        "policy_nodes": list(payload.get("policy_nodes") or []),
        "agent_a_selected_tasks": list(payload.get("agent_a_selected_tasks") or []),
        "region_status": dict(payload.get("region_status") or {}),
        "region_map_view": list(payload.get("region_map_view") or []),
        "region_catalog": list(payload.get("region_catalog") or []),
        "war_arcs": dict(payload.get("war_arcs") or {}),
    }
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def build_adp_sse_http_body(
    *,
    request_id: str,
    session_id: str,
    bot_app_key: str,
    content: str,
    stream: str = "disable",
) -> Dict[str, Any]:
    """按 ADP 旧版 SSE 文档组装 HTTP Body；业务 JSON 整包放入 content。"""
    return {
        "request_id": request_id,
        "session_id": session_id,
        "visitor_biz_id": session_id,
        "bot_app_key": bot_app_key,
        "content": content,
        "file_infos": [],
        "workflow_status": "enable",
        "stream": stream,
        "incremental": False,
        "search_network": "",
    }


def normalize_agent_flow_report(obj: Any) -> Dict[str, Any]:
    """解包 merged_output / result 等 ADP 工作流常见外层。"""
    if not isinstance(obj, dict):
        raise AdpClientError("AgentFlow 输出不是 JSON 对象")
    result = obj.get("result")
    if isinstance(result, dict):
        obj = {**obj, **{k: v for k, v in result.items() if k not in obj or obj.get(k) in (None, "", {})}}
    merged = obj.get("merged_output")
    if isinstance(merged, dict):
        out = dict(merged)
        for key in (
            "proposals",
            "updated_action_flow_state",
            "route_mode",
            "status",
            "contest",
            "counter",
            "engine_hints",
            "primary_action",
            "merged_result",
        ):
            if key in obj and key not in out:
                out[key] = obj[key]
        return out
    if merged is None and isinstance(obj.get("proposals"), dict):
        return dict(obj)
    outer = obj.get("Output")
    if isinstance(outer, dict):
        inner = outer.get("Output")
        if isinstance(inner, dict):
            return normalize_agent_flow_report(inner)
        return normalize_agent_flow_report(outer)
    return dict(obj)


def iter_sse_events(raw: str) -> Iterator[Tuple[str, str]]:
    """解析 text/event-stream 为 (event_name, data_json)。"""
    event_name: Optional[str] = None
    data_lines: List[str] = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            if data_lines:
                yield (event_name or "message", "\n".join(data_lines))
                data_lines = []
            event_name = line[len("event:") :].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
            continue
        if line == "" and data_lines:
            yield (event_name or "message", "\n".join(data_lines))
            event_name = None
            data_lines = []
    if data_lines:
        yield (event_name or "message", "\n".join(data_lines))


def _parse_event_data(data: str) -> Any:
    text = (data or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _payload_from_reply_event(obj: Any) -> Optional[Dict[str, Any]]:
    if isinstance(obj, list) and len(obj) >= 2 and isinstance(obj[1], dict):
        return dict(obj[1])
    if isinstance(obj, dict):
        if isinstance(obj.get("payload"), dict):
            return dict(obj["payload"])
        return dict(obj)
    return None


def extract_from_workflow_outputs(
    payload: Dict[str, Any],
    normalize: Callable[[Any], Dict[str, Any]],
) -> Dict[str, Any]:
    """优先从 work_flow.outputs 解析工作流 JSON 输出。"""
    wf = dict(payload.get("work_flow") or {})
    outputs = wf.get("outputs") or []
    if isinstance(outputs, list):
        for raw in reversed(outputs):
            if raw is None:
                continue
            text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
            text = text.strip()
            if not text:
                continue
            try:
                return normalize(json.loads(text))
            except (json.JSONDecodeError, AdpClientError, TypeError, ValueError):
                continue

    content = (payload.get("content") or "").strip()
    if content.startswith("{") or content.startswith("["):
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return normalize(parsed)

    node = dict(wf.get("current_node") or {})
    for key in ("Output", "TaskOutput", "Reply"):
        raw = (node.get(key) or "").strip()
        if raw.startswith("{"):
            return normalize(json.loads(raw))

    raise AdpClientError("reply 中未找到可解析的工作流 JSON（work_flow.outputs / content / current_node）")


def parse_workflow_sse(
    raw: str,
    normalize: Callable[[Any], Dict[str, Any]],
) -> Dict[str, Any]:
    """从旧版 SSE 响应中提取工作流终端 JSON。"""
    bot_replies: List[Dict[str, Any]] = []

    for event_name, data in iter_sse_events(raw):
        obj = _parse_event_data(data)
        if obj is None:
            continue
        if event_name == "error" or (isinstance(obj, dict) and obj.get("type") == "error"):
            err = obj.get("error") if isinstance(obj, dict) else None
            if isinstance(err, dict):
                raise AdpClientError("ADP error %s: %s" % (err.get("code"), err.get("message")))
            raise AdpClientError("ADP error event")

        if event_name != "reply" and not (isinstance(obj, dict) and obj.get("type") == "reply"):
            continue

        payload = _payload_from_reply_event(obj)
        if not payload:
            continue

        if payload.get("is_evil"):
            raise AdpClientError("ADP 敏感内容拦截: %s" % (payload.get("content") or "")[:120])

        if payload.get("is_from_self"):
            continue

        reply_method = payload.get("reply_method")
        if reply_method in (4, 7):
            raise AdpClientError("ADP reply_method=%s" % reply_method)

        if payload.get("is_final"):
            bot_replies.append(payload)

    if not bot_replies:
        raise AdpClientError("SSE 未收到 is_final=true 的 bot reply")

    for payload in reversed(bot_replies):
        try:
            return extract_from_workflow_outputs(payload, normalize)
        except AdpClientError:
            continue

    return extract_from_workflow_outputs(bot_replies[-1], normalize)


def call_adp_workflow_sse(
    *,
    bot_app_key: str,
    content: str,
    game_session_id: str = "",
    session_id: str = "",
    request_id: Optional[str] = None,
    normalize: Callable[[Any], Dict[str, Any]],
    workflow_label: str = "adp",
) -> Dict[str, Any]:
    """调用 ADP 旧版 SSE，返回 normalize 后的工作流输出 dict。

    业务 JSON 整包写入 HTTP content（ADP 侧映射为 SYS.userQuery）。
    """
    app_key = (bot_app_key or "").strip()
    if not app_key:
        raise AdpClientError("bot_app_key 未配置")

    sid = _normalize_session_id(game_session_id, session_id)
    req_id = (request_id or str(uuid.uuid4())).strip()
    stream = "disable"
    payload_json = (content or "").strip()
    if not payload_json:
        raise AdpClientError("content 不能为空")

    body = build_adp_sse_http_body(
        request_id=req_id,
        session_id=sid,
        bot_app_key=app_key,
        content=payload_json,
        stream=stream,
    )
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(
        AGENT_FLOW_SSE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=AGENT_FLOW_SSE_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read().decode(charset, errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AdpClientError("HTTP %s: %s" % (exc.code, detail)) from exc
    except URLError as exc:
        raise AdpClientError("网络错误: %s" % exc.reason) from exc

    report = parse_workflow_sse(raw, normalize)
    report["_adp_trace"] = {
        "source": "adp_sse",
        "workflow": workflow_label,
        "request_id": req_id,
        "conversation_id": sid,
        "content_len": len(payload_json),
        "content_is_json": payload_json.startswith("{"),
    }
    return report


def extract_report_from_reply_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return extract_from_workflow_outputs(payload, normalize_agent_flow_report)


def parse_agent_flow_sse(raw: str) -> Dict[str, Any]:
    return parse_workflow_sse(raw, normalize_agent_flow_report)


def call_agent_flow_sse(
    *,
    payload: Dict[str, Any],
    game_session_id: str = "",
    session_id: str = "",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """调用 ADP Workflow A，返回 AgentFlowReport dict。"""
    report = call_adp_workflow_sse(
        bot_app_key=AGENT_FLOW_BOT_APP_KEY,
        content=build_workflow_a_content(payload),
        game_session_id=game_session_id,
        session_id=session_id,
        request_id=request_id,
        normalize=normalize_agent_flow_report,
        workflow_label="agent_flow",
    )
    report.setdefault("session_id", session_id or report.get("_adp_trace", {}).get("conversation_id", ""))
    report.setdefault("quarter_index", int(payload.get("quarter_index") or 0))
    trace = dict(report.get("trace") or {})
    trace.update(dict(report.get("_adp_trace") or {}))
    report["trace"] = trace
    return report


def adp_agent_flow_enabled() -> bool:
    return bool((AGENT_FLOW_BOT_APP_KEY or "").strip())
