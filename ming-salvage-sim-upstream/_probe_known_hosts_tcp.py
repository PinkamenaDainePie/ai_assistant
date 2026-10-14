# -*- coding: utf-8 -*-
"""TCP reachability for hosts previously used (from known_hosts / ssh config)."""
from __future__ import annotations

import socket
import sys

TARGETS = [
    ("gpuhub-westc", "connect.westc.gpuhub.com", 43653),
    ("seetacloud-cqa1-cfg", "connect.cqa1.seetacloud.com", 35144),
    ("seetacloud-cqa1-old", "connect.cqa1.seetacloud.com", 10658),
    ("seetacloud-westc", "connect.westc.seetacloud.com", 35144),
    ("lab_3090", "dpcau.686788.xyz", 44415),
    ("host-111.231", "111.231.31.56", 22),
    ("host-122.51", "122.51.245.227", 22),
    ("host-124.221", "124.221.252.181", 22),
    ("host-8.137", "8.137.91.164", 22),
    ("lan-192.168.1.190", "192.168.1.190", 22),
    ("lan-192.168.254.130", "192.168.254.130", 22),
    ("006", "202.115.17.216", 11222),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for name, host, port in TARGETS:
        try:
            with socket.create_connection((host, port), timeout=5) as s:
                print(f"OPEN  {name:22} {host}:{port}")
        except Exception as e:
            print(f"CLOSED {name:22} {host}:{port}  ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
