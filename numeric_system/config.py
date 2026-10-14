# -*- coding: utf-8 -*-
"""数值系统数据根目录（表格 xlsx）。"""
import os
from pathlib import Path


def default_data_root() -> str:
    env = (os.getenv("NUMERIC_DATA_ROOT") or "").strip()
    if env:
        return env
    here = Path(__file__).resolve().parent.parent
    return str(here / "biaoge")

