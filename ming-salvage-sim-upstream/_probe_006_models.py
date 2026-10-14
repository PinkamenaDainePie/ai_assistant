# -*- coding: utf-8 -*-
"""Probe 006 for local / available LLM endpoints. Does not print full secrets."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE_CMD = r"""
set +e
echo '=== HOST ==='
hostname; date; whoami
echo '=== GPU ==='
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader 2>&1 | head -20
echo '=== LISTEN LLM-ish PORTS ==='
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(11434|8000|8001|8080|8888|9000|5000|6006|7860|3000|1234|7000|7001)\b' || echo 'no common ports'
echo '=== PROCESSES ==='
ps -ef | grep -Ei 'vllm|ollama|tgi|text-generation|sglang|llama.cpp|api_server|openai' | grep -v grep | head -30 || echo none
echo '=== OLLAMA ==='
command -v ollama; ollama list 2>&1 | head -20
curl -sS --max-time 5 http://127.0.0.1:11434/api/tags 2>&1 | head -c 800; echo
echo '=== OPENAI COMPAT /v1/models ==='
for p in 8000 8001 8080 9000 5000 7000 1234; do
  code=$(curl -sS -o "/tmp/m_$p.json" -w '%{http_code}' --max-time 3 "http://127.0.0.1:$p/v1/models" 2>/dev/null || echo fail)
  echo "port $p -> HTTP $code"
  if [ "$code" = "200" ]; then head -c 600 "/tmp/m_$p.json"; echo; fi
done
echo '=== ENV MODEL NAMES ==='
for f in \
  /home/async/data-disk/ljc/ming-salvage-sim-upstream/.env \
  /home/async/data-disk/ljc/.env.program2 \
  /home/async/data-disk/ljc/MCST/.env.program2
do
  if [ -f "$f" ]; then
    echo "FILE $f"
    grep -E 'MODEL|BASE_URL|OPENAI_|OLLAMA|VLLM' "$f" 2>/dev/null \
      | sed -E 's/(KEY|TOKEN|SECRET|PASSWORD)=.*/\1=***/I' | head -40
  fi
done
echo '=== LJC TOP ==='
ls /home/async/data-disk/ljc 2>/dev/null | head -40
echo '=== MODEL-ISH DIRS ==='
find /home/async/data-disk/ljc -maxdepth 3 -type d \( -iname '*model*' -o -iname '*checkpoint*' -o -iname '*ollama*' -o -iname '*vllm*' -o -iname 'huggingface' \) 2>/dev/null | head -40
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
        print("STDERR", err[-1000:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
