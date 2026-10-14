# -*- coding: utf-8 -*-
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
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)

    def run(cmd: str, timeout: int = 120) -> str:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        stdout.channel.recv_exit_status()
        return out + (("\n" + err) if err.strip() else "")

    print("[1] kill by pid list", flush=True)
    print(run(r"""
set +e
# stop ablation first
ps -ef | awk '/run_ablation|_worker_/ && !/awk/ {print $2}' | xargs -r kill -9
# kill every vllm api_server
ps -ef | awk '/vllm.entrypoints.openai.api_server/ && !/awk/ {print $2}' | tee /tmp/vllm_pids.txt | xargs -r kill -9
sleep 2
# kill anything still on 8000
pids=$(ss -lntp | sed -n 's/.*:8000.*pid=\([0-9]\+\).*/\1/p' | sort -u)
echo port_pids=$pids
for p in $pids; do kill -9 $p 2>/dev/null; done
# nvidia compute apps except none
nvidia-smi --query-compute-apps=pid --format=csv,noheader | tr -d ' ' | while read p; do
  [ -n "$p" ] && kill -9 "$p" 2>/dev/null || true
done
sleep 3
echo '=== leftover ==='
ps -ef | grep -E 'vllm|run_ablation|_worker_' | grep -v grep || echo none
ss -lntp | grep 8000 || echo port_free
nvidia-smi --query-gpu=memory.used --format=csv,noheader
"""), flush=True)

    print("[2] start ONLY 32k", flush=True)
    print(run(f"""
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
echo started=$(cat {VLLM_PID})
"""), flush=True)

    for i in range(100):
        out = run("curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models || echo fail")
        print(f"try {i+1}: {out.strip()}", flush=True)
        if out.strip() == "200":
            break
        if (i + 1) % 4 == 0:
            print(run(f"tail -n 20 {VLLM_LOG}")[-1200:], flush=True)
            if "CUDA out of memory" in run(f"tail -n 40 {VLLM_LOG}"):
                print("OOM", flush=True)
                client.close()
                return 1
        time.sleep(8)
    else:
        print("not ready", flush=True)
        client.close()
        return 1

    chk = run(r"""
ps -ef | grep vllm.entrypoints.openai.api_server | grep -v grep
n=$(ps -ef | grep vllm.entrypoints.openai.api_server | grep -v grep | wc -l)
echo count=$n
ps -ef | grep vllm.entrypoints.openai.api_server | grep -v grep | grep -q '32768' && echo HAS_32K || echo NO_32K
ps -ef | grep vllm.entrypoints.openai.api_server | grep -v grep | grep -q '8192' && echo STILL_8192 || echo NO_8192
""")
    print(chk, flush=True)
    if "HAS_32K" not in chk or "STILL_8192" in chk or "count=1" not in chk:
        print("[fatal] server state bad", flush=True)
        client.close()
        return 1

    print("[3] rerun core", flush=True)
    run(f"rm -rf {OUT} {REMOTE_BENCH}/runs/_workers; mkdir -p {OUT}")
    out = run(f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
date '+%F %T' > {OUT}/started_wall.txt
nohup python -m salvage_bench.run_ablation --suite core --conds A,B,C --turn-timeout 420 --out-dir {OUT} > {OUT}/run.log 2>&1 &
echo $! > {OUT}/run.pid
echo started_pid=$(cat {OUT}/run.pid)
""")
    print(out, flush=True)
    pid = [ln.split("=", 1)[1] for ln in out.splitlines() if ln.startswith("started_pid=")][0]

    deadline = time.time() + 14400
    last = ""
    while time.time() < deadline:
        out = run(f"""
grep -E '^==== SPAWN|^######## COND|elapsed=|maximum context' {OUT}/run.log | tail -20
echo '---'
wc -l {OUT}/ablation_A.jsonl {OUT}/ablation_B.jsonl {OUT}/ablation_C.jsonl 2>/dev/null
if [ -f {OUT}/summary.json ] && [ {OUT}/summary.json -nt {OUT}/started_wall.txt ]; then echo HAS_NEW_SUMMARY; else echo NO_NEW_SUMMARY; fi
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
grep -c 'maximum context length' {OUT}/run.log 2>/dev/null | awk '{{print "ctx_err",$1}}'
""")
        if out != last:
            print(out, flush=True)
            last = out
        if "HAS_NEW_SUMMARY" in out:
            break
        if "DEAD" in out and "HAS_NEW_SUMMARY" not in out:
            print("dead", flush=True)
            client.close()
            return 1
        try:
            ctx = int([x for x in out.splitlines() if x.startswith("ctx_err")][0].split()[1])
        except Exception:
            ctx = 0
        if ctx >= 3:
            print("ctx fail", flush=True)
            client.close()
            return 1
        time.sleep(45)

    print(run(f"cat {OUT}/SUMMARY.md"), flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
