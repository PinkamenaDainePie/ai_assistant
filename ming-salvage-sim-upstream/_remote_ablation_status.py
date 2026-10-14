# -*- coding: utf-8 -*-
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
OUT = f"{REMOTE}/scripts/runs/ablation_m"

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
echo '=== PROC ==='
pgrep -af 'scripts/run_hallucination_ablation.py' || echo NONE
echo '=== LOG TAIL ==='
tail -n 80 {LOG} 2>/dev/null || echo NO_LOG
echo '=== OUT DIR ==='
ls -lah {OUT} 2>/dev/null || true
echo '=== JSONL COUNTS ==='
for f in {OUT}/*.jsonl {OUT}/*/*.jsonl; do
  [ -f "$f" ] || continue
  echo "$(wc -l < "$f") $f"
done
echo '=== SUMMARY FILES ==='
ls -lah {OUT}/*summary* {OUT}/*.md {OUT}/*.json 2>/dev/null || true
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", "replace"))
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print("[stderr]", err[-1000:])
c.close()
