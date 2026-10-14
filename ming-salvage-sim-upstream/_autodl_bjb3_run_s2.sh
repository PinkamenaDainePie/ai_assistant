#!/usr/bin/env bash
set -euo pipefail
WORK=/root/autodl-tmp/work
PY=/root/miniconda3/bin/python
unset VIRTUAL_ENV
export PATH="/root/miniconda3/bin:/usr/bin:/bin"
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT=$WORK/ming-salvage-sim-upstream
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_MODEL=qwen2.5-7b-instruct
cd "$WORK/salvage_faithfulness"

echo "[py] $($PY -c 'import sys; print(sys.executable)')"
$PY -c "import agno, vllm; print('imports_ok', agno.__file__)"

ABC_OUT=$WORK/salvage_faithfulness/runs/ablation_s2_abc_autodl
MEM_OUT=$WORK/salvage_faithfulness/runs/ablation_s2_memkg_autodl
rm -rf "$ABC_OUT" "$MEM_OUT"
mkdir -p "$ABC_OUT" "$MEM_OUT"
date '+%F %T' > "$ABC_OUT/started_wall.txt"
$PY -c "import sys; open(r'$ABC_OUT/interpreter.txt','w').write(sys.executable+'\n')"

$PY -m salvage_bench.run_ablation \
  --suite s2 --conds A,B,C --turn-timeout 1200 --out-dir "$ABC_OUT"

$PY -m salvage_bench.run_ablation \
  --suite s2chain --conds A0,A1,C0,C1,CK --turn-timeout 1200 --out-dir "$MEM_OUT"

date '+%F %T' > "$MEM_OUT/finished_wall.txt"
echo S2_DONE
