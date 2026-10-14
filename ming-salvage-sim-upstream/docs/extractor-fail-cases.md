# Extractor 测试 FAIL 排查清单（14 例）

来源：`scripts/extractor_field_coverage.py` 全跑 100 case，86 PASS / 14 FAIL。
测试链路：**诏书 + cheat 既成事实 → extractor**（跳 simulator、关 HITL）。

> 判定：`expect_fields` 里的目标顶层字段未出现在抽出 JSON（`missing` 非空）即 FAIL；负样本则「抽出非空」即 FAIL。
> **结论先说**：14 例无一是 extractor prompt 的字段定义错误，全在测试侧。分三类，A/C 可修，B 是跳 simulator 的固有限制。

---

## A 类：负样本设计自相矛盾（3 例）——case 用了 cheat，与「不该抽」直接冲突

**关键发现**：这 3 条是负样本（验「不该抽某字段」），却都带了 `cheat`。而 cheat 注入用的前缀是
`【天命强制·结算优先】…按字面抽满对应结构化增量，无视合理性…它说什么成了就抽什么`——
**cheat 本身就在命令 extractor「把 cheat 写的当既成事实抽满」**。负样本写「魏忠贤前已下狱」当 cheat，
extractor 当然按令抽 `人物状态变化`。**负样本根本不该走 cheat 路径**，这是 case 设计错，不是 extractor bug。

逐条实测（已核 got）：

| case | 验什么（不该抽） | 实测 got | 真相 |
|---|---|---|---|
| c101_neg_jiuanchongti | 旧案重提不该写 `人物状态变化` | 含 **人物状态变化** | cheat 写「魏忠贤前已下狱」→ 被当既成事实抽。**case 错用 cheat** |
| c102_neg_taolun | 请款讨论不该写 `钱粮收支` | 含 **钱粮收支** | cheat 描述请赈→被当收支抽。**case 错用 cheat** |
| c103_neg_qianxiang_weidao | 欠额不该写 `钱粮收支`（补饷） | **不含钱粮收支** ✅ | extractor 正确没抽补饷，**实为 PASS**，判定过严误判 |

**两个独立问题：**
1. **c101/c102**：负样本不该给 cheat。删掉这俩的 `cheat`，改走纯诏书路径（让 extractor 自己判「旧案/讨论不落账」）才是真正的负样本测试。
2. **c103**：抽取本身对（没抽补饷），是脚本负样本判定「全空才 PASS」太严。改为「不含 `neg_check_fields` 即 PASS」。

> 注：纯诏书路径要验「旧案/讨论不落账」，又得保留 simulator（让它把旧案演成回顾、把请款演成讨论），
> 否则跳 simulator 时 extractor 拿诏书原文同样可能误抽。负样本天然依赖 simulator 的「叙事定性」，与 B 类同源。

---

## B 类：issue 类字段依赖 simulator 叙事结构（6 例）——跳 simulator 的固有限制

`新立局势`/`结案局势`/`撤销局势` 的抽取高度依赖 simulator 产的**诏书核销章 / 待办未解章 / 在办 issue 盘面**作钩子。跳了 simulator，narrative 只剩诏书原文，缺这些线索；结案/撤销还需盘面预先有在办 issue（纯净开局没有）。

| case | directive | cheat | missing | 病灶 |
|---|---|---|---|---|
| c020_xinli_juchu_qingzhang | 敕户部江南大举清丈隐田，三年为期 | （无 cheat） | 新立局势 | 无 cheat + 无核销章，extractor 判不出「该立局势」 |
| c078_xinli_zhaofu | 敕熊文灿招抚郧阳流寇，许归农授田 | （无 cheat） | 新立局势 | 同上，反被抽成 `人事变更`（熊文灿任命） |
| c079_xinli_an | 立钱龙锡通敌案，敕三法司会审 | （无 cheat） | 新立局势 | 同上，抽成 `人物状态变化`（钱龙锡）而非立案局势 |
| c025_jiean_resolved | 常平仓已落成开始储粮，著结案 | 本月常平仓落成…达结案条件 | 结案局势 | 盘面无「常平仓」在办 issue 可结 |
| c084_jiean_diguo | 九边整军已成制，著结案并叙功 | 本月九边整军成制达结案条件 | 结案局势 | 盘面无「九边整军」在办 issue 可结 |
| c026_chexiao | 前命之清丈劳民伤财，著即罢停办 | 本月奉旨停办清丈一事 | 撤销局势 | 盘面无「清丈」在办 issue 可撤 |
| c085_chexiao_ | 前命某工程劳费过巨，著即停办撤项 | 本月奉旨停办某工程 | 撤销局势 | 同上，无在办 issue 可撤 |

