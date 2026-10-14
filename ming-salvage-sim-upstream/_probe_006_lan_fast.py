# -*- coding: utf-8 -*-
"""Fast LAN neighbor GPU probe from 006."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE = r"""
set +e
echo '=== ARP / NEIGH eno1 ==='
ip neigh show dev eno1 nud reachable nud stale nud delay nud probe 2>/dev/null
ip neigh show dev eno1 2>/dev/null | head -100

echo '=== fping or parallel ping subset ==='
# Prefer nmap if present
if command -v nmap >/dev/null; then
  nmap -sn -T4 172.168.3.0/24 2>/dev/null | grep -E 'Nmap scan report|Host is up' | head -80
elif command -v fping >/dev/null; then
  fping -a -q -g 172.168.3.0/24 2>/dev/null
else
  # 40-way parallel, one pass
  for i in $(seq 1 254); do
    (ping -c 1 -W 1 172.168.3.$i >/dev/null 2>&1 && echo 172.168.3.$i) &
    if [ $((i % 50)) -eq 0 ]; then wait; fi
  done
  wait
fi

echo '=== check 22/11222 on neighbors from neigh table ==='
ips=$(ip neigh show dev eno1 2>/dev/null | awk '{print $1}' | grep -E '^172\.168\.3\.' | sort -u)
for ip in $ips; do
  [ "$ip" = "172.168.3.150" ] && continue
  o22=no; o11222=no
  timeout 1 bash -c "echo >/dev/tcp/$ip/22" 2>/dev/null && o22=yes
  timeout 1 bash -c "echo >/dev/tcp/$ip/11222" 2>/dev/null && o11222=yes
  echo "$ip ssh22=$o22 ssh11222=$o11222"
done
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, stdout, stderr = client.exec_command(REMOTE, timeout=120)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
