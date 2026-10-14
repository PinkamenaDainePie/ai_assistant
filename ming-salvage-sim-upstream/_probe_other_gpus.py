# -*- coding: utf-8 -*-
"""Probe GPU occupancy on known SSH hosts (key-based)."""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import paramiko

HOSTS = [
    {
        "name": "006",
        "hostname": "202.115.17.216",
        "port": 11222,
        "user": "async",
        "password": "asdf@1234",
        "key": None,
    },
    {
        "name": "gpuhub-westc",
        "hostname": "connect.westc.gpuhub.com",
        "port": 43653,
        "user": "root",
        "password": None,
        "key": None,  # agent / default keys
    },
    {
        "name": "seetacloud-cqa1",
        "hostname": "connect.cqa1.seetacloud.com",
        "port": 35144,
        "user": "root",
        "password": None,
        "key": None,
    },
    {
        "name": "lab_3090",
        "hostname": "dpcau.686788.xyz",
        "port": 44415,
        "user": "server-3090-002",
        "password": None,
        "key": None,
    },
]

REMOTE = r"""
set +e
echo HOST=$(hostname)
echo DATE=$(date '+%F %T')
echo USER=$(whoami)
echo '--- nvidia-smi ---'
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>&1
echo '--- compute apps ---'
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader 2>&1
echo '--- top gpu procs ---'
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' ' | sort -u); do
  [ -n "$pid" ] || continue
  ps -o user=,pid=,etime=,cmd= -p "$pid" 2>/dev/null
done | head -40
"""


def _try_connect(h: dict) -> paramiko.SSHClient | None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(
        hostname=h["hostname"],
        port=h["port"],
        username=h["user"],
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
        banner_timeout=25,
        auth_timeout=25,
    )
    if h.get("password"):
        kwargs["password"] = h["password"]
        kwargs["allow_agent"] = False
        kwargs["look_for_keys"] = False
    try:
        client.connect(**kwargs)
        return client
    except Exception as e:
        print(f"[{h['name']}] CONNECT FAIL: {type(e).__name__}: {e}", flush=True)
        try:
            client.close()
        except Exception:
            pass
        return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for h in HOSTS:
        print(f"\n========== {h['name']} ({h['user']}@{h['hostname']}:{h['port']}) ==========", flush=True)
        # quick TCP
        try:
            with socket.create_connection((h["hostname"], h["port"]), timeout=8):
                pass
        except Exception as e:
            print(f"[{h['name']}] TCP FAIL: {e}", flush=True)
            continue
        client = _try_connect(h)
        if not client:
            continue
        try:
            _, stdout, stderr = client.exec_command(REMOTE, timeout=60)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            print(out)
            if err.strip():
                print("STDERR", err[-500:])
        except Exception as e:
            print(f"[{h['name']}] EXEC FAIL: {type(e).__name__}: {e}", flush=True)
        finally:
            client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
