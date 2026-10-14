# -*- coding: utf-8 -*-
"""Pack, upload ming-salvage-sim-upstream to 006:/home/async/data-disk/ljc and start ablation."""
from __future__ import annotations

import os
import tarfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent
REMOTE_BASE = "/home/async/data-disk/ljc"
REMOTE_DIR = f"{REMOTE_BASE}/ming-salvage-sim-upstream"
HOST = "202.115.17.216"
PORT = 11222
USER = "async"
PASSWORD = "asdf@1234"

EXCLUDE_PREFIXES = (
    ".git/",
    "data/",
    "scripts/runs/",
    "__pycache__/",
    ".pytest_cache/",
    "node_modules/",
    ".venv/",
    "web/",
    "docs/",
    "frontend/",
    # wheelhouse uploaded as separate tarball
    "wheelhouse_linux/",
)

EXCLUDE_NAMES = {
    "_ablation_upload.tgz",
    "_deploy_ablation_006.py",
    "_remote_probe.py",
    "_remote_probe2.py",
}

EXCLUDE_SUFFIXES = (
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".otf",
    ".ttf",
    ".woff",
    ".woff2",
    ".mp4",
    ".pdf",
    ".docx",
    ".xlsx",
)


def _should_exclude(name: str) -> bool:
    name = name.replace("\\", "/")
    base = name.rsplit("/", 1)[-1]
    if base in EXCLUDE_NAMES:
        return True
    if name.startswith("_remote_") or name.startswith("_ablation"):
        return True
    lower = name.lower()
    for s in EXCLUDE_SUFFIXES:
        if lower.endswith(s):
            return True
    for p in EXCLUDE_PREFIXES:
        if name == p.rstrip("/") or name.startswith(p):
            return True
    # keep .env for API keys on remote
    return False


def make_tarball(out: Path) -> Path:
    if out.exists():
        out.unlink()
    with tarfile.open(out, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if _should_exclude(rel):
                continue
            tar.add(path, arcname=f"ming-salvage-sim-upstream/{rel}")
    print(f"[tar] {out} size={out.stat().st_size}")
    return out


def main() -> None:
    tarball = ROOT / "_ablation_upload.tgz"
    make_tarball(tarball)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST, port=PORT, username=USER, password=PASSWORD,
        timeout=30, allow_agent=False, look_for_keys=False,
    )

    def run(cmd: str, timeout: int = 120) -> str:
        print(f"[ssh] {cmd[:160]}{'...' if len(cmd) > 160 else ''}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        if out.strip():
            print(out[-2000:])
        if err.strip():
            print("[stderr]", err[-1500:])
        if code != 0:
            raise RuntimeError(f"remote exit {code}: {cmd}")
        return out

    run(f"mkdir -p {REMOTE_BASE}")
    remote_tar = f"{REMOTE_BASE}/_ablation_upload.tgz"
    print(f"[sftp] put {tarball} -> {remote_tar} ({tarball.stat().st_size} bytes)")

    def _upload() -> None:
        sftp = client.open_sftp()
        try:
            last = [0.0]

            def cb(transferred: int, total: int) -> None:
                now = time.time()
                if now - last[0] >= 2.0 or transferred >= total:
                    pct = 100.0 * transferred / max(total, 1)
                    print(f"[sftp] {transferred}/{total} ({pct:.1f}%)")
                    last[0] = now

            sftp.put(str(tarball), remote_tar, callback=cb)
        finally:
            sftp.close()

    for attempt in range(1, 4):
        try:
            _upload()
            break
        except Exception as e:
            print(f"[sftp] attempt {attempt} failed: {e}")
            if attempt >= 3:
                raise
            client.close()
            time.sleep(2)
            client.connect(
                HOST, port=PORT, username=USER, password=PASSWORD,
                timeout=30, allow_agent=False, look_for_keys=False,
            )

    # upload offline wheelhouse (006 has no outbound PyPI)
    wh_local = ROOT / "wheelhouse_linux"
    wh_tar = ROOT / "_wheelhouse_linux.tgz"
    if wh_tar.exists():
        wh_tar.unlink()
    with tarfile.open(wh_tar, "w:gz") as tar:
        tar.add(wh_local, arcname="wheelhouse_linux")
    print(f"[tar] wheelhouse {wh_tar.stat().st_size} bytes")
    remote_wh = f"{REMOTE_BASE}/_wheelhouse_linux.tgz"
    sftp = client.open_sftp()
    try:
        sftp.put(str(wh_tar), remote_wh)
    finally:
        sftp.close()

    run(f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR} && tar -xzf {remote_tar} -C {REMOTE_BASE}")
    run(f"tar -xzf {remote_wh} -C {REMOTE_DIR}")
    run(f"test -f {REMOTE_DIR}/requirements.txt && test -d {REMOTE_DIR}/wheelhouse_linux && echo UNPACK_OK")

    # venv + offline deps (do not hit network)
    venv = f"{REMOTE_DIR}/.venv"
    wh = f"{REMOTE_DIR}/wheelhouse_linux"
    run(
        f"python3 -m venv {venv} && "
        f"{venv}/bin/pip install --no-index --find-links={wh} "
        f"\"agno[openai,sqlite]==2.6.18\" greenlet",
        timeout=600,
    )
    run(
        f"{venv}/bin/python -c "
        f"\"import agno,openai,sqlalchemy; from agno.agent import Agent; "
        f"from agno.db.sqlite import SqliteDb; print('deps_ok', agno.__version__)\""
    )

    # ensure .env present
    run(f"test -f {REMOTE_DIR}/.env && echo HAS_ENV || echo NO_ENV")
    # sanity: required keys exist without printing values
    run(
        f"{venv}/bin/python - <<'PY'\n"
        f"from pathlib import Path\n"
        f"p=Path('{REMOTE_DIR}/.env')\n"
        f"text=p.read_text(encoding='utf-8') if p.exists() else ''\n"
        f"keys=['OPENAI_API_KEY','OPENAI_BASE_URL','OPENAI_MODEL']\n"
        f"for k in keys:\n"
        f"    ok=any(line.startswith(k+'=') and len(line.split('=',1)[1].strip())>0 for line in text.splitlines() if not line.startswith('#'))\n"
        f"    print(k, 'OK' if ok else 'MISSING')\n"
        f"PY"
    )

    # start ablation in background
    run(f"mkdir -p {REMOTE_DIR}/scripts/runs/ablation_m {REMOTE_DIR}/data")
    log = f"{REMOTE_DIR}/scripts/runs/ablation_m/run.log"
    cmd = (
        f"cd {REMOTE_DIR} && "
        f"nohup {venv}/bin/python -X utf8 scripts/run_hallucination_ablation.py "
        f"--suite m --conds A,B,C --turn-timeout 360 "
        f"--out-dir scripts/runs/ablation_m "
        f"> {log} 2>&1 & echo $!"
    )
    out = run(cmd)
    pid = out.strip().splitlines()[-1].strip()
    print(f"[started] pid={pid} log={log}")
    time.sleep(3)
    run(f"ps -p {pid} -o pid,cmd || true; tail -n 30 {log} || true")
    client.close()
    print("[done] deploy+start")


if __name__ == "__main__":
    main()
