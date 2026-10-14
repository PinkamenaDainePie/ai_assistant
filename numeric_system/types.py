from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TreasurySnapshot:
    balance_liang: float = 0.0
    total_income_liang: float = 0.0
    total_expense_liang: float = 0.0


@dataclass
class LandBlock:
    name: str
    faction: str
    total_tax_liang: float
    tax_multiplier: float
    tax_completion: float
    public_support: float
    unrest: float
    disaster_level: str


@dataclass
class TaxRule:
    land_type: str
    total_tax_per_mu: float


@dataclass
class ArmyUnit:
    name: str
    faction: str
    supply: float
    morale: float
    total_people: float
    extra_cost_per_person: float
    maintenance_liang: float


@dataclass
class NavyUnit:
    name: str
    faction: str
    supply: float
    morale: float
    sailors: float
    maintenance_liang: float


@dataclass
class StrataGroup:
    name: str
    satisfaction: float
    influence: float
    revolt_risk: float


@dataclass
class Minister:
    name: str
    office: str
    party: str
    stance: str
    influence: float
    # 0–100，缺表列时由 loader 填默认 50
    ability_internal: float = 50.0
    ability_military: float = 50.0
    ability_diplomacy: float = 50.0
    ability_finance: float = 50.0


@dataclass
class ArmyType:
    name: str
    equipment_requirement: str
    maintenance_liang: float
    description: str = ""


@dataclass
class ShipType:
    name: str
    light_cannon_count: float
    heavy_cannon_count: float
    maintenance_liang: float
    description: str = ""


@dataclass
class EquipmentItem:
    name: str
    stock: float
    quarterly_output: float
    description: str = ""


@dataclass
class FactionPower:
    name: str
    ruler: str
    public_support: float
    population: float
    corruption: float
    authority: float
    currency_supply: str
    controlled_blocks: str


@dataclass
class PartyGroup:
    name: str
    influence: float
    support: float
    stance: str = ""
    description: str = ""


@dataclass
class NumericData:
    treasury: TreasurySnapshot = field(default_factory=TreasurySnapshot)
    inner_treasury: TreasurySnapshot = field(default_factory=TreasurySnapshot)
    land_blocks: List[LandBlock] = field(default_factory=list)
    tax_rules: List[TaxRule] = field(default_factory=list)
    armies: List[ArmyUnit] = field(default_factory=list)
    navies: List[NavyUnit] = field(default_factory=list)
    strata: List[StrataGroup] = field(default_factory=list)
    ministers: List[Minister] = field(default_factory=list)
    army_types: List[ArmyType] = field(default_factory=list)
    ship_types: List[ShipType] = field(default_factory=list)
    equipment_items: List[EquipmentItem] = field(default_factory=list)
    faction_powers: List[FactionPower] = field(default_factory=list)
    party_groups: List[PartyGroup] = field(default_factory=list)


@dataclass
class QuarterState:
    quarter_index: int = 1
    metrics: Dict[str, float] = field(
        default_factory=lambda: {
            "treasury_balance": 0.0,
            "inner_treasury_balance": 0.0,
            "public_support": 50.0,
            "unrest": 30.0,
            "fiscal_pressure": 30.0,
        }
    )
    flags: Dict[str, bool] = field(default_factory=dict)
    policy_tree: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 运行时地区状态（按 route_id 如 "jinghunan"）：occupied / disaster 等
    # 由 set_region_status effect 写入，季末 tick 更新 ignored_quarters、revolt 等
    region_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 运行时大臣状态（按姓名）：active(默认) / dead / dismissed
    # 由 set_minister_status effect 写入；静态 NumericData.ministers 为初始名册
    minister_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)

