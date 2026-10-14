# -*- coding: utf-8 -*-
import time
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV_PY = f"{REMOTE}/.venv/bin/python"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
PIDF = f"{REMOTE}/scripts/runs/ablation_m/run.pid"
LAUNCHER = f"{REMOTE}/scripts/runs/ablation_m/start.sh"

PROBE = r'''
import httpx
from pathlib import Path
env = {}
for raw in Path("/home/async/data-disk/ljc/ming-salvage-sim-upstream/.env").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
base = env["OPENAI_BASE_URL"].rstrip("/")
key = env["OPENAI_API_KEY"]
r = httpx.get(base + "/models", headers={"Authorization": "Bearer " + key}, timeout=20)
print("API", r.status_code, env["OPENAI_BASE_URL"])
'''

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "202.115.17.216",
    port=11222,
    username="async",
    password="asdf@1234",
    timeout=30,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd, timeout=30):
    print("[ssh]", cmd[:200])
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2000:])
    if err.strip():
        print("[stderr]", err[-800:])
    print("[exit]", code)
    return out, code


run(f"{VENV_PY} - <<'PY'\n{PROBE}\nPY", timeout=40)
run(
    "pkill -f 'scripts/run_hallucination_ablation.py' >/dev/null 2>&1; "
    "pkill -f 'scripts/runs/_worker_' >/dev/null 2>&1; sleep 1; echo KILLED"
)
run(
    f"mkdir -p {REMOTE}/scripts/runs/ablation_m; "
    f"rm -f {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl "
    f"{REMOTE}/scripts/runs/ablation_m/summary.json "
    f"{REMOTE}/scripts/runs/_turn_*.json; "
    f": > {LOG}; echo CLEAN"
)

script = (
    "#!/bin/bash\n"
    f"cd {REMOTE} || exit 1\n"
    f"exec {VENV_PY} -X utf8 scripts/run_hallucination_ablation.py "
    f"--suite m --conds A,B,C --turn-timeout 360 "
    f"--out-dir scripts/runs/ablation_m\n"
)
sftp = c.open_sftp()
with sftp.file(LAUNCHER, "w") as f:
    f.write(script)
sftp.close()
run(f"chmod +x {LAUNCHER}")
run(
    f"nohup {LAUNCHER} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; "
    f"echo STARTED $(cat {PIDF})",
    timeout=10,
)
time.sleep(4)
run(f"pgrep -af run_hallucination_ablation || echo NONE; tail -n 40 {LOG}")
c.close()
