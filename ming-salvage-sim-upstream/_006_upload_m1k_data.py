# -*- coding: utf-8 -*-
"""Upload cases_m_1000.json + updated cases_m.py / run_ablation.py to 006 ljc."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

LOCAL_BENCH = Path(r"e:\ai_assistant\experiments\salvage_faithfulness")
REMOTE_BENCH = "/home/async/data-disk/ljc/salvage_faithfulness"

FILES = [
    ("data/cases_m_1000.json", f"{REMOTE_BENCH}/data/cases_m_1000.json"),
    ("data/cases_m_1000_meta.json", f"{REMOTE_BENCH}/data/cases_m_1000_meta.json"),
    ("salvage_bench/cases_m.py", f"{REMOTE_BENCH}/salvage_bench/cases_m.py"),
    ("salvage_bench/run_ablation.py", f"{REMOTE_BENCH}/salvage_bench/run_ablation.py"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    sftp = c.open_sftp()
    for rel, rpath in FILES:
        lpath = LOCAL_BENCH / rel
        print(f"[put] {rel} -> {rpath} ({lpath.stat().st_size} bytes)", flush=True)
        sftp.put(str(lpath), rpath)
    sftp.close()
    _, o, _ = c.exec_command(
        f"""
# ensure full set still present
wc -c {REMOTE_BENCH}/data/cases_m.json {REMOTE_BENCH}/data/cases_m_1000.json
/home/async/data-disk/ljc/salvage-bench-venv313/bin/python - <<'PY'
import sys
sys.path.insert(0, '{REMOTE_BENCH}')
from salvage_bench.cases_m import dataset_stats, cases_by_mode
print(dataset_stats())
print('m1k', len(cases_by_mode('m1k')), 'm3k', len(cases_by_mode('m3k')))
PY
""",
        timeout=40,
    )
    print(o.read().decode("utf-8", "replace"))
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
