# -*- coding: utf-8 -*-
"""人物 AI 主逻辑：RAG 检索 + Prompt 组装 + LLM 调用（支持多角色）。"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DEFAULT_DATA_DIR, PERSONAS_FILE, PERSONA_ID_WANGANSHI, RAG_TOP_K
from .characters import CharacterConfig, get_character
from .rag import load_chunks, retrieve, format_chunks_for_prompt
from .prompts import build_messages


def _load_personas(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _get_persona_by_id(persona_path: Path, persona_id: str) -> Optional[Dict[str, Any]]:
    personas = _load_personas(persona_path)
    for p in personas:
        if p.get("persona_id") == persona_id:
            return p
    return None


def get_wanganshi_persona(data_dir: Path = DEFAULT_DATA_DIR) -> Optional[Dict[str, Any]]:
    """兼容旧接口：从默认 personas 文件中取出王安石条目。"""
    return _get_persona_by_id(data_dir / PERSONAS_FILE, PERSONA_ID_WANGANSHI)


def _call_llm(messages: List[Dict[str, str]], api_key: str, base_url: str, model: str) -> str:
    """调用 OpenAI 兼容 API（支持 openai>=1.0 或 0.8.x）。"""
    from .config import LLM_REQUEST_TIMEOUT

    timeout = LLM_REQUEST_TIMEOUT

    def _call_via_http() -> str:
        """
        不依赖 openai SDK 的纯 HTTP 调用（OpenAI 兼容 /chat/completions）。
        适配旧 Python/受限索引环境，作为最终兜底。
        """
        import urllib.request
        import urllib.error

        url = (base_url or "").rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'sk-placeholder'}",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode("utf-8", errors="ignore")
            except Exception:
                raw = str(e)
            raise RuntimeError(f"LLM HTTPError: {e.code} {raw}")
        except Exception as e:
            raise RuntimeError(f"LLM request failed: {str(e)}")

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip()

        choices = obj.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return (msg.get("content") or "").strip()

    try:
        from openai import OpenAI

        try:
            client = OpenAI(
                api_key=api_key or "sk-placeholder",
                base_url=base_url,
                timeout=timeout,
            )
        except TypeError:
            client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        choice = resp.choices[0] if resp.choices else None
        if not choice or not getattr(choice, "message", None):
            return ""
        return (choice.message.content or "").strip()
    except (ImportError, AttributeError):
        # openai 0.8.x：使用 openai.api_key / api_base + ChatCompletion.create
        try:
            import openai
        except ImportError:
            # 没有 openai 包，直接走 HTTP
            return _call_via_http()
        openai.api_key = api_key or "sk-placeholder"
        openai.api_base = base_url
        chat_completion = getattr(openai, "ChatCompletion", None)
        if chat_completion is None:
            # openai 包太老（如 0.10.x），走 HTTP 兜底
            return _call_via_http()
        resp = chat_completion.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        choices = getattr(resp, "choices", None) or resp.get("choices", [])
        choice = choices[0] if choices else None
        if not choice:
            return ""
        msg = getattr(choice, "message", None) or choice.get("message", {})
        content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
        return (content or "").strip()


def reply(
    user_message: str,
    character_id: str = "wang_anshi",
    data_dir: Optional[Path] = None,
    top_k: int = RAG_TOP_K,
    chat_history: Optional[List[Dict[str, str]]] = None,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    皇帝提问，返回王安石的回复及检索到的史料（便于调试或展示）。

    :param user_message: 陛下（用户）的提问
    :param character_id: 角色 ID，如 wang_anshi / zhang_juzheng
    :param data_dir: 可选，覆盖角色默认的史料目录
    :param top_k: RAG 检索条数
    :param chat_history: 此前轮次的 [{"role":"user"|"assistant","content":"..."}]
    :param metrics: 可选，当前局势指标（如国库、民心等），会注入用户 prompt
    :param api_key: 可选覆盖 API Key；默认按角色自动选择（王安石本地、其他角色公网）
    :param base_url: 可选覆盖 API 基地址；默认按角色自动选择
    :param model: 可选覆盖模型名；默认按角色自动选择
    :return: {"reply": "王安石回复文本", "references": [检索到的 chunk 摘要], "retrieved_count": n}
    """
    from .config import resolve_chat_llm

    # 选角色配置
    character: CharacterConfig = get_character(character_id)
    char_data_dir = data_dir or character.data_dir
    if not (api_key and base_url and model):
        resolved_key, resolved_base, resolved_model = resolve_chat_llm(character.id)
        api_key = api_key or resolved_key
        base_url = base_url or resolved_base
        model = model or resolved_model

    if not api_key or (isinstance(api_key, str) and "placeholder" in api_key.lower()):
        return {
            "reply": (
                "未配置有效的 LLM API Key，无法调用大模型。"
                "请在项目根目录 `.env` 中设置 DASHSCOPE_API_KEY（通义千问，所有大臣问策默认共用）；"
                "若王安石要走本机 Ollama，请设 WANGANSHI_USE_LOCAL_LLM=1 并配置 WANGANSHI_API_BASE。"
                "修改后重启 API 服务。"
            ),
            "references": [],
            "retrieved_count": 0,
        }

    # 加载该角色的 RAG 片段与 persona
    # 王安石：默认不合并全项目 docs/（其中含大量明代张居正材料），避免检索抢答成「张居正文风」。
    merge_docs = True
    if character.id == "wang_anshi":
        merge_docs = os.getenv(
            "RAG_WANGANSHI_MERGE_PROJECT_DOCS", ""
        ).strip().lower() in ("1", "true", "yes")
    chunks = load_chunks(
        char_data_dir,
        character.knowledge_file,
        merge_project_docs=merge_docs,
    )
    persona = None
    if character.persona_file:
        persona_path = char_data_dir / character.persona_file
        if persona_path.exists():
            # persona_id 默认为角色 id，可根据需要在 personas 文件中设置相同的 persona_id
            persona = _get_persona_by_id(persona_path, character.id)
    retrieved = retrieve(user_message, chunks, top_k=top_k)
    reference_context = format_chunks_for_prompt(retrieved)

    messages = build_messages(
        user_message=user_message,
        reference_context=reference_context,
        character=character,
        persona=persona,
        chat_history=chat_history,
    )

    reply_text = _call_llm(messages, api_key, base_url, model)

    references = []
    for r in retrieved:
        references.append({
            "source": r.get("source_doc"),
            "section": r.get("section_title"),
            "preview": (r.get("content") or "")[:200] + "..." if (r.get("content") or "") and len(r.get("content", "")) > 200 else (r.get("content") or ""),
        })

    return {
        "reply": reply_text,
        "references": references,
        "retrieved_count": len(retrieved),
    }


