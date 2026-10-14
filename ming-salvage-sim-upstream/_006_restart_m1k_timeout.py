# -*- coding: utf-8 -*-
"""Kill timed-out m1k run; restart A/B/C with turn-timeout=1200 (keep vLLM)."""
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

    print("[1] vLLM health", flush=True)
    _, out = run(
        """
for p in 8000 8001 8002; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:$p/v1/models || echo x)
  echo port_$p=$code
done
""",
        timeout=30,
    )
    print(out, flush=True)
    if "port_8000=200" not in out or "port_8001=200" not in out or "port_8002=200" not in out:
        print("[fatal] vLLM down — need relaunch first", flush=True)
        client.close()
        return 1

    print("[2] kill ablations/workers only", flush=True)
    run(
        """
pkill -f 'salvage_bench.run_ablation' || true
pkill -f 'runs/_workers/_worker_' || true
sleep 2
ps -ef | grep -E 'run_ablation|_worker_' | grep -v grep || echo no_ablation
""",
        timeout=30,
    )

    print("[3] wipe out + bump engine timeout", flush=True)
    run(
        f"""
rm -rf {OUT}
mkdir -p {OUT}
date '+%F %T' > {OUT}/started_wall.txt
# keep base_url default; each shard overrides OPENAI_BASE_URL
cat > {REMOTE_ENGINE}/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=600
EOF
""",
        timeout=20,
    )

    print("[4] relaunch A/B/C timeout=1200", flush=True)
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
export OPENAI_TIMEOUT_SECONDS=600
export HF_HUB_OFFLINE=1
cd {REMOTE_BENCH}
nohup python -m salvage_bench.run_ablation \
  --suite m3k --conds {cond} \
  --max-cases 1000 \
  --turn-timeout 1200 \
  --out-dir {cond_out} \
  > {cond_out}/run.log 2>&1 &
echo $! > {cond_out}/run.pid
echo started cond={cond} port={port} pid=$(cat {cond_out}/run.pid)
""",
            timeout=30,
        )
        print(out, flush=True)

    print("[5] wait first ok (~4 min)", flush=True)
    deadline = time.time() + 300
    while time.time() < deadline:
        _, out = run(
            f"""
wc -l {OUT}/cond_A/ablation_A.jsonl {OUT}/cond_B/ablation_B.jsonl {OUT}/cond_C/ablation_C.jsonl 2>/dev/null
for c in A B C; do
  echo ---$c---
  grep -E '^\\[ok\\]|^\\[ERROR\\]|^\\[suite\\]|^\\[max-cases\\]' {OUT}/cond_$c/run.log | tail -6
done
""",
            timeout=30,
        )
        print(out, flush=True)
        if "[ok]" in out:
            break
        if "[ERROR]" in out and "timeout" in out.lower():
            # keep waiting a bit; 1200s timeout means early errors are real
            pass
        time.sleep(45)

    _, out = run(
        f"""
ps -ef | grep run_ablation | grep -v grep | head
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
""",
        timeout=20,
    )
    print(out, flush=True)
    client.close()
    print("[ok] restarted with turn-timeout=1200", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
