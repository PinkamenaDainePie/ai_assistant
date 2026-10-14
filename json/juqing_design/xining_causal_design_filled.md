# 熙宁战役 · 因果设计补全稿

## 设计基线

- 因果链只走：诏书 → 数值变化 → 任务变化 → 国策节点变化。
- 本稿不新增 `playbook → node` 直连边。
- `scholar_support` 尚未进入当前 `METRIC_SCHEMA`，所以旧党/士大夫压力暂用 `authority`、`public_support`、`unrest`、`fiscal_pressure` 组合表达。
- 进度默认按 100 制；主线任务影响 8–20 点，随机任务影响 3–12 点。
- `suspended` 用来表达“制度已被迫暂缓/路线未死但停摆”；`failed` 用来表达“风险节点成局或制度失败”。

---

## 一、第四节：主线任务 · 因果设计表（补全）

| 源任务 template_id | 任务状态 | 数值门控 | 目标 node_id | 节点效果 | 设计意图 | 状态 |
|---|---:|---|---|---|---|---|
| `main_xining_reform_mandate` | completed | — | `reform_mandate` | active | 变法路线确立 | ✅ completes |
| `main_xining_reform_mandate` | failed | — | `reform_mandate` | suspended + flag:`conservative_compromise` | 守旧/缓进路线成立，新法总开关暂缓 | ✅ 新补 |
| `main_xining_reform_mandate` | failed | — | `old_party_pressure` | active, progress+6 | 守旧话语权上升，后续改革天然阻力变高 | ✅ 新补 |
| `main_wang_anshi_to_court` | completed | — | `wang_anshi_in_court` | active | 王安石入朝 | ✅ completes |
| `main_wang_anshi_to_court` | failed | — | `wang_anshi_in_court` | suspended + flag:`wang_anshi_delayed` | 人事迟疑导致新法无人主持 | ✅ 新补 |
| `main_sansi_establish` | completed | authority≥52 | `sansi_established` | active | 条例司成立 | ✅ completes |
| `main_sansi_establish` | active | overdue≥2 | `old_party_pressure` | active, progress+8，可重复 | 建制拖延，旧党议论“变法无纲” | ✅ 新补 |
| `main_sansi_establish` | failed | authority<50 或 public_support<48 | `court_fierce_resistance` | active, progress+10 | 条例司未立而朝局先乱，引发群臣攻讦 | ✅ 新补 |
| `main_sansi_establish` | failed | — | `sansi_established` | suspended | 机构方案流产，后续财政新法推进减速 | ✅ 新补 |
| `main_green_sprout_route` | active | tax_completion≥42 | `green_sprout_active` | progress+12 | 指标达标推制度落地 | ✅ 已实现 |
| `main_green_sprout_route` | active/failed | overdue≥3 | `green_sprout_reform_failed` | failed / active risk | 改革长期不能结案，青苗合法性破产 | ✅ 已实现 |
| `main_green_sprout_route` | active/failed | overdue≥3 + authority<48 或 public_support<46 | `court_fierce_resistance` | active | 群臣激烈反抗 | ✅ 已实现调整 |
| `main_corvee_commutation` | completed | 青苗已开，且青苗进度≥20 | `corvee_active` | completed | 免役法建立在青苗财政执行能力之上 | ✅ 已实现 |
| `main_corvee_commutation` | failed | overdue≥2 | `corvee_active` | suspended | 役法争议过大，募役/免役暂缓 | ✅ 新补 |
| `main_corvee_commutation` | failed | overdue≥2 + unrest≥42 | `court_fierce_resistance` | active, progress+10 | 役法僵局从地方怨怼转为朝堂攻击 | ✅ 新补 |
| `main_fiscal_reform_pack` | completed | treasury≥38000 | `fiscal_reform_pack_active` / `shiyi_active` / `equalized_transport_active` / `fangtian_active` | active | 理财包及三子法落地 | ✅ completes |
| `main_fiscal_reform_pack` | active | fiscal_pressure≥58 + public_support<50 | `shiyi_active` | suspended + flag:`shiyi_deferred_by_pressure` | 财政过紧且民心不足时，市易先被暂缓，避免商怨爆炸 | ✅ 新补 |
| `main_fiscal_reform_pack` | failed | — | `fiscal_reform_pack_active` | suspended | 国家理财改革包未能统一成制 | ✅ 新补 |
| `main_fiscal_reform_pack` | failed | authority<50 或 public_support<48 | `court_fierce_resistance` | active, progress+12 | 理财包失败被旧党定义为聚敛失政 | ✅ 新补 |
| `main_baojia_baoma_route` | completed | unrest 降3 | `baojia_active` / `baoma_active` | active | 强兵制度立 | ✅ completes |
| `main_baojia_baoma_route` | active | overdue≥2 + unrest≥42 | `court_fierce_resistance` | active, progress+6，可重复 | 保甲训练扰民、连坐争议成为攻讦点 | ✅ 新补 |
| `main_baojia_baoma_route` | failed | — | `baojia_active` / `baoma_active` | suspended | 乡兵与保马制度停摆 | ✅ 新补 |
| `main_wangshao_hehuang` | active | overdue≥2 + army_supply<58 | `old_party_pressure` | active, progress+8，可重复 | 西北军粮拖累改革叙事，旧党转攻“开边耗财” | ✅ 新补 |
| `main_wangshao_hehuang` | active | overdue≥3 + fiscal_pressure≥55 | `court_fierce_resistance` | active, progress+10 | 战费过重引发朝争 | ✅ 新补 |
| `main_wangshao_hehuang` | completed | 战争弧 outcome ready | — | flag:`hehuang_campaign_success`（建议新增 session flag） | 熙河战功可作为后续压制旧党压力的依据 | ⚙️ 建议 |
| `main_drought_famine_crisis` | completed | unrest 降4 | `drought_crisis_resolved` | completed | 旱荒收束 | ✅ completes |
| `main_drought_famine_crisis` | active | disaster_index≥35 + public_support<48 | `old_party_pressure` | active, progress+8，可重复 | 旱荒未解，旧党将灾异解释为新法失德 | ✅ 新补 |
| `main_drought_famine_crisis` | failed | flag:`green_sprout_active` | `green_sprout_reform_failed` | active, progress+20 | 赈济失败反噬青苗合法性 | ✅ 新补 |
| `main_drought_famine_crisis` | failed | unrest≥50 | `court_fierce_resistance` | active, progress+12 | 流民图/灾荒舆论触发朝堂激烈反抗 | ✅ 新补 |
| `main_song_viet_war_1075` | active | — | `song_viet_war_active` | active + flag:`song_viet_war_active` | 战争弧开启时同步显化政策节点 | ✅ 新补 |
| `main_song_viet_war_1075` | active | overdue≥2 + army_morale<58 | `court_fierce_resistance` | active, progress+8，可重复 | 南征久战伤军心，言官攻击理财误国 | ✅ 新补 |
| `main_song_viet_war_1075` | active | overdue≥3 + fiscal_pressure≥55 + unrest≥48 | `wang_anshi_retired` | active + flag:`wartime_resignation_pressure` | 战争、财政、民怨三者叠加，推动罢相危机提前成形 | ✅ 新补 |
| `main_wang_anshi_resignation_crisis` | active | fiscal_pressure≥48 + authority<50 或 public_support<46 | `wang_anshi_retired` | active | 危机进行中即形成罢相压力 | ✅ 新补 |
| `main_wang_anshi_resignation_crisis` | completed | spawn 条件已满足 | `wang_anshi_retired` | active | 罢相 | ✅ completes |

