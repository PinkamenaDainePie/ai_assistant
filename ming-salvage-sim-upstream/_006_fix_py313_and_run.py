# -*- coding: utf-8 -*-
"""Rebuild bench venv with system Py3.13 (matches wheelhouse), offline vLLM, run m1k."""
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
BENCH_VENV = f"{REMOTE_LJC}/salvage-bench-venv313"
VLLM_PY = "/home/async/data-disk/miniconda3/envs/vLLM_new/bin/python"
HF_HOME = "/home/async/data-disk/huggingface"
OUT = f"{REMOTE_BENCH}/runs/ablation_m1k_006"
SYS_PY = "/usr/bin/python3"

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

    print("[0] py + snap", flush=True)
    rc, out = run(
        f"""
{SYS_PY} -V
SNAP=$(ls -d {HF_HOME}/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/* | head -1)
echo SNAP=$SNAP
test -f "$SNAP/config.json"
ls {REMOTE_ENGINE}/wheelhouse_linux | grep pydantic_core
""",
        timeout=30,
    )
    print(out, flush=True)
    snap = None
    for line in out.splitlines():
        if line.startswith("SNAP="):
            snap = line.split("=", 1)[1].strip()
    if not snap or "Python 3.13" not in out:
        print("[fatal] need py3.13 + snap", flush=True)
        client.close()
        return 1

    print("[1] rebuild venv313 + offline install", flush=True)
    rc, out = run(
        f"""
set -e
export TMPDIR={REMOTE_LJC}/tmp
mkdir -p "$TMPDIR"
rm -rf {BENCH_VENV}
{SYS_PY} -m venv {BENCH_VENV}
. {BENCH_VENV}/bin/activate
python -V
pip install --upgrade pip -i about:blank >/dev/null 2>&1 || true
# full requirements from wheelhouse; allow failures on missing extras then force core pkgs
set +e
pip install --no-index --find-links={REMOTE_ENGINE}/wheelhouse_linux -r {REMOTE_ENGINE}/requirements.txt 2>&1 | tail -40
pip install --no-index --find-links={REMOTE_ENGINE}/wheelhouse_linux \
  agno openai httpx pydantic pydantic-core typing-extensions annotated-types \
  anyio httpcore h11 idna certifi distro jiter tqdm sniffio starlette fastapi uvicorn \
  python-dotenv sqlite-utils 2>&1 | tail -40
set -e
python - <<'PY'
import agno, openai, pydantic
print('pkgs', agno.__name__, openai.__version__, pydantic.__version__)
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.db import GameDB
from ming_sim.session import GameSession
print('engine_ok')
sys.path.insert(0, '{REMOTE_BENCH}')
from salvage_bench.run_ablation import _apply_max_cases
from salvage_bench.cases_m import SINGLE_CASES, CHAIN_CASES
s,c=_apply_max_cases(list(SINGLE_CASES), list(CHAIN_CASES), 1000)
print('m1k', len(s), len(c), 'total', len(s)+len(c))
PY
""",
        timeout=600,
    )
    print(out[-5000:], flush=True)
    if "engine_ok" not in out or "m1k" not in out:
        print("[fatal] venv", flush=True)
        client.close()
        return 1

    print("[2] kill old", flush=True)
    run(
        """
pkill -f 'vllm.entrypoints.openai.api_server' || true
pkill -f 'salvage_bench.run_ablation' || true
for p in 8000 8001 8002; do fuser -k ${p}/tcp 2>/dev/null || true; done
sleep 3
""",
        timeout=30,
    )

    print("[3] start offline vLLM", flush=True)
    for gpu, port, cond in SHARDS:
        _, out = run(
            f"""
set -e
export CUDA_VISIBLE_DEVICES={gpu}
export HF_HOME={HF_HOME}
export HUGGINGFACE_HUB_CACHE={HF_HOME}/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
nohup {VLLM_PY} -m vllm.entrypoints.openai.api_server \
  --model {snap} \
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

    print("[4] wait vLLM", flush=True)
    deadline = time.time() + 900
    ready = {p: False for _, p, _ in SHARDS}
    while time.time() < deadline and not all(ready.values()):
        for _, port, _ in SHARDS:
            if ready[port]:
                continue
            _, alive = run(
                f"kill -0 $(cat {REMOTE_LJC}/vllm_{port}.pid) 2>/dev/null && echo ALIVE || echo DEAD",
                timeout=15,
            )
            _, out = run(
                f"curl -sS -o /dev/null -w '%{{http_code}}' --max-time 5 http://127.0.0.1:{port}/v1/models || echo fail",
                timeout=20,
            )
            code = out.strip().splitlines()[-1] if out.strip() else "fail"
            if code == "200":
                ready[port] = True
                print(f"  port {port} ready", flush=True)
            elif "DEAD" in alive:
                _, log = run(f"tail -n 40 {REMOTE_LJC}/vllm_{port}.log", timeout=20)
                print(f"[fatal] port {port} dead\n{log[-2000:]}", flush=True)
                client.close()
                return 1
        if not all(ready.values()):
            _, mem = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader", timeout=20)
            print("  wait", {k: v for k, v in ready.items()}, "|", mem.strip().replace("\n", " ; "), flush=True)
            time.sleep(15)
    if not all(ready.values()):
        print("[fatal] timeout", ready, flush=True)
        client.close()
        return 1

    print("[5] launch ablations", flush=True)
    run(
        f"""
rm -rf {OUT}
mkdir -p {OUT}
date '+%F %T' > {OUT}/started_wall.txt
printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt
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
export HF_HUB_OFFLINE=1
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

    print("[6] smoke 180s", flush=True)
    time.sleep(180)
    _, out = run(
        f"""
for p in 8000 8001 8002; do echo -n p$p=; curl -sS -o /dev/null -w '%{{http_code}}\\n' --max-time 3 http://127.0.0.1:$p/v1/models || echo x; done
ps -ef | grep -E 'run_ablation|api_server' | grep -v grep | head -20
wc -l {OUT}/cond_A/ablation_A.jsonl {OUT}/cond_B/ablation_B.jsonl {OUT}/cond_C/ablation_C.jsonl 2>/dev/null
for c in A B C; do
  echo --- $c ---
  grep -E '^\\[suite\\]|^\\[max-cases\\]|^########|^\\[ok\\]|^\\[ERROR\\]|Traceback|ImportError|ModuleNotFound' {OUT}/cond_$c/run.log | head -30
done
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
