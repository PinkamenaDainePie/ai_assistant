# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

FIND = r"""
set +e
for py in \
  /home/async/data-disk/ljc/ming-salvage-sim-upstream/.venv/bin/python \
  /home/async/data-disk/ljc/MCST/.venv/bin/python \
  /home/async/data-disk/miniconda3/bin/python \
  /home/async/data-disk/miniconda3/envs/LogTokU/bin/python \
  /usr/bin/python3
do
  [ -x "$py" ] || continue
  echo "TRY $py"
  "$py" -c 'import paramiko; print("paramiko", paramiko.__version__)' 2>&1
done
"""

PROBE = r"""
set +e
PYBIN=""
for py in \
  /home/async/data-disk/ljc/ming-salvage-sim-upstream/.venv/bin/python \
  /home/async/data-disk/ljc/MCST/.venv/bin/python \
  /home/async/data-disk/miniconda3/bin/python \
  /home/async/data-disk/miniconda3/envs/LogTokU/bin/python
do
  [ -x "$py" ] || continue
  if "$py" -c 'import paramiko' 2>/dev/null; then PYBIN="$py"; break; fi
done
echo PYBIN=$PYBIN
[ -n "$PYBIN" ] || exit 3
"$PYBIN" - <<'PY'
import paramiko
ips=['172.168.3.51','172.168.3.78','172.168.3.99','172.168.3.151']
users=['async','goat','root']
pw='asdf@1234'
cmd='hostname; whoami; nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader; echo ---apps---; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader; echo ---ps---; for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|tr -d " "|sort -u); do ps -o user=,pid=,etime=,cmd= -p $p 2>/dev/null; done'
for ip in ips:
    print('====', ip, '====', flush=True)
    ok=False
    for u in users:
        c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            c.connect(ip, port=22, username=u, password=pw, timeout=6, allow_agent=False, look_for_keys=False, banner_timeout=6, auth_timeout=6)
        except Exception as e:
            print(f'  {u}: {type(e).__name__}: {e}', flush=True)
            try: c.close()
            except Exception: pass
            continue
        print(f'  {u}: OK', flush=True)
        _,o,e=c.exec_command(cmd, timeout=25)
        print(o.read().decode('utf-8','replace'))
        err=e.read().decode('utf-8','replace')
        if err.strip():
            print('STDERR', err[:400])
        c.close(); ok=True; break
    if not ok:
        print('  no login', flush=True)
PY
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    print("=== FIND ===", flush=True)
    _, stdout, stderr = client.exec_command(FIND, timeout=30)
    print(stdout.read().decode("utf-8", "replace"))
    print(stderr.read().decode("utf-8", "replace")[-400:])
    print("=== PROBE ===", flush=True)
    _, stdout, stderr = client.exec_command(PROBE, timeout=120)
    print(stdout.read().decode("utf-8", "replace"))
    print(stderr.read().decode("utf-8", "replace")[-800:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