---

## 二、第五节：随机任务池 · 因果方向表（39 项全覆盖）

### agriculture 农政

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `agri_spring_encourage_farming` | `green_sprout_active` progress+3；`fiscal_reform_pack_active` progress+2 | 若 tax_completion 仍<50，则 `old_party_pressure` progress+3 | 劝农使青苗/理财拥有基层税粮基础 |
| `agri_irrigation_or_land_improvement` | `drought_crisis_resolved` progress+6 | disaster_index≥35 时失败 → `old_party_pressure` progress+4 | 水利是抗灾合法性来源 |
| `agri_mulberry_silk_promotion` | `fiscal_reform_pack_active` progress+3；`equalized_transport_active` progress+2 | public_support<48 时失败 → `court_fierce_resistance` progress+3 | 蚕桑增课连接财政改革，但过度夺农则反噬 |
| `agri_spring_grain_lending` | `green_sprout_active` progress+8 | flag 青苗已开时失败 → `green_sprout_reform_failed` progress+8 | 春贷就是青苗实务演练 |
| `agri_post_disaster_replant` | `drought_crisis_resolved` progress+8 | disaster_index≥35 时失败 → `court_fierce_resistance` progress+5 | 灾后复耕决定旱荒能否收束 |
| `agri_song_irrigation_charter` | `drought_crisis_resolved` progress+6；`fangtian_active` progress+2 | corruption≥44 时失败 → `old_party_pressure` progress+4 | 水利条约与方田基层丈量互相支撑 |

