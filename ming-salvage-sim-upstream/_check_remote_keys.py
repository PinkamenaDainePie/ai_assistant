# -*- coding: utf-8 -*-
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
python3 - <<'PY'
from pathlib import Path
cands = [
    Path('/home/async/data-disk/ljc/MCST/.env.program2'),
    Path('/home/async/data-disk/ljc/.env.program2'),
    Path('/home/async/data-disk/ljc/ming-salvage-sim-upstream/.env'),
]
for p in cands:
    print('FILE', p, 'exists', p.is_file())
    if not p.is_file():
        continue
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.strip() or line.strip().startswith('#') or '=' not in line:
            continue
        k,v = line.split('=',1)
        k=k.strip(); v=v.strip()
        if any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD')):
            print(f'  {k}=***{v[-4:] if len(v)>=4 else "????"}')
        elif 'MODEL' in k.upper() or 'BASE' in k.upper() or 'URL' in k.upper():
            print(f'  {k}={v}')
PY
"""
_, o, e = c.exec_command(cmd, timeout=30)
print(o.read().decode("utf-8", "replace"))
err = e.read().decode("utf-8", "replace")
if err.strip():
    print("STDERR", err[-500:])
c.close()
