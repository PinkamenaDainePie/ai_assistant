import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple



from .effects import effects_from_edict_text

from .edict_categories import (

    apply_category_to_effects,

    category_label_zh,

    normalize_edict_categories,

    normalize_edict_category,

    select_primary_category,

)

from .edict_rules import run_category_pack

from .loader import load_numeric_data

from .metric_schema import METRIC_SCHEMA, clamp_effect_delta, get_metric_meta
from .candidate_scorer import merge_effects_weighted, score_candidates
from .safety_guardrail import apply_safety_guardrail
from .text_normalizer import normalize_edict_text
from .llm_intent_schema import apply_degree_hint, build_intent_whitelist, parse_llm_dsl_json
from .llm_intent_mapper import build_intent_effect_templates, map_dsl_to_effects

from .executor_modifiers import (
    apply_executor_effect_modifications,
    format_executor_prompt_block,
    infer_executor_context_from_edict,
)
from .types import NumericData

from nlu_layer.intent_catalog import INTENT_CATALOG
from nlu_layer.intent_classifier import sim_score as _sim_score
from nlu_layer.pipeline import merge_l3_into_nlu_trace, run_edict_nlu


def _l3_http_config() -> Dict[str, Any]:
    """诏书 L3 与人物对话共用 .env；本地 Ollama + 通义 Key 并存时默认走通义解析。"""
    try:
        from renwu_module.config import (
            DASHSCOPE_API_BASE,
            DASHSCOPE_API_KEY,
            DEFAULT_LLM_MODEL,
            LLM_REQUEST_TIMEOUT,
            WANGANSHI_API_BASE,
            WANGANSHI_API_KEY,
            WANGANSHI_LLM_MODEL,
        )
    except ImportError:
        DASHSCOPE_API_BASE = os.getenv(
            "DASHSCOPE_API_BASE",
            os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen-plus")
        WANGANSHI_API_BASE = os.getenv("WANGANSHI_API_BASE") or DASHSCOPE_API_BASE
        WANGANSHI_API_KEY = os.getenv("WANGANSHI_API_KEY") or DASHSCOPE_API_KEY
        WANGANSHI_LLM_MODEL = os.getenv("WANGANSHI_LLM_MODEL") or DEFAULT_LLM_MODEL
        LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "300"))

    profile = str(os.getenv("EDICT_L3_PROFILE") or "auto").strip().lower()
    dash_key = (DASHSCOPE_API_KEY or "").strip()
    dash_ok = bool(dash_key) and "placeholder" not in dash_key.lower() and "请替换" not in dash_key
    wang_base = (WANGANSHI_API_BASE or "").strip()
    local_wang = any(x in wang_base for x in ("127.0.0.1", "localhost", ":11434"))

    if profile in ("dashscope", "qwen", "cloud"):
        api_key, base_url, model, tag = dash_key, DASHSCOPE_API_BASE, DEFAULT_LLM_MODEL, "dashscope"
    elif profile in ("wanganshi", "ollama", "local"):
        api_key, base_url, model, tag = WANGANSHI_API_KEY, WANGANSHI_API_BASE, WANGANSHI_LLM_MODEL, "wanganshi"
    elif local_wang and dash_ok:
        api_key, base_url, model, tag = dash_key, DASHSCOPE_API_BASE, DEFAULT_LLM_MODEL, "dashscope_auto"
    else:
        api_key, base_url, model, tag = WANGANSHI_API_KEY, WANGANSHI_API_BASE, WANGANSHI_LLM_MODEL, "wanganshi_default"

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "timeout_sec": float(LLM_REQUEST_TIMEOUT or 300),
        "profile": tag,
    }





METRIC_KEYS = set(METRIC_SCHEMA.keys())





def _cn_to_int(token: str) -> int:

    if not token:

        return 0

    token = token.strip()

    if token.isdigit():

        return int(token)



    nums = {

        "零": 0,

        "一": 1,

        "二": 2,

        "两": 2,

        "三": 3,

        "四": 4,

        "五": 5,

        "六": 6,

        "七": 7,

        "八": 8,

        "九": 9,

    }

    units = {"十": 10, "百": 100, "千": 1000, "万": 10000, "亿": 100000000}



    total = 0

    section = 0

    number = 0

    for ch in token:

        if ch in nums:

            number = nums[ch]

        elif ch in units:

            u = units[ch]

            if u >= 10000:

                section = (section + (number or 1)) * u

                total += section

                section = 0

            else:

                section += (number or 1) * u

            number = 0

    return total + section + number





def _parse_amount_liang(text: str) -> float:

    t = (text or "").strip()

    if not t:

        return 0.0



    m = re.search(r"(\d+(?:\.\d+)?)\s*(亿|万)?", t)

    if m:

        base = float(m.group(1))

        unit = m.group(2) or ""

        if unit == "万":

            base *= 10000

        elif unit == "亿":

            base *= 100000000

        return base



    m2 = re.search(r"([零一二两三四五六七八九十百千万亿]+)", t)

    if m2:

        return float(_cn_to_int(m2.group(1)))

    return 0.0





def _make_effect(key: str, value: float) -> Dict[str, Any]:

    return {"action": "add_metric", "key": key, "value": round(float(value), 2)}