### faction 党争

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `faction_balance_court` | `old_party_pressure` suspended | failed → `old_party_pressure` progress+6 | 平衡朝堂可暂压旧党压力 |
| `faction_anti_corruption` | `sansi_established` progress+4；`fangtian_active` progress+3 | failed → `court_fierce_resistance` progress+5 | 反腐失败使条例司/方田被质疑 |
| `faction_stability_optional` | `old_party_pressure` suspended | failed → `court_fierce_resistance` progress+5 | 台谏纷争压不住则升级 |
| `reform_green_coerce_probe` | 不推进改革节点；建议只设 flag:`green_coercion_checked` | failed → `green_sprout_reform_failed` progress+12；`court_fierce_resistance` progress+10 | 强贷若纠不住，青苗失败与朝争同步上升 |
| `reform_gentry_boycott` | `green_sprout_active` progress+4 | failed → `green_sprout_active` suspended；`court_fierce_resistance` progress+8 | 豪右抵制会堵住青苗基层执行 |
| `reform_water_gentry_monopoly` | `fangtian_active` progress+4；`drought_crisis_resolved` progress+4 | failed → `old_party_pressure` progress+4 | 清豪右占堰，使方田/水利合理化 |
| `reform_throne_debate` | `wang_anshi_leading_reform` progress+6；`reform_mandate` progress+4 | failed → `old_party_pressure` progress+6 | 御前辩论是政治合法性节点 |

### finance 财政

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `finance_raise_treasury` | `fiscal_reform_pack_active` progress+8 | fiscal_pressure≥55 时 failed → `court_fierce_resistance` progress+5 | 国库充盈是理财包推进条件 |
| `finance_reduce_pressure` | `fiscal_reform_pack_active` progress+4；`old_party_pressure` suspended | failed → `old_party_pressure` progress+6 | 压不住财政压力，旧党更易攻“聚敛” |
| `finance_relieve_tax` | `corvee_active` progress+3；`green_sprout_active` progress+3 | failed + unrest≥45 → `green_sprout_reform_failed` progress+5 | 税负缓和能保新法民意 |
| `reform_green_spring_lend` | `green_sprout_active` progress+8 | failed → `green_sprout_reform_failed` progress+8 | 青苗钱实务 |
| `reform_even_transport_pilot` | `equalized_transport_active` progress+8 | failed → `old_party_pressure` progress+5 | 均输贡调若失败，会被视为扰漕 |

