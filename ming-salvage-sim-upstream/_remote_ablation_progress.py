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
REMOTE=/home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_m
echo '=== counts ==='
wc -l $REMOTE/ablation_*.jsonl 2>/dev/null
echo '=== recent ==='
grep -E 'summary |######## COND |^\[ok\]|^\[ERROR\]|==== SPAWN|\[done\]' $REMOTE/run.log | tail -50
echo '=== summary? ==='
test -f $REMOTE/summary.json && echo HAS_SUMMARY || echo NO_SUMMARY
pgrep -c -f 'scripts/run_hallucination_ablation.py' || echo 0
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
print(stdout.read().decode("utf-8", "replace"))
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print("[stderr]", err[-500:])
c.close()
