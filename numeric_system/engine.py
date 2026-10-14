from typing import Any, Dict, List

from .types import NumericData, QuarterState


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class QuarterEngine:
    def __init__(self, data: NumericData):
        self.data = data

    def init_state(self) -> QuarterState:
        avg_support = 50.0
        avg_unrest = 25.0
        if self.data.land_blocks:
            avg_support = sum(b.public_support for b in self.data.land_blocks) / len(
                self.data.land_blocks
            )
            avg_unrest = sum(b.unrest for b in self.data.land_blocks) / len(
                self.data.land_blocks
            )

        state = QuarterState()
        state.metrics["treasury_balance"] = self.data.treasury.balance_liang
        state.metrics["inner_treasury_balance"] = self.data.inner_treasury.balance_liang
        if self.data.faction_powers:
            faction_support = sum(f.public_support for f in self.data.faction_powers) / len(
                self.data.faction_powers
            )
            avg_support = (avg_support * 0.7) + (faction_support * 0.3)
        state.metrics["public_support"] = _clamp(avg_support, 0.0, 100.0)
        state.metrics["unrest"] = _clamp(avg_unrest, 0.0, 100.0)
        state.metrics["fiscal_pressure"] = 30.0

        # ---- Table-backed derived indices (0-100) ----
        # disaster_index: map levels to severity score then scale to 0-100.
        if self.data.land_blocks:
            level_map = {"": 0.0, "轻微": 1.0, "中等": 2.0, "严重": 3.0}
            avg_lvl = sum(level_map.get((b.disaster_level or "").strip(), 0.0) for b in self.data.land_blocks) / len(
                self.data.land_blocks
            )
            state.metrics["disaster_index"] = _clamp(avg_lvl / 3.0 * 100.0, 0.0, 100.0)
            avg_completion = sum(max(0.0, min(1.0, float(b.tax_completion))) for b in self.data.land_blocks) / len(
                self.data.land_blocks
            )
            state.metrics["tax_completion_index"] = _clamp(avg_completion * 100.0, 0.0, 100.0)
        else:
            state.metrics["disaster_index"] = 0.0
            state.metrics["tax_completion_index"] = 80.0

        if self.data.tax_rules:
            avg_tax_per_mu = sum(r.total_tax_per_mu for r in self.data.tax_rules) / len(self.data.tax_rules)
            # Normalize around 1.0 baseline, cap to plausible band.
            tax_idx = _clamp((avg_tax_per_mu - 1.0) / 4.0 * 100.0 + 50.0, 0.0, 100.0)
            state.metrics["tax_intensity"] = tax_idx
        else:
            state.metrics["tax_intensity"] = 50.0

        if self.data.armies:
            state.metrics["army_morale"] = _clamp(
                sum(a.morale for a in self.data.armies) / len(self.data.armies), 0.0, 100.0
            )
            state.metrics["army_supply"] = _clamp(
                sum(a.supply for a in self.data.armies) / len(self.data.armies), 0.0, 100.0
            )
        else:
            state.metrics["army_morale"] = 60.0
            state.metrics["army_supply"] = 60.0

        if self.data.navies:
            state.metrics["navy_morale"] = _clamp(
                sum(n.morale for n in self.data.navies) / len(self.data.navies), 0.0, 100.0
            )
            state.metrics["navy_supply"] = _clamp(
                sum(n.supply for n in self.data.navies) / len(self.data.navies), 0.0, 100.0
            )
        else:
            state.metrics["navy_morale"] = 60.0
            state.metrics["navy_supply"] = 60.0

        if self.data.strata:
            total_weight = sum(max(1.0, s.influence) for s in self.data.strata)
            revolt = sum(max(1.0, s.influence) * s.revolt_risk for s in self.data.strata) / total_weight
            state.metrics["revolt_risk"] = _clamp(revolt, 0.0, 100.0)
        else:
            state.metrics["revolt_risk"] = 35.0

        if self.data.faction_powers:
            corr = sum(f.corruption for f in self.data.faction_powers) / len(self.data.faction_powers)
            auth = sum(f.authority for f in self.data.faction_powers) / len(self.data.faction_powers)
            state.metrics["corruption"] = _clamp(corr, 0.0, 100.0)
            state.metrics["authority"] = _clamp(auth, 0.0, 100.0)
        else:
            state.metrics["corruption"] = 50.0
            state.metrics["authority"] = 50.0
        for mk in list(state.metrics.keys()):
            try:
                state.metrics[str(mk)] = round(float(state.metrics[mk]), 4)
            except (TypeError, ValueError):
                pass
        return state

    def _tax_policy_modifier(self) -> Dict[str, float]:
        if not self.data.tax_rules:
            return {"income_factor": 1.0, "support_delta": 0.0, "unrest_delta": 0.0}
        avg_tax_per_mu = sum(r.total_tax_per_mu for r in self.data.tax_rules) / len(
            self.data.tax_rules
        )
        # Use tax intensity as a coarse policy pressure proxy.
        pressure = _clamp((avg_tax_per_mu - 1.0) / 4.0, -0.2, 0.3)
        return {
            "income_factor": 1.0 + pressure * 0.4,
            "support_delta": -pressure * 4.0,
            "unrest_delta": pressure * 5.0,
        }

    def _strata_feedback(self) -> Dict[str, float]:
        if not self.data.strata:
            return {"support_delta": 0.0, "unrest_delta": 0.0}
        total_weight = sum(max(1.0, s.influence) for s in self.data.strata)
        sat_score = (
            sum(max(1.0, s.influence) * s.satisfaction for s in self.data.strata)
            / total_weight
        )
        revolt_score = (
            sum(max(1.0, s.influence) * s.revolt_risk for s in self.data.strata)
            / total_weight
        )
        return {
            "support_delta": (sat_score - 50.0) * 0.05,
            "unrest_delta": (revolt_score - 35.0) * 0.06,
        }

    def _faction_feedback(self) -> Dict[str, float]:
        if not self.data.faction_powers:
            return {"support_delta": 0.0, "unrest_delta": 0.0, "fiscal_pressure_delta": 0.0}
        corr = sum(f.corruption for f in self.data.faction_powers) / len(
            self.data.faction_powers
        )
        auth = sum(f.authority for f in self.data.faction_powers) / len(
            self.data.faction_powers
        )
        support_delta = (auth - 50.0) * 0.02 - (corr - 50.0) * 0.05
        unrest_delta = (corr - 50.0) * 0.05 - (auth - 50.0) * 0.03
        fiscal_pressure_delta = max(0.0, corr - 60.0) * 0.08
        return {
            "support_delta": support_delta,
            "unrest_delta": unrest_delta,
            "fiscal_pressure_delta": fiscal_pressure_delta,
        }

    def _party_feedback(self) -> Dict[str, float]:
        if not self.data.party_groups:
            return {"support_delta": 0.0, "unrest_delta": 0.0, "fiscal_pressure_delta": 0.0}
        total_weight = sum(max(1.0, p.influence) for p in self.data.party_groups)
        weighted_support = (
            sum(max(1.0, p.influence) * p.support for p in self.data.party_groups)
            / total_weight
        )
        # Polarization proxy: low average support among influential parties means higher friction.
        support_gap = 50.0 - weighted_support
        return {
            "support_delta": -support_gap * 0.04,
            "unrest_delta": max(0.0, support_gap) * 0.05,
            "fiscal_pressure_delta": max(0.0, support_gap) * 0.04,
        }

    def _equipment_feedback(self) -> Dict[str, float]:
        if not self.data.equipment_items:
            return {"expense_factor": 1.0, "support_delta": 0.0, "unrest_delta": 0.0}
        stock = sum(i.stock for i in self.data.equipment_items)
        output = sum(i.quarterly_output for i in self.data.equipment_items)
        ratio = output / max(1.0, stock)
        if ratio < 0.006:
            return {"expense_factor": 1.07, "support_delta": -0.3, "unrest_delta": 0.4}
        if ratio > 0.03:
            return {"expense_factor": 0.98, "support_delta": 0.2, "unrest_delta": -0.2}
        return {"expense_factor": 1.0, "support_delta": 0.0, "unrest_delta": 0.0}

    def _land_income(self) -> float:
        total = 0.0
        tax_mod = self._tax_policy_modifier()
        for b in self.data.land_blocks:
            disaster_factor = 1.0
            level = (b.disaster_level or "").strip()
            if level == "严重":
                disaster_factor = 0.65
            elif level == "中等":
                disaster_factor = 0.82
            elif level == "轻微":
                disaster_factor = 0.92
            block_income = (
                b.total_tax_liang
                * max(0.0, b.tax_completion)
                * max(0.0, b.tax_multiplier)
                * disaster_factor
                * max(0.7, tax_mod["income_factor"])
            )
            total += block_income
        return total

    def _military_expense(self) -> float:
        total = 0.0
        for a in self.data.armies:
            supply_factor = 1.0 + max(0.0, 70.0 - a.supply) / 140.0
            morale_factor = 1.0 + max(0.0, 50.0 - a.morale) / 200.0
            extra = a.total_people * a.extra_cost_per_person
            total += (a.maintenance_liang + extra) * supply_factor * morale_factor
        for n in self.data.navies:
            supply_factor = 1.0 + max(0.0, 70.0 - n.supply) / 160.0
            morale_factor = 1.0 + max(0.0, 50.0 - n.morale) / 220.0
            total += n.maintenance_liang * supply_factor * morale_factor
        if self.data.army_types:
            total += sum(max(0.0, t.maintenance_liang) for t in self.data.army_types) * 0.35
        if self.data.ship_types:
            ship_type_base = 0.0
            for t in self.data.ship_types:
                cannon_factor = 1.0 + (t.heavy_cannon_count * 0.015) + (
                    t.light_cannon_count * 0.005
                )
                ship_type_base += max(0.0, t.maintenance_liang) * cannon_factor
            total += ship_type_base * 0.25
        equip_mod = self._equipment_feedback()
        total *= equip_mod["expense_factor"]
        return total

    def apply_effects(self, state: QuarterState, effects: List[Dict[str, Any]]) -> None:
        """
        Unified effect actions:
        - add_metric: {"action":"add_metric","key":"public_support","value":5}
        - add_regional_metric: {"action":"add_regional_metric","region":"jinghunan","key":"unrest","value":-3}
        - mul_metric: {"action":"mul_metric","key":"treasury_balance","ratio":1.1}
        - set_flag: {"action":"set_flag","flag":"policy_qingmiao","value":true}
        - set_region_status: {"action":"set_region_status","region":"jinghunan","status":"disaster","disaster_kind":"flood","relief_pending":true}
        - set_minister_status: {"action":"set_minister_status","name":"章惇","status":"dismissed","reason":"demoted"}
        - clear_region_status / clear_minister_status
        这些 action 让任务反馈助手（或事件/战弧/人事 outcome）可“放权”改变地区/人物状态。
        """
        for e in effects:
            action = e.get("action", "")
            if action == "add_regional_metric":
                from edict_execution_frame.regional_effects import regional_metric_storage_key

                region = str(e.get("region") or "").strip()
                key = str(e.get("key") or "").strip()
                val = float(e.get("value", 0.0))
                if region and key:
                    rk = regional_metric_storage_key(region, key)
                    state.metrics[rk] = float(state.metrics.get(rk, 0.0)) + val
            elif action == "add_metric":
                key = e.get("key")
                val = float(e.get("value", 0.0))
                if key in state.metrics:
                    state.metrics[key] += val
            elif action == "mul_metric":
                key = e.get("key")
                ratio = float(e.get("ratio", 1.0))
                if key in state.metrics:
                    state.metrics[key] *= ratio
            elif action == "set_flag":
                flag = e.get("flag")
                if flag:
                    state.flags[str(flag)] = bool(e.get("value", True))
            elif action == "set_region_status":
                from scenario_system.song_locations import set_region_status

                set_region_status(
                    state,
                    region=str(e.get("region") or ""),
                    status=str(e.get("status") or "normal"),
                    disaster_kind=str(e.get("disaster_kind") or ""),
                    occupier=str(e.get("occupier") or ""),
                    relief_pending=e.get("relief_pending"),
                    since_quarter=e.get("since_quarter") or getattr(state, "quarter_index", 0),
                )
            elif action == "set_minister_status":
                from scenario_system.song_locations import set_minister_status

                set_minister_status(
                    state,
                    name=str(e.get("name") or ""),
                    status=str(e.get("status") or "active"),
                    reason=str(e.get("reason") or ""),
                    last_office=str(e.get("last_office") or ""),
                    since_quarter=e.get("since_quarter") or getattr(state, "quarter_index", 0),
                )
            elif action == "clear_region_status":
                from scenario_system.song_locations import clear_region_status

                clear_region_status(state, str(e.get("region") or ""))
            elif action == "clear_minister_status":
                from scenario_system.song_locations import clear_minister_status

                clear_minister_status(state, str(e.get("name") or ""))

        # final clamp
        state.metrics["public_support"] = _clamp(
            state.metrics.get("public_support", 50.0), 0.0, 100.0
        )
        state.metrics["unrest"] = _clamp(state.metrics.get("unrest", 30.0), 0.0, 100.0)
        state.metrics["fiscal_pressure"] = _clamp(
            state.metrics.get("fiscal_pressure", 30.0), 0.0, 100.0
        )
        for k in (
            "disaster_index",
            "tax_completion_index",
            "tax_intensity",
            "army_morale",
            "army_supply",
            "navy_morale",
            "navy_supply",
            "revolt_risk",
            "corruption",
            "authority",
        ):
            if k in state.metrics:
                state.metrics[k] = _clamp(state.metrics.get(k, 50.0), 0.0, 100.0)

    def settle_quarter(
        self, state: QuarterState, effects: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if effects is None:
            effects = []

        # 1) base fiscal flow
        tax_mod = self._tax_policy_modifier()
        strata_mod = self._strata_feedback()
        faction_mod = self._faction_feedback()
        party_mod = self._party_feedback()
        equip_mod = self._equipment_feedback()

        land_income = self._land_income()
        military_expense = self._military_expense()
        civil_expense = self.data.treasury.total_expense_liang * 0.2
        total_expense = military_expense + civil_expense
        net = land_income - total_expense

        state.metrics["treasury_balance"] += net
        state.metrics["inner_treasury_balance"] += (
            self.data.inner_treasury.total_income_liang
            - self.data.inner_treasury.total_expense_liang
        )

        # 2) social feedback
        tax_pressure = 0.0
        if land_income > 0:
            tax_pressure = _clamp(total_expense / land_income * 50.0, 0.0, 100.0)
        state.metrics["fiscal_pressure"] = tax_pressure

        support_delta = 0.0
        unrest_delta = 0.0
        if net < 0:
            support_delta -= 3.0
            unrest_delta += 4.0
        else:
            support_delta += 1.5
            unrest_delta -= 1.0
        support_delta -= max(0.0, tax_pressure - 55.0) * 0.06
        unrest_delta += max(0.0, tax_pressure - 60.0) * 0.08
        support_delta += (
            tax_mod["support_delta"]
            + strata_mod["support_delta"]
            + faction_mod["support_delta"]
            + party_mod["support_delta"]
            + equip_mod["support_delta"]
        )
        unrest_delta += (
            tax_mod["unrest_delta"]
            + strata_mod["unrest_delta"]
            + faction_mod["unrest_delta"]
            + party_mod["unrest_delta"]
            + equip_mod["unrest_delta"]
        )
        state.metrics["fiscal_pressure"] = _clamp(
            state.metrics["fiscal_pressure"]
            + faction_mod["fiscal_pressure_delta"]
            + party_mod["fiscal_pressure_delta"],
            0.0,
            100.0,
        )

        state.metrics["public_support"] = _clamp(
            state.metrics["public_support"] + support_delta, 0.0, 100.0
        )
        state.metrics["unrest"] = _clamp(
            state.metrics["unrest"] + unrest_delta, 0.0, 100.0
        )

        # 3) apply task/edict/event effects
        self.apply_effects(state, effects)

        # 4) 地区状态季末 tick（ignored、revolt 惩罚、多灾边压 flag 等）
        tick_trace: Dict[str, Any] = {}
        try:
            from scenario_system.song_locations import tick_region_statuses

            tick_trace = tick_region_statuses(state, int(getattr(state, "quarter_index", 0)))
        except Exception:
            tick_trace = {"error": "tick_skipped"}

        report = {
            "quarter": state.quarter_index,
            "income_land_liang": round(land_income, 2),
            "expense_military_liang": round(military_expense, 2),
            "expense_civil_liang": round(civil_expense, 2),
            "net_liang": round(net, 2),
            "metrics": {
                "treasury_balance": round(state.metrics["treasury_balance"], 2),
                "inner_treasury_balance": round(
                    state.metrics["inner_treasury_balance"], 2
                ),
                "public_support": round(state.metrics["public_support"], 2),
                "unrest": round(state.metrics["unrest"], 2),
                "fiscal_pressure": round(state.metrics["fiscal_pressure"], 2),
            },
            "applied_effects_count": len(effects),
            "region_tick": tick_trace,
            "modifiers_breakdown": {
                "tax_policy": {
                    "income_factor": round(tax_mod["income_factor"], 4),
                    "support_delta": round(tax_mod["support_delta"], 4),
                    "unrest_delta": round(tax_mod["unrest_delta"], 4),
                },
                "strata_feedback": {
                    "support_delta": round(strata_mod["support_delta"], 4),
                    "unrest_delta": round(strata_mod["unrest_delta"], 4),
                },
                "faction_feedback": {
                    "support_delta": round(faction_mod["support_delta"], 4),
                    "unrest_delta": round(faction_mod["unrest_delta"], 4),
                    "fiscal_pressure_delta": round(
                        faction_mod["fiscal_pressure_delta"], 4
                    ),
                },
                "party_feedback": {
                    "support_delta": round(party_mod["support_delta"], 4),
                    "unrest_delta": round(party_mod["unrest_delta"], 4),
                    "fiscal_pressure_delta": round(
                        party_mod["fiscal_pressure_delta"], 4
                    ),
                },
                "equipment_feedback": {
                    "expense_factor": round(equip_mod["expense_factor"], 4),
                    "support_delta": round(equip_mod["support_delta"], 4),
                    "unrest_delta": round(equip_mod["unrest_delta"], 4),
                },
            },
        }
        state.quarter_index += 1
        return report

