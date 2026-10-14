#!/usr/bin/env bash
set -euo pipefail
WORK=/root/autodl-tmp/work
WHEEL_DIR=$WORK/wheels
mkdir -p "$WHEEL_DIR"

pkill -f "pip download" || true
pkill -f "pip install vllm" || true
pkill -f _setup_s2_fast || true
sleep 2
rm -rf /tmp/pip-unpack-* || true

export PATH="/root/miniconda3/bin:/root/autodl-tmp/work/venv/bin:$PATH"
PYTHON_BIN=/root/miniconda3/bin/python
if [ -x /root/autodl-tmp/work/venv/bin/python ]; then
  PYTHON_BIN=/root/autodl-tmp/work/venv/bin/python
fi
"$PYTHON_BIN" - <<'PY'
import re
import urllib.request
html = urllib.request.urlopen(
    "https://pypi.tuna.tsinghua.edu.cn/simple/vllm/", timeout=60
).read().decode("utf-8", "replace")
pat = r'href="([^"]+vllm-0\.11\.0-cp38-abi3-manylinux1_x86_64\.whl[^"]*)"'
cands = re.findall(pat, html)
print("cands", len(cands))
if not cands:
    raise SystemExit("no wheel url")
url = cands[0]
if url.startswith("/"):
    url = "https://pypi.tuna.tsinghua.edu.cn" + url
elif url.startswith("../../"):
    url = "https://pypi.tuna.tsinghua.edu.cn/" + url.replace("../../", "")
# strip hash fragment for wget/aria2
url = url.split("#", 1)[0]
print(url)
open("/root/autodl-tmp/work/wheels/URL.txt", "w").write(url)
PY

URL=$(cat "$WHEEL_DIR/URL.txt")
echo "URL=$URL"
OUT=$WHEEL_DIR/vllm-0.11.0-cp38-abi3-manylinux1_x86_64.whl

apt-get update -y >/dev/null 2>&1 || true
apt-get install -y aria2 wget >/dev/null 2>&1 || true

if command -v aria2c >/dev/null 2>&1; then
  aria2c -x 16 -s 16 -k 1M -c -d "$WHEEL_DIR" \
    -o vllm-0.11.0-cp38-abi3-manylinux1_x86_64.whl "$URL"
else
  wget -c -O "$OUT" "$URL"
fi

ls -lah "$OUT"
echo WHEEL_READY

# continue install + model + vllm + s2
# shellcheck disable=SC1091
source "$WORK/venv/bin/activate"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=$WORK/hf
mkdir -p "$HF_HOME"

echo "[install] vllm from local wheel"
pip install "$OUT"
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

echo "[model] download"
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
echo "[vllm] start"
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
    tail -n 50 "$WORK/vllm.log"
    exit 1
  fi
  sleep 10
done
echo SETUP_DONE

nohup bash "$WORK/_run_s2.sh" > "$WORK/_run_s2.log" 2>&1 &
echo $! > "$WORK/_run_s2.pid"
echo "RUN_PID=$(cat "$WORK/_run_s2.pid")"
