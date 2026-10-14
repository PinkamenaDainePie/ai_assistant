# -*- coding: utf-8 -*-
"""Deeper probe: :9000, models/, GPU1 owner, gateway."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE_CMD = r"""
set +e
echo '=== GPU1 PROCESS ==='
nvidia-smi -i 1 --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>&1
ps -fp $(nvidia-smi -i 1 --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' ' | paste -sd, -) 2>/dev/null | head -20

echo '=== PORT 9000 OWNER ==='
ss -lntp 2>/dev/null | grep ':9000' || true
fuser 9000/tcp 2>/dev/null; lsof -i :9000 2>/dev/null | head -10

echo '=== CURL 9000 ROOT / DOCS / HEALTH ==='
for path in / /health /v1 /v1/models /docs /openapi.json; do
  code=$(curl -sS -o "/tmp/p9000_resp" -w '%{http_code}' --max-time 3 "http://127.0.0.1:9000$path" 2>/dev/null || echo fail)
  echo "GET $path -> $code"
  head -c 400 /tmp/p9000_resp 2>/dev/null; echo
done

echo '=== LLM GATEWAY ==='
head -80 /home/async/data-disk/ljc/llm_gateway.py 2>/dev/null
echo '--- gateway log tail ---'
tail -30 /home/async/data-disk/ljc/llm_gateway.log 2>/dev/null
ps -ef | grep -i llm_gateway | grep -v grep | head -5

echo '=== MODELS DIR ==='
ls -lah /home/async/data-disk/ljc/models 2>/dev/null | head -40
du -sh /home/async/data-disk/ljc/models/* 2>/dev/null | head -40

echo '=== HUGGINGFACE CACHE ==='
ls -lah ~/.cache/huggingface/hub 2>/dev/null | head -30
du -sh ~/.cache/huggingface/hub 2>/dev/null

echo '=== OLLAMA MODELS ON DISK ==='
ls -lah ~/.ollama/models 2>/dev/null | head -20
du -sh ~/.ollama 2>/dev/null
find /home/async -maxdepth 4 -type d -name blobs 2>/dev/null | head -10

echo '=== DOCKER LLM ==='
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null | head -20 || echo no-docker

echo '=== RECENT VLLM/OLLAMA CMDS ==='
grep -E 'vllm|ollama serve|openai.api|uvicorn' /home/async/.bash_history 2>/dev/null | tail -20
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[connect] {USER}@{HOST}:{PORT}", flush=True)
    client.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASSWORD,
        timeout=40,
        allow_agent=False,
        look_for_keys=False,
    )
    _, stdout, stderr = client.exec_command(REMOTE_CMD, timeout=120)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print(out)
    if err.strip():
        print("STDERR", err[-1500:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
