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
echo '=== proxy files ==='
head -n 40 /home/async/data-disk/ljc/proxy_fwd_7890.py 2>/dev/null || true
ss -lntp 2>/dev/null | grep -E '7890|1080|3128|8080' || netstat -lntp 2>/dev/null | grep -E '7890|1080|3128|8080' || true
ps aux | grep -iE 'proxy|clash|v2ray|mitm' | grep -v grep | head
echo '=== env proxy ==='
env | grep -iE 'proxy|http_proxy|https_proxy|all_proxy' || true
echo '=== try proxy pip ==='
for p in http://127.0.0.1:7890 http://127.0.0.1:10809 http://127.0.0.1:7897 http://192.168.1.1:7890; do
  echo TRY_PROXY $p
  curl -I -m 5 -x "$p" https://pypi.org 2>&1 | head -4
done
echo '=== RagHop site-packages sample ==='
SP=/home/async/data-disk/ljc/RagHop/.venv/lib/python3.13/site-packages
ls "$SP" | grep -iE 'openai|httpx|pydantic|fastapi|agno|sqlite|dotenv' | head -40
echo '=== TruthX ==='
find /home/async/data-disk/ljc/TruthX -maxdepth 3 -name 'site-packages' 2>/dev/null
ls /home/async/data-disk/ljc/TruthX 2>/dev/null | head
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=90)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()
