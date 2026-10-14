#!/usr/bin/env bash
# Paste on CloudStudio /workspace after uploading _cloudstudio_salvage_bundle.tgz
# S2 plan: stratified 160 × A,B,C then 48-chain × A0,A1,C0,C1,CK (~720 runs).
set -euo pipefail
cd /workspace

echo "[1] extract bundle"
test -f _cloudstudio_salvage_bundle.tgz || test -f salvage_bundle.tgz || {
  echo "Upload tarball to /workspace first (name: _cloudstudio_salvage_bundle.tgz)"
  exit 1
}
TGZ=_cloudstudio_salvage_bundle.tgz
[ -f salvage_bundle.tgz ] && TGZ=salvage_bundle.tgz
tar -xzf "$TGZ"
test -d ming-salvage-sim-upstream/ming_sim
test -f salvage_faithfulness/salvage_bench/run_ablation.py
test -f salvage_faithfulness/data/cases_m_s2.json
printf '%s\n' /workspace/ming-salvage-sim-upstream > salvage_faithfulness/engine_root.txt

echo "[2] venv + deps"
python3 -m venv /workspace/venv
# shellcheck disable=SC1091
source /workspace/venv/bin/activate
pip install -U pip wheel
pip install "vllm>=0.8.5,<0.11" "transformers>=4.49" openai httpx
pip install -r ming-salvage-sim-upstream/requirements.txt || \
  pip install "agno[openai,sqlite]>=2.6.7" fastapi uvicorn pexpect

cat > ming-salvage-sim-upstream/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF

echo "[3] download model (HF)"
export HF_HOME=/workspace/hf
mkdir -p "$HF_HOME"
python - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download("Qwen/Qwen2.5-7B-Instruct", cache_dir="/workspace/hf")
print("MODEL_PATH", p)
open("/workspace/MODEL_PATH.txt","w").write(p)
PY

echo "[4] start vLLM"
pkill -f 'vllm.entrypoints.openai.api_server' || true
sleep 2
MODEL=$(cat /workspace/MODEL_PATH.txt)
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --served-model-name qwen2.5-7b-instruct \
  --host 0.0.0.0 --port 8000 \
  --dtype float16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  > /workspace/vllm.log 2>&1 &
echo $! > /workspace/vllm.pid
echo "vllm pid=$(cat /workspace/vllm.pid) log=/workspace/vllm.log"

echo "[5] wait ready"
for i in $(seq 1 90); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8000/v1/models || echo x)
  if [ "$code" = "200" ]; then echo READY; break; fi
  sleep 10
  echo "wait $i code=$code"
done
curl -sS http://127.0.0.1:8000/v1/models | head -c 300; echo

export PYTHONUTF8=1 SALVAGE_ENGINE_ROOT=/workspace/ming-salvage-sim-upstream
export OPENAI_API_KEY=EMPTY OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_MODEL=qwen2.5-7b-instruct
cd /workspace/salvage_faithfulness

echo "[6] smoke ablation max-cases=8 (A only) — check elapsed"
SMOKE=/workspace/salvage_faithfulness/runs/ablation_smoke_cs
rm -rf "$SMOKE"
mkdir -p "$SMOKE"
python -m salvage_bench.run_ablation \
  --suite s2 --conds A --max-cases 8 \
  --turn-timeout 1200 --out-dir "$SMOKE" \
  > "$SMOKE/run.log" 2>&1 || true
python - <<'PY'
import json, statistics
from pathlib import Path
p = Path("/workspace/salvage_faithfulness/runs/ablation_smoke_cs/ablation_A.jsonl")
if not p.is_file():
    print("SMOKE_FAIL no jsonl"); raise SystemExit(1)
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
ts = [float(r.get("elapsed_sec") or 0) for r in rows]
mean = statistics.mean(ts) if ts else 0
print(f"SMOKE n={len(ts)} mean_elapsed={mean:.1f}s max={max(ts) if ts else 0:.1f}")
# Hint: if mean>100, manually shrink singles before full run.
open("/workspace/SMOKE_MEAN.txt","w").write(f"{mean:.1f}")
PY

echo "[7] optional nosleep (long-run keep-alive)"
echo "  Get token: https://cloudstudio.net/settings/tokens"
echo "  Then: wget .../nosleep && export CS_HEALTHZ_TOKEN=... && nohup ./nosleep <cmd>"

echo "[8] full S2: ABC on 160, then memkg on 48-chain"
ABC_OUT=/workspace/salvage_faithfulness/runs/ablation_s2_abc_cs
MEM_OUT=/workspace/salvage_faithfulness/runs/ablation_s2_memkg_cs
rm -rf "$ABC_OUT" "$MEM_OUT"
mkdir -p "$ABC_OUT" "$MEM_OUT"
date '+%F %T' > "$ABC_OUT/started_wall.txt"

# Prefer wrapping with nosleep if present
WRAP=""
if [ -x /workspace/nosleep ] && [ -n "${CS_HEALTHZ_TOKEN:-}" ]; then
  WRAP="/workspace/nosleep"
fi

run_bg () {
  local out="$1"; shift
  if [ -n "$WRAP" ]; then
    nohup $WRAP "$@" > "$out/run.log" 2>&1 &
  else
    nohup "$@" > "$out/run.log" 2>&1 &
  fi
  echo $! > "$out/run.pid"
  echo "started pid=$(cat "$out/run.pid") out=$out"
}

# Sequential via a driver script so B waits for A, etc.
cat > /workspace/run_s2_driver.sh <<'DRV'
#!/usr/bin/env bash
set -euo pipefail
source /workspace/venv/bin/activate
export PYTHONUTF8=1 SALVAGE_ENGINE_ROOT=/workspace/ming-salvage-sim-upstream
export OPENAI_API_KEY=EMPTY OPENAI_BASE_URL=http://127.0.0.1:8000/v1 OPENAI_MODEL=qwen2.5-7b-instruct
cd /workspace/salvage_faithfulness
ABC_OUT=/workspace/salvage_faithfulness/runs/ablation_s2_abc_cs
MEM_OUT=/workspace/salvage_faithfulness/runs/ablation_s2_memkg_cs
python -m salvage_bench.run_ablation \
  --suite s2 --conds A,B,C --turn-timeout 1200 --out-dir "$ABC_OUT"
python -m salvage_bench.run_ablation \
  --suite s2chain --conds A0,A1,C0,C1,CK --turn-timeout 1200 --out-dir "$MEM_OUT"
date '+%F %T' > "$MEM_OUT/finished_wall.txt"
echo S2_DONE
DRV
chmod +x /workspace/run_s2_driver.sh

if [ -n "$WRAP" ]; then
  nohup $WRAP /workspace/run_s2_driver.sh > /workspace/s2_driver.log 2>&1 &
else
  nohup /workspace/run_s2_driver.sh > /workspace/s2_driver.log 2>&1 &
fi
echo $! > /workspace/s2_driver.pid
echo "S2 driver pid=$(cat /workspace/s2_driver.pid) log=/workspace/s2_driver.log"
echo "tail -f /workspace/s2_driver.log"
echo "ABC -> $ABC_OUT"
echo "MEMKG -> $MEM_OUT"
