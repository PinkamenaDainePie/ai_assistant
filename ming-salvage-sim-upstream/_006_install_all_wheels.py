# -*- coding: utf-8 -*-
"""Install every wheel in wheelhouse into py313 venv (no-deps), then verify+run."""
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
WHL = f"{REMOTE_ENGINE}/wheelhouse_linux"

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

    _, out = run(
        f"SNAP=$(ls -d {HF_HOME}/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/* | head -1); echo SNAP=$SNAP",
        timeout=20,
    )
    snap = [ln.split("=", 1)[1].strip() for ln in out.splitlines() if ln.startswith("SNAP=")][0]
    print("snap", snap, flush=True)

    print("[1] install all wheels --no-deps", flush=True)
    rc, out = run(
        f"""
set -e
export TMPDIR={REMOTE_LJC}/tmp
mkdir -p "$TMPDIR"
rm -rf {BENCH_VENV}
{SYS_PY} -m venv {BENCH_VENV}
. {BENCH_VENV}/bin/activate
python -V
# install every compatible wheel ignoring dependency resolver
shopt -s nullglob
ok=0
fail=0
for w in {WHL}/*.whl; do
  if pip install --no-index --no-deps "$w" >/tmp/pip_one.log 2>&1; then
    ok=$((ok+1))
  else
    fail=$((fail+1))
    echo FAIL $(basename "$w")
    tail -2 /tmp/pip_one.log
  fi
done
echo WHEEL_OK=$ok FAIL=$fail
python - <<'PY'
import agno, openai, pydantic, httpx
print('imports_ok', openai.__version__, pydantic.__version__)
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.session import GameSession
print('engine_ok')
sys.path.insert(0, '{REMOTE_BENCH}')
from salvage_bench.run_ablation import _apply_max_cases
from salvage_bench.cases_m import SINGLE_CASES, CHAIN_CASES
s,c=_apply_max_cases(list(SINGLE_CASES), list(CHAIN_CASES), 1000)
print('m1k', len(s), len(c), len(s)+len(c))
PY
""",
        timeout=600,
    )
    print(out[-6000:], flush=True)
    if "engine_ok" not in out:
        print("[fatal] still cannot import", flush=True)
        client.close()
        return 1

    print("[2] restart vLLM offline + ablations", flush=True)
    run(
        """
pkill -f 'vllm.entrypoints.openai.api_server' || true
pkill -f 'salvage_bench.run_ablation' || true
for p in 8000 8001 8002; do fuser -k ${p}/tcp 2>/dev/null || true; done
sleep 3
""",
        timeout=30,
    )
    for gpu, port, cond in SHARDS:
        _, o = run(
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
  --dtype auto --max-model-len 32768 --gpu-memory-utilization 0.90 \
  > {REMOTE_LJC}/vllm_{port}.log 2>&1 &
echo $! > {REMOTE_LJC}/vllm_{port}.pid
echo started port={port} pid=$(cat {REMOTE_LJC}/vllm_{port}.pid)
""",
            timeout=20,
        )
        print(o, flush=True)

    deadline = time.time() + 900
    ready = {p: False for _, p, _ in SHARDS}
    while time.time() < deadline and not all(ready.values()):
        for _, port, _ in SHARDS:
            if ready[port]:
                continue
            _, alive = run(f"kill -0 $(cat {REMOTE_LJC}/vllm_{port}.pid) 2>/dev/null && echo ALIVE || echo DEAD", timeout=15)
            _, o = run(
                f"curl -sS -o /dev/null -w '%{{http_code}}' --max-time 5 http://127.0.0.1:{port}/v1/models || echo fail",
                timeout=20,
            )
            code = o.strip().splitlines()[-1] if o.strip() else "fail"
            if code == "200":
                ready[port] = True
                print("ready", port, flush=True)
            elif "DEAD" in alive:
                _, log = run(f"tail -n 50 {REMOTE_LJC}/vllm_{port}.log", timeout=20)
                print("DEAD", port, log[-2500:], flush=True)
                client.close()
                return 1
        if not all(ready.values()):
            _, mem = run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader", timeout=20)
            print("wait", ready, mem.strip().replace("\n", " | "), flush=True)
            time.sleep(15)
    if not all(ready.values()):
        print("timeout", ready, flush=True)
        client.close()
        return 1

    run(f"rm -rf {OUT}; mkdir -p {OUT}; date '+%F %T' > {OUT}/started_wall.txt; printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt", timeout=20)
    for gpu, port, cond in SHARDS:
        cond_out = f"{OUT}/cond_{cond}"
        _, o = run(
            f"""
set -e
mkdir -p {cond_out}
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1 SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
export OPENAI_API_KEY=EMPTY OPENAI_BASE_URL=http://127.0.0.1:{port}/v1 OPENAI_MODEL=qwen2.5-7b-instruct
export HF_HUB_OFFLINE=1
cd {REMOTE_BENCH}
nohup python -m salvage_bench.run_ablation --suite m3k --conds {cond} --max-cases 1000 --turn-timeout 420 --out-dir {cond_out} > {cond_out}/run.log 2>&1 &
echo $! > {cond_out}/run.pid
echo started cond={cond} pid=$(cat {cond_out}/run.pid)
""",
            timeout=30,
        )
        print(o, flush=True)

    time.sleep(180)
    _, o = run(
        f"""
for p in 8000 8001 8002; do echo -n p$p=; curl -sS -o /dev/null -w '%{{http_code}}\\n' --max-time 3 http://127.0.0.1:$p/v1/models || echo x; done
ps -ef | grep run_ablation | grep -v grep
wc -l {OUT}/cond_*/ablation_*.jsonl 2>/dev/null
for c in A B C; do echo ---$c---; grep -E '^\\[suite\\]|^\\[max-cases\\]|^########|^\\[ok\\]|^\\[ERROR\\]|Traceback|ModuleNotFound' {OUT}/cond_$c/run.log | head -25; done
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
""",
        timeout=40,
    )
    print(o, flush=True)
    client.close()
    print("[ok]", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
