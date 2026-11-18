# 确定性证据与算术工具契约

普通对话解答无需创建中间文件或运行本地脚本。当任务涉及严格 `as-of` 截点多源证据筛选、复杂传导有向图核验，或包含多项环比变动、分项占比、跨币种换算、分类加总及有条件情景收益计算时，可调用 `scripts/event_claim_engine.py` 进行确定性复核。未实际运行的脚本绝不声称已执行。

## 参数说明、输入限制与退出码

`scripts/event_claim_engine.py` 仅使用 Python 标准库，支持两种模式：

- `input`（位置参数，可选，默认 `-`）：JSON 文件路径、内联 JSON 字符串或 `-`（从标准输入读取）。单次输入上限为 **1 MB（1,048,576 字节）UTF-8 JSON**，单数组上限 **500 条记录**。
- `--mode`（可选，`claims` 或 `calc`，默认 `claims`）：
  - `claims`：校验事件法律状态门禁（`rumor` / `proposed` / `announced` / `adopted` / `effective` / `superseded` / `repealed`）、核对证据发布时间 `published_at` 是否晚于信息截点 `event.as_of`（要求带时区的 ISO-8601 时间戳）、检查传导图是否存在环路或孤立节点，并评估是否具备同口径事前预期与可比行情以判断市场计价。参考 [工具输入样例](schemas/deterministic-tool.example.json)；如需记录可读台账可参考 [事实台账样例](schemas/facts.example.json)。
  - `calc`：执行纯领域算术与勾稽复核，支持五类计算块：`changes`（初末值涨跌幅、基点与变动方向）、`shares`（分项占总量比例及分项是否大于总量的越界拦截）、`reconciliations`（分类子项加总与总计差额核对）、`fx_conversions`（跨币种金额同纲折算，汇率须大于 `0`）、`scenarios`（仅在事件已确认且概率和等于 `1.0 ± 1e-6`、各情景均在 `[0, 1]` 且分母大于 `0` 时计算持有期与年化收益）。
- `--output`（可选）：将结果 JSON 写入指定文件路径；省略时输出至标准输出。
- `--pretty`（可选开关）：启用缩进与键排序格式化输出。
- **退出码**：`0` 表示输入合法且完成计算或证据评估（结果中的领域异常在 `errors` / `warnings` 字段结构化返回）；`2` 表示文件不可读、JSON 语法错误、超出大小上限、缺少时区或数值越界等输入错误。

## 可执行调用示例

```bash
# 示例1：默认 claims 模式，核验样例事件的截点证据、传导图与计价基线门禁并格式化输出
python3 scripts/event_claim_engine.py references/schemas/deterministic-tool.example.json --pretty

# 示例2：calc 模式复核环比变动方向、分项占总量越界与分类条目加总勾稽
python3 scripts/event_claim_engine.py --mode calc '{"changes":[{"id":"period_metric","start":120.0,"end":114.0,"unit":"USD_mn"}],"shares":[{"id":"sub_segment","part":18.0,"whole":75.0,"strict_subset":true}],"reconciliations":[{"id":"category_items","total":30,"parts":[12,18]}]}' --pretty

# 示例3：calc 模式将不同币种金额折算为同一计价货币，消除跨币种比较量纲误差
python3 scripts/event_claim_engine.py --mode calc '{"fx_conversions":[{"id":"fx_sample","amount":100.0,"from_currency":"CNY","to_currency":"USD","fx_rate":0.14}]}' --pretty

# 示例4：calc 模式通过标准输入计算已确认事件的多情景概率加权终值，并写入输出文件
echo '{"scenarios":{"event_status":"confirmed","current_value":100,"scenarios":[{"name":"base","probability":0.6,"terminal_value":112,"years":1},{"name":"downside","probability":0.4,"terminal_value":88,"years":1}]}}' | python3 scripts/event_claim_engine.py - --mode calc --output /tmp/scenario-calc.json --pretty
```

引用工具结果时完整保留单位、币种、假设前提及因证据缺失而标记为不可量化的边界，不篡改计算值。
