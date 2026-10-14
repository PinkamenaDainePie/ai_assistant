#!/usr/bin/env bash
set -euo pipefail
WORK=/root/autodl-tmp/work
# shellcheck disable=SC1091
source "$WORK/venv/bin/activate"
export PATH="/root/miniconda3/bin:$WORK/venv/bin:$PATH"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=$WORK/hf
mkdir -p "$HF_HOME" "$WORK/wheels"
INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

pkill -f "pip install" || true
sleep 2

# Prefer tuna for ALL remaining deps
pip config unset global.index-url >/dev/null 2>&1 || true
pip config set global.index-url "$INDEX" || true

echo "[torch] resolve + aria2"
"$WORK/venv/bin/python" - <<'PY'
import re, urllib.request
html = urllib.request.urlopen(
    "https://pypi.tuna.tsinghua.edu.cn/simple/torch/", timeout=60
).read().decode("utf-8", "replace")
pat = r'href="([^"]+torch-2\.8\.0-cp312-cp312-manylinux_2_28_x86_64\.whl[^"]*)"'
cands = re.findall(pat, html)
if not cands:
    raise SystemExit("no torch wheel")
url = cands[0].split("#", 1)[0]
if url.startswith("/"):
    url = "https://pypi.tuna.tsinghua.edu.cn" + url
elif url.startswith("../../"):
    url = "https://pypi.tuna.tsinghua.edu.cn/" + url.replace("../../", "")
print(url)
open("/root/autodl-tmp/work/wheels/TORCH_URL.txt", "w").write(url)
PY

TORCH_URL=$(cat "$WORK/wheels/TORCH_URL.txt")
aria2c -x 16 -s 16 -k 1M -c -d "$WORK/wheels" -o torch-2.8.0-cp312-cp312-manylinux_2_28_x86_64.whl "$TORCH_URL"
ls -lah "$WORK/wheels/torch-2.8.0-cp312-cp312-manylinux_2_28_x86_64.whl"
echo TORCH_READY

echo "[install] torch then vllm"
pip install "$WORK/wheels/torch-2.8.0-cp312-cp312-manylinux_2_28_x86_64.whl" -i "$INDEX" --timeout 120
pip install "$WORK/wheels/vllm-0.11.0-cp38-abi3-manylinux1_x86_64.whl" -i "$INDEX" --timeout 120
pip install "transformers>=4.55.2,<4.57" "numpy<2.3,>=1.26" openai httpx -i "$INDEX" --timeout 120
pip install -r "$WORK/ming-salvage-sim-upstream/requirements.txt" -i "$INDEX" --timeout 120 || \
  pip install "agno[openai,sqlite]>=2.6.7" fastapi uvicorn pexpect -i "$INDEX" --timeout 120

# fix typo if svelte got installed path - ensure fastapi
pip install fastapi uvicorn pexpect -i "$INDEX" --timeout 120

cat > "$WORK/ming-salvage-sim-upstream/.env" <<EOF
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF

echo "[model]"
python - <<'PY'
from huggingface_hub import snapshot_download
import os
p = snapshot_download("Qwen/Qwen2.5-7B-Instruct", cache_dir=os.environ["HF_HOME"])
print("MODEL_PATH", p)
open("/root/autodl-tmp/work/MODEL_PATH.txt", "w").write(p)
PY

MODEL=$(cat "$WORK/MODEL_PATH.txt")
pkill -f "vllm.entrypoints.openai.api_server" || true
sleep 2
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 --port 8000 \
  --dtype float16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  > "$WORK/vllm.log" 2>&1 &
echo $! > "$WORK/vllm.pid"

for i in $(seq 1 120); do
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:8000/v1/models || echo x)
  echo "wait_$i=$code"
  if [ "$code" = "200" ]; then break; fi
  if ! kill -0 "$(cat "$WORK/vllm.pid")" 2>/dev/null; then
    echo DEAD
    tail -n 60 "$WORK/vllm.log"
    exit 1
  fi
  sleep 10
done
echo SETUP_DONE

nohup bash "$WORK/_run_s2.sh" > "$WORK/_run_s2.log" 2>&1 &
echo $! > "$WORK/_run_s2.pid"
echo "RUN_PID=$(cat "$WORK/_run_s2.pid")"
