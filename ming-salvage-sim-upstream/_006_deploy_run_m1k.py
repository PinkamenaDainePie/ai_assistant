# -*- coding: utf-8 -*-
"""Deploy salvage_faithfulness + sync engine to 006 ljc; serve 3×vLLM; run A/B/C ×1000."""
from __future__ import annotations

import io
import sys
import tarfile
import time
from pathlib import Path

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

LOCAL_ENGINE = Path(r"e:\ai_assistant\ming-salvage-sim-upstream")
LOCAL_BENCH = Path(r"e:\ai_assistant\experiments\salvage_faithfulness")
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

# GPU -> (port, cond)
SHARDS = [
    (0, 8000, "A"),
    (2, 8001, "B"),
    (3, 8002, "C"),
]


def build_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # slim engine sync: ming_sim + content + requirements + wheelhouse
        for path in LOCAL_ENGINE.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(LOCAL_ENGINE).as_posix()
            parts = rel.split("/")
            if any(
                p in {".git", ".venv", "__pycache__", "node_modules", "web", "docs", "scripts", "experiments", "saves", "tests"}
                for p in parts
            ):
                continue
            top = parts[0]
            if top not in {"ming_sim", "content", "requirements.txt", "wheelhouse_linux", "data"} and not (
                len(parts) == 1 and path.name in {"requirements.txt", "README.md"}
            ):
                continue
            if path.suffix.lower() in {".db", ".db-journal", ".pdf", ".docx", ".png", ".jpg", ".tgz", ".zip", ".pem"}:
                continue
            if len(parts) == 1 and path.name.startswith("_"):
                continue
            if "data/saves" in rel or "scenario_dbs" in rel:
                continue
            # keep wheelhouse wheels only
            if top == "wheelhouse_linux" and path.suffix != ".whl":
                continue
            tf.add(path, arcname=f"ming-salvage-sim-upstream/{rel}", recursive=False)

        for path in LOCAL_BENCH.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(LOCAL_BENCH).as_posix()
            parts = rel.split("/")
            if any(p in {".git", ".venv", "__pycache__", "runs"} for p in parts):
                continue
            if path.suffix.lower() in {".bak", ".pem"} or ".bak." in path.name:
                continue
            if rel.startswith("data/") and path.suffix not in {".json", ".jsonl"}:
                continue
            if any(x in path.name for x in ("bak", "before_", "3000_before", "clean.before")):
                continue
            tf.add(path, arcname=f"salvage_faithfulness/{rel}", recursive=False)
    return buf.getvalue()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("[1] build tarball", flush=True)
    blob = build_tarball()
    print(f"  size={len(blob)/1e6:.1f} MB", flush=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[2] connect {HOST}:{PORT}", flush=True)
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        if err.strip():
            out = (out + "\n" + err) if out else err
        return rc, out

    print("[3] upload", flush=True)
    sftp = client.open_sftp()
    with sftp.file(REMOTE_TGZ, "wb") as rf:
        rf.write(blob)
    sftp.close()

    print("[4] extract + env", flush=True)
    rc, out = run(
        f"""
set -e
mkdir -p {REMOTE_LJC}
# extract into ljc (overwrites package trees, keeps other ljc files)
tar -xzf {REMOTE_TGZ} -C {REMOTE_LJC}
printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt
# point engine at local vLLM (default A shard; each run overrides OPENAI_BASE_URL)
cat > {REMOTE_ENGINE}/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=300
EOF
test -f {REMOTE_BENCH}/salvage_bench/run_ablation.py
test -d {REMOTE_ENGINE}/ming_sim
test -f {REMOTE_BENCH}/data/cases_m.json
wc -l {REMOTE_BENCH}/data/cases_m.json | awk '{{print "cases_json_lines",$1}}'
du -sh {REMOTE_ENGINE} {REMOTE_BENCH}
""",
        timeout=180,
    )
    print(out[-3000:], flush=True)
    if rc != 0:
        print("[fatal] extract", rc, flush=True)
        client.close()
        return rc

    print("[5] bench venv (offline wheelhouse)", flush=True)
    rc, out = run(
        f"""
set -e
export TMPDIR={REMOTE_LJC}/tmp
mkdir -p "$TMPDIR"
if [ ! -x {BENCH_VENV}/bin/python ]; then
  {CONDA_PY} -m venv {BENCH_VENV}
fi
. {BENCH_VENV}/bin/activate
pip install --no-index --find-links={REMOTE_ENGINE}/wheelhouse_linux -r {REMOTE_ENGINE}/requirements.txt openai httpx 2>&1 | tail -30
python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.db import GameDB
print('engine_import_ok')
sys.path.insert(0, '{REMOTE_BENCH}')
from salvage_bench.cases_m import dataset_stats
print('stats', dataset_stats())
PY
""",
        timeout=600,
    )
    print(out[-4000:], flush=True)
    if rc != 0 or "engine_import_ok" not in out:
        print("[fatal] bench venv", rc, flush=True)
        client.close()
        return 1

    print("[6] start 3× vLLM on free GPUs", flush=True)
    # kill prior salvage vllm on our ports only
    run(
        f"""
pkill -f 'salvage_bench.run_ablation' || true
for p in 8000 8001 8002; do
  fuser -k ${{p}}/tcp 2>/dev/null || true
done
sleep 2
""",
        timeout=30,
    )
    for gpu, port, cond in SHARDS:
        log = f"{REMOTE_LJC}/vllm_{port}.log"
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
  > {log} 2>&1 &
echo $! > {REMOTE_LJC}/vllm_{port}.pid
echo started gpu={gpu} port={port} cond={cond} pid=$(cat {REMOTE_LJC}/vllm_{port}.pid)
""",
            timeout=20,
        )
        print(out, flush=True)

    print("[7] wait vLLM ready", flush=True)
    deadline = time.time() + 900
    ready = {p: False for _, p, _ in SHARDS}
    while time.time() < deadline and not all(ready.values()):
        for _, port, _ in SHARDS:
            if ready[port]:
                continue
            rc, out = run(
                f"curl -sS -o /dev/null -w '%{{http_code}}' --max-time 5 http://127.0.0.1:{port}/v1/models || echo fail",
                timeout=20,
            )
            code = out.strip().splitlines()[-1] if out.strip() else "fail"
            if code == "200":
                ready[port] = True
                print(f"  port {port} ready", flush=True)
        if not all(ready.values()):
            time.sleep(10)
    if not all(ready.values()):
        print("[fatal] vLLM not ready", ready, flush=True)
        for _, port, _ in SHARDS:
            _, out = run(f"tail -n 40 {REMOTE_LJC}/vllm_{port}.log", timeout=20)
            print(f"--- log {port} ---", out[-2000:], flush=True)
        client.close()
        return 1

    print("[8] launch A/B/C max-cases=1000", flush=True)
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
        rc, out = run(
            f"""
set -e
mkdir -p {cond_out}
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL=http://127.0.0.1:{port}/v1
export OPENAI_MODEL=qwen2.5-7b-instruct
export CUDA_VISIBLE_DEVICES={gpu}
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

    print("[9] smoke poll 90s", flush=True)
    time.sleep(90)
    rc, out = run(
        f"""
echo === procs ===
ps -ef | grep -E 'run_ablation|api_server' | grep -v grep | head -20
echo === lines ===
wc -l {OUT}/cond_A/ablation_A.jsonl {OUT}/cond_B/ablation_B.jsonl {OUT}/cond_C/ablation_C.jsonl 2>/dev/null
echo === suite headers ===
grep -E '^\\[suite\\]|^\\[engine\\]|^######## COND|^\\[ok\\]|^\\[ERROR\\]' {OUT}/cond_A/run.log | head -20
grep -E '^\\[suite\\]|^######## COND|^\\[ok\\]|^\\[ERROR\\]' {OUT}/cond_B/run.log | head -10
grep -E '^\\[suite\\]|^######## COND|^\\[ok\\]|^\\[ERROR\\]' {OUT}/cond_C/run.log | head -10
echo === gpu ===
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
""",
        timeout=40,
    )
    print(out, flush=True)
    client.close()
    print(f"[ok] running under {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
