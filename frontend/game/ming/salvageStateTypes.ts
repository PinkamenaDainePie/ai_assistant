/** ming-salvage GET /api/game/state 完整快照类型（Drawer / HUD 消费） */

export type SalvageBudgetItem = {
  name: string;
  amount: number;
  note?: string;
  base_key?: string;
  rate_key?: string;
  base?: number;
  rate?: number;
  formula?: string;
  formula_kind?: string;
  basis?: string;
  basis_total?: number;
  rate_unit?: string;
  paid_estimate?: number;
};

export type SalvageBudgetMovement = {
  delta: number;
  balance_after: number;
  category: string;
  reason: string;
};

export type SalvageBudgetAccount = {
  balance: number;
  income: SalvageBudgetItem[];
  expense: SalvageBudgetItem[];
  income_total: number;
  expense_total: number;
  net: number;
  base_income_total?: number;
  base_expense_total?: number;
  base_net?: number;
  modifier_pct?: number;
  movements: SalvageBudgetMovement[];
  movements_total: number;
};

export type SalvageBudget = Record<'国库' | '内库', SalvageBudgetAccount>;

export type SalvageLegacy = {
  id: number;
  name: string;
  narrative_hint?: string;
  modifiers?: Record<string, unknown>;
  effect_text: string;
  remaining_months: number;
  clear_condition?: string;
};

export type SalvageRegion = {
  id: string;
  name: string;
  /** API 展示名；熙宁 v2 为宋制路分，万历可与 name 相同 */
  display_name?: string;
  /** 路分短名（如「京畿 / 开封」→「京畿」），无则省略 */
  circuit_name?: string;
  kind?: string;
  population?: number;
  public_support?: number;
  unrest: number;
  natural_disaster?: string;
  human_disaster?: string;
  registered_land?: number;
  hidden_land?: number;
  tax_per_turn?: number;
  tax_actual?: number;
  tax_efficiency?: number;
  tax_breakdown?: Record<string, number>;
  fiscal?: Record<string, number | string>;
  grain_output?: number;
  grain_stock?: number;
  gentry_resistance?: number;
  military_pressure?: number;
  status?: string;
  controlled_by?: string;
};

export type SalvageArmyWeapon = {
  troop_type: string;
  id: string;
  name: string;
  tier: string;
  qty: number;
};

export type SalvageArmy = {
  id: string;
  name: string;
  station?: string;
  theater?: string;
  commander?: string;
  controller?: string;
  troop_type?: string;
  troop_composition?: Record<string, number>;
  manpower: number;
  maintenance_per_turn?: number;
  supply?: number;
  morale?: number;
  training?: number;
  equipment?: number;
  arrears?: number;
  mobility?: number;
  loyalty?: number;
  status?: string;
  owner_power?: string;
  arms?: SalvageArmyWeapon[];
};

export type SalvageArmsStockItem = {
  id: string;
  name: string;
  tier: string;
  qty: number;
  unlocked: boolean;
  requires_tech?: string;
};

export type SalvageBuilding = {
  id: string;
  region_id?: string;
  name: string;
  category?: string;
  level?: number;
  condition?: number;
  maintenance?: number;
  risk?: number;
  output_metric?: string;
  output_amount?: number;
  status?: string;
  origin?: string;
};

export type SalvageTechnology = {
  id: string;
  name: string;
  category?: string;
  effect_summary?: string;
  status?: string;
  origin?: string;
};

export type SalvageDepartment = {
  name: string;
  authority_scope?: string;
  power?: number;
  responsibility?: number;
  corruption_risk?: number;
};

export type SalvagePower = {
  id: string;
  name: string;
  kind?: string;
  leader?: string;
  stance?: string;
  leverage?: number;
  satisfaction?: number;
  military_strength?: number;
  cohesion?: number;
  supply?: number;
  agenda?: string;
  status?: string;
  last_action?: string;
};

export type SalvagePresetTreeItem = {
  key: string;
  name: string;
  category: string;
  effect_summary: string;
  authority_scope?: string;
  power?: number;
  expected_months: number;
  bar_value: number;
  requires: string[];
  unlocked: boolean;
  available: boolean;
};

