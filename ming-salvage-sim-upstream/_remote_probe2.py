# -*- coding: utf-8 -*-
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "202.115.17.216",
    port=11222,
    username="async",
    password="asdf@1234",
    timeout=20,
    allow_agent=False,
    look_for_keys=False,
)
cmd = """
find /home/async/data-disk/ljc -maxdepth 3 -name pyvenv.cfg 2>/dev/null
find /home/async/data-disk/ljc -maxdepth 4 -type d -name site-packages 2>/dev/null | head
ls /home/async/data-disk/ljc/pydeps 2>/dev/null | grep -iE 'openai|agno|httpx|pydantic|dotenv' || true
python3 -m venv -h >/dev/null 2>&1 && echo VENV_OK || echo VENV_NO
pip3 --version 2>&1 | head -1
"""
stdin, stdout, stderr = c.exec_command(cmd)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()
