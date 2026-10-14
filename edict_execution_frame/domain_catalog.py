# -*- coding: utf-8 -*-
"""九域任务目录 + 逻辑指标名到 METRIC_SCHEMA 键的别名。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from numeric_system.metric_schema import METRIC_SCHEMA

METRIC_KEY_ALIASES: Dict[str, str] = {
    "treasury": "treasury_balance",
    "国库": "treasury_balance",
    "内帑": "inner_treasury_balance",
    "inner_treasury": "inner_treasury_balance",
    "贪腐": "corruption",
    "吏治": "corruption",
    "民变": "unrest",
    "民怨": "unrest",
    "财政吃紧": "fiscal_pressure",
}


@dataclass(frozen=True)
class DomainTaskRow:
    task_key: str
    title_zh: str
    default_executor_zh: str
    default_quarters: int
    action_type: str  # default_machine | named_execution
    expected_effect_profile: Dict[str, str]
    keywords: Tuple[str, ...] = ()
    delegate_allowed: bool = True
    min_task_confidence: float = 0.62
    ambiguity_fallback: bool = False
    # None: inherit DOMAIN_ABILITY_WEIGHTS for the row's domain at resolve time
    ability_weights: Optional[Dict[str, float]] = None
    narrative_mode: str = "delegated_execution"
    task_risk_tags: Tuple[str, ...] = ()
    # P2 委托路径标签：central_direct | provincial_delegate | mixed | imperial_commission
    delegate_route: str = "mixed"


# Logical ability keys (catalog) -> numeric_system.Minister attribute names
LOGICAL_ABILITY_TO_MINISTER: Dict[str, str] = {
    "administration": "ability_internal",
    "integrity": "ability_internal",
    "prestige": "influence",
    "learning": "ability_diplomacy",
    "politics": "ability_internal",
    "military": "ability_military",
    "diplomacy": "ability_diplomacy",
    "fiscal": "ability_finance",
    "management": "ability_internal",
}

# Per-domain default weights (logical keys; normalized in ability module)
DOMAIN_ABILITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "anti_corruption": {
        "integrity": 0.45,
        "administration": 0.30,
        "prestige": 0.15,
        "politics": 0.10,
    },
    "disaster_relief": {
        "administration": 0.45,
        "integrity": 0.20,
        "prestige": 0.20,
        "learning": 0.15,
    },
    "agriculture": {
        "administration": 0.40,
        "learning": 0.30,
        "integrity": 0.15,
        "prestige": 0.15,
    },
    "fiscal": {
        "administration": 0.45,
        "integrity": 0.30,
        "politics": 0.15,
        "learning": 0.10,
    },
    "military": {
        "military": 0.55,
        "prestige": 0.25,
        "administration": 0.15,
        "politics": 0.05,
    },
    "diplomacy": {
        "diplomacy": 0.55,
        "prestige": 0.20,
        "politics": 0.15,
        "learning": 0.10,
    },
    "personnel": {
        "administration": 0.45,
        "integrity": 0.30,
        "politics": 0.15,
        "prestige": 0.10,
    },
    "engineering": {
        "administration": 0.45,
        "learning": 0.30,
        "integrity": 0.15,
        "prestige": 0.10,
    },
    "public_order": {
        "military": 0.35,
        "administration": 0.30,
        "prestige": 0.20,
        "integrity": 0.15,
    },
    "general": {
        "administration": 0.35,
        "politics": 0.25,
        "prestige": 0.20,
        "integrity": 0.20,
    },
}


def effective_ability_weights(domain: str, row: "DomainTaskRow") -> Dict[str, float]:
    """Merge DOMAIN_ABILITY_WEIGHTS[domain] with row-level overrides."""
    base = dict(DOMAIN_ABILITY_WEIGHTS.get(domain) or DOMAIN_ABILITY_WEIGHTS["general"])
    ow = getattr(row, "ability_weights", None)
    if ow:
        base.update(dict(ow))
    return base


def logical_weights_to_minister_weights(logical: Dict[str, float]) -> Dict[str, float]:
    """Map catalog logical keys to Minister dataclass fields (sums preserved)."""
    out: Dict[str, float] = {}
    for lk, w in (logical or {}).items():
        try:
            wf = float(w)
        except (TypeError, ValueError):
            continue
        mk = LOGICAL_ABILITY_TO_MINISTER.get(str(lk).strip())
        if not mk:
            continue
        # integrity: split across internal + influence for gameplay variety
        if str(lk).strip() == "integrity":
            out["ability_internal"] = out.get("ability_internal", 0.0) + wf * 0.55
            out["influence"] = out.get("influence", 0.0) + wf * 0.45
        else:
            out[mk] = out.get(mk, 0.0) + wf
    return out


def _prof(**kwargs: str) -> Dict[str, str]:
    return {k: v for k, v in kwargs.items() if v}


# 九域骨架：每域至少一条默认可解析任务（expected keys 须为 schema 键或经别名映射）
DOMAIN_TASK_CATALOG: Dict[str, List[DomainTaskRow]] = {
    "anti_corruption": [
        DomainTaskRow(
            task_key="strict_local_probe",
            title_zh="严查地方贪墨",
            default_executor_zh="都察院与吏部",
            default_quarters=1,
            action_type="named_execution",
            expected_effect_profile=_prof(
                corruption="down_strong",
                treasury_balance="up_small",
                authority="up_medium",
                unrest="up_small",
            ),
            keywords=(
                "肃贪",
                "反贪",
                "贪墨",
                "贪官",
                "贪腐",
                "严查",
                "彻查",
                "清查",
                "查贪",
                "吏治腐败",
            ),
            delegate_route="imperial_commission",
        ),
        DomainTaskRow(
            task_key="routine_audit",
            title_zh="按例清查吏案",
            default_executor_zh="御史台与户部",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_small",
                fiscal_pressure="up_small",
                authority="neutral",
            ),
            keywords=("整饬吏治", "吏治"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="reform_audit_sansi",
            title_zh="条例司勘核三司簿籍",
            default_executor_zh="制置三司条例司",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_medium",
                tax_completion_index="up_small",
                authority="up_small",
                fiscal_pressure="up_small",
            ),
            keywords=("三司", "条例司", "勘核", "簿籍", "青苗", "隐漏", "转运", "漕运"),
            delegate_route="imperial_commission",
        ),
        DomainTaskRow(
            task_key="market_monopoly_graft",
            title_zh="严查市易侵渔",
            default_executor_zh="户部与市易司",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_medium",
                treasury_balance="up_small",
                public_support="down_small",
                fiscal_pressure="up_small",
            ),
            keywords=("市易", "侵渔", "和买", "舞弊", "市易司", "苛敛"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="river_work_embezzle",
            title_zh="纠察河工冒领",
            default_executor_zh="工部与都水监",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_medium",
                treasury_balance="down_small",
                disaster_index="down_small",
                public_support="up_small",
            ),
            keywords=("河工", "堤工", "冒领", "工料", "克扣", "都水", "黄河"),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("engineering_delay", "flood_risk"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="hidden_land_gentry",
            title_zh="清查隐田庇奸",
            default_executor_zh="户部与诸路转运司",
            default_quarters=3,
            action_type="named_execution",
            expected_effect_profile=_prof(
                corruption="down_medium",
                tax_completion_index="up_small",
                authority="up_small",
                unrest="up_small",
            ),
            keywords=("隐田", "方田", "丈量", "豪强", "庇奸", "诡名", "漏税"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="relief_grain_embezzle",
            title_zh="严查赈粮仓胥",
            default_executor_zh="户部与提刑司",
            default_quarters=3,
            action_type="named_execution",
            expected_effect_profile=_prof(
                corruption="down_strong",
                public_support="up_medium",
                treasury_balance="down_medium",
                unrest="down_small",
            ),
            keywords=("赈银", "侵吞", "仓胥", "克扣", "赈粮", "漕粮", "开仓"),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("grain_embezzlement", "transport_delay"),
            delegate_route="imperial_commission",
        ),
        DomainTaskRow(
            task_key="memorial_screen_impeachment",
            title_zh="台谏甄别诬告",
            default_executor_zh="御史台与中书省",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_small",
                authority="up_medium",
                unrest="up_small",
                fiscal_pressure="neutral",
            ),
            keywords=("诬告", "甄别诬告", "弹劾", "论吏", "纠弹", "甄别"),
            delegate_route="central_direct",
        ),
    ],
    "disaster_relief": [
        DomainTaskRow(
            task_key="open_granary_relief",
            title_zh="开仓赈济灾民",
            default_executor_zh="户部与地方官",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_medium",
                treasury_balance="down_small",
                disaster_index="down_medium",
                unrest="down_small",
            ),
            keywords=(
                "开仓",
                "发仓",
                "放粮",
                "赈仓",
                "水患",
                "赈济",
                "赈灾",
                "灾民",
                "饥荒",
                "救灾",
                "安抚",
                "流民",
                "饥馑",
                "抚恤",
            ),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("grain_shortage", "local_corruption", "transport_delay"),
            delegate_route="mixed",
        ),
        DomainTaskRow(
            task_key="tax_remission_relief",
            title_zh="蠲免缓征以纾灾",
            default_executor_zh="户部与地方官",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_medium",
                tax_completion_index="down_small",
                fiscal_pressure="up_small",
                disaster_index="down_small",
            ),
            keywords=("蠲免", "免赋", "缓征", "蠲赋", "停征", "除赋", "除租"),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("fiscal_gap", "local_underreport"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="dispatch_imperial_commissioner",
            title_zh="遣钦差督办赈务",
            default_executor_zh="内阁与户部",
            default_quarters=3,
            action_type="named_execution",
            expected_effect_profile=_prof(
                public_support="up_strong",
                treasury_balance="down_medium",
                disaster_index="down_strong",
                corruption="up_small",
            ),
            keywords=("钦差", "专办", "遣大臣", "督办赈", "钦命赈", "钦使"),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("center_local_tension", "commissioner_risk"),
            delegate_route="imperial_commission",
        ),
        DomainTaskRow(
            task_key="local_official_relief",
            title_zh="责成地方就地赈济",
            default_executor_zh="巡抚与州县",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                treasury_balance="down_small",
                disaster_index="down_small",
                fiscal_pressure="neutral",
            ),
            keywords=("巡抚", "地方官", "州县", "就地", "自理", "令地方", "地方赈", "安顿流民"),
            narrative_mode="relief_and_logistics",
            task_risk_tags=("local_coverup", "execution_variance"),
            delegate_route="provincial_delegate",
        ),
    ],
    "agriculture": [
        DomainTaskRow(
            task_key="spring_encourage_farming",
            title_zh="劝课农桑",
            default_executor_zh="户部与州县",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                tax_completion_index="up_small",
                fiscal_pressure="neutral",
            ),
            keywords=(
                "农业",
                "春耕",
                "劝农",
                "农桑",
                "劝课",
                "农时",
                "稼穑",
                "播种",
                "蚕桑",
                "桑麻",
                "力穑",
                "督农",
                "勿误农时",
                "下种",
            ),
            narrative_mode="agriculture_extension",
            task_risk_tags=("false_report", "disturb_farmers"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="irrigation_or_land_improvement",
            title_zh="兴修农田水利",
            default_executor_zh="户部与工部",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                disaster_index="down_small",
                treasury_balance="down_medium",
                fiscal_pressure="up_small",
            ),
            keywords=(
                "农田水利",
                "陂塘",
                "灌溉",
                "淤田",
                "垦田",
                "兴修水利",
                "疏浚农渠",
                "筑陂",
                "水利利便",
                "膏腴",
            ),
            narrative_mode="agriculture_infrastructure",
            task_risk_tags=("corvee_dispute", "project_delay"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="mulberry_silk_promotion",
            title_zh="广植桑麻与蚕课",
            default_executor_zh="户部与州县",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                tax_completion_index="up_small",
                treasury_balance="up_small",
                unrest="up_small",
            ),
            keywords=(
                "改稻为桑",
                "植桑",
                "桑柘",
                "桑田",
                "蚕桑",
                "丝绵",
                "课桑",
                "蚕事",
                "衣被天下",
            ),
            narrative_mode="agriculture_sericulture",
            task_risk_tags=("food_security", "sericulture_overreach"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="spring_grain_lending",
            title_zh="春前给散贷种",
            default_executor_zh="户部与常平司",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                treasury_balance="down_small",
                tax_completion_index="up_small",
                fiscal_pressure="up_small",
            ),
            keywords=(
                "春前给散",
                "贷种",
                "备春耕",
                "给散",
                "常平给散",
                "散种",
                "春贷",
            ),
            narrative_mode="agriculture_fiscal_bridge",
            task_risk_tags=("usury_abuse", "spring_timing_slip"),
            delegate_route="central_direct",
        ),
    ],
    "fiscal": [
        DomainTaskRow(
            task_key="tax_collection_push",
            title_zh="清厘赋役与积欠",
            default_executor_zh="户部与税课司",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                tax_completion_index="up_small",
                fiscal_pressure="down_small",
                public_support="down_small",
            ),
            keywords=(
                "钱粮",
                "赋役",
                "逋欠",
                "积欠",
                "完纳",
                "追比",
                "清厘",
                "催征",
                "税课",
                "岁课",
                "税籍",
                "括户",
                "磨勘",
                "勾考",
                "旧欠",
                "岁输",
                "税负",
                "平衡税负",
                "均平赋役",
            ),
            narrative_mode="fiscal_collection",
            task_risk_tags=("tax_resistance", "gentry_obstruction"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="increase_tax_levy",
            title_zh="加征以充国用",
            default_executor_zh="户部与三司",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                tax_completion_index="up_small",
                treasury_balance="up_small",
                public_support="down_medium",
                unrest="up_small",
            ),
            keywords=(
                "加派",
                "加征",
                "增纳",
                "权增",
                "助军钱",
                "边饷",
                "量户等第",
                "别纳",
                "增输",
                "加一成",
                "加税",
                "权加",
                "复旧",
            ),
            narrative_mode="fiscal_levy",
            task_risk_tags=("popular_backlash", "merchant_flight"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="reduce_court_spending",
            title_zh="裁冗节流",
            default_executor_zh="三司与户部",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                fiscal_pressure="down_medium",
                treasury_balance="up_small",
                public_support="up_small",
                authority="neutral",
            ),
            keywords=(
                "裁冗",
                "节流",
                "裁省",
                "冗费",
                "浮费",
                "停罢营造",
                "节内帑",
                "减支",
                "供亿",
                "节财",
                "停给",
                "宫禁",
                "内帑",
                "停罢",
                "造作",
            ),
            narrative_mode="fiscal_austerity",
            task_risk_tags=("court_resistance", "service_disruption"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="expand_state_monopoly",
            title_zh="市易禁榷开源",
            default_executor_zh="户部与市易司",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                treasury_balance="up_medium",
                public_support="down_small",
                fiscal_pressure="down_small",
                corruption="up_small",
            ),
            keywords=(
                "市易",
                "市易务",
                "市易法",
                "榷货",
                "榷盐",
                "榷茶",
                "商税",
                "平准",
                "收息",
                "禁私贩",
                "禁榷",
            ),
            narrative_mode="fiscal_monopoly",
            task_risk_tags=("merchant_backlash", "monopoly_abuse"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="corvee_commutation",
            title_zh="推行免役钱代",
            default_executor_zh="户部与州县",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                tax_completion_index="up_small",
                fiscal_pressure="up_small",
                unrest="down_small",
            ),
            keywords=(
                "免役",
                "募役",
                "助役钱",
                "钱代役",
                "输钱免役",
                "差役",
                "雇役",
                "助役",
            ),
            narrative_mode="fiscal_corvee",
            task_risk_tags=("levy_inequity", "elite_evasion"),
            delegate_route="provincial_delegate",
        ),
        DomainTaskRow(
            task_key="equalized_transport",
            title_zh="均输调剂漕贡",
            default_executor_zh="户部与发运司",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                treasury_balance="up_small",
                fiscal_pressure="down_small",
                public_support="neutral",
            ),
            keywords=(
                "均输",
                "均输法",
                "发运使",
                "发运司",
                "漕运",
                "漕贡",
                "上供",
                "徙贵就贱",
                "用近易远",
                "转输",
            ),
            narrative_mode="fiscal_transport",
            task_risk_tags=("transport_loss", "regional_friction"),
            delegate_route="central_direct",
        ),
        DomainTaskRow(
            task_key="abolish_state_monopoly",
            title_zh="废止市易禁榷",
            default_executor_zh="户部与中书",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                treasury_balance="down_small",
                fiscal_pressure="up_small",
                corruption="down_small",
            ),
            keywords=(
                "罢市易",
                "罢市易务",
                "停市易",
                "革市易",
                "撤销市易",
                "废止市易",
                "停市易法",
            ),
            narrative_mode="fiscal_monopoly_repeal",
            task_risk_tags=("merchant_relief", "revenue_shortfall"),
            delegate_route="central_direct",
        ),
    ],
    "military": [
        DomainTaskRow(
            task_key="campaign_against",
            title_zh="出师讨伐",
            default_executor_zh="枢密与边帅",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                army_morale="up_medium",
                army_supply="down_medium",
                revolt_risk="down_medium",
                treasury_balance="down_medium",
            ),
            keywords=("讨伐", "征讨", "进兵", "攻伐", "开战", "击贼", "讨贼"),
            delegate_route="provincial_delegate",
            task_risk_tags=("campaign_defeat", "supply_line_cut"),
        ),
        DomainTaskRow(
            task_key="border_readiness",
            title_zh="整饬边防",
            default_executor_zh="兵部与边将",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                army_morale="up_small",
                army_supply="up_small",
                treasury_balance="down_small",
                unrest="neutral",
            ),
            keywords=("边患", "边防", "整军", "军备", "边境", "不宁", "备边", "戍边"),
            delegate_route="provincial_delegate",
            task_risk_tags=("frontier_pressure",),
        ),
    ],
    "diplomacy": [
        DomainTaskRow(
            task_key="tributary_stability",
            title_zh="抚驭外藩与朝贡秩序",
            default_executor_zh="礼部与鸿胪寺",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                authority="up_small",
                treasury_balance="down_small",
                public_support="neutral",
            ),
            keywords=("外交", "番邦", "朝贡", "外藩", "抚驭", "修明"),
        ),
    ],
    "personnel": [
        DomainTaskRow(
            task_key="merit_appointment",
            title_zh="擢用与除授",
            default_executor_zh="中书门下与吏部",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                authority="up_small",
                public_support="neutral",
                fiscal_pressure="up_small",
            ),
            keywords=("擢用", "除授", "拜为", "权知", "平章事", "参政", "出任", "署理", "入中枢", "召", "召回", "秉政"),
        ),
        DomainTaskRow(
            task_key="censure_and_removal",
            title_zh="黜罢与夺职",
            default_executor_zh="台谏与吏部",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                authority="up_small",
                corruption="down_small",
                public_support="down_small",
            ),
            keywords=("黜罢", "罢黜", "夺职", "削职", "编窜", "台谏", "纠劾", "罢相"),
        ),
        DomainTaskRow(
            task_key="official_evaluation",
            title_zh="考课与铨选",
            default_executor_zh="吏部与都察院",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_small",
                authority="up_small",
                fiscal_pressure="up_small",
            ),
            keywords=("人事", "考课", "铨选", "百官", "磨勘", "考成", "访察", "整肃吏治"),
        ),
    ],
    "engineering": [
        DomainTaskRow(
            task_key="river_dike_repair",
            title_zh="修缮黄河堤防",
            default_executor_zh="工部与地方河道官",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                disaster_index="down_small",
                treasury_balance="down_medium",
                public_support="up_small",
            ),
            keywords=("黄河", "堤防", "河工", "修缮", "岁修", "防汛", "河患", "损坏"),
            delegate_route="provincial_delegate",
            task_risk_tags=("engineering_delay", "flood_risk"),
        ),
    ],
    "public_order": [
        DomainTaskRow(
            task_key="mountain_bandit_campaign",
            title_zh="山地剿匪",
            default_executor_zh="兵部与诸路将佐",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                unrest="down_medium",
                revolt_risk="down_small",
                army_supply="down_medium",
            ),
            keywords=("山寨", "沿山", "险阻", "洞蛮", "山林", "山地"),
            delegate_route="provincial_delegate",
            task_risk_tags=("ambush_risk", "supply_drain"),
        ),
        DomainTaskRow(
            task_key="urban_order",
            title_zh="坊市夜禁与京师治安",
            default_executor_zh="开封府与巡尉",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                unrest="down_small",
                public_support="up_small",
                authority="up_small",
            ),
            keywords=("京师", "坊市", "夜禁", "盗窃", "汴京", "开封"),
            delegate_route="provincial_delegate",
            task_risk_tags=("over_policing", "merchant_unrest"),
        ),
        DomainTaskRow(
            task_key="patrol_order",
            title_zh="巡缉靖安",
            default_executor_zh="州县巡尉与保甲",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                unrest="down_small",
                revolt_risk="down_small",
                public_support="up_small",
            ),
            keywords=("巡缉", "缉盗", "保甲", "巡捕"),
            delegate_route="provincial_delegate",
            task_risk_tags=("petty_corruption",),
        ),
        DomainTaskRow(
            task_key="bandit_suppression",
            title_zh="剿匪与靖安地方",
            default_executor_zh="兵部与地方营伍",
            default_quarters=2,
            action_type="default_machine",
            expected_effect_profile=_prof(
                unrest="down_medium",
                revolt_risk="down_small",
                army_supply="down_small",
            ),
            keywords=("治安", "剿匪", "剿捕", "盗贼", "匪患", "剿讨"),
            delegate_route="provincial_delegate",
            task_risk_tags=("bandit_resistance", "supply_drain"),
        ),
    ],
    "general": [
        DomainTaskRow(
            task_key="steady_governance",
            title_zh="稳步推行政务",
            default_executor_zh="内阁与部院",
            default_quarters=1,
            action_type="default_machine",
            expected_effect_profile=_prof(
                public_support="up_small",
                fiscal_pressure="neutral",
            ),
            keywords=(),
        ),
        DomainTaskRow(
            task_key="local_governance_cleanup",
            title_zh="地方吏治整饬",
            default_executor_zh="都察院与吏部",
            default_quarters=3,
            action_type="default_machine",
            expected_effect_profile=_prof(
                corruption="down_medium",
                authority="up_small",
                fiscal_pressure="up_small",
            ),
            keywords=("积弊", "整饬", "严加", "吏治", "料理", "地方", "诸务", "处置"),
        ),
    ],
}


_INTENT_DOMAIN_HINT: Dict[str, str] = {
    "strict_governance": "anti_corruption",
    "disaster_relief": "disaster_relief",
    "tax_relief": "fiscal",
    "welfare": "disaster_relief",
}


def canonical_metric_key(logical: str) -> str:
    k = str(logical or "").strip()
    if k in METRIC_SCHEMA:
        return k
    return METRIC_KEY_ALIASES.get(k, k)


def normalize_effect_profile_keys(profile: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for lk, tier in (profile or {}).items():
        ck = canonical_metric_key(lk)
        if ck in METRIC_SCHEMA:
            out[ck] = str(tier or "").strip() or "neutral"
    return out


_FISCAL_GENERIC_KW = frozenset(
    {"钱粮", "赋役", "岁课", "税课", "完纳", "追比", "清厘", "催征", "税籍"}
)


def _kw_hit_weight(domain: str, kw: str) -> int:
    if domain == "fiscal" and kw in _FISCAL_GENERIC_KW:
        return 2
    return 3


def _score_row(text: str, row: DomainTaskRow, *, domain: str = "") -> Tuple[int, int]:
    t = text or ""
    score = 0
    hits = 0
    for kw in row.keywords:
        if kw and kw in t:
            if (
                row.task_key == "expand_state_monopoly"
                and kw == "市易"
                and re.search(r"(罢|停|革|废止|撤销|撤除)", t)
            ):
                continue
            score += _kw_hit_weight(domain, kw)
            hits += 1
    return score, hits


def select_task_row_for_domain(domain: str, edict_text: str) -> DomainTaskRow:
    """同域内按关键词选一条；无命中取首条。同分则命中词数多者优先。"""
    rows = DOMAIN_TASK_CATALOG.get(domain) or DOMAIN_TASK_CATALOG["general"]
    text = edict_text or ""
    if domain == "fiscal" and re.search(
        r"(罢|停|革|撤销|废止|撤除).{0,8}(市易|榷货|榷盐|榷茶|市易务|市易法)", text
    ):
        for row in rows:
            if row.task_key == "abolish_state_monopoly":
                return row
    best = rows[0]
    best_score, best_hits = _score_row(text, best, domain=domain)
    for row in rows[1:]:
        sc, hits = _score_row(text, row, domain=domain)
        if sc > best_score or (sc == best_score and hits > best_hits):
            best, best_score, best_hits = row, sc, hits
    return best


def lookup_task_row(domain: str, task_key: str) -> Optional[DomainTaskRow]:
    dom = (domain or "").strip()
    tk = (task_key or "").strip()
    if not dom or not tk:
        return None
    for row in DOMAIN_TASK_CATALOG.get(dom) or []:
        if row.task_key == tk:
            return row
    return None


def catalog_domain_ids() -> Set[str]:
    return {str(k) for k in DOMAIN_TASK_CATALOG.keys() if k and k != "general"}


def catalog_playbook_keys() -> Set[Tuple[str, str]]:
    out: Set[Tuple[str, str]] = set()
    for dom, rows in DOMAIN_TASK_CATALOG.items():
        if dom == "general":
            continue
        for row in rows:
            out.add((dom, row.task_key))
    return out


def build_playbook_whitelist_for_llm(*, max_per_domain: int = 8) -> List[Dict[str, str]]:
    """供 LLM prompt 使用的紧凑 playbook 白名单。"""
    entries: List[Dict[str, str]] = []
    for dom in sorted(catalog_domain_ids()):
        rows = DOMAIN_TASK_CATALOG.get(dom) or []
        for row in rows[: max(1, int(max_per_domain))]:
            entries.append(
                {
                    "domain": dom,
                    "task_key": row.task_key,
                    "title_zh": row.title_zh,
                }
            )
    return entries


def resolve_domain_from_semantic_and_text(
    *,
    trace_domain: str,
    l3_intent: str,
    edict_text: str,
) -> str:
    """从解析 trace 的板块、L3 intent、正文关键词推断 catalog 域。"""
    from edict_execution_frame.fiscal_clarification import is_fiscal_goal_vague

    if is_fiscal_goal_vague(edict_text or ""):
        return "fiscal"
    text = edict_text or ""
    if re.search(r"(黜罢|罢黜|夺职|削职|编窜|罢相)", text):
        return "personnel"
    if re.search(r"(擢用|除授|权知|拜为|平章事|参政|署理)", text):
        return "personnel"
    if re.search(r"(考课|铨选|磨勘|考成)", text) and not re.search(
        r"(贪墨|肃贪|反贪|贪腐|赃|贪|赃吏)", text
    ):
        return "personnel"
    intent_dom = _INTENT_DOMAIN_HINT.get((l3_intent or "").strip())
    if intent_dom:
        return intent_dom
    td = (trace_domain or "").strip().lower()
    if td in DOMAIN_TASK_CATALOG and td != "general":
        return td
    # 关键词跨域扫描
    best_dom = "general"
    best_score = 0
    for dom, rows in DOMAIN_TASK_CATALOG.items():
        if dom == "general":
            continue
        for row in rows:
            sc, _ = _score_row(text, row, domain=dom)
            if sc > best_score:
                best_score = sc
                best_dom = dom
    if best_score > 0:
        return best_dom
    # 板块英文/中文粗映射
    military_kw = re.compile(r"(军|兵|边|战|武备)")
    if military_kw.search(text) or td in ("military", "军"):
        return "military"
    if td in ("internal", "内政"):
        if re.search(r"(水|灾|赈|饥)", text):
            return "disaster_relief"
        return "general"
    return "general"


_SLUG = re.compile(r"[^a-zA-Z0-9_\u4e00-\u9fff]+")


def slug_frame_id(edict_text: str, task_key: str) -> str:
    base = _SLUG.sub("_", (edict_text or "").strip()).strip("_")[:24] or "edict"
    return f"{base}_{task_key}"[:56]
