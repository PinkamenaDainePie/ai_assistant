# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "connect.bjb3.seetacloud.com"
PORT = 18177
USER = "root"
PASSWORD = "CLMHfQOsgKFs"
HERE = Path(__file__).resolve().parent
LOCAL = HERE / "_autodl_bjb3_accel_wheel.sh"
REMOTE = "/root/autodl-tmp/work/_accel_wheel.sh"
LOG = "/root/autodl-tmp/work/_accel_wheel.log"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = LOCAL.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    LOCAL.write_bytes(text.encode("utf-8"))

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
    sftp = c.open_sftp()
    sftp.put(str(LOCAL), REMOTE)
    sftp.chmod(REMOTE, 0o755)
    # also refresh run script LF
    run_local = HERE / "_autodl_bjb3_run_s2.sh"
    if run_local.is_file():
        rt = run_local.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        run_local.write_bytes(rt.encode("utf-8"))
        sftp.put(str(run_local), "/root/autodl-tmp/work/_run_s2.sh")
        sftp.chmod("/root/autodl-tmp/work/_run_s2.sh", 0o755)
    sftp.close()

    cmd = (
        f"nohup bash {REMOTE} > {LOG} 2>&1 & echo PID=$!; "
        f"sleep 15; ps -ef | grep -v grep | grep -E 'accel_wheel|aria2|wget|pip' | head -15; "
        f"echo ---LOG---; tail -n 50 {LOG}"
    )
    _, o, e = c.exec_command(cmd, timeout=90)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
