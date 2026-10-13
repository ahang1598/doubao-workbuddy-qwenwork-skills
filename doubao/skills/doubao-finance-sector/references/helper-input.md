# `sector_metrics.py` 契约

仅在问题确实需要可比区间收益、基准相对收益或涨跌家数比例时使用。它不是热度、阶段或资金分类器，也不验证来源、成员、基准、日历或因果。

```text
python3 scripts/sector_metrics.py INPUT.json
python3 scripts/sector_metrics.py -
```

程序只读输入并向标准输出写 JSON，不联网、不写文件。输入结构见 [sector-metrics-input.schema.json](sector-metrics-input.schema.json)。

根对象含带时区的 `as_of` 和 `rows`。每行必须有唯一非空 `id`，非空 `market`、`taxonomy`、`basis`、`state`，以及带时区的 `start`、`end`、`available_at`，并满足 `start < end`。

可选 `quote`、`benchmark` 缺失或为 `null` 时对应指标为 `null`；存在时含正且有限的 `start`、`end`。可选 `breadth` 含非负整数 `up`、`down`、`unchanged` 和正整数 `total`，且三项之和等于 `total`。所有行都要通过验证，包括未来排除行。

成功输出恰好为 `{as_of,rows,comparison_groups}`。输出行恰好含 `id`、`eligible`、`reasons`、`return_pct`、`benchmark_return_pct`、`relative_pp`、`up_share`、`down_share`。资格要求 `end <= as_of` 且 `available_at <= as_of`；原因顺序固定为 `end_after_as_of`、`available_at_after_as_of`。排除行五个指标均为 `null`。

公式：

- `return_pct = (end / start - 1) * 100`
- `benchmark_return_pct` 使用同式。
- `relative_pp = return_pct - benchmark_return_pct`，单位为百分点。
- `up_share = up / total`，`down_share = down / total`，范围为 `[0,1]`，分母包含平盘。

`comparison_groups` 按相同 `market`、`taxonomy`、`basis`、`state`、UTC 归一后的 `start`、`end` 分组，只含合资格行；保留首次出现顺序和单元素组。`id` 不是分组键。

重复 JSON 键或 ID、畸形 JSON、布尔或非有限价格、非法计数、错误合计、无时区时间、无效区间和输出溢出均失败。失败以非零退出并只输出 `{"error":{"message":"非空说明"}}`，不返回部分结果或静默默认值。

先从任务构造有来源谱系的输入，检查排除原因和比较组，再只使用合资格结果。区间收益不自动代表热度变化，也不等于日涨跌幅序列的复合结果。

同一任务还需要断言、事件或文件检查时，可把相同输入放入 `sector_workflow.py` 的 `metrics` 字段。只有复杂任务确实要求复现时，才按任务授权扩展原始数据、日涨跌复合、量能或有效成分处理；不把简单问题变成量化评分，不按名称或 ID 分配阶段。
