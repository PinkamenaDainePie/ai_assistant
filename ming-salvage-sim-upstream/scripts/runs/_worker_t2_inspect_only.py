# -*- coding: utf-8 -*-
import json, os, sys, time
from pathlib import Path
ROOT = Path(r"E:\ai_assistant\ming-salvage-sim-upstream")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HITL_MIN_DECISIONS", "0")
os.environ.setdefault("MING_SIM_THINKING_STREAM_LIMIT", "0")
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
envp = ROOT / ".env"
if envp.exists():
    for raw in envp.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from ming_sim.scenario_active import set_active_scenario
set_active_scenario(None)

from ming_sim.session import GameSession
from ming_sim.llm_config import load_llm_config
import ming_sim.token_stats as ts
_orig = ts.tlog

def _quiet(msg):
    if "思考]" in msg:
        return
    _orig(msg)

ts.tlog = _quiet

case = json.loads("{\"id\": \"t2_inspect_only\", \"directive\": \"\u7740\u6d3e\u4eba\u67e5\u6838\u5f00\u5c01\u8d48\u6d4e\u94f6\u4e24\u662f\u5426\u5230\u4f4d\uff0c\u53ea\u67e5\u4e0d\u529e\uff0c\u4e0d\u5f97\u518d\u62e8\u65b0\u9977\u3002\", \"decree\": \"\u6555\u66f0\uff1a\u7740\u6d3e\u5458\u67e5\u6838\u5f00\u5c01\u8d48\u6d4e\u94f6\u4e24\u662f\u5426\u5982\u6570\u5230\u4f4d\u53ca\u6709\u65e0\u4fb5\u541e\uff1b\u6b64\u65e8\u53ea\u51c6\u67e5\u6838\u594f\u62a5\uff0c\u4e0d\u5f97\u518d\u62e8\u65b0\u9977\u3001\u4e0d\u5f97\u64c5\u81ea\u62ff\u95ee\u5b98\u5458\u3002\u94a6\u6b64\u3002\"}")
db = r"E:\ai_assistant\ming-salvage-sim-upstream\data\hallucination_multi_faithful4.db"
out_one = Path(r"E:\ai_assistant\ming-salvage-sim-upstream\scripts\runs\_turn_t2_inspect_only.json")

llm = load_llm_config(
    os.environ["OPENAI_BASE_URL"],
    os.environ["OPENAI_MODEL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
session = GameSession(db, llm)
snap = session.begin_turn()
before = {
    k: int(v)
    for k, v in (session.state.metrics or {}).items()
    if isinstance(v, (int, float)) or str(v).lstrip("-").isdigit()
}
print(f"[worker] turn={snap.turn} {snap.year}.{snap.period:02d} case={case['id']}", flush=True)
session.add_directive(case["directive"], notes=case["id"])
session.enter_review()
t0 = time.time()

def on_event(kind, data):
    if kind in ("thinking", "text", "simulator_chunk", "extractor_chunk", "thinking_chunk"):
        return
    print(f"  [evt] {kind}: {str(data)[:120]}", flush=True)

result = session.resolve_turn(decree=case["decree"], on_event=on_event)
if getattr(result, "awaiting", False):
    choices = []
    for d in result.decisions:
        opts = d.get("options") or []
        choices.append(dict(opts[0]) if opts else {})
    report = session.submit_decisions(choices, on_event=on_event)
else:
    report = result.report or ""
elapsed = round(time.time() - t0, 1)
turn_no = int(session.state.turn) - 1
extraction = session.db.get_turn_extraction(turn_no) or {}
player_report = session.db.get_turn_report(turn_no) or ""
after = {
    k: int(v)
    for k, v in (session.state.metrics or {}).items()
    if isinstance(v, (int, float)) or str(v).lstrip("-").isdigit()
}
delta = {
    k: after.get(k, 0) - before.get(k, 0)
    for k in sorted(set(before) | set(after))
    if after.get(k, 0) != before.get(k, 0)
}
session.end_turn()
out = {
    "case_id": case["id"],
    "year": extraction.get("year") or snap.year,
    "period": extraction.get("period") or snap.period,
    "turn": turn_no,
    "elapsed_sec": elapsed,
    "error": None,
    "decree_text": case["decree"],
    "report": report,
    "player_report": player_report,
    "metrics_delta": delta,
    "extractor_output": extraction.get("extractor_output"),
    "gate_log": extraction.get("gate_log") or [],
}
out_one.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print(f"[worker-done] turn={turn_no} elapsed={elapsed}s report_len={len(report)}", flush=True)
