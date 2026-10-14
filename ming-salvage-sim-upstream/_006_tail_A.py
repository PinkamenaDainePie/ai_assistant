# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = r"""
echo === workers ===
ps -ef | grep _worker_ | grep -v grep | head
echo === logtail ===
tail -n 60 /home/async/data-disk/ljc/salvage_faithfulness/runs/ablation_m1k_006/cond_A/run.log
echo === vllm recent ===
tail -n 15 /home/async/data-disk/ljc/vllm_8000.log
echo === quick chat ===
time curl -sS --max-time 30 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"只回复ok"}],"max_tokens":4}' | head -c 200
echo
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
