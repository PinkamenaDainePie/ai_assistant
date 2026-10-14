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
set +e
# kill anything related under ljc salvage
ps -ef | awk '/salvage_bench.run_ablation|serial_supervisor|_worker_|ablation_m1k_006/ && !/awk/ {print $2}' | while read p; do
  echo kill $p
  kill -9 $p 2>/dev/null || true
done
sleep 1
ps -ef | grep -E 'run_ablation|serial_supervisor|_worker_' | grep -v grep || echo STOPPED
wc -l /home/async/data-disk/ljc/salvage_faithfulness/runs/ablation_m1k_006/cond_A/ablation_A.jsonl 2>/dev/null
"""
    _, o, e = c.exec_command(cmd, timeout=40)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-300:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
