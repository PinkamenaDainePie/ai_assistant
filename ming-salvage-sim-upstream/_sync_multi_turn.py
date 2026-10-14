# -*- coding: utf-8 -*-
import paramiko
from pathlib import Path

LOCAL = Path(__file__).resolve().parent / "scripts" / "hallucination_multi_turn.py"
REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream/scripts/hallucination_multi_turn.py"

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
sftp.put(str(LOCAL), REMOTE)
sftp.close()
stdin, stdout, stderr = c.exec_command(
    f"grep -n 'verify_llm' {REMOTE} | head",
    timeout=20,
)
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
print("synced", LOCAL)
