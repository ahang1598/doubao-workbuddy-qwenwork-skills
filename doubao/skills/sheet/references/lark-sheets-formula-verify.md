> ⚠️ **强制前置条件**：本文档共 115 行，指令说明和约束分散在各部分。必须先读到末行「全文完」，再执行任何其他操作；即使已找到当前任务所需的指令，也不得提前停止。未见该标记时，下一步必须继续调用 Read，在读完之前不得调用 Bash、`--help` 或任何其他工具。读取工具能一次取全文就一次取全，被截断则调整偏移量（`offset`）续读。本技能所有文档末行均有该标记。

# Lark Sheet Formula Verify（+formula-verify）

> **本文定位**：飞书表格"公式写入后是否真的零错误"的诊断入口。公式的书写规则与 Excel→飞书迁移的语义规则一律以 `lark-sheets-formula-translation` 为唯一权威，本文不重复；本文聚焦"写完之后如何用一次调用发现公式错误"与 AI 公式的异步抽检交付。
>
> **边界**：本文不讲公式怎么写（去 `lark-sheets-formula-translation`），也不讲公式怎么写入表格（去 `lark-sheets-write-cells` / `lark-sheets-batch-update`）。本文只讲两件事：
>
> - **普通公式**：任务里发生公式落表、批量填充公式、`--copy-to-range` 扩展公式、导入含公式 workbook 时，用 `+formula-verify` 做诊断，`errors_found` / `partial` 是风险信号，关键输出区优先修复，非关键区可在交付说明记录。
> - **AI 公式**（`=AI(...)`）：不要用普通公式的"轮询到 zero-error"逻辑；改用 `+formula-verify --ai-only --range` 按「AI 公式校验」的异步抽检规则交付。

## 为什么需要自检

飞书在线表格已经实时算好结果，但"算出来"和"算对了"是两件事。常见缺口：

- 公式编译失败 → 单元格落成文本（写入类 shortcut 返回的 `formula_errors[]` 是**编译失败**信号）。
- 公式编译成功但**运行时错误**：`#REF!` / `#DIV/0!` / `#VALUE!` / `#NAME?` / `#NULL!` / `#NUM!` / `#N/A`——这一类只看 `formula_errors[]` 看不到，必须扫单元格值。

`+formula-verify` 把两路信号合并成一份统一 JSON：一次调用聚合全表错误清单 + 编译失败清单 + 每类错误的定位与样本，AI 一眼就能定位修复。G2 分支中，它提供诊断信号，不再作为默认交付前置条件。

## 调用契约

最小调用形态：

| 入参 | 含义 |
|---|---|
| `--url` / `--spreadsheet-token` | 表格定位（XOR 二选一，必填） |
| `--sheet-id` / `--sheet-name` | 限定子表（mutually exclusive；省略则扫全部可见子表） |
| `--range` | 限定 A1 范围；省略则用各 sheet 的 `current_region` |
| `--max-locations` | 每类错误样本上限，默认 20 |
| `--exit-on-error` | `status='errors_found'` 时返回非 0 退出码（CI 网关用） |
| `--ai-only` | 只校验 AI 公式（见「AI 公式校验」），跳过普通公式的 7 类 Excel 错误扫描；写完 AI 公式后查看计算状态用 |

返回核心字段：

- `status` ∈ `success` / `errors_found` / `partial`——**唯一可机读的健康度判据**。
- `total_errors` / `total_formulas` / `scanned_cells`——本次扫描规模指标。
- `has_more`——为 true 表示扫描被内部上限截断（详见后文「截断与续读」），未覆盖完整范围。
- `error_summary[<错误类型>]`——每类错误的 `count` / `locations[]` / `samples[].{address,formula,depends_on}`。
- `compile_errors[]`——合并最近一次写入留下的编译失败清单，与运行时错误并存时同时出现。
- `warning_message`——仅在 `has_more=true` 时出现，告知调用方需要缩小 `--range` / 拆 `--sheet-id` 续读。

## 写入后诊断规则

任何批量公式 / 含公式列写入完成后，都应调用 `+formula-verify` 做一次诊断。普通公式关键输出区优先修复到 `status='success'`，非关键区可在交付说明中记录；AI 公式不等待全部异步计算完成，按「AI 公式校验」抽检后即可交付。不要等用户显式说"校验一下公式"才想到这里。触发场景：

- `+cells-set` / `+csv-put`
- `+cells-set --copy-to-range` / 模板单元格向整列或整块扩展公式
- `+workbook-import`
- `+batch-update` 中含写入子操作
- `+table-put`（任意列含公式时）
- `+workbook-import`（导入的 xlsx 含公式时）

处置规则：

1. `status='success'` → 记录诊断通过。
2. `status='partial'` → 扫描被内部上限截断。若该公式区是关键输出，可缩小 `--range` 或拆 `--sheet-id` 续扫；否则在交付说明中标明诊断覆盖不完整。
3. `status='errors_found'` 且 `compile_errors[]` 非空 → 根据 `compile_errors[].reason` 修正公式语法（飞书函数名 / 范围语法 / 引用样式），或在成本过高时降级为静态值并说明原因。
4. `status='errors_found'` 且只剩运行时错误 → 按 `error_summary` 的 `samples[].formula` + `depends_on` 排查根因（零除？空值参与运算？引用越界？日期差写法？数组语义？），优先修复关键输出区。
5. 同一处错误连续修复 3 次仍未通过 → 改用 `IFERROR` 包裹兜底，或退回纯值写入，并在交付说明写清不随源数据更新。

注意：

