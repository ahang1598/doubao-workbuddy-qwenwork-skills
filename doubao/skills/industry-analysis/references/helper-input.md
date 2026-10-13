# `industry_metrics.py` 输入输出契约

仅在增长、分项勾稽、利润池或库存流量计算会影响结论时使用 `scripts/industry_metrics.py`。脚本不是必经步骤，也不负责检索或验证来源。

## 调用与执行边界

调用方式仅有：

```bash
python3 scripts/industry_metrics.py INPUT.json
python3 scripts/industry_metrics.py -
```

第一种读取指定 JSON 文件，第二种从标准输入读取 JSON。脚本离线运行，仅使用 Python 标准库；除读取输入外不读其他材料，不写文件、不访问网络。成功时向标准输出写一行 JSON 并返回零；失败时向标准输出写 `{"error":{"message":"具体错误"}}` 结构并返回非零。

## 通用输入

顶层必须且只能包含 `operation`、`scope`、`inputs`。`scope` 必须且只能包含 `object`、`region`、`unit`、`basis`，四项均为非空字符串，描述调用者已经统一的对象、地区、单位及统计或会计基础。

脚本不会自动完成币种或单位转换、时间对齐、范围桥接和来源核验。调用前先验证 `scope` 与各输入来自同一可比口径。数值字段中的 `null` 表示未知；布尔值、非有限数、未知字段、重复 JSON 键、重复成员 ID 和空 ID 均被拒绝。成功输出必须且只能包含 `operation`、`scope`、`result`。任何无效输入、错误结果、溢出或非有限输出都不能支持业务结论。

## `growth`

`inputs` 必须且只能是 `start`、`end`、`years`：

- `start` 为大于零的有限数或 `null`。
- `end` 为非负有限数或 `null`。
- `years` 为大于零的有限数，表示实际经过的增长期数，而不是起止标签的包含式计数。

当两个端点均已知时：

- `growth_pct = (end / start - 1) * 100`
- `cagr_pct = ((end / start) ** (1 / years) - 1) * 100`
- `status = calculated`

任一端点为 `null` 时两个结果均为 `null`，`status = missing`。`end` 为零时，总增长率和 CAGR 均为 `-100`。输出百分数以百分比数值表示，不是比例。

## `reconcile`

`inputs` 必须且只能是 `total`、`components`。`total` 是非负有限数或 `null`；`components` 是非空数组，每项必须且只能包含非空唯一 `id` 和非负有限 `value` 或 `null`。

`result` 包含：

- `component_sum`：所有分项均已知时的和；任一未知则为 `null`。
- `delta_components_minus_total`：总额与分项和均已知时为分项和减总额，否则为 `null`。
- `coverage_ratio`：总额大于零且分项和已知时为分项和除以总额，否则为 `null`；该值是比例，不是百分数。
- `status`：差额可计算时为 `calculated`，否则为 `missing`。

非零残差不能直接解释为事实错误；先检查总体范围、类别是否完备、舍入和统计基础。部分分类本来就不一定加总至总体。

## `profit_pool`

`inputs` 必须且只能是 `before_period`、`after_period`、`before`、`after`。两个期间标签必须非空且不同。`before` 和 `after` 均为非空数组，每项必须且只能包含唯一非空 `id` 与有限有符号 `profit` 或 `null`；两期成员集合必须完全相同，并已统一范围、单位和会计基础。

`result` 包含 `before_total`、`after_total`、`rows`、`status`、`share_limit`。每个 `rows` 成员包含：

- `id`
- `profit_change`：两期成员利润均已知时为后期减前期；即使利润池总额因其他成员缺失而未知，该项仍可计算。
- `before_share`、`after_share`：对应期间总额为正且所需数值均已知时，成员利润除以该期总利润；输出为比例。
- `share_change_pp`：两期份额均已知时，以 `(after_share - before_share) * 100` 输出百分点变化。

任一期间总额因成员缺失而未知时 `status = missing`，否则为 `calculated`。某期总额非正或未知时，只将该期份额置为 `null`。成员利润允许为负，因此份额可能超出 `[0,1]`；不得把它解释为普通市场份额。`share_limit` 固定解释为：`Shares omitted when a period total is missing or nonpositive; signed components may yield shares outside [0,1].`

## `inventory`

`inputs` 必须且只能是 `opening`、`inflow`、`outflow`、`adjustments`。前三项是非负有限数或 `null`；`adjustments` 是有符号有限数或 `null`，该键必填且绝不能默认成零。所有流入流出必须使用相同期间和范围边界。

所有数值已知时，`closing = opening + inflow - outflow + adjustments`。任一值未知时 `closing = null` 且 `status = missing`。若计算结果为负，脚本保留该值并返回 `status = inconsistent_flow`，不截断为零，也不将其解释为真实负实物库存；应回查边界、期间、符号和漏项。其他非负结果返回 `status = calculated`。

## 使用顺序与解释

1. 根据研究问题准备并人工核对已经统一口径的输入。
2. 仅在允许使用工具时执行一次调用。
3. 先检查退出状态、顶层结构、`error`、`result.status`、单位和异常值。
4. 再把结果解释为支持某个明确主张的计算，不让计算替代来源和因果判断。

用户明确要求零工具时，不加载本文件、不执行脚本。只可用对话内已给数据展示透明的简单公式；无法可靠完成的计算保持未知，并明确未执行或验证脚本。
