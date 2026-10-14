# -*- coding: utf-8 -*-
"""诏书显式度 A/B/C/D：决定是否需要内部多假设补全。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from numeric_system.semantic_frame_extract import extract_semantic_frame_from_trace

_ZH_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
_DURATION_DIGIT = re.compile(r"(\d+)\s*季")
_DURATION_ZH = re.compile(r"([一二三四五])\s*季")
_ORDER_PREFIX = re.compile(r"(?:命|诏)\s*")
_DUAL_MINISTERS = re.compile(r"命\s*([\u4e00-\u9fff]{2,4})\s*[^，,]*[，,]\s*([\u4e00-\u9fff]{2,4})")
# 第一人名止于「统筹/督办…」前，避免吞「张居正统」；第二人名止于纠察类动词前
_DUAL_HEAD_TAIL_VERB = re.compile(
    r"命\s*([\u4e00-\u9fff]{2,3}?)(?=统筹|总领|督办|率领|协同|主持)"
    r"\s*[^，,]*[，,]\s*(.+?)(?=纠察|查办|督查|督察|巡察|审理)"
)


def get_l3_intent(trace: Dict[str, Any]) -> str:
    nlu = (trace or {}).get("nlu") or {}
    if isinstance(nlu, dict):
        source = str(nlu.get("intent_source") or "").strip()
        intent = str(nlu.get("intent_id") or "").strip()
        if source == "llm" and intent and intent not in ("unspecified", "none"):
            return intent
    for st in reversed(trace.get("stages") or []):
        if not isinstance(st, dict):
            continue
        if st.get("layer") != "layer3_llm":
            continue
        dsl = st.get("dsl") or {}
        if isinstance(dsl, dict):
            intent = str(dsl.get("intent") or "").strip()
            if intent:
                return intent
    return ""


def _executor_from_trace(trace: Dict[str, Any]) -> str:
    ex = trace.get("executor_resolution") or {}
    if isinstance(ex, dict):
        return str(ex.get("name") or "").strip()
    return ""


def _minister_names_from_data(minister_names: Optional[Set[str]]) -> Set[str]:
    return minister_names or set()


def extract_dual_ministers_in_text(edict_text: str, minister_names: Set[str]) -> List[str]:
    """命张居正统筹，海瑞纠察 —— 两名均须在大臣表中。"""
    text = edict_text or ""
    mv = _DUAL_HEAD_TAIL_VERB.search(text)
    if mv:
        a = mv.group(1).strip()
        raw_b = mv.group(2).strip()
        for ln in (4, 3, 2):
            if len(raw_b) >= ln:
                cand = raw_b[:ln]
                if cand in minister_names and a in minister_names:
                    return [a, cand]
        if raw_b in minister_names and a in minister_names:
            return [a, raw_b]
    m = _DUAL_MINISTERS.search(text)
    if not m:
        return []
    a, b = m.group(1).strip(), m.group(2).strip()
    if a in minister_names and b in minister_names:
        return [a, b]
    for ln in (4, 3, 2):
        if len(b) >= ln:
            cand = b[:ln]
            if cand in minister_names and a in minister_names:
                return [a, cand]
    return []


def extract_named_person_in_text(edict_text: str, minister_names: Set[str]) -> str:
    """命某某：按大臣表最长前缀匹配，避免「命张居正统筹」吞字。"""
    m = _ORDER_PREFIX.search(edict_text or "")
    if not m:
        return ""
    tail = edict_text[m.end() :]
    for cand in sorted(minister_names, key=len, reverse=True):
        if tail.startswith(cand):
            return cand
    return ""


def duration_explicit_from_text(edict_text: str) -> Tuple[Optional[int], bool]:
    """若正文能读出季数则 (quarters, True)，否则 (None, False)。"""
    text = edict_text or ""
    m = _DURATION_DIGIT.search(text)
    if m:
        try:
            n = int(m.group(1))
            return max(1, min(5, n)), True
        except ValueError:
            pass
    m2 = _DURATION_ZH.search(text)
    if m2:
        n = _ZH_NUM.get(m2.group(1), 0)
        if n:
            return n, True
    for phrase, n in (("一季", 1), ("两季", 2), ("三季", 3), ("四季", 4), ("五季", 5)):
        if phrase in text:
            return n, True
    # 避免「宜速修缮」类工程诏书被误判为当季办结（仅赈济类「速行/从速」收紧为 1 季）
    if re.search(r"(速行赈|速行救济|从速办|即刻施行)", text) or "从速" in text or "即刻" in text:
        return 1, True
    return None, False


def _task_signal_strength(
    *,
    domain: str,
    intent: str,
    edict_text: str,
) -> Tuple[bool, str]:
    """
    任务是否足够明确：领域非 general 或 intent 在政务意图表、或正文强关键词。
    返回 (task_clear, resolved_domain_for_hint).
    """
    from edict_execution_frame.domain_catalog import DOMAIN_TASK_CATALOG, _score_row

    text = edict_text or ""
    if intent in ("strict_governance", "disaster_relief", "tax_relief", "welfare"):
        return True, domain
    if domain and domain != "general":
        rows = DOMAIN_TASK_CATALOG.get(domain) or []
        for row in rows:
            sc, _ = _score_row(text, row, domain=domain)
            if sc >= 3:
                return True, domain
        # 有明确领域但无关键词仍算「领域任务可辨」
        return True, domain
    # general：看 general 目录下非 steady 的关键词
    for row in DOMAIN_TASK_CATALOG.get("general", []):
        if row.task_key == "steady_governance":
            continue
        sc, _ = _score_row(text, row, domain="general")
        if sc >= 3:
            return True, "general"
    if re.search(
        r"(肃贪|反贪|贪墨|赈济|水患|河工|堤防|边患|整军|劝农|农桑|陂塘|改稻为桑|农田水利|春前给散|逋欠|追比|加派|市易|免役|均输|裁冗|钱粮|赋役|宫禁|内帑|停罢)",
        text,
    ):
        return True, domain
    return False, domain


def classify_edict_explicitness(
    edict_text: str,
    parse_trace: Dict[str, Any],
    *,
    edict_executor_name: str = "",
    minister_names: Optional[Set[str]] = None,
    resolved_domain: str = "",
) -> str:
    """
    A：执行者、任务、时长均可在诏书/解析中锁定。
    B：执行者明确，任务或时长至少一项模糊。
    C：任务/领域明确，执行者未锁定。
    D：其余模糊情况。
    """
    trace = parse_trace or {}
    names = _minister_names_from_data(minister_names)

    dual = extract_dual_ministers_in_text(edict_text or "", names)
    ex_name = ""
    if len(dual) == 2:
        executor_clear = True
        ex_name = dual[0]
    else:
        executor_clear = False
        ex_name = (edict_executor_name or "").strip()
        if not ex_name:
            ex_name = _executor_from_trace(trace)
        if not ex_name:
            ex_name = extract_named_person_in_text(edict_text or "", names)

    sem = extract_semantic_frame_from_trace(edict_text or "", trace)
    intent = get_l3_intent(trace)
    dom = (resolved_domain or "").strip()
    if not dom:
        from edict_execution_frame.domain_catalog import resolve_domain_from_semantic_and_text

        dom = resolve_domain_from_semantic_and_text(
            trace_domain=str(sem.domain or trace.get("edict_category") or "general"),
            l3_intent=intent,
            edict_text=edict_text or "",
        )
    task_clear, _ = _task_signal_strength(
        domain=str(sem.domain or "general"),
        intent=intent,
        edict_text=edict_text or "",
    )
    _, dur_explicit = duration_explicit_from_text(edict_text or "")

    if len(dual) != 2:
        executor_clear = bool(ex_name)

    # 领域仍落在 general、无承办、无显式季数：视为 D（泛化吏治 rhetoric），走内部消歧。
    if not executor_clear and not dur_explicit and dom == "general":
        return "D"

    if executor_clear and task_clear and dur_explicit:
        return "A"
    if executor_clear and (not task_clear or not dur_explicit):
        return "B"
    if (not executor_clear) and task_clear:
        return "C"
    return "D"
