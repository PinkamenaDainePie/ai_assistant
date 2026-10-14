# -*- coding: utf-8 -*-
"""Stop heavy m1k serial run on 006; keep vLLM optional."""
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
set +e
pkill -9 -f 'serial_supervisor' || true
pkill -9 -f 'salvage_bench.run_ablation' || true
pkill -9 -f 'salvage_faithfulness/runs/_workers' || true
pkill -9 -f '_worker_' || true
sleep 2
echo === left ===
ps -ef | grep -E 'run_ablation|serial_supervisor|_worker_' | grep -v grep || echo none
echo === progress kept ===
wc -l /home/async/data-disk/ljc/salvage_faithfulness/runs/ablation_m1k_006/cond_*/ablation_*.jsonl 2>/dev/null
ls /home/async/data-disk/ljc/salvage_faithfulness/runs/ablation_m1k_006/ 2>/dev/null
"""
    _, o, e = c.exec_command(cmd, timeout=40)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-400:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
