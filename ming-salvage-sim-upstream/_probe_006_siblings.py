# -*- coding: utf-8 -*-
"""From 006: find sibling GPU hosts and their occupancy if reachable."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE = r"""
set +e
echo '=== LOCAL SSH CONFIG / KNOWN ==='
ls -la ~/.ssh 2>/dev/null | head -30
echo '--- config ---'
cat ~/.ssh/config 2>/dev/null | head -80
echo '--- known_hosts hosts ---'
awk '{print $1}' ~/.ssh/known_hosts 2>/dev/null | tr ',' '\n' | sort -u | head -40

echo '=== /etc/hosts (gpu-ish) ==='
grep -Ei 'gpu|3090|a100|4090|server|async|00[0-9]' /etc/hosts 2>/dev/null | head -40

echo '=== LAN SCAN HINTS ==='
ip -4 addr 2>/dev/null | head -40
ip route 2>/dev/null | head -20

echo '=== WHO / W / LAST ==='
who 2>/dev/null | head -20
w 2>/dev/null | head -20
last -n 15 2>/dev/null

echo '=== OTHER USERS GPU NOW (all cards) ==='
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_memory --format=csv,noheader 2>&1
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' ' | sort -u); do
  ps -o user=,pid=,etime=,cmd= -p "$pid" 2>/dev/null
done

echo '=== TRY COMMON SIBLING IPs (same /24) ==='
# discover local CIDR
CIDR=$(ip -4 route | awk '/src/ && /proto kernel/ {print $1; exit}')
echo CIDR=$CIDR
BASE=$(ip -4 addr show | awk '/inet /{print $2}' | head -1)
echo BASE=$BASE
# try ssh to a few likely neighbors if any in known_hosts with 202.115
for h in $(awk '{print $1}' ~/.ssh/known_hosts 2>/dev/null | tr ',' '\n' | grep -E '^[0-9.]+$' | sort -u | head -20); do
  echo -n "ping $h: "
  ping -c 1 -W 1 "$h" >/dev/null 2>&1 && echo up || echo down
done

echo '=== HOMEDIR OTHER SERVER NOTES ==='
ls /home 2>/dev/null
grep -RIlE '202\.115\.|1122[0-9]|gpuhub|seetacloud|3090' /home/async/data-disk/ljc --include='*.md' --include='*.txt' --include='*.sh' 2>/dev/null | head -30
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
        print("STDERR", err[-1000:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
