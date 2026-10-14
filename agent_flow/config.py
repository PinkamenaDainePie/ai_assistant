# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        for path in (ROOT / ".env", Path.cwd() / ".env"):
            if path.exists():
                load_dotenv(path, override=True)
                break
    except ImportError:
        pass


_load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
AGENT_FLOW_USE_LANGGRAPH = (os.getenv("AGENT_FLOW_USE_LANGGRAPH") or "1").strip().lower() in (
    "1",
    "true",
    "yes",
)
AGENT_FLOW_AUTO_CREATE_TABLES = (os.getenv("AGENT_FLOW_AUTO_CREATE_TABLES") or "1").strip().lower() in (
    "1",
    "true",
    "yes",
)

# 腾讯云 ADP Workflow A（旧版 HTTP SSE）
AGENT_FLOW_BOT_APP_KEY = (os.getenv("AGENT_FLOW_BOT_APP_KEY") or "").strip()
AGENT_FLOW_SSE_URL = (
    os.getenv("AGENT_FLOW_SSE_URL") or "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse"
).strip()
AGENT_FLOW_SSE_TIMEOUT = max(30, int(os.getenv("AGENT_FLOW_SSE_TIMEOUT") or "300"))

# 腾讯云 ADP Workflow B（季度总结，旧版 HTTP SSE）
QUARTER_NARRATIVE_BOT_APP_KEY = (os.getenv("QUARTER_NARRATIVE_BOT_APP_KEY") or "").strip()

# 腾讯云 ADP Workflow C（结局总结，旧版 HTTP SSE）
ENDING_SUMMARY_BOT_APP_KEY = (os.getenv("ENDING_SUMMARY_BOT_APP_KEY") or "").strip()
