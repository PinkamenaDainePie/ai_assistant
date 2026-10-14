# -*- coding: utf-8 -*-
"""Diagnose m1k hang/timeouts on 006."""
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
echo === jsonl sample A ===
/home/async/data-disk/ljc/salvage-bench-venv313/bin/python - <<'PY'
import json
from pathlib import Path
from collections import Counter
p=Path('{OUT}/cond_A/ablation_A.jsonl')
rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
print('n', len(rows))
print('errors', Counter((r.get('error') or 'ok') for r in rows))
for r in rows[:3]:
    print('---', r.get('case_id'), 'err', r.get('error'), 'elapsed', r.get('elapsed_sec'))
    print('keys', sorted(r.keys())[:20])
PY
echo === workers ===
ps -ef | grep _worker_ | grep -v grep | head
echo === worker files ===
ls -lt /home/async/data-disk/ljc/salvage_faithfulness/runs/_workers 2>/dev/null | head -15
echo === tail run A ===
tail -n 80 {OUT}/cond_A/run.log
echo === curl chat smoke ===
curl -sS --max-time 60 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{{"model":"qwen2.5-7b-instruct","messages":[{{"role":"user","content":"ping"}}],"max_tokens":8}}' | head -c 500
echo
echo === vllm logtail ===
tail -n 30 /home/async/data-disk/ljc/vllm_8000.log
echo === gpu ===
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
"""
    _, o, e = c.exec_command(cmd, timeout=120)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-1000:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
