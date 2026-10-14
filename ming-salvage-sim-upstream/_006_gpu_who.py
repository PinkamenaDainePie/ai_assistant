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
nvidia-smi
echo === compute apps ===
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_gpu_memory --format=csv
echo === our procs ===
ps -ef | grep -E 'vllm|run_ablation|_worker_' | grep -v grep | head -20
echo === free estimate ===
nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
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
