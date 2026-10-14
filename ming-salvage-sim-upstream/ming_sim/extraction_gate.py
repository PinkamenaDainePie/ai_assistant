"""SAVeR 风格结算门控：抽取 JSON 在 Apply 前对照诏书/密令实体验收。

原则：叙事可雾，状态须证。规则层始终执行；可选 LLM 审计只做最小修补建议，
最终仍以规则验收为准，避免审计模型再发明支出。
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ming_sim.token_stats import tlog

CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

PAY_PATTERNS = (
    r"(?:支银|拨银|发银|着.{0,8}银|国库.{0,6}银|内库.{0,6}银)",
)

FORBID_PAY_MARKERS = ("不得再拨", "不得拨款", "不准再拨", "不得新饷", "不得再发")

MILITARY_GRANT_MARKERS = (
    "建军", "立营", "收编", "招抚为军", "准其成军", "扩编", "募兵", "补兵",
    "裁军", "拨饷", "发饷", "军备", "火器", "大炮", "硝黄",
)

ARMY_CLAMP_FIELDS = ("supply", "morale", "loyalty", "equipment", "training", "mobility")


def _env_flag(name: str, default: str = "1") -> bool:
    raw = os.environ.get(name, default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def gate_settings() -> Dict[str, Any]:
    from ming_sim.llm_config import load_runtime_game

    settings = load_runtime_game()
    return {
        "enabled": bool(int(settings.get("saver_gate_enabled", 1))) and _env_flag("SAVER_GATE", "1"),
        "llm_audit": bool(int(settings.get("saver_llm_audit", 0))) or (os.environ.get("SAVER_LLM_AUDIT", "").strip() in {"1", "true", "yes"}),
        "drop_new_armies": bool(int(settings.get("saver_drop_new_armies", 1))) and _env_flag("SAVER_DROP_NEW_ARMIES", "1"),
        "army_clamp": int(settings.get("saver_army_clamp", _env_int("SAVER_ARMY_CLAMP", 5))),
        "issue_clamp": int(settings.get("saver_issue_clamp", _env_int("SAVER_ISSUE_CLAMP", 10))),
        "issue_unmentioned_clamp": int(settings.get("saver_issue_unmentioned_clamp", _env_int("SAVER_ISSUE_UNMENTIONED_CLAMP", 5))),
        "pay_tolerance": float(settings.get("saver_pay_tolerance", _env_float("SAVER_PAY_TOLERANCE", 0.5))),
    }


def canonicalize_extraction_payload(raw: object) -> Dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    from ming_sim.simulation import _canonicalize_extraction
    return _canonicalize_extraction(raw)


def parse_cn_or_arabic_number(text: str) -> Optional[float]:
    """Parse a Chinese/arabic integer that may include 十百千万, without treating a
    trailing 万两 unit as part of the numeric value. '五万' -> 5; '五千' -> 5000."""
    text = (text or "").strip().replace(",", "")
    if not text:
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return float(text)
    total = section = number = 0.0
    unit_seen = False
    for ch in text:
        if ch in CN_DIGITS:
            number = float(CN_DIGITS[ch])
        elif ch in "十百千":
            unit_seen = True
            section += (number or 1) * {"十": 10, "百": 100, "千": 1000}[ch]
            number = 0
        elif ch == "万":
            unit_seen = True
            total += (section + (number or 0) or 1) * 10000
            section = number = 0
        elif ch == "亿":
            unit_seen = True
            total += (section + (number or 0) or 1) * 100000000
            section = number = 0
    total += section + number
    if unit_seen or total:
        return float(total)
    return None


def parse_amount_before_unit(text: str) -> Optional[float]:
    """'五万' before 万两 means 5, not 50000."""
    text = (text or "").strip()
    if not text:
        return None
    if text.endswith("万") and len(text) > 1:
        head = parse_cn_or_arabic_number(text[:-1])
        if head is not None:
            return head
    return parse_cn_or_arabic_number(text)


def _liang_to_wanliang(amount: float, context: str) -> float:
    if "万两" in context or "万银" in context:
        return amount
    if amount >= 100:  # 五千两 / 5000 两
        return amount / 10000.0
    return amount


def authorized_payouts(decree_text: str, directives_text: str = "") -> List[Dict[str, Any]]:
    blob = f"{decree_text or ''}\n{directives_text or ''}"
    found: List[Dict[str, Any]] = []
    for m in re.finditer(
        r"(国库|内库)?.{0,16}(?:支银|拨银|发银|着.{0,8}银).{0,8}([零〇一二两三四五六七八九十百千\d\.]+)\s*(万)?两",
        blob,
    ):
        account = m.group(1) or "国库"
        span = m.group(0)
        num = parse_cn_or_arabic_number(m.group(2) or "")
        if num is None:
            continue
        unit_wan = bool(m.group(3)) or "万两" in span
        wan = num if unit_wan else (num / 10000.0 if num >= 100 else num)
        if wan <= 0:
            continue
        found.append({"account": account, "amount": wan, "span": span})
    if not found:
        for m in re.finditer(r"([零〇一二两三四五六七八九十百千\d\.]+)\s*万两", blob):
            if not re.search(PAY_PATTERNS[0], blob[max(0, m.start() - 24): m.end() + 8]):
                continue
            num = parse_cn_or_arabic_number(m.group(1))
            if num is None or num <= 0:
                continue
            found.append({"account": "国库", "amount": float(num), "span": m.group(0)})
    return found


def payouts_forbidden(decree_text: str, directives_text: str = "") -> bool:
    blob = f"{decree_text or ''}{directives_text or ''}"
    return any(marker in blob for marker in FORBID_PAY_MARKERS)


def military_granted(decree_text: str, directives_text: str = "") -> bool:
    blob = f"{decree_text or ''}{directives_text or ''}"
    return any(marker in blob for marker in MILITARY_GRANT_MARKERS)


def _log(entries: List[Dict[str, object]], action: str, field: str, detail: str, **extra: object) -> None:
    row = {"action": action, "field": field, "detail": detail, **extra}
    entries.append(row)
    tlog(f"[gate] {action} field={field} {detail}")


def _as_list(value: object) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _as_dict(value: object) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clamp_num(value: object, lo: int, hi: int) -> Tuple[Optional[float], bool]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None, False
    clamped = max(lo, min(hi, num))
    return clamped, clamped != num


def gate_economy_moves(
    moves: Sequence[Dict[str, Any]],
    *,
    decree_text: str,
    directives_text: str,
    settings: Dict[str, Any],
    log: List[Dict[str, object]],
) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    forbidden = payouts_forbidden(decree_text, directives_text)
    grants = authorized_payouts(decree_text, directives_text)
    remaining = [dict(g) for g in grants]
    for move in moves:
        if not isinstance(move, dict):
            continue
        try:
            delta = float(move.get("delta") or 0)
        except (TypeError, ValueError):
            continue
        if delta >= 0:
            kept.append(move)
            continue
        if forbidden:
            _log(log, "drop", "economy_moves", "decree forbids additional payout", before=move)
            continue
        if not remaining:
            _log(log, "drop", "economy_moves", "no decree authorization for expense", before=move)
            continue
        account = str(move.get("account") or "国库")
        need = abs(delta)
        matched = None
        for grant in remaining:
            if grant["account"] == account and abs(grant["amount"] - need) <= settings["pay_tolerance"]:
                matched = grant
                break
        if matched is None:
            for grant in remaining:
                if grant["account"] == account and grant["amount"] + settings["pay_tolerance"] >= need:
                    matched = grant
                    break
        if matched is None:
            _log(log, "drop", "economy_moves", "expense does not match authorized payout", before=move)
            continue
        remaining.remove(matched)
        if abs(matched["amount"] - need) > settings["pay_tolerance"]:
            patched = dict(move)
            patched["delta"] = -float(matched["amount"])
            _log(log, "clamp", "economy_moves", "clamped to authorized amount", before=move, after=patched)
            kept.append(patched)
        else:
            kept.append(move)
    return kept


def gate_secret_updates(
    updates: Sequence[Dict[str, Any]],
    *,
    active_secret_ids: Sequence[int],
    log: List[Dict[str, object]],
) -> List[Dict[str, Any]]:
    allowed = {int(i) for i in active_secret_ids}
    if not allowed:
        if updates:
            _log(log, "drop", "secret_order_updates", "no active secret orders", before=list(updates))
        return []
    kept = []
    for item in updates:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("order_id", item.get("密令编号"))
        try:
            oid = int(raw_id)
        except (TypeError, ValueError):
            _log(log, "drop", "secret_order_updates", "non-integer order_id", before=item)
            continue
        if oid not in allowed:
            _log(log, "drop", "secret_order_updates", f"order_id {oid} not active", before=item)
            continue
        kept.append(item)
    return kept


def gate_new_armies(
    armies: Sequence[Dict[str, Any]],
    *,
    granted: bool,
    drop_by_default: bool,
    log: List[Dict[str, object]],
) -> List[Dict[str, Any]]:
    if not armies:
        return []
    if drop_by_default and not granted:
        _log(log, "drop", "new_armies", "no decree authorization to create armies", before=list(armies))
        return []
    return list(armies)


def gate_arms_and_powers(
    arms: Dict[str, Any],
    powers: Dict[str, Any],
    *,
    granted: bool,
    log: List[Dict[str, object]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if arms and not granted:
        numeric = {k: v for k, v in arms.items() if k != "原因" and k != "reason"}
        if any(v not in (0, 0.0, None, "") for v in numeric.values()):
            _log(log, "drop", "arms_changes", "no military authorization", before=arms)
            arms = {}
    if powers and not granted:
        cleaned = {}
        dropped = {}
        for pid, delta in powers.items():
            if isinstance(delta, dict) and any(
                _nonzero(delta.get(k)) for k in ("威望", "实力", "经济", "prestige", "strength", "economy")
            ):
                dropped[pid] = delta
            else:
                cleaned[pid] = delta
        if dropped:
            _log(log, "drop", "power_updates", "non-zero power delta without authorization", before=dropped)
        powers = cleaned
    return arms, powers


def _nonzero(value: object) -> bool:
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return bool(value)


def gate_army_delta(
    army_delta: Dict[str, Any],
    *,
    granted: bool,
    clamp: int,
    log: List[Dict[str, object]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for army_id, delta in _as_dict(army_delta).items():
        if not isinstance(delta, dict):
            continue
        patched = dict(delta)
        if not granted and "manpower" in patched:
            _log(log, "drop", "army_delta.manpower", f"{army_id} manpower change without authorization", before=patched.get("manpower"))
            patched.pop("manpower", None)
        for field in ARMY_CLAMP_FIELDS:
            if field not in patched:
                continue
            clamped, changed = _clamp_num(patched[field], -clamp, clamp)
            if clamped is None:
                continue
            if changed:
                _log(log, "clamp", f"army_delta.{field}", f"{army_id} {field} {patched[field]} -> {clamped}")
                patched[field] = int(clamped) if clamped == int(clamped) else clamped
        out[army_id] = patched
    return out


def gate_issue_advances(
    advances: Sequence[Dict[str, Any]],
    *,
    decree_text: str,
    narrative: str,
    clamp: int,
    unmentioned_clamp: int,
    log: List[Dict[str, object]],
) -> List[Dict[str, Any]]:
    blob = f"{decree_text or ''}\n{narrative or ''}"
    kept: List[Dict[str, Any]] = []
    for item in advances:
        if not isinstance(item, dict):
            continue
        patched = dict(item)
        raw = patched.get("delta_bar", patched.get("进度增量"))
        try:
            delta = float(raw)
        except (TypeError, ValueError):
            kept.append(patched)
            continue
        issue_id = patched.get("issue_id", patched.get("局势编号"))
        mentioned = str(issue_id) in blob or any(
            str(patched.get(k) or "") and str(patched.get(k)) in blob
            for k in ("title", "narrative", "叙述", "阶段")
        )
        limit = clamp if mentioned else unmentioned_clamp
        bounded = max(-limit, min(limit, delta))
        if bounded != delta:
            _log(log, "clamp", "issue_advances", f"issue {issue_id} {delta} -> {bounded} (limit={limit})")
            patched["delta_bar"] = int(bounded) if bounded == int(bounded) else bounded
            if "进度增量" in patched:
                patched["进度增量"] = patched["delta_bar"]
        kept.append(patched)
    return kept


def apply_rule_gate(
    extracted: Dict[str, object],
    *,
    decree_text: str = "",
    directives_text: str = "",
    active_secret_ids: Sequence[int] = (),
    narrative: str = "",
    settings: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    settings = settings or gate_settings()
    log: List[Dict[str, object]] = []
    data = deepcopy(canonicalize_extraction_payload(extracted))
    granted = military_granted(decree_text, directives_text)

    data["economy_moves"] = gate_economy_moves(
        _as_list(data.get("economy_moves")),
        decree_text=decree_text,
        directives_text=directives_text,
        settings=settings,
        log=log,
    )
    data["secret_order_updates"] = gate_secret_updates(
        _as_list(data.get("secret_order_updates")),
        active_secret_ids=active_secret_ids,
        log=log,
    )
    data["new_armies"] = gate_new_armies(
        _as_list(data.get("new_armies")),
        granted=granted,
        drop_by_default=bool(settings["drop_new_armies"]),
        log=log,
    )
    arms, powers = gate_arms_and_powers(
        _as_dict(data.get("arms_changes")),
        _as_dict(data.get("power_updates")),
        granted=granted,
        log=log,
    )
    data["arms_changes"] = arms
    data["power_updates"] = powers
    data["army_delta"] = gate_army_delta(
        _as_dict(data.get("army_delta")),
        granted=granted,
        clamp=int(settings["army_clamp"]),
        log=log,
    )
    data["issue_advances"] = gate_issue_advances(
        _as_list(data.get("issue_advances")),
        decree_text=decree_text,
        narrative=narrative,
        clamp=int(settings["issue_clamp"]),
        unmentioned_clamp=int(settings["issue_unmentioned_clamp"]),
        log=log,
    )
    return data, log


def maybe_llm_audit(
    extracted: Dict[str, object],
    *,
    decree_text: str,
    directives_text: str,
    active_secret_ids: Sequence[int],
    llm_config=None,
    agno_db=None,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """可选审计：只允许删/钳制已有字段，不允许新增支出或新建军。失败则原样返回。"""
    if llm_config is None:
        return extracted, []
    try:
        from ming_sim.agents import create_json_sanitizer_agent, parse_agent_json, run_agent_text
    except Exception:
        return extracted, []
    try:
        agent = create_json_sanitizer_agent(llm_config, agno_db)
        payload = {
            "task": "audit_extraction_before_commit",
            "decree_text": decree_text,
            "directives_text": directives_text,
            "active_secret_ids": list(active_secret_ids),
            "extracted": extracted,
            "instruction": (
                "对照诏书授权删除无依据的钱粮支出、无主密令进度、无授权新建军队/军备/势力。"
                "只输出 JSON object，字段集合必须是输入 extracted 的子集；禁止新增 economy_moves 或 new_armies。"
            ),
        }
        raw = run_agent_text(agent, json.dumps(payload, ensure_ascii=False), tag="saver-audit")
        parsed = parse_agent_json(raw, "SAVeR审计")
        if not isinstance(parsed, dict):
            return extracted, [{"action": "audit_skip", "detail": "non-object"}]
        audited = canonicalize_extraction_payload(parsed)
        if _as_list(audited.get("economy_moves")) and not _as_list(extracted.get("economy_moves")):
            return extracted, [{"action": "audit_reject", "detail": "audit invented economy_moves"}]
        if _as_list(audited.get("new_armies")) and not _as_list(extracted.get("new_armies")):
            return extracted, [{"action": "audit_reject", "detail": "audit invented new_armies"}]
        return audited, [{"action": "audit", "detail": "applied sanitizer subset"}]
    except Exception as exc:
        tlog(f"[gate] llm audit skipped: {exc}")
        return extracted, [{"action": "audit_skip", "detail": str(exc)}]


def gate_extraction(
    extracted: Dict[str, object],
    *,
    decree_text: str = "",
    directives_text: str = "",
    active_secret_ids: Sequence[int] = (),
    narrative: str = "",
    llm_config=None,
    agno_db=None,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    settings = gate_settings()
    if not settings["enabled"]:
        return canonicalize_extraction_payload(extracted), [{"action": "bypass", "detail": "saver_gate_enabled=0"}]

    data = canonicalize_extraction_payload(extracted)
    audit_log: List[Dict[str, object]] = []
    if settings["llm_audit"]:
        data, audit_log = maybe_llm_audit(
            data,
            decree_text=decree_text,
            directives_text=directives_text,
            active_secret_ids=active_secret_ids,
            llm_config=llm_config,
            agno_db=agno_db,
        )
    gated, rule_log = apply_rule_gate(
        data,
        decree_text=decree_text,
        directives_text=directives_text,
        active_secret_ids=active_secret_ids,
        narrative=narrative,
        settings=settings,
    )
    return gated, audit_log + rule_log
