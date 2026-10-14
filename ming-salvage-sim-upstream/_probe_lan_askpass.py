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
cat > /tmp/askpass_gpu.sh <<'EOF'
#!/bin/sh
echo 'asdf@1234'
EOF
chmod 700 /tmp/askpass_gpu.sh
export SSH_ASKPASS=/tmp/askpass_gpu.sh
export SSH_ASKPASS_REQUIRE=force
export DISPLAY=dummy:0

for ip in 172.168.3.51 172.168.3.78 172.168.3.99 172.168.3.151; do
  echo "==== $ip ===="
  for u in async goat root; do
    out=$(setsid -w ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      "${u}@${ip}" 'hostname; whoami; nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader; echo ---apps---; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader; echo ---ps---; for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null|tr -d " "|sort -u); do ps -o user=,pid=,etime=,cmd= -p $p 2>/dev/null; done' 2>&1)
    rc=$?
    echo "user=$u rc=$rc"
    echo "$out" | head -40
    echo "$out" | grep -q 'nvidia-smi\|MiB\|No devices\|command not found\|hostname' && [ $rc -eq 0 ] && break
  done
done
rm -f /tmp/askpass_gpu.sh
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, stdout, stderr = client.exec_command(REMOTE, timeout=120)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
