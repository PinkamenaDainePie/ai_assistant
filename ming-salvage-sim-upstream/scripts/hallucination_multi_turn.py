# -*- coding: utf-8 -*-
"""Legacy 3-turn probe → experiments.faithfulness.worker."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.faithfulness.worker import build_worker, load_dotenv  # noqa: E402

TURN_CASES = [
    {
        "id": "t1_grain_relief",
        "directive": "令户部自国库拨银五万两，于开封府赈济饥民，不得加派地方。",
        "decree": (
            "敕曰：开封府饥民待哺。着户部自国库支银五万两，专款赈济开封饥民；"
            "不得加派地方、不得挪作他用。户部堂官督办，事毕奏闻。钦此。"
        ),
    },
    {
        "id": "t2_inspect_only",
        "directive": "着派人查核开封赈济银两是否到位，只查不办，不得再拨新饷。",
        "decree": (
            "敕曰：着派员查核开封赈济银两是否如数到位及有无侵吞；"
            "此旨只准查核奏报，不得再拨新饷、不得擅自拿问官员。钦此。"
        ),
    },
    {
        "id": "t3_no_war",
        "directive": "申明本月不兴边事，边军各守营垒，不得主动出击。",
        "decree": (
            "敕曰：本月边事以守为要。各边镇严守营垒，不得主动出击、不得轻启战端；"
            "亦不得擅自议和割地。违者奏闻候旨。钦此。"
        ),
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--turn-timeout", type=int, default=200)
    ap.add_argument("--db", default="data/hallucination_multi.db")
    ap.add_argument("--out", default="scripts/runs/hallucination_multi.jsonl")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--start-index", type=int, default=0)
    args = ap.parse_args()

    load_dotenv()
    db = str((ROOT / args.db).resolve())
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    py = sys.executable

    from ming_sim.scenario_active import set_active_scenario

    set_active_scenario(None)
    print("[main] deactivated scenario -> Chongzhen 1627 default", flush=True)

    if not args.resume:
        for p in (db, db.replace(".db", "_agno.db"), db.replace(".db", "_agno.db") + ".emperor.db"):
            if os.path.exists(p):
                os.remove(p)
        if out_path.exists():
            out_path.unlink()

    n = max(1, min(args.turns, len(TURN_CASES) - args.start_index))
    work = ROOT / "experiments" / "faithfulness" / "runs" / "_workers"
    work.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fout:
        for i in range(args.start_index, args.start_index + n):
            case = TURN_CASES[i]
            out_one = work / f"_turn_{case['id']}.json"
            worker_file = work / f"_worker_{case['id']}.py"
            if out_one.exists():
                out_one.unlink()
            worker_file.write_text(build_worker(case, db, str(out_one)), encoding="utf-8")
            print(f"\n==== SPAWN {case['id']} timeout={args.turn_timeout}s ====", flush=True)
            t0 = time.time()
            try:
                proc = subprocess.run(
                    [py, "-X", "utf8", str(worker_file)],
                    cwd=str(ROOT),
                    timeout=args.turn_timeout,
                    env={
                        **os.environ,
                        "PYTHONUTF8": "1",
                        "PYTHONIOENCODING": "utf-8",
                        "HITL_MIN_DECISIONS": "0",
                        "MING_SIM_THINKING_STREAM_LIMIT": "0",
                        "SAVER_GATE": os.environ.get("SAVER_GATE", "1"),
                        "SAVER_RECONCILE": os.environ.get("SAVER_RECONCILE", "1"),
                        "CHAPTER_MEMORY": os.environ.get("CHAPTER_MEMORY", "1"),
                        "LIGHTWEIGHT_KG": os.environ.get("LIGHTWEIGHT_KG", "0"),
                    },
                )
                elapsed = round(time.time() - t0, 1)
                if proc.returncode != 0 or not out_one.exists():
                    row = {
                        "case_id": case["id"],
                        "error": f"worker_exit_{proc.returncode}",
                        "elapsed_sec": elapsed,
                    }
                    fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fout.flush()
                    break
                row = json.loads(out_one.read_text(encoding="utf-8"))
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                fout.flush()
                print(f"[ok] {case['id']} elapsed={elapsed}s", flush=True)
            except subprocess.TimeoutExpired:
                row = {
                    "case_id": case["id"],
                    "error": f"timeout_{args.turn_timeout}s",
                    "elapsed_sec": round(time.time() - t0, 1),
                }
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                fout.flush()
                break

    print(f"\n[out] {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
