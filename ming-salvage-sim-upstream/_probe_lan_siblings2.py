# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE = r"""
set +e
for ip in 172.168.3.51 172.168.3.78 172.168.3.99 172.168.3.100 172.168.3.151; do
  echo "=== $ip ==="
  ping -c 1 -W 1 "$ip" >/dev/null 2>&1 && echo ping=up || echo ping=down
  for p in 22 11222 2222; do
    if timeout 1 bash -c "echo >/dev/tcp/$ip/$p" 2>/dev/null; then
      echo "port$p=open"
    else
      echo "port$p=closed"
    fi
  done
  timeout 4 ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=2 "async@$ip" \
    'hostname; nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader' 2>&1 | head -25
  timeout 4 ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=2 -p 11222 "async@$ip" \
    'hostname; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader' 2>&1 | head -15
done
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, stdout, stderr = client.exec_command(REMOTE, timeout=90)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