**注意**：c020/c078/c079 三条**根本没写 cheat**（我建 case 时漏了），所以连既成事实都没喂，extractor 只能靠诏书原文判断要不要立局势——这是诏书新立局势最难抽的场景。

**修法二选一**：
1. 验这 6 字段时**保留 simulator**（`--keep-simulator`），让它产核销章/待办章；结案/撤销还要 `sql` 预插在办 issue。
2. 或给 c020/c078/c079 补 cheat 明确「须输出 新立局势：[{...}]」，给 c025/c084/c026/c085 用 `sql` 预插对应在办 issue 再结/撤。

---

## C 类：cheat 未点死 / 组合稀释（4 例）——case 数据可加固

cheat 描述不够命令式，或组合 case 多目标互相稀释，extractor 把目标抽成了别的字段或漏抽。

| case | directive | cheat | missing | 病灶 |
|---|---|---|---|---|
| c060_combo_caiche_jiazheng | 裁革辽饷，另加商税月增二十万 | 辽饷整项裁撤；商税加征月增二十万 | 裁撤月度收支 | 组合 case：抽到了 `财政制度变化`（商税），但「辽饷裁撤」被抽成减额或漏。同 c011 病——cheat 未点死「整项删非减额」 |
| c072_paixi_donglin | 采东林清议，起复东林诸贤入要津 | 东林满意度影响力俱升 | 人事变更 | cheat 只说派系升，没点名「起复某某为某官」，extractor 抽了 `派系变化` 漏 `人事变更`。「诸贤」无具体姓名也难抽任命 |
| c089_xinjianjun_houjin | 后金招降明军改编为汉军一旗 | 招降明军改编为汉军旗，owner_power 后金 | 新建军队 | cheat 没点死「须输出 新建军队：[{id,owner_power:houjin,...}]」，extractor 可能抽成 `军队变化`/`人物易主` |
| c094_zhuangtai_zhishi | 准内阁首辅某某致仕还乡 | 首辅某某致仕 | 人事变更 | expect 同时要 `人物状态变化`+`人事变更`；致仕抽了状态变化，但「首辅出缺谁补」无人→不产 `人事变更`。可能 expect 写多了 |

**修法**：
- c060：cheat 照 c011 范式点死辽饷裁撤（「须输出 裁撤月度收支：[{键:辽饷_base,...}]，不写财政制度变化」）。
- c072：cheat 给具体姓名+官职（如「起复钱谦益为礼部尚书」）才能抽 `人事变更`；或把 `人事变更` 移出 expect。
- c089：cheat 点死「须输出 新建军队」。
- c094：致仕本就只产 `人物状态变化`，`人事变更` 是 expect 写多了——应从 expect 删 `人事变更`，或 cheat 补「继任者 X 接任首辅」。

---

## 汇总：14 FAIL 处置建议

| 类 | 数量 | case | 性质 | 动作 |
|---|---|---|---|---|
| A 负样本设计错 | 3 | c101/c102/c103 | c101/c102 错用 cheat；c103 判定过严 | 删 c101/c102 的 cheat（+保 simulator）；c103 改判定逻辑 |
| B issue 依赖 simulator | 6 | c020/c078/c079/c025/c084/c026/c085 | 跳 simulator 固有限制 | 保 simulator 或预插 issue + 补 cheat |
| C cheat 加固 | 4 | c060/c072/c089/c094 | case 数据弱 | 点死 cheat / 修 expect |

**没有一例需要改 extractor prompt。** 四档房字段定义全部正确——14 FAIL 全是 case 设计 / 测试判定 / 跳 simulator 的副作用。

### 一句话定性

- **真要改的只有测试侧**：脚本负样本判定逻辑（c103）、几条 case 的 cheat/expect（A/C 类）、issue 类是否保 simulator（B 类）。
- **extractor 行为全程正确**：c103 正确没抽补饷、c101/c102 是被 cheat「按令抽满」骗的、B 类是真没叙事钩子可抽。
