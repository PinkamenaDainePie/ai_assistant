# -*- coding: utf-8 -*-
"""本地 PyTorch Transformer 意图分类（仅依赖 torch）。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from nlu_layer.intent_catalog import INTENT_CATALOG, domain_hint_for_intent
from nlu_layer.schemas import IntentPrediction

_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
_WEIGHTS_PATH = _ARTIFACT_DIR / "intent_transformer.pt"
_META_PATH = _ARTIFACT_DIR / "intent_transformer_meta.json"

_MAX_LEN = 96
_EMBED_DIM = 128
_NHEAD = 4
_NLAYERS = 2
_FF_DIM = 256
_DROPOUT = 0.1
_EPOCHS = 120
_LR = 2e-3
_SCORE_THRESHOLD = 0.42

_MODEL = None
_META: Optional[Dict] = None
_UNAVAILABLE_REASON = ""


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def transformer_available() -> bool:
    return _get_model() is not None


def transformer_unavailable_reason() -> str:
    _get_model()
    return _UNAVAILABLE_REASON


def _require_torch():
    try:
        import torch
        import torch.nn as nn

        return torch, nn
    except ImportError as exc:
        global _UNAVAILABLE_REASON
        _UNAVAILABLE_REASON = "torch_not_installed:%s" % exc
        return None, None


def _build_vocab(samples: Sequence[str]) -> Dict[str, int]:
    chars = set()
    for s in samples:
        for ch in s or "":
            if not ch.isspace():
                chars.add(ch)
    special = ["<pad>", "<unk>"]
    vocab = {tok: i for i, tok in enumerate(special)}
    for ch in sorted(chars):
        vocab[ch] = len(vocab)
    return vocab


def _encode(text: str, vocab: Dict[str, int], max_len: int) -> List[int]:
    ids = []
    for ch in (text or "").strip():
        if ch.isspace():
            continue
        ids.append(vocab.get(ch, vocab.get("<unk>", 1)))
        if len(ids) >= max_len:
            break
    if not ids:
        ids = [vocab.get("<unk>", 1)]
    return ids


def _training_rows() -> Tuple[List[str], List[str]]:
    texts: List[str] = []
    labels: List[str] = []
    repeat = {
        "disaster_relief": 4,
        "strict_governance": 3,
        "tax_relief": 2,
    }
    for item in INTENT_CATALOG:
        intent_id = str(item.get("intent") or "").strip()
        if not intent_id:
            continue
        copies = int(repeat.get(intent_id, 1))
        for phrase in item.get("phrases") or []:
            p = str(phrase or "").strip()
            if p:
                for _ in range(copies):
                    texts.append(p)
                    labels.append(intent_id)
    extras = [
        ("荆湖赈济饥民", "disaster_relief"),
        ("江右灾区蠲免赋税", "disaster_relief"),
        ("开仓赈济山东", "disaster_relief"),
        ("命王安石修缮黄河堤防", "allocate_funds"),
        ("命狄青整饬边防", "military_expand"),
        ("严查地方贪官", "strict_governance"),
    ]
    for text, lab in extras:
        texts.append(text)
        labels.append(lab)
    return texts, labels


def _make_model(nn, vocab_size: int, num_classes: int):
    class IntentTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(vocab_size, _EMBED_DIM, padding_idx=0)
            self.pos = nn.Embedding(_MAX_LEN, _EMBED_DIM)
            enc_layer = nn.TransformerEncoderLayer(
                d_model=_EMBED_DIM,
                nhead=_NHEAD,
                dim_feedforward=_FF_DIM,
                dropout=_DROPOUT,
                batch_first=False,
            )
            self.encoder = nn.TransformerEncoder(enc_layer, num_layers=_NLAYERS)
            self.head = nn.Linear(_EMBED_DIM, num_classes)

        def forward(self, x):
            # x: (batch, seq)
            import torch

            bsz, seqlen = x.shape
            pad_mask = x.eq(0)
            emb = self.embed(x) + self.pos(torch.arange(seqlen, device=x.device).unsqueeze(0).expand(bsz, -1))
            hidden = self.encoder(emb.transpose(0, 1), src_key_padding_mask=pad_mask).transpose(0, 1)
            mask = (~pad_mask).float().unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
            return self.head(pooled)

    return IntentTransformer()


def _train_and_save(torch, nn) -> Optional[Dict]:
    texts, labels = _training_rows()
    if not texts:
        return None
    intent_ids = sorted(set(labels))
    label_to_id = {k: i for i, k in enumerate(intent_ids)}
    vocab = _build_vocab(texts)
    model = _make_model(nn, len(vocab), len(intent_ids))
    optimizer = torch.optim.Adam(model.parameters(), lr=_LR)
    loss_fn = nn.CrossEntropyLoss()
    x_all = []
    y_all = []
    for text, lab in zip(texts, labels):
        x_all.append(_encode(text, vocab, _MAX_LEN))
        y_all.append(label_to_id[lab])
    max_len = max(len(row) for row in x_all)
    x_pad = [row + [0] * (max_len - len(row)) for row in x_all]
    x_tensor = torch.tensor(x_pad, dtype=torch.long)
    y_tensor = torch.tensor(y_all, dtype=torch.long)
    model.train()
    for _ in range(_EPOCHS):
        optimizer.zero_grad()
        logits = model(x_tensor)
        loss = loss_fn(logits, y_tensor)
        loss.backward()
        optimizer.step()
    model.eval()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "vocab": vocab,
        "intent_ids": intent_ids,
        "label_to_id": label_to_id,
        "max_len": _MAX_LEN,
    }
    torch.save({"state_dict": model.state_dict(), "meta": meta}, str(_WEIGHTS_PATH))
    with _META_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "intent_ids": intent_ids,
                "vocab_size": len(vocab),
                "num_classes": len(intent_ids),
            },
            f,
            ensure_ascii=False,
        )
    return meta


def _load_model(torch, nn) -> Optional[Tuple[object, Dict]]:
    global _MODEL, _META, _UNAVAILABLE_REASON
    if _MODEL is not None and _META is not None:
        return _MODEL, _META
    if not _env_flag("NLU_TRANSFORMER_ENABLED", default=False):
        _UNAVAILABLE_REASON = "disabled_by_env"
        return None
    if not _WEIGHTS_PATH.is_file():
        meta = _train_and_save(torch, nn)
        if meta is None:
            _UNAVAILABLE_REASON = "training_failed"
            return None
    try:
        payload = torch.load(str(_WEIGHTS_PATH), map_location="cpu")
        meta = payload.get("meta") or {}
        model = _make_model(nn, len(meta["vocab"]), len(meta["intent_ids"]))
        model.load_state_dict(payload.get("state_dict"))
        model.eval()
    except Exception as exc:
        _UNAVAILABLE_REASON = "init_failed:%s" % exc
        return None
    _MODEL = model
    _META = meta
    _UNAVAILABLE_REASON = ""
    return _MODEL, _META


def _get_model():
    torch, nn = _require_torch()
    if torch is None:
        return None
    pack = _load_model(torch, nn)
    if pack is None:
        return None
    return pack[0]


def _resolve_domain(intent_id: str, text: str, kw_dom: str, kw_sc: float) -> str:
    from nlu_layer.intent_classifier import _domain_keyword_hint

    intent_dom = domain_hint_for_intent(intent_id)
    if kw_sc <= 0:
        kw_dom, kw_sc = _domain_keyword_hint(text)
    if kw_sc > 0 and (intent_dom in ("general", "fiscal") or kw_dom != intent_dom):
        return kw_dom
    if intent_dom != "general":
        return intent_dom
    return kw_dom if kw_sc > 0 else "general"


def classify_edict_intent_transformer(
    text: str,
    edict_category_ids: Optional[List[str]] = None,
) -> Optional[IntentPrediction]:
    torch, nn = _require_torch()
    if torch is None:
        return None
    pack = _load_model(torch, nn)
    if pack is None:
        return None
    model, meta = pack
    t = (text or "").strip()
    if not t:
        return None
    cids = list(edict_category_ids or []) or ["other"]
    allowed = set()
    for item in INTENT_CATALOG:
        intent_id = str(item.get("intent") or "").strip()
        cats = item.get("categories")
        if cats is not None and not any(cid in cats for cid in cids):
            continue
        if intent_id:
            allowed.add(intent_id)
    if not allowed:
        return None
    ids = _encode(t, meta["vocab"], int(meta.get("max_len") or _MAX_LEN))
    x = torch.tensor([ids], dtype=torch.long)
    with torch.no_grad():
        logits = model(x)[0]
        probs = torch.softmax(logits, dim=-1).cpu().tolist()
    intent_ids = list(meta["intent_ids"])
    ranked = sorted(
        [(intent_ids[i], float(probs[i])) for i in range(len(intent_ids)) if intent_ids[i] in allowed],
        key=lambda z: z[1],
        reverse=True,
    )
    if not ranked:
        return None
    top_id, top_sc = ranked[0]
    if top_sc < _SCORE_THRESHOLD:
        return None
    from nlu_layer.intent_classifier import _domain_keyword_hint

    kw_dom, kw_sc = _domain_keyword_hint(t)
    dom = _resolve_domain(top_id, t, kw_dom, kw_sc)
    alts = [(i, s) for i, s in ranked[1:4]]
    return IntentPrediction(
        intent_id=top_id,
        domain_hint=dom,
        confidence=round(top_sc, 4),
        source="transformer",
        alternatives=alts,
    )
