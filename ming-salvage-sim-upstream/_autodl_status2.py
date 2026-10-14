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
echo '=== PROCS ==='
ps -ef | grep -E 'setup_vllm|snapshot|modelscope|vllm|pip' | grep -v grep | head -20
echo '=== DISK ==='
df -h /root/autodl-tmp
du -sh /root/autodl-tmp/* 2>/dev/null | sort -h | tail -20
echo '=== MODEL DIR ==='
ls -la /root/autodl-tmp/models 2>/dev/null
find /root/autodl-tmp/modelscope_cache -name '*.safetensors' 2>/dev/null | head
find /root/autodl-tmp/modelscope_cache -name '*.safetensors' -printf '%s %p\n' 2>/dev/null | awk '{s+=$1; n++} END{print "shards",n,"bytes",s}'
echo '=== LOG MARKERS ==='
grep -E '^\[|^DONE|^FATAL|downloaded_to|linked |vllm |Successfully installed vllm' /root/autodl-tmp/setup_vllm.log | tail -40
echo '=== LOG LAST NON-PROGRESS ==='
grep -v 'safetensors\|MB/s\|it/s' /root/autodl-tmp/setup_vllm.log | tail -30
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
