# -*- coding: utf-8 -*-
"""Hard-clean AutoDL ablation dir and rerun core A,B,C with robust polling."""
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

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

    def run(cmd: str, timeout: int = 60) -> tuple[int, str]:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        if err.strip():
            out = (out + "\n" + err) if out else err
        return rc, out

    print("[0] vllm + GameDB", flush=True)
    rc, out = run(
        f"""
curl -sS -o /dev/null -w 'vllm=%{{http_code}}\\n' --max-time 5 http://127.0.0.1:8000/v1/models
{BENCH_VENV}/bin/python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_ENGINE}')
from ming_sim.db import GameDB
from ming_sim.session import GameSession
print('import_ok')
PY
"""
    )
    print(out, flush=True)
    if "import_ok" not in out or "vllm=200" not in out:
        print("[fatal] prerequisites", flush=True)
        client.close()
        return 1

    print("[1] kill all ablation/workers", flush=True)
    run(
        r"""
pkill -9 -f 'salvage_bench.run_ablation' || true
pkill -9 -f '_worker_' || true
pkill -9 -f 'runs/ablation_core' || true
sleep 2
ps -ef | grep -E 'run_ablation|_worker_' | grep -v grep || echo 'no leftover procs'
"""
    )

    print("[2] wipe out dir", flush=True)
    run(
        f"""
rm -rf {OUT} {REMOTE_BENCH}/runs/_workers
mkdir -p {OUT}
test ! -f {OUT}/summary.json && echo CLEARED || echo STILL_HAS_SUMMARY
ls -la {OUT}
"""
    )

    print("[3] start", flush=True)
    rc, out = run(
        f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
# mark start time
date '+%F %T' > {OUT}/started_wall.txt
nohup python -m salvage_bench.run_ablation \
  --suite core --conds A,B,C \
  --turn-timeout 360 \
  --out-dir {OUT} \
  > {OUT}/run.log 2>&1 &
echo $! > {OUT}/run.pid
echo started_pid=$(cat {OUT}/run.pid)
""",
        timeout=30,
    )
    print(out, flush=True)
    pid = None
    for line in out.splitlines():
        if line.startswith("started_pid="):
            pid = line.split("=", 1)[1].strip()
    if not pid:
        print("[fatal] no pid", flush=True)
        client.close()
        return 1

    print(f"[4] poll pid={pid}", flush=True)
    deadline = time.time() + 10800
    last_tail = ""
    while time.time() < deadline:
        rc, out = run(
            f"""
# progress
echo WALL=$(cat {OUT}/started_wall.txt 2>/dev/null)
tail -n 20 {OUT}/run.log
echo '---'
grep -E '^==== SPAWN|^######## COND|^\\[ERROR\\]|^\\[OK\\]|elapsed=' {OUT}/run.log | tail -15
echo '---'
ls {OUT}/ablation_*.jsonl 2>/dev/null | wc -l | awk '{{print "jsonl_files",$1}}'
wc -l {OUT}/ablation_A.jsonl 2>/dev/null | awk '{{print "A_lines",$1}}'
wc -l {OUT}/ablation_B.jsonl 2>/dev/null | awk '{{print "B_lines",$1}}'
wc -l {OUT}/ablation_C.jsonl 2>/dev/null | awk '{{print "C_lines",$1}}'
# only accept summary newer than start marker
if [ -f {OUT}/summary.json ] && [ {OUT}/summary.json -nt {OUT}/started_wall.txt ]; then
  echo HAS_NEW_SUMMARY
else
  echo NO_NEW_SUMMARY
fi
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
grep -c 'ImportError' {OUT}/run.log 2>/dev/null | awk '{{print "importerr",$1}}'
grep -c 'worker_exit_1' {OUT}/run.log 2>/dev/null | awk '{{print "exit1",$1}}'
""",
            timeout=40,
        )
        if out != last_tail:
            print(out, flush=True)
            last_tail = out
        if "HAS_NEW_SUMMARY" in out:
            print("[ok] new summary", flush=True)
            break
        if "DEAD" in out and "HAS_NEW_SUMMARY" not in out:
            print("[fail] process dead", flush=True)
            _, log = run(f"tail -n 80 {OUT}/run.log")
            print(log, flush=True)
            client.close()
            return 1
        # fail fast on import errors
        if "importerr" in out:
            try:
                n = int([x for x in out.splitlines() if x.startswith("importerr")][0].split()[1])
            except Exception:
                n = 0
            if n >= 1:
                print("[fail] ImportError in run", flush=True)
                client.close()
                return 1
        time.sleep(30)

    rc, out = run(
        f"""
echo '=== SUMMARY.md ==='
cat {OUT}/SUMMARY.md
echo '=== errors sample ==='
{BENCH_VENV}/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('{OUT}/summary.json')
d=json.loads(p.read_text())
for tname, trial in d.get('conds',{{}}).items():
    for c, row in (trial.get('conds') or {{}}).items():
        print(c, 'n_ok=', row.get('n_ok'), 'errors=', row.get('errors'), 'mean_live=', row.get('mean_live'), 'mean_narr=', row.get('mean_narr'))
        errs=[r for r in row.get('rows',[]) if r.get('error')]
        print('  sample_err', errs[:3])
PY
""",
        timeout=40,
    )
    print(out, flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
