# `industry_workflow.py` 输入输出契约

仅在任务需要重复情景经济性、项目样本状态汇总、系统到设备构成桥接、数值门槛、源单位换算、事实主张核对、回收阈值反解、多期路径或显式请求项覆盖时读取。各分支独立；局部定义和定性问题不建立全套工作流。脚本只验证结构、声明口径和算术，不验证来源真实性或业务语义。

## 调用与根对象

```bash
python3 scripts/industry_workflow.py INPUT.json
python3 scripts/industry_workflow.py -
```

脚本仅使用标准库，读取一个 JSON 文件或标准输入，只向标准输出写 JSON，不写文件、不联网、不执行动态代码或子进程。结构错误输出 `{"error":{"message":"..."}}` 并返回 2；意外 I/O 或实现错误返回其他非零值。经济缺失、冲突、不兼容或不可行是状态结果，返回 0。

根对象精确包含 `version`、`as_of`、`facts`、`jobs`、`obligations`。`version` 为 `"1"`；`as_of` 为 `null` 或带 UTC 偏移的 ISO-8601 时间。事实精确包含 `value`、`unit`、`basis`、`source`、`evidence`、`known_at`：值为有限数或 `null`，三个文本字段非空，证据为 `fact|forecast|assumption`，首次可知时间为 `null` 或偏移时间。

根 `as_of` 非空时，空值、未知首次可知时间或晚于截止时点都使依赖输出缺失；等于截止时点可用。ID 只允许 ASCII 字母、数字、下划线和连字符。重复 JSON 键或命名空间 ID、未知字段、布尔数值、非有限数、错误时间、未知引用或跨任务结果引用均为结构错误。有限 JSON 词法中的指数溢出、非零下溢以及超过运行时整数词法转换限制的整数不是结构错误；解析器保留该词法并让对应事实及其依赖结果返回 `conflict/null`。显式 `NaN`、`Infinity`、`-Infinity` 和布尔数值仍为结构错误。

成功输出精确包含 `version`、`results`、`coverage`。每条结果精确包含 `value`、`status`、`reason`、`dependencies`、`evidence`、`unit`、`basis`、`raw_value`。状态为 `calculated|missing|conflict|incompatible|infeasible`；多因优先级依次为冲突、不兼容、缺失、不可行，原因保留所有重要限制。有限但超出脚本数值表示范围的输入，或派生出不可表示数值时，返回 `conflict/null`，不得返回实现级错误。部分信息使用单独的 `known_subtotal`，不替代完整总额，并保留部分范围及排除项说明。

义务精确包含 `id`、`result_id`、`reason`，后二者恰有一个非空。有效结果为已计算时覆盖为 `answered`，否则为 `limited`；原因义务直接为 `limited`。这只核对已声明请求项，不能发现模型没有声明的遗漏。

## `economics`

输入精确包含 `currency`、`basis`、`rows`。行精确包含 `id`、`scenario`、`period`、`values`、`capex`，情景期间组合唯一。`values` 精确包含：

`units, period_units, utilization, unit_price, variable_cost, fee_rate, fixed_cost, target_years, utilization_min, utilization_max, price_index`

全部为事实 ID。单位依次为 `unit`、`period_per_year`、`ratio`、`<currency>/activity`、`<currency>/activity`、`ratio`、`<currency>/year`、`year`、`ratio`、`ratio`、`ratio`；基础等于任务基础。资本开支组件精确包含 `id`、`amount`、`subsidy_rate`，单位为币种和比例。空数组明确表示无资本开支；未知组件不能省略。

令字段为 `U,P,u,p,v,f,F,T,umin,umax,D`：

- `activity=U*P*u`
- `gross_flow=activity*p`
- `fee=gross_flow*f`
- `variable_cost_total=activity*v`
- `net_flow=gross_flow-fee-variable_cost_total-F`
- `net_capex=sum(amount_i*(1-subsidy_rate_i))`
- `payback_years=net_capex/net_flow`，仅当净流量为正
- `constant_gross_flow=gross_flow/D`
- `constant_net_flow=net_flow/D`
- `contribution_at_full_utilization=U*P*(p*(1-f)-v)`
- `required_utilization=(net_capex/T+F)/contribution_at_full_utilization`

反向利用率仅在贡献为正时计算，检查 `[umin,umax]` 和 `[0,1]`，越界时保留有限 `raw_value`。同一前向方程必须能回算目标净流量。每行还生成只含合格已知组件的 `net_capex_known_subtotal`。缺失资本开支不阻断运营流，缺失目标不阻断观察净流量，缺失指数只阻断不变价结果。

## `projects`

