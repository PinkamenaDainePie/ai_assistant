# -*- coding: utf-8 -*-
import time
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
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
cmd = f"""
echo '=== worker db line ==='
rg -n \"^db =\" {REMOTE}/scripts/runs/_worker_s01_relief_kaifeng_5.py || grep -n \"^db =\" {REMOTE}/scripts/runs/_worker_s01_relief_kaifeng_5.py
echo '=== open files of worker ==='
PID=$(pgrep -f '_worker_s01_relief_kaifeng_5' | head -1)
echo PID=$PID
if [ -n \"$PID\" ]; then ls -l /proc/$PID/fd 2>/dev/null | head -40; tr '\\0' ' ' < /proc/$PID/cmdline; echo; ls -l /proc/$PID/cwd; fi
echo '=== find db ==='
find {REMOTE} -name '*.db' 2>/dev/null | head
echo '=== log ==='
tail -n 40 {REMOTE}/scripts/runs/ablation_m/run.log
echo '=== sleep 30 and recheck ==='
sleep 30
tail -n 60 {REMOTE}/scripts/runs/ablation_m/run.log
find {REMOTE} -name '*.db' 2>/dev/null | head
ls -la {REMOTE}/data | head
wc -l {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null || true
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=90)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace")[-1500:])
c.close()