### fiscal 财政制度

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `fiscal_tax_collection_push` | `sansi_established` progress+4；`green_sprout_active` progress+4；`fiscal_reform_pack_active` progress+4 | public_support<45 时 failed → `court_fierce_resistance` progress+5 | 清厘钱粮既推条例司，也推青苗和理财包 |
| `fiscal_increase_tax_levy` | treasury 达标时 `fiscal_reform_pack_active` progress+6 | failed + unrest≥45 → `court_fierce_resistance` progress+8 | 加派是高收益高反噬 |
| `fiscal_reduce_court_spending` | `reform_mandate` progress+3；`fiscal_reform_pack_active` progress+4 | failed → `old_party_pressure` progress+4 | 节流证明变法不是只向民间加压 |
| `fiscal_expand_state_monopoly` | `shiyi_active` progress+8 | failed + corruption≥44 → `court_fierce_resistance` progress+6 | 市易/榷利若被吏胥侵渔会激化反抗 |
| `fiscal_corvee_commutation` | `corvee_active` progress+10 | failed + unrest≥42 → `court_fierce_resistance` progress+6 | 随机免役任务是主线免役的执行支线 |
| `fiscal_equalized_transport` | `equalized_transport_active` progress+8 | failed → `old_party_pressure` progress+5 | 均输试点的直接推进边 |

### internal_affairs 朝政

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `internal_reduce_corruption` | `sansi_established` progress+6；`fangtian_active` progress+2 | failed → `old_party_pressure` progress+5 | 吏治清则财政改革可信 |
| `internal_restore_authority` | `sansi_established` progress+4；`reform_mandate` progress+4 | failed → `court_fierce_resistance` progress+4 | 权威是建制前提 |
| `internal_stabilize_order` | `baojia_active` progress+4；`old_party_pressure` suspended | failed → `court_fierce_resistance` progress+5 | 稳定秩序支撑保甲 |
| `reform_sansi_audit` | `sansi_established` progress+8 | failed → `old_party_pressure` progress+6 | 条例司勘账是机构能力证明 |
| `reform_canal_patrol` | `equalized_transport_active` progress+6；`fiscal_reform_pack_active` progress+3 | failed → `old_party_pressure` progress+5 | 漕弊治理连接均输 |
| `reform_memorial_backlash` | authority≥56 时 `old_party_pressure` suspended | failed → `old_party_pressure` progress+10 | 台谏攻讦若折冲失败，旧党压力显化 |
| `reform_local_delay` | `green_sprout_active` progress+4；`sansi_established` progress+3 | failed → `green_sprout_active` suspended；`court_fierce_resistance` progress+5 | 地方阳奉阴违让新法止于纸面 |

### livelihood 民生

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `livelihood_reduce_unrest` | unrest<40 时 `old_party_pressure` suspended；`baojia_active` progress+3 | failed → `court_fierce_resistance` progress+6 | 民怨降低会削弱旧党攻势 |
| `livelihood_disaster_relief` | `drought_crisis_resolved` progress+10 | failed + flag 青苗已开 → `green_sprout_reform_failed` progress+8 | 赈济失败会反噬新法合法性 |
| `livelihood_support_recovery` | `green_sprout_active` progress+3；`corvee_active` progress+3 | failed → `old_party_pressure` progress+5 | 民心恢复为新法降噪 |
| `reform_water_charter` | `drought_crisis_resolved` progress+6；`fangtian_active` progress+3 | failed → `old_party_pressure` progress+4 | 水利条约既是民生，也服务田亩秩序 |

### military 军事

| 任务 | completed 指向 | failed / active 反噬 | 设计意图 |
|---|---|---|---|
| `military_raise_morale` | `baojia_active` progress+4；`song_viet_war_active` progress+3 | failed → `court_fierce_resistance` progress+4 | 军心与强兵/战争节点相连 |
| `military_secure_supply` | `baoma_active` progress+5；`song_viet_war_active` progress+4 | failed + army_supply<58 → `court_fierce_resistance` progress+5 | 补给不足会转化为朝争 |
| `military_reduce_revolt` | `baojia_active` progress+5 | failed → `court_fierce_resistance` progress+4 | 流寇风险下降证明保甲有效 |
| `reform_northwest_budget` | completed 时可 `old_party_pressure` suspended（若 engine 支持缓释边） | failed + army_supply<58 → `court_fierce_resistance` progress+10；fiscal_pressure≥55+unrest≥48 → `wang_anshi_retired` active | 西北边饷是改革财政压力的军事化表现 |

---

## 三、第七节：任务 × 节点速查矩阵（补全版）

