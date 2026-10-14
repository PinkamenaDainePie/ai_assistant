# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"
OUT = "/home/async/data-disk/ljc/salvage_faithfulness/runs/ablation_m1k_006"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = f"""
set +e
echo === vllm ===
for p in 8000 8001 8002; do
  code=$(curl -sS -o /dev/null -w '%{{http_code}}' --max-time 3 http://127.0.0.1:$p/v1/models 2>/dev/null || echo x)
  echo port_$p=$code
done
echo === procs ===
ps -ef | grep -E 'run_ablation|api_server' | grep -v grep | head -20
echo === lines ===
wc -l {OUT}/cond_A/ablation_A.jsonl {OUT}/cond_B/ablation_B.jsonl {OUT}/cond_C/ablation_C.jsonl 2>/dev/null
echo === recent ===
for c in A B C; do
  echo --- $c ---
  grep -E '^\\[suite\\]|^########|^\\[ok\\]|^\\[ERROR\\]|^==== SPAWN' {OUT}/cond_$c/run.log 2>/dev/null | tail -8
done
echo === summary ===
for c in A B C; do
  test -f {OUT}/cond_$c/summary.json && echo HAS_$c || echo NO_$c
done
echo === gpu ===
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
"""
    _, o, e = c.exec_command(cmd, timeout=40)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
