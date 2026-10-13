# 离线计算输入与核验

只在任务需要且宿主允许离线执行时读取和运行。脚本仅依赖 Python 3.10+ 标准库，不安装依赖、不联网、不读取环境凭证。用户明确零工具时不要加载本文件，采用 SKILL.md 内手算规则。

本页保留单项检查接口。多期偿债、互斥回售情景、融资提款或产品组合/提款边界，优先使用 [完整计算工作流](workflow-contract.md) 的统一输入、余额滚动和文件生成；不要把下面几个独立命令的结果手工拼成未经勾稽的“完整流程”。

## 目录

- [执行与共同约定](#执行与共同约定)
- [cash：净息和占款](#cash净息和占款)
- [debt-window：同口径债务勾稽](#debt-window同口径债务勾稽)
- [funding：带用途约束的跨期来源匹配](#funding带用途约束的跨期来源匹配)
- [实际工作簿与交付检查](#实际工作簿与交付检查)

## 执行与共同约定

在 Skill 目录下执行，输入、输出路径由实际任务工作区决定：

```bash
python3 scripts/fixed_income_checks.py cash cash-input.json
python3 scripts/fixed_income_checks.py debt-window debt-input.json
python3 scripts/fixed_income_checks.py funding funding-input.json
python3 scripts/verify_workbook.py report.xlsx --required-sheet 债务明细 --required-sheet 资金匹配 --require-formulas
```

计算返回 JSON；退出码非零时修正输入错误，不能把报错当作零值。金额和利率用十进制字符串，利率为小数而非百分数字面值；同次运行不混币种或单位。单项计算在独立的 512 位 Decimal 上下文中运行，不改变调用方精度；年化将分子、分母分别相乘后再相除，避免先除后乘引入可避免的尾差。金额展示最后才按任务要求舍入；非复利模型，不提供最优投资/交易建议。小数精度本身不证明原始输入正确。

所有参数须能回指材料页码/表格/单元格；语义抽取由使用者负责，脚本不证明文件内容与输入一致。`null` 表示未知，除明示例外不能填成零。未使用字段及拼错字段会被拒绝。

先校验所有已填非 null 数值和日期，再按证据、范围或缺失字段决定可算部分。占款字段缺失不掩盖其他字段的非法值；未生效或不在汇总范围的债务、暂不可比的报表金额及其证据日期也须合法。证据 known_at/effective_at、余额确认/可用/失效日期和付款日均不因草稿、冻结、假设或来源缺失而免检；null 为未知，空字符串、数字或非法日期直接拒绝。该检查不把未知补零，不因缺占款基数而抹去可算净息。

证据不合格时不按其业务日期断言“已过期”或“付款不在截点后”。`debt-window/funding` 新增逐行 `admission_diagnostics`，保留证据原文定位、给定日期及分类原因；结构同[资格留痕](workflow-contract.md#资格留痕)。旧 `excluded/unresolved` 仍保留简短原因，完整障碍看诊断字段。范围排除是按输入 scope 过滤，不证明该条记录的事实资格。汇总证据另用 `aggregate_evidence_diagnostics` 留下并存障碍，kind 不是 fact 不能覆盖原始证据失效原因。

单项与完整流程共用 `scripts/input_guards.py`。JSON 读取拒绝重复字段（含嵌套和转义后同名）、非有限数字和非普通文件；不采用“后一个值覆盖前一个值”。CLI 及直接调用 `cash/debt_window/funding` 均检查形状和数值，输入大小、深度、行数及数值表示范围见 [本地资源边界](workflow-contract.md#本地资源边界)。直接调用已解析对象不能还原此前被其他解析器吞掉的重复字段；原始 JSON 应使用本包读取入口。

单项资金匹配在构图前检查资金/付款各最多 512 项、候选配对最多 50000 对；准备、配对、构图、遍历、回溯和结果展开共享 2000000 个工作单位。独立调用 `max_cover` 也保留计数保护并拒绝重复或悬空连线。超过本地支持范围以 `unsupported_size_or_work` 停止，CLI 退出码 2 且不输出结果 JSON；这些不是金融额度或风险阈值，不得删行或拆开同一余额的付款表绕过。

时间使用 `YYYY-MM-DD` 或含 UTC 偏移的完整 ISO 时间；同任务统一时区。同日只有日期、截点却精确到时刻时，不能推定发生顺序。日期窗口的闭开边界必须显式填写；不自动推断节假日、交易日或滚动十二个月的结束日。

## cash：净息和占款

必填字段：

- `principal`：报价对应本金；`annual_rate`、`interest_days`、`year_days`：已确认报价及日计数。
- `rate_kind`：`gross` 或 `net`。`fee_rate` 是按本金一次收取的比例，`fixed_fee` 是一次性金额，两者必须明确给出，免收写 `"0"`。`net` 模式要求额外费用为零，避免重复扣费；若净报价之外还有另收费项，先查明包含范围再归一。
- `availability`：`trading_day`、`withdrawal_day`，均为相对同一起点的日偏移，可为 `null`。不把它们当计息天数；真实时间的小时差可换成有依据的小数天。

可选 `occupancy`，字段完整包含：`purpose`（`withdrawal` / `trading` / `custom`）、`start_day`、`end_day`、`capital_base`、`year_days`、`basis_note`。起止与 availability 使用同一原点。用途为提现或交易时，终点必须与对应可用日一致；`custom` 必须解释另选区间的经济用途，不能规避真实的提现约束。

`capital_base` 是该年化口径下实际投入资金，是否包括预付费用须有材料或假设支持；不自动等于本金。缺少占款对象或关键字段，返回 `net_simple_annual_rate=null`，但保留可算的净息。输出年化是小数，不是百分数；`0.012` 显示为 `1.2%`。

提现可行性另按本金及净收益实际可取日期核对；本脚本不自动计算产品组合、申购粒度、最小佣金、分期手续费、复杂税费或复投。超出一次性费用模型时不得强行套用，需补明确公式或独立计算。

## debt-window：同口径债务勾稽

输入包含：

- `as_of`：研究截点。
- `meta`：`scope`、`currency`、`unit`，例如明确的合并外部债务或母公司口径。仅名字相同不足以证明抵销和分类一致。
- `window`：`start`、`end`、`include_start`、`include_end`；后两项为布尔值。
- `ledger_complete`：是否经材料核对为完整台账，布尔值；另用 `ledger_complete_evidence` 绑定完整性原文。
- `debts`：每项含唯一 `id`、`meta`、`amount`、`maturity_date`、`evidence`。只输入法定到期本金；回售压力与利息不混入此表。分期本金每期使用独立记录 ID，不能再叠加整笔本金。
- 可选 `reported`：含 `as_of`、`meta`、`window`、`basis`、`amount`，以及绑定报表金额和口径的 `evidence`。只有与上述完全可比、`basis="legal_principal"`、台账完整且无未知记录，且完整性和报表各自有合格事实证据，才算“台账减报表”的差额；财务账面短期负债未桥接前用其他 basis，返回 `incompatible_basis`。

每项 `evidence` 包含 `source`（原文定位）、`known_at`、`effective_at`、`status`（`effective` / `draft` / `revoked` / `unknown`）。缺证据或截点后证据进入 unresolved，不填入已知本金。有效文件的未来付款日不等于文件未来才生效；不要混淆 effective_at 与 maturity_date。

汇总级证据 `ledger_complete_evidence`、`reported.evidence` 和下述 `demand_schedule_complete_evidence` 均须包含上述四项及明确的 `kind="fact"`。来源必须定位支持该具体断言的原文；仅布尔值为 true 不算完整性证据。汇总证据缺省、缺项、截点后、失效或 kind=assumption 时不算确定勾稽差额或完整缺口，但保留逐笔合格证据支持的小计。登记结构不证明原文语义正确，仍须人工复核。输出 `aggregate_evidence`、`aggregate_evidence_status` 与对应的 `*_complete_confirmed`，不可删除未知原因后只展示结果。

输出 included、excluded、unresolved 明细及 `known_legal_principal`；后者只是已知小计。不要将其直接称为完整本金总额，或把“可比差额”当作已解释的会计错误。

## funding：带用途约束的跨期来源匹配

输入包含 `as_of`、`meta`、`funds`、`demands`、`demand_schedule_complete`；另用 `demand_schedule_complete_evidence` 绑定需求完整性证据，结构同上。meta 同上。一次提交全部研究期间的付款，不要在各年重启同一余额。只有本金、利息及适用情景付款日期均已核实时，才能把 demand_schedule_complete 设为 true；缺少合格事实证据仍不输出完整缺口。

`registered_debt_ids` 是从材料登记的完整债务 ID 数组，各项须为非空且不重复的文本。任何资金填写 `debt_ids` 时必须提供该登记；提供后，资金引用及所有 demands 的 `debt_id` 都须属于登记。不能只从当前 demands 推断登记，因为合法专户可以服务已登记但本期无付款的债务，这类资金保持未使用，不算非法输入。无债务限制且未提供该数组时，单项接口不声称完成债务登记核验。

funds 每项：

- `id`：记录 ID；`balance_id`：经济余额 ID，用于防止现金、授信或专户同一额度重复入表。一般账户必须先剔除另列的受限子余额；不同名称不能掩盖重复。
- `owner`、`amount`、`meta`：实际持有主体、研究截点尚未消耗且可动用的余额及口径。授信仅可用“已批准、无未满足提款条件、未使用”部分；已提款入现金的额度不得再列一次授信。
- `balance_at`：该余额被确认的截点，须与 as_of 可比且相同。旧快照不能凭 known_at 较新就滚成新余额。
- `available_from`、`expires_on`：可使用起日和末日，ISO 日期；expires_on 的 `null` 特指材料确认无到期限制，不代表不知道。未知到期限制的资金将 status 设为 unknown。末日不能早于起日；准入证据支持的末日早于截点时记录 `expired_at_cutoff`，不列为当前未用余额；证据不合格时保留原证据障碍，不作过期事实判断。末日等于截点日不代表翌日仍可支付。若精确截点同日才可用但缺时刻，需先核对后再处理，不推定当日零时可用。
- `status`：`available` / `conditional` / `planned` / `frozen` / `unknown`，仅 available 进入已确认来源。
- `restriction`：`unrestricted` / `dedicated` / `unknown`；`debt_ids`、`purposes`：非空文本元素组成且无重复项的数组。unrestricted 时两数组须为空；dedicated 时两个数组均须非空。用途只接受 `principal`、`interest`、`put`，不能默认为一般资金，也不自动纠正拼写。unknown 可以保留空数组及未知限制，但不进入确认来源；一旦填写限制，仍须通过用途和债务登记检查。
- `evidence`：与 debt-window 相同；截点后确认或尚未生效不能晋升为 available。

demands 每项：唯一 `id`、`payment_id`（同笔经济付款不可重复）、`debt_id`、`obligor`、`amount`、`meta`、`due`（ISO 日期）、`purpose`、`evidence`。仅处理截点后的付款；已逾期及截点当日精确时点不明的项目另核，不能静默排除后宣称全覆盖。

demands 的 purpose 同样只接受 `principal/put/interest`。用途拼错、未登记引用、重复限制项属于输入错误，即使该资金被冻结、待批或暂不使用，也先拒绝计算，而不是输出“无法匹配”的业务缺口。未知证据或未知限制与非法结构分开处理，不能把两者都写成确定缺口。

法定到期与回售是同一本金的不同情景，不能分别赋不同 payment_id 后同时加入。正常与压力情景分开运行、分别标示假设；来源的批准/未知状态不随情景变成事实。融资兑现、资金调拨、未来经营流入、偿债后新增债务不由脚本生成；复杂循环融资须另建闭合现金流模型。

脚本按 owner=obligor、可用/到期日期、债务 ID 和用途构建允许匹配，再求这些已确认余额对给定付款的最大覆盖；每个余额全期间最多消耗一次。不会默认子公司现金可偿母公司债务，也不会先汇总专户后再任意抵扣。分配方案不是业务优先级最优解或交易指令。

输出逐笔 allocations、未覆盖付款、剩余余额、排除来源及不匹配原因。`known_schedule_uncovered` 是已知付款对给定已确认来源的缺口；仅完整付款表时提供 `full_schedule_gap_against_confirmed_supplied_sources`。后者仍不是“未来全部融资后最终缺口”，不说明违约概率；条件额度、未知款项须在报告中另列。

## 实际工作簿与交付检查

计算 JSON 是中间结果，不是用户要求的 XLSX。用宿主现有且获授权的工作簿能力，保留原始数据、指标公式、到期明细、资金匹配、情景假设与待核项；工作表名跟随本次任务，不固定为某次评测的名称。核对任务所要求的内容后再传 `--required-sheet`，不要只为让校验器通过而建空表或填无关内容。

`verify_workbook.py` 只读文件，先限制 ZIP 大小、展开量、条目数、XML 深度和单元格数量，再核验 OPC 内容类型、根关系及工作表关系。拒绝路径穿越、重复条目、符号链接、DTD/实体、宏、嵌入对象、外链、隐藏表及未支持的结构。这些是本地文件解析安全限制。

生成、回读和公式引用共用坐标检查：本子集只接受大写 A1 坐标，列 `A` 至 `XFD`、行 `1` 至 `1048576`，不接受前导零、范围或绝对引用；空行的行号也必须合法。表名允许中文及内部单引号，长度 1 至 31 字符；拒绝 `[]:*?/\\`、控制/非法 XML 字符、首尾单引号、保留名 `History` 和不区分大小写的重名。`sheetId` 必须为 ASCII 十进制整数，数值范围 1 至 65534 且唯一；`01` 与 `1` 不能成为两个编号。上述编号范围按 Office 支持约束，不泛称整个 OOXML 标准都要求此范围。

写出前检查全部坐标、元数据及公式语法/引用；失败不创建工作簿文件。回读仍独立检查缓存、结构和所需表，不能以“由本脚本生成”免除复核。

支持本工作流生成的被动结构、内联文本、数值及同表输入单元格的加减乘除；不使用 `eval`，不执行工作簿代码，不调用网络。支持的公式会重新计算并与缓存核对；缺缓存给警告，公式链、跨表公式、复杂函数、样式/图表等超出该校验器的支持范围时明确拒绝，不静默忽略。普通 Excel 文件被拒绝不等于其业务错误，应使用另一个获授权且适用的核验器，不得把本校验器的失败改标成通过。

算术子集采用 15 位有效数的输入/常量、50 位中间运算和最终 15 位结果。缓存先按原始十进制数解析，再与复算值精确比较，不能预先舍入掩盖微小差异；等值尾零、正负零不算差异。非公式输入单元格若超过支持精度且舍入会改变值，则明确拒绝，不擅自修正。生成工作簿时可将精确 JSON 结果投影为 15 位显示数，结果与显示算术的容差勾稽不用于缓存验证。此约定是可复现有限模型，不是 Excel 引擎兼容性承诺。

结果中的 `formula_cells_checked` 记录检查到的公式单元格数量。无公式文件可以通过结构或逐格一致性核验，但数量为零且 `recalculated=false`；有公式也只有检查无错误、无警告时才标为 true。需要公式的交付使用 `--require-formulas`，不能将纯数值表的结构通过描述为完成公式复算。

单独核验的 `financial_content_verified=false`，即使 `recalculated=true` 也只说明支持的算术复算无错；完整工作流 `verify` 另外将所有单元格、输入、报告与重新计算的统一结果比较。该检查仍不证明原文语义抽取、法律解释、市场真实性或用户已收到文件。保留路径、哈希、大小和回读记录，最终通过宿主实际挂载；未完成的文件或业务内容须明确说明。
