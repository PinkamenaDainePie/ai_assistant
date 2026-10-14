# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = r"""
set +e
ps -ef | awk '/run_ablation|_worker_/ && !/awk/ {print $2}' | xargs -r kill -9
sleep 1
ps -ef | grep -E 'run_ablation|_worker_|vllm.entrypoints' | grep -v grep || echo none
echo ---
tail -n 15 /root/autodl-tmp/vllm_qwen7b.log
echo ---
curl -sS -o /dev/null -w 'http=%{http_code}\n' --max-time 5 http://127.0.0.1:8000/v1/models || echo http=fail
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
"""
    _, o, e = c.exec_command(cmd, timeout=40)
    print(o.read().decode("utf-8", "replace"))
    print(e.read().decode("utf-8", "replace")[-300:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
