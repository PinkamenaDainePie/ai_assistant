# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = r"""
set +e
echo === conda envs ===
ls /home/async/data-disk/miniconda3/envs 2>/dev/null
echo === find vllm ===
ls /home/async/data-disk/miniconda3/envs/*/lib/python*/site-packages/vllm 2>/dev/null | head
find /home/async/data-disk/miniconda3/envs -maxdepth 3 -name 'vllm' -type d 2>/dev/null | head
for env in /home/async/data-disk/miniconda3/envs/*/bin/python; do
  [ -x "$env" ] || continue
  out=$($env -c 'import vllm; print(vllm.__version__)' 2>/dev/null) || continue
  echo FOUND $env vllm=$out
done
echo === pydeps ===
ls /home/async/data-disk/ljc/pydeps 2>/dev/null | head -20
echo === models local ===
ls /home/async/data-disk/ljc/models 2>/dev/null | head
echo === salvage .env keys only ===
grep -E '^(OPENAI_BASE_URL|OPENAI_MODEL|OPENAI_API_KEY)=' /home/async/data-disk/ljc/ming-salvage-sim-upstream/.env 2>/dev/null | sed 's/KEY=.*/KEY=***/'
echo === outnet ping ===
curl -sS -o /dev/null -w 'baidu=%{http_code}\n' --max-time 5 https://www.baidu.com || echo baidu_fail
curl -sS -o /dev/null -w 'pypi=%{http_code}\n' --max-time 5 https://pypi.org || echo pypi_fail
"""
    _, o, e = c.exec_command(cmd, timeout=120)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
