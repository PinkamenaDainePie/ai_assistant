# -*- coding: utf-8 -*-
from pathlib import Path
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/runs/ablation_memkg"
LOCAL = Path(__file__).resolve().parent / "scripts" / "runs" / "ablation_memkg"
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
names = ["summary.json", "SUMMARY.md", "run.log"] + [
    f"ablation_{x}.jsonl" for x in ["A0", "A1", "C0", "C1", "CK"]
]
for name in names:
    print("get", name)
    sftp.get(f"{REMOTE}/{name}", str(LOCAL / name))
sftp.close()
c.close()
print("done")
