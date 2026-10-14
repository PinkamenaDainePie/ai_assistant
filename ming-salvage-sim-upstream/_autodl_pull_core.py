# -*- coding: utf-8 -*-
"""Pull AutoDL core ablation artifacts to local runs/."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"
REMOTE_OUT = "/root/autodl-tmp/work/salvage_faithfulness/runs/ablation_core_autodl"
LOCAL_OUT = Path(r"e:\ai_assistant\experiments\salvage_faithfulness\runs\ablation_core_autodl")

FILES = [
    "SUMMARY.md",
    "summary.json",
    "aggregate.json",
    "run.log",
    "run.pid",
    "started_wall.txt",
    "ablation_A.jsonl",
    "ablation_B.jsonl",
    "ablation_C.jsonl",
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )
    sftp = client.open_sftp()
    for name in FILES:
        rpath = f"{REMOTE_OUT}/{name}"
        lpath = LOCAL_OUT / name
        try:
            sftp.stat(rpath)
        except FileNotFoundError:
            print(f"[skip] {name}", flush=True)
            continue
        print(f"[get] {name}", flush=True)
        sftp.get(rpath, str(lpath))
        print(f"  -> {lpath} ({lpath.stat().st_size} bytes)", flush=True)
    sftp.close()
    client.close()
    print(f"[ok] {LOCAL_OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