| 任务 ↓ / 节点 → | 青苗试行 | 青苗失败 | 群臣反抗 | 旧党压力 | 条例司 | 免役 | 理财包 | 保甲 | 旱荒收束 | 罢相 | 备注 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `main_xining_reform_mandate` |  |  |  | ● |  |  |  |  |  |  | failed→守旧/旧党话语权 |
| `main_wang_anshi_to_court` |  |  |  | ● |  |  |  |  |  |  | failed→主持人迟滞 |
| `main_sansi_establish` |  |  | ● | ● | ● |  |  |  |  |  | completed→条例司；拖延→旧党 |
| `main_green_sprout_route` | ● | ● | ● |  |  |  |  |  |  |  | 已实现主链 |
| `main_corvee_commutation` |  |  | ● |  |  | ● |  |  |  |  | failed→役法僵局 |
| `main_fiscal_reform_pack` |  |  | ● | ● |  |  | ● |  |  |  | failed/高压→朝争；completed→理财包 |
| `main_baojia_baoma_route` |  |  | ● |  |  |  |  | ● |  |  | 扰民逾期→反抗 |
| `main_wangshao_hehuang` |  |  | ● | ● |  |  |  |  |  | ●? | 补给/财政崩坏→朝争，极端时促罢相 |
| `main_drought_famine_crisis` |  | ● | ● | ● |  |  |  |  | ● | ●? | failed→青苗合法性崩；高压可并入罢相危机 |
| `main_song_viet_war_1075` |  |  | ● | ● |  |  |  |  |  | ● | 战事拖延+财政民怨→罢相压力 |
| `main_wang_anshi_resignation_crisis` |  |  |  | ● |  |  |  |  |  | ● | 完成→罢相 |
| `agri_spring_grain_lending` | ● | ● |  |  |  |  |  |  |  |  | 完成+；失败反噬青苗 |
| `fiscal_tax_collection_push` | ● |  |  |  | ● |  | ● |  |  |  | 钱粮清厘支撑三线 |
| `fiscal_corvee_commutation` |  |  | ● |  |  | ● |  |  |  |  | 完成推免役，失败扰民 |
| `fiscal_equalized_transport` |  |  |  | ● |  |  | ● |  |  |  | 完成推均输，失败旧党 |
| `fiscal_expand_state_monopoly` |  |  | ● |  |  |  | ● |  |  |  | 市易推进/失败商怨 |
| `reform_even_transport_pilot` |  |  |  | ● |  |  | ● |  |  |  | 均输支线 |
| `reform_green_spring_lend` | ● | ● |  |  |  |  |  |  |  |  | 青苗实务 |
| `finance_raise_treasury` |  |  |  |  |  |  | ● |  |  |  | 国库支撑理财包 |
| `reform_sansi_audit` |  |  |  | ● | ● |  |  |  |  |  | 勘账推条例司 |
| `reform_local_delay` | ● |  | ● |  | ● |  |  |  |  |  | 地方拖延阻滞新法 |
| `reform_memorial_backlash` |  |  |  | ● |  |  |  |  |  |  | failed→旧党压力 |
| `reform_gentry_boycott` | ● | ●? | ● | ● |  |  |  |  |  |  | 豪强抵制青苗 |
| `reform_green_coerce_probe` |  | ● | ● |  |  |  |  |  |  |  | 强贷纠弹失败最危险 |
| `reform_northwest_budget` |  |  | ● | ● |  |  |  |  |  | ●? | 西北边饷拖垮财政 |
| `military_secure_supply` |  |  | ●? |  |  |  |  | ● |  |  | 完成推保马，失败朝争 |
| `military_reduce_revolt` |  |  | ●? |  |  |  |  | ● |  |  | 完成证明保甲有效 |
| `livelihood_disaster_relief` |  | ● | ●? | ● |  |  |  |  | ● |  | 赈济成功收束，失败反噬 |
| `livelihood_reduce_unrest` |  |  | ●? | ● |  |  |  | ● |  |  | 民怨降则旧党失据 |
| `reform_water_charter` |  |  |  | ●? |  |  |  |  | ● |  | 水利救灾支线 |

---

## 四、数值 → 任务 对照补全

