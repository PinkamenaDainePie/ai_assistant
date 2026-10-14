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
REMOTE=/home/async/data-disk/ljc/ming-salvage-sim-upstream
echo '=== perms ==='
ls -lad $REMOTE $REMOTE/data $REMOTE/scripts/runs $REMOTE/scripts/runs/ablation_m
touch $REMOTE/data/_wtest && echo DATA_WRITABLE || echo DATA_RO
touch $REMOTE/scripts/runs/_wtest && echo RUNS_WRITABLE || echo RUNS_RO
df -h $REMOTE | tail -1
mount | grep data-disk | head
echo '=== find readonly dbs ==='
find $REMOTE -name '*.db' 2>/dev/null | head
ls -la $REMOTE/data 2>/dev/null | head
ls -la $REMOTE/scripts/runs/*.db 2>/dev/null | head
# who owns / is sticky
namei -l $REMOTE/data | head
id
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
