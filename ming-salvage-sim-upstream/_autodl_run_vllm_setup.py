# -*- coding: utf-8 -*-
"""Upload and run AutoDL vLLM setup; poll log until done."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"
LOCAL_SH = Path(__file__).with_name("_autodl_vllm_remote.sh")
REMOTE_SH = "/root/autodl-tmp/setup_vllm.sh"
REMOTE_LOG = "/root/autodl-tmp/setup_vllm.log"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[connect] {USER}@{HOST}:{PORT}", flush=True)
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )
    # quick probe
    _, stdout, _ = client.exec_command(
        "hostname; nvidia-smi -L; df -h / /root/autodl-tmp; /root/miniconda3/bin/python -V",
        timeout=30,
    )
    print(stdout.read().decode("utf-8", "replace"), flush=True)

    sftp = client.open_sftp()
    print(f"[upload] -> {REMOTE_SH}", flush=True)
    data = LOCAL_SH.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    with sftp.file(REMOTE_SH, "wb") as rf:
        rf.write(data)
    sftp.chmod(REMOTE_SH, 0o755)
    sftp.close()

    _, stdout, _ = client.exec_command(
        f"rm -f {REMOTE_LOG}; nohup bash {REMOTE_SH} >{REMOTE_LOG} 2>&1 & echo $!",
        timeout=30,
    )
    pid = stdout.read().decode().strip().splitlines()[-1]
    print(f"[started] pid={pid}", flush=True)

    last_len = 0
    deadline = time.time() + 5400
    body = ""
    while time.time() < deadline:
        _, stdout, _ = client.exec_command(
            f"wc -c < {REMOTE_LOG}; tail -c 12000 {REMOTE_LOG}",
            timeout=30,
        )
        data = stdout.read().decode("utf-8", "replace")
        parts = data.split("\n", 1)
        try:
            cur_len = int(parts[0].strip())
        except Exception:
            cur_len = last_len
        body = parts[1] if len(parts) > 1 else data
        if cur_len != last_len:
            print(body[-5000:], flush=True)
            last_len = cur_len
            if "DONE OPENAI_BASE_URL=" in body:
                print("[ok] setup finished", flush=True)
                client.close()
                return 0
            if "FATAL not ready" in body:
                print("[fail] vllm not ready", flush=True)
                client.close()
                return 1

        _, stdout, _ = client.exec_command(f"kill -0 {pid} 2>/dev/null; echo $?", timeout=10)
        alive = stdout.read().decode().strip()
        if alive != "0":
            _, stdout, _ = client.exec_command(f"tail -n 80 {REMOTE_LOG}", timeout=20)
            print(stdout.read().decode("utf-8", "replace"), flush=True)
            print("[process exited]", flush=True)
            client.close()
            return 0 if "DONE OPENAI_BASE_URL=" in body else 1
        time.sleep(8)

    print("[timeout]", flush=True)
    client.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
