# -*- coding: utf-8 -*-
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
    print("[ssh]", cmd[:240], flush=True)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-3000:], flush=True)
    if err.strip():
        print("[stderr]", err[-800:], flush=True)
    print("[exit]", code, flush=True)
    return out


# nuke by pid list from pgrep -f, excluding the kill shell itself
run(
    "python3 - <<'PY'\n"
    "import os, signal, subprocess, time\n"
    "out=subprocess.check_output(['pgrep','-af','ming-salvage-sim-upstream'], text=True)\n"
    "print('BEFORE')\n"
    "print(out)\n"
    "for line in out.splitlines():\n"
    "    parts=line.split(None,1)\n"
    "    if len(parts)<2: continue\n"
    "    pid=int(parts[0]); cmd=parts[1]\n"
    "    if 'pgrep' in cmd or 'python3 -' in cmd: continue\n"
    "    if 'run_hallucination_ablation' in cmd or '_worker_' in cmd or 'ablation_m/start.sh' in cmd:\n"
    "        print('KILL', pid, cmd[:120])\n"
    "        try: os.kill(pid, signal.SIGKILL)\n"
    "        except ProcessLookupError: pass\n"
    "time.sleep(2)\n"
    "after=subprocess.run(['pgrep','-af','run_hallucination_ablation|_worker_'], capture_output=True, text=True)\n"
    "print('AFTER', after.stdout or 'NONE')\n"
    "PY"
)

run(
    f"rm -rf {REMOTE}/data; mkdir -p {REMOTE}/data {REMOTE}/scripts/runs/ablation_m; "
    f"rm -f {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl "
    f"{REMOTE}/scripts/runs/ablation_m/summary.json "
    f"{REMOTE}/scripts/runs/ablation_m/SUMMARY.md "
    f"{REMOTE}/scripts/runs/_turn_*.json "
    f"{REMOTE}/scripts/runs/_worker_*.py; "
    f": > {LOG}; echo WIPED"
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

# ensure only one start
run(
    f"nohup {LAUNCHER} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; "
    f"echo STARTED $(cat {PIDF})",
    timeout=15,
)
time.sleep(12)
run(
    "python3 - <<'PY'\n"
    "import subprocess\n"
    "out=subprocess.run(['pgrep','-af','run_hallucination_ablation|_worker_'], capture_output=True, text=True)\n"
    "print(out.stdout or 'NONE')\n"
    "PY"
)
run(f"tail -n 80 {LOG}")
run(f"ls -la {REMOTE}/data | head -20")
c.close()