| 数值 key | 升高时易刷新的任务 | 降低时易刷新的任务 | 关联主线完成难度 |
|---|---|---|---|
| `fiscal_pressure` | `finance_reduce_pressure`, `fiscal_increase_tax_levy`, `reform_throne_debate`, `reform_northwest_budget` | `finance_raise_treasury`, `fiscal_reduce_court_spending` | `main_fiscal_reform_pack`, `main_song_viet_war_1075`, `main_wangshao_hehuang` |
| `tax_completion_index` | `agri_spring_encourage_farming`, `agri_mulberry_silk_promotion`, `fiscal_tax_collection_push` | `reform_local_delay`, `reform_canal_patrol`, `reform_even_transport_pilot` | `main_green_sprout_route`, `main_corvee_commutation`, `main_fiscal_reform_pack` |
| `unrest` | `faction_stability_optional`, `internal_stabilize_order`, `livelihood_reduce_unrest`, `reform_memorial_backlash`, `fiscal_corvee_commutation` | `faction_balance_court`, `livelihood_support_recovery` | `main_baojia_baoma_route`, `main_drought_famine_crisis`, `main_wang_anshi_resignation_crisis` |
| `authority` | `reform_throne_debate` | `internal_restore_authority`, `faction_balance_court`, `main_sansi_establish` 压力上升 | `main_sansi_establish`, `main_wang_anshi_resignation_crisis` |
| `public_support` | `reform_gentry_boycott` 若税强高；`faction_balance_court` 若朝局低 | `livelihood_support_recovery`, `finance_relieve_tax`, `tax_remission_relief` 类任务 | `main_green_sprout_route`, `main_corvee_commutation`, `main_drought_famine_crisis` |
| `corruption` | `internal_reduce_corruption`, `faction_anti_corruption`, `reform_sansi_audit`, `reform_green_coerce_probe`, `reform_water_gentry_monopoly` | — | `main_sansi_establish`, `main_fiscal_reform_pack` |
| `disaster_index` | `livelihood_disaster_relief`, `agri_post_disaster_replant`, `agri_irrigation_or_land_improvement`, `reform_water_charter`, `agri_song_irrigation_charter` | — | `main_drought_famine_crisis` |
| `army_supply` | — | `military_secure_supply`, `reform_northwest_budget`, `reform_war_supply` 类事件 | `main_wangshao_hehuang`, `main_song_viet_war_1075` |
| `army_morale` | `military_raise_morale` 已完成后战争任务更易推进 | `military_raise_morale`, `reform_northwest_budget` | `main_song_viet_war_1075`, `main_baojia_baoma_route` |
| `revolt_risk` | `military_reduce_revolt`, `bandit_suppression` 派生任务 | `military_reduce_revolt` 权重降低 | `main_baojia_baoma_route`, 战争逾期压力 |
| `treasury_balance` | `fiscal_expand_state_monopoly` 权重下降；战争任务更易完成 | `finance_raise_treasury`, `fiscal_expand_state_monopoly`, `fiscal_increase_tax_levy` | `main_fiscal_reform_pack`, 两条 war_arc |

---

## 五、待决问题建议

1. `scholar_support` 建议进入 `METRIC_SCHEMA`，初值 48–52，主要由台谏、旧党、大臣影响力派生。
2. `conflicts` 边建议用于“守旧路线 vs 变法路线”“市易暂缓 vs 理财包完成”这类互斥，不建议用 `advances` 硬模拟互斥。
3. `suspended` 后任务池建议改权重：相关 `reform_*` 任务不剔除，但权重降 50%；反噬类任务权重升 25%。
4. 两条战争弧建议保留独立 `war_arc`，政策节点只承接 flag 与风险压力，避免把战斗阶段塞进国策树。
5. 如果 engine 不支持 `progress_delta` 负数，本稿所有“缓释压力”的设计均用 `set_status:"suspended"` 表达；未来可新增 `mitigates` 边。

---

## 六、落地 JSON

见同目录：`policy_xining_advances_draft.json`。本 JSON 包含主线补齐 + 高优先级随机任务共 57 条 `advances` 边。
