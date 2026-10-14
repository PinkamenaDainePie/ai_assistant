# -*- coding: utf-8 -*-
"""Upload missing __init__/_helpers, verify GameDB import, rerun core A,B,C."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

LOCAL_ENGINE = Path(r"e:\ai_assistant\ming-salvage-sim-upstream")
REMOTE_ENGINE = "/root/autodl-tmp/work/ming-salvage-sim-upstream"
REMOTE_BENCH = "/root/autodl-tmp/work/salvage_faithfulness"
BENCH_VENV = "/root/autodl-tmp/work/bench-venv"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )
    sftp = client.open_sftp()

    # upload all missing underscore-named py files under ming_sim
    uploaded = 0
    for path in (LOCAL_ENGINE / "ming_sim").rglob("*"):
        if not path.is_file():
            continue
        if path.suffix != ".py":
            continue
        name = path.name
        if not (name.startswith("_") or name == "__init__.py"):
            # also re-upload __init__ which starts with __
            pass
        if not (name.startswith("_")):
            continue
        rel = path.relative_to(LOCAL_ENGINE).as_posix()
        remote = f"{REMOTE_ENGINE}/{rel}"
        # ensure parent dir
        parent = "/".join(remote.split("/")[:-1])
        try:
            sftp.stat(parent)
        except FileNotFoundError:
            # mkdir -p via ssh later
            pass
        print(f"upload {rel}", flush=True)
        # create dirs
        parts = remote.split("/")
        for i in range(2, len(parts)):
            d = "/".join(parts[:i])
            try:
                sftp.stat(d)
            except FileNotFoundError:
                try:
                    sftp.mkdir(d)
                except OSError:
                    pass
        sftp.put(str(path), remote)
        uploaded += 1
    sftp.close()
    print(f"[uploaded] {uploaded} underscore py files", flush=True)

    def run(cmd: str, timeout: int = 60) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        if err.strip():
            out = (out + "\n" + err) if out else err
        return rc, out

    print("[verify] GameDB import", flush=True)
    rc, out = run(
        f"""
# clear pycache
find {REMOTE_ENGINE}/ming_sim -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true
{BENCH_VENV}/bin/python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.db import GameDB
from ming_sim.session import GameSession
print('OK', GameDB, GameSession)
PY
ls {REMOTE_ENGINE}/ming_sim/__init__.py {REMOTE_ENGINE}/ming_sim/db/__init__.py {REMOTE_ENGINE}/ming_sim/db/_helpers.py
"""
    )
    print(out, flush=True)
    if rc != 0 or "OK" not in out:
        print("[fatal] import still broken", flush=True)
        client.close()
        return 1

    print("[kill] old ablation", flush=True)
    run(
        f"""
pkill -f 'salvage_bench.run_ablation' || true
pkill -f '_worker_' || true
rm -rf {REMOTE_BENCH}/runs/ablation_core_autodl {REMOTE_BENCH}/runs/_workers
mkdir -p {REMOTE_BENCH}/runs/ablation_core_autodl
"""
    )

    print("[start] core A,B,C", flush=True)
    rc, out = run(
        f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
nohup python -m salvage_bench.run_ablation \
  --suite core --conds A,B,C \
  --turn-timeout 360 \
  --out-dir runs/ablation_core_autodl \
  > runs/ablation_core_autodl/run.log 2>&1 &
echo $! > runs/ablation_core_autodl/run.pid
echo started_pid=$(cat runs/ablation_core_autodl/run.pid)
""",
        timeout=30,
    )
    print(out, flush=True)
    pid = "unknown"
    for line in out.splitlines():
        if line.startswith("started_pid="):
            pid = line.split("=", 1)[1].strip()

    print(f"[poll] pid={pid}", flush=True)
    deadline = time.time() + 7200
    while time.time() < deadline:
        rc, out = run(
            f"""
tail -n 25 {REMOTE_BENCH}/runs/ablation_core_autodl/run.log
echo '---'
ls {REMOTE_BENCH}/runs/ablation_core_autodl/*.jsonl 2>/dev/null | wc -l | awk '{{print "jsonl",$1}}'
test -f {REMOTE_BENCH}/runs/ablation_core_autodl/summary.json && echo HAS_SUMMARY || echo NO_SUMMARY
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
grep -c 'ImportError' {REMOTE_BENCH}/runs/ablation_core_autodl/run.log 2>/dev/null | awk '{{print "importerr",$1}}'
""",
            timeout=30,
        )
        print(out, flush=True)
        if "HAS_SUMMARY" in out:
            break
        if "DEAD" in out and "HAS_SUMMARY" not in out:
            print("[fail] died", flush=True)
            client.close()
            return 1
        # early abort if still import errors after first cases
        if "importerr" in out:
            try:
                n = int([x for x in out.splitlines() if x.startswith("importerr")][0].split()[1])
            except Exception:
                n = 0
            if n >= 3 and "SPAWN" in out:
                # give it a moment; if first wave still ImportError, fail fast
                if "cannot import name 'GameDB'" in out:
                    print("[fail] GameDB still broken in workers", flush=True)
                    client.close()
                    return 1
        time.sleep(25)

    rc, out = run(
        f"""
echo '=== SUMMARY.md ==='
cat {REMOTE_BENCH}/runs/ablation_core_autodl/SUMMARY.md 2>/dev/null | head -100
echo '=== summary.json head ==='
{BENCH_VENV}/bin/python -m json.tool {REMOTE_BENCH}/runs/ablation_core_autodl/summary.json 2>/dev/null | head -120
""",
        timeout=30,
    )
    print(out, flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
