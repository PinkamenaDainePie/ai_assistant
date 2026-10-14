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
PID=$(pgrep -f '_worker_s01_relief_kaifeng_5.py' | head -1)
echo PID=$PID
if [ -z "$PID" ]; then echo NO_WORKER; exit 0; fi
echo STATE=$(awk '{print $3}' /proc/$PID/stat)
echo WCHAN=$(cat /proc/$PID/wchan)
ls -l /proc/$PID/fd | head -40
echo '--- stack ---'
# python traceback via faulthandler if available; else py-spy; else /proc/pid/stack
timeout 3 strace -p $PID -f -e trace=network,file,write,read 2>&1 | tail -40 || true
echo '--- parent ---'
ps -o pid,ppid,stat,etime,cmd -p $PID
pgrep -af run_hallucination_ablation || true
find /home/async/data-disk/ljc/ming-salvage-sim-upstream -name '*.db' 2>/dev/null | head
"""
stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
print(stdout.read().decode("utf-8", "replace"))
print(stderr.read().decode("utf-8", "replace")[-2000:])
c.close()
