# Lark Sheet Formula Verify（+formula-verify）

用户明确要求诊断公式时使用。后续业务需要 AI 计算值时，使用 `--ai-only` 查询异步状态，流程见 `references/lark-sheets-ai-formula-monitoring.md`。公式写法见 `references/lark-sheets-formula-translation.md`。

## 调用契约

最小调用形态：

| 入参 | 含义 |
|---|---|
| `--url` / `--spreadsheet-token` | 表格定位（XOR 二选一，必填） |
| `--sheet-id` / `--sheet-name` | 限定子表（mutually exclusive；省略则扫全部可见子表） |
| `--range` | 限定 A1 范围；省略则用各 sheet 的 `current_region` |
| `--max-locations` | 每类错误样本上限，默认 20 |
| `--exit-on-error` | `status='errors_found'` 时返回非 0 退出码；`partial` 仍需调用方检查 status 并拆分续扫 |
| `--ai-only` | 只检查 `=AI(...)` 异步计算状态；与普通公式 7 类错误扫描分开使用 |

返回核心字段：

- `status` ∈ `success` / `errors_found` / `partial`——**唯一可机读的健康度判据**。
- `total_errors` / `total_formulas` / `scanned_cells`——本次扫描规模指标。
- `has_more`——为 true 表示扫描被内部上限截断（详见后文「截断与续读」），未覆盖完整范围。
- `error_summary[<错误类型>]`——每类错误的 `count` / `locations[]` / `samples[].{address,formula,depends_on}`。
- `compile_errors[]`——合并最近一次写入留下的编译失败清单，与运行时错误并存时同时出现。
- `warning_message`——仅在 `has_more=true` 时出现，告知调用方需要缩小 `--range` / 拆 `--sheet-id` 续读。

## 截断与续读

本节仅用于用户要求的普通公式诊断。

后端有一个内部硬上限对总扫描单元格数做截断（不暴露给调用方），超过后立即返回 `has_more=true` + `warning_message`，`error_summary` / `compile_errors` 仅覆盖已扫描部分。处理路径：

- 关键输出区优先按 `--sheet-id` / `--sheet-name` 拆成多次调用。
- 同 sheet 内按 `--range` 切片（如先 `A1:Z200` 再 `AA1:AZ200`），逐块诊断。
- 按范围继续核验，全部分段通过后才可宣称完整验证；本轮无法完成时保留公式并明确未覆盖范围，不用转纯值、清空或掩盖错误来消除“未验证”状态。

## AI 公式计算状态（`--ai-only`）


飞书表格提供一个统一的 **`AI` 公式**（`=AI(prompt, [range])`，用自然语言驱动翻译 / 分类 / 情感分析 / 信息提取 / 总结 / 润色等，写法与清单见 `references/lark-sheets-formula-translation.md`）。AI 公式的写入与普通公式一致（复用 `+cells-set` / `set_cell_range`，无需特殊接口），但**计算是异步的**：写入后要等 AI 算完才有结果。普通的 `+formula-verify` 只扫本地单元格值（7 类 Excel 错误），看不到 AI 公式的计算状态。

后续操作需要 AI 计算值时，使用 `+formula-verify --ai-only` 查询异步状态；它跳过普通公式的 Excel 错误扫描。状态轮询与完成后取值按 `references/lark-sheets-ai-formula-monitoring.md` 执行，不用 `+cells-get` / `+csv-get` 轮询 AI 结果。

- **`--ai-only` 返回字段**（机读判据以这些为准，均为整数）：
  - `ai_formula_total`——后端返回的 AI 公式汇总计数，**不是本次写入的单元格条数**（同一批写入的多个 AI 公式可能只计为 1），`--range` 也不收窄它——**认返回里的单元格定位，不要拿它和本次预期条数做等值比对**。
  - `ai_formula_done`——已算出结果的条数。
  - `ai_formula_pending_count`——仍在后台计算（`pending`）的条数。
  - `ai_formula_failed_count`——失败 / 不支持的条数。
- **异步预期**：`pending` 只表示后台未完成，不能仅凭此断定服务失败，也不能保证结果稍后一定生成。
- **`--exit-on-error` 兼容**：`--ai-only --exit-on-error` 时，若 `ai_formula_failed_count > 0`，返回非 0 退出码，便于脚本 / CI 收敛。
- 可与 `--sheet-id` / `--sheet-name` / `--range` 共存；AI 状态汇总不保证按 `--range` 收窄，需按返回格址核对目标范围。
- **普通公式不要带 `--ai-only`**：带上会跳过 7 类 Excel 错误扫描，普通公式等于没验。

**`--range` 用整个写入区间，不要抽样**：`--ai-only` 是只读操作、成本低，`--range` 应覆盖本次写入的**全部** AI 公式区间（而非代表性子集）——子集抽检会漏掉「只有列尾那批被写坏」的情况。但别把 `--range` 当过滤器用：它只透传给后端，AI-only 汇总不保证按它收窄，失败项要按返回的单元格定位核对是否落在本次写入区间内。区间过大触发截断（`has_more=true`）时按「截断与续读」拆 `--range` / `--sheet-id`。




典型用法：

```bash
# 后续操作需要 AI 真值时，查询整个写入区间的计算状态
lark-cli sheets +formula-verify --url <表URL> --sheet-name <子表名> --range <整个写入区间> --ai-only
# 需 AI 真值时按 lark-sheets-ai-formula-monitoring 委派监控；收到 computed 后读取结果
```

## 常见陷阱

| 坑 | 应对 |
|---|---|
| 错误字符串本地化 | 后端按内部 `error_kind` / `compute_status` 字段识别错误类别，不走字符串匹配；调用方拿到的 7 类英文错误代码由后端统一规范输出，与 locale 无关。 |
| `formatted_value` 可能隐藏错误 | 某些条件格式 / 自定义数字格式会把 `#DIV/0!` 显示成空白。后端直接读 cell `error_kind`，不依赖 `formatted_value`，绕开此类被遮蔽。 |
| 把 `partial` 当全量健康 | `partial` 仅表示**已扫描部分**无错误，剩余区域未知；缩小 ranges 或按 sheet 拆分，直到本次普通公式范围全部 success。 |
| 编译失败 vs 运行时错误 | 同一份报告里 `compile_errors[]` 与 `error_summary` 并存。语义层先解决 `compile_errors[]`、再定位运行时错误。 |

===== 全文完（共 76 行）=====
