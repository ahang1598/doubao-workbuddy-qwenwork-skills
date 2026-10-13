# 04 · stats — 统计

> 模板使用排行 / 任务完成率 / 门店表现 / 时间趋势。**运行时只读操作**，可随时执行。

---

## 速查表

| 想知道 | 命令 |
| :--- | :--- |
| 最近哪个模板用得多 | [`stats template`](#stats-template) |
| 整体完成率怎么样 | [`stats task`](#stats-task) |
| 哪家门店最积极 / 最拖拉 | [`stats store`](#stats-store) |
| 近期每天的派发量 / 完成率走势 | [`stats trend`](#stats-trend) |
| 钻取单模板 | 任意子命令加 `--template-id TPL_xxx` |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py stats --help` / `uv run python scripts/cli.py stats <subcmd> --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### 通用规则（所有 stats 子命令共享）

- **时间窗口**：`--days N` 与 `--from / --to` **互斥**
  - 都不传时**默认 `--days 7`**
  - `--from / --to` 是 `YYYY-MM-DD`，**含起含止**；只传 `--to` 时起点默认为 `--to - 6 天`
- **`--template-id` 可选**：不传则统计全部模板；传入则钻取单模板
- **输出格式**：所有子命令统一输出**纯文本表格**（含中文宽度对齐），**不输出 JSON**——后续解析场景请用其他命令
- **退出码**：`0` 正常；`2` 参数冲突或日期格式错误

### 各子命令业务场景映射

- **`stats template`** → 「最近哪个模板用得多」（默认按 `dispatch_count` 倒序）
- **`stats task`** → 「整体完成率怎么样」（输出末尾附「全局完成率」汇总行）
- **`stats store`** → 「哪家门店最积极/拖拉」；`--sort-by completion_rate`（默认）= 完成率排序；`--sort-by avg_duration` = 按平均耗时由快到慢
- **`stats trend`** → 「近期每天/每周走势」；`--granularity day`（默认）/ `week`

---

## 查看统计

**触发信号**：用户问"最近哪个模板用得多 / 完成率怎么样 / 哪家门店最积极 / 趋势怎样"。

### 业务场景对照表

| 想知道 | 子命令骨架 | 默认行为 / 关键决策点 |
| :--- | :--- | :--- |
| 最近哪个模板用得多 | `stats template` | 按 `dispatch_count` 倒序；可加 `--limit` |
| 整体完成率 | `stats task` | 末尾附「全局完成率」汇总行 |
| 哪家门店最积极 | `stats store` | 默认按完成率倒序 |
| 哪家门店最拖拉 | `stats store --sort-by avg_duration` | 按平均耗时由快到慢 |
| 近期每天 / 每周走势 | `stats trend [--granularity day\|week]` | 默认 `day` |
| 钻取单模板 | 任意子命令加 `--template-id <TPL>` | 与上述任一组合可叠加 |

完整参数 / 时间窗（`--days N` 与 `--from/--to` 互斥，默认 7 天）：`uv run python scripts/cli.py stats <子命令> --help`。

### 性能提示

跨多张动态任务表查询会按时间窗口扫描，时间范围越大开销越大，建议默认用 `--days 7`，
确实需要长跨度时再扩大窗口。

---

## 统计口径

完整口径定义见 `../shared/data-model.md#统计口径stats-命令族--summary-run`，**不要在这里重复**。

简要：完成定义 = 动态任务表中**存在记录**即视为已提交；完成率 = `submitted / total_targets`；
平均耗时基于 `submitted_at - initiated_at`。

---

## 相关参考

- 完整统计口径：`../shared/data-model.md#统计口径stats-命令族--summary-run`
- 配套：先用 `stats *` 找问题模板 → 用 [01-dispatch.md](./01-dispatch.md) 触发补发 / [02-monitor.md](./02-monitor.md) 催办
