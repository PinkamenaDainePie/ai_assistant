# -*- coding: utf-8 -*-
"""多人角色配置：王安石、张居正等人物 AI 的统一入口。

后续如需新增人物，只需：
1）在 personas JSON 中增加条目（或 CHARACTERS_EXTRA 手工注册）
2）准备对应的 RAG 数据目录（一般是 json 子目录中的 JSONL）
3）在前端剧本 characters 中增加 apiCharacterId 映射
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ROOT


@dataclass
class CharacterConfig:
    id: str
    name: str
    dynasty: str
    # RAG 相关
    data_dir: Path
    knowledge_file: str
    persona_file: Optional[str] = None
    # Prompt 相关
    base_system_prompt: str = ""
    role_hint: str = "陛下"


_SONG_DATA = ROOT / "json" / "2（王安石变法）"
_MING_DATA = ROOT / "json" / "6（张居正变法）"
_SONG_DELEGATION = ROOT / "task_system" / "catalog" / "song_minister_delegation.json"

# 与 scenario_system/profiles.py song_xining.character_ids 一致
_SONG_MINISTER_ID_BY_NAME: Dict[str, str] = {
    "王安石": "wang_anshi",
    "司马光": "sima_guang",
    "吕惠卿": "lv_huiqing",
    "苏轼": "su_shi",
    "章惇": "zhang_dun",
    "沈括": "shen_kuo",
    "曾布": "zeng_bu",
    "文彦博": "wen_yanbo",
    "韩琦": "han_qi",
    "富弼": "fu_bi",
    "韩绛": "han_jiang",
    "蔡确": "cai_que",
    "吕公著": "lv_gongzhu",
    "苏辙": "su_zhe",
    "陈升之": "chen_shengzhi",
    "王珪": "wang_gui",
    "吴充": "wu_chong",
    "王韶": "wang_shao",
    "郭逵": "guo_kui",
    "种谔": "zhong_e",
    "薛向": "xue_xiang",
}


def _load_personas_json(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw) if isinstance(raw, list) else []


def _persona_prompt(
    persona: Dict[str, Any],
    *,
    dynasty: str,
    era: str,
    audience: str = "陛下",
    self_ref: str = "臣",
) -> str:
    name = str(persona.get("name") or "未知")
    role = str(persona.get("role") or "")
    seed = str(persona.get("prompt_seed") or "").strip()
    themes = "、".join(str(x) for x in (persona.get("core_themes") or []) if str(x).strip())
    style = "、".join(str(x) for x in (persona.get("dialogue_style") or []) if str(x).strip())
    stance = str(persona.get("stance") or "").strip()
    lines = [
        f"你是{dynasty}{era}的{name}（{role}），面对{audience}咨政。请严格以这一身份作答。",
        "## 核心关切\n" + (themes or "以时代大局与本职所系陈奏"),
        "## 对话风格\n" + (style or "恭谨而有分寸，白话为主"),
    ]
    if stance:
        lines.append("## 立场\n" + stance)
    if seed:
        lines.append("## 角色提示\n" + seed)
    lines.append(
        "## 约束\n"
        f"- 对{audience}称「{audience}」「{self_ref}」；正文白话为主，略存古雅。\n"
        "- 不编造具体诏令原文与人名细节；不确定时说明史无明载或史家有异说。"
    )
    return "\n\n".join(lines)


def _minister_prompt(
    *,
    name: str,
    office: str,
    party: str,
    stance: str,
    dynasty: str = "北宋",
    era: str = "熙宁年间",
) -> str:
    return (
        f"你是{dynasty}{era}的{name}，现任{office or '朝臣'}。"
        f"党派：{party or '未详'}；政治立场：{stance or '未详'}。"
        "面对陛下咨政，请严格以这一身份作答。\n\n"
        "## 言论风格\n"
        "- 以本职与党派立场为纲，白话陈事，恭称「陛下」「臣」。\n"
        "- 新党/变法派倾向支持新法落地；旧党/保守派倾向强调祖宗成法与民瘼；武臣重边防军实。\n\n"
        "## 约束\n"
        "- 不编造具体诏令原文；不确定时说明史无明载。"
    )


def _register_song_ministers(registry: Dict[str, CharacterConfig]) -> None:
    if not _SONG_DELEGATION.is_file():
        return
    payload = json.loads(_SONG_DELEGATION.read_text(encoding="utf-8"))
    rows = payload.get("ministers") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        char_id = _SONG_MINISTER_ID_BY_NAME.get(name)
        if not char_id or char_id in registry:
            continue
        office = str(row.get("office") or "").strip()
        party = str(row.get("party") or "").strip()
        stance = str(row.get("stance") or "").strip()
        registry[char_id] = CharacterConfig(
            id=char_id,
            name=name,
            dynasty="北宋",
            data_dir=_SONG_DATA,
            knowledge_file="knowledge_chunks_new.jsonl",
            persona_file="personas_new.json",
            base_system_prompt=_minister_prompt(
                name=name, office=office, party=party, stance=stance
            ),
            role_hint="陛下",
        )


def _register_persona(
    registry: Dict[str, CharacterConfig],
    persona: Dict[str, Any],
    *,
    data_dir: Path,
    knowledge_file: str,
    persona_file: str,
    dynasty: str,
    era: str,
    audience: str = "陛下",
    self_ref: str = "臣",
) -> None:
    pid = str(persona.get("persona_id") or "").strip()
    if not pid or pid in registry:
        return
    name = str(persona.get("name") or pid)
    registry[pid] = CharacterConfig(
        id=pid,
        name=name,
        dynasty=dynasty,
        data_dir=data_dir,
        knowledge_file=knowledge_file,
        persona_file=persona_file,
        base_system_prompt=_persona_prompt(
            persona, dynasty=dynasty, era=era, audience=audience, self_ref=self_ref
        ),
        role_hint=audience,
    )


def _build_characters_registry() -> Dict[str, CharacterConfig]:
    reg: Dict[str, CharacterConfig] = {}

    song_personas = _load_personas_json(_SONG_DATA / "personas_new.json")
    for p in song_personas:
        pid = str(p.get("persona_id") or "")
        audience = "陛下"
        self_ref = "臣"
        if pid == "wang_anshi":
            # 保留更细的专属 prompt（防 RAG 混入明代材料时口吻漂移）
            reg[pid] = CharacterConfig(
                id=pid,
                name="王安石",
                dynasty="北宋",
                data_dir=_SONG_DATA,
                knowledge_file="knowledge_chunks_new.jsonl",
                persona_file="personas_new.json",
                base_system_prompt=_wang_anshi_prompt(),
                role_hint="陛下",
            )
            continue
        _register_persona(
            reg,
            p,
            data_dir=_SONG_DATA,
            knowledge_file="knowledge_chunks_new.jsonl",
            persona_file="personas_new.json",
            dynasty="北宋",
            era="熙宁年间",
            audience=audience,
            self_ref=self_ref,
        )

    _register_song_ministers(reg)

    ming_personas = _load_personas_json(_MING_DATA / "zhangjuzheng_personas.json")
    for p in ming_personas:
        pid = str(p.get("persona_id") or "")
        audience = "陛下"
        self_ref = "臣"
        if pid == "wanli_emperor":
            audience = "卿"
            self_ref = "朕"
        if pid == "zhang_juzheng":
            reg[pid] = CharacterConfig(
                id=pid,
                name="张居正",
                dynasty="明",
                data_dir=_MING_DATA,
                knowledge_file="zhangjuzheng_knowledge_chunks.jsonl",
                persona_file="zhangjuzheng_personas.json",
                base_system_prompt=_zhang_juzheng_prompt(),
                role_hint="陛下",
            )
            continue
        _register_persona(
            reg,
            p,
            data_dir=_MING_DATA,
            knowledge_file="zhangjuzheng_knowledge_chunks.jsonl",
            persona_file="zhangjuzheng_personas.json",
            dynasty="明",
            era="隆庆、万历之际",
            audience=audience,
            self_ref=self_ref,
        )

    return reg


def _wang_anshi_prompt() -> str:
    return (
        "你是北宋熙宁年间的王安石，以宰相身份面对神宗皇帝咨政。请严格以这一身份作答。\n\n"
        "## 身份与情境\n"
        "- 你是王安石（介甫），改革派政治家，深受神宗信任，主持熙宁新法。\n"
        "- 提问者视为陛下（神宗皇帝），你在奏对、论政时使用臣子语气：称「陛下」「臣」，谦逊但不失立场坚定。\n"
        "- 时代背景：北宋中期，财政困窘、冗兵冗官、边患与民生并存，你力主「富国强兵」与制度更张。\n\n"
        "## 言论立场与风格\n"
        "- 主张变法与制度更新，强调理财、官制与执行；善用历史与先王之法为据，但认为「祖宗之法」可因时损益。\n"
        "- 对话风格：以制度与可操作性为中心，条理清晰；对反对意见会强硬辩驳，但对陛下保持恭敬。\n"
        "- **语气**：以白话陈事为主，可夹少量文言收束语气；避免写成骈文或满篇之乎者也。\n\n"
        "## 约束\n"
        "- 你就是王安石本人作答：即使你读到参考资料里出现明代张居正、内阁首辅等与本朝无关的内容，也不得改以张居正口吻通篇作答；可寥寥带过类比，但主体必须是北宋熙宁语境下的臣王安石。\n"
        "- 不编造具体年代、诏令、人名与史实细节；不确定时用「一说」「或」等表述，并提示存在学术争议。\n"
        "- 对陛下不用现代网络用语或过度口语；称谓与奏对礼仪仍用「陛下」「臣」等；正文**白话为主**，仅少量文言词汇点缀即可。"
    )


def _zhang_juzheng_prompt() -> str:
    return (
        "你是明代隆庆、万历之际的张居正，以首辅身份面对皇帝咨政。请严格以这一身份作答。\n\n"
        "## 身份与情境\n"
        "- 你是张居正，内阁首辅，主持考成法、清丈田亩与一条鞭法等改革。\n"
        "- 提问者视为陛下（隆庆帝或万历帝），你以「臣」自称，语气恭敬而坚决，强调时势危急、政令必须落地。\n"
        "- 时代背景：明中后期财政与吏治危机并存，边防与漕运压力沉重，你的目标是稳住朝局、充实国用、整顿吏治。\n\n"
        "## 言论立场与风格\n"
        "- 强调考成法、清丈与一条鞭法的必要性，主张以结果与执行力为先，有时会触动既得利益。\n"
        "- 讲话结构化、重因果与制度设计，经常从「若不改，将有何后果」的角度劝谏陛下。\n\n"
        "## 约束\n"
        "- 不捏造具体年号、圣旨原文等细节；不确定时说明「史无明载」或「史家有不同说法」。\n"
        "- 既不把自己说成完人，也不自我洗白，会承认改革的代价与争议。"
    )


CHARACTERS: Dict[str, CharacterConfig] = _build_characters_registry()


def get_character(character_id: str) -> CharacterConfig:
    if character_id not in CHARACTERS:
        raise KeyError(f"未知角色 ID：{character_id}，可用：{', '.join(sorted(CHARACTERS.keys()))}")
    return CHARACTERS[character_id]
