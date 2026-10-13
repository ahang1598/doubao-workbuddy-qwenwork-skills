# 03 · summary — 汇总报表

> 生成并推送某模板的当日汇总报表。**运行时只读操作**，一次性调用即返回。

---

## 速查表

| 想做什么 | 直接看 |
| :--- | :--- |
| 立即给某模板出一份汇总并推送 | [#生成报表](#生成报表) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py summary --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### summary run

- **自动定位机制**：`--template-id` 必填，会自动定位该模板**当日**最新一条任务记录，读取对应动态任务表的记录数量计算指标（记录存在即视为已提交）
- **多模板时未指定 ID** → H8 触发，必须先 `template list` 让用户挑（见 `../shared/hard-constraints.md#H8`）
- **接收人**：取模板的 `summary_receivers` 字段（逗号分隔 UserID）；**为空则不推送**，仅返回结构化报表给 Agent
- **输出**：`{template_id, task_id, task_table_name, total, submitted, pending, summary_text, recipients, ...}`
- **统计口径**：与 `stats *` 命令族一致，详见 `../shared/data-model.md#统计口径stats-命令族--summary-run`

---

## 生成报表

**触发信号**：用户说"现在就给我推一份汇总 / 生成某模版的报表"。

调用 `summary run --template-id <TPL>`；完整参数见 `uv run python scripts/cli.py summary run --help`。

**关键决策点**：
- **多模板时未指定 `--template-id`** → H8 触发，必须先 `template list` 让用户确认，详见 `../shared/hard-constraints.md#H8`
- **模板 `summary_receivers` 为空** → 不推送，仅返回结构化报表给 Agent

---

## 相关参考

- 字段定义（任务记录 / 动态任务表）：`../shared/data-model.md#任务记录`
- 统计口径：`../shared/data-model.md#统计口径stats-命令族--summary-run`
- 多模板确认规则：`../shared/hard-constraints.md#H8`