def _global_treasury_regex(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

    """无表时的通用银两/税关键词，或有表时仅 other 板块使用。"""

    effects: List[Dict[str, Any]] = []

    trace: Dict[str, Any] = {

        "layer": "global_treasury_regex",

        "hits": [],

        "confidence": 0.0,

    }

    t = (text or "").strip()

    if not t:

        return effects, trace



    patterns = [

        (r"(拨银|拨款|发银|给.*?银|赈银)([^，。；]*)", "treasury_balance", -1.0, "allocate_funds"),

        (r"(加税|加派|加征)([^，。；]*)", "treasury_balance", 1.0, "raise_tax"),

        (r"(蠲免|免税|减税)([^，。；]*)", "treasury_balance", -1.0, "tax_relief"),

    ]



    for pat, key, sign, name in patterns:

        for m in re.finditer(pat, t):

            seg = "".join(g or "" for g in m.groups())

            amount = _parse_amount_liang(seg)

            if amount <= 0:

                amount = 50000.0

            effects.append(_make_effect(key, sign * amount))

            if key == "treasury_balance" and sign < 0:

                effects.append(_make_effect("public_support", 0.8))

                effects.append(_make_effect("unrest", -0.5))

            trace["hits"].append({"rule": name, "segment": seg, "amount": amount})



    hit_count = len(trace["hits"])

    base = 0.45 if effects else 0.0

    trace["confidence"] = min(0.98, base + hit_count * 0.15)

    return effects, trace





def _layer1_combined(

    text: str,

    *,

    numeric_data: Optional[NumericData],

    edict_category_ids: List[str],

) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

    """

    L1：effects_from_edict_text + 板块规则包（有表）+ 条件性全局银两正则。

    """

    t0 = time.perf_counter()
    effects = effects_from_edict_text(text)

    trace: Dict[str, Any] = {

        "layer": "layer1_combined",

        "legacy_effects": True,

        "category_ids": edict_category_ids,

        "category_pack": None,

        "global_treasury": None,

    }



    t = (text or "").strip()

    cat_ids = [normalize_edict_category(x) for x in (edict_category_ids or [])]
    if not cat_ids:
        cat_ids = ["other"]
    cat_id = select_primary_category(cat_ids)



    if numeric_data is not None:

        pack_effects, pack_trace = run_category_pack(text, numeric_data, cat_ids)

        effects.extend(pack_effects)

        trace["category_pack"] = pack_trace



    use_global = False

    if numeric_data is None:

        use_global = True

    elif cat_id == "other":

        use_global = True

    elif cat_id in ("internal", "diplomacy", "military"):

        pack_empty = not trace.get("category_pack") or not trace["category_pack"].get("hits")

        if pack_empty and t and re.search(r"(拨银|拨款|加税|蠲免|免税|减税|加征|赈银)", t):

            use_global = True



    if use_global:

        ge, gtr = _global_treasury_regex(text)

        effects.extend(ge)

        trace["global_treasury"] = gtr



    hit_total = 0

    if trace.get("category_pack") and trace["category_pack"].get("hits"):

        hit_total += len(trace["category_pack"]["hits"])

    if trace.get("global_treasury") and trace["global_treasury"].get("hits"):

        hit_total += len(trace["global_treasury"]["hits"])

    conf = min(0.98, 0.35 + hit_total * 0.12 + (0.1 if effects_from_edict_text(text) else 0))

    if hit_total > 0:

        conf = max(conf, 0.76)

    trace["confidence"] = conf

    trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return effects, trace





def _layer2_semantic(

    text: str,

    edict_category_ids: List[str],

) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

    t0 = time.perf_counter()
    t = (text or "").strip()

    trace: Dict[str, Any] = {
        "layer": "layer2_semantic",
        "legacy_effects": True,
        "hits": [],
        "confidence": 0.0,
        "diagnostics": {},
    }

    if not t:

        return [], trace



    cids = [normalize_edict_category(x) for x in (edict_category_ids or [])]
    if not cids:
        cids = ["other"]

    effects: List[Dict[str, Any]] = []

    best_score = 0.0

    skipped_by_category = 0
    low_score_count = 0
    for item in INTENT_CATALOG:

        allowed = item.get("categories")

        if allowed is not None and not any(cid in allowed for cid in cids):
            skipped_by_category += 1

            continue

        score = _sim_score(t, item["phrases"])

        if score < 0.50:
            low_score_count += 1

            continue

        best_score = max(best_score, score)

        for key, val in item["effects"]:

            effects.append(_make_effect(key, val))

        trace["hits"].append({"intent": item["intent"], "score": round(score, 3)})



    trace["confidence"] = round(best_score, 3)

    trace["edict_category_filter"] = cids
    trace["diagnostics"] = {
        "catalog_size": len(INTENT_CATALOG),
        "skipped_by_category": skipped_by_category,
        "below_score_threshold": low_score_count,
        "score_threshold": 0.50,
        "reason_if_zero": (
            "no_intent_over_threshold_or_filtered"
            if best_score <= 0.0
            else ""
        ),
    }

    trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return effects, trace


def _parser_nlu_separated_enabled() -> bool:
    return _env_flag("PARSER_NLU_SEPARATED", default=True)


def _layer2_nlu_trace(
    nlu_trace: Dict[str, Any],
    edict_category_ids: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """L2 意图由 NLU 承担；本层仅留 trace，不产 effects。"""
    nlu = nlu_trace or {}
    cids = [normalize_edict_category(x) for x in (edict_category_ids or [])] or ["other"]
    return [], {
        "layer": "layer2_semantic",
        "replaced_by": "nlu",
        "legacy_effects": False,
        "intent_id": str(nlu.get("intent_id") or ""),
        "intent_source": str(nlu.get("intent_source") or ""),
        "domain_hint": str(nlu.get("domain_hint") or ""),
        "confidence": float(nlu.get("confidence") or 0.0),
        "edict_category_filter": cids,
        "hits": (
            [{"intent": nlu.get("intent_id"), "score": nlu.get("confidence"), "source": "nlu"}]
            if nlu.get("intent_id")
            else []
        ),
    }


def _finish_nlu_separated_parse(
    trace: Dict[str, Any],
    *,
    sanitize_warnings: List[Dict[str, Any]],
    t_all: float,
    l1_trace: Dict[str, Any],
    l2_trace: Dict[str, Any],
    l3_trace: Dict[str, Any],
    use_l3: bool,
    cat_id: str,
    cat_ids: List[str],
    use_legacy_category_multiplier: bool,
    effective_executor_ctx: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    nlu = trace.get("nlu") or {}
    trace["parser_mode_separated"] = True
    trace["decision_trace"] = {
        "mode": "nlu_separated",
        "intent_id": nlu.get("intent_id"),
        "intent_source": nlu.get("intent_source"),
        "domain_hint": nlu.get("domain_hint"),
        "parse_effects_policy": "frame_resolver_only",
        "l1_effects_suppressed": bool(l1_trace.get("effects_suppressed")),
        "l2_replaced_by_nlu": bool(l2_trace.get("replaced_by") == "nlu"),
        "l3_effects_suppressed": bool((l3_trace or {}).get("effects_suppressed")),
        "l3_invoked": bool(use_l3),
    }
    trace["final_layer"] = "nlu_separated"
    trace["final_confidence"] = round(float(nlu.get("confidence") or 0.0), 4)
    eff, meta = apply_category_to_effects([], cat_id, use_legacy_multiplier=use_legacy_category_multiplier)
    if effective_executor_ctx:
        eff, ex_trace = apply_executor_effect_modifications(eff, effective_executor_ctx, cat_id)
        trace["executor_modifier"] = ex_trace
    trace["edict_category"] = meta["resolved_id"]
    trace["edict_categories"] = cat_ids
    trace["edict_categories_label_zh"] = [category_label_zh(x) for x in cat_ids]
    trace["edict_category_label_zh"] = meta["label_zh"]
    trace["category_modifier"] = meta
    trace["sanitize_warnings"] = sanitize_warnings
    trace["latency_total_ms"] = round((time.perf_counter() - t_all) * 1000.0, 3)
    return {"effects": eff, "trace": trace}


def _sanitize_effects(
    effects: List[Dict[str, Any]],
    warnings: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:

    out = []

    for e in effects:

        if e.get("action") != "add_metric":

            continue

        key = str(e.get("key", "")).strip()

        if key not in METRIC_KEYS:

            continue

        try:

            val = float(e.get("value", 0.0))

        except (TypeError, ValueError):

            continue

        meta = get_metric_meta(key)
        if meta is None:
            continue
        if abs(val) > 0 and meta.kind == "resource" and abs(val) < meta.tiny_delta_hint:
            if warnings is not None:
                warnings.append(
                    {
                        "type": "tiny_resource_delta_warning",
                        "key": key,
                        "value": round(val, 4),
                        "tiny_delta_hint": meta.tiny_delta_hint,
                        "unit": meta.unit,
                    }
                )
        val, clamp_warning = clamp_effect_delta(key, val)
        if clamp_warning is not None and warnings is not None:
            warnings.append(clamp_warning)

        out.append({"action": "add_metric", "key": key, "value": round(val, 2)})

    return out





def _layer3_llm(

    text: str,

    *,

    edict_category_hint_zh: str = "",
    degree_hint: str = "",
    executor_prompt_block: str = "",

) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

    trace: Dict[str, Any] = {
        "layer": "layer3_llm",
        "hits": [],
        "confidence": 0.0,
        "dsl": None,
        "dsl_parse_trace": None,
        "intent_mapping_trace": None,
        "guardrail_trace": None,
        "raw_output_preview": "",
    }

    t = (text or "").strip()

    if not t:
        return [], trace

    # Offline/debug override: bypass network and treat this as LLM output JSON.
    override = (os.getenv("LLM_DSL_OVERRIDE_JSON") or "").strip()
    if override:
        t0 = time.perf_counter()
        content = override
        trace["raw_output_preview"] = content[:600]
        allowed_intents = build_intent_whitelist(INTENT_CATALOG)
        dsl, dsl_trace = parse_llm_dsl_json(content, allowed_intents=allowed_intents)
        trace["dsl_parse_trace"] = dsl_trace
        if dsl is None:
            trace["hits"].append({"reason": "dsl_parse_failed", "error": dsl_trace.get("error")})
            trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
            return [], trace

        dsl2, hint_trace = apply_degree_hint(
            dsl,
            degree_hint=degree_hint,
            degree_provided=bool(dsl_trace.get("degree_provided")),
            parse_error=str(dsl_trace.get("error") or ""),
        )
        trace["dsl"] = {"intent": dsl2.intent, "degree": dsl2.degree}
        trace["degree_hint_trace"] = hint_trace
        templates = build_intent_effect_templates(INTENT_CATALOG)
        mapped_effects, mapping_trace = map_dsl_to_effects(dsl2, templates=templates)
        trace["intent_mapping_trace"] = mapping_trace
        safe_effects, guardrail_trace = apply_safety_guardrail(mapped_effects)
        trace["guardrail_trace"] = guardrail_trace

        effects = _sanitize_effects(safe_effects)
        trace["confidence"] = 0.82 if effects else 0.0
        trace["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        trace["hits"].append(
            {
                "dsl": trace["dsl"],
                "mapped_count": len(mapped_effects),
                "safe_count": len(effects),
                "override_used": True,
            }
        )
        return effects, trace

    http_cfg = _l3_http_config()
    api_key = str(http_cfg.get("api_key") or "").strip()
    base_url = str(http_cfg.get("base_url") or "").strip()
    model = str(http_cfg.get("model") or "qwen-plus").strip()
    timeout_sec = float(http_cfg.get("timeout_sec") or 300)
    trace["http_profile"] = http_cfg.get("profile")
    trace["http_model"] = model
    trace["http_base"] = base_url

    if not api_key:
        trace["hits"].append({"reason": "no_api_key", "profile": http_cfg.get("profile")})
        return [], trace

    url = base_url.rstrip("/") + "/chat/completions"

    cat_line = ""

    if (edict_category_hint_zh or "").strip():

        cat_line = f"诏书板块：{edict_category_hint_zh.strip()}。"

    exec_line = ""
    if (executor_prompt_block or "").strip():
        exec_line = executor_prompt_block.strip() + "\n"

    allowed_intents = build_intent_whitelist(INTENT_CATALOG)
    prompt = (
        "你是诏书意图解析器。你的任务：把输入诏书归类为一个【意图intent】与一个【程度degree】。\n"
        "你必须只输出一个JSON对象，不要输出解释、不要输出多余字符。\n"
        + cat_line
        + exec_line
        + "JSON结构严格为：{\"intent\": string, \"degree\": \"slightly\"|\"moderately\"|\"heavily\"}。\n"
        + "intent 必须从以下白名单中选择其一："
        + ",".join(allowed_intents)
        + "。\n"
        + "degree 表示力度：slightly(轻) moderately(中) heavily(重)。\n"
        + "若诏书涉及委派臣工办事：政令成效与成败不由你裁定，下季由朝政模拟系统结算；"
        "你只输出 intent 与 degree 供当期归类，不要编造执行结果或成功概率。\n"
        + "输入："
        + t
    )

    payload = {

        "model": model,

        "messages": [{"role": "user", "content": prompt}],

        "temperature": 0.1,

        "max_tokens": 300,

    }

    req = urllib.request.Request(

        url,

        data=json.dumps(payload).encode("utf-8"),

        headers={

            "Content-Type": "application/json",

            "Authorization": f"Bearer {api_key}",

        },

        method="POST",

    )



    try:

        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:

            raw = resp.read().decode("utf-8", errors="ignore")

        obj = json.loads(raw)

        content = (

            (((obj.get("choices") or [{}])[0].get("message") or {}).get("content"))

            or ""

        ).strip()

        trace["raw_output_preview"] = content[:600]

        dsl, dsl_trace = parse_llm_dsl_json(content, allowed_intents=allowed_intents)
        trace["dsl_parse_trace"] = dsl_trace
        if dsl is None:
            trace["hits"].append({"reason": "dsl_parse_failed", "error": dsl_trace.get("error")})
            return [], trace

        dsl2, hint_trace = apply_degree_hint(
            dsl,
            degree_hint=degree_hint,
            degree_provided=bool(dsl_trace.get("degree_provided")),
            parse_error=str(dsl_trace.get("error") or ""),
        )
        trace["dsl"] = {"intent": dsl2.intent, "degree": dsl2.degree}
        trace["degree_hint_trace"] = hint_trace
        templates = build_intent_effect_templates(INTENT_CATALOG)
        mapped_effects, mapping_trace = map_dsl_to_effects(dsl2, templates=templates)
        trace["intent_mapping_trace"] = mapping_trace

        # Safety guardrail (LLM output always goes through it)
        safe_effects, guardrail_trace = apply_safety_guardrail(mapped_effects)
        trace["guardrail_trace"] = guardrail_trace

        effects = _sanitize_effects(safe_effects)
        trace["confidence"] = 0.62 if effects else 0.0
        trace["hits"].append(
            {
                "dsl": trace["dsl"],
                "mapped_count": len(mapped_effects),
                "safe_count": len(effects),
            }
        )
        return effects, trace

    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:

        trace["hits"].append({"error": str(exc)})

        return [], trace

    return [], trace


def _parser_v2_enabled() -> bool:
    raw = (os.getenv("PARSER_V2_ENABLED") or "").strip().lower()
    if not raw:
        return False
    return raw in ("1", "true", "yes", "on")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _infer_difficulty(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "easy"
    if re.search(r"(但|而不是|不要太|不要|同时|平衡|一面|另一面|兼顾|稍微|有点)", t):
        return "hard"
    if re.search(r"(适度|略微|提高一点|稍加|酌情)", t):
        return "medium"
    if len(t) >= 24:
        return "medium"
    return "easy"


def _is_fuzzy_text(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.search(r"(稍微|有点|不要太|但|而不是|尽量|酌情|适度)", t))


def _text_complexity_signals(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    has_constraint = bool(re.search(r"(不要|不可|勿|不得|但|而不是|除非)", t))
    has_multi_goal = bool(re.search(r"(同时|并且|一面|另一面|兼顾|且)", t))
    has_degree = bool(re.search(r"(稍微|略微|适度|大力|大幅|显著)", t))
    score = 0.0
    if has_constraint:
        score += 1.2
    if has_multi_goal:
        score += 1.1
    if has_degree:
        score += 0.8
    if len(t) >= 26:
        score += 0.4
    return {
        "has_constraint": has_constraint,
        "has_multi_goal": has_multi_goal,
        "has_degree": has_degree,
        "semantic_complexity_score": round(score, 3),
    }


def _has_policy_action_signal(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(
        re.search(
            r"(加税|减税|增税|免税|蠲免|赈灾|赈济|开仓|募兵|裁军|扩军|修船|海防|边防|整饬|整顿|清查|惩治|罢兵|和议|通商|纳贡|拨款|拨银|减免|增征|停征)",
            t,
        )
    )


def _is_none_like_text(text: str) -> bool:
    """
    Heuristic for generic/empty instructions that should produce no policy effect.
    Used to suppress false positives in single_l3 mode.
    """
    t = (text or "").strip()
    if not t:
        return True
    # Too short or mostly punctuation/latin noise
    if len(t) <= 2:
        return True
    if re.fullmatch(r"[A-Za-z0-9\s\W_]+", t):
        return True
    # Generic/non-policy phrasing patterns
    if re.search(r"(务必|妥善|慎之又慎|从长计议|酌情处理|严加|切实|认真|抓紧|落实|遵行|照办)$", t):
        return True
    if re.search(r"(务必|妥善|慎之又慎|从长计议|酌情处理|认真|抓紧|落实|遵行|照办).{0,8}(此事|此令|之事|相关事宜|诸事)", t):
        return True
    # Pure degree/attitude words without action
    if re.fullmatch(r"(稍微|略|适度|大力|大幅|显著|有点|尽量|酌情|适当)[。！!？?]*", t):
        return True
    return False


def _effect_sign_map(effects: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in effects or []:
        if e.get("action") != "add_metric":
            continue
        key = str(e.get("key") or "").strip()
        if not key:
            continue
        try:
            v = float(e.get("value") or 0.0)
        except (TypeError, ValueError):
            continue
        out[key] = 1 if v > 0 else (-1 if v < 0 else 0)
    return out


def _candidate_intent(candidate: Optional[Dict[str, Any]]) -> str:
    if not candidate:
        return "none"
    src = str(candidate.get("source_layer") or "")
    rt = candidate.get("raw_trace") or {}
    if src == "layer3_llm":
        return str((rt.get("dsl") or {}).get("intent") or "none")
    if src == "layer2_semantic":
        hits = rt.get("hits") or []
        return str((hits[0] if hits else {}).get("intent") or "none")
    return "none"


def _candidate_completeness(candidate: Optional[Dict[str, Any]]) -> float:
    if not candidate:
        return 0.0
    effects = candidate.get("effects") or []
    src = str(candidate.get("source_layer") or "")
    base = float(min(5, len(effects))) * 0.35
    if src == "layer3_llm":
        dsl = ((candidate.get("raw_trace") or {}).get("dsl") or {})
        if dsl.get("intent"):
            base += 0.7
        if dsl.get("degree"):
            base += 0.5
    return round(base, 4)


def _analyze_conflict(
    *,
    top_l3: Optional[Dict[str, Any]],
    top_non_l3: Optional[Dict[str, Any]],
    scoring_context: Dict[str, Any],
    score_meta: Dict[str, Any],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "should_conflict": False,
        "actually_conflict": bool(score_meta.get("conflicts")),
        "conflict_score": 0.0,
        "conflict_threshold": 0.6,
        "intent_conflict": False,
        "direction_conflict": False,
        "completeness_conflict": False,
        "l3_completeness": 0.0,
        "other_completeness": 0.0,
        "reason_tags": [],
        "missed_conflict_reason": "",
    }
    if not top_l3 or not top_non_l3:
        return out
    l3_intent = _candidate_intent(top_l3)
    other_intent = _candidate_intent(top_non_l3)
    intent_conflict = (
        l3_intent != "none" and other_intent != "none" and l3_intent != other_intent
    )
    l3_dirs = _effect_sign_map(top_l3.get("effects") or [])
    other_dirs = _effect_sign_map(top_non_l3.get("effects") or [])
    shared = set(l3_dirs.keys()) & set(other_dirs.keys())
    direction_conflict = any(l3_dirs[k] != other_dirs[k] for k in shared)
    l3_comp = _candidate_completeness(top_l3)
    other_comp = _candidate_completeness(top_non_l3)
    completeness_conflict = (l3_comp - other_comp) >= 0.9

    out["intent_conflict"] = intent_conflict
    out["direction_conflict"] = direction_conflict
    out["completeness_conflict"] = completeness_conflict
    out["l3_completeness"] = l3_comp
    out["other_completeness"] = other_comp

    if intent_conflict:
        out["reason_tags"].append("intent")
    if direction_conflict:
        out["reason_tags"].append("direction")
    if completeness_conflict:
        out["reason_tags"].append("completeness")
    if float(scoring_context.get("semantic_complexity_score") or 0.0) >= 1.5:
        out["reason_tags"].append("complexity")

    # Continuous conflict confidence, then threshold by difficulty bucket.
    c_score = (
        (0.4 if intent_conflict else 0.0)
        + (0.3 if direction_conflict else 0.0)
        + (0.3 if completeness_conflict else 0.0)
    )
    if float(scoring_context.get("semantic_complexity_score") or 0.0) >= 1.5:
        c_score += 0.1
    c_score = max(0.0, min(1.0, c_score))
    d = str(scoring_context.get("difficulty") or "medium").lower()
    thresholds = {
        "easy": float(scoring_context.get("conflict_threshold_easy") or 0.45),
        "medium": float(scoring_context.get("conflict_threshold_medium") or 0.35),
        "hard": float(scoring_context.get("conflict_threshold_hard") or 0.25),
        "edge": float(scoring_context.get("conflict_threshold_hard") or 0.25),
    }
    t = thresholds.get(d, thresholds["medium"])
    out["conflict_score"] = round(c_score, 4)
    out["conflict_threshold"] = round(t, 4)
    if bool(scoring_context.get("conflict_score_enabled", True)):
        out["should_conflict"] = bool(c_score >= t)
    else:
        out["should_conflict"] = bool(
            intent_conflict
            or direction_conflict
            or completeness_conflict
            or (float(scoring_context.get("semantic_complexity_score") or 0.0) >= 2.2)
        )
    if out["should_conflict"] and not out["actually_conflict"]:
        out["missed_conflict_reason"] = "score_triggered_but_no_directional_conflict"
    elif (not out["should_conflict"]) and c_score > 0:
        out["missed_conflict_reason"] = "score_below_threshold"
    return out


def _candidate_from_layer(
    layer_name: str,
    *,
    effects: List[Dict[str, Any]],
    layer_trace: Dict[str, Any],
    categories: List[str],
) -> Dict[str, Any]:
    hit_count = 0
    evidence_items: List[Dict[str, Any]] = []
    if layer_name == "layer1_combined":
        pack = (layer_trace.get("category_pack") or {})
        pack_hits = pack.get("hits") or []
        gt_hits = ((layer_trace.get("global_treasury") or {}).get("hits")) or []
        hit_count = len(pack_hits) + len(gt_hits)
        evidence_items.extend(pack_hits[:20])
        evidence_items.extend(gt_hits[:20])
    elif layer_name == "layer2_semantic":
        l2_hits = layer_trace.get("hits") or []
        hit_count = len(l2_hits)
        evidence_items.extend(l2_hits[:20])
    elif layer_name == "layer3_llm":
        l3_hits = layer_trace.get("hits") or []
        hit_count = len(l3_hits)
        evidence_items.extend(l3_hits[:20])
    return {
        "source_layer": layer_name,
        "effects": effects,
        "confidence": float(layer_trace.get("confidence") or 0.0),
        "categories": list(categories),
        "evidence": {"hit_count": hit_count, "items": evidence_items},
        "risk_flags": [],
        "raw_trace": layer_trace,
    }


def _merge_candidates(
    scored_candidates: List[Dict[str, Any]],
    *,
    strategy: str,
) -> List[Dict[str, Any]]:
    if not scored_candidates:
        return []
    if strategy == "weighted_merge":
        return merge_effects_weighted(scored_candidates)
    best = scored_candidates[0]
    return list(best.get("effects") or [])


def _pick_top_by_layer(
    scored_candidates: List[Dict[str, Any]], layer_name: str
) -> Optional[Dict[str, Any]]:
    for c in scored_candidates:
        if str(c.get("source_layer") or "") == layer_name:
            return c
    return None


def _resolve_conflict(
    scored_candidates: List[Dict[str, Any]],
    *,
    scoring_context: Dict[str, Any],
    conflict_analysis: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Resolve l3 vs non-l3 conflict with AI-dominant rules.
    Returns (chosen_candidate, resolver_trace).
    """
    trace: Dict[str, Any] = {"used": False, "reason": "none"}
    if not scored_candidates:
        return None, trace
    top_l3 = _pick_top_by_layer(scored_candidates, "layer3_llm")
    top_non_l3 = next(
        (c for c in scored_candidates if str(c.get("source_layer")) != "layer3_llm"),
        None,
    )
    if top_l3 is None or top_non_l3 is None:
        return None, trace
    if not bool(conflict_analysis.get("should_conflict")):
        trace["reason"] = "no_conflict_detected"
        return None, trace
    trace["used"] = True
    d = str(scoring_context.get("difficulty") or "").lower()
    is_fuzzy = bool(scoring_context.get("is_fuzzy"))
    complexity = float(scoring_context.get("semantic_complexity_score") or 0.0)
    l3_count = len(top_l3.get("effects") or [])
    other_count = len(top_non_l3.get("effects") or [])
    if d in ("hard", "edge"):
        trace["reason"] = "hard_prefers_l3"
        return top_l3, trace
    if is_fuzzy:
        trace["reason"] = "fuzzy_prefers_l3"
        return top_l3, trace
    if bool(conflict_analysis.get("completeness_conflict")):
        trace["reason"] = "completeness_prefers_l3"
        return top_l3, trace
    if bool(conflict_analysis.get("direction_conflict")) and complexity >= 1.5:
        trace["reason"] = "direction_plus_complexity_prefers_l3"
        return top_l3, trace
    if l3_count > other_count:
        trace["reason"] = "l3_more_complete"
        return top_l3, trace
    bias = 0.08 + (0.08 if complexity >= 1.5 else 0.0)
    l3_score = float(top_l3.get("score") or 0.0) + bias
    other_score = float(top_non_l3.get("score") or 0.0)
    trace["reason"] = "biased_argmax"
    trace["l3_bias"] = round(bias, 4)
    trace["l3_biased_score"] = round(l3_score, 4)
    trace["other_score"] = round(other_score, 4)
    return (top_l3 if l3_score >= other_score else top_non_l3), trace


def _should_trigger_l3_advantage(
    scoring_context: Dict[str, Any],
    conflict_analysis: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Non-conflict path trigger: when semantics are complex, give L3 a chance.
    """
    if bool(conflict_analysis.get("should_conflict")):
        return False, "conflict_path"
    complexity = float(scoring_context.get("semantic_complexity_score") or 0.0)
    has_constraint = bool(scoring_context.get("has_constraint"))
    has_multi_goal = bool(scoring_context.get("has_multi_goal"))
    has_degree = bool(scoring_context.get("has_degree"))
    difficulty = str(scoring_context.get("difficulty") or "").lower()
    if complexity >= 2.2:
        return True, "high_complexity"
    if (has_constraint and has_multi_goal) or (has_constraint and has_degree):
        return True, "constraint_combo"
    if difficulty in ("hard", "edge") and (has_multi_goal or has_constraint):
        return True, "hard_complex_pattern"
    return False, "not_triggered"


def _compute_l3_trust_score(
    *,
    scoring_context: Dict[str, Any],
    conflict_analysis: Dict[str, Any],
    top_l3: Optional[Dict[str, Any]],
    top_non_l3: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Estimate probability-like trust score for choosing L3 in current case.
    Returns score and decomposed features for observability.
    """
    complexity = float(scoring_context.get("semantic_complexity_score") or 0.0)
    has_constraint = 1.0 if bool(scoring_context.get("has_constraint")) else 0.0
    has_multi_goal = 1.0 if bool(scoring_context.get("has_multi_goal")) else 0.0
    has_degree = 1.0 if bool(scoring_context.get("has_degree")) else 0.0
    is_fuzzy = 1.0 if bool(scoring_context.get("is_fuzzy")) else 0.0
    conflict_score = float(conflict_analysis.get("conflict_score") or 0.0)
    completeness_gap = float(conflict_analysis.get("l3_completeness") or 0.0) - float(
        conflict_analysis.get("other_completeness") or 0.0
    )

    l3_conf = float((top_l3 or {}).get("confidence") or 0.0)
    other_conf = float((top_non_l3 or {}).get("confidence") or 0.0)
    conf_margin = l3_conf - other_conf

    score = (
        0.10 * min(1.0, complexity / 3.0)
        + 0.05 * has_constraint
        + 0.05 * has_multi_goal
        + 0.04 * has_degree
        + 0.04 * is_fuzzy
        + 0.12 * conflict_score
        + 0.10 * max(0.0, min(1.0, completeness_gap / 1.5))
        + 0.10 * max(0.0, min(1.0, (conf_margin + 1.0) / 2.0))
    )
    # difficulty prior: hard/edge should trust L3 more.
    d = str(scoring_context.get("difficulty") or "").lower()
    if d in ("hard", "edge"):
        score += 0.06
    elif d == "easy":
        score -= 0.05
    score = max(0.0, min(1.0, score))
    return {
        "trust_score": round(score, 4),
        "features": {
            "semantic_complexity_score": round(complexity, 4),
            "has_constraint": bool(has_constraint),
            "has_multi_goal": bool(has_multi_goal),
            "has_degree": bool(has_degree),
            "is_fuzzy": bool(is_fuzzy),
            "conflict_score": round(conflict_score, 4),
            "completeness_gap": round(completeness_gap, 4),
            "l3_conf": round(l3_conf, 4),
            "other_conf": round(other_conf, 4),
            "conf_margin": round(conf_margin, 4),
            "difficulty": d or "unknown",
        },
    }





def parse_edict_to_effects(

    text: str,

    *,

    edict_category: str = "other",

    numeric_data: Optional[NumericData] = None,

    root_dir: Optional[str] = None,

    enable_layer3_llm: bool = True,

    threshold_l1: float = 0.75,

    threshold_l2: float = 0.78,

    use_legacy_category_multiplier: bool = False,

    executor_context: Optional[Dict[str, Any]] = None,

) -> Dict[str, Any]:

    """

    root_dir: 未传 numeric_data 时可指定表格根目录以加载 NumericData（与 quarter 结算对齐）。

    executor_context: 显式承办人档案（API/表单）；若为 None 且启用推断，则从诏书原文子串匹配大臣表姓名。

    """

    trace: Dict[str, Any] = {"stages": []}
    sanitize_warnings: List[Dict[str, Any]] = []
    normalized_text, normalize_trace = normalize_edict_text(text)
    cat_ids = normalize_edict_categories(edict_category, normalized_text)
    cat_id = select_primary_category(cat_ids)
    cat_zh = category_label_zh(cat_id)

    data = numeric_data
    if data is None and (root_dir or "").strip():
        data = load_numeric_data(root_dir.strip())
    trace["numeric_data_loaded"] = data is not None

    effective_executor_ctx: Optional[Dict[str, Any]] = executor_context
    infer_enabled = _env_flag("PARSER_INFER_EXECUTOR_FROM_TEXT", default=True)
    if (
        effective_executor_ctx is None
        and infer_enabled
        and data is not None
        and getattr(data, "ministers", None)
    ):
        inferred = infer_executor_context_from_edict(normalized_text, data.ministers)
        if inferred is not None:
            effective_executor_ctx = {**inferred, "inferred_from_edict": True}
    trace["executor_resolution"] = {
        "source": (
            "api"
            if executor_context is not None
            else ("inferred" if effective_executor_ctx is not None else "none")
        ),
        "name": (effective_executor_ctx or {}).get("name"),
    }

    minister_names = set()
    if data is not None and getattr(data, "ministers", None):
        minister_names = {
            str(getattr(m, "name", "") or "").strip()
            for m in data.ministers
            if getattr(m, "name", None)
        }
    nlu_result = run_edict_nlu(
        normalized_text,
        edict_category_ids=cat_ids,
        minister_names=minister_names,
        executor_name=str((effective_executor_ctx or {}).get("name") or "").strip(),
        executor_source=str(trace["executor_resolution"].get("source") or "none"),
    )
    trace["nlu"] = nlu_result.to_trace_dict()
    trace["nlu_authoritative"] = True

    trace["normalization"] = normalize_trace
    trace["parser_mode"] = "v2" if _parser_v2_enabled() else "v1"
    runtime_mode = str(os.getenv("PARSER_RUNTIME_MODE") or "single_l3").strip().lower()
    if runtime_mode not in ("fusion", "single_l3"):
        runtime_mode = "fusion"
    trace["runtime_mode"] = runtime_mode
    difficulty = (
        str((normalize_trace or {}).get("difficulty") or "").strip().lower() or _infer_difficulty(normalized_text)
    )
    scoring_context: Dict[str, Any] = {
        "difficulty": difficulty,
        "is_fuzzy": _is_fuzzy_text(normalized_text),
        "ai_first_enabled": _env_flag("PARSER_V2_AI_FIRST_ENABLED", default=True),
        "conflict_score_enabled": _env_flag("PARSER_V2_CONFLICT_SCORE_ENABLED", default=True),
        "conflict_threshold_easy": float(os.getenv("PARSER_V2_CONFLICT_THRESHOLD_EASY") or 0.45),
        "conflict_threshold_medium": float(os.getenv("PARSER_V2_CONFLICT_THRESHOLD_MEDIUM") or 0.35),
        "conflict_threshold_hard": float(os.getenv("PARSER_V2_CONFLICT_THRESHOLD_HARD") or 0.25),
        "override_easy_protect_enabled": _env_flag("PARSER_V2_OVERRIDE_EASY_PROTECT_ENABLED", default=True),
        "l1_conf_mult": float(os.getenv("PARSER_V2_L1_CONF_MULT") or 0.85),
        "l2_conf_mult": float(os.getenv("PARSER_V2_L2_CONF_MULT") or 0.90),
        "l3_conf_mult": float(os.getenv("PARSER_V2_L3_CONF_MULT") or 1.15),
        "trust_l3_threshold_easy": float(os.getenv("PARSER_V2_TRUST_L3_THRESHOLD_EASY") or 0.72),
        "trust_l3_threshold_medium": float(os.getenv("PARSER_V2_TRUST_L3_THRESHOLD_MEDIUM") or 0.62),
        "trust_l3_threshold_hard": float(os.getenv("PARSER_V2_TRUST_L3_THRESHOLD_HARD") or 0.52),
    }
    scoring_context.update(_text_complexity_signals(normalized_text))
    # Dynamic confidence redistribution: feature-conditional calibration.
    if bool(scoring_context.get("has_constraint")):
        scoring_context["l3_conf_mult"] = float(scoring_context.get("l3_conf_mult") or 1.15) * 1.05
    if bool(scoring_context.get("has_multi_goal")):
        scoring_context["l3_conf_mult"] = float(scoring_context.get("l3_conf_mult") or 1.15) * 1.05
    if bool(scoring_context.get("is_fuzzy")):
        scoring_context["l1_conf_mult"] = float(scoring_context.get("l1_conf_mult") or 0.85) * 0.85
    if float(scoring_context.get("semantic_complexity_score") or 0.0) >= 2.2:
        scoring_context["l3_conf_mult"] = float(scoring_context.get("l3_conf_mult") or 1.15) * 1.08
    for k in ("l1_conf_mult", "l2_conf_mult", "l3_conf_mult"):
        scoring_context[k] = round(float(scoring_context.get(k) or 1.0), 4)
    trace["scoring_context"] = dict(scoring_context)

    executor_prompt_block = ""
    if effective_executor_ctx:
        executor_prompt_block = format_executor_prompt_block(
            effective_executor_ctx,
            edict_category_zh=cat_zh,
            edict_category_id=cat_id,
        )
        trace["executor_context"] = {
            "name": effective_executor_ctx.get("name"),
            "abilities_zh": effective_executor_ctx.get("abilities_zh"),
            "abilities": dict(effective_executor_ctx.get("abilities") or {}),
            "influence": effective_executor_ctx.get("influence"),
            "office": effective_executor_ctx.get("office"),
            "party": effective_executor_ctx.get("party"),
            "stance": effective_executor_ctx.get("stance"),
            "matched_minister": effective_executor_ctx.get("matched_minister"),
            "inferred_from_edict": bool(effective_executor_ctx.get("inferred_from_edict")),
        }

    def _finalize(effects: List[Dict[str, Any]]) -> Dict[str, Any]:
        eff, meta = apply_category_to_effects(
            effects,
            cat_id,
            use_legacy_multiplier=use_legacy_category_multiplier,
        )
        if effective_executor_ctx:
            eff, ex_trace = apply_executor_effect_modifications(
                eff, effective_executor_ctx, cat_id
            )
            trace["executor_modifier"] = ex_trace
        trace["edict_category"] = meta["resolved_id"]
        trace["edict_categories"] = cat_ids
        trace["edict_categories_label_zh"] = [category_label_zh(x) for x in cat_ids]
        trace["edict_category_label_zh"] = meta["label_zh"]
        trace["category_modifier"] = meta
        trace["sanitize_warnings"] = sanitize_warnings
        return {"effects": eff, "trace": trace}

    t_all = time.perf_counter()
    nlu_separated = _parser_nlu_separated_enabled()

    _raw_l1_effects, l1_trace = _layer1_combined(
        normalized_text, numeric_data=data, edict_category_ids=cat_ids
    )
    if nlu_separated:
        l1_trace["effects_suppressed"] = True
        l1_trace["shadow_effect_count"] = len(_raw_l1_effects or [])
        l1_effects: List[Dict[str, Any]] = []
    else:
        l1_effects = _sanitize_effects(_raw_l1_effects, sanitize_warnings)
    trace["stages"].append(l1_trace)

    if nlu_separated:
        l2_effects, l2_trace = _layer2_nlu_trace(trace.get("nlu") or {}, cat_ids)
    else:
        l2_effects, l2_trace = _layer2_semantic(normalized_text, cat_ids)
        l2_effects = _sanitize_effects(l2_effects, sanitize_warnings)
    trace["stages"].append(l2_trace)

    l3_effects: List[Dict[str, Any]] = []
    l3_trace: Dict[str, Any] = {}
    always_call_l3 = _env_flag("PARSER_V2_ALWAYS_CALL_L3", default=True)
    force_use_l3 = _env_flag("PARSER_FORCE_USE_L3", default=True)
    skipped_for_unified = False
    try:
        from edict_execution_frame.multi_segment import should_skip_standalone_l3

        skipped_for_unified = bool(should_skip_standalone_l3() and enable_layer3_llm)
    except ImportError:
        skipped_for_unified = False
    use_l3 = bool(
        enable_layer3_llm
        and not skipped_for_unified
        and (force_use_l3 or always_call_l3 or not _parser_v2_enabled())
    )
    if use_l3:
        _raw_l3_effects, l3_trace = _layer3_llm(
            normalized_text,
            edict_category_hint_zh=cat_zh,
            degree_hint=str((normalize_trace or {}).get("degree_hint") or ""),
            executor_prompt_block=executor_prompt_block,
        )
        if nlu_separated:
            l3_trace["effects_suppressed"] = True
            l3_trace["shadow_effect_count"] = len(_raw_l3_effects or [])
            l3_effects = []
        else:
            l3_effects = _sanitize_effects(_raw_l3_effects, sanitize_warnings)
        trace["stages"].append(l3_trace)
        merge_l3_into_nlu_trace(trace, l3_trace)
    trace["l3_control"] = {
        "enable_layer3_llm": bool(enable_layer3_llm),
        "force_use_l3": bool(force_use_l3),
        "always_call_l3": bool(always_call_l3),
        "used_l3": bool(use_l3),
        "skipped_for_unified_semantic": bool(skipped_for_unified),
        "intent_only_when_separated": bool(nlu_separated),
    }

    if nlu_separated:
        return _finish_nlu_separated_parse(
            trace,
            sanitize_warnings=sanitize_warnings,
            t_all=t_all,
            l1_trace=l1_trace,
            l2_trace=l2_trace,
            l3_trace=l3_trace,
            use_l3=use_l3,
            cat_id=cat_id,
            cat_ids=cat_ids,
            use_legacy_category_multiplier=use_legacy_category_multiplier,
            effective_executor_ctx=effective_executor_ctx,
        )

    # Runtime route: single_l3 keeps code path simple for online validation.
    # We still enforce guardrail and keep trace compatible for reporting.
    if runtime_mode == "single_l3":
        selected_effects = list(l3_effects or [])
        reject_reason = ""
        l3_dsl = (l3_trace.get("dsl") or {}) if isinstance(l3_trace, dict) else {}
        l3_intent = str(l3_dsl.get("intent") or "none").strip() or "none"
        l3_conf = float(l3_trace.get("confidence") or 0.0) if isinstance(l3_trace, dict) else 0.0
        min_conf = float(os.getenv("PARSER_SINGLE_L3_MIN_CONF") or 0.60)
        reject_none = _env_flag("PARSER_SINGLE_L3_REJECT_NONE", default=True)
        require_policy_signal = _env_flag("PARSER_SINGLE_L3_REQUIRE_POLICY_SIGNAL", default=False)
        has_policy_signal = _has_policy_action_signal(normalized_text)
        reject_none_like = _env_flag("PARSER_SINGLE_L3_REJECT_NONE_LIKE", default=True)
        is_none_like = _is_none_like_text(normalized_text)
        if reject_none and l3_intent == "none":
            selected_effects = []
            reject_reason = "l3_intent_none"
        elif l3_conf < min_conf:
            selected_effects = []
            reject_reason = "l3_conf_below_threshold"
        elif reject_none_like and is_none_like:
            selected_effects = []
            reject_reason = "none_like_text"
        elif require_policy_signal and not has_policy_signal:
            selected_effects = []
            reject_reason = "no_policy_action_signal"
        safe_effects, guardrail_trace = apply_safety_guardrail(selected_effects)

        fallback_used = False
        fallback_source = ""
        fallback_reason = ""
        if not safe_effects:
            # If L3 is unavailable/rejected/empty, still allow deterministic L1/L2 output.
            l1_conf = float(l1_trace.get("confidence") or 0.0)
            l2_conf = float(l2_trace.get("confidence") or 0.0)
            fallback_l1_min_conf = float(
                os.getenv("PARSER_SINGLE_L3_FALLBACK_L1_MIN_CONF") or 0.55
            )
            fallback_l2_min_conf = float(
                os.getenv("PARSER_SINGLE_L3_FALLBACK_L2_MIN_CONF") or 0.55
            )

            fallback_effects: List[Dict[str, Any]] = []
            if l1_effects and l1_conf >= fallback_l1_min_conf:
                fallback_effects = list(l1_effects)
                fallback_source = "layer1"
            else:
                merged = _sanitize_effects(l1_effects + l2_effects, sanitize_warnings)
                if merged:
                    fallback_effects = merged
                    fallback_source = (
                        "layer1_plus_layer2"
                        if l2_effects and l2_conf >= fallback_l2_min_conf
                        else "layer1_plus_layer2_best_effort"
                    )

            if fallback_effects:
                safe_effects, guardrail_trace = apply_safety_guardrail(fallback_effects)
                fallback_used = True
                fallback_reason = reject_reason or "l3_empty_or_rejected"
        trace["decision_trace"] = {
            "runtime_mode": runtime_mode,
            "l3_invoked": bool(use_l3),
            "selected_layer": "layer3_llm" if l3_effects else ("none" if not fallback_used else f"fallback_{fallback_source}"),
            "selected_effect_count": len(selected_effects),
            "fallback_reason": (
                reject_reason
                or ("" if l3_effects else "l3_empty_or_unavailable")
                or (fallback_reason if fallback_used else "")
            ),
            "fallback_used": bool(fallback_used),
            "fallback_source": fallback_source,
            "merge_strategy": "single_l3_direct",
            "single_l3_guard": {
                "l3_intent": l3_intent,
                "l3_conf": round(l3_conf, 4),
                "min_conf": round(min_conf, 4),
                "has_policy_action_signal": has_policy_signal,
                "is_none_like_text": is_none_like,
                "reject_none_like": bool(reject_none_like),
                "reject_none": bool(reject_none),
                "require_policy_signal": bool(require_policy_signal),
            },
        }
        trace["guardrail_trace"] = guardrail_trace
        trace["fallback_used"] = bool(fallback_used)
        trace["fallback_source"] = fallback_source
        trace["final_confidence"] = round(float(l3_trace.get("confidence") or 0.0), 4) if l3_trace else 0.0
        if safe_effects and fallback_used:
            trace["final_layer"] = f"single_l3_fallback_to_{fallback_source}"
        else:
            trace["final_layer"] = "single_l3" if safe_effects else "single_l3_no_effect"
        trace["latency_total_ms"] = round((time.perf_counter() - t_all) * 1000.0, 3)
        return _finalize(safe_effects)

    # V1 compatibility path (legacy short-circuit)
    if not _parser_v2_enabled():
        if l1_trace.get("confidence", 0.0) >= threshold_l1 and l1_effects:
            trace["final_layer"] = "layer1_combined"
            return _finalize(l1_effects)
        if l2_trace.get("confidence", 0.0) >= threshold_l2 and l2_effects:
            trace["final_layer"] = "layer2_semantic"
            return _finalize(_sanitize_effects(l1_effects + l2_effects, sanitize_warnings))
        if use_l3:
            merged = _sanitize_effects(l1_effects + l2_effects + l3_effects, sanitize_warnings)
            trace["final_layer"] = "layer3_llm" if l3_effects else "fallback_no_llm_hit"
            return _finalize(merged)
        trace["final_layer"] = "fallback_no_layer3"
        return _finalize(_sanitize_effects(l1_effects + l2_effects, sanitize_warnings))

    # V2 path: candidates -> scoring -> merge strategy -> guardrail.
    raw_candidates = [
        _candidate_from_layer(
            "layer1_combined",
            effects=l1_effects,
            layer_trace=l1_trace,
            categories=cat_ids,
        ),
        _candidate_from_layer(
            "layer2_semantic",
            effects=l2_effects,
            layer_trace=l2_trace,
            categories=cat_ids,
        ),
    ]
    if use_l3:
        raw_candidates.append(
            _candidate_from_layer(
                "layer3_llm",
                effects=l3_effects,
                layer_trace=l3_trace,
                categories=cat_ids,
            )
        )
    # Keep only candidates with content or non-zero confidence for observability.
    candidates = [
        c
        for c in raw_candidates
        if c.get("effects") or float(c.get("confidence") or 0.0) > 0.0
    ]
    scored, score_meta = score_candidates(
        candidates,
        expected_categories=cat_ids,
        scoring_context=scoring_context,
    )
    top_l3 = _pick_top_by_layer(scored, "layer3_llm")
    top_non_l3 = next(
        (c for c in scored if str(c.get("source_layer") or "") != "layer3_llm"),
        None,
    )
    conflict_analysis = _analyze_conflict(
        top_l3=top_l3,
        top_non_l3=top_non_l3,
        scoring_context=scoring_context,
        score_meta=score_meta,
    )
    trust_pack = _compute_l3_trust_score(
        scoring_context=scoring_context,
        conflict_analysis=conflict_analysis,
        top_l3=top_l3,
        top_non_l3=top_non_l3,
    )
    trust_score = float(trust_pack.get("trust_score") or 0.0)
    d = str(scoring_context.get("difficulty") or "medium").lower()
    trust_thresholds = {
        "easy": float(scoring_context.get("trust_l3_threshold_easy") or 0.72),
        "medium": float(scoring_context.get("trust_l3_threshold_medium") or 0.62),
        "hard": float(scoring_context.get("trust_l3_threshold_hard") or 0.52),
        "edge": float(scoring_context.get("trust_l3_threshold_hard") or 0.52),
    }
    trust_threshold = trust_thresholds.get(d, trust_thresholds["medium"])
    strategy = (os.getenv("PARSER_V2_MERGE_STRATEGY") or "winner_take_all").strip().lower()
    if strategy not in ("winner_take_all", "weighted_merge"):
        strategy = "winner_take_all"
    selected_effects = _merge_candidates(scored, strategy=strategy)
    resolver_choice = None
    trust_trace: Dict[str, Any] = {
        "enabled": _env_flag("PARSER_V2_TRUST_L3_ENABLED", default=True),
        "trust_score": round(trust_score, 4),
        "threshold": round(trust_threshold, 4),
        "triggered": False,
        "reason": "below_threshold",
        "features": trust_pack.get("features") or {},
    }
    l3_advantage_trace: Dict[str, Any] = {"triggered": False, "reason": "disabled"}
    if trust_trace["enabled"] and strategy == "winner_take_all" and top_l3 is not None:
        if trust_score >= trust_threshold:
            selected_effects = list(top_l3.get("effects") or [])
            resolver_choice = dict(top_l3)
            trust_trace["triggered"] = True
            trust_trace["reason"] = "trust_l3_selected"
    if _env_flag("PARSER_V2_L3_ADVANTAGE_TRIGGER_ENABLED", default=True):
        trig, trig_reason = _should_trigger_l3_advantage(scoring_context, conflict_analysis)
        l3_advantage_trace = {"triggered": bool(trig), "reason": trig_reason}
        if trig and strategy == "winner_take_all" and resolver_choice is None:
            top_l3 = _pick_top_by_layer(scored, "layer3_llm")
            top_non_l3 = next(
                (c for c in scored if str(c.get("source_layer") or "") != "layer3_llm"),
                None,
            )
            if top_l3 is not None and top_non_l3 is not None:
                l3_score_biased = float(top_l3.get("score") or 0.0) + 0.10
                other_score = float(top_non_l3.get("score") or 0.0)
                l3_advantage_trace["l3_biased_score"] = round(l3_score_biased, 4)
                l3_advantage_trace["other_score"] = round(other_score, 4)
                if l3_score_biased >= other_score:
                    selected_effects = list(top_l3.get("effects") or [])
                    resolver_choice = dict(top_l3)
                    l3_advantage_trace["promoted"] = True
                else:
                    l3_advantage_trace["promoted"] = False
    resolver_trace: Dict[str, Any] = {"used": False, "reason": "disabled"}
    if _env_flag("PARSER_V2_CONFLICT_RESOLVER_ENABLED", default=True) and not bool(trust_trace.get("triggered")):
        conflict_choice, resolver_trace = _resolve_conflict(
            scored,
            scoring_context=scoring_context,
            conflict_analysis=conflict_analysis,
        )
        if conflict_choice is not None:
            resolver_choice = conflict_choice
    if resolver_choice is not None and strategy == "winner_take_all":
        selected_effects = list(resolver_choice.get("effects") or [])

    # L3 retry/override: when not selected but l3 score is strong and safe.
    l3_override_trace: Dict[str, Any] = {"used": False, "reason": "skipped"}
    if _env_flag("PARSER_V2_L3_OVERRIDE_ENABLED", default=True) and strategy == "winner_take_all":
        top_l3 = _pick_top_by_layer(scored, "layer3_llm")
        selected_layer = (
            str(resolver_choice.get("source_layer")) if resolver_choice else (str(scored[0].get("source_layer")) if scored else "none")
        )
        if top_l3 is not None and selected_layer != "layer3_llm":
            l3_score = float(top_l3.get("score") or 0.0)
            is_high_value_conflict = bool(
                conflict_analysis.get("should_conflict")
                and (
                    conflict_analysis.get("completeness_conflict")
                    or conflict_analysis.get("direction_conflict")
                    or ("complexity" in (conflict_analysis.get("reason_tags") or []))
                )
            )
            if not is_high_value_conflict:
                l3_override_trace = {
                    "used": False,
                    "reason": "not_high_value_conflict",
                }
            else:
                threshold = 0.62
                if float(scoring_context.get("semantic_complexity_score") or 0.0) >= 1.5:
                    threshold = 0.56
                if bool(conflict_analysis.get("completeness_conflict")):
                    threshold = min(threshold, 0.52)
                if (
                    str(scoring_context.get("difficulty") or "").lower() == "easy"
                    and bool(scoring_context.get("override_easy_protect_enabled", True))
                ):
                    threshold = max(threshold, 0.72)
                if l3_score >= threshold:
                    l3_safe_effects, l3_guard = apply_safety_guardrail(list(top_l3.get("effects") or []))
                    if l3_safe_effects:
                        selected_effects = l3_safe_effects
                        resolver_choice = dict(top_l3)
                        l3_override_trace = {
                            "used": True,
                            "reason": "l3_retry_override",
                            "l3_score": round(l3_score, 4),
                            "threshold": round(threshold, 4),
                            "high_value_conflict": True,
                            "guardrail_adjustments": len((l3_guard or {}).get("adjustments") or []),
                        }
                    else:
                        l3_override_trace = {"used": False, "reason": "l3_failed_safety"}
                else:
                    l3_override_trace = {
                        "used": False,
                        "reason": "l3_score_below_threshold",
                        "l3_score": round(l3_score, 4),
                        "threshold": round(threshold, 4),
                    }
    safe_effects, guardrail_trace = apply_safety_guardrail(selected_effects)

    trace["candidates"] = [
        {
            "source_layer": c.get("source_layer"),
            "confidence": c.get("confidence"),
            "score": c.get("score"),
            "score_features": c.get("score_features"),
            "score_features_v2": c.get("score_features_v2"),
            "effect_count": len(c.get("effects") or []),
            "evidence": c.get("evidence"),
        }
        for c in scored
    ]
    trace["decision_trace"] = {
        "merge_strategy": strategy,
        "score_meta": score_meta,
        "selected_layer": (
            resolver_choice.get("source_layer")
            if resolver_choice is not None
            else (scored[0].get("source_layer") if scored else "none")
        ),
        "selected_effect_count": len(selected_effects),
        "conflicts": (score_meta.get("conflicts") or []),
        "conflict_analysis": conflict_analysis,
        "l3_trust": trust_trace,
        "l3_advantage_trigger": l3_advantage_trace,
        "conflict_resolver": resolver_trace,
        "l3_override": l3_override_trace,
    }
    trace["guardrail_trace"] = guardrail_trace
    trace["final_confidence"] = round(float(scored[0].get("score") or 0.0), 4) if scored else 0.0
    if safe_effects:
        trace["final_layer"] = "v2_fusion"
    else:
        trace["final_layer"] = "v2_no_effect"
    trace["latency_total_ms"] = round((time.perf_counter() - t_all) * 1000.0, 3)
    return _finalize(safe_effects)


