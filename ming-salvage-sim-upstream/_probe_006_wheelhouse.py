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
WH=/home/async/data-disk/ljc/_wheelhouse_linux.tgz
ls -lh "$WH"
# list matching names without full extract
tar -tzf "$WH" 2>/dev/null | grep -iE 'vllm|torch-|triton' | head -40
echo 'count:' $(tar -tzf "$WH" 2>/dev/null | wc -l)
echo '=== autodl disk risk ==='
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, o, e = c.exec_command(REMOTE, timeout=120)
    print(o.read().decode("utf-8", "replace"))
    print(e.read().decode("utf-8", "replace")[-400:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
