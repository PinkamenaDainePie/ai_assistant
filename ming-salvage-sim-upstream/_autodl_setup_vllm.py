# -*- coding: utf-8 -*-
"""Install vLLM + download Qwen2.5-7B + start OpenAI server on AutoDL."""
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westb.seetacloud.com"
PORT = 24768
USER = "root"
PASSWORD = "+PsU1+55zgQW"

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_DIR = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct"
VLLM_LOG = "/root/autodl-tmp/vllm_qwen7b.log"
VLLM_PID = "/root/autodl-tmp/vllm_qwen7b.pid"


def ssh() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    # login shell so conda PATH works if present
    wrapped = f"bash -lc {repr(cmd)}"
    _, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = ssh()
    print("[1] check disk/gpu", flush=True)
    rc, out, err = run(client, "df -h /root/autodl-tmp; nvidia-smi -L; /root/miniconda3/bin/python -V")
    print(out)

    print("[2] install vllm (may take several minutes)", flush=True)
    # Use existing torch; install recent vllm compatible with cu121/py312
    install_cmd = r"""
set -e
export PATH=/root/miniconda3/bin:$PATH
python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
# Prefer pip vllm; pin loosely for py3.12
pip install -U pip wheel
pip install "vllm>=0.6.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
python -c 'import vllm; print("vllm", vllm.__version__)'
"""
    rc, out, err = run(client, install_cmd, timeout=900)
    print(out[-3000:] if len(out) > 3000 else out)
    if err.strip():
        print("STDERR_TAIL", err[-2000:])
    if rc != 0:
        print("[fatal] vllm install rc=", rc, flush=True)
        client.close()
        return rc

    print("[3] download model via modelscope (HF mirror fallback)", flush=True)
    dl_cmd = rf"""
set -e
export PATH=/root/miniconda3/bin:$PATH
mkdir -p /root/autodl-tmp/models
if [ -f "{MODEL_DIR}/config.json" ]; then
  echo "model already present: {MODEL_DIR}"
  ls -la "{MODEL_DIR}" | head
  exit 0
fi
pip install -q modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
python - <<'PY'
from modelscope import snapshot_download
p = snapshot_download('Qwen/Qwen2.5-7B-Instruct', cache_dir='/root/autodl-tmp/modelscope_cache')
print('downloaded_to', p)
import os, shutil
dst = '{MODEL_DIR}'
os.makedirs(os.path.dirname(dst), exist_ok=True)
if os.path.isdir(dst):
    shutil.rmtree(dst)
# symlink to save space
os.symlink(p, dst)
print('linked', dst, '->', p)
PY
du -sh "{MODEL_DIR}" || true
test -f "{MODEL_DIR}/config.json"
"""
    rc, out, err = run(client, dl_cmd, timeout=1800)
    print(out[-4000:] if len(out) > 4000 else out)
    if err.strip():
        print("STDERR_TAIL", err[-2000:])
    if rc != 0:
        print("[fatal] model download rc=", rc, flush=True)
        client.close()
        return rc

    print("[4] start vllm openai server on :8000", flush=True)
    start_cmd = rf"""
set -e
export PATH=/root/miniconda3/bin:$PATH
export CUDA_VISIBLE_DEVICES=0
# kill old
if [ -f {VLLM_PID} ]; then kill $(cat {VLLM_PID}) 2>/dev/null || true; fi
pkill -f 'vllm.entrypoints.openai.api_server' 2>/dev/null || true
sleep 2
nohup python -m vllm.entrypoints.openai.api_server \
  --model "{MODEL_DIR}" \
  --served-model-name qwen2.5-7b-instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  > {VLLM_LOG} 2>&1 &
echo $! > {VLLM_PID}
echo started_pid=$(cat {VLLM_PID})
sleep 3
tail -n 30 {VLLM_LOG} || true
"""
    rc, out, err = run(client, start_cmd, timeout=60)
    print(out)
    if err.strip():
        print("STDERR", err[-1000:])

    print("[5] wait for /v1/models", flush=True)
    for i in range(60):
        rc, out, err = run(
            client,
            "curl -sS -o /tmp/vllm_models.json -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models || echo fail",
            timeout=20,
        )
        code = out.strip()
        print(f"  try {i+1}: HTTP {code}", flush=True)
        if code == "200":
            break
        # show log progress every 5 tries
        if (i + 1) % 5 == 0:
            _, log, _ = run(client, f"tail -n 20 {VLLM_LOG}", timeout=15)
            print(log[-1500:], flush=True)
        time.sleep(10)
    else:
        _, log, _ = run(client, f"tail -n 80 {VLLM_LOG}", timeout=15)
        print("[fatal] vllm not ready\n", log)
        client.close()
        return 1

    _, models, _ = run(client, "python -c \"import json; print(json.load(open('/tmp/vllm_models.json')))\"", timeout=20)
    print("MODELS", models)

    print("[6] chat smoke", flush=True)
    smoke = r"""
curl -sS --max-time 120 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"只回复：pong"}],"max_tokens":16,"temperature":0}'
"""
    rc, out, err = run(client, smoke, timeout=150)
    print(out[:2000])
    if err.strip():
        print("STDERR", err[-500:])

    _, gpu, _ = run(client, "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader", timeout=15)
    print("GPU", gpu)
    client.close()
    print("[done] OPENAI_BASE_URL=http://127.0.0.1:8000/v1  OPENAI_MODEL=qwen2.5-7b-instruct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
