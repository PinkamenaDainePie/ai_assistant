# -*- coding: utf-8 -*-
"""Upload S2 bundle to AutoDL bjb3 and launch setup (do not commit passwords to public remotes)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

HOST = "connect.bjb3.seetacloud.com"
PORT = 18177
USER = "root"
PASSWORD = "CLMHfQOsgKFs"

HERE = Path(__file__).resolve().parent
LOCAL_TGZ = HERE / "_cloudstudio_salvage_bundle.tgz"
LOCAL_SETUP = HERE / "_autodl_bjb3_setup_s2.sh"
LOCAL_RUN = HERE / "_autodl_bjb3_run_s2.sh"
REMOTE_DIR = "/root/autodl-tmp/work"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (LOCAL_TGZ, LOCAL_SETUP, LOCAL_RUN):
        if not p.is_file():
            print("missing", p)
            return 1

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASSWORD,
        timeout=40,
        allow_agent=False,
        look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 120) -> tuple[int, str]:
        print(">>", cmd[:140], flush=True)
        _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        text = out if out.strip() else err
        if text.strip():
            print(text[-4000:], flush=True)
        return rc, out

    run(f"mkdir -p {REMOTE_DIR}")
    sftp = c.open_sftp()
    print("upload tgz", LOCAL_TGZ.stat().st_size, flush=True)
    sftp.put(str(LOCAL_TGZ), f"{REMOTE_DIR}/_salvage_s2_bundle.tgz")
    sftp.put(str(LOCAL_SETUP), f"{REMOTE_DIR}/_setup_s2.sh")
    sftp.put(str(LOCAL_RUN), f"{REMOTE_DIR}/_run_s2.sh")
    sftp.chmod(f"{REMOTE_DIR}/_setup_s2.sh", 0o755)
    sftp.chmod(f"{REMOTE_DIR}/_run_s2.sh", 0o755)
    sftp.close()
    print("upload ok", flush=True)

    run(
        f"nohup bash {REMOTE_DIR}/_setup_s2.sh > {REMOTE_DIR}/_setup_s2.log 2>&1 & echo PID=$!; sleep 2; wc -l {REMOTE_DIR}/_setup_s2.log; head -n 20 {REMOTE_DIR}/_setup_s2.log",
        timeout=30,
    )
    c.close()
    print("setup launched; poll _setup_s2.log for SETUP_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
