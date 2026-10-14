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
echo '=== GPU ==='
nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv,noheader
echo '=== QWEN7B ==='
P=/home/async/data-disk/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct
du -sh "$P" 2>/dev/null
find "$P" -maxdepth 3 -name config.json 2>/dev/null | head -3
find "$P" -maxdepth 4 -name '*.safetensors' 2>/dev/null | wc -l
echo '=== OUTBOUND ==='
curl -sS -o /dev/null -w 'pypi:%{http_code} t=%{time_total}\n' --max-time 8 https://pypi.org/simple/vllm/ 2>&1
curl -sS -o /dev/null -w 'tuna:%{http_code} t=%{time_total}\n' --max-time 8 https://pypi.tuna.tsinghua.edu.cn/simple/vllm/ 2>&1
echo '=== WHEELHOUSE ==='
ls /home/async/data-disk/ljc/_wheelhouse_linux.tgz 2>/dev/null
ls /home/async/data-disk/ljc/bin 2>/dev/null | head
echo '=== VLLM IMPORT ==='
for py in \
  /home/async/data-disk/ljc/ming-salvage-sim-upstream/.venv/bin/python \
  /home/async/data-disk/miniconda3/bin/python \
  /home/async/data-disk/miniconda3/envs/LogTokU/bin/python
do
  [ -x "$py" ] || continue
  echo TRY $py
  "$py" -c 'import vllm; print(vllm.__version__)' 2>&1 | head -2
  "$py" -c 'import torch; print(torch.__version__, torch.cuda.is_available())' 2>&1 | head -2
done
echo '=== DISK ==='
df -h /home/async/data-disk | tail -1
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    _, o, e = c.exec_command(REMOTE, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-500:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
