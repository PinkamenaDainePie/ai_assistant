# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

import paramiko

HOST = "connect.westb.seetacloud.com"
PORT = 24768
USER = "root"
PASSWORD = "+PsU1+55zgQW"

REMOTE = r"""
set +e
source /root/miniconda3/etc/profile.d/conda.sh
conda info --envs
which python python3
ls /root/miniconda3/bin/python*
/root/miniconda3/bin/python -V
/root/miniconda3/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)' 2>&1
echo '=== DATA DISK ==='
df -h /root/autodl-tmp 2>/dev/null
ls -la /root/autodl-tmp
echo '=== CUDA ==='
nvcc --version 2>&1 | tail -3
nvidia-smi | head -15
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, stdout, stderr = client.exec_command(REMOTE, timeout=60)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-600:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