输入精确包含 `mode`、`cutoff`、`unit`、`basis`、`states`、`records`。历史模式要求截止时间等于根 `as_of`；快照模式要求截止为空。状态精确包含 `id`、`prospective`、`weight`。非前瞻状态权重必须为空；前瞻权重为 `[0,1]` 的独立概率，不要求加总为一。

记录精确包含 `id`、`project_id`、`state`、`effective_at`、`known_at`、`revision`、`quantity`、`capacity_check`。历史模式以首次可知时间不晚于截止为信息可得边界：非前瞻状态还要求生效时间不晚于截止；前瞻管线或未来状态允许纳入“截止时已知、未来生效”的记录。再按最大生效时间、最大首次可知时间、最大非负修订号在合格记录中选择。相同等级只合并完全相同的状态、数量引用和容量校验，其他情况为冲突；冲突结果必须保留全部竞争数量及相关状态权重依赖。快照要求两个时间为空、修订为零，同一项目只能有一个去重后的语义载荷。

容量校验精确包含 `power`、`duration`、`reported`、`power_unit`、`duration_unit`、`capacity_unit`、`factor`。换算因子为正比例，必须显式给出桥接单位 `<capacity_unit>/(<power_unit>*<duration_unit>)`，例如 `MWh/(MW*h)`；脚本不替用户猜测物理量纲。`derived=power*duration*factor`，`residual=reported-derived`。它不改写项目数量。

每状态生成 `total`、`known_subtotal`，只描述合格样本。冲突或不可用项目从部分小计排除并说明。跨状态同 rank 冲突会同时标记涉及的状态；各冲突状态的 `total` 都保留该项目全部竞争载荷，不能只携带本状态记录。`pipeline=sum(前瞻项目数量*状态概率)`；已实现状态不进入正常加权项，空前瞻管线为零。若同 rank 冲突涉及任一前瞻状态，管线返回 `conflict`，但依赖列表保留已选未来项、全部竞争数量（包括竞争的已实现载荷）及相关前瞻状态权重，避免丢失可追溯性。任何派生求和或乘积溢出均为 `conflict/null`，不得向用户输出无穷值或返回实现级错误。容量记录另生成 `derived_capacity`、`reported_capacity`、`capacity_residual`。

## `investment`

输入精确包含 `currency`、`basis`、`groups`、`mix`。组精确包含 `id`、`total`、`components`；组件精确包含 `id`、`share`、`equipment`、`accessible`。份额和可获得比例均为 `[0,1]` 比例。组件须代表互不重叠的完整系统支出总体；已知份额在绝对容差 `1e-6` 内加总为一，不归一化。

每组生成 `equipment=total*设备份额和`、`accessible=total*sum(设备份额*可获得比例)` 和部分 `equipment_known_subtotal`。非设备组件的可获得比例不影响设备可获得结果。可获得支出不是收入或利润。

`mix` 为 `null` 或精确包含聚合 `total` 和按组唯一完整覆盖的 `weights`。权重是系统支出份额，须在 `1e-6` 内加总为一。生成 `aggregate_equipment` 和 `aggregate_accessible`；没有组合时二者缺失，各组结果保留。聚合使用组构成比例，不依赖组自身总额；权重恰好为零的分组不参与聚合，其组总额或构成结果冲突不单独阻断其他权重分组，但全局权重、聚合总额和实际参与分组的冲突仍须阻断。

## `gates`

输入精确包含非空 `rows`；行精确包含 `id`、`start`、`gate`、`duration`。时长事实单位为 `day`、值非负；输出基础逐行继承。检查 `start+duration*24小时<=gate`，相等可行，晚于门槛不可行。它只验证时间顺序，不证明观察实际完成。

## `convert`

输入精确包含 `rows`、`ratios`；`rows` 非空，`ratios` 可为空数组。行精确包含 `id`、`source`、`declared_source_unit`、`canonical_unit`、`factor`。源和因子均为事实 ID。源值可为有限正数、负数或零；因子必须严格为正。因子单位为 `<canonical_unit>/<declared_source_unit>`；声明源单位含 `*` 或 `/` 时，分母加括号。

只有源事实单位与声明源单位完全一致时才允许换算；两者不同时，即使给了因子，`source_value` 和 `canonical` 也返回不兼容。脚本不识别“千、百万、亿”等规模词，模型必须先照抄源单元格单位，不能同时从事实单位和声明单位中丢掉同一规模词。源事实缺失会阻断源值和规范值；因子为空值只阻断 `canonical`，不阻断 `source_value`。

