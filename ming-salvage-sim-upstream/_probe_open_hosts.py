# -*- coding: utf-8 -*-
"""Try SSH (keys/agent) to reachable historical hosts; print nvidia if login works."""
from __future__ import annotations

import sys

import paramiko

TARGETS = [
    ("122.51.245.227", 22, ["root", "ubuntu", "async", "ljc"]),
    ("124.221.252.181", 22, ["root", "ubuntu", "async", "ljc"]),
    ("8.137.91.164", 22, ["root", "ubuntu", "async", "ljc"]),
]

CMD = "hostname; whoami; nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>&1 | head -20; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>&1 | head -20"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for host, port, users in TARGETS:
        print(f"\n===== {host}:{port} =====", flush=True)
        for user in users:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    host,
                    port=port,
                    username=user,
                    timeout=12,
                    allow_agent=True,
                    look_for_keys=True,
                    banner_timeout=12,
                    auth_timeout=12,
                )
            except Exception as e:
                print(f"  {user}: FAIL {type(e).__name__}: {e}", flush=True)
                try:
                    client.close()
                except Exception:
                    pass
                continue
            print(f"  {user}: OK", flush=True)
            try:
                _, stdout, stderr = client.exec_command(CMD, timeout=30)
                print(stdout.read().decode("utf-8", "replace"))
                err = stderr.read().decode("utf-8", "replace")
                if err.strip():
                    print("STDERR", err[:300])
            finally:
                client.close()
            break  # next host after first successful user
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
