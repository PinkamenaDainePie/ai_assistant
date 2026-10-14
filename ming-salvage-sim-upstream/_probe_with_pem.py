# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

KEY = Path(r"e:\ai_assistant\ai_ass_key.pem")
TARGETS = [
    ("122.51.245.227", 22),
    ("124.221.252.181", 22),
    ("8.137.91.164", 22),
    ("connect.westc.gpuhub.com", 43653),
    ("connect.cqa1.seetacloud.com", 35144),
    ("dpcau.686788.xyz", 44415),
]
USERS = ["root", "ubuntu", "async", "ljc", "server-3090-002", "ec2-user", "centos"]
CMD = "hostname; whoami; nvidia-smi -L 2>&1 | head -10; nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>&1 | head -20; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>&1 | head -20"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pkey = paramiko.RSAKey.from_private_key_file(str(KEY))
    print(f"key bits={pkey.get_bits()}", flush=True)
    for host, port in TARGETS:
        print(f"\n===== {host}:{port} =====", flush=True)
        for user in USERS:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    host,
                    port=port,
                    username=user,
                    pkey=pkey,
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False,
                    banner_timeout=10,
                    auth_timeout=10,
                )
            except Exception as e:
                msg = str(e).split("\n")[0][:120]
                print(f"  {user}: {type(e).__name__}: {msg}", flush=True)
                try:
                    client.close()
                except Exception:
                    pass
                continue
            print(f"  {user}: OK", flush=True)
            _, stdout, _ = client.exec_command(CMD, timeout=25)
            print(stdout.read().decode("utf-8", "replace"))
            client.close()
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
