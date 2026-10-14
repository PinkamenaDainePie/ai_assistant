# -*- coding: utf-8 -*-
"""Reverse-tunnel DashScope via local machine, then restart ablation on 006."""
from __future__ import annotations

import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import httpx
import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"
REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
VENV_PY = f"{REMOTE}/.venv/bin/python"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"
PIDF = f"{REMOTE}/scripts/runs/ablation_m/run.pid"
REMOTE_LISTEN = 18080
UPSTREAM = "https://dashscope.aliyuncs.com"


def load_local_env() -> dict:
    env = {}
    for raw in Path(".env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[relay] {self.address_string()} {fmt % args}", flush=True)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        path = self.path
        url = UPSTREAM.rstrip("/") + path
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in {"host", "content-length", "transfer-encoding", "connection"}
        }
        try:
            with httpx.Client(timeout=180.0, follow_redirects=True) as client:
                r = client.request(self.command, url, headers=headers, content=body)
            payload = r.content
            self.send_response(r.status_code)
            for k, v in r.headers.items():
                lk = k.lower()
                if lk in {"transfer-encoding", "connection", "content-encoding", "content-length"}:
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return
        except Exception as e:
            msg = f"relay_error: {type(e).__name__}: {e}".encode("utf-8", "replace")
            try:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(msg)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy()


def start_local_relay() -> ThreadingHTTPServer:
    # bind ephemeral local port
    srv = ThreadingHTTPServer(("127.0.0.1", 0), RelayHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"[relay] local http://127.0.0.1:{srv.server_address[1]} -> {UPSTREAM}", flush=True)
    return srv


def _handler(chan: paramiko.Channel, local_port: int) -> None:
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


def setup_reverse_forward(transport: paramiko.Transport, local_port: int) -> None:
    # cancel existing if any
    try:
        transport.cancel_port_forward("127.0.0.1", REMOTE_LISTEN)
    except Exception:
        pass

    def accept_loop():
        while True:
            try:
                chan = transport.accept(timeout=1.0)
            except Exception:
                continue
            if chan is None:
                if not transport.is_active():
                    break
                continue
            threading.Thread(target=_handler, args=(chan, local_port), daemon=True).start()

    transport.request_port_forward("127.0.0.1", REMOTE_LISTEN)
    threading.Thread(target=accept_loop, daemon=True).start()
    print(f"[tunnel] remote 127.0.0.1:{REMOTE_LISTEN} -> local {local_port}", flush=True)


def ssh_run(client: paramiko.SSHClient, cmd: str, timeout: int = 60, check: bool = True) -> str:
    print(f"[ssh] {cmd[:220]}", flush=True)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2500:], flush=True)
    if err.strip():
        print("[stderr]", err[-1200:], flush=True)
    if check and code != 0:
        raise RuntimeError(f"exit {code}: {cmd}")
    return out


def patch_remote_env(client: paramiko.SSHClient) -> None:
    new_base = f"http://127.0.0.1:{REMOTE_LISTEN}/compatible-mode/v1"
    py = f"""
from pathlib import Path
p = Path("{REMOTE}/.env")
lines = p.read_text(encoding="utf-8").splitlines()
out = []
seen = False
for line in lines:
    if line.startswith("OPENAI_BASE_URL="):
        out.append("OPENAI_BASE_URL={new_base}")
        seen = True
    else:
        out.append(line)
if not seen:
    out.append("OPENAI_BASE_URL={new_base}")
p.write_text("\\n".join(out) + "\\n", encoding="utf-8")
print("PATCHED", "{new_base}")
"""
    ssh_run(client, f"{VENV_PY} - <<'PY'\n{py}\nPY")


