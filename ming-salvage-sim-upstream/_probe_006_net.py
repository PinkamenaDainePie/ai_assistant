# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE_CMD = r"""
set +e
echo '=== PROXY / GATEWAY LISTEN ==='
ss -lntp 2>/dev/null | grep -E ':(7890|18080|18081|28080)\b' || echo none
ps -ef | grep -E 'llm_gateway|proxy_fwd|clash|v2ray|sing-box' | grep -v grep | head -15
echo '=== CURL DIRECT / VIA PROXY ==='
curl -sS -o /dev/null -w 'direct:%{http_code} t=%{time_total}\n' --max-time 15 https://dashscope.aliyuncs.com/ 2>&1
curl -sS -o /dev/null -w 'proxy7890:%{http_code} t=%{time_total}\n' --max-time 15 -x http://127.0.0.1:7890 https://dashscope.aliyuncs.com/ 2>&1
echo '=== LLAMA WEIGHTS ELSEWHERE ==='
find /home/async/data-disk -maxdepth 4 -type d \( -iname '*Llama-3.1*' -o -iname '*llama3.1*' -o -iname '*Meta-Llama-3*' \) 2>/dev/null | head -20
ls /home/async/data-disk/wjf 2>/dev/null | head -20
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, stdout, stderr = client.exec_command(REMOTE_CMD, timeout=90)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