export type SalvagePresetTrees = {
  technologies: SalvagePresetTreeItem[];
  departments: SalvagePresetTreeItem[];
};

export type SalvageVictoryStatus = {
  status?: string;
  summary?: string;
  [key: string]: unknown;
};

export type SalvageEvent = Record<string, unknown>;

export type SalvageStructuredDirectiveRow = {
  id?: number;
  template_id?: string;
  category?: string;
  title?: string;
  fields?: Record<string, string>;
  compiled_text?: string;
  settlement_hint?: string;
  status?: string;
};

export type SalvageDirectiveRow = {
  id: number;
  text: string;
  status: string;
  actor?: string;
  notes?: string;
};

export type SalvageClosedIssueRow = {
  id?: number;
  kind?: string;
  title?: string;
  status?: string;
  bar_value?: number;
  bar_good_meaning?: string;
  bar_bad_meaning?: string;
  closed_turn?: number;
  stage_text?: string;
  effect?: Record<string, unknown>;
};

export type SalvageEndingRow = {
  status?: string;
  label?: string;
  summary?: string;
  score?: number;
  score_label_zh?: string;
  timeline?: Array<{
    turn?: number;
    year?: number;
    period?: number;
    decree_brief?: string;
    effect_brief?: string;
    chapter?: string;
  }>;
};

export type SalvageMapNode = {
  id: string;
  kind?: string;
  x?: number;
  y?: number;
  label?: string;
  risk?: number;
  region?: SalvageRegion;
  armies?: SalvageArmy[];
  buildings?: SalvageBuilding[];
  power?: SalvagePower;
};

export type SalvageMinister = {
  id?: string;
  name: string;
  office?: string;
  office_type?: string;
  faction?: string;
  summary?: string;
  description?: string;
  status?: string;
  status_label?: string;
  favorite?: boolean;
  archived?: boolean;
  power_id?: string;
  origin?: string;
  portrait_id?: string;
  loyalty?: number;
  ability?: number;
  integrity?: number;
  martial?: number;
  stewardship?: number;
  intrigue?: number;
  learning?: number;
  birth_year?: number;
  historical_death_year?: number;
  skills?: Array<{ id: string; name: string; description?: string }>;
};

export type SalvageGameState = {
  turn?: {
    year?: number;
    period?: number;
    turn?: number;
    phase?: string;
  };
  metrics?: Record<string, number>;
  treasury?: string;
  directives?: SalvageDirectiveRow[];
  pending_count?: number;
  pending_decisions?: Array<Record<string, unknown>>;
  last_decree?: string;
  last_report?: string;
  previous_summary?: string;
  max_decree_issues?: number;
  issue_log_limit?: number;
  structured_directives?: SalvageStructuredDirectiveRow[];
  ending?: SalvageEndingRow | null;
  ministers?: SalvageMinister[];
  archived_ministers?: SalvageMinister[];
  consorts?: SalvageMinister[];
  issues?: Array<Record<string, unknown>>;
  closed_this_turn?: SalvageClosedIssueRow[];
  regions?: SalvageRegion[];
  armies?: SalvageArmy[];
  arms_stock?: SalvageArmsStockItem[];
  troop_rates?: Record<string, number>;
  departments?: SalvageDepartment[];
  technologies?: SalvageTechnology[];
  map_nodes?: SalvageMapNode[];
  buildings?: SalvageBuilding[];
  budget?: SalvageBudget;
  legacies?: SalvageLegacy[];
  victory_status?: SalvageVictoryStatus;
  region_warning?: string;
  army_warning?: string;
  power_warning?: string;
  powers?: SalvagePower[];
  preset_trees?: SalvagePresetTrees;
  events?: SalvageEvent[];
  /** 非 state_payload 字段；可由 store 合并密令 API 结果 */
  secret_orders?: Array<Record<string, unknown>>;
  /** 后端未来新增字段，normalize 时保留 */
  [key: string]: unknown;
};

export type MingHudDrawerKey =
  | 'none'
  | 'court'
  | 'appointment'
  | 'region'
  | 'army'
  | 'economy'
  | 'building'
  | 'harem'
  | 'goal';
