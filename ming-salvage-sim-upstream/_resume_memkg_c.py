# -*- coding: utf-8 -*-
"""Resume mem/KG ablation for C0,C1,CK only. Keep A0/A1 jsonl. Hold CONNECT tunnel."""
from __future__ import annotations

import json
import select
import socket
import threading
import time
from pathlib import Path

import paramiko

HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"
REMOTE_ENGINE = "/home/async/data-disk/ljc/ming-salvage-sim-upstream"
REMOTE_BENCH = "/home/async/data-disk/ljc/salvage_faithfulness"
REMOTE = REMOTE_ENGINE  # backward alias
VENV_PY = f"{REMOTE_ENGINE}/.venv/bin/python"
OUT = f"{REMOTE_BENCH}/runs/ablation_memkg"
LOG = f"{OUT}/run_c.log"
PIDF = f"{OUT}/run_c.pid"
LAUNCHER = f"{OUT}/start_c.sh"
REMOTE_LISTEN = 18081
REAL_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ROOT = Path(__file__).resolve().parent
LOCAL_BENCH = Path(r"E:\ai_assistant\experiments\salvage_faithfulness")
LOCAL_OUT = LOCAL_BENCH / "runs" / "ablation_memkg"
LEGACY_OUT = ROOT / "scripts" / "runs" / "ablation_memkg"
PROGRAM2_ENV = Path(r"E:\program2\src\config\.env")


def _load_program2_qwen() -> dict[str, str]:
    """Read Program2 DashScope Qwen credentials (PAPERAI_LLM_QWEN_*)."""
    if not PROGRAM2_ENV.is_file():
        raise FileNotFoundError(f"missing {PROGRAM2_ENV}")
    keys: dict[str, str] = {}
    for raw in PROGRAM2_ENV.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.strip().startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k.startswith("PAPERAI_LLM_QWEN"):
            keys[k] = v
    api_key = keys.get("PAPERAI_LLM_QWEN_API_KEY", "")
    base = keys.get("PAPERAI_LLM_QWEN_BASE_URL", REAL_BASE)
    model = keys.get("PAPERAI_LLM_QWEN_MODEL_NAME", "qwen3.7-plus")
    if not api_key:
        raise RuntimeError("PAPERAI_LLM_QWEN_API_KEY missing in program2 .env")
    print(f"[program2] model={model} base={base} key=***{api_key[-4:]}", flush=True)
    return {"api_key": api_key, "base_url": base, "model": model}


def _pipe(a, b):
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
        head, _, rest = raw.partition(b"\r\n\r\n")
        line = head.split(b"\r\n", 1)[0].decode("latin1", "replace")
        parts = line.split()
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            cli.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
            cli.close()
            return
        target = parts[1]
        host, port_s = target.rsplit(":", 1) if ":" in target else (target, "443")
        up = socket.create_connection((host, int(port_s)), timeout=20)
        cli.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        if rest:
            up.sendall(rest)
        print(f"[connect] {host}:{port_s}", flush=True)
        threading.Thread(target=_pipe, args=(cli, up), daemon=True).start()
        _pipe(up, cli)
    except Exception as e:
        print(f"[connect-err] {type(e).__name__}: {e}", flush=True)
        try:
            cli.close()
        except Exception:
            pass


def ssh_run(client, cmd, timeout=60):
    print(f"[ssh] {cmd[:240]}", flush=True)
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out[-2500:], flush=True)
    if err.strip():
        print("[stderr]", err[-800:], flush=True)
    return out, code


def merge_summaries(c_summary: dict) -> dict:
    """Merge preserved A0/A1 from local summary backup with new C* results."""
    backup = LOCAL_OUT / "summary_a0a1_backup.json"
    if not backup.exists():
        # fall back to current summary.json if it still has A0/A1
        cur = LOCAL_OUT / "summary.json"
        if cur.exists():
            old = json.loads(cur.read_text(encoding="utf-8"))
        else:
            old = {"conds": {}}
    else:
        old = json.loads(backup.read_text(encoding="utf-8"))
    merged = {
        "conds": {},
        "started_at": c_summary.get("started_at"),
        "resumed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "A0/A1 from first successful run (qwen-plus); C0/C1/CK resumed with program2 Qwen key (qwen3.7-plus)",
    }
    for k in ("A0", "A1"):
        if k in old.get("conds", {}):
            merged["conds"][k] = old["conds"][k]
    for k, v in c_summary.get("conds", {}).items():
        merged["conds"][k] = v
    return merged


