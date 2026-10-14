# -*- coding: utf-8 -*-
"""Upload content/ pack and rerun core ablation."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

LOCAL_CONTENT = Path(r"e:\ai_assistant\ming-salvage-sim-upstream\content")
REMOTE_ENGINE = "/root/autodl-tmp/work/ming-salvage-sim-upstream"
REMOTE_BENCH = "/root/autodl-tmp/work/salvage_faithfulness"
BENCH_VENV = "/root/autodl-tmp/work/bench-venv"
OUT = f"{REMOTE_BENCH}/runs/ablation_core_autodl"


def _mkdir_p(sftp: paramiko.SFTPClient, remote: str) -> None:
    parts = remote.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            try:
                sftp.mkdir(cur)
            except OSError:
                pass


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

    print("[1] kill current run", flush=True)
    run("pkill -9 -f salvage_bench.run_ablation || true; pkill -9 -f _worker_ || true; sleep 1")

    print("[2] upload content/", flush=True)
    sftp = client.open_sftp()
    n = 0
    for path in LOCAL_CONTENT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(LOCAL_CONTENT).as_posix()
        remote = f"{REMOTE_ENGINE}/content/{rel}"
        _mkdir_p(sftp, "/".join(remote.split("/")[:-1]))
        sftp.put(str(path), remote)
        n += 1
    sftp.close()
    print(f"  uploaded {n} files", flush=True)

    rc, out = run(
        f"test -f {REMOTE_ENGINE}/content/characters.json && echo CONTENT_OK; "
        f"{BENCH_VENV}/bin/python - <<'PY'\n"
        f"import sys; sys.path.insert(0,'{REMOTE_ENGINE}')\n"
        f"from ming_sim.content import GameContent\n"
        f"c=GameContent.load()\n"
        f"print('characters', len(getattr(c,'characters',{{}}) or getattr(c,'_characters',{{}}) or []) )\n"
        f"print('load_ok')\n"
        f"PY"
    )
    print(out, flush=True)
    if "CONTENT_OK" not in out:
        print("[fatal] content missing", flush=True)
        client.close()
        return 1

    print("[3] wipe + start", flush=True)
    run(f"rm -rf {OUT} {REMOTE_BENCH}/runs/_workers; mkdir -p {OUT}")
    rc, out = run(
        f"""
set -e
. {BENCH_VENV}/bin/activate
export PYTHONUTF8=1
export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}
cd {REMOTE_BENCH}
date '+%F %T' > {OUT}/started_wall.txt
nohup python -m salvage_bench.run_ablation --suite core --conds A,B,C --turn-timeout 360 --out-dir {OUT} > {OUT}/run.log 2>&1 &
echo $! > {OUT}/run.pid
echo started_pid=$(cat {OUT}/run.pid)
""",
        timeout=30,
    )
    print(out, flush=True)
    pid = [ln.split("=", 1)[1] for ln in out.splitlines() if ln.startswith("started_pid=")][0]

    print(f"[4] poll {pid}", flush=True)
    deadline = time.time() + 10800
    last = ""
    while time.time() < deadline:
        rc, out = run(
            f"""
tail -n 15 {OUT}/run.log
echo '---'
grep -E '^==== SPAWN|^######## COND|elapsed=|设定文件' {OUT}/run.log | tail -12
echo '---'
wc -l {OUT}/ablation_A.jsonl 2>/dev/null | awk '{{print "A_lines",$1}}'
wc -l {OUT}/ablation_B.jsonl 2>/dev/null | awk '{{print "B_lines",$1}}'
wc -l {OUT}/ablation_C.jsonl 2>/dev/null | awk '{{print "C_lines",$1}}'
if [ -f {OUT}/summary.json ] && [ {OUT}/summary.json -nt {OUT}/started_wall.txt ]; then echo HAS_NEW_SUMMARY; else echo NO_NEW_SUMMARY; fi
kill -0 {pid} 2>/dev/null && echo ALIVE || echo DEAD
grep -c '设定文件缺失' {OUT}/run.log 2>/dev/null | awk '{{print "missing_content",$1}}'
grep -c 'ImportError' {OUT}/run.log 2>/dev/null | awk '{{print "importerr",$1}}'
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
            miss = int([x for x in out.splitlines() if x.startswith("missing_content")][0].split()[1])
        except Exception:
            miss = 0
        if miss >= 3:
            print("[fail] still missing content", flush=True)
            client.close()
            return 1
        time.sleep(30)

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
