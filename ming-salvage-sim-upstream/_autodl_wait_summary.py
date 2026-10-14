# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"
OUT = "/root/autodl-tmp/work/salvage_faithfulness/runs/ablation_core_autodl"
BENCH_VENV = "/root/autodl-tmp/work/bench-venv"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)

    def run(cmd: str, timeout: int = 40) -> str:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        stdout.channel.recv_exit_status()
        return out + (("\n" + err) if err.strip() else "")

    deadline = time.time() + 12000
    last = ""
    while time.time() < deadline:
        out = run(
            f"""
wc -l {OUT}/ablation_A.jsonl {OUT}/ablation_B.jsonl {OUT}/ablation_C.jsonl 2>/dev/null
grep -E '^######## COND|^\\[ok\\]|^\\[ERROR\\]' {OUT}/run.log | tail -8
ps -ef | awk '/run_ablation/ && !/awk/ {{print "PID",$2}}'
if [ -f {OUT}/summary.json ] && [ -f {OUT}/started_wall.txt ] && [ {OUT}/summary.json -nt {OUT}/started_wall.txt ]; then echo HAS_NEW_SUMMARY; else echo NO_NEW_SUMMARY; fi
grep -c 'maximum context length' {OUT}/run.log 2>/dev/null | awk '{{print "ctx_err",$1}}'
"""
        )
        # always print a one-line heartbeat with counts
        lines = [ln for ln in out.splitlines() if "jsonl" in ln or ln.strip().endswith(".jsonl") or ln.startswith(" ") or "ablation_" in ln]
        brief = " | ".join(out.splitlines()[:4])
        if out != last:
            print(out, flush=True)
            last = out
        else:
            print(f"[hb] {brief}", flush=True)
        if "HAS_NEW_SUMMARY" in out:
            break
        if "PID" not in out and "HAS_NEW_SUMMARY" not in out:
            # process gone
            print("[warn] run_ablation not found", flush=True)
            if "HAS_NEW_SUMMARY" not in out:
                time.sleep(10)
                out2 = run(f"test -f {OUT}/summary.json && echo HAS || echo NO; tail -n 30 {OUT}/run.log")
                print(out2, flush=True)
                if "HAS" not in out2:
                    client.close()
                    return 1
            break
        time.sleep(60)

    print("=== SUMMARY.md ===", flush=True)
    print(run(f"cat {OUT}/SUMMARY.md"), flush=True)
    print(run(f"""
{BENCH_VENV}/bin/python - <<'PY'
import json
from pathlib import Path
d=json.loads(Path('{OUT}/summary.json').read_text())
meta=d.get('run_metadata',{{}})
print('model', meta.get('openai_model'), 'base', meta.get('openai_base_url'))
for t, trial in d.get('conds',{{}}).items():
  for c,row in (trial.get('conds') or {{}}).items():
    print(c, 'n_ok', row.get('n_ok'), 'errors', row.get('errors'), 'mean_live', row.get('mean_live'), 'mean_narr', row.get('mean_narr'))
PY
"""), flush=True)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