def main() -> None:
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    # migrate legacy A0/A1 artifacts if new dir empty
    if LEGACY_OUT.is_dir() and not (LOCAL_OUT / "ablation_A0.jsonl").exists():
        for name in (
            "ablation_A0.jsonl",
            "ablation_A1.jsonl",
            "summary.json",
            "SUMMARY.md",
            "summary_a0a1_backup.json",
        ):
            src = LEGACY_OUT / name
            if src.exists():
                dst = LOCAL_OUT / name
                dst.write_bytes(src.read_bytes())
                print(f"[migrate] {src.name} -> experiments/.../ablation_memkg/", flush=True)
    # backup A0/A1 summary if present
    local_sum = LOCAL_OUT / "summary.json"
    if not local_sum.exists() and (LEGACY_OUT / "summary.json").exists():
        local_sum = LEGACY_OUT / "summary.json"
    if local_sum.exists():
        old = json.loads(local_sum.read_text(encoding="utf-8"))
        bak = {"conds": {k: old["conds"][k] for k in ("A0", "A1") if k in old.get("conds", {})}, "started_at": old.get("started_at")}
        (LOCAL_OUT / "summary_a0a1_backup.json").write_text(
            json.dumps(bak, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("[backup] A0/A1 summary saved", flush=True)

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy.bind(("127.0.0.1", 0))
    proxy.listen(128)
    local_port = proxy.getsockname()[1]

    def accept_proxy():
        while True:
            try:
                cli, _ = proxy.accept()
            except Exception:
                break
            threading.Thread(target=handle_connect_client, args=(cli,), daemon=True).start()

    threading.Thread(target=accept_proxy, daemon=True).start()
    print(f"[proxy] CONNECT :{local_port}", flush=True)

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

    def accept_ssh():
        while transport.is_active():
            try:
                chan = transport.accept(timeout=1.0)
            except Exception:
                continue
            if chan is None:
                continue

            def _h(ch=chan):
                try:
                    sock = socket.create_connection(("127.0.0.1", local_port), timeout=10)
                except Exception:
                    ch.close()
                    return
                threading.Thread(target=_pipe, args=(ch, sock), daemon=True).start()
                _pipe(sock, ch)

            threading.Thread(target=_h, daemon=True).start()

    listen = REMOTE_LISTEN
    try:
        transport.request_port_forward("127.0.0.1", listen)
    except Exception as e:
        print(f"[tunnel] port {listen} busy ({e}); trying 18082", flush=True)
        listen = 18082
        transport.request_port_forward("127.0.0.1", listen)
    threading.Thread(target=accept_ssh, daemon=True).start()
    print(f"[tunnel] remote 127.0.0.1:{listen} -> local {local_port}", flush=True)

    sftp = client.open_sftp()
    for rel in (
        "ming_sim/lightweight_kg.py",
        "ming_sim/simulation.py",
        "ming_sim/decree.py",
    ):
        local = ROOT / rel
        remote = f"{REMOTE_ENGINE}/{rel}"
        ssh_run(client, f"mkdir -p {'/'.join(remote.split('/')[:-1])}")
        print(f"[sftp-engine] {rel}", flush=True)
        sftp.put(str(local), remote)
    ssh_run(client, f"mkdir -p {REMOTE_BENCH}/salvage_bench {OUT}")
    with sftp.file(f"{REMOTE_BENCH}/engine_root.txt", "w") as f:
        f.write(REMOTE_ENGINE + "\n")
    for rel in (
        "salvage_bench/__init__.py",
        "salvage_bench/paths.py",
        "salvage_bench/conds.py",
        "salvage_bench/cases_m.py",
        "salvage_bench/score.py",
        "salvage_bench/worker.py",
        "salvage_bench/run_ablation.py",
    ):
        local = LOCAL_BENCH / rel
        if not local.is_file():
            print(f"[skip-missing] {rel}", flush=True)
            continue
        remote = f"{REMOTE_BENCH}/{rel}"
        ssh_run(client, f"mkdir -p {'/'.join(remote.split('/')[:-1])}")
        print(f"[sftp-bench] {rel}", flush=True)
        sftp.put(str(local), remote)
    sftp.close()

    p2 = _load_program2_qwen()
    # Escape for embedding into remote python (key is hex/sk- form, no quotes expected)
    api_key = p2["api_key"].replace("\\", "\\\\").replace('"', '\\"')
    base_url = p2["base_url"].replace("\\", "\\\\").replace('"', '\\"')
    model = p2["model"].replace("\\", "\\\\").replace('"', '\\"')

    # patch env — inject Program2 Qwen key/model
    py = f"""
from pathlib import Path
p = Path("{REMOTE_ENGINE}/.env")
lines = p.read_text(encoding="utf-8").splitlines()
keys = {{
    "OPENAI_API_KEY": "{api_key}",
    "OPENAI_BASE_URL": "{base_url}",
    "OPENAI_MODEL": "{model}",
    "HTTPS_PROXY": "http://127.0.0.1:{listen}",
    "HTTP_PROXY": "http://127.0.0.1:{listen}",
    "ALL_PROXY": "http://127.0.0.1:{listen}",
    "NO_PROXY": "127.0.0.1,localhost",
}}
seen=set(); out=[]
for line in lines:
    if not line.strip() or line.strip().startswith("#") or "=" not in line:
        out.append(line); continue
    k=line.split("=",1)[0].strip()
    if k in keys:
        out.append(f"{{k}}={{keys[k]}}"); seen.add(k)
    else:
        out.append(line)
for k,v in keys.items():
    if k not in seen: out.append(f"{{k}}={{v}}")
p.write_text("\\n".join(out)+"\\n", encoding="utf-8")
print("ENV_OK", "model="+keys["OPENAI_MODEL"], "proxy="+keys["HTTPS_PROXY"], "key_tail="+keys["OPENAI_API_KEY"][-4:])
"""
    ssh_run(client, f"{VENV_PY} - <<'PY'\n{py}\nPY")

    probe = f"""
import os
from pathlib import Path
import httpx
env={{}}
for raw in Path("{REMOTE_ENGINE}/.env").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#") or "=" not in raw: continue
    k,v=raw.split("=",1); env[k.strip()]=v.strip().strip('"').strip("'")
for k,v in env.items():
    if k in ("HTTPS_PROXY","HTTP_PROXY","ALL_PROXY","NO_PROXY","OPENAI_BASE_URL","OPENAI_API_KEY","OPENAI_MODEL"):
        os.environ[k]=v
with httpx.Client(proxy=env.get("HTTPS_PROXY"), timeout=45.0) as c:
    r=c.post(env["OPENAI_BASE_URL"].rstrip("/")+"/chat/completions",
        headers={{"Authorization":"Bearer "+env["OPENAI_API_KEY"],"Content-Type":"application/json"}},
        json={{"model":env.get("OPENAI_MODEL","qwen3.7-plus"),"messages":[{{"role":"user","content":"ping"}}],"max_tokens":4}})
    print("CHAT", r.status_code, r.text[:300])
    raise SystemExit(0 if r.status_code == 200 else 2)
"""
    out, code = ssh_run(client, f"{VENV_PY} - <<'PY'\n{probe}\nPY", timeout=90)
    if "CHAT 200" not in out:
        print("[abort] Program2 DashScope probe failed", flush=True)
        client.close()
        proxy.close()
        raise SystemExit(2)

    # kill old workers
    ssh_run(
        client,
        "python3 - <<'PY'\n"
        "import os,signal,subprocess,time\n"
        "out=subprocess.check_output(['pgrep','-af','ming-salvage-sim-upstream'],text=True)\n"
        "for line in out.splitlines():\n"
        "  parts=line.split(None,1)\n"
        "  if len(parts)<2: continue\n"
        "  pid=int(parts[0]); cmd=parts[1]\n"
        "  if 'pgrep' in cmd or 'python3 -' in cmd: continue\n"
        "  if 'run_hallucination_ablation' in cmd or 'salvage_bench.run_ablation' in cmd or '_worker_' in cmd:\n"
        "    print('KILL',pid)\n"
        "    try: os.kill(pid,signal.SIGKILL)\n"
        "    except ProcessLookupError: pass\n"
        "time.sleep(1); print('KILL_DONE')\n"
        "PY",
    )

    # wipe only C* + summary markers; KEEP A0/A1
    ssh_run(
        client,
        f"mkdir -p {OUT}; "
        f"rm -f {OUT}/ablation_C0.jsonl {OUT}/ablation_C1.jsonl {OUT}/ablation_CK.jsonl "
        f"{OUT}/summary.json {OUT}/SUMMARY.md; "
        f": > {LOG}; "
        f"ls -lah {OUT}; echo WIPED_C_ONLY",
    )

    script = (
        "#!/bin/bash\n"
        f"cd {REMOTE_BENCH} || exit 1\n"
        "set -a\n"
        f". {REMOTE_ENGINE}/.env\n"
        "set +a\n"
        f"export SALVAGE_ENGINE_ROOT={REMOTE_ENGINE}\n"
        f"export PYTHONPATH=\"{REMOTE_BENCH}:${{PYTHONPATH}}\"\n"
        "export HTTPS_PROXY HTTP_PROXY ALL_PROXY NO_PROXY OPENAI_BASE_URL OPENAI_API_KEY OPENAI_MODEL\n"
        f"exec {VENV_PY} -X utf8 -m salvage_bench.run_ablation "
        f"--suite chain --conds C0,C1,CK --turn-timeout 360 "
        f"--out-dir runs/ablation_memkg\n"
    )
    sftp = client.open_sftp()
    with sftp.file(LAUNCHER, "w") as f:
        f.write(script)
    sftp.close()
    ssh_run(client, f"chmod +x {LAUNCHER}")
    ssh_run(
        client,
        f"nohup {LAUNCHER} >> {LOG} 2>&1 < /dev/null & echo $! > {PIDF}; echo STARTED $(cat {PIDF})",
        timeout=15,
    )
    time.sleep(5)
    ssh_run(
        client,
        f"pgrep -af 'run_hallucination_ablation|salvage_bench.run_ablation|_worker_' || echo NONE; "
        f"tail -n 30 {LOG}",
    )
    print("[hold] tunnel alive for C0/C1/CK", flush=True)

    while transport.is_active():
        out, _ = ssh_run(
            client,
            f"wc -l {OUT}/ablation_C*.jsonl 2>/dev/null; "
            f"tail -n 5 {LOG}; "
            f"test -f {OUT}/summary.json && echo DONE || echo RUN",
            timeout=40,
        )
        if out.strip().endswith("DONE") or "\nDONE" in out:
            print("[done] C-group finished", flush=True)
            break
        time.sleep(90)

    # pull C results + A0/A1 still on remote
    sftp = client.open_sftp()
    for name in (
        "summary.json",
        "SUMMARY.md",
        "run_c.log",
        "ablation_A0.jsonl",
        "ablation_A1.jsonl",
        "ablation_C0.jsonl",
        "ablation_C1.jsonl",
        "ablation_CK.jsonl",
    ):
        remote = f"{OUT}/{name}"
        try:
            sftp.stat(remote)
        except OSError:
            print(f"[skip] missing {name}", flush=True)
            continue
        print(f"[get] {name}", flush=True)
        sftp.get(remote, str(LOCAL_OUT / name))
    sftp.close()

    c_sum = json.loads((LOCAL_OUT / "summary.json").read_text(encoding="utf-8"))
    merged = merge_summaries(c_sum)
    (LOCAL_OUT / "summary.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    # also write merged SUMMARY.md
    order = ["A0", "A1", "C0", "C1", "CK"]
    md = [
        "# SAVeR 消融结果（记忆×KG 链）",
        "",
        f"时间：{merged.get('started_at')}；续跑：{merged.get('resumed_at')}",
        "",
        "| 条件 | 落库违规合计 | 邸报硬标记合计 | 错误回合 |",
        "|------|-------------|----------------|----------|",
    ]
    for cond in order:
        s = merged["conds"].get(cond) or {}
        md.append(
            f"| {cond} | {s.get('sum_live_total', '-')} | {s.get('sum_narrative_total', '-')} | {s.get('errors', '-')} |"
        )
    md.append("")
    md.append(f"> {merged.get('note', '')}")
    md.append("")
    (LOCAL_OUT / "SUMMARY.md").write_text("\n".join(md), encoding="utf-8")
    # push merged summary back
    sftp = client.open_sftp()
    sftp.put(str(LOCAL_OUT / "summary.json"), f"{OUT}/summary.json")
    sftp.put(str(LOCAL_OUT / "SUMMARY.md"), f"{OUT}/SUMMARY.md")
    sftp.close()
    print((LOCAL_OUT / "SUMMARY.md").read_text(encoding="utf-8"), flush=True)

    client.close()
    proxy.close()


if __name__ == "__main__":
    main()
