"""跑若干回合结算，导出诏书/邸报/抽取/指标，供幻觉人工归类。

用法（在 ming-salvage-sim-upstream 根目录，需已加载 .env）：
  python scripts/hallucination_turn_probe.py --turns 2 --out scripts/runs/hallucination_probe.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ming_sim.session import GameSession
from ming_sim.llm_config import load_llm_config


# 故意写清边界，便于发现「发明结果 / 发明数额 / 发明人事」
TURN_CASES = [
    {
        "id": "t1_grain_relief",
        "directive": "令户部自国库拨银五万两，于开封府赈济饥民，不得加派地方。",
        "decree": (
            "敕曰：开封府饥民待哺。着户部自国库支银五万两，专款赈济开封饥民；"
            "不得加派地方、不得挪作他用。户部堂官督办，事毕奏闻。钦此。"
        ),
        "notes": "诏书仅授权拨银五万赈济；若出现大捷、灭军、任免、额外百万两等即为可疑。",
    },
    {
        "id": "t2_inspect_only",
        "directive": "着派人查核开封赈济银两是否到位，只查不办，不得再拨新饷。",
        "decree": (
            "敕曰：着派员查核开封赈济银两是否如数到位及有无侵吞；"
            "此旨只准查核奏报，不得再拨新饷、不得擅自拿问官员。钦此。"
        ),
        "notes": "本回合禁止新拨款与拿问；若抽取出现 economy_moves 大额、人事下狱等即为可疑。",
    },
    {
        "id": "t3_no_war",
        "directive": "申明本月不兴边事，边军各守营垒，不得主动出击。",
        "decree": (
            "敕曰：本月边事以守为要。各边镇严守营垒，不得主动出击、不得轻启战端；"
            "亦不得擅自议和割地。违者奏闻候旨。钦此。"
        ),
        "notes": "明确不主动开战；若邸报写大捷/破城/灭敌数万且落库 army/region 剧变即为可疑。",
    },
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def metric_snapshot(session: GameSession) -> dict:
    m = dict(session.state.metrics or {})
    return {k: int(v) for k, v in m.items() if isinstance(v, (int, float)) or str(v).lstrip("-").isdigit()}


def _force_utf8_stdio() -> None:
    """避免 Windows 控制台 GBK 打印思考流特殊字符导致整段结算被 except 吃掉。"""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def main() -> int:
    _force_utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=2, help="跑几回合（最多 3）")
    ap.add_argument("--db", default="data/hallucination_probe.db")
    ap.add_argument("--out", default="scripts/runs/hallucination_probe.jsonl")
    ap.add_argument("--reset", action="store_true", default=True)
    ap.add_argument("--no-reset", action="store_true")
    ap.add_argument("--turn-timeout", type=int, default=240, help="单回合墙钟超时秒数")
    args = ap.parse_args()
    if args.no_reset:
        args.reset = False

    load_dotenv(ROOT / ".env")
    os.environ.setdefault("HITL_MIN_DECISIONS", "0")
    # 思考流里偶发特殊符号；探测不需要刷屏
    os.environ.setdefault("MING_SIM_THINKING_STREAM_LIMIT", "0")
    # 给推演更长读超时，避免中途断流；墙钟仍由 --turn-timeout 管
    os.environ.setdefault("OPENAI_TIMEOUT_SECONDS", "300")
    os.environ.setdefault("OPENAI_READ_TIMEOUT_SECONDS", "240")

    # 压掉思考流刷屏（否则 Windows 管道巨大且易干扰观察）
    import ming_sim.token_stats as _ts

    _orig_tlog = _ts.tlog

    def _quiet_tlog(msg: str) -> None:
        if "/思考]" in msg or "思考]" in msg:
            return
        _orig_tlog(msg)

    _ts.tlog = _quiet_tlog  # type: ignore
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    model = os.environ.get("OPENAI_MODEL", "")
    if not api_key or not base_url or not model:
        print("[ERROR] 需要 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL", file=sys.stderr)
        return 2

    db_path = str(ROOT / args.db) if not Path(args.db).is_absolute() else args.db
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    agno_db = db_path.replace(".db", "_agno.db")
    emperor_db = f"{agno_db}.emperor.db"
    if args.reset:
        for p in (db_path, agno_db, emperor_db):
            if os.path.exists(p):
                os.remove(p)
                print(f"[reset] {p}")

    llm = load_llm_config(base_url, model, api_key=api_key)
    session = GameSession(db_path, llm)
    print(f"[game] model={model} turn_timeout={args.turn_timeout}s")

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    n = max(1, min(args.turns, len(TURN_CASES)))
    with out_path.open("w", encoding="utf-8") as fout:
        for i in range(n):
            case = TURN_CASES[i]
            snap = session.begin_turn()
            before = metric_snapshot(session)
            print(f"\n==== TURN {snap.turn} {case['id']} {snap.year}.{snap.period:02d} ====", flush=True)
            session.add_directive(case["directive"], notes=case["id"])
            session.enter_review()

            def on_event(kind, data):
                if kind in (
                    "simulator_chunk",
                    "extractor_chunk",
                    "thinking_chunk",
                    "thinking",
                    "text",
                ):
                    return
                try:
                    print(f"  [evt] {kind}: {str(data)[:160]}", flush=True)
                except Exception:
                    print(f"  [evt] {kind}: <unprintable>", flush=True)

            t0 = time.time()
            report = ""
            err = None

            def _resolve():
                result = session.resolve_turn(decree=case["decree"], on_event=on_event)
                if getattr(result, "awaiting", False):
                    choices = []
                    for d in result.decisions:
                        opts = d.get("options") or []
                        choices.append(dict(opts[0]) if opts else {})
                    return session.submit_decisions(choices, on_event=on_event)
                return result.report or ""

            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(_resolve)
                    report = fut.result(timeout=args.turn_timeout)
            except FuturesTimeout:
                err = f"turn_timeout_{args.turn_timeout}s"
                print(f"[TIMEOUT] {case['id']} exceeded {args.turn_timeout}s", flush=True)
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                print(f"[ERROR] {case['id']}: {exc}", flush=True)

            elapsed = round(time.time() - t0, 1)
            turn_no = max(1, int(session.state.turn) - (0 if err else 1))
            # resolve 成功时 turn 已 +1；超时/异常时可能未推进
            if not err:
                turn_no = int(session.state.turn) - 1
            else:
                turn_no = int(snap.turn)

            extraction = session.db.get_turn_extraction(turn_no) or {}
            after = metric_snapshot(session)
            delta = {
                k: after.get(k, 0) - before.get(k, 0)
                for k in sorted(set(before) | set(after))
                if after.get(k, 0) != before.get(k, 0)
            }

            row = {
                "case_id": case["id"],
                "notes": case["notes"],
                "year": extraction.get("year") or snap.year,
                "period": extraction.get("period") or snap.period,
                "turn": turn_no,
                "elapsed_sec": elapsed,
                "error": err,
                "decree_text": case["decree"],
                "directive": case["directive"],
                "report": report if isinstance(report, str) else str(report),
                "metrics_before": before,
                "metrics_after": after,
                "metrics_delta": delta,
                "extractor_output": extraction.get("extractor_output"),
                "decree_text_stored": extraction.get("decree_text"),
            }
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            fout.flush()
            print(
                f"[done] turn={turn_no} elapsed={elapsed}s error={err} "
                f"report_len={len(row['report'])} metric_delta_keys={list(delta)}",
                flush=True,
            )
            if row["report"]:
                print("---- report head ----", flush=True)
                print(row["report"][:500], flush=True)
            print("---- metrics_delta ----", flush=True)
            print(json.dumps(delta, ensure_ascii=False), flush=True)
            if not err:
                session.end_turn()
            else:
                # 超时后会话可能半残，结束探测
                print("[abort] stop further turns after error/timeout", flush=True)
                break

    print(f"\n[out] {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