- 在 `status='errors_found'` 的状态下调用 `+cells-set --copy-to-range` 继续扩展会把错误复制放大，建议先处理关键错误。
- "编译失败但运行时无报错"不是 zero-error（编译失败的单元格此刻是文本不是公式，源数据一变就再也算不出值）。
- 只靠肉眼读首末 5 行确认不可靠——表中段、隐藏行、合并区里的错误这样根本看不到；`+formula-verify` 可补充这一诊断视角。
- 只验证写入区首行不够：批量填公式后同时抽查首行、中段、尾部和汇总行；目标是发现“只填到前 N 行”“把明细公式写进合计行”“尾部仍是空/错误值”这类问题。
- 修公式时先定位根因格，再看下游链路。不要把被上游错误污染的下游格全部重写；同型公式优先从相邻正确单元格复制/改引用，写完回读下游关键格是否仍有 `#VALUE!` / `#REF!`。
- 查找/匹配公式必须有错误处理：不要裸写 `VLOOKUP` / `XLOOKUP`。未匹配时返回明确文本（如“未匹配到”），不要静默空串，除非用户明确要求空值。
- 排名/排序公式要处理空值、0 值和不参与排名项；这些项应保持空/0，而不是进入通用排名公式得到正整数名次。

## 截断与续读

后端有一个内部硬上限对总扫描单元格数做截断（不暴露给调用方），超过后立即返回 `has_more=true` + `warning_message`，`error_summary` / `compile_errors` 仅覆盖已扫描部分。处理路径：

- 关键输出区优先按 `--sheet-id` / `--sheet-name` 拆成多次调用。
- 同 sheet 内按 `--range` 切片（如先 `A1:Z200` 再 `AA1:AZ200`），逐块诊断。
- 如时间不足，说明已诊断范围和未覆盖范围。

## AI 公式校验（`--ai-only`）

飞书表格提供一个统一的 **`AI` 公式**（`=AI(prompt, [range])`，用自然语言驱动翻译 / 分类 / 情感分析 / 信息提取 / 总结 / 润色等，写法与清单见 `lark-sheets-formula-translation`）。AI 公式的写入与普通公式一致（复用 `+cells-set` / `set_cell_range`，无需特殊接口），但**计算是异步的**：写入后要等 AI 算完才有结果。普通的 `+formula-verify` 只扫本地单元格值（7 类 Excel 错误），看不到 AI 公式的计算状态。

`--ai-only` 让 `+formula-verify` 只校验 AI 公式、跳过普通公式的 Excel 错误扫描，专用于写完 AI 公式后的异步状态抽检。**它必须是第一校验入口；禁止先用 `+cells-get` / `+csv-get` 轮询 AI 结果。**

- **返回当前计算状态**：`+formula-verify --ai-only` 返回本次调用时 AI 公式的**当前**计算状态快照。
- **异步预期**：少量 AI 公式通常很快算出结果；批量写入后部分公式仍为 `pending`（计算中）属于正常现象，飞书会在后台持续计算。
- **状态三态**：至少能区分「完成」/「进行中（仍在计算）」/「失败或不支持」。仍有「进行中」时，间隔一段时间后再查一次。
- **`--exit-on-error` 兼容**：`--ai-only --exit-on-error` 时，若仍有 AI 公式处于失败态，返回非 0 退出码，便于脚本 / CI 收敛。
- 可与 `--sheet-id` / `--sheet-name` / `--range` 共存，表示「只在指定范围里校验 AI 公式」。

交付规则：用 `--range` 选取代表性范围抽检；确认公式已写入且抽检没有明确的失败 / 不支持状态后，即使仍有 pending 也可以交付，不必轮询到全部完成。交付时告知用户"AI 公式仍在后台运行，结果会陆续完成"。只有发现明确失败 / 不支持状态时才先修复；`+cells-get` 仅在需要核对公式文本、样式或定位异常单元格时补充使用。

**区分「写入层坏了」与「AI 失败 / 仍在算」**：若读回是 `#ERROR`，或看似被截断的字面量（残缺括号如 `E2)`、半截函数名、全角括号），说明公式串在 shell / CSV / JSON 引号层被破坏、根本没作为公式写进去——`--ai-only` 只统计「结构上仍被识别为 AI 公式」的单元格，坏掉的格不计入 `failed`，因此会出现「`failed_count=0` 却读到 `#ERROR`」的假矛盾。此时不要继续等 pending，回到 `+cells-set` 用 `\"` 转义重写该格（写入范例见 `lark-sheets-formula-translation` 的 AI 公式章节）。

典型用法：

```bash
# 写入一批 AI 公式后，抽检代表性范围的计算状态
lark-cli sheets +formula-verify --url <表URL> --sheet-name <子表名> --range <代表性范围> --ai-only
# 没有明确失败 / 不支持状态即可交付；pending 会在后台继续计算
```

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

## 常见陷阱

| 坑 | 应对 |
|---|---|
| 错误字符串本地化 | 后端按内部 `error_kind` / `compute_status` 字段识别错误类别，不走字符串匹配；调用方拿到的 7 类英文错误代码由后端统一规范输出，与 locale 无关。 |
| `formatted_value` 可能隐藏错误 | 某些条件格式 / 自定义数字格式会把 `#DIV/0!` 显示成空白。后端直接读 cell `error_kind`，不依赖 `formatted_value`，绕开此类被遮蔽。 |
| 把 `partial` 当全量健康 | `partial` 仅表示**已扫描部分**无错误，剩余区域未知。关键公式区应继续缩小范围诊断；非关键区可在交付说明标明覆盖不足。 |
| 编译失败 vs 运行时错误 | 同一份报告里 `compile_errors[]` 与 `error_summary` 并存。语义层先解决 `compile_errors[]`、再做运行时自检。 |

===== 全文完（共 115 行）=====
