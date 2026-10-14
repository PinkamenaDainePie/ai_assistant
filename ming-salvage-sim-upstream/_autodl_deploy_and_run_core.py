# -*- coding: utf-8 -*-
"""Pack slim engine+bench, upload to AutoDL, install deps, run core A,B,C."""
from __future__ import annotations

import io
import sys
import tarfile
import time
from pathlib import Path

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

LOCAL_ENGINE = Path(r"e:\ai_assistant\ming-salvage-sim-upstream")
LOCAL_BENCH = Path(r"e:\ai_assistant\experiments\salvage_faithfulness")
REMOTE_ROOT = "/root/autodl-tmp/work"
REMOTE_TGZ = "/root/autodl-tmp/salvage_bundle.tgz"
REMOTE_ENGINE = f"{REMOTE_ROOT}/ming-salvage-sim-upstream"
REMOTE_BENCH = f"{REMOTE_ROOT}/salvage_faithfulness"
BENCH_VENV = f"{REMOTE_ROOT}/bench-venv"


def _add_tree(tf: tarfile.TarFile, src: Path, arc_prefix: str, *, allow_dirs: set[str] | None = None) -> None:
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        parts = rel.split("/")
        if any(p in {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"} for p in parts):
            continue
        if allow_dirs is not None:
            # only top-level dirs/files in allow list
            top = parts[0]
            if top not in allow_dirs and path.parent != src:
                # allow files at root if listed
                if not (len(parts) == 1 and top in allow_dirs):
                    continue
            if path.parent == src and top not in allow_dirs:
                continue
        # skip heavy / irrelevant
        if path.suffix.lower() in {".db", ".db-journal", ".pdf", ".docx", ".png", ".jpg", ".tgz", ".zip", ".pem"}:
            continue
        if path.name.startswith("_probe") or path.name.startswith("_autodl") or path.name.startswith("_remote"):
            continue
        if path.name.startswith("_check") or path.name.startswith("_pull") or path.name.startswith("_sync"):
            continue
        if path.name.startswith("_resume") or path.name.startswith("_deploy") or path.name.startswith("_api_"):
            continue
        if path.name.startswith("_hold") or path.name.startswith("_fix_") or path.name.startswith("_wait"):
            continue
        arcname = f"{arc_prefix}/{rel}"
        tf.add(path, arcname=arcname, recursive=False)


def build_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # engine: slim
        engine_allow = {
            "ming_sim",
            "content",
            "requirements.txt",
            "README.md",
            "data",  # filtered further by extension; keep scenarios json
        }
        # custom walk for engine
        for path in LOCAL_ENGINE.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(LOCAL_ENGINE).as_posix()
            parts = rel.split("/")
            if any(p in {".git", ".venv", "__pycache__", "node_modules", "web", "docs", "scripts", "experiments", "saves", "wheelhouse_linux"} for p in parts):
                continue
            top = parts[0]
            if top not in engine_allow and not (len(parts) == 1 and path.name in engine_allow):
                continue
            if path.suffix.lower() in {".db", ".db-journal", ".pdf", ".docx", ".png", ".jpg", ".tgz", ".zip", ".pem"}:
                continue
            # only skip local helper scripts at engine root, never package __init__/_helpers
            if len(parts) == 1 and path.name.startswith("_"):
                continue
            # skip large save trees under data
            if "data/saves" in rel or "data\\saves" in rel:
                continue
            if "/scenario_dbs/" in f"/{rel}/" or rel.startswith("data/scenario_dbs"):
                continue
            tf.add(path, arcname=f"ming-salvage-sim-upstream/{rel}", recursive=False)

        # bench package
        for path in LOCAL_BENCH.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(LOCAL_BENCH).as_posix()
            parts = rel.split("/")
            if any(p in {".git", ".venv", "__pycache__", "runs"} for p in parts):
                continue
            if path.suffix.lower() in {".bak", ".bak.json"} or ".bak." in path.name:
                continue
            if path.name.endswith(".bak.json") or "before_" in path.name:
                continue
            # keep core data; skip huge optional backups already filtered
            if rel.startswith("data/") and path.name not in {
                "cases_m.json",
                "cases_m.jsonl",
                "cases_m_core.json",
                "cases_m_stats.json",
                "cases_m_clean.json",
            }:
                # still allow cases_m.json (main) - actually keep all non-bak under data
                if path.suffix not in {".json", ".jsonl"}:
                    continue
                if any(x in path.name for x in ("bak", "before", "3000_before", "clean.before")):
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
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        text = out
        if err.strip():
            text += ("\n" + err if text else err)
        return rc, text

    # verify vllm
    rc, out = run("curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/v1/models")
    print(f"  vllm /v1/models HTTP {out.strip()}", flush=True)
    if out.strip() != "200":
        print("[fatal] vLLM not up", flush=True)
        client.close()
        return 1

    print("[3] upload", flush=True)
    sftp = client.open_sftp()
    with sftp.file(REMOTE_TGZ, "wb") as rf:
        rf.write(blob)
    sftp.close()

    print("[4] extract + configure", flush=True)
    rc, out = run(
        f"""
set -e
mkdir -p {REMOTE_ROOT}
rm -rf {REMOTE_ENGINE} {REMOTE_BENCH}
tar -xzf {REMOTE_TGZ} -C {REMOTE_ROOT}
# engine_root for bench
printf '%s\\n' {REMOTE_ENGINE} > {REMOTE_BENCH}/engine_root.txt
# .env for local vllm
cat > {REMOTE_ENGINE}/.env <<'EOF'
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=qwen2.5-7b-instruct
OPENAI_TIMEOUT_SECONDS=300
EOF
ls -la {REMOTE_ENGINE} | head
ls -la {REMOTE_BENCH} | head
du -sh {REMOTE_ENGINE} {REMOTE_BENCH}
test -d {REMOTE_ENGINE}/ming_sim
test -f {REMOTE_BENCH}/salvage_bench/run_ablation.py
""",
        timeout=120,
    )
    print(out, flush=True)
    if rc != 0:
        print("[fatal] extract failed", rc, flush=True)
        client.close()
        return rc

    print("[5] bench venv + deps", flush=True)
    rc, out = run(
        f"""
set -e
export PIP_CACHE_DIR=/root/autodl-tmp/pip-cache
export TMPDIR=/root/autodl-tmp/tmp
/root/miniconda3/bin/python -m venv {BENCH_VENV}
. {BENCH_VENV}/bin/activate
pip install -U pip wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r {REMOTE_ENGINE}/requirements.txt openai httpx -i https://pypi.tuna.tsinghua.edu.cn/simple
python -c "import agno,openai; print('agno/openai ok')"
python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.llm_config import load_llm_config
import os
os.environ['OPENAI_API_KEY']='EMPTY'
os.environ['OPENAI_BASE_URL']='http://127.0.0.1:8000/v1'
os.environ['OPENAI_MODEL']='qwen2.5-7b-instruct'
print('engine import ok')
PY
""",
        timeout=600,
    )
    print(out[-4000:], flush=True)
    if rc != 0:
        print("[fatal] deps failed", rc, flush=True)
        client.close()
        return rc

    print("[6] run core A,B,C", flush=True)
    # long running — nohup and poll
    run_cmd = f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
mkdir -p runs/ablation_core_autodl
nohup python -m salvage_bench.run_ablation \
  --suite core --conds A,B,C \
  --turn-timeout 360 \
  --out-dir runs/ablation_core_autodl \
  > runs/ablation_core_autodl/run.log 2>&1 &
echo $! > runs/ablation_core_autodl/run.pid
echo started_pid=$(cat runs/ablation_core_autodl/run.pid)
"""
    rc, out = run(run_cmd, timeout=30)
    print(out, flush=True)

    pid = None
    for line in out.splitlines():
        if line.startswith("started_pid="):
            pid = line.split("=", 1)[1].strip()
    print(f"[7] poll pid={pid}", flush=True)
    deadline = time.time() + 7200
    last_len = 0
    while time.time() < deadline:
        rc, out = run(
            f"""
wc -c < {REMOTE_BENCH}/runs/ablation_core_autodl/run.log
tail -n 30 {REMOTE_BENCH}/runs/ablation_core_autodl/run.log
ls {REMOTE_BENCH}/runs/ablation_core_autodl/*.jsonl 2>/dev/null | wc -l
test -f {REMOTE_BENCH}/runs/ablation_core_autodl/summary.json && echo HAS_SUMMARY || echo NO_SUMMARY
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
""",
            timeout=30,
        )
        print(out, flush=True)
        if "HAS_SUMMARY" in out:
            print("[ok] summary ready", flush=True)
            break
        if "DEAD" in out and "HAS_SUMMARY" not in out:
            print("[fail] process died without summary", flush=True)
            client.close()
            return 1
        time.sleep(20)

    rc, out = run(
        f"""
python -m json.tool {REMOTE_BENCH}/runs/ablation_core_autodl/summary.json 2>/dev/null | head -120
echo '--- SUMMARY.md ---'
head -80 {REMOTE_BENCH}/runs/ablation_core_autodl/SUMMARY.md 2>/dev/null
""",
        timeout=30,
    )
    print(out, flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
