# -*- coding: utf-8 -*-
from pathlib import Path
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_m"
LOCAL = Path(__file__).resolve().parent / "scripts" / "runs" / "ablation_m"
LOCAL.mkdir(parents=True, exist_ok=True)

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
sftp = c.open_sftp()
for name in (
    "summary.json",
    "SUMMARY.md",
    "ablation_A.jsonl",
    "ablation_B.jsonl",
    "ablation_C.jsonl",
):
    remote = f"{REMOTE}/{name}"
    local = LOCAL / name
    print("get", remote, "->", local)
    sftp.get(remote, str(local))
sftp.close()
c.close()
print("done")
print((LOCAL / "SUMMARY.md").read_text(encoding="utf-8"))
