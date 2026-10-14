"""把门控丢掉的硬情节从玩家可见邸报里抹掉，避免「档未改、字还在」污染下月上下文。

抽取仍读原始叙事；落库 turn_report / 章节记忆用调和后文本。
许可事实：committed 钱粮/军册 + gate_log 拒绝项；不靠固定旧句模板。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set


_SECRET_DETAIL_RE = re.compile(r"<secret>\s*(.*?)\s*</secret>", re.DOTALL)
_CHAPTER_UNKNOWN = re.compile(
    r"(?:^[一二三四五六七八九十]+、)?陛下未知者[^\n]*\n(?:.*?)(?=^[一二三四五六七八九十]+、|\Z)",
    re.MULTILINE | re.DOTALL,
)
_CHAPTER_SECRET_ORDERS = re.compile(
    r"(?:^[一二三四五六七八九十]+、)?密令动向[^\n]*\n(?:.*?)(?=^[一二三四五六七八九十]+、|\Z)",
    re.MULTILINE | re.DOTALL,
)

# 奏章里「某部 + 成军/人数/聚结」：未入军册时一律改口
_UNREGISTERED_FORCE = re.compile(
    r"([\u4e00-\u9fff]{2,8}部)"
    r"(?=(?:聚众|扩至|增至|已聚|流寇|成股|盘踞|已具|新聚|"
    r"[一二三四五六七八九十百千万零〇\d]+人|"
    r"[^，。；]{0,16}聚))"
)

_SHORTFALL_CLAUSE = re.compile(
    r"[，,]?然[^；。]{0,100}?(?:实得不足|不足半数|实到饥民|实到[^；。]{0,10}仅|"
    r"截留银两|层层截留|被开封[^；。]{0,8}截留)[^；。]{0,60}[；;]"
)

_EXTRA_RELIEF_CLAIM = re.compile(
    r"(?:国库因西北赈济又损五万两|"
    r"户部临时拨付五万两[^，。；]*|"
    r"洪承畴[^，。；]{0,12}拨[^，。；]{0,20}万两[^，。；]*)"
)


def _has_active_secret_orders(secret_orders: Sequence[object] | None) -> bool:
    if not secret_orders:
        return False
    for item in secret_orders:
        if isinstance(item, dict):
            status = str(item.get("status") or "active").lower()
            if status in {"active", "pending_review"}:
                return True
            if item.get("id") not in (None, "", 0):
                return True
        elif item:
            return True
    return False


def _as_list(value: object) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _as_dict(value: object) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dropped(gate_log: Sequence[Dict[str, object]] | None, field: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in gate_log or []:
        if not isinstance(item, dict):
            continue
        if item.get("action") != "drop":
            continue
        if str(item.get("field") or "") == field:
            rows.append(item)
    return rows


def _army_names(before: object) -> List[str]:
    names: List[str] = []
    for army in _as_list(before):
        if not isinstance(army, dict):
            continue
        raw = str(army.get("name") or "").strip()
        if raw and raw not in names:
            names.append(raw)
    names.sort(key=len, reverse=True)
    return names


def _committed_army_names(committed: object) -> Set[str]:
    """落库后军册里已有的番号（含军队变化键）；新建军若为空则不保护流寇部名。"""
    data = _as_dict(committed)
    names: Set[str] = set()
    for key in ("army_delta", "军队变化"):
        block = data.get(key)
        if isinstance(block, dict):
            for name in block.keys():
                if isinstance(name, str) and name.strip():
                    names.add(name.strip())
    for army in _as_list(data.get("new_armies") or data.get("新建军队")):
        if isinstance(army, dict):
            n = str(army.get("name") or "").strip()
            if n:
                names.add(n)
    return names


def _replace_name(text: str, name: str) -> str:
    if not name or name not in text:
        return text
    if name.endswith("部"):
        repl = "未入军册之众"
    else:
        repl = f"{name}（传闻，未入军册）"
    return text.replace(name, repl)


def _wanliang_to_liang_phrases(delta: object) -> List[str]:
    try:
        wan = abs(float(delta))
    except (TypeError, ValueError):
        return []
    liang = int(round(wan * 10000))
    if liang <= 0:
        return []
    phrases = [f"{liang}两", f"{liang} 两"]
    if liang % 1000 == 0:
        thousand = liang // 1000
        phrases.extend([f"{thousand}千两", f"{thousand}千 两"])
    return phrases


def _move_delta(row: object) -> float:
    data = _as_dict(row)
    for key in ("delta", "增量"):
        try:
            return float(data.get(key))
        except (TypeError, ValueError):
            continue
    return 0.0


def _move_text(row: object) -> str:
    data = _as_dict(row)
    return " ".join(
        str(data.get(k) or "")
        for k in ("category", "分类", "reason", "原因", "account", "账户")
    )


def _economy_moves(committed: object) -> List[Any]:
    data = _as_dict(committed)
    moves = data.get("economy_moves") or data.get("钱粮收支") or []
    return _as_list(moves)


def _committed_full_relief(committed: object) -> bool:
    for row in _economy_moves(committed):
        if _move_delta(row) < 0 and abs(_move_delta(row) + 5) < 0.6:
            blob = _move_text(row)
            if "赈" in blob or "开封" in blob:
                return True
    return False


def _redact_invented_shortfalls(text: str, committed: object) -> str:
    """落库已按诏书足额出账时，删掉赈济核销里的少额/截留说法（不碰火耗截留等财政积弊）。"""
    if not _committed_full_relief(committed):
        return text

    def _repl(m: re.Match) -> str:
        span = m.group(0)
        ctx = text[max(0, m.start() - 48) : m.end()]
        if "火耗截留" in span and not any(t in span for t in ("饥民", "实得", "实到", "赈银")):
            return span
        if not any(t in ctx for t in ("赈", "饥民", "开封", "实得", "实到", "截留银")):
            return span
        return "；户部按旨意五万两出账，地方侵吞细节未入本月太仓；"

    text = _SHORTFALL_CLAUSE.sub(_repl, text)
    text = re.sub(
        r"然因地方胥吏盘剥，实到饥民之手仅[^，。]+，余款[^，。]+，",
        "",
        text,
    )
    text = re.sub(
        r"仅三万五千两实济饥民，余一万五千两被[^。]+。",
        "账册仍按上月五万两核销，侵吞细节未入本月太仓。",
        text,
    )
    text = re.sub(
        r"实赈不及半数",
        "赈务已按太仓出账数核销",
        text,
    )
    text = re.sub(
        r"实发不足半",
        "账册仍按拨数核销",
        text,
    )
    return text


def _committed_new_army_names(committed: object) -> Set[str]:
    data = _as_dict(committed)
    names: Set[str] = set()
    for army in _as_list(data.get("new_armies") or data.get("新建军队")):
        if isinstance(army, dict):
            n = str(army.get("name") or "").strip()
            if n:
                names.add(n)
    return names


def _redact_unregistered_forces(
    text: str,
    gate_log: Sequence[Dict[str, object]] | None,
    committed: object,
) -> str:
    """未入新建军册的「X部+成军动词」一律改口；不依赖本回合是否 drop 过 new_armies。"""
    allowed = _committed_new_army_names(committed)
    for item in _dropped(gate_log, "new_armies"):
        for name in _army_names(item.get("before")):
            allowed.discard(name)
            text = _replace_name(text, name)

    def _sub(m: re.Match) -> str:
        name = m.group(1)
        if name in allowed:
            return name
        return "未入军册之众"

    return _UNREGISTERED_FORCE.sub(_sub, text)


def _repair_false_no_decree(text: str, decree_text: Optional[str]) -> str:
    """有正式诏书却写「本月无新诏」时，用诏书摘要补回核销章。"""
    d = (decree_text or "").strip()
    if not d or "无新诏" in d[:40]:
        return text
    if not re.search(r"诏书核销\s*\n(?:[一二三四五六七八九十]+、)?本月无新诏", text):
        return text
    summary = d.replace("敕曰：", "").replace("钦此。", "").replace("\n", "")
    if len(summary) > 72:
        summary = summary[:72] + "…"
    return re.sub(
        r"(诏书核销\s*\n)(?:[一二三四五六七八九十]+、)?本月无新诏。?",
        rf"\1本月旨意 — {summary}（结果：完成）",
        text,
        count=1,
    )


def _redact_uncommitted_extra_relief(text: str) -> str:
    """门控丢掉或未授权的加拨叙事；月度成例「西北赈济五万两」措辞保留。"""
    def _repl(m: re.Match) -> str:
        s = m.group(0)
        if "又损" in s or "临时拨付" in s or "洪承畴" in s:
            return "陕西无新诏加拨"
        return s

    text = _EXTRA_RELIEF_CLAIM.sub(_repl, text)
    text = re.sub(r"实到灾民之手不足两万两，?", "", text)
    text = re.sub(r"实到灾民不足两万两，?", "", text)
    text = re.sub(r"赈银实到不足两万两（拨五万）", "月度西北赈济照常", text)
    text = re.sub(r"赈银实到不足两万两", "月度西北赈济照常", text)
    return text


def _redact_dropped_economy(text: str, before: object) -> str:
    row = _as_dict(before)
    reason = str(row.get("reason") or "")
    blob = reason + _move_text(row)
    if any(tok in blob for tok in ("洪承畴", "再拨", "西北赈济", "临时拨付")):
        text = _redact_uncommitted_extra_relief(text)
        return text
    for phrase in _wanliang_to_liang_phrases(row.get("delta")):
        text = text.replace(f"截留银{phrase}", "截留银数未入太仓")
        text = text.replace(phrase, "未入档之银数")
    if "三千两" in reason or "三千两" in text:
        text = re.sub(r"查得截留银三千两[^，。；]*", "查核未见可入太仓之确数", text)
        text = text.replace("隐匿开封赈银三千两", "开封赈银账目未清")
    return text


def _redact_dropped_arms(text: str, before: object) -> str:
    """只抹抽取里那句入库/损毁理由，不删局势里对既有火器短缺的概括。"""
    data = _as_dict(before)
    reason = str(data.get("reason") or data.get("原因") or "")
    if reason and reason in text:
        text = text.replace(reason, "军备变动未入册")
    return text


def strip_secret_detail(narrative: str) -> str:
    """剥掉 <secret>…</secret> 详细暗线段（连同标签）。"""
    if not narrative:
        return narrative
    clean = _SECRET_DETAIL_RE.sub("", narrative)
    clean = clean.replace("<secret>", "").replace("</secret>", "")
    return _collapse_blank(clean)


def _collapse_blank(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def reconcile_report_with_gate(
    narrative: str,
    gate_log: Optional[Sequence[Dict[str, object]]] = None,
    *,
    secret_orders: Optional[Sequence[object]] = None,
    committed: Optional[object] = None,
    decree_text: Optional[str] = None,
) -> str:
    """生成给玩家看、并作为下月前文的邸报。"""
    text = strip_secret_detail(narrative or "")
    if not text:
        return text

    has_secrets = _has_active_secret_orders(secret_orders)
    if not has_secrets:
        text = _CHAPTER_UNKNOWN.sub("", text)
        text = _CHAPTER_SECRET_ORDERS.sub("", text)

    text = _repair_false_no_decree(text, decree_text)
    text = _redact_unregistered_forces(text, gate_log, committed)

    for item in _dropped(gate_log, "economy_moves"):
        text = _redact_dropped_economy(text, item.get("before"))

    for item in _dropped(gate_log, "arms_changes"):
        text = _redact_dropped_arms(text, item.get("before"))

    text = _redact_invented_shortfalls(text, committed)
    text = _redact_uncommitted_extra_relief(text)
    return _collapse_blank(text)
