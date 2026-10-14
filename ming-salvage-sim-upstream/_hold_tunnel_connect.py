# -*- coding: utf-8 -*-
"""SSH reverse-forward a local HTTP CONNECT proxy so 006 can reach DashScope with end-to-end TLS."""
from __future__ import annotations

import select
import socket
import threading
import time

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"
REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV_PY = f"{REMOTE}/.venv/bin/python"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
PIDF = f"{REMOTE}/scripts/runs/ablation_m/run.pid"
LAUNCHER = f"{REMOTE}/scripts/runs/ablation_m/start.sh"
REMOTE_LISTEN = 18081
REAL_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _pipe(a: socket.socket, b: socket.socket) -> None:
    try:
        while True:
            r, _, _ = select.select([a], [], [], 300)
            if not r:
                break
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except Exception:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                s.close()
            except Exception:
                pass


def handle_connect_client(cli: socket.socket) -> None:
    cli.settimeout(60)
    try:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = cli.recv(4096)
            if not chunk:
                cli.close()
                return
            raw += chunk
            if len(raw) > 65536:
                cli.close()
                return
        head, _, rest = raw.partition(b"\r\n\r\n")
        line = head.split(b"\r\n", 1)[0].decode("latin1", "replace")
        parts = line.split()
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            # plain HTTP probe — reject quickly
            body = b"CONNECT proxy only\n"
            cli.sendall(
                b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: "
                + str(len(body)).encode()
                + b"\r\nConnection: close\r\n\r\n"
                + body
            )
            cli.close()
            return
        target = parts[1]
        if ":" in target:
            host, port_s = target.rsplit(":", 1)
            port = int(port_s)
        else:
            host, port = target, 443
        up = socket.create_connection((host, port), timeout=20)
        cli.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        if rest:
            up.sendall(rest)
        print(f"[connect] {host}:{port}", flush=True)
        threading.Thread(target=_pipe, args=(cli, up), daemon=True).start()
        _pipe(up, cli)
    except Exception as e:
        print(f"[connect-err] {type(e).__name__}: {e}", flush=True)
        try:
            cli.close()
        except Exception:
            pass


def start_connect_proxy() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]

    def accept_loop() -> None:
        while True:
            try:
                cli, _ = sock.accept()
            except Exception:
                break
            threading.Thread(target=handle_connect_client, args=(cli,), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    print(f"[proxy] CONNECT on 127.0.0.1:{port}", flush=True)
    return sock, port


def _ssh_handler(chan: paramiko.Channel, local_port: int) -> None:
    try:
        sock = socket.create_connection(("127.0.0.1", local_port), timeout=10)
    except Exception:
        chan.close()
        return

    def pump(a, b):
        try:
            while True:
                r, _, _ = select.select([a], [], [], 300)
                if not r:
                    break
                data = a.recv(65536)
                if not data:
                    break
                b.sendall(data)
        except Exception:
            pass
        finally:
            for s in (a, b):
                try:
                    s.close()
                except Exception:
                    pass

    threading.Thread(target=pump, args=(chan, sock), daemon=True).start()
    pump(sock, chan)


def ssh_run(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> str:
    print(f"[ssh] {cmd[:220]}", flush=True)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2500:], flush=True)
    if err.strip():
        print("[stderr]", err[-1000:], flush=True)
    return out


def patch_env(client: paramiko.SSHClient) -> None:
    py = f"""
from pathlib import Path
p = Path("{REMOTE}/.env")
lines = p.read_text(encoding="utf-8").splitlines()
keys = {{
    "OPENAI_BASE_URL": "{REAL_BASE}",
    "HTTPS_PROXY": "http://127.0.0.1:{REMOTE_LISTEN}",
    "HTTP_PROXY": "http://127.0.0.1:{REMOTE_LISTEN}",
    "ALL_PROXY": "http://127.0.0.1:{REMOTE_LISTEN}",
    "NO_PROXY": "127.0.0.1,localhost",
}}
seen = set()
out = []
for line in lines:
    if not line.strip() or line.strip().startswith("#") or "=" not in line:
        out.append(line)
        continue
    k = line.split("=", 1)[0].strip()
    if k in keys:
        out.append(f"{{k}}={{keys[k]}}")
        seen.add(k)
    else:
        out.append(line)
for k, v in keys.items():
    if k not in seen:
        out.append(f"{{k}}={{v}}")
p.write_text("\\n".join(out) + "\\n", encoding="utf-8")
print("ENV_OK", keys["OPENAI_BASE_URL"], keys["HTTPS_PROXY"])
"""
    ssh_run(client, f"{VENV_PY} - <<'PY'\n{py}\nPY")


def probe(client: paramiko.SSHClient) -> None:
    py = f"""
import os
from pathlib import Path
import httpx
env = {{}}
for raw in Path("{REMOTE}/.env").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
for k in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY", "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"):
    if k in env:
        os.environ[k] = env[k]
base = env["OPENAI_BASE_URL"].rstrip("/")
key = env["OPENAI_API_KEY"]
model = env.get("OPENAI_MODEL", "qwen-plus")
proxy = env.get("HTTPS_PROXY")
print("using_proxy", proxy)
with httpx.Client(proxy=proxy, timeout=60.0) as client:
    r = client.get(base + "/models", headers={{"Authorization": "Bearer " + key}})
    print("MODELS", r.status_code, r.text[:120].replace("\\n", " "))
    r2 = client.post(
        base + "/chat/completions",
        headers={{"Authorization": "Bearer " + key, "Content-Type": "application/json"}},
        json={{"model": model, "messages": [{{"role": "user", "content": "ping"}}], "max_tokens": 8}},
    )
    print("CHAT", r2.status_code, r2.text[:180].replace("\\n", " "))
    # streaming
    with client.stream(
        "POST",
        base + "/chat/completions",
        headers={{"Authorization": "Bearer " + key, "Content-Type": "application/json"}},
        json={{
            "model": model,
            "messages": [{{"role": "user", "content": "say hi"}}],
            "max_tokens": 16,
            "stream": True,
        }},
    ) as r3:
        n = 0
        for line in r3.iter_lines():
            if line:
                n += 1
                if n <= 3:
                    print("STREAM", line[:120])
        print("STREAM_LINES", n, "status", r3.status_code)
"""
    ssh_run(client, f"{VENV_PY} - <<'PY'\n{py}\nPY", timeout=120)


