# -*- coding: utf-8 -*-
"""Check remote cases_m.json suite sizes vs local."""
from __future__ import annotations

import sys

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=40, allow_agent=False, look_for_keys=False)
    cmd = r"""
set -e
ls -lh /root/autodl-tmp/work/salvage_faithfulness/data/cases_m.json
/root/autodl-tmp/work/bench-venv/bin/python - <<'PY'
import json,sys
from pathlib import Path
p=Path('/root/autodl-tmp/work/salvage_faithfulness/data/cases_m.json')
rows=json.loads(p.read_text(encoding='utf-8'))
print('n_rows', len(rows))
singles=[r for r in rows if not r.get('chain')]
chains=[r for r in rows if r.get('chain')]
print('singles', len(singles), 'chains', len(chains), 'chain_ids', len({r.get('chain') for r in chains}))
sys.path.insert(0,'/root/autodl-tmp/work/salvage_faithfulness')
from salvage_bench.cases_m import cases_by_mode, dataset_stats
print('dataset_stats', dataset_stats())
for m in ['core','chain','single','m','m3k']:
    print('suite', m, len(cases_by_mode(m)))
PY
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
