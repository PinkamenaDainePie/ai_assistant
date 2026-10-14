#!/usr/bin/env bash
set -euo pipefail
WORK=/root/autodl-tmp/work
cd "$WORK"
tar -xzf _salvage_s2_bundle.tgz
test -d ming-salvage-sim-upstream
test -f salvage_faithfulness/data/cases_m_s2.json
printf '%s\n' "$WORK/ming-salvage-sim-upstream" > salvage_faithfulness/engine_root.txt

python3 -m venv "$WORK/venv"
# shellcheck disable=SC1091
source "$WORK/venv/bin/activate"
pip install -U pip wheel

export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=$WORK/hf
mkdir -p "$HF_HOME"

pip install 'vllm==0.11.0' 'transformers>=4.55.2,<4.57' 'numpy<2.3,>=1.26' openai httpx
pip install -r ming-salvage-sim-upstream/requirements.txt || \
  pip install 'agno[openai,sqlite]>=2.6.7' fastapi uvicorn pexpect

cat > ming-salvage-sim-upstream/.env <<EOF
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF

python - <<'PY'
from huggingface_hub import snapshot_download
import os
p = snapshot_download("Qwen/Qwen2.5-7B-Instruct", cache_dir=os.environ["HF_HOME"])
print("MODEL_PATH", p)
open("/root/autodl-tmp/work/MODEL_PATH.txt", "w").write(p)
PY

MODEL=$(cat "$WORK/MODEL_PATH.txt")
pkill -f 'vllm.entrypoints.openai.api_server' || true
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
echo "vllm_pid=$(cat "$WORK/vllm.pid")"

for i in $(seq 1 120); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8000/v1/models || echo x)
  echo "wait_$i=$code"
  if [ "$code" = "200" ]; then
    break
  fi
  sleep 10
done
curl -sS http://127.0.0.1:8000/v1/models | head -c 300
echo
echo SETUP_DONE
