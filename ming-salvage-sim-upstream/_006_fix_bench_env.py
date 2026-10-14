# -*- coding: utf-8 -*-
"""Find a Python on 006 that can import agno + ming_sim, and wheel tags."""
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
echo === conda py ===
/home/async/data-disk/miniconda3/bin/python -V
echo === wheel tags sample ===
ls /home/async/data-disk/ljc/ming-salvage-sim-upstream/wheelhouse_linux | grep -iE 'pydantic|agno|httpx' | head -40
echo === find agno in envs ===
for env in /home/async/data-disk/miniconda3/envs/*/bin/python; do
  out=$($env -c 'import agno; print(agno.__version__ if hasattr(agno,"__version__") else "ok")' 2>/dev/null) || continue
  ver=$($env -V 2>&1)
  echo FOUND $env agno=$out $ver
done
echo === salvage-bench-venv ===
/home/async/data-disk/ljc/salvage-bench-venv/bin/python -V 2>/dev/null
/home/async/data-disk/ljc/salvage-bench-venv/bin/pip list 2>/dev/null | head -40
echo === try clone env with agno via PYTHONPATH from site-packages ===
# list any site-packages containing agno
find /home/async/data-disk/miniconda3/envs -maxdepth 4 -type d -name agno 2>/dev/null | head
"""
    _, o, e = c.exec_command(cmd, timeout=180)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
