# -*- coding: utf-8 -*-
import paramiko

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
cmd = r"""
echo '=== procs ==='
ps -o pid,ppid,stat,etime,cmd -C python 2>/dev/null | grep -E 'ablation|_worker_' || true
pgrep -af 'run_hallucination_ablation|_worker_' || echo NONE
echo '=== log tail ==='
tail -n 30 /home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_m/run.log
echo '=== log mtime ==='
stat -c '%y %s' /home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_m/run.log
stat -c '%y %s' /home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_m/ablation_C.jsonl 2>/dev/null
echo '=== proxy port ==='
ss -lntp 2>/dev/null | grep 18081 || netstat -lntp 2>/dev/null | grep 18081 || echo NO_18081
echo '=== env proxy ==='
grep -E 'PROXY|OPENAI_BASE' /home/async/data-disk/ljc/ming-salvage-sim-upstream/.env | sed 's/=.*/=***/'
date
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=40)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace")[-800:])
c.close()
