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
echo which_sshpass=$(command -v sshpass)
echo which_ssh=$(command -v ssh)
# try pip user paramiko quickly if needed
python3 -c 'import paramiko' 2>/dev/null || pip3 install --user -q paramiko 2>/dev/null
python3 - <<'PY'
import sys
try:
    import paramiko
except Exception as e:
    print('no paramiko', e)
    sys.exit(2)
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
    _, stdout, stderr = client.exec_command(REMOTE, timeout=180)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-1500:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
