# -*- coding: utf-8 -*-
"""Ablation condition → env flags.

SAVER_GATE / SAVER_RECONCILE / CHAPTER_MEMORY / LIGHTWEIGHT_KG are read by ming_sim.
"""
from __future__ import annotations

CONDS: dict[str, dict[str, str]] = {
    # Main: gate × reconcile (chapter memory on, KG off)
    "A": {
        "SAVER_GATE": "0",
        "SAVER_RECONCILE": "0",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "0",
    },
    "B": {
        "SAVER_GATE": "1",
        "SAVER_RECONCILE": "0",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "0",
    },
    "C": {
        "SAVER_GATE": "1",
        "SAVER_RECONCILE": "1",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "0",
    },
    # Chain: memory × lightweight KG
    "A0": {
        "SAVER_GATE": "0",
        "SAVER_RECONCILE": "0",
        "CHAPTER_MEMORY": "0",
        "LIGHTWEIGHT_KG": "0",
    },
    "A1": {
        "SAVER_GATE": "0",
        "SAVER_RECONCILE": "0",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "0",
    },
    "C0": {
        "SAVER_GATE": "1",
        "SAVER_RECONCILE": "1",
        "CHAPTER_MEMORY": "0",
        "LIGHTWEIGHT_KG": "0",
    },
    "C1": {
        "SAVER_GATE": "1",
        "SAVER_RECONCILE": "1",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "0",
    },
    "CK": {
        "SAVER_GATE": "1",
        "SAVER_RECONCILE": "1",
        "CHAPTER_MEMORY": "1",
        "LIGHTWEIGHT_KG": "1",
    },
}
