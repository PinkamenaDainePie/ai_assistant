#!/usr/bin/env python3
"""API smoke + one-turn flow for ming_wanli (salvage :8010)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8010"
FORBIDDEN = ("魏忠贤", "袁崇焕", "煤山", "崇祯帝")
EXPECTED_ISSUE_KEYWORDS = ("考成", "一条鞭", "蓟", "辽", "北防")
EXPECTED_MINISTERS = ("张居正", "冯保", "高拱")


def req(method: str, path: str, body: dict | None = None, timeout: float = 120) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def read_sse_done(path: str, body: dict | None = None, timeout: float = 300) -> dict | None:
    data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        buf = resp.read().decode("utf-8", errors="replace")
    for block in buf.split("\n\n"):
        if "event: done" not in block and "event: error" not in block:
            continue
        for line in block.split("\n"):
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "message" in payload and "state" not in payload:
                    raise RuntimeError(payload.get("message") or payload)
                return payload
    return None


def ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return passed


def main() -> int:
    results: list[bool] = []

    code, data = req("GET", "/api/scenarios", timeout=10)
    scenarios = (data or {}).get("scenarios") or []
    wanli = next((s for s in scenarios if s.get("id") == "ming_wanli"), None)
    results.append(ok("GET /api/scenarios", code == 200 and wanli is not None, f"code={code}"))

    code, _ = req("POST", "/api/scenarios/ming_wanli/activate", timeout=15)
    results.append(ok("POST activate ming_wanli", code == 200, f"code={code}"))

    code, ng = req("POST", "/api/menu/new_game", {"scenario_id": "ming_wanli"}, timeout=120)
    results.append(ok("POST new_game", code == 200, f"code={code}"))
    if code != 200:
        print(json.dumps(ng, ensure_ascii=False, indent=2)[:2000])
        return 1

    state = (ng or {}).get("state") or ng
    turn = state.get("turn") or {}
    results.append(ok("开局年份", turn.get("year") == 1573, f"year={turn.get('year')}"))
    results.append(ok("开局阶段", turn.get("phase") == "summoning", f"phase={turn.get('phase')}"))

    ministers = [m.get("name", "") for m in state.get("ministers", [])]
    for name in EXPECTED_MINISTERS:
        results.append(ok(f"大臣·{name}", name in ministers))
    results.append(ok("无晚明穿帮人物", "张居正" in ministers and "魏忠贤" not in ministers))

    issues = [i.get("title", "") for i in state.get("issues", [])]
    issue_blob = " ".join(issues)
    for kw in EXPECTED_ISSUE_KEYWORDS:
        results.append(ok(f"在办局势含「{kw}」", kw in issue_blob, issue_blob[:80]))

    armies = [a.get("name", "") for a in state.get("armies", []) if a.get("owner_power") == "ming"]
    results.append(ok("军队·蓟镇", any("蓟" in n for n in armies), str(armies[:6])))
    results.append(ok("军队·辽东", any("辽东" in n for n in armies), str(armies[:6])))
    results.append(ok("无关宁军", not any("关宁" in n for n in armies)))

    summary = state.get("previous_summary") or ""
    for bad in FORBIDDEN:
        results.append(ok(f"邸报无「{bad}」", bad not in summary))

    beizhili = next((r for r in (state.get("regions") or []) if r.get("id") == "beizhili"), None)
    if beizhili:
        dn = beizhili.get("display_name") or beizhili.get("name") or ""
        results.append(ok("北直隶 display_name", dn == beizhili.get("name"), dn))
        results.append(ok("无 circuit_name 宋制字段", not beizhili.get("circuit_name")))

    metrics = state.get("metrics") or {}
    results.append(ok("顶栏指标", bool(metrics), str(list(metrics.keys())[:4])))

    print("\n--- 颁诏结算（LLM，可能 1–3 分钟）---")
    issue: dict | None = None
    try:
        code, issue = req("POST", "/api/decree/issue", {}, timeout=300)
        if code != 200:
            raise RuntimeError(f"decree/issue HTTP {code}: {issue}")
        if isinstance(issue, dict) and issue.get("awaiting_decision"):
            decisions = issue.get("decisions") or []
            choices = []
            for d in decisions:
                opts = d.get("options") or []
                pick = opts[0] if opts else {"label": "准"}
                choices.append({"label": pick.get("label", "准"), "hint": pick.get("hint", ""), "note": ""})
            issue = read_sse_done("/api/decree/resolve_decisions/stream", {"choices": choices})
        results.append(ok("POST decree/issue 结算", issue is not None))
    except Exception as exc:  # noqa: BLE001
        results.append(ok("POST decree/issue 结算", False, str(exc)))

    if issue:
        st = issue.get("state") if isinstance(issue, dict) else None
        if st:
            t2 = st.get("turn") or {}
            results.append(
                ok(
                    "结算后回合推进",
                    (t2.get("turn", 0) > 1) or (t2.get("period", 0) > 1),
                    f"year={t2.get('year')} period={t2.get('period')} turn={t2.get('turn')}",
                )
            )
            report = issue.get("report") or ""
            results.append(ok("结算报告非空", len(str(report)) > 50, f"len={len(str(report))}"))
        else:
            results.append(ok("POST decree/issue 返回 state", False, str(type(issue))))

    code, _ = req("POST", "/api/menu/continue", {"scenario_id": "ming_wanli"}, timeout=60)
    results.append(ok("POST continue", code == 200, f"code={code}"))

    code, _ = req("GET", "/api/game/state", timeout=30)
    results.append(ok("GET state after continue", code == 200, f"code={code}"))

    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    print(f"\n合计: {passed} PASS / {failed} FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
