# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import urlparse

env = {}
for raw in Path(".env").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
u = urlparse(env.get("OPENAI_BASE_URL", ""))
print("host", u.hostname)
print("port", u.port or (443 if u.scheme == "https" else 80))
print("path", u.path)
print("model", env.get("OPENAI_MODEL"))
