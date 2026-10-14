# -*- coding: utf-8 -*-
"""Kill leftover 8192 vLLM, ensure only 32768 serves :8000, rerun core."""
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

MODEL_DIR = "/root/autodl-tmp/models/Qwen2.5-7B-Instruct"
VLLM_LOG = "/root/autodl-tmp/vllm_qwen7b.log"
VLLM_PID = "/root/autodl-tmp/vllm_qwen7b.pid"
VENV_PY = "/root/autodl-tmp/venv/bin/python"
REMOTE_ENGINE = "/root/autodl-tmp/work/ming-salvage-sim-upstream"
REMOTE_BENCH = "/root/autodl-tmp/work/salvage_faithfulness"
BENCH_VENV = "/root/autodl-tmp/work/bench-venv"
OUT = f"{REMOTE_BENCH}/runs/ablation_core_autodl"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        if err.strip():
            out = (out + "\n" + err) if out else err
        return rc, out

    print("[1] kill ALL python servers/ablation", flush=True)
    run(
        r"""
pkill -9 -f salvage_bench.run_ablation || true
pkill -9 -f _worker_ || true
pkill -9 -f vllm.entrypoints.openai.api_server || true
# also kill by port holders
fuser -k 8000/tcp 2>/dev/null || true
sleep 4
ps -ef | grep -E 'vllm|run_ablation|_worker_' | grep -v grep || echo CLEARED
ss -lntp | grep 8000 || echo PORT_FREE
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
"""
    )

    print("[2] start single 32k server", flush=True)
    run(
        f"""
set -e
export PATH=/root/autodl-tmp/venv/bin:$PATH
export CUDA_VISIBLE_DEVICES=0
rm -f {VLLM_LOG} {VLLM_PID}
nohup {VENV_PY} -m vllm.entrypoints.openai.api_server \
  --model {MODEL_DIR} \
  --served-model-name qwen2.5-7b-instruct \
  --host 0.0.0.0 --port 8000 \
  --dtype auto --max-model-len 32768 \
  --gpu-memory-utilization 0.92 \
  >{VLLM_LOG} 2>&1 &
echo $! >{VLLM_PID}
echo started_pid=$(cat {VLLM_PID})
"""
    )

    print("[3] wait ready + verify max len via error probe", flush=True)
    for i in range(100):
        rc, out = run(
            "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models || echo fail",
            timeout=20,
        )
        print(f"  try {i+1}: {out.strip()}", flush=True)
        if out.strip() == "200":
            break
        if (i + 1) % 5 == 0:
            _, log = run(f"tail -n 30 {VLLM_LOG}")
            print(log[-1800:], flush=True)
            if "CUDA out of memory" in log:
                print("[fatal] OOM at 32k", flush=True)
                client.close()
                return 1
        time.sleep(8)
    else:
        print("[fatal] not ready", flush=True)
        client.close()
        return 1

    # confirm only one server and cmdline has 32768
    rc, out = run(
        r"""
ps -ef | grep vllm.entrypoints.openai.api_server | grep -v grep
# ask models then a tiny chat
curl -sS --max-time 30 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5-7b-instruct","messages":[{"role":"user","content":"只回复pong"}],"max_tokens":8,"temperature":0}' | head -c 300
echo
nvidia-smi --query-gpu=memory.used --format=csv,noheader
"""
    )
    print(out, flush=True)
    if "32768" not in out or out.count("api_server") > 1 and out.count("\n") > 5:
        # soft check: must see 32768 in process list
        if "max-model-len 32768" not in out and "--max-model-len 32768" not in out:
            print("[fatal] 32k server not alone/confirmed", flush=True)
            client.close()
            return 1

    print("[4] start core ablation", flush=True)
    run(f"rm -rf {OUT} {REMOTE_BENCH}/runs/_workers; mkdir -p {OUT}")
    rc, out = run(
        f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
date '+%F %T' > {OUT}/started_wall.txt
nohup python -m salvage_bench.run_ablation --suite core --conds A,B,C --turn-timeout 420 --out-dir {OUT} > {OUT}/run.log 2>&1 &
echo $! > {OUT}/run.pid
echo started_pid=$(cat {OUT}/run.pid)
""",
        timeout=30,
    )
    print(out, flush=True)
    pid = [ln.split("=", 1)[1] for ln in out.splitlines() if ln.startswith("started_pid=")][0]

    print(f"[5] poll {pid}", flush=True)
    deadline = time.time() + 14400
    last = ""
    while time.time() < deadline:
        rc, out = run(
            f"""
grep -E '^==== SPAWN|^######## COND|elapsed=|maximum context' {OUT}/run.log | tail -20
echo '---'
wc -l {OUT}/ablation_A.jsonl {OUT}/ablation_B.jsonl {OUT}/ablation_C.jsonl 2>/dev/null
if [ -f {OUT}/summary.json ] && [ {OUT}/summary.json -nt {OUT}/started_wall.txt ]; then echo HAS_NEW_SUMMARY; else echo NO_NEW_SUMMARY; fi
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
grep -c 'maximum context length' {OUT}/run.log 2>/dev/null | awk '{{print "ctx_err",$1}}'
# success signal: any elapsed>=10 without error line immediately? count OK-ish rows
grep -c 'elapsed=' {OUT}/run.log 2>/dev/null | awk '{{print "elapsed_n",$1}}'
""",
            timeout=40,
        )
        if out != last:
            print(out, flush=True)
            last = out
        if "HAS_NEW_SUMMARY" in out:
            break
        if "DEAD" in out and "HAS_NEW_SUMMARY" not in out:
            print("[fail] dead", flush=True)
            client.close()
            return 1
        try:
            ctx = int([x for x in out.splitlines() if x.startswith("ctx_err")][0].split()[1])
        except Exception:
            ctx = 0
        if ctx >= 3:
            print("[fail] context errors persist", flush=True)
            client.close()
            return 1
        time.sleep(45)

    rc, out = run(
        f"""
cat {OUT}/SUMMARY.md
echo '---'
{BENCH_VENV}/bin/python - <<'PY'
import json
from pathlib import Path
d=json.loads(Path('{OUT}/summary.json').read_text())
for t, trial in d.get('conds',{{}}).items():
  for c,row in (trial.get('conds') or {{}}).items():
    print(c, 'n_ok', row.get('n_ok'), 'errors', row.get('errors'), 'mean_live', row.get('mean_live'), 'mean_narr', row.get('mean_narr'))
PY
"""
    )
    print(out, flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
