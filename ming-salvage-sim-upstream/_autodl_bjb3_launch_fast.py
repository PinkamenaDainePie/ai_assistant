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
LOCAL = HERE / "_autodl_bjb3_setup_s2_fast.sh"
REMOTE = "/root/autodl-tmp/work/_setup_s2_fast.sh"


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
    sftp.close()

    cmd = (
        "pkill -f 'pip install vllm' || true; "
        "pkill -f '_setup_s2.sh' || true; "
        "pkill -f '_setup_s2_fast.sh' || true; "
        "sleep 2; "
        f"nohup bash {REMOTE} > /root/autodl-tmp/work/_setup_s2_fast.log 2>&1 & "
        "echo PID=$!; sleep 6; "
        "ps -ef | grep -v grep | grep -E 'setup_s2_fast|pip' | head -10; "
        "echo ---; head -n 50 /root/autodl-tmp/work/_setup_s2_fast.log"
    )
    _, o, e = c.exec_command(cmd, timeout=60)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[-800:])
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
