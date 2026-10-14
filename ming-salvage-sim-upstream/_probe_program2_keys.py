# -*- coding: utf-8 -*-
"""Probe Program2-related DashScope keys without printing full secrets."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CANDIDATES: list[tuple[str, str, str]] = []

# current program2
p2 = Path(r"E:\program2\src\config\.env")
bak = Path(r"E:\program2\src\config\.env.env.bak_before_key_switch")
local_yaml_key = "sk-9f74da14e9b94c8d8a80748fc7e64442"

def add(label: str, key: str, model: str) -> None:
    if key and not any(k == key for _, k, _ in CANDIDATES):
        CANDIDATES.append((label, key, model))

for path, label in ((p2, "program2.current"), (bak, "program2.bak_key_switch")):
    if not path.is_file():
        continue
    d: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        d[k.strip()] = v.strip()
    add(label + ".qwen", d.get("PAPERAI_LLM_QWEN_API_KEY", ""), d.get("PAPERAI_LLM_QWEN_MODEL_NAME", "qwen3.7-plus"))

add("config.local.yaml", local_yaml_key, "qwen3.7-plus")

# ai_assistant root
ai_env = Path(r"e:\ai_assistant\.env")
if ai_env.is_file():
    d = {}
    for raw in ai_env.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    add("ai_assistant.env", d.get("DASHSCOPE_API_KEY", ""), d.get("DEFAULT_LLM_MODEL", "qwen-plus"))

for label, key, model in CANDIDATES:
    try:
        with httpx.Client(timeout=45.0) as c:
            r = c.post(
                BASE.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 4},
            )
        snippet = r.text[:160].replace("\n", " ")
        print(f"{label}: key***{key[-4:]} model={model} -> {r.status_code} {snippet}")
    except Exception as e:
        print(f"{label}: key***{key[-4:]} model={model} -> EXC {type(e).__name__}: {e}")
