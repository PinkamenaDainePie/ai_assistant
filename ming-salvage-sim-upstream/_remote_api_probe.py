# -*- coding: utf-8 -*-
import paramiko

REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV = f"{REMOTE}/.venv/bin/python"

remote_py = r"""
from pathlib import Path
import socket
from urllib.parse import urlparse
import httpx

p = Path("/home/async/data-disk/ljc/ming-salvage-sim-upstream/.env")
env = {}
for raw in p.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
base = env.get("OPENAI_BASE_URL", "")
model = env.get("OPENAI_MODEL", "")
key = env.get("OPENAI_API_KEY", "")
u = urlparse(base)
print("MODEL", model)
print("BASE_HOST", u.netloc)
print("BASE_SCHEME", u.scheme)
print("KEY_LEN", len(key))
host = u.hostname
port = u.port or (443 if u.scheme == "https" else 80)
print("RESOLVE", host)
try:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    print("ADDR", infos[0][4] if infos else None)
except Exception as e:
    print("RESOLVE_FAIL", type(e).__name__, e)
try:
    s = socket.create_connection((host, port), timeout=8)
    print("TCP_OK", host, port)
    s.close()
except Exception as e:
    print("TCP_FAIL", type(e).__name__, e)
try:
    url = base.rstrip("/") + "/models"
    headers = {"Authorization": "Bearer " + key} if key else {}
    r = httpx.get(url, headers=headers, timeout=15.0)
    print("HTTP_MODELS", r.status_code, r.text[:160].replace("\n", " "))
except Exception as e:
    print("HTTP_FAIL", type(e).__name__, e)
"""

shell = f"""
{VENV} - <<'PY'
{remote_py}
PY
echo '=== listeners ==='
ss -lntp 2>/dev/null | grep -E '8000|8080|17890|17891|28080|7890' || true
echo '=== gateway ==='
pgrep -af llm_gateway || echo NO_GW
head -n 40 /home/async/data-disk/ljc/llm_gateway.py 2>/dev/null || true
tail -n 8 /home/async/data-disk/ljc/llm_gateway.log 2>/dev/null || true
"""

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
stdin, stdout, stderr = c.exec_command(shell, timeout=90)
print(stdout.read().decode("utf-8", "replace"))
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print("[stderr]", err[-2000:])
c.close()
