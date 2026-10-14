# -*- coding: utf-8 -*-
"""Kill ablation/workers, wipe data dbs, restart once. Tunnel must already be up."""
import time
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV_PY = f"{REMOTE}/.venv/bin/python"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
PIDF = f"{REMOTE}/scripts/runs/ablation_m/run.pid"
LAUNCHER = f"{REMOTE}/scripts/runs/ablation_m/start.sh"

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


def run(cmd, timeout=40):
    print("[ssh]", cmd[:220], flush=True)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2500:], flush=True)
    if err.strip():
        print("[stderr]", err[-1000:], flush=True)
    print("[exit]", code, flush=True)
    return out


# 1) API check with key
run(
    f"{VENV_PY} - <<'PY'\n"
    "import httpx\n"
    "from pathlib import Path\n"
    "env={}\n"
    f"for raw in Path('{REMOTE}/.env').read_text(encoding='utf-8').splitlines():\n"
    "    if (not raw.strip()) or raw.startswith('#') or ('=' not in raw): continue\n"
    "    k,v=raw.split('=',1); env[k.strip()]=v.strip().strip(chr(34)).strip(chr(39))\n"
    "r=httpx.get(env['OPENAI_BASE_URL'].rstrip('/')+'/models', headers={'Authorization':'Bearer '+env['OPENAI_API_KEY']}, timeout=20)\n"
    "print('API', r.status_code)\n"
    "PY"
)

# 2) hard kill
run("kill -9 $(pgrep -f 'scripts/run_hallucination_ablation.py') 2>/dev/null; "
    "kill -9 $(pgrep -f 'scripts/runs/_worker_') 2>/dev/null; "
    "sleep 2; "
    "pgrep -af 'run_hallucination_ablation|_worker_' || echo ALL_DEAD")

# 3) wipe
run(
    f"rm -rf {REMOTE}/data/*; mkdir -p {REMOTE}/data {REMOTE}/scripts/runs/ablation_m; "
    f"rm -f {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl "
    f"{REMOTE}/scripts/runs/ablation_m/summary.json "
    f"{REMOTE}/scripts/runs/ablation_m/SUMMARY.md "
    f"{REMOTE}/scripts/runs/_turn_*.json "
    f"{REMOTE}/scripts/runs/_worker_*.py; "
    f": > {LOG}; echo WIPED"
)

# 4) launcher + start
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
run(f"nohup {LAUNCHER} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; echo STARTED $(cat {PIDF})", timeout=15)
time.sleep(8)
run(f"pgrep -af 'run_hallucination_ablation|_worker_' || echo NONE")
run(f"tail -n 60 {LOG}")
run(f"ls -la {REMOTE}/data | head")
c.close()
