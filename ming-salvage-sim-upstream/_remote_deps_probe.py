# -*- coding: utf-8 -*-
import paramiko

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
cmd = r"""
set -e
echo '=== py ==='
python3 --version
which python3
echo '=== try existing venvs ==='
for v in \
  /home/async/data-disk/ljc/gsm8k_autogen/.venv \
  /home/async/data-disk/ljc/RagHop/.venv
do
  echo "-- $v"
  if [ -x "$v/bin/python" ]; then
    "$v/bin/python" - <<'PY'
import sys
print(sys.version)
mods=['openai','agno','httpx','pydantic','fastapi','dotenv']
for m in mods:
    try:
        __import__(m)
        print(m,'OK')
    except Exception as e:
        print(m,'NO',type(e).__name__)
PY
  fi
done
echo '=== network ==='
curl -I -m 5 https://pypi.org 2>&1 | head -5 || true
ping -c 1 -W 2 8.8.8.8 2>&1 | head -3 || true
echo '=== user site / other ==='
ls /home/async/data-disk/ljc/ | head -40
find /home/async/data-disk/ljc -maxdepth 4 -type d -name 'site-packages' 2>/dev/null | head -20
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()