每行生成 `<job>.<row>.source_value` 和 `<job>.<row>.canonical`，后者为源值乘以因子，二者共享源事实基础。比率精确包含 `id`、`numerator_row`、`denominator_row`，只能引用本任务行。两个 canonical 均已计算、单位和基础相同且分母非零时，生成单位为 `ratio` 的 `.multiple`；单位或基础不同为不兼容，零分母为不可行。

## `claims`

输入精确包含非空 `rows`，只接受事实 ID，不读取其他作业的计算结果。方向行精确包含 `id`、`kind`、`series`、`claimed`；`kind` 为 `direction`，`series` 至少包含两个事实 ID，`claimed` 为 `all_nondecreasing` 或 `all_nonincreasing`。序列事实必须同单位、同基础；相等相邻值同时满足两种单调主张。后续下降推翻全增，后续上升推翻全降，结果为冲突。

处理行精确包含 `id`、`kind`、`recorded`、`asserted`、`residual`；`kind` 为 `treatment`，记录值和声称值为 `retain_residual|use_reported|use_derived`。`residual` 始终是事实 ID，其数值可以是有限数或 `null`；空残差本身不构成冲突。记录处理与声称处理不一致时为冲突。项目残差仍由 `projects` 作业管理，本作业不改写。

如果要核对的是工作流计算结果形成的序列，模型必须在答案中按结果 ID 逐项核对，不得把计算结果复制成 `facts`，也不得构造跨作业引用。

## `thresholds`

输入精确包含 `currency`、`basis`、非空 `rows`。行精确包含 `id`、`net_capex`、`period_units`、`benefit_per_unit`、`fixed_cost`、`target_years`、`observed_units`、`max_units`、`eligible_amount`、`ineligible_amount`、`observed_subsidy_rate`，全部为事实 ID。单位依次为币种、`period_per_year`、`<currency>/unit`、`<currency>/year`、`year`、`unit`、`unit`、币种、币种、`ratio`。

金额和单位数非负；期间、单位收益和目标年数在使用时必须严格为正；补贴率在 `[0,1]`。`max_units` 是显式空值事实时跳过单位上限；未知与显式零仍不同。

令 `C=net_capex`、`P=period_units`、`b=benefit_per_unit`、`F=fixed_cost`、`T=target_years`、`U=observed_units`、`M=max_units`、`E=eligible_amount`、`I=ineligible_amount`、`s0=observed_subsidy_rate`。当 C、E、I、s0 都可计算时，先在相对 `1e-12` 或绝对 `1e-9` 内核对 `C=E*(1-s0)+I`；不一致时，依赖资本身份的输出均为冲突。

每行生成：

- `observed_net_flow=U*P*b-F`，独立于资本身份；负流量是已计算损失。
- `payback_years=C/observed_net_flow`，仅在观察净流量为正且资本身份成立时计算。
- `required_units=(C/T+F)/(P*b)`，只反解单位数；超过 M 时为不可行并保留有限 `raw_value`，可行值必须回算满足 `U*P*b-F=C/T`。
- `required_subsidy_rate=1-((observed_net_flow*T-I)/E)`，只反解补贴率；结果超出 `[0,1]` 时为不可行并保留 `raw_value`，可行值必须回算满足资本恒等式。E 为零为不可行，E 缺失为缺失。

不支持反解其他变量；既有 `economics.required_utilization` 仍按原合同独立计算。

## `path`

输入精确包含 `unit`、`energy_unit`、`duration_unit`、`basis`、非空 `rows`。行精确包含 `id`、`period`、`opening`、`addition`、`retirement`、`duration`、`factor`。行 ID 和 period 唯一；`opening`、`addition`、`retirement` 为同单位、同基础的非负事实。`duration` 与 `factor` 必须同时为空或同时为事实 ID；因子单位为 `<energy_unit>/(<unit>*<duration_unit>)`。

每行透传 `opening`、`addition`、`retirement`，并在三者均可计算时生成 `closing=opening+addition-retirement`。closing 为负时不可行，`raw_value` 保留该有限负数，不标为 calculated。退休为空且期初、新增可计算时，完整 closing 为缺失，同时生成带部分范围说明的 `known_subtotal=opening+addition`；期初缺失时不得用新增减退休制造小计。显式零退休必须用值为 0 的事实，不等于未知退休。

时长和因子存在时，只转换新增流量，生成 `energy_addition=addition*duration*factor`。各期行互不引用；乱序输入不构成跨期引用。只给终点不能替代路径，模型答案仍须说明存量、新增、退役和期末之间的勾稽。

## 解释边界

模型负责从已授权材料提取需求、映射事实并判断公式适用性。执行后检查状态、依赖、证据、单位和基础，在正文和表格复用同一结果。标签相同不证明来源、总体或语义兼容；未知不得默认为零。零工具任务不加载本文件或执行脚本。
