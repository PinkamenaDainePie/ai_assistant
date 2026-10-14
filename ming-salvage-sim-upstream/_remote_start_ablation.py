# -*- coding: utf-8 -*-
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV = f"{REMOTE}/.venv/bin/python"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
PIDF = f"{REMOTE}/scripts/runs/ablation_m/run.pid"

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

def run(cmd, timeout=60):
    print("[ssh]", cmd[:200])
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-3000:])
    if err.strip():
        print("[stderr]", err[-1500:])
    print("[exit]", code)
    return out, code

# status
run(f"ls -la {REMOTE}/scripts/runs/ablation_m 2>/dev/null || mkdir -p {REMOTE}/scripts/runs/ablation_m")
run(f"pgrep -af run_hallucination_ablation || echo NONE")
run(f"test -f {LOG} && wc -l {LOG} && tail -n 40 {LOG} || echo NO_LOG")

# kill stale if any hung from prior attempt without pid
run(
    f"if pgrep -f 'scripts/run_hallucination_ablation.py' >/dev/null; then "
    f"echo ALREADY_RUNNING; else "
    f"cd {REMOTE} && "
    f"nohup {VENV} -X utf8 scripts/run_hallucination_ablation.py "
    f"--suite m --conds A,B,C --turn-timeout 360 "
    f"--out-dir scripts/runs/ablation_m "
    f"> {LOG} 2>&1 < /dev/null & "
    f"echo $! > {PIDF}; "
    f"echo STARTED $(cat {PIDF}); "
    f"fi"
)

# brief check without waiting on the job
import time
time.sleep(2)
run(f"cat {PIDF} 2>/dev/null; pgrep -af run_hallucination_ablation || echo NONE")
run(f"tail -n 50 {LOG} || true")
c.close()
