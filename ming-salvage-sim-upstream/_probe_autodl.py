# -*- coding: utf-8 -*-
"""Probe newly created AutoDL instance (no secrets printed)."""
from __future__ import annotations

import sys

import paramiko

HOST = "connect.westb.seetacloud.com"
PORT = 24768
USER = "root"
PASSWORD = "+PsU1+55zgQW"

REMOTE = r"""
set +e
echo '=== HOST ==='
hostname; date; whoami; pwd
echo '=== GPU ==='
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader 2>&1
echo '=== PY / TORCH ==='
python -V 2>&1
python -c 'import torch; print("torch", torch.__version__, "cuda", torch.version.cuda, "avail", torch.cuda.is_available(), "dev", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)' 2>&1
which python pip
echo '=== DISK ==='
df -h / /root /home 2>/dev/null | head -20
ls -la /root 2>/dev/null | head -20
echo '=== NET DASHSCOPE ==='
curl -sS -o /dev/null -w 'dashscope:%{http_code} t=%{time_total}\n' --max-time 15 https://dashscope.aliyuncs.com/ 2>&1
curl -sS -o /tmp/ds_models.json -w 'models:%{http_code}\n' --max-time 20 https://dashscope.aliyuncs.com/compatible-mode/v1/models 2>&1 | tail -1
echo '=== VLLM? ==='
python -c 'import vllm; print(vllm.__version__)' 2>&1
echo DONE
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[connect] {USER}@{HOST}:{PORT}", flush=True)
    client.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASSWORD,
        timeout=40,
        allow_agent=False,
        look_for_keys=False,
    )
    _, stdout, stderr = client.exec_command(REMOTE, timeout=90)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
