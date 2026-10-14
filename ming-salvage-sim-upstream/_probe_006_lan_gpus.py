# -*- coding: utf-8 -*-
"""Scan 006 LAN for other hosts with nvidia-smi / ssh."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

# Parallel-ish ping + ssh batch on 172.168.3.0/24; also 200.200.200.0/24 tun peers
REMOTE = r"""
set +e
echo '=== PING 172.168.3.1-254 (alive) ==='
alive=""
for i in $(seq 1 254); do
  (ping -c 1 -W 1 172.168.3.$i >/dev/null 2>&1 && echo 172.168.3.$i) &
  # limit concurrency
  if [ $((i % 40)) -eq 0 ]; then wait; fi
done
wait

echo '=== SSH PORT OPEN ON ALIVE? ==='
# re-ping collect
for i in $(seq 1 254); do
  ping -c 1 -W 1 172.168.3.$i >/dev/null 2>&1 && echo 172.168.3.$i
done > /tmp/alive_lan.txt
wc -l /tmp/alive_lan.txt
cat /tmp/alive_lan.txt

while read ip; do
  # skip self
  [ "$ip" = "172.168.3.150" ] && continue
  code=$(timeout 2 bash -c "echo >/dev/tcp/$ip/22" 2>/dev/null && echo open22 || echo no22)
  code2=$(timeout 2 bash -c "echo >/dev/tcp/$ip/11222" 2>/dev/null && echo open11222 || echo no11222)
  echo "$ip $code $code2"
done < /tmp/alive_lan.txt

echo '=== ARP / NEIGH ==='
ip neigh show dev eno1 2>/dev/null | head -80

echo '=== TUN PEERS 200.200.200.x ==='
for i in 1 2 10 50 100 150 198 199 200 254; do
  ping -c 1 -W 1 200.200.200.$i >/dev/null 2>&1 && echo up 200.200.200.$i
done
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("[connect] 006", flush=True)
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    # LAN scan can take a bit
    _, stdout, stderr = client.exec_command(REMOTE, timeout=300)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
