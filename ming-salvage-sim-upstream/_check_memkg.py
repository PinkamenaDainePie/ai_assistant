# -*- coding: utf-8 -*-
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = "/home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_memkg"
cmd = f"""
ls -lah {OUT}
wc -l {OUT}/ablation_*.jsonl 2>/dev/null || echo NO_JSONL
grep -nE 'NameError|SPAWN|summary A|\\[ERROR\\]|chapter-memory|CHAPTER_MEMORY|live=' {OUT}/run.log | tail -n 60
echo '--- TAIL ---'
tail -n 20 {OUT}/run.log
"""
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
_, stdout, stderr = c.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", "replace"))
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print("STDERR", err[-500:])
c.close()
