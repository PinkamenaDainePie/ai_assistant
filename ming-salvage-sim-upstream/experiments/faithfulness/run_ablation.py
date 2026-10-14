# -*- coding: utf-8 -*-
"""Faithfulness ablation runner (gate / reconcile / memory / KG).

Standalone:
  cd e:/ai_assistant/experiments/salvage_faithfulness
  python -m salvage_bench.run_ablation --suite chain --conds A0,A,B,C0,C,CK

In-repo copy (same API, package name differs):
  cd ming-salvage-sim-upstream
  python -m experiments.faithfulness.run_ablation --suite chain --conds A,B,C

P0 live = extractor_output payload violations (see score.LIVE_METRIC_DEFINITION).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from .cases_m import (
    CHAIN_CASES,
    CORE_CHAIN_CASES,
    CORE_SINGLE_CASES,
    SINGLE_CASES,
    cases_by_mode,
)
from .conds import CONDS
from .paths import DATA_DIR, ENGINE_ROOT, PROJECT_DIR, RUNS_DIR
from .aggregate import aggregate_root, paired_deltas
from .score import LIVE_METRIC_DEFINITION, LIVE_METRIC_ID, score_narrative, score_row
from .worker import build_worker, load_dotenv


def _run_metadata() -> dict:
    meta = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "cwd": os.getcwd(),
        "openai_model": os.environ.get("OPENAI_MODEL"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL"),
        "temperature": os.environ.get("OPENAI_TEMPERATURE")
        or os.environ.get("MING_SIM_TEMPERATURE"),
        "top_p": os.environ.get("OPENAI_TOP_P") or os.environ.get("MING_SIM_TOP_P"),
        "seed": os.environ.get("SALVAGE_TRIAL_SEED") or os.environ.get("PYTHONHASHSEED"),
    }
    try:
        git = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ENGINE_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if git.returncode == 0:
            meta["engine_git_head"] = git.stdout.strip()
    except Exception:
        pass
    return meta


def _reset_db(db: str) -> None:
    for p in (db, db.replace(".db", "_agno.db"), db.replace(".db", "_agno.db") + ".emperor.db"):
        if os.path.exists(p):
            os.remove(p)


def _run_case(
    case: dict,
    *,
    db: str,
    out_path: Path,
    turn_timeout: int,
    env_extra: dict,
    append: bool,
    work_dir: Path,
) -> dict:
    py = sys.executable
    work_dir.mkdir(parents=True, exist_ok=True)
    out_one = work_dir / f"_turn_{case['id']}.json"
    worker_file = work_dir / f"_worker_{case['id']}.py"
    if out_one.exists():
        out_one.unlink()
    worker_file.write_text(build_worker(case, db, str(out_one)), encoding="utf-8")
    print(f"\n==== SPAWN {case['id']} timeout={turn_timeout}s ====", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [py, "-X", "utf8", str(worker_file)],
            cwd=str(ENGINE_ROOT),
            timeout=turn_timeout,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "HITL_MIN_DECISIONS": "0",
                "MING_SIM_THINKING_STREAM_LIMIT": "0",
                **env_extra,
            },
        )
        elapsed = round(time.time() - t0, 1)
        if proc.returncode != 0 or not out_one.exists():
            row = {
                "case_id": case["id"],
                "error": f"worker_exit_{proc.returncode}",
                "elapsed_sec": elapsed,
                "tags": case.get("tags") or [],
                "allow_expense_wanliang": case.get("allow_expense_wanliang"),
                "chain": case.get("chain"),
            }
        else:
            row = json.loads(out_one.read_text(encoding="utf-8"))
            row["tags"] = case.get("tags") or []
            row["allow_expense_wanliang"] = case.get("allow_expense_wanliang")
            row["chain"] = case.get("chain")
            row["decree_text"] = case.get("decree") or row.get("decree_text")
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - t0, 1)
        row = {
            "case_id": case["id"],
            "error": f"timeout_{turn_timeout}s",
            "elapsed_sec": elapsed,
            "tags": case.get("tags") or [],
            "allow_expense_wanliang": case.get("allow_expense_wanliang"),
            "chain": case.get("chain"),
        }

    mode = "a" if append and out_path.exists() else "w"
    with out_path.open(mode, encoding="utf-8") as fout:
        fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    status = "ERROR" if row.get("error") else "ok"
    print(
        f"[{status}] {case['id']} elapsed={row.get('elapsed_sec')} "
        f"gate={len(row.get('gate_log') or [])}",
        flush=True,
    )
    return row


def _summarize(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    live_tot = 0
    narr_tot = 0
    errors = 0
    per = []
    for row in rows:
        if row.get("error"):
            errors += 1
            per.append({"case_id": row.get("case_id"), "error": row.get("error")})
            continue
        live = score_row(row, use_gated=False)
        narr = score_narrative(row)
        live_tot += live["total"]
        narr_tot += narr["total"]
        per.append(
            {
                "case_id": row.get("case_id"),
                "live_total": live["total"],
                "narrative_total": narr["total"],
                "live": live,
                "narrative": narr,
                "gate_log": len(row.get("gate_log") or []),
            }
        )
    n_ok = len(rows) - errors
    return {
        "file": str(path),
        "n": len(rows),
        "n_ok": n_ok,
        "errors": errors,
        "sum_live_total": live_tot,
        "sum_narrative_total": narr_tot,
        "mean_live": (live_tot / n_ok) if n_ok else 0.0,
        "mean_narr": (narr_tot / n_ok) if n_ok else 0.0,
        "metric_policy": "P0 live/narr separate",
        "rows": per,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Salvage faithfulness ablation")
    ap.add_argument(
        "--suite",
        default="core",
        help="core(~26)|s2/m160(160)|s2chain(48)|m/m1k/m3k(~3000)|single|chain|legacy",
    )
    ap.add_argument(
        "--conds",
        default="A,B,C",
        help="comma list: A,B,C and/or A0,A1,C0,C1,CK",
    )
    ap.add_argument("--turn-timeout", type=int, default=360)
    ap.add_argument(
        "--out-dir",
        default=str(RUNS_DIR / "ablation_m"),
        help="relative to this project (salvage_faithfulness) or absolute",
    )
    ap.add_argument("--skip-singles", action="store_true")
    ap.add_argument("--skip-chains", action="store_true")
    ap.add_argument(
        "--trials",
        type=int,
        default=1,
        help="P1 multi-trial repeats (default 1; formal runs use 3). Writes trial_k/ subdirs when >1.",
    )
    args = ap.parse_args(argv)

    load_dotenv()
    print(f"[engine] {ENGINE_ROOT}", flush=True)
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (PROJECT_DIR / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = RUNS_DIR / "_workers"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    suite = (args.suite or "core").lower()
    if suite in {"core", "m26", "small"}:
        singles = [] if args.skip_singles else list(CORE_SINGLE_CASES)
        chains = [] if args.skip_chains else list(CORE_CHAIN_CASES)
    elif suite in {"s2", "m160", "m_s2", "s2chain", "s2_chain", "m160chain"}:
        picked = cases_by_mode(suite)
        singles = [] if args.skip_singles else [c for c in picked if not c.get("chain")]
        chains = [] if args.skip_chains else [c for c in picked if c.get("chain")]
    elif suite in {"m", "m1k", "m3k", "all", "1k", "3k"}:
        singles = [] if args.skip_singles else list(SINGLE_CASES)
        chains = [] if args.skip_chains else list(CHAIN_CASES)
    elif suite == "single":
        singles = list(SINGLE_CASES)
        chains = []
    elif suite in {"chain", "legacy"}:
        singles = []
        chains = list(CHAIN_CASES)
        if suite == "legacy":
            chains = [c for c in CORE_CHAIN_CASES if c.get("chain") == "chain_relief_inspect_hold"]
    else:
        picked = cases_by_mode(suite)
        singles = [c for c in picked if not c.get("chain")]
        chains = [c for c in picked if c.get("chain")]
    print(
        f"[suite] {suite} singles={len(singles)} chain_turns={len(chains)} "
        f"total={len(singles)+len(chains)} trials={args.trials}",
        flush=True,
    )

    cond_names = [x.strip().upper() for x in args.conds.split(",") if x.strip()]
    n_trials = max(1, int(args.trials))
    master: dict = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "suite": suite,
        "trials": n_trials,
        "live_metric_id": LIVE_METRIC_ID,
        "live_metric_definition": LIVE_METRIC_DEFINITION,
        "metric_policy": (
            "P0 extractor_live(=live alias)/narr separate; "
            "P1 t-CI/ICC exploratory; P2 SE/Judge off"
        ),
        "run_metadata": _run_metadata(),
        "conds": {},
    }

    for trial in range(1, n_trials + 1):
        trial_dir = out_dir / f"trial_{trial}" if n_trials > 1 else out_dir
        trial_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n======== TRIAL {trial}/{n_trials} -> {trial_dir} ========", flush=True)
        summary: dict = {"conds": {}, "trial": trial, "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}

        for cond in cond_names:
            if cond not in CONDS:
                print(f"[skip] unknown cond {cond}", flush=True)
                continue
            env_extra = dict(CONDS[cond])
            out_path = trial_dir / f"ablation_{cond}.jsonl"
            if out_path.exists():
                out_path.unlink()
            print(f"\n######## COND {cond} {env_extra} ########", flush=True)

            for case in singles:
                db = str((DATA_DIR / f"ablation_{cond}_{case['id']}_t{trial}.db").resolve())
                _reset_db(db)
                _run_case(
                    case,
                    db=db,
                    out_path=out_path,
                    turn_timeout=args.turn_timeout,
                    env_extra=env_extra,
                    append=True,
                    work_dir=work_dir,
                )

            by_chain: dict[str, list] = defaultdict(list)
            for case in chains:
                by_chain[str(case.get("chain") or case["id"])].append(case)
            for chain_id, cases in by_chain.items():
                db = str((DATA_DIR / f"ablation_{cond}_{chain_id}_t{trial}.db").resolve())
                _reset_db(db)
                for case in cases:
                    _run_case(
                        case,
                        db=db,
                        out_path=out_path,
                        turn_timeout=args.turn_timeout,
                        env_extra=env_extra,
                        append=True,
                        work_dir=work_dir,
                    )

            summary["conds"][cond] = _summarize(out_path)
            print(
                f"[summary {cond}] live={summary['conds'][cond]['sum_live_total']} "
                f"narr={summary['conds'][cond]['sum_narrative_total']} "
                f"mean_live={summary['conds'][cond]['mean_live']:.3f} "
                f"mean_narr={summary['conds'][cond]['mean_narr']:.3f} "
                f"errors={summary['conds'][cond]['errors']}",
                flush=True,
            )

        (trial_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        master["conds"][f"trial_{trial}"] = summary

    agg = aggregate_root(out_dir)
    deltas = []
    for a, b in (("A", "B"), ("B", "C"), ("A0", "A"), ("C0", "C"), ("C", "CK")):
        d = paired_deltas(agg, a, b)
        if d.get("ok"):
            deltas.append(d)
    agg["deltas"] = deltas
    agg_path = out_dir / "aggregate.json"
    agg_path.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = out_dir / "summary.json"
    master["aggregate"] = agg
    summary_path.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Salvage faithfulness 消融结果",
        "",
        f"时间：{master['started_at']}",
        f"trials：{n_trials}",
        "",
        "指标策略：**P0** `extractor_live`（表中仍简称 live）与 rule-based **narr** 分报；"
        "**P1** aggregate.json（Student-t CI，小样本 exploratory）；**P2** SE/Judge 关闭。",
        "",
        f"> live 定义：{LIVE_METRIC_DEFINITION}",
        "",
        "| 条件 | mean_live | CI95_live | mean_narr | CI95_narr | ICC_live | errorsΣ |",
        "|------|-----------|-----------|-----------|-----------|----------|---------|",
    ]
    for cond, s in (agg.get("conds") or {}).items():
        md_lines.append(
            f"| {cond} | {s.get('mean_live', '-'):.3f} | {s.get('ci95_live')} | "
            f"{s.get('mean_narr', '-'):.3f} | {s.get('ci95_narr')} | {s.get('icc_live')} | {s.get('sum_errors', '-')} |"
        )
    md_lines.append("")
    if deltas:
        md_lines.append("## 配对 Δ（trial-paired，描述性，非显著性检验）")
        md_lines.append("")
        for d in deltas:
            md_lines.append(
                f"- {d['pair']}: Δlive={d['delta_mean_live']:.3f} CI={d.get('ci95_delta_live')}, "
                f"Δnarr={d['delta_mean_narr']:.3f} CI={d.get('ci95_delta_narr')}"
            )
        md_lines.append("")
    md_path = out_dir / "SUMMARY.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\n[done] {summary_path}", flush=True)
    print(f"[aggregate] {agg_path}", flush=True)
    print(md_path.read_text(encoding="utf-8"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
