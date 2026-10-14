# -*- coding: utf-8 -*-
"""Use only free GPU0: one vLLM :8000; run A then B then C ×1000 serially."""
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
CONDS = ["A", "B", "C"]


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

    print("[1] hard-kill our ablations/workers/old vllm on 8001/8002", flush=True)
    run(
        """
# kill by pattern
pkill -9 -f 'salvage_bench.run_ablation' || true
pkill -9 -f 'salvage_faithfulness/runs/_workers' || true
pkill -9 -f '_worker_' || true
# kill vllm not on gpu0/port8000 if any
for p in 8001 8002; do fuser -k -9 ${p}/tcp 2>/dev/null || true; done
# if port 8000 unhealthy, kill and restart later
sleep 2
ps -ef | grep -E 'run_ablation|_worker_|api_server' | grep -v grep | head -20 || echo clean
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
""",
        timeout=40,
    )

    print("[2] ensure vLLM :8000 on GPU0", flush=True)
    _, health = run(
        "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models || echo x",
        timeout=20,
    )
    print("health", health.strip(), flush=True)
    if health.strip() != "200":
        run(
            """
pkill -9 -f 'vllm.entrypoints.openai.api_server' || true
fuser -k -9 8000/tcp 2>/dev/null || true
sleep 3
""",
            timeout=20,
        )
        _, o = run(
            f"""
set -e
export CUDA_VISIBLE_DEVICES=0
export HF_HOME={HF_HOME}
export HUGGINGFACE_HUB_CACHE={HF_HOME}/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
nohup {VLLM_PY} -m vllm.entrypoints.openai.api_server \
  --model {snap} \
  --served-model-name qwen2.5-7b-instruct \
  --host 127.0.0.1 --port 8000 \
  --dtype auto --max-model-len 32768 --gpu-memory-utilization 0.90 \
  > {REMOTE_LJC}/vllm_8000.log 2>&1 &
echo $! > {REMOTE_LJC}/vllm_8000.pid
echo started pid=$(cat {REMOTE_LJC}/vllm_8000.pid)
""",
            timeout=20,
        )
        print(o, flush=True)
        deadline = time.time() + 600
        while time.time() < deadline:
            _, h = run(
                "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models || echo x",
                timeout=15,
            )
            if h.strip() == "200":
                print("vllm ready", flush=True)
                break
            _, alive = run(f"kill -0 $(cat {REMOTE_LJC}/vllm_8000.pid) 2>/dev/null && echo ALIVE || echo DEAD", timeout=10)
            if "DEAD" in alive:
                _, log = run(f"tail -n 40 {REMOTE_LJC}/vllm_8000.log", timeout=15)
                print(log[-2000:], flush=True)
                client.close()
                return 1
            time.sleep(10)
        else:
            print("vllm timeout", flush=True)
            client.close()
            return 1

    print("[3] prepare out dir + env", flush=True)
    run(
        f"""
rm -rf {OUT}
mkdir -p {OUT}
date '+%F %T' > {OUT}/started_wall.txt
cat > {REMOTE_ENGINE}/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF
printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt
""",
        timeout=20,
    )

    # Launch a supervisor that runs A,B,C sequentially in background on remote
    print("[4] start remote serial supervisor", flush=True)
    supervisor = f"{OUT}/serial_supervisor.sh"
    # write script via heredoc
    _, o = run(
        f"""
cat > {supervisor} <<'EOS'
#!/bin/bash
set -e
BENCH_VENV="{BENCH_VENV}"
REMOTE_BENCH="{REMOTE_BENCH}"
REMOTE_ENGINE="{REMOTE_ENGINE}"
OUT="{OUT}"
. "$BENCH_VENV/bin/activate"
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT="$REMOTE_ENGINE"
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_MODEL=qwen2.5-7b-instruct
export OPENAI_TIMEOUT_SECONDS=600
export HF_HUB_OFFLINE=1
cd "$REMOTE_BENCH"
for COND in A B C; do
  COND_OUT="$OUT/cond_$COND"
  mkdir -p "$COND_OUT"
  echo "[supervisor] START $COND $(date '+%F %T')" | tee -a "$OUT/supervisor.log"
  python -m salvage_bench.run_ablation \
    --suite m3k --conds "$COND" --max-cases 1000 \
    --turn-timeout 1200 --out-dir "$COND_OUT" \
    > "$COND_OUT/run.log" 2>&1
  echo "[supervisor] DONE $COND $(date '+%F %T')" | tee -a "$OUT/supervisor.log"
  test -f "$COND_OUT/summary.json" && echo "[supervisor] HAS_SUMMARY $COND" | tee -a "$OUT/supervisor.log"
done
echo "[supervisor] ALL_DONE $(date '+%F %T')" | tee -a "$OUT/supervisor.log"
EOS
chmod +x {supervisor}
nohup bash {supervisor} > {OUT}/supervisor.stdout 2>&1 &
echo $! > {OUT}/supervisor.pid
echo supervisor_pid=$(cat {OUT}/supervisor.pid)
""",
        timeout=30,
    )
    print(o, flush=True)

    print("[5] smoke 3 min", flush=True)
    time.sleep(180)
    _, o = run(
        f"""
echo === supervisor ===
ps -ef | grep serial_supervisor | grep -v grep || echo dead
tail -n 20 {OUT}/supervisor.log 2>/dev/null
echo === ablation ===
ps -ef | grep run_ablation | grep -v grep | head
echo === lines ===
wc -l {OUT}/cond_A/ablation_A.jsonl 2>/dev/null
grep -E '^\\[ok\\]|^\\[ERROR\\]|^\\[suite\\]|^\\[max-cases\\]|^########' {OUT}/cond_A/run.log 2>/dev/null | tail -15
echo === vllm ===
curl -sS -o /dev/null -w '%{{http_code}}\\n' --max-time 5 http://127.0.0.1:8000/v1/models || echo x
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
""",
        timeout=40,
    )
    print(o, flush=True)
    client.close()
    print(f"[ok] serial A→B→C on GPU0 OUT={OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
