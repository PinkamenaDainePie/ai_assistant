# -*- coding: utf-8 -*-
"""熙宁十年历法：quarter_index 1..40 ↔ 1068–1077 年 × 四季。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

_XINING_START_YEAR = 1068
_CAMPAIGN_QUARTERS = 40
_ZH_YEAR = ("", "元", "二", "三", "四", "五", "六", "七", "八", "九", "十")
_SEASON_ZH = ("", "春", "夏", "秋", "冬")


@dataclass(frozen=True)
class CampaignQuarter:
    quarter_index: int
    reign_year: int
    xining_year_index: int
    season: int
    label_zh: str


def quarter_to_campaign(quarter_index: int) -> CampaignQuarter:
    q = max(1, min(int(quarter_index or 1), _CAMPAIGN_QUARTERS))
    zero = q - 1
    reign_year = _XINING_START_YEAR + zero // 4
    season = zero % 4 + 1
    xining_idx = reign_year - 1067
    yr_zh = _ZH_YEAR[xining_idx] if 0 < xining_idx < len(_ZH_YEAR) else str(xining_idx)
    label = "熙宁%s年 %s" % (yr_zh, _SEASON_ZH[season])
    return CampaignQuarter(
        quarter_index=q,
        reign_year=reign_year,
        xining_year_index=xining_idx,
        season=season,
        label_zh=label,
    )


def is_song_xining_campaign(*, data_root: str = "", scenario_id: str = "") -> bool:
    sid = (scenario_id or os.getenv("SCENARIO") or "").strip().lower()
    if sid in ("song", "song_xining", "xining"):
        return True
    root = (data_root or os.getenv("NUMERIC_DATA_ROOT") or "").replace("\\", "/").lower()
    return "biaoge/song" in root or root.endswith("/song")


def campaign_quarter_cap() -> int:
    return _CAMPAIGN_QUARTERS