def restart_ablation(client: paramiko.SSHClient) -> None:
    ssh_run(
        client,
        "python3 - <<'PY'\n"
        "import os, signal, subprocess, time\n"
        "out=subprocess.check_output(['pgrep','-af','ming-salvage-sim-upstream'], text=True)\n"
        "for line in out.splitlines():\n"
        "    parts=line.split(None,1)\n"
        "    if len(parts)<2: continue\n"
        "    pid=int(parts[0]); cmd=parts[1]\n"
        "    if 'pgrep' in cmd or 'python3 -' in cmd: continue\n"
        "    if 'run_hallucination_ablation' in cmd or '_worker_' in cmd or 'ablation_m/start.sh' in cmd:\n"
        "        print('KILL', pid)\n"
        "        try: os.kill(pid, signal.SIGKILL)\n"
        "        except ProcessLookupError: pass\n"
        "time.sleep(2)\n"
        "print('DONE_KILL')\n"
        "PY",
    )
    ssh_run(
        client,
        f"rm -rf {REMOTE}/data; mkdir -p {REMOTE}/data {REMOTE}/scripts/runs/ablation_m; "
        f"rm -f {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl "
        f"{REMOTE}/scripts/runs/ablation_m/summary.json "
        f"{REMOTE}/scripts/runs/ablation_m/SUMMARY.md "
        f"{REMOTE}/scripts/runs/_turn_*.json "
        f"{REMOTE}/scripts/runs/_worker_*.py; "
        f": > {LOG}; echo WIPED",
    )
    script = (
        "#!/bin/bash\n"
        f"cd {REMOTE} || exit 1\n"
        "set -a\n"
        f". {REMOTE}/.env\n"
        "set +a\n"
        f"export HTTPS_PROXY HTTP_PROXY ALL_PROXY NO_PROXY OPENAI_BASE_URL OPENAI_API_KEY OPENAI_MODEL\n"
        f"exec {VENV_PY} -X utf8 scripts/run_hallucination_ablation.py "
        f"--suite m --conds A,B,C --turn-timeout 360 "
        f"--out-dir scripts/runs/ablation_m\n"
    )
    sftp = client.open_sftp()
    with sftp.file(LAUNCHER, "w") as f:
        f.write(script)
    sftp.close()
    ssh_run(client, f"chmod +x {LAUNCHER}")
    ssh_run(
        client,
        f"nohup {LAUNCHER} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; "
        f"echo STARTED $(cat {PIDF})",
        timeout=15,
    )
    time.sleep(5)
    ssh_run(client, f"pgrep -af 'run_hallucination_ablation|_worker_s' || echo NONE; tail -n 40 {LOG}")


def main() -> None:
    # stop old HTTP-relay tunnel holder if still around — user/machine may have it; we take the port
    proxy_sock, local_port = start_connect_proxy()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=30, allow_agent=False, look_for_keys=False,
    )
    transport = client.get_transport()
    assert transport is not None
    transport.set_keepalive(30)
    try:
        transport.cancel_port_forward("127.0.0.1", REMOTE_LISTEN)
    except Exception:
        pass

    def accept_loop() -> None:
        while transport.is_active():
            try:
                chan = transport.accept(timeout=1.0)
            except Exception:
                continue
            if chan is None:
                continue
            threading.Thread(target=_ssh_handler, args=(chan, local_port), daemon=True).start()

    transport.request_port_forward("127.0.0.1", REMOTE_LISTEN)
    threading.Thread(target=accept_loop, daemon=True).start()
    print(f"[tunnel] remote 127.0.0.1:{REMOTE_LISTEN} -> CONNECT :{local_port}", flush=True)

    patch_env(client)
    probe(client)
    restart_ablation(client)
    print("[hold] CONNECT tunnel alive", flush=True)

    while transport.is_active():
        try:
            out = ssh_run(
                client,
                f"pgrep -c -f 'scripts/run_hallucination_ablation.py' || true; "
                f"wc -l {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null; "
                f"tail -n 6 {LOG}; "
                f"test -f {REMOTE}/scripts/runs/ablation_m/summary.json && echo DONE || echo RUN",
                timeout=30,
            )
            if "DONE" in out.splitlines()[-1:]:
                print("[done] summary present", flush=True)
                break
            if "\nDONE" in out or out.strip().endswith("DONE"):
                print("[done] summary present", flush=True)
                break
        except Exception as e:
            print("[hb-err]", type(e).__name__, e, flush=True)
        time.sleep(90)

    try:
        transport.cancel_port_forward("127.0.0.1", REMOTE_LISTEN)
    except Exception:
        pass
    client.close()
    proxy_sock.close()


if __name__ == "__main__":
    main()
