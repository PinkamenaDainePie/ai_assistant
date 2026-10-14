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
find /root/autodl-tmp/work/ming-salvage-sim-upstream/ming_sim -maxdepth 3 -type f | sort
echo '--- local compare hint ---'
ls -la /root/autodl-tmp/work/ming-salvage-sim-upstream/ming_sim/ | head -50
echo '--- import ---'
/root/autodl-tmp/work/bench-venv/bin/python - <<'PY'
import sys
sys.path.insert(0, '/root/autodl-tmp/work/ming-salvage-sim-upstream')
import ming_sim.db as d
print('file', getattr(d, '__file__', None))
print('path', list(getattr(d, '__path__', [])))
print('attrs', [x for x in dir(d) if 'Game' in x or 'DB' in x])
try:
    from ming_sim.db import GameDB
    print('GameDB', GameDB)
except Exception as e:
    print('import err', type(e), e)
PY
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    print(e.read().decode("utf-8", "replace")[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
