#!/bin/bash
set -eu
export PATH=/root/autodl-tmp/venv/bin:/root/miniconda3/bin:$PATH
export CUDA_VISIBLE_DEVICES=0
export PIP_CACHE_DIR=/root/autodl-tmp/pip-cache
export TMPDIR=/root/autodl-tmp/tmp
export HF_HOME=/root/autodl-tmp/hf
export MODELSCOPE_CACHE=/root/autodl-tmp/modelscope_cache

MODEL_DIR=/root/autodl-tmp/models/Qwen2.5-7B-Instruct
VLLM_LOG=/root/autodl-tmp/vllm_qwen7b.log
VLLM_PID=/root/autodl-tmp/vllm_qwen7b.pid
VENV=/root/autodl-tmp/venv

mkdir -p /root/autodl-tmp/{pip-cache,tmp,models,hf}

echo "[1] env"
df -h / /root/autodl-tmp
nvidia-smi -L
/root/miniconda3/bin/python -V
/root/miniconda3/bin/python -c "import torch; print('base_torch', torch.__version__, torch.cuda.is_available())"

echo "[2] venv on data disk"
if [ ! -x "$VENV/bin/python" ]; then
  /root/miniconda3/bin/python -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -V
pip install -U pip wheel -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "[3] install vllm (pinned, fewer CUDA13 deps)"
# Prefer a build that works with cu12; avoid latest pulling torch/cuda13 onto 30G root
pip install "vllm==0.8.5" -i https://pypi.tuna.tsinghua.edu.cn/simple
python -c "import vllm,torch; print('vllm', vllm.__version__, 'torch', torch.__version__, 'cuda', torch.cuda.is_available())"

echo "[4] download model"
if [ -f "$MODEL_DIR/config.json" ]; then
  echo "model already present: $MODEL_DIR"
else
  pip install -q modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
  python - <<'PY'
from modelscope import snapshot_download
import os, shutil
p = snapshot_download("Qwen/Qwen2.5-7B-Instruct", cache_dir="/root/autodl-tmp/modelscope_cache")
print("downloaded_to", p)
dst = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct"
os.makedirs(os.path.dirname(dst), exist_ok=True)
if os.path.islink(dst) or os.path.exists(dst):
    if os.path.islink(dst):
        os.unlink(dst)
    elif os.path.isdir(dst):
        shutil.rmtree(dst)
os.symlink(p, dst)
print("linked", dst, "->", p)
PY
fi
test -f "$MODEL_DIR/config.json"
du -sh "$MODEL_DIR"
df -h /root/autodl-tmp

echo "[5] start server"
set +e
if [ -f "$VLLM_PID" ]; then kill "$(cat "$VLLM_PID")" 2>/dev/null || true; fi
pkill -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true
set -e
sleep 2
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_DIR" \
  --served-model-name qwen2.5-7b-instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  >"$VLLM_LOG" 2>&1 &
echo $! >"$VLLM_PID"
echo "started_pid=$(cat "$VLLM_PID")"

echo "[6] wait ready"
code=fail
for i in $(seq 1 90); do
  code=$(curl -sS -o /tmp/vllm_models.json -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/v1/models || echo fail)
  echo "try $i HTTP $code"
  if [ "$code" = "200" ]; then
    break
  fi
  if [ $((i % 5)) -eq 0 ]; then
    tail -n 30 "$VLLM_LOG" || true
  fi
  sleep 10
done
if [ "$code" != "200" ]; then
  echo "FATAL not ready"
  tail -n 120 "$VLLM_LOG" || true
  exit 1
fi

echo "[7] smoke"
curl -sS --max-time 120 http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"只回复：pong"}],"max_tokens":16,"temperature":0}'
echo
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
echo "DONE OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_MODEL=qwen2.5-7b-instruct"
