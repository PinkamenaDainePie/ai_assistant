# -*- coding: utf-8 -*-
"""List shared HF hub models + probe DashScope via remote .env."""
from __future__ import annotations

import sys

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

REMOTE_CMD = r"""
set +e
echo '=== SHARED HF HUB (top) ==='
ls /home/async/data-disk/huggingface/hub 2>/dev/null | head -60
echo '--- size ---'
du -sh /home/async/data-disk/huggingface/hub 2>/dev/null
echo '=== MODEL NAME DIRS ==='
ls -d /home/async/data-disk/huggingface/hub/models--* 2>/dev/null | sed 's|.*/||' | head -80

echo '=== DASHSCOPE VIA GATEWAY :18081 ==='
# Use key from ming-salvage .env without printing it
KEY=$(grep -E '^OPENAI_API_KEY=' /home/async/data-disk/ljc/ming-salvage-sim-upstream/.env | head -1 | cut -d= -f2-)
MODEL=$(grep -E '^OPENAI_MODEL=' /home/async/data-disk/ljc/ming-salvage-sim-upstream/.env | head -1 | cut -d= -f2-)
echo "MODEL=$MODEL KEY_LEN=${#KEY}"
# Prefer local gateway if up, else direct
for BASE in 'http://127.0.0.1:18081/compatible-mode/v1' 'https://dashscope.aliyuncs.com/compatible-mode/v1'; do
  echo "TRY $BASE"
  code=$(curl -sS -o /tmp/ds_models.json -w '%{http_code}' --max-time 20 \
    -H "Authorization: Bearer $KEY" "$BASE/models" 2>/dev/null || echo fail)
  echo "  /models HTTP $code"
  head -c 300 /tmp/ds_models.json; echo
  code2=$(curl -sS -o /tmp/ds_chat.json -w '%{http_code}' --max-time 40 \
    -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":8}" \
    "$BASE/chat/completions" 2>/dev/null || echo fail)
  echo "  /chat/completions HTTP $code2"
  # redact any key-looking substrings
  python3 - <<'PY'
import json,re
p='/tmp/ds_chat.json'
try:
  t=open(p,'r',encoding='utf-8',errors='replace').read()
except Exception as e:
  print('  read err',e); raise SystemExit
t=re.sub(r'sk-[A-Za-z0-9]+','sk-***',t)
t=re.sub(r'Bearer [A-Za-z0-9._-]+','Bearer ***',t)
print(' ', t[:500])
PY
done

echo '=== FREE GPUS ==='
nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv,noheader
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[connect] {USER}@{HOST}:{PORT}", flush=True)
    client.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASSWORD,
        timeout=40,
        allow_agent=False,
        look_for_keys=False,
    )
    _, stdout, stderr = client.exec_command(REMOTE_CMD, timeout=180)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print(out)
    if err.strip():
        print("STDERR", err[-1500:])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
