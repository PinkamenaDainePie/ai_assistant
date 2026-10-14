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
REMOTE=/home/async/data-disk/ljc/ming-salvage-sim-upstream
echo '=== status ==='
pgrep -af run_hallucination_ablation || echo NONE
pgrep -af '_worker_' || echo NO_WORKER
tail -n 50 $REMOTE/scripts/runs/ablation_m/run.log
echo '=== workers ROOT ==='
head -n 20 $REMOTE/scripts/runs/_worker_s01_relief_kaifeng_5.py 2>/dev/null || echo NO_WORKER_FILE
echo '=== sqlite test ==='
rm -rf $REMOTE/data/*
mkdir -p $REMOTE/data
$REMOTE/.venv/bin/python - <<'PY'
import sqlite3
from pathlib import Path
p = Path("/home/async/data-disk/ljc/ming-salvage-sim-upstream/data/test_write.db")
if p.exists():
    p.unlink()
conn = sqlite3.connect(str(p))
conn.executescript("create table t(x int); insert into t values (1);")
conn.commit()
print("sqlite_ok", list(conn.execute("select * from t")))
conn.close()
# also GameDB init
import sys
sys.path.insert(0, "/home/async/data-disk/ljc/ming-salvage-sim-upstream")
from ming_sim.db import GameDB
dbp = "/home/async/data-disk/ljc/ming-salvage-sim-upstream/data/gamedb_test.db"
Path(dbp).unlink(missing_ok=True)
g = GameDB(dbp)
print("gamedb_ok", g.path)
g.close()
PY
ls -la $REMOTE/data | head
echo '=== jsonl ==='
wc -l $REMOTE/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null || true
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace")[-2000:])
c.close()
