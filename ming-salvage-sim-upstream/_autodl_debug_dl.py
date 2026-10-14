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
set +e
echo '=== TREE PID 1537 ==='
pstree -p 1537 2>/dev/null || ps --forest -g $(ps -o sid= -p 1537) 2>/dev/null
ps -o pid,ppid,stat,etime,cmd -p 1537
pgrep -P 1537 -a || echo 'no children'
echo '=== CACHE TREE ==='
find /root/autodl-tmp/modelscope_cache -maxdepth 5 -type f 2>/dev/null | head -40
du -sh /root/autodl-tmp/modelscope_cache/* 2>/dev/null | head -20
echo '=== LOG BYTES / MTIME ==='
ls -la /root/autodl-tmp/setup_vllm.log
wc -l /root/autodl-tmp/setup_vllm.log
# last 5kb raw
tail -c 2000 /root/autodl-tmp/setup_vllm.log | tr '\r' '\n' | tail -40
echo '=== STRACE? skip ==='
# if hung python, show open files
ls -l /proc/1537/fd 2>/dev/null | head -20
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    print(e.read().decode("utf-8", "replace")[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
