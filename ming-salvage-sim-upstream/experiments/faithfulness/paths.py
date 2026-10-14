# -*- coding: utf-8 -*-
"""In-repo copy: engine root is the parent of experiments/."""
from __future__ import annotations

from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = PKG_DIR.parent
ENGINE_ROOT = EXPERIMENTS_DIR.parent  # ming-salvage-sim-upstream
PROJECT_DIR = PKG_DIR  # for out-dir relative to this package
RUNS_DIR = PKG_DIR / "runs"
DATA_DIR = ENGINE_ROOT / "data"
ENV_FILE = ENGINE_ROOT / ".env"
