# -*- coding: utf-8 -*-
"""Keep reverse tunnel alive for already-running ablation on 006."""
from __future__ import annotations

import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"
REMOTE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
REMOTE_LISTEN = 18080
UPSTREAM = "https://dashscope.aliyuncs.com"
LOG = f"{REMOTE}/scripts/runs/ablation_m/run.log"


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[relay] {self.address_string()} {fmt % args}", flush=True)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        url = UPSTREAM.rstrip("/") + self.path
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
                if k.lower() in {"transfer-encoding", "connection", "content-encoding", "content-length"}:
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
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                return

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()


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


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), RelayHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    local_port = srv.server_address[1]
    print(f"[relay] local :{local_port} -> {UPSTREAM}", flush=True)

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

    def accept_loop():
        while transport.is_active():
            try:
                chan = transport.accept(timeout=1.0)
            except Exception:
                continue
            if chan is None:
                continue
            threading.Thread(target=_handler, args=(chan, local_port), daemon=True).start()

    transport.request_port_forward("127.0.0.1", REMOTE_LISTEN)
    threading.Thread(target=accept_loop, daemon=True).start()
    print(f"[tunnel] remote 127.0.0.1:{REMOTE_LISTEN} -> local {local_port}", flush=True)

    # quick probe
    stdin, stdout, stderr = client.exec_command(
        f"{REMOTE}/.venv/bin/python -c \"import httpx; r=httpx.get('http://127.0.0.1:{REMOTE_LISTEN}/compatible-mode/v1/models',timeout=20); print(r.status_code, r.text[:80])\"",
        timeout=40,
    )
    print("[probe]", stdout.read().decode("utf-8", "replace"), stderr.read().decode("utf-8", "replace")[-400:], flush=True)
    print("[hold] tunnel alive", flush=True)

    while transport.is_active():
        try:
            stdin, stdout, stderr = client.exec_command(
                f"pgrep -c -f 'scripts/run_hallucination_ablation.py' || true; "
                f"ls {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null | wc -l; "
                f"wc -l {REMOTE}/scripts/runs/ablation_m/ablation_*.jsonl 2>/dev/null; "
                f"tail -n 4 {LOG}",
                timeout=30,
            )
            print("[hb]", stdout.read().decode("utf-8", "replace")[-1500:], flush=True)
            # done?
            out_check = ""
            stdin, stdout, stderr = client.exec_command(
                f"test -f {REMOTE}/scripts/runs/ablation_m/summary.json && echo DONE || echo RUN",
                timeout=20,
            )
            out_check = stdout.read().decode("utf-8", "replace").strip()
            if "DONE" in out_check:
                print("[done] summary.json present", flush=True)
                break
        except Exception as e:
            print("[hb-err]", type(e).__name__, e, flush=True)
        time.sleep(90)

    client.close()
    srv.shutdown()


if __name__ == "__main__":
    main()
