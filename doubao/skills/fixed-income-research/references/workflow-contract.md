# 完整离线计算工作流

只在当前任务需要且允许离线工具时使用。目录内 Python 3.10+ 标准库脚本不联网、不安装依赖、不读取凭证、不交易。明确零工具任务不加载本页、不运行脚本。金融检索规则不变。

## 目录

- [从材料到交付](#从材料到交付)
- [统一输入](#统一输入)
- [偿债与融资分析](#偿债与融资分析)
- [现金产品与提款可行域](#现金产品与提款可行域)
- [本地资源边界](#本地资源边界)
- [产物、精度和验证范围](#产物精度和验证范围)

入口脚本依赖 `workflow_inputs.py`、`fixed_income_checks.py`、`debt_workflow.py`、`cash_workflow.py`、`workbook_io.py` 和共享的 `input_guards.py`；这些是内部模块，不是需逐个运行的独立任务。

## 从材料到交付

1. 读取本次获授权的原始材料，抽取对象、日期、单位、条款和金额，保留页码/单元格。抽取属于语义工作，不因有脚本而跳过。先区分事实、假设、未知；不使用公开数据补造内部事实。
2. 计算每份实际材料的 SHA-256，构造下述统一 JSON。原材料在指定 `--source-root` 内，文件路径必须为相对路径和普通文件；来源根目录本身、其祖先和文件路径均不得经过符号链接，不允许 `..`。先检查字面路径再解析真实路径。哈希绑定的是文件字节，不证明输入确实来自所标页码；这些检查不等于操作系统隔离，也不防御同账户并发恶意替换文件。
3. 在 Skill 目录执行以下命令，输出必须是新目录。脚本校验来源及输入关系后，执行所需的一条或两条分析，生成计算结果、公式工作簿、计算报告、原材料副本和清单。失败保留不完整目录，不重用旧文件冒充成功。
4. `verify` 重新核对清单、脚本版本、材料副本，重跑统一输入，逐项比对结果、报告和工作簿。最后审查语义抽取和用户指定的交付要求，再用宿主实际挂载相关文件。

```bash
python3 scripts/fixed_income_workflow.py run task-input.json \
  --source-root /absolute/task/materials --out-dir /absolute/task/new-calculation-run
python3 scripts/fixed_income_workflow.py verify /absolute/task/new-calculation-run
```

退出码 2 表示未通过，不得作零值或已完成。两个分析为独立研究视图，不会自动共享账户余额或把产品可行域当作偿债资金分配；同一现金跨两个视图不得再汇总抵扣。

## 统一输入

所有字段名严格校验，拼错/多余字段拒绝；JSON 读取阶段拒绝重复字段，含嵌套和转义后同名，不静默覆盖。金额、利率和年基数建议用十进制字符串，利率为小数；JSON 小数输入在首次计算前统一保存为精确字符串，确保工作簿与回放输入一致。`null` 表示未知，不能补零。日历、币种换算、税费、份额粒度和利息口径不自动推断。日期使用 `YYYY-MM-DD`，须先统一业务时区。

顶层必填：

- `version`：固定为 `fixed-income-workflow-v1`。
- `as_of`、`cutoff`：研究日及明确的 `end_of_day`。需要精确日内截止时改用另一个可表达该口径的模型，不把本工作流日期结果描述为日内认证。剩余付款严格在截点后；逾期项目需另行勾稽。
- `meta`：`scope`、`currency`、`unit`。各笔数据必须完全一致；标准化须有材料依据，不能只改标签。
- `sources`：非空数组，每项 `id`、`path`、`sha256`，登记实际获授权材料，同一规范路径只登记一次。题面自含数据时可保存原题面为来源，不因此要求额外附件。`evidence` 也至少有一项，用不同 locator 引用同一来源即可。
- `evidence`：数组，每项 `id`、`source_id`、`locator`、`known_at`、`effective_at`、`status`、`kind`、`note`。`source_id` 关联原材料，`locator` 定位原文。`status` 为 `effective/draft/revoked/unknown`；`kind` 为 `fact/assumption`，假设必须有非空 `note`。缺失、未生效或截点后证据不晋升为截点事实。同日精确时刻与日期截点无法安全比较时保留未知。
- `debt_analysis`、`cash_analysis`：不用的填 `null`，至少一项非空。

各对象的 `evidence_id` 引用上述登记项，不能只填写一段无法关联的来源文字。有效文件的未来付款日不等于文件未来才生效。

可选 `report_metadata` 支持 `business_timezone`、`material_classification`，每项为 `{value, evidence_id}`。从本次材料提取非空文本及登记证据；未提供的项可省略，未知值或证据 ID 为 null，不补时区或材料性质。结果保留 `supplied_value/evidence_id/evidence_status`，只有合格事实证据才给确认 `value`，否则为 null、`status=unknown`。确认值进入报告页首，全量状态进入报告及工作簿字段追踪；缺少元数据不普遍阻断其他独立计算。该绑定不证明语义抽取正确，也不执行时区转换。

所有已填非 null 数值和日期先检查格式和范围，再应用证据资格；草稿、未选中记录或兄弟字段缺失不能掩盖负本金、非法数字、日期或非正年基数。日期的 null 表示未知，空字符串、数字及错误日期不是未知而是非法输入。合法的 null/不合格证据仍为未知；允许有符号利率的模型不因此禁止负利率。

## 偿债与融资分析

`debt_analysis` 必填 `ledger_complete`、`window`、`reported`、`debts`、`opening_funds`、`facilities`、`scenarios`。

`ledger_complete` 为材料是否证明台账完整的布尔值，不能为了求总缺口设成 true；同时提供 `ledger_complete_evidence_id`，引用证明完整性的登记证据。`window` 包含 `start/end/include_start/include_end`。`reported` 不勾稽时为 null；否则包含 `as_of/meta/window/basis/amount/evidence_id`，以登记证据绑定报表金额及口径，只比较 `legal_principal`，不把账面负债等同未来到期本金。完整工作流使用证据 ID，单项检查使用展开的 `evidence`，两者不要同时填写；工作流会将实际登记的证据传给单项核验器。

上述两项证据 ID 为兼容旧输入允许缺省，但缺省不代表通过：缺少完整性证据时不输出完整需求或完整缺口，缺少报表证据时不算确定勾稽差额。截点后、失效或假设证据也不能建立这两项事实；打开情景假设开关不改变此边界。登记外的 ID 直接拒绝。结果保留证据状态、所用 ID 及未知原因，不抹去已有证据支持的本金小计。ID 和文件哈希不能替代对原文是否实际支持该断言的语义核对。

### 债务、互斥计划与利息

`debts` 每项：

- `id`、`obligor`、`meta`、`principal`、`evidence_id`。
- `origin`：`opening` 表示截点剩余债务；`draw` 表示情景新提款生成的债务，不进入原法定到期台账。
- `legal_plan`：指定法定计划 ID；`plans`：候选偿还计划数组。

每套 plan 必填 `id/kind/evidence_id/principal_payments/interest_periods/interest_schedule_complete`。`kind` 为 `legal/put`，`interest_schedule_complete` 为布尔值。每套计划的分期本金总和必须等于该债务剩余本金，已知金额不得超额。部分回售计划应同时列回售部分和其余本金后续偿还，不另叠加整笔到期本金。每个情景每笔债务只能选择一套计划。

全部登记计划（含未选、未提款新债的备选）都检查字段、证据引用、日期格式、用途、利息区间和历史计提结构；原始已知本金分项不得超过已知本金，全部分项已知时必须守恒，不因证据掩码而跳过。未选方案不参与现金流计算；截点以后、提款起日等激活业务校验仅适用于合格的选中路径，不能把所有备选同时当成生效义务。

事实完整性另用两个可选 ID 绑定：`principal_schedule_complete_evidence_id` 证明该计划的本金表完整，`interest_schedule_complete_evidence_id` 证明剩余利息表完整。为兼容旧输入允许缺省，但缺省、假设、失效或截点后证据均不算事实完整；登记外 ID 拒绝。利息表为空也须有“无剩余利息”的事实依据，不能由空数组或 true 布尔值推断。即使这两项完整性证明有效，债务、所选计划、逐笔本金、利息及历史计提桥接中的假设或未知也不能被洗成事实。

`principal_payments` 每项：`id/due/amount/evidence_id`，以及逐笔 `purpose`。法定计划可省略 purpose，表示 `principal`，不得标成 `put`；回售计划的每笔 purpose 必填，回售部分为 `put`，剩余普通到期部分为 `principal`。不根据计划名或记录 ID 推断用途；专户按该逐笔用途匹配。日期或金额未知可为 null，明细保留未知，不计作已覆盖且不输出完整缺口。经济上同一本金不能拆成不同债务 ID 重复登记；脚本只能验证登记关系，语义去重仍需核对原文。

付款的准入同时依赖债务、所选计划、提款激活及逐笔证据。任一不合格时 `due/amount` 均为 null，保留 `evidence_id/evidence_status` 及原输入，不用草稿或截点后证据中的日期驱动事件、资金失效或负债结转。有效且明确允许的假设可进入标注的情景，但不能因此取得事实完整性。格式与内部区间关系始终校验；截点与起债日的业务校验只作用于准入路径。

`interest_periods` 每项必填：

- `id/due/start/end/annual_rate/year_days/paid_amount/evidence_id`。区间为 `[start,end)`，`due` 不早于区间结束。采用按剩余本金计算的实际天数单利；本金支付日开始按新余额计息，若合同不同不得套用。不允许区间重叠。利率、年基数或已付金额缺失可为 null。
- `paid_amount` 仅为截至研究截点已向债权人支付的非负利息金额，不包含将来支付额或收到的利息抵扣。不得超过历史计提的正向部分；纯未来区间必须为零。
- 可选 `accrued_before_start`：存量债务区间起日早于或等于研究截点、且包含截点之后计息日时，必需有 `{amount,through,evidence_id}` 桥接。`through` 与日终研究截点一致，`amount` 为计至该日（含当日）且尚未扣除已付部分的有符号累计计息金额。未来从截点次日与区间起日的较晚者开始，按分期偿还日切段；历史和未来不重叠、不漏日。最终剩余应付为历史计提加未来计提减截点已付。历史不足时保留可算未来分段，但完整剩余利息未知，不推测过去本金。区间结束不晚于截点次日属于全部历史计息，须另用支持该模型的入口。
- 新提款按提款日与区间起日的较晚者起算，提款当日属于未来本金路径，不能套用存量债务的次日规则。合格路径的区间不得早于提款，也不接受截点历史计提。日期语法仍对全部记录校验，起算与桥接的业务检查仅激活于合格选中路径。

利率和历史计提可有符号。`calculation.accrued/remaining` 保留带符号计算；付款 `amount=max(remaining,0)` 只表示借款人正向支出，`interest_credit=max(-remaining,0)` 单列负向利息余额。未知时两者均为 null。抵扣额不自动成为现金流入、不抵消本金，也不进入资金匹配的负容量；实际收款或合同允许的净额结算须先按原文归一，并以独立证据登记，不能把已收款填成负 `paid_amount`。

利息依赖 `[start,end)` 内的本金路径，不依赖未来全部付款已知。金额未知但付款日不早于 end 的分期，不影响该期计提；更早的未知本金或可能非零但日期未知的付款，阻断受影响计提。金额明确为零的未知日期不改变余额，但仍不能据此宣布全表完整。保留已知早期分段及其他独立债务，不从本金守恒反推未提供的金额。

每段从该段起日（含当日）核对本金依赖，输出 `status=computed/unknown` 及 `missing_dependencies`，未知本金或利息为 null。历史、利率、年基数或已付金额的缺失分别传播，不抹去不依赖它的本金或利息分段。`known_future_accrual` 仅合计可算未来段，没有可算段则为 null；`future_accrued` 必须全部未来段可算才有值；`accrued` 还需历史计提，`remaining` 还需截点已付金额。整期 `calculation.status=partial` 不等于全部不可算；缺必要项时票息付款、抵扣和完整需求缺口仍为 null。部分小计不是完整票息、下限或可直接用于资金匹配的数值。

全部历史计息但未来才支付、复利、浮动重设、罚息、税务或不规则权利金不属于此模型，不伪装为一个常数利率。每笔利息是否实际完整、同笔票息是否拆重，需要抽取阶段对照合同。

### 资金、授信与情景

`opening_funds` 每项必填：

- `id/balance_id/owner/meta/amount/evidence_id`；同一经济余额的 `balance_id` 不能重复。一般资金先剔除另列专户，不用不同名字掩盖重复。
- 证据准入后，`balance_at` 必须等于 as_of，`available_from` 不晚于截点；已填的矛盾日期须纠正，null 则保留未知并排除资金。旧余额不能只因文件新而滚成当前余额。
- `expires_on`：最后可用日；null **仅表示材料确认没有到期限制**，不是未知。限制未知时令 status=unknown。合格证据支持的末日早于截点时，在日期排除原因中记录 `expired_at_cutoff`，金额为 null，不计为当前资金；只有这一原因时摘要资格也为该状态。末日等于截点时该日仍可用，后续事件从次日扣除未使用额。证据不合格时不以该日期断言资金已过期。
- `status`：`confirmed/conditional/planned/unknown`。`restriction`：`unrestricted/dedicated/unknown`。
- `debt_ids/purposes`：非空文本元素组成且无重复项的数组。unrestricted 时都为空；dedicated 时两数组均非空；用途只接受 `principal/put/interest`。所有已填 debt_ids 必须属于统一输入的 `debts` 登记，不默认可用于其他偿债主体或用途。

`facilities` 每项：`id/owner/meta/undrawn_limit/available_from/expires_on/status/evidence_id/restriction/debt_ids/purposes`。`undrawn_limit` 为截至截点尚未使用部分，不能再加已提款金额；提款累计不可超限，偿还后不自动恢复循环额度。不是全部授信额度都可计为确认来源。

期初资金、各情景流入、全部授信（含未提款、条件未满足的授信）及提款衍生资金使用相同的限制校验。用途拼错、未登记债务或重复限制项均在匹配前拒绝；不能把输入错误误报为资金缺口。校验使用全部 `debts`，不从当前付款表推断登记；已登记但当前无付款或未提款的债务可以被合法专户引用，未匹配金额保留为未使用。`restriction=unknown` 不提供确认覆盖，但已填写的数组仍须合法；不得把未知当作无限制。

`scenarios` 每项：

- `id/note/allow_assumptions`：必须解释情景；是否允许显式假设为布尔值。打开开关不会把 conditional 的事实记录自动变成 confirmed。假设须单独有 kind=assumption 的证据记录，结果保留其身份。
- `plans`：对象 `{debt_id: plan_id}`，必须覆盖全部 opening 债务和本情景已选择提款的新债，不接受数组/重复备选。
- `inflows`：资金数组，字段同 opening_funds，但无 `balance_at`。证据准入后 `available_from` 必须在截点后；未知起日不能参与计算。不把未经授权预测写成已知事实。
- `draws`：数组，每项 `id/facility_id/debt_id/date/amount/evidence_id`。绑定已登记授信和 origin=draw 的新债；提款额必须等于该新债本金，主体一致且在授信有效期内。一笔新债只绑定一次提款。

提款先校验结构、日期格式、登记关系、金额和主体一致性，再以授信状态、授信证据、提款证据和新债证据共同决定能否进入数值情景。只有合格事实路径或本情景允许的有效显式假设才检查截点、授信有效期并占用累计额度。证据不合格的提款不会抢占其他合格提款的额度，也不会因业务日期超出授信期而中止其他独立路径；结构错误和未登记引用仍拒绝。结果 `facility_usage` 仅记录准入情景提款占用，包含假设时不得描述为实际已用额度。

未确认、截点后或失效证据不能只从现金端剔除而仍生成确定负债：对应提款日期/金额、后续本金、利息、付款日期及负债路径均保留 null，完整需求缺口也保持未知，其他有证据的债务仍计算。已选择但证据不合格的新债仍须选择一套计划，不可静默删除。结果 `draws` 保留各环节证据 ID、情景和事实资格状态；允许且有效的显式假设可计算，但标为 `assumed`，不称实际提款或实际余额。

### 资格留痕

资金及提款结果的 `admission` 分开保留 `evidence_reasons`、`business_reasons`、`missing_reasons`、`temporal_reasons`，并在 `ineligibility_reasons` 合并去重。`evidence_status` 只摘要证据资格；`eligibility_status` 依上述类别顺序取第一个原因，没有原因才为 eligible。摘要是兼容读取入口，不代替完整原因列表，原因顺序也不是风险等级。

业务原因只说明输入申报状态或依赖路径不满足准入，不认证该状态的真实性。只有证据准入、且提款激活路径合格时，才用业务日期进行时点分类；否则 `temporal_status=not_evaluated`，不是“日期已通过”。空字段仍单独记录缺失，非法非空日期/数值和逆序日期区间仍在准入前拒绝。不同证据障碍可并存，假设身份不能覆盖草稿、晚到或缺时间的原因；允许假设也只接纳本身有效的假设证据。

原始资金日期保存在 `supplied_dates`，不合格证据/激活路径的计算日期为 null；提款原始日为 `supplied_date`。提款的 `evidence_status` 与 `factual_evidence_status` 保留授信、提款、新债各自证据摘要，另用 `admission/factual_admission` 表示完整路径，授信业务状态不能覆盖证据状态。提款衍生资金继承上游原因及类别，不把依赖证据失败改写成业务状态，也不把自身证据合格当作整条路径合格。这些诊断随结果、报告与工作簿回放；原始输入和来源副本仍保留，不将排除理解为资金不存在或已发生违约。

匹配按主体、有效日期、债务和用途构图，余额全期间只消耗一次；先保障较早日期可覆盖总额，再通过剩余网络重排资金，避免简单贪心浪费专户。该分配是条件性研究方案，不是实际支付或业务优先级指令。

输出法定窗口明细、情景选择、逐笔本息及计算分段、分配记录、逐日现金、负债结转和未知项。未覆盖到期款保留为未覆盖，不自动用更晚现金消除。`full_schedule_gap_against_supplied_eligible_sources` 仅在需求完整时返回，且始终只针对所供合格来源；它不是未来全部融资后的最终缺口。内部调拨和循环授信恢复需要独立勾稽模型，不在这里虚构。

两套完整性含义不可互换：

- `plan_completeness` 分别保留模型的 `principal_schedule_complete/scenario_schedule_complete`，以及事实的 `factual_principal_schedule_complete/factual_interest_schedule_complete`、证明 ID、明细依赖和 `factual_unknowns`。法定本金窗口只依赖事实本金完整性，缺利息证明不抹去已核对的本金勾稽。
- `scenario_payment_schedule_complete` 和 `selected_schedule_gap_against_supplied_eligible_sources` 只回答所选登记债务计划是否可算及其条件性缺口，不证明台账完整。`scenario_status=computed` 仍可能伴随主 `status=partial`。
- `payment_schedule_complete` 和完整需求缺口必须同时具备事实台账完整、事实本金完整和事实利息完整。允许情景假设不能放宽这三道门。`funding_basis` 另标所供资金是否含显式假设，即使需求已证明完整也不能将假设资金覆盖说成确认融资。

`cashflow` 的 `covered/cumulative_uncovered` 是给定合格来源的条件性分配和累计未覆盖额，不代表实际已付或拖欠。`liabilities` 则是选定计划如期履行时的本金路径：`closing=opening+draw-principal_scheduled`，与利息分段使用同一计划，不按 funded/covered 金额另滚一条相矛盾的负债路径。仅从未知本金可能影响的日期起保留余额未知，不抹去更早的已知余额；合格新债在提款发生前仍为零。`actual_payment_status=unknown`、`actual_closing=null` 保留；实际履约、实际期末余额及违约判断须另有执行证据，不能由所供资金不足推定。两种视图不得混作已实现现金流。

## 现金产品与提款可行域

`cash_analysis` 必填：

- `capital/capital_evidence_id/investment_date`：初始可取现金及其来源，投资日严格晚于截点。
- `allow_assumptions`：是否允许有标记的假设，布尔值。
- `products`：下述产品数组。
- `withdrawals`：每项 `id/date/amount/evidence_id`，已知日期不早于投资日。日期 null 时按 `withdrawals/<id>/date` 记录 `unknown_withdrawal_date`，现金可行性为 `unknown_inputs`，不编造提款时间线；独立偿债结果继续返回。金额、证据引用、其他提款和给定份额仍全部校验，非空错误日期、负金额或未登记证据不能因已有缺失而被吞掉。投资日起点不是可缺省的提款日期，仍须明确。
- `proposed_lots`：null 或完整的 `{product_id: 整数份额}`。用它检查用户给定分配，不能仅提交一部分产品。
- `search_limit`：明确整数，最多 100000 个分配组合。该限制只保护本地穷举计算；超过时报告未穷尽，不宣称无解。给定分配仍可单独核验。

每个 product 必填：

- `id/meta/evidence_id/lot_size/min_lots/max_lots`。lot_size 为每份本金；投入非零时遵守正整数 min_lots 和 max_lots；零投入始终允许。
- `annual_rate/rate_kind/interest_days/year_days`。只支持单次购买的单利，年利率为小数，rate_kind=gross/net。
- `fee_rate/fixed_fee/minimum_fee/fee_timing`。非零投入费用为 `max(本金×比例+固定费,最低费用)`，零投入费用为零。fee_timing=upfront 时投资时扣；redemption 时在本金可取日扣。净报价不得重复加费用；分期费或不同收费基数需另建模型。
- `principal_available/interest_available`：本金和报价收益分别实际可取的日期，不是交易可用日；未确认填 null。同日按日终可取净额核对提款，不认证日内顺序。

计算同时检查投资后可用现金和每个后续事件日，不只看终值；不足时保留具体日期与 shortfall。穷尽得到 `feasible_lot_bounds`、可行数及一个见证分配，后者不是收益最优或交易建议。未知参数返回 `unknown_inputs`；超出组合上限返回 `not_exhausted_safety_limit`；搜索阶段工作预算不足返回 `not_exhausted_work_limit`。只有完全枚举且无解才是 `exhausted_infeasible`。未穷尽时总可行数和全域边界保持 null；`evaluated_allocations/observed_feasible_count/witness` 仅描述已检查部分，不能冒充全域结论。已完成的 `proposed` 检查仍保留。

搜索空间乘积采用上限截断，不构造超大精确整数。上限内 `search_space_size_exact=true`、`search_space_size` 为精确数量；超过时精确数量为 null、exact=false，仅保留有界的 `search_space_lower_bound`。输入缺失或计算提前停止也不得将未知空间大小填零。

## 本地资源边界

以下是本地解析、复制和计算的支持范围，不是业务额度、风险阈值或输入默认值。运行前先预检，流式读取和复制期间继续计数；文件增长、哈希变化或超限均不能取得已验证结果。

- 输入 JSON 最多 8 MiB；结构最多 20000 个节点，嵌套最多 32 层，每个数组或对象最多 512 项，单字符串最多 65536 字符，全部字符串合计最多 8 MiB。数值字段最多 28 位十进制系数数字、指数绝对值 28；数字文本最多 128 字符，整数最多 28 位。JSON 小数和整数在解析阶段即检查；字符串数值在消费字段时检查，直接计算入口同样检查，避免短科学计数法展开或超长整数转换消耗过量资源。拒绝 NaN/Infinity 和以布尔值充当金额，超深 JSON 直接返回不支持。这些共同保护也适用于单项计算，不只保护完整流程。
- 来源最多 64 份，每份最多 32 MiB，合计最多 128 MiB；相对来源路径最多 16 段、1024 个 UTF-8 字节。先检查全部文件数量和大小，再读取内容；哈希和复制分别使用共享总字节计数，不能逐文件重置。
- 偿债情景最多 16 个，每情景登记资金和付款分别最多 512 笔，包括证据不足的登记项；合格资金与付款的候选配对最多 50000 对。构图前检查配对数量。全计划校验、图遍历、计划编译及现金产品/提款校验、域构造、每次分配和事件计算共用每次计算 2000000 个工作单位；事件排序和展开采用保守预扣。工作单位是内部计算计数，不等于秒数或可承诺的运行时长。
- 每情景现金流与负债展开最多 4096 行；先检查主体、计划和事件的乘积，再展开。报告、清单和回放核验单文件最多 32 MiB，JSON 回放文件仍为 8 MiB；JSON 序列化和报告组装逐段计数，不先拼接无限输出再检查。全部产物合计最多 256 MiB，目录项最多 2048 个、目录深度最多 18 层。工作簿仍受其独立解析限制约束。

必要解析或计算超限以 `unsupported_size_or_work` 和退出码 2 停止；可选的现金穷举阶段则保留已核验部分并明确未穷尽，不能声称“无解”“零缺口”或全域完成。失败期间产生的文件仅是不完整残留，不是验证证据；不要删掉未知或专户、拆开会重复消耗同一余额的付款表来绕过边界。若任务超过此模型支持范围，应说明具体限制，改用另经授权、能保持全局守恒和证据关系的计算方案。

## 产物、精度和验证范围

- `input.json`：统一输入；`sources/`：实际材料副本，遵循原隐私边界，不对外上传。
- `result.json`：完整精确结果、明细、来源、假设、未知及限制。单利商保留 50 位有效精度，汇总/匹配使用更宽的 Decimal 上下文防止尾差假缺口；这不是合同舍入规则。需要支付级分位舍入时先明确规则，不能把研究小数称为实际结算额。
- `calculations.xlsx`：输入与结果逐字段表、适用的现金流与利息分段公式表。先以未转换原值复核模型恒等式（单利 50 位、现金 512 位 Decimal 上下文），不相等即拒绝导出；再将表格数值舍入为 15 位有效数。每行分列模型结果 `Model`、由显示输入复算的 `Projected` 及 `Projected minus model` 差额；差额比较两个显示值，精确小数仍以 JSON 为准，不把差额称为模型错误或忽略实际模型错误。每行是原模型的显示投影，不用显示尾差逐行替代模型余额；该差额也不代表合同结算舍入。未知利息段显示状态与依赖，不写伪零或公式；整期状态和部分小计另在 Result 表保留。
- 支持的工作簿公式按 15 位输入/常量、50 位中间运算、最终 15 位结果计算，与未经舍入的原始缓存作十进制数值精确比较，不用勾稽容差放过缓存偏差。独立文件中超过该精度且舍入会改变数值的非公式输入单元格拒绝；等值尾零可接受。该有限算术模型不声称与 Excel 计算引擎完全等价。不支持的 Excel 功能拒绝核验，不静默移除后声明原文件已通过。`formula_cells_checked` 记录检查到的公式数；只有公式数大于零且核验无错误或警告时，`recalculated` 才为 true。
- `report.md`：计算字段及结果来源索引，不自动替代投资研究报告或用户指定的单张主表。来源文字、字段路径和数值均在代码跨度中展示，HTML、链接和图片语法不作为可执行内容；竖线和换行采用可见显示转义，原始精确字符串以 `result.json` 为准。还需将研究结论、条款解释和用户要求的表式/附录完成，并核对其引用。
- `manifest.json`：实际产物大小与 SHA-256、脚本版本绑定。`verify` 检查文件集合和字节，重算结果，重建报告和工作簿期望值，再比较实际文件。

`locally_reconciled` 只认证这套有限模型与留存输入一致；`semantic_source_mapping_verified=false`、`host_delivery_confirmed=false` 必须保留。不把哈希、防篡改复核、预审或本地测试当作原材料真实性认证、效果胜率或用户收件证明。用户需要其他表式或复杂文件时用获授权宿主能力完成，并另留实际核验证据。

工作簿生成、回读、空行和公式引用都使用同一坐标及元数据校验；中文表名可用，越界坐标、非法/重名表名及非法/重复数值工作表编号拒绝。支持范围见 [实际工作簿与交付检查](calculation-contracts.md#实际工作簿与交付检查)。结构通过、公式复算、财务内容勾稽和宿主实际交付仍是不同结论，不能相互替代。

生成、回读和私有目录创建在解析真实路径前检查字面路径及全部已存在祖先，拒绝 `..`、符号链接和非目录父节点。新产物目录及新增父目录使用 POSIX `0700`，新文件（含来源副本和工作簿）使用 `0600`；不覆盖已有文件，不改变原始材料或已有父目录权限。`verify` 同时检查产物权限，权限扩大、符号链接或非普通文件不能取得验证通过。不支持 POSIX 权限的环境停止本入口，改用具备明确保护的获授权宿主能力。此措施不是加密、ACL 审计或完整主机隔离，不消除同账户恶意并发替换的竞态，也不阻止管理员或获授权宿主访问；实际分享文件仍遵守材料授权。
