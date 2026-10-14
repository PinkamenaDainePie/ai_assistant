"""战役时间锚点：按激活剧本或环境变量解析开局年月与合法年份范围。

默认（无自定义剧本）：1627.10 崇祯。ming_wanli 剧本：1573.01 万历元年。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from ming_sim.scenario_active import active_scenario_dir, active_scenario_id


@dataclass(frozen=True)
class CampaignAnchor:
    start_year: int
    start_month: int
    year_min: int
    year_max: int
    campaign_years: int = 20
    reign_label: str = "崇祯"

    @property
    def timeout_turn(self) -> int:
        """满 N 个自然月仍未分胜负则 timeout（与旧版 TIMEOUT_TURN=240 口径一致）。"""
        return self.campaign_years * 12

    def turn_from_ym(self, year: int, month: int) -> int:
        return (year - self.start_year) * 12 + (month - self.start_month) + 1

    def ym_from_turn(self, turn: int) -> Tuple[int, int]:
        total = self.start_year * 12 + self.start_month - 1 + max(0, turn - 1)
        return total // 12, total % 12 + 1

    def default_start_ym(self) -> str:
        return f"{self.start_year:04d}.{self.start_month:02d}"

    def validate_ym(self, year: int, month: int) -> None:
        if not (1 <= month <= 12):
            raise SystemExit(f"月份非法：{month}，须 1–12。")
        if not (self.year_min <= year <= self.year_max):
            raise SystemExit(
                f"年份 {year} 超出本剧本范围 {self.year_min}–{self.year_max}（{self.reign_label}）。"
            )


_CHONGZHEN = CampaignAnchor(
    start_year=1627,
    start_month=10,
    year_min=1627,
    year_max=1644,
    campaign_years=20,
    reign_label="崇祯",
)

_WANLI = CampaignAnchor(
    start_year=1573,
    start_month=1,
    year_min=1573,
    year_max=1593,
    campaign_years=20,
    reign_label="万历",
)

_PRESETS: dict[str, CampaignAnchor] = {
    "ming_wanli": _WANLI,
}


def _load_campaign_json(scenario_dir: str) -> Optional[CampaignAnchor]:
    path = os.path.join(scenario_dir, "campaign.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        sy = int(data["start_year"])
        sm = int(data["start_month"])
        y0 = int(data.get("year_min", sy))
        y1 = int(data.get("year_max", sy + int(data.get("campaign_years", 20))))
        years = int(data.get("campaign_years", 20))
        label = str(data.get("reign_label") or data.get("label") or "").strip()
    except (KeyError, TypeError, ValueError):
        return None
    return CampaignAnchor(
        start_year=sy,
        start_month=sm,
        year_min=y0,
        year_max=y1,
        campaign_years=years,
        reign_label=label or "明",
    )


def get_campaign_anchor() -> CampaignAnchor:
    """解析当前生效战役锚点（激活剧本 > 预设 id > 环境变量 > 崇祯默认）。"""
    sid = active_scenario_id()
    scenario_dir = active_scenario_dir()
    if scenario_dir:
        loaded = _load_campaign_json(scenario_dir)
        if loaded:
            return loaded
    if sid in _PRESETS:
        return _PRESETS[sid]

    env_ym = os.environ.get("MING_SIM_START_YM", "").strip()
    if env_ym:
        try:
            y_str, m_str = env_ym.split(".")
            y, m = int(y_str), int(m_str)
        except (ValueError, AttributeError):
            pass
        else:
            base = _CHONGZHEN
            return CampaignAnchor(
                start_year=y,
                start_month=m,
                year_min=min(y, base.year_min),
                year_max=base.year_max,
                campaign_years=base.campaign_years,
                reign_label=base.reign_label,
            )
    return _CHONGZHEN


def resolve_start_ym(explicit: str = "") -> str:
    """新档开局年月：显式参数 > 环境变量 > 剧本 campaign.json > 预设。"""
    cleaned = (explicit or os.environ.get("MING_SIM_START_YM", "") or "").strip()
    if cleaned:
        return cleaned
    return get_campaign_anchor().default_start_ym()
