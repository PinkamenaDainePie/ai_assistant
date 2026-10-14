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
ps -ef | grep -E 'setup_vllm|pip|vllm' | grep -v grep | head -20
echo '=== DISK ==='
df -h / /root/autodl-tmp
echo '=== LOG TAIL ==='
tail -n 50 /root/autodl-tmp/setup_vllm.log 2>/dev/null || echo no-log
echo '=== VLLM PORT ==='
curl -sS -o /dev/null -w 'models:%{http_code}\n' --max-time 3 http://127.0.0.1:8000/v1/models || echo models:fail
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader 2>/dev/null
"""
    _, o, e = c.exec_command(cmd, timeout=30)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
