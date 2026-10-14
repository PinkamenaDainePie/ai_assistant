# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time

import paramiko

HOST = "connect.westc.seetacloud.com"
PORT = 57699
USER = "root"
PASSWORD = "pe8AzI2qrrps"

REMOTE_POLL = r"""
set +e
/root/miniconda3/bin/python - <<'PY'
import os,glob
base='/root/autodl-tmp/modelscope_cache/models/Qwen--Qwen2.5-7B-Instruct/snapshots/master'
inc=glob.glob(base+'/*.incomplete')
done=glob.glob(base+'/*.safetensors')
sz=sum(os.path.getsize(p) for p in inc+done)
print(f'incomplete={len(inc)} done={len(done)} bytes={sz/1e9:.2f}G')
PY
grep -E '^\[5\]|^\[6\]|^\[7\]|^DONE|^FATAL|linked |downloaded_to|try .* HTTP|vllm 0' /root/autodl-tmp/setup_vllm.log | tail -30
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8000/v1/models 2>/dev/null || echo fail)
echo "http=$code"
ps -p $(pgrep -f setup_vllm.sh | head -1) -o etime= 2>/dev/null | awk '{print "setup_etime",$1}'
df -h /root/autodl-tmp | tail -1
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=40, allow_agent=False, look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 40) -> str:
        _, stdout, _ = client.exec_command(cmd, timeout=timeout)
        return stdout.read().decode("utf-8", "replace")

    deadline = time.time() + 1800
    last = ""
    while time.time() < deadline:
        out = run(REMOTE_POLL)
        if out != last:
            print(out, flush=True)
            last = out
        if "DONE OPENAI_BASE_URL=" in out or "FATAL not ready" in out:
            break
        if "http=200" in out:
            time.sleep(20)
            out2 = run(
                "grep -E '^DONE|^FATAL|^\\[7\\]|pong|started_pid|try .* HTTP' "
                "/root/autodl-tmp/setup_vllm.log | tail -40; "
                "tail -c 2500 /root/autodl-tmp/setup_vllm.log | tr '\\r' '\\n' | tail -30"
            )
            print(out2, flush=True)
            if "DONE OPENAI_BASE_URL=" in out2 or "FATAL" in out2:
                break
        time.sleep(20)

    print("=== FINAL ===", flush=True)
    print(
        run(
            "grep -E '^\\[|^DONE|^FATAL|linked |downloaded_to|started_pid|try .* HTTP' "
            "/root/autodl-tmp/setup_vllm.log | tail -50; echo ---; "
            "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader; "
            "curl -sS --max-time 8 http://127.0.0.1:8000/v1/models | head -c 500; echo; "
            "curl -sS --max-time 60 http://127.0.0.1:8000/v1/chat/completions "
            "-H 'Content-Type: application/json' "
            "-d '{\"model\":\"qwen2.5-7b-instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"只回复：pong\"}],\"max_tokens\":16,\"temperature\":0}' "
            "| head -c 800; echo"
        ),
        flush=True,
    )
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
