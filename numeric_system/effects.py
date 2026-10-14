from typing import Any, Dict, List


def effects_from_edict_text(text: str) -> List[Dict[str, Any]]:
    """
    Turn free-form edict text into effect actions.
    This is a deterministic v1 scorer for balancing and quick iteration.
    """
    t = (text or "").strip()
    if not t:
        return []

    rules = [
        # 财政向
        ("加税", [("treasury_balance", 120000), ("public_support", -3), ("unrest", 3)]),
        ("清查", [("treasury_balance", 80000), ("public_support", -1), ("unrest", 1.5)]),
        ("盐引", [("treasury_balance", 60000), ("fiscal_pressure", -1)]),
        ("矿税", [("treasury_balance", 90000), ("public_support", -4), ("unrest", 4)]),
        ("蠲免", [("treasury_balance", -100000), ("public_support", 4), ("unrest", -2)]),
        ("赈济", [("treasury_balance", -70000), ("public_support", 3), ("unrest", -3)]),
        # 军政向
        ("练兵", [("treasury_balance", -60000), ("fiscal_pressure", 1), ("unrest", -1)]),
        ("裁兵", [("treasury_balance", 50000), ("public_support", -1), ("unrest", 2)]),
        ("整饬吏治", [("public_support", 2.5), ("unrest", -2), ("treasury_balance", -20000)]),
        ("严禁", [("public_support", 1.5), ("unrest", -1)]),
        ("重惩", [("public_support", -1), ("unrest", -0.5)]),
        ("从宽", [("public_support", 1.2), ("unrest", 0.8)]),
        ("试行", [("public_support", 1.0), ("unrest", -0.8), ("fiscal_pressure", -0.8)]),
        ("暂缓", [("public_support", 0.8), ("treasury_balance", -20000)]),
    ]

    merged: Dict[str, float] = {}
    for kw, pairs in rules:
        if kw not in t:
            continue
        for key, value in pairs:
            merged[key] = merged.get(key, 0.0) + float(value)

    # 语气微调
    hard_words = ["即刻", "严令", "务必", "不得", "限期"]
    soft_words = ["酌情", "暂缓", "体恤", "商议", "宽限"]
    hard = sum(1 for w in hard_words if w in t)
    soft = sum(1 for w in soft_words if w in t)
    if hard > soft:
        merged["public_support"] = merged.get("public_support", 0.0) - 0.8
        merged["unrest"] = merged.get("unrest", 0.0) + 0.8
    elif soft > hard:
        merged["public_support"] = merged.get("public_support", 0.0) + 0.8
        merged["unrest"] = merged.get("unrest", 0.0) - 0.6

    effects: List[Dict[str, Any]] = []
    for key, value in merged.items():
        effects.append({"action": "add_metric", "key": key, "value": round(value, 2)})
    return effects


def effects_from_debate_choice(choice: str) -> List[Dict[str, Any]]:
    """
    choice:
      - 'wang_anshi' / 'reformer': 更激进，财政短期更强，社会波动更大
      - 'sima_guang' / 'conservative': 更稳健，财政短期承压但动乱更低
      - others: no-op
    """
    c = (choice or "").strip().lower()
    if c in ("wang_anshi", "reformer"):
        return [
            {"action": "add_metric", "key": "treasury_balance", "value": 50000},
            {"action": "add_metric", "key": "public_support", "value": -1.5},
            {"action": "add_metric", "key": "unrest", "value": 1.8},
        ]
    if c in ("sima_guang", "conservative"):
        return [
            {"action": "add_metric", "key": "treasury_balance", "value": -25000},
            {"action": "add_metric", "key": "public_support", "value": 1.6},
            {"action": "add_metric", "key": "unrest", "value": -1.8},
        ]
    return []


def effects_from_minister_advice(
    minister: Dict[str, Any], advice_text: str
) -> List[Dict[str, Any]]:
    """
    Convert minister advice into effects with minister profile weighting.
    minister expected keys: name, influence, stance, party
    """
    base = effects_from_edict_text(advice_text)
    if not base:
        return []

    influence = float(minister.get("influence", 50.0) or 50.0)
    stance = str(minister.get("stance", "") or "")
    party = str(minister.get("party", "") or "")

    # influence range 0-100 -> factor ~0.8 to 1.2
    influence_factor = 0.8 + max(0.0, min(100.0, influence)) / 250.0

    # stance bias: pragmatic/reform/interest groups
    treasury_bias = 1.0
    support_bias = 1.0
    unrest_bias = 1.0
    s = stance + "|" + party
    if "利己" in s or "阉党" in s:
        treasury_bias += 0.08
        support_bias -= 0.1
        unrest_bias += 0.12
    if "稳健" in s or "保守" in s:
        treasury_bias -= 0.05
        support_bias += 0.08
        unrest_bias -= 0.08
    if "改革" in s or "激进" in s:
        treasury_bias += 0.06
        support_bias -= 0.04
        unrest_bias += 0.05

    out: List[Dict[str, Any]] = []
    for e in base:
        if e.get("action") != "add_metric":
            out.append(e)
            continue
        key = e.get("key")
        val = float(e.get("value", 0.0))
        factor = influence_factor
        if key == "treasury_balance":
            factor *= treasury_bias
        elif key == "public_support":
            factor *= support_bias
        elif key == "unrest":
            factor *= unrest_bias
        out.append({"action": "add_metric", "key": key, "value": round(val * factor, 2)})

    # add trace flag for report/debug
    if minister.get("name"):
        out.append(
            {
                "action": "set_flag",
                "flag": f"adopt_minister_{minister.get('name')}",
                "value": True,
            }
        )
    return out


def merge_effect_lists(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for g in groups:
        if not g:
            continue
        out.extend(g)
    return out

