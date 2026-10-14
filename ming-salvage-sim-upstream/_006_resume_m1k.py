# -*- coding: utf-8 -*-
"""Resume after partial deploy: ensure extract/venv, start 3×vLLM, run A/B/C ×1000."""
from __future__ import annotations

import sys
import time

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE_LJC = "/home/async/data-disk/ljc"
REMOTE_ENGINE = f"{REMOTE_LJC}/ming-salvage-sim-upstream"
REMOTE_BENCH = f"{REMOTE_LJC}/salvage_faithfulness"
REMOTE_TGZ = f"{REMOTE_LJC}/_salvage_m1k_bundle.tgz"
BENCH_VENV = f"{REMOTE_LJC}/salvage-bench-venv"
VLLM_PY = "/home/async/data-disk/miniconda3/envs/vLLM_new/bin/python"
CONDA_PY = "/home/async/data-disk/miniconda3/bin/python"
HF_HOME = "/home/async/data-disk/huggingface"
MODEL = "Qwen/Qwen2.5-7B-Instruct"
OUT = f"{REMOTE_BENCH}/runs/ablation_m1k_006"

SHARDS = [
    (0, 8000, "A"),
    (2, 8001, "B"),
    (3, 8002, "C"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        if err.strip():
            out = (out + "\n" + err) if out else err
        return rc, out

    print("[1] re-extract + check max-cases", flush=True)
    rc, out = run(
        f"""
set -e
tar -xzf {REMOTE_TGZ} -C {REMOTE_LJC}
printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt
cat > {REMOTE_ENGINE}/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=300
EOF
grep -n max-cases {REMOTE_BENCH}/salvage_bench/run_ablation.py | head
test -f {REMOTE_BENCH}/data/cases_m.json
python3 - <<'PY'
import json
from pathlib import Path
n=len(json.loads(Path('{REMOTE_BENCH}/data/cases_m.json').read_text(encoding='utf-8')))
print('cases_n', n)
PY
""",
        timeout=180,
    )
    print(out[-2500:], flush=True)
    if rc != 0 or "max-cases" not in out:
        # tarball may be stale from interrupted build; still try if remote file has it after extract
        print("[warn] extract/check rc=", rc, flush=True)

    print("[2] bench venv", flush=True)
    rc, out = run(
        f"""
set -e
export TMPDIR={REMOTE_LJC}/tmp
mkdir -p "$TMPDIR"
if [ ! -x {BENCH_VENV}/bin/python ]; then
  {CONDA_PY} -m venv {BENCH_VENV}
fi
. {BENCH_VENV}/bin/activate
pip install --no-index --find-links={REMOTE_ENGINE}/wheelhouse_linux -r {REMOTE_ENGINE}/requirements.txt openai httpx 2>&1 | tail -40
python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.db import GameDB
print('engine_import_ok')
sys.path.insert(0, '{REMOTE_BENCH}')
from salvage_bench.cases_m import dataset_stats
print('stats', dataset_stats())
import inspect
from salvage_bench import run_ablation
print('has_max_cases', 'max-cases' in open(run_ablation.__file__, encoding='utf-8').read())
PY
""",
        timeout=600,
    )
    print(out[-4000:], flush=True)
    if "engine_import_ok" not in out:
        print("[fatal] venv/import", flush=True)
        client.close()
        return 1

    print("[3] start vLLMs", flush=True)
    run(
        """
pkill -f 'salvage_bench.run_ablation' || true
for p in 8000 8001 8002; do
  fuser -k ${p}/tcp 2>/dev/null || true
done
sleep 2
""",
        timeout=30,
    )
    for gpu, port, cond in SHARDS:
        rc, out = run(
            f"""
set -e
export CUDA_VISIBLE_DEVICES={gpu}
export HF_HOME={HF_HOME}
export HUGGINGFACE_HUB_CACHE={HF_HOME}/hub
nohup {VLLM_PY} -m vllm.entrypoints.openai.api_server \
  --model {MODEL} \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 --port {port} \
  --dtype auto \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  > {REMOTE_LJC}/vllm_{port}.log 2>&1 &
echo $! > {REMOTE_LJC}/vllm_{port}.pid
echo started gpu={gpu} port={port} pid=$(cat {REMOTE_LJC}/vllm_{port}.pid)
""",
            timeout=20,
        )
        print(out, flush=True)

    print("[4] wait ready", flush=True)
    deadline = time.time() + 900
    ready = {p: False for _, p, _ in SHARDS}
    while time.time() < deadline and not all(ready.values()):
        for _, port, _ in SHARDS:
            if ready[port]:
                continue
            _, out = run(
                f"curl -sS -o /dev/null -w '%{{http_code}}' --max-time 5 http://127.0.0.1:{port}/v1/models || echo fail",
                timeout=20,
            )
            code = (out.strip().splitlines()[-1] if out.strip() else "fail")
            if code == "200":
                ready[port] = True
                print(f"  port {port} ready", flush=True)
        if not all(ready.values()):
            time.sleep(15)
            # heartbeat
            _, mem = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader", timeout=20)
            print("  gpu", mem.strip().replace("\n", " | "), flush=True)
    if not all(ready.values()):
        print("[fatal] vllm not ready", ready, flush=True)
        for _, port, _ in SHARDS:
            _, out = run(f"tail -n 50 {REMOTE_LJC}/vllm_{port}.log", timeout=20)
            print(f"--- {port} ---", out[-2500:], flush=True)
        client.close()
        return 1

    print("[5] launch ablations", flush=True)
    run(
        f"""
rm -rf {OUT}
mkdir -p {OUT}
date '+%F %T' > {OUT}/started_wall.txt
""",
        timeout=20,
    )
    for gpu, port, cond in SHARDS:
        cond_out = f"{OUT}/cond_{cond}"
        _, out = run(
            f"""
set -e
mkdir -p {cond_out}
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL=http://127.0.0.1:{port}/v1
export OPENAI_MODEL=qwen2.5-7b-instruct
cd {REMOTE_BENCH}
nohup python -m salvage_bench.run_ablation \
  --suite m3k --conds {cond} \
  --max-cases 1000 \
  --turn-timeout 420 \
  --out-dir {cond_out} \
  > {cond_out}/run.log 2>&1 &
echo $! > {cond_out}/run.pid
echo started cond={cond} port={port} pid=$(cat {cond_out}/run.pid)
""",
            timeout=30,
        )
        print(out, flush=True)

    print("[6] poll 120s", flush=True)
    time.sleep(120)
    _, out = run(
        f"""
echo === procs ===
ps -ef | grep -E 'run_ablation|api_server' | grep -v grep | head -20
echo === lines ===
wc -l {OUT}/cond_A/ablation_A.jsonl {OUT}/cond_B/ablation_B.jsonl {OUT}/cond_C/ablation_C.jsonl 2>/dev/null
echo === logs ===
for c in A B C; do
  echo --- $c ---
  grep -E '^\\[suite\\]|^\\[max-cases\\]|^########|^\\[ok\\]|^\\[ERROR\\]|Traceback|ImportError' {OUT}/cond_$c/run.log | head -25
done
echo === gpu ===
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
""",
        timeout=40,
    )
    print(out, flush=True)
    client.close()
    print(f"[ok] OUT={OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
