#!/usr/bin/env bash
set -euo pipefail
WORK=/root/autodl-tmp/work
cd "$WORK"
# shellcheck disable=SC1091
source "$WORK/venv/bin/activate"

pkill -f 'pip install vllm' || true
sleep 1
rm -rf /tmp/pip-unpack-* || true

export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=$WORK/hf
mkdir -p "$HF_HOME" "$WORK/wheels"

echo "[1] download vllm via tsinghua"
pip download -d "$WORK/wheels" "vllm==0.11.0" \
  -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120

echo "[2] install vllm + deps"
pip install --no-index --find-links="$WORK/wheels" "vllm==0.11.0" || \
  pip install "vllm==0.11.0" -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120

pip install "transformers>=4.55.2,<4.57" "numpy<2.3,>=1.26" openai httpx \
  -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120

pip install -r "$WORK/ming-salvage-sim-upstream/requirements.txt" \
  -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 || \
  pip install "agno[openai,sqlite]>=2.6.7" fastapi uvicorn pexpect \
  -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120

cat > "$WORK/ming-salvage-sim-upstream/.env" <<EOF
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF

echo "[3] download model"
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
echo "[4] start vllm"
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
  if [ "$code" = "200" ]; then
    break
  fi
  if ! kill -0 "$(cat "$WORK/vllm.pid")" 2>/dev/null; then
    echo DEAD
    tail -n 40 "$WORK/vllm.log"
    exit 1
  fi
  sleep 10
done
curl -sS http://127.0.0.1:8000/v1/models | head -c 300
echo
echo SETUP_DONE

echo "[5] start S2 run"
nohup bash "$WORK/_run_s2.sh" > "$WORK/_run_s2.log" 2>&1 &
echo $! > "$WORK/_run_s2.pid"
echo "RUN_PID=$(cat "$WORK/_run_s2.pid")"
