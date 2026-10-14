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
echo === ljc top ===
ls /home/async/data-disk/ljc | head -40
echo === engine ===
ls /home/async/data-disk/ljc/ming-salvage-sim-upstream | head -25
echo === inrepo faithfulness ===
ls /home/async/data-disk/ljc/ming-salvage-sim-upstream/experiments/faithfulness 2>/dev/null | head
echo === standalone bench ===
ls /home/async/data-disk/ljc/salvage_faithfulness 2>/dev/null | head
echo === vLLM_new ===
/home/async/data-disk/miniconda3/envs/vLLM_new/bin/python - <<'PY'
import vllm, torch
print('vllm', vllm.__version__)
print('cuda', torch.cuda.device_count())
PY
echo === gpu ===
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv,noheader
echo === wheelhouse count ===
ls /home/async/data-disk/ljc/ming-salvage-sim-upstream/wheelhouse_linux 2>/dev/null | wc -l
"""
    _, o, e = c.exec_command(cmd, timeout=90)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-1000:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
