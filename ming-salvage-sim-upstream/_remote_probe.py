# -*- coding: utf-8 -*-
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "202.115.17.216",
    port=11222,
    username="async",
    password="asdf@1234",
    timeout=15,
    allow_agent=False,
    look_for_keys=False,
)
cmd = r"""
set -e
echo '== pydeps =='
ls /home/async/data-disk/ljc/pydeps | head
echo '== find python =='
find /home/async -maxdepth 5 -name python -type f 2>/dev/null | head -20
echo '== conda envs =='
ls /home/async/.conda/envs 2>/dev/null || true
ls /home/async/miniconda3/envs 2>/dev/null || true
echo '== system python packages =='
python3 -c 'import sys; print(sys.version)'
python3 -c 'import openai; print("openai", openai.__version__)' 2>&1 | head -2
PYTHONPATH=/home/async/data-disk/ljc/pydeps python3 -c 'import agno; print("agno ok")' 2>&1 | head -2
ls /home/async/data-disk/ljc/TruthX | head
"""
stdin, stdout, stderr = c.exec_command(cmd)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace"))
c.close()
