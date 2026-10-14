# -*- coding: utf-8 -*-
"""Probe whether 006 can serve Qwen2.5-7B via vLLM."""
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
echo === who ===
hostname; whoami; pwd
echo === nvidia ===
nvidia-smi -L
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv
echo === procs on gpu ===
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv
echo === python/vllm ===
which python3; python3 -V
ls -d /home/async/data-disk/ljc/*/ 2>/dev/null | head -40
ls /home/async/data-disk/ljc/venv/bin/python 2>/dev/null
ls /home/async/data-disk/ljc/.venv/bin/python 2>/dev/null
for p in /home/async/data-disk/ljc/venv/bin/python /home/async/data-disk/ljc/.venv/bin/python /home/async/miniconda3/bin/python /opt/conda/bin/python; do
  [ -x "$p" ] || continue
  echo TRY $p
  $p -c 'import vllm,transformers; print("vllm", vllm.__version__, "tf", transformers.__version__)' 2>&1 | tail -5
done
echo === wheelhouse ===
ls /home/async/data-disk/ljc/ming-salvage-sim-upstream/wheelhouse_linux 2>/dev/null | head
ls /home/async/data-disk/ljc/wheelhouse* 2>/dev/null | head
echo === qwen path ===
ls -d /home/async/data-disk/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/* 2>/dev/null | head
echo === listening ===
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) | grep -E ':(8000|8001|8002|8003|8004|8005|11434)\b' || echo none
echo === disk ===
df -h /home/async/data-disk | tail -1
"""
    _, o, e = c.exec_command(cmd, timeout=90)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
