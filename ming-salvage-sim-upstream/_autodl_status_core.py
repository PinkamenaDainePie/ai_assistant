# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"
OUT = "/root/autodl-tmp/work/salvage_faithfulness/runs/ablation_core_autodl"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = f"""
set +e
echo === vllm ===
curl -sS -o /dev/null -w '%{{http_code}}\\n' --max-time 5 http://127.0.0.1:8000/v1/models
echo === procs ===
ps -ef | grep -E 'run_ablation|api_server|_worker_' | grep -v grep | head -15
echo === progress ===
grep -E '^==== SPAWN|^######## COND|elapsed=|ERROR|设定文件' {OUT}/run.log | tail -25
echo === lines ===
wc -l {OUT}/ablation_A.jsonl {OUT}/ablation_B.jsonl {OUT}/ablation_C.jsonl 2>/dev/null
echo === summary ===
test -f {OUT}/summary.json && echo HAS_SUMMARY || echo NO_SUMMARY
echo === gpu ===
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
echo === logtail ===
tail -n 20 {OUT}/run.log
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
