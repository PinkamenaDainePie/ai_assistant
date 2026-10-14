# -*- coding: utf-8 -*-
"""Fix transformers pin and restart vLLM on AutoDL."""
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

MODEL_DIR = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct"
VLLM_LOG = "/root/autodl-tmp/vllm_qwen7b.log"
VLLM_PID = "/root/autodl-tmp/vllm_qwen7b.pid"
VENV_PY = "/root/autodl-tmp/venv/bin/python"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out + (("\n" + err) if err.strip() else "")

    print("[1] stop old setup / vllm", flush=True)
    run("pkill -f setup_vllm.sh || true; pkill -f vllm.entrypoints.openai.api_server || true; sleep 2")

    print("[2] pin transformers for vllm 0.8.5", flush=True)
    rc, out = run(
        f"export PIP_CACHE_DIR=/root/autodl-tmp/pip-cache; "
        f"{VENV_PY} -m pip install 'transformers==4.49.0' -i https://pypi.tuna.tsinghua.edu.cn/simple && "
        f"{VENV_PY} -c \"import transformers,vllm; print('transformers', transformers.__version__, 'vllm', vllm.__version__)\"",
        timeout=300,
    )
    print(out[-2500:], flush=True)
    if rc != 0:
        print("[fatal] pip pin failed", rc, flush=True)
        client.close()
        return rc

    print("[3] restart vllm", flush=True)
    start = f"""
set -e
export PATH=/root/autodl-tmp/venv/bin:$PATH
export CUDA_VISIBLE_DEVICES=0
rm -f {VLLM_LOG} {VLLM_PID}
nohup {VENV_PY} -m vllm.entrypoints.openai.api_server \
  --model {MODEL_DIR} \
  --served-model-name qwen2.5-7b-instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  >{VLLM_LOG} 2>&1 &
echo $! >{VLLM_PID}
echo started_pid=$(cat {VLLM_PID})
"""
    rc, out = run(start, timeout=30)
    print(out, flush=True)

    print("[4] wait /v1/models", flush=True)
    for i in range(90):
        rc, out = run(
            "curl -sS -o /tmp/vllm_models.json -w '%{http_code}' --max-time 5 "
            "http://127.0.0.1:8000/v1/models || echo fail",
            timeout=20,
        )
        code = out.strip()
        print(f"  try {i+1}: HTTP {code}", flush=True)
        if code == "200":
            break
        if (i + 1) % 5 == 0:
            _, log = run(f"tail -n 40 {VLLM_LOG} | tr '\\r' '\\n' | tail -40", timeout=20)
            print(log[-2000:], flush=True)
        time.sleep(10)
    else:
        _, log = run(f"tail -n 100 {VLLM_LOG}", timeout=20)
        print("[fatal] not ready\n", log[-4000:], flush=True)
        client.close()
        return 1

    print("[5] smoke", flush=True)
    rc, out = run(
        """curl -sS --max-time 120 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"只回复：pong"}],"max_tokens":16,"temperature":0}'""",
        timeout=150,
    )
    print(out[:2000], flush=True)
    _, gpu = run("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader")
    print("GPU", gpu, flush=True)
    print("DONE OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_MODEL=qwen2.5-7b-instruct", flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