_JSON_MARKER = "\n===JSON===\n"


def _split_answer_and_json(raw: str) -> tuple:
    text = (raw or "").strip()
    if _JSON_MARKER in text:
        a, j = text.split(_JSON_MARKER, 1)
        return a.strip(), j.strip()
    brace = text.rfind("}")
    if brace >= 0:
        start = text.rfind("{", 0, brace)
        if start >= 0:
            return text[:start].strip(), text[start : brace + 1]
    return text, ""


def persona_reply_with_advice(
    user_message: str,
    character_id: str = "wang_anshi",
    data_dir: Optional[Path] = None,
    top_k: int = RAG_TOP_K,
    chat_history: Optional[List[Dict[str, str]]] = None,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    minister_display_name: str = "",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    人物对话 + 结构化「政务建议候选」JSON（单次 LLM；不直接改数值）。
    """
    from numeric_system.policy_ir import MinisterAdviceLLMBlock

    from .minister_qa.classifier import classify_question

    qc = classify_question(user_message, minister_name=minister_display_name)
    empty_extra = {
        "question_classification": qc,
        "stance": {},
        "advice_candidates": [],
        "candidate_scores": [],
        "parse_warning": "",
    }

    character: CharacterConfig = get_character(character_id)
    char_data_dir = data_dir or character.data_dir
    from .config import resolve_chat_llm

    if not (api_key and base_url and model):
        resolved_key, resolved_base, resolved_model = resolve_chat_llm(character.id)
        api_key = api_key or resolved_key
        base_url = base_url or resolved_base
        model = model or resolved_model

    if not api_key or (isinstance(api_key, str) and "placeholder" in api_key.lower()):
        r = reply(
            user_message=user_message,
            character_id=character_id,
            data_dir=data_dir,
            top_k=top_k,
            chat_history=chat_history,
            metrics=metrics,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        return {**r, **empty_extra, "parse_warning": "no_llm_key"}

    merge_docs = True
    if character.id == "wang_anshi":
        merge_docs = os.getenv(
            "RAG_WANGANSHI_MERGE_PROJECT_DOCS", ""
        ).strip().lower() in ("1", "true", "yes")
    chunks = load_chunks(
        char_data_dir,
        character.knowledge_file,
        merge_project_docs=merge_docs,
    )
    persona = None
    if character.persona_file:
        persona_path = char_data_dir / character.persona_file
        if persona_path.exists():
            persona = _get_persona_by_id(persona_path, character.id)
    retrieved = retrieve(user_message, chunks, top_k=top_k)
    reference_context = format_chunks_for_prompt(retrieved)
    messages = build_messages(
        user_message=user_message,
        reference_context=reference_context,
        character=character,
        persona=persona,
        chat_history=chat_history,
    )
    metrics_line = _metrics_to_text(metrics)
    struct = (
        "\n\n## 局势指标（供参考）\n"
        f"{metrics_line}\n"
        "\n## 结构化输出（务必遵守）\n"
        "1) 正文须含「### 一、局势分析」与「### 二、具体建议」两节；"
        "「具体建议」中每条须为完整委派诏书句式（命/遣/诏…若干季为期）。\n"
        "2) 正文结束后单独一行，仅包含：===JSON===\n"
        "3) 下一行起输出**唯一**一个 JSON 对象（不要 markdown 代码围栏），格式：\n"
        '{"answer_zh":"含局势分析与委派建议的奏对全文","stance":{},"advice_candidates":['
        '{"candidate_id":"唯一id","domain":"anti_corruption或general",'
        '"title_zh":"短标题","summary_zh":"与委派模版一致的诏书建议句",'
        '"executor":"承办大臣姓名，可空","intensity":"low|medium|high",'
        '"policy_style":"strict|moderate|soft|institutional|unknown",'
        '"target_metrics":["corruption"],'
        '"expected_effect_profile":{"corruption":"down_medium"},'
        '"risk_tags":[]}]} 。\n'
        "advice_candidates 至少 1 条、至多 3 条；summary_zh 须可直接改写为诏书；"
        "metric 键须为 corruption、treasury_balance、public_support、unrest、fiscal_pressure、authority 等已有键。\n"
        f"系统已粗分类玩家问题为：{qc}。\n"
    )
    messages[0]["content"] = messages[0]["content"] + struct

    raw = _call_llm(messages, api_key or "", base_url or "", model or "")
    answer_body, json_blob = _split_answer_and_json(raw)
    base_reply = answer_body or raw.strip()
    references = []
    for r in retrieved:
        references.append(
            {
                "source": r.get("source_doc"),
                "section": r.get("section_title"),
                "preview": (r.get("content") or "")[:200] + "..."
                if (r.get("content") or "") and len(r.get("content", "")) > 200
                else (r.get("content") or ""),
            }
        )

    if not json_blob.strip():
        return {
            "reply": base_reply,
            "references": references,
            "retrieved_count": len(retrieved),
            **empty_extra,
            "parse_warning": "empty_json_blob",
        }

    try:
        block = MinisterAdviceLLMBlock.model_validate_json(json_blob)
    except Exception as exc:  # noqa: BLE001
        return {
            "reply": base_reply,
            "references": references,
            "retrieved_count": len(retrieved),
            **empty_extra,
            "parse_warning": f"json_invalid:{exc}",
        }

    cands = []
    for i, p in enumerate(block.advice_candidates[:3]):
        cid = (p.candidate_id or "").strip() or f"advice_{character_id}_{i}"
        cands.append(p.model_copy(update={"candidate_id": cid}).model_dump())
    scores = [{"candidate_id": c["candidate_id"], "score": 70.0 - i * 5} for i, c in enumerate(cands)]
    return {
        "reply": block.answer_zh or base_reply,
        "references": references,
        "retrieved_count": len(retrieved),
        "question_classification": qc,
        "stance": block.stance or {},
        "advice_candidates": cands,
        "candidate_scores": scores,
        "parse_warning": "",
    }


def _metrics_to_text(metrics: Optional[dict]) -> str:
    if not metrics:
        return "（未提供）"
    items = []
    for k, v in metrics.items():
        items.append(f"- {k}={v}")
    return "\n".join(items) if items else "（未提供）"


def _build_debate_prompt(
    *,
    issue: str,
    metrics: Optional[dict],
    edict_text: str,
    opponent_name: str,
) -> str:
    metrics_text = _metrics_to_text(metrics)
    edict = (edict_text or "").strip() or "（空）"
    return (
        "你正在朝议中与另一位重臣争辩。必须严格以你的历史身份与语气回答。\n\n"
        f"议题：{issue}\n"
        "局势指标：\n"
        f"{metrics_text}\n\n"
        "陛下拟诏书原文（可为空）：\n"
        f"{edict}\n\n"
        f"对手：{opponent_name}\n\n"
        "输出要求（极重要）：\n"
        "- 文风：白话为主，可夹少量文言套语，忌通篇文言。\n"
        "- 自由辩论表达即可，但每一段都必须包含四要素：\n"
        "  1) 驳斥对方观点（点名对手或其论点）\n"
        "  2) 强调你的核心主张（你认为应当如何）\n"
        "  3) 给出你的做法（具体怎么推行/怎么约束吏治/怎么试点）\n"
        "  4) 说明预期结果（会改善什么、代价是什么，最好点到一两项指标方向）\n"
        "- 形式建议：写成1段或2段短陈词即可，但总句数必须控制在3-5句内（句子可长）。\n"
        "- 为便于展示：尽量每句一行；不要分点编号。\n"
        "- 不要输出JSON，不要输出标题，不要输出多余解释，只输出辩论内容。\n"
    )


def _split_5_lines(text: str) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    # 优先按行切（模型若遵守“尽量每句一行”）
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) >= 2:
        return lines[:5]

    # 若只有一大段，则按中文常见标点切句
    import re

    s = lines[0] if lines else raw
    # 把全角标点作为句子边界，保留标点以维持语气
    parts = re.split(r"(?<=[。！？；])\s*", s)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return []
    return parts[:5]


def _split_sentences(text: str, max_sentences: int) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    # 先按行；如果行数>=2，视为“句”
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) >= 2:
        return lines[:max_sentences]

    # 否则按常见标点切句
    import re

    s = lines[0] if lines else raw
    parts = re.split(r"(?<=[。！？；])\s*", s)
    parts = [p.strip() for p in parts if p.strip()]
    return parts[:max_sentences]


def _join_sentences(sentences: List[str]) -> str:
    # 尽量保持自然：如果句子末尾已有标点就直接拼，否则补一个。
    out = []
    for s in sentences:
        s = (s or "").strip()
        if not s:
            continue
        out.append(s)
    return "\n".join(out).strip()


def debate_multi(
    *,
    issue: str,
    metrics: Optional[dict] = None,
    edict_text: str = "",
    participants: Optional[List[str]] = None,
    rounds: int = 3,
    max_sentences_per_turn: int = 3,
    data_dir: Optional[Path] = None,
    top_k: int = RAG_TOP_K,
) -> Dict[str, Any]:
    """
    多轮斗嘴：两位人物来回辩论多轮。

    - rounds: 来回轮数（每轮双方各发言一次，总发言数 = rounds*2）
    - max_sentences_per_turn: 每次发言最多几句（用于 UI 控制，也用于写回 history）

    返回：
    {
      "issue": "...",
      "participants": [{"id":"...","name":"..."}, ...],
      "transcript": [
        {"turn_index": 1, "speaker_id": "...", "speaker_name":"...", "text":"...", "sentences":[...], "references":[...], "retrieved_count": n},
        ...
      ]
    }
    """
    if not participants:
        participants = ["wang_anshi", "sima_guang"]
    if len(participants) != 2:
        raise ValueError("participants 必须恰好包含2个角色ID。")
    if rounds < 1 or rounds > 10:
        raise ValueError("rounds 必须在 1-10 之间。")
    if max_sentences_per_turn < 1 or max_sentences_per_turn > 6:
        raise ValueError("max_sentences_per_turn 必须在 1-6 之间。")

    a_id, b_id = participants[0], participants[1]
    char_a = get_character(a_id)
    char_b = get_character(b_id)

    def _turn_prompt(speaker: CharacterConfig, opponent: CharacterConfig, is_first: bool) -> str:
        base = _build_debate_prompt(
            issue=issue,
            metrics=metrics,
            edict_text=edict_text,
            opponent_name=opponent.name,
        )
        # 多轮：要求“接续上文继续驳论”，并控制句数
        extra = (
            "\n补充要求：\n"
            f"- 本次只发言不超过{max_sentences_per_turn}句，尽量每句一行。\n"
            "- 必须直接回应对手上一段的观点，抓住要害驳斥。\n"
            "- 必须重申你的主张，并给出可执行的做法与预期结果。\n"
        )
        if is_first:
            extra += "- 这是第一轮，请先开宗明义表态。\n"
        return base + extra

    # 将已展示的文本写回 history，保证后续“接着吵”与 UI 一致
    history: List[Dict[str, str]] = []
    transcript: List[Dict[str, Any]] = []

    turn_counter = 0
    for r in range(rounds):
        for speaker, opponent in [(char_a, char_b), (char_b, char_a)]:
            turn_counter += 1
            prompt = _turn_prompt(speaker, opponent, is_first=(turn_counter == 1))
            result = reply(
                user_message=prompt,
                character_id=speaker.id,
                data_dir=data_dir,
                top_k=top_k,
                chat_history=history,
                metrics=metrics,
            )
            raw_text = result.get("reply", "") or ""
            sentences = _split_sentences(raw_text, max_sentences=max_sentences_per_turn)
            trimmed_text = _join_sentences(sentences) if sentences else raw_text.strip()

            # 把“展示版本”写回 history，避免模型在后续引用未展示内容
            history.append(
                {
                    "role": "assistant",
                    "content": f"【{speaker.name}】{trimmed_text}",
                }
            )

            transcript.append(
                {
                    "turn_index": turn_counter,
                    "round_index": r + 1,
                    "speaker_id": speaker.id,
                    "speaker_name": speaker.name,
                    "text": trimmed_text,
                    "sentences": sentences,
                    "references": result.get("references", []) or [],
                    "retrieved_count": result.get("retrieved_count", 0),
                }
            )

    return {
        "issue": issue,
        "participants": [
            {"id": char_a.id, "name": char_a.name},
            {"id": char_b.id, "name": char_b.name},
        ],
        "transcript": transcript,
    }

def debate(
    *,
    issue: str,
    metrics: Optional[dict] = None,
    edict_text: str = "",
    participants: Optional[List[str]] = None,
    data_dir: Optional[Path] = None,
    top_k: int = RAG_TOP_K,
) -> Dict[str, Any]:
    """
    斗嘴：两位人物各输出5句（逐行），总共<=10句。

    返回：
    {
      "issue": "...",
      "sides": [
        {"character_id": "...", "character_name": "...", "text": "...", "lines": [...], "references": [...], "retrieved_count": n},
        ...
      ]
    }
    """
    if not participants:
        participants = ["wang_anshi", "sima_guang"]
    if len(participants) != 2:
        raise ValueError("participants 必须恰好包含2个角色ID。")

    a, b = participants[0], participants[1]
    # get_character 会在未知时抛 KeyError
    char_a = get_character(a)
    char_b = get_character(b)

    sides: List[Dict[str, Any]] = []
    for speaker, opponent in [(char_a, char_b), (char_b, char_a)]:
        prompt = _build_debate_prompt(
            issue=issue,
            metrics=metrics,
            edict_text=edict_text,
            opponent_name=opponent.name,
        )
        result = reply(
            user_message=prompt,
            character_id=speaker.id,
            data_dir=data_dir,
            top_k=top_k,
            chat_history=[],
            metrics=metrics,
        )
        text = result.get("reply", "") or ""
        sides.append(
            {
                "character_id": speaker.id,
                "character_name": speaker.name,
                "text": text,
                "lines": _split_5_lines(text),
                "references": result.get("references", []) or [],
                "retrieved_count": result.get("retrieved_count", 0),
            }
        )

    return {"issue": issue, "sides": sides}
