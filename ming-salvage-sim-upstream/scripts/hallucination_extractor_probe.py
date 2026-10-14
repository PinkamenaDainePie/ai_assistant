"""用含已知虚构事实的邸报喂真实 extractor，观察哪些幻觉会落库。

不调 season_simulator（避免思考环超时），专门测「叙事→抽取→Apply」放大。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("HITL_MIN_DECISIONS", "0")

from ming_sim.session import GameSession
from ming_sim.llm_config import load_llm_config
from ming_sim.decree import resolve_directives
import ming_sim.simulation as sim


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


DECREE = (
    "敕曰：开封府饥民待哺。着户部自国库支银五万两，专款赈济开封饥民；"
    "不得加派地方、不得挪作他用。户部堂官督办，事毕奏闻。钦此。"
)

# 故意混入：超诏书数额、假大捷、假任免、假密情、改年月
FAKE_NARRATIVE = """《开封赈济与虚报》
1627年10月 月末奏章

一、诏书核销
一、开封赈济 — 户部实拨国库银五十万两（非五万）办赈，开封饥民已全部安置妥当，地方士绅捐粮百万石（结果：完成）

二、长期局势
一、#5 蓟辽北防 — 蓟镇官兵主动出击，大破建州于抚顺关外，斩首一万二千级，收复失地三城（进展：good）

三、陛下未知者
一、京营空额。<secret>京营实欠饷银三万两，将领虚报兵额。</secret>
二、人事异动。<secret>已暗中拿问河南巡抚下狱，并起复张居正兼领户部。</secret>
"""


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    load_dotenv(ROOT / ".env")
    db = str(ROOT / "data" / "hallucination_extractor_probe.db")
    for p in (db, db.replace(".db", "_agno.db"), db.replace(".db", "_agno.db") + ".emperor.db"):
        if os.path.exists(p):
            os.remove(p)

    llm = load_llm_config(
        os.environ["OPENAI_BASE_URL"],
        os.environ["OPENAI_MODEL"],
        api_key=os.environ["OPENAI_API_KEY"],
    )
    session = GameSession(db, llm)
    snap = session.begin_turn()
    before = dict(session.state.metrics)
    session.add_directive("开封赈济五万两", notes="extractor-hallucination")
    session.enter_review()

    # monkeypatch：跳过真实 simulator，注入含幻觉的邸报
    def _fake_simulate(agent, state, db_, decree_text, previous_narrative, *args, **kwargs):
        payload = kwargs.get("simulator_payload") or sim.build_simulator_payload(
            state, db_, decree_text, previous_narrative
        )
        return FAKE_NARRATIVE, payload

    sim.simulate_season_with_payload = _fake_simulate  # type: ignore

    print("[resolve] extractor-only with planted hallucinations...")
    result = session.resolve_turn(decree=DECREE)
    report = result.report or ""
    turn_no = int(session.state.turn) - 1
    extraction = session.db.get_turn_extraction(turn_no) or {}
    after = dict(session.state.metrics)
    delta = {
        k: int(after.get(k, 0)) - int(before.get(k, 0))
        for k in set(before) | set(after)
        if int(after.get(k, 0) or 0) != int(before.get(k, 0) or 0)
    }

    out = {
        "mode": "extractor_only_planted_narrative",
        "turn": turn_no,
        "year": snap.year,
        "period": snap.period,
        "decree": DECREE,
        "planted_narrative": FAKE_NARRATIVE,
        "report_saved": report[:2000],
        "metrics_delta": delta,
        "extractor_output": extraction.get("extractor_output"),
    }
    out_path = ROOT / "scripts" / "runs" / "hallucination_extractor_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"metrics_delta": delta, "extractor_keys": list((extraction.get("extractor_output") or {}) if isinstance(extraction.get("extractor_output"), dict) else [])}, ensure_ascii=False, indent=2))
    print(f"[out] {out_path}")
    session.end_turn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