def probe_via_tunnel(client: paramiko.SSHClient) -> None:
    py = f"""
import httpx
from pathlib import Path
env={{}}
for raw in Path("{REMOTE}/.env").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#") or "=" not in raw: continue
    k,v=raw.split("=",1); env[k.strip()]=v.strip().strip('"').strip("'")
base=env["OPENAI_BASE_URL"].rstrip("/")
key=env["OPENAI_API_KEY"]
model=env.get("OPENAI_MODEL","qwen-plus")
r=httpx.get(base+"/models", headers={{"Authorization":"Bearer "+key}}, timeout=30.0)
print("MODELS", r.status_code, r.text[:180].replace("\\n"," "))
# tiny chat
payload={{"model":model,"messages":[{{"role":"user","content":"ping"}}],"max_tokens":8}}
r2=httpx.post(base+"/chat/completions", headers={{"Authorization":"Bearer "+key,"Content-Type":"application/json"}}, json=payload, timeout=60.0)
print("CHAT", r2.status_code, r2.text[:220].replace("\\n"," "))
"""
    ssh_run(client, f"{VENV_PY} - <<'PY'\n{py}\nPY", timeout=120)


def restart_ablation(client: paramiko.SSHClient) -> None:
    ssh_run(
        client,
        "pkill -f 'scripts/run_hallucination_ablation.py' >/dev/null 2>&1; "
        "pkill -f 'scripts/runs/_worker_' >/dev/null 2>&1; "
        "sleep 1; "
        f"mkdir -p {REMOTE}/scripts/runs/ablation_m; "
        f"rm -f {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl "
        f"{REMOTE}/scripts/runs/ablation_m/summary.json "
        f"{REMOTE}/scripts/runs/_turn_*.json; "
        f": > {LOG}; echo CLEAN_OK",
        check=False,
    )
    # write a tiny launcher so the ssh exec channel can exit immediately
    launcher = f"{REMOTE}/scripts/runs/ablation_m/start.sh"
    script = (
        "#!/bin/bash\n"
        f"cd {REMOTE} || exit 1\n"
        f"exec {VENV_PY} -X utf8 scripts/run_hallucination_ablation.py "
        f"--suite m --conds A,B,C --turn-timeout 360 "
        f"--out-dir scripts/runs/ablation_m\n"
    )
    sftp = client.open_sftp()
    try:
        with sftp.file(launcher, "w") as f:
            f.write(script)
    finally:
        sftp.close()
    ssh_run(client, f"chmod +x {launcher}")
    # double-fork style detach: nohup + redirect everything away from ssh channel
    ssh_run(
        client,
        f"nohup {launcher} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; "
        f"sleep 0.2; echo STARTED $(cat {PIDF})",
        timeout=15,
    )
    time.sleep(2)
    ssh_run(
        client,
        f"pgrep -af run_hallucination_ablation || echo NONE; tail -n 40 {LOG}",
        timeout=30,
    )


def main() -> None:
    env = load_local_env()
    u = urlparse(env.get("OPENAI_BASE_URL", ""))
    if "dashscope" not in (u.hostname or ""):
        print(f"[warn] local OPENAI_BASE_URL host={u.hostname}", flush=True)

    relay = start_local_relay()
    local_port = relay.server_address[1]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=30, allow_agent=False, look_for_keys=False,
    )
    transport = client.get_transport()
    assert transport is not None
    transport.set_keepalive(30)
    setup_reverse_forward(transport, local_port)

    # wait for forward to be usable
    time.sleep(1)
    patch_remote_env(client)
    probe_via_tunnel(client)
    restart_ablation(client)

    print("[hold] tunnel kept alive; Ctrl+C to stop (ablation keeps running but API will die)", flush=True)
    try:
        while True:
            if not transport.is_active():
                print("[fatal] ssh transport dead", flush=True)
                break
            # heartbeat status every 2 min
            try:
                stdin, stdout, stderr = client.exec_command(
                    f"pgrep -c -f 'scripts/run_hallucination_ablation.py' || echo 0; "
                    f"wc -l {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null; "
                    f"tail -n 5 {LOG}",
                    timeout=30,
                )
                print("[hb]", stdout.read().decode("utf-8", "replace")[-1200:], flush=True)
            except Exception as e:
                print("[hb-err]", type(e).__name__, e, flush=True)
            time.sleep(120)
    except KeyboardInterrupt:
        print("[stop] keyboard", flush=True)
    finally:
        try:
            transport.cancel_port_forward("127.0.0.1", REMOTE_LISTEN)
        except Exception:
            pass
        client.close()
        relay.shutdown()


if __name__ == "__main__":
    main()
