# -*- coding: utf-8 -*-
"""场景注册表：每个历史剧本对应一个 ScenarioProfile。

新增场景只需在 SCENARIOS 中追加一条记录；核心 pipeline（解析、结算、
事件、执行帧）从 profile 中读取配置，无需修改各自的业务逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

# 项目根目录（biaoge/ 等相对路径的基点）
_ROOT = Path(__file__).resolve().parent.parent


def _abs(rel: str) -> str:
    """将相对项目根的路径转为绝对路径字符串。"""
    return str(_ROOT / rel)


@dataclass(frozen=True)
class ScenarioProfile:
    """一个可游玩历史场景的全部元数据配置。"""

    id: str
    """唯一场景 ID，如 'song_xining'。"""

    label_zh: str
    """中文标题，用于 UI 展示。"""

    dynasty: str
    """朝代名，如 '北宋' / '明'。"""

    reign_title: str
    """年号，如 '熙宁' / '万历'。"""

    year_label: str
    """开局年份标签，如 '熙宁二年 春'。"""

    data_root: str
    """数值表格（biaoge/）根目录绝对路径，由 loader 使用。"""

    map_image: str
    """前端地图图片路径（public/ 下相对路径），如 '/maps/china_north_song.png'。"""

    event_era_tags: Tuple[str, ...]
    """事件目录中 era_tags 白名单；EventService.roll() 仅抽此列表内的事件。"""

    character_ids: Tuple[str, ...]
    """本场景可用的 AI 角色 id 列表（对应 renwu_module/characters.py CHARACTERS）。"""

    completion_personas: Tuple[str, ...]
    """模糊诏书补全时，按优先级考虑的具名大臣（需与大臣表一致）。"""

    description_zh: str = ""
    """向玩家展示的剧本简介（可多行）。"""


SCENARIOS: Dict[str, ScenarioProfile] = {
    "song_xining": ScenarioProfile(
        id="song_xining",
        label_zh="熙宁变法",
        dynasty="北宋",
        reign_title="熙宁",
        year_label="熙宁元年 春",
        data_root=_abs("biaoge/song"),
        map_image="/maps/china_north_song.png",
        event_era_tags=("song", "xining"),
        character_ids=(
            "wang_anshi",
            "sima_guang",
            "lv_huiqing",
            "su_shi",
            "zhang_dun",
            "shen_kuo",
            "zeng_bu",
            "wen_yanbo",
            "han_qi",
            "fu_bi",
            "han_jiang",
            "cai_que",
            "lv_gongzhu",
            "su_zhe",
            "chen_shengzhi",
            "wang_gui",
            "wu_chong",
            "wang_shao",
            "guo_kui",
            "zhong_e",
            "xue_xiang",
        ),
        completion_personas=("王安石", "沈括", "章惇"),
        description_zh=(
            "熙宁二年，宋神宗锐意变法，王安石以参知政事身份主持新法。\n"
            "你将在财政困窘、边患频仍的北宋中期，权衡改革步伐与政局稳定。\n"
            "（经典版：季度推演引擎 :8000）"
        ),
    ),
    "song_xining_v2": ScenarioProfile(
        id="song_xining_v2",
        label_zh="熙宁变法（新引擎）",
        dynasty="北宋",
        reign_title="熙宁",
        year_label="熙宁元年 正月",
        data_root=_abs("biaoge/song"),
        map_image="/maps/china_north_song.png",
        event_era_tags=("song", "xining", "salvage"),
        character_ids=(
            "wang_anshi",
            "sima_guang",
            "lv_huiqing",
            "su_shi",
            "zhang_dun",
            "shen_kuo",
        ),
        completion_personas=("王安石", "沈括", "章惇"),
        description_zh=(
            "熙宁变法 salvage 版：月度模拟，内容包 content/scenarios/song_xining_v2/。\n"
            "与 song_xining quarter 经典版并行，验收通过后下线经典版。"
        ),
    ),
    "ming_wanli": ScenarioProfile(
        id="ming_wanli",
        label_zh="万历改革",
        dynasty="明",
        reign_title="万历",
        year_label="万历元年 春",
        # 明代专用数值目录（与 biaoge/song 分离）
        data_root=_abs("biaoge/ming"),
        map_image="/maps/china_north_song.png",  # 占位；待专属地图制作后替换
        event_era_tags=("ming", "wanli"),
        character_ids=(
            "zhang_juzheng",
            "empress_dowager_li",
            "feng_bao",
            "gao_gong",
            "qi_jiguang",
            "li_chengliang",
            "pan_jixun",
            "conservative_gentry",
            "local_county_magistrate",
        ),
        completion_personas=("张居正", "海瑞"),
        description_zh=(
            "万历初年，张居正以内阁首辅身份主持考成法与一条鞭法改革。\n"
            "你将在吏治积弊、财政危机的明代中期，推动制度革新。\n"
            "（本场景数值内容持续完善中）"
        ),
    ),
}


def get_scenario(scenario_id: str) -> ScenarioProfile:
    """获取场景配置；未知 ID 时抛出 KeyError。"""
    if scenario_id not in SCENARIOS:
        raise KeyError(
            f"未知场景 ID：{scenario_id!r}，可用：{', '.join(SCENARIOS)}"
        )
    return SCENARIOS[scenario_id]


def list_scenarios() -> list[dict]:
    """返回所有场景的摘要列表（供前端 GET /scenarios 接口使用）。"""
    return [
        {
            "id": p.id,
            "label_zh": p.label_zh,
            "dynasty": p.dynasty,
            "reign_title": p.reign_title,
            "year_label": p.year_label,
            "map_image": p.map_image,
            "description_zh": p.description_zh,
        }
        for p in SCENARIOS.values()
    ]
