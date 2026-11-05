# Lark Sheet Read Data

## 按输入类型设计公式与条件

计算、排序、筛选或公式提取使用任务所需的源数据。复用已读取且满足当前协作时效要求的字段、值与类型信息；信息不足时补读相关区域。读取范围由本次处理需求决定，不另设固定行数的预探步骤，也不把源数据读取延伸为写后结果比对。

按业务规则分别处理输入中实际存在的格式：

- **日期格式**：`YYYYMM`、`YYYY-MM-DD`、`YYYY/M/D`、时间戳与文本“未知”。
- **数值与文本混存**：数值、文本数字、带单位的金额、公式文本或注释；编号和标识符保留文本语义，参与运算的值按任务口径转换。
- **空值与 0 / "0"**：区分缺失、合法零值及文本值。
- **大小写 / 全角半角差异**：仅按用户允许的归一化规则处理。

根据已知输入格式和业务定义编写条件分支，必要时使用 `IFS`、`IFERROR` 或数值辅助列。`IFERROR` 只表达符合业务定义的异常分支，不用它掩盖已知的类型或引用错误。

⚠️ **大数字（15 位以上的身份证 / 参考号 / 流水号）做去重 / 比较时禁止用 `+csv-get` 的显示值**：`+csv-get` 返回的是**格式化显示值**，15 位以上数字会被显示成 `1.04E+14` 这类科学计数法——多个本不相同的号在显示层全变成同一个 `1.04E+14`，拿去判重会**整列误判为重复**。比较 / 去重 / 匹配大数字时必须改用 `+cells-get`（取原始精确值）或把该列读为文本，禁止用 csv-get 的科学计数显示值（反例：大批长参考号被显示成科学计数后，互不相同的号全变成同一个值，被当成整列重复并错误高亮）。

## 使用场景

读取。从飞书表格中读取单元格数据。本 reference 覆盖 4 个 shortcut，按读取目的选择：

| 读取目的 | 用这个 shortcut | 数据去向 | 说明 |
|---------|----------------|---------|------|
| 快速查看纯值数据、批量处理 | `+csv-get` | 对话上下文 | 返回标准 CSV（`csv` 字段，可直接喂 csv.reader）；**不传 `--max-chars` 即读全量**，大表由 CLI 内部分批取回拼接。要按字面行号逐行定位时加 `--include-row-prefix` 拿回 `[row=N]` 版本。已通过产物交付工具交付的表格，在回复中用产物名称指代，不再追加 URL 引用。引用其他来源表的信息时，保留工具结果 `citations` 字段中 `<url>...</url>` 内的原始 URL，并紧随对应表述以 `<RichMediaReference>["url"]</RichMediaReference>` 格式标注。 |
| 按列类型结构化读出（喂 DataFrame / round-trip 回 `+table-put`） | `+table-get` | 对话上下文 | 返回 typed 协议（`columns:[列名]` + `data` + `dtypes`/`formats` + `range`），输出形状对齐 pandas split；可一行 `pd.DataFrame(sheet["data"], columns=sheet["columns"]).astype(sheet["dtypes"])` 还原 DataFrame，或直接 round-trip 回 `+table-put`。不带 `--range` 时读**完整 used range**（跨过表中部空行 / 空列），每个子表回传读取范围 `range`；used range 超 20 万格时会被拒绝并给出替代命令——每格是一个对象，体积约为 `+csv-get` 的 17 倍，整表读走 `+workbook-export --file-extension csv --output-path` 或 `+csv-get`；不传 `--max-chars` 时读全量；显式给了才会截断，此时该子表带 `truncated: true` 与 `truncation_warning`。回执的 `complete` 是读全判据，`complete:false` 必定伴随非零退出码。注意这与下文 `current_region` "遇表中部空行截断"不矛盾：`+table-get` 读的是子表物理 used range（飞书记录的已用矩形，含中间空行），`current_region` 是从锚点连通扩展、遇整行空行就断 |
| 查看公式、样式、批注、数据验证 | `+cells-get` | 对话上下文 | 返回单元格完整信息，token 开销较大 |
| 查看某区域的下拉框（数据验证）配置 | `+dropdown-get` | 对话上下文 | 返回该 A1 范围的下拉选项、多选开关和胶囊配色 |

**选择原则**：
- 只看值或做数据处理 → `+csv-get`；默认读全量，结果超出 stdout 阈值时自动落盘、路径写在回执里
- 要按列类型结构化读出（喂 DataFrame / round-trip 回 `+table-put`）→ `+table-get`
- 需要公式/样式/批注 → `+cells-get`
- 查看某区域下拉框的选项、多选开关或胶囊配色 → `+dropdown-get`

## 读表理解脚本（Agent 优先入口）

当目标是"先理解表格内容 / 结构 / 子表边界"，且本地存在 `scripts/lark_*.py`（只随仓库版 skill 分发，二进制内嵌版不含 `scripts/`），可优先用这组只读脚本，再决定是否直接调用上述 shortcut。脚本是可选捷径，不是必经入口——脚本不可用时直接按下表右列的 CLI 等价路径执行：如果任务很小，或需要公式 / 样式 / 批注 / 精确原始值等脚本未覆盖的信息，可以直接用 CLI 做等价或更精细读取。

| 脚本 | 底层 shortcut | 适用场景 |
| --- | --- | --- |
| `scripts/lark_inspect_workbook.py` | `+workbook-info` / `+sheet-info` / `+csv-get` | 飞书表格第一步预检：输出所有 sheet summary、布局、预览和 `data.selection`；未点名时仅从 `resource_type=sheet && is_hidden=false` 的 visible_grid 候选中选，唯一才自动使用，多候选不得按 index 猜。 |
| `scripts/lark_detect_subtables.py` | `+workbook-info` / `+sheet-info --include merges,hidden_rows,hidden_cols` / 小窗口 `+csv-get` | 同一 sheet 可能有多个表格区域、汇总块、备注块时，在**已知且未截断的窗口**内识别候选子表 range |
| `scripts/lark_profile_table.py` | `+csv-get` / `+sheet-info --include hidden_rows,hidden_cols`（默认包含隐藏行列时；必要时再手工 `+cells-get` / `+table-get`） | 对**已确认且未截断的候选 range**做表头、数据范围、列类型、特殊行画像，并输出 `summary` / `field_map` / `risk_warnings` / `write_hints` |

`lark_profile_table.py` 提供候选表头、数据范围、列类型及特殊行信息。结合任务语义和已有数据选择实际处理范围；存在影响本轮操作的歧义时补读对应区域。已有信息足够时直接处理，不重复画像或采样。

`lark_profile_table.py` 的使用口径：

| 任务类型 | 建议 |
| --- | --- |
| 只读取或修改用户明确指定的单个单元格 / 很小范围，且不需要理解整表 | 可直接用 CLI |
| 批量写入、公式 / 计算、排序、筛选、删除、仅保留、去重、lookup / 匹配、条件高亮、透视表、图表、汇总 | 已有读取结果足以确定表头、数据范围、字段列、列类型和特殊行时直接使用；信息不足时，可用 `lark_profile_table.py` 或等价 CLI 补充。去重 / lookup 若目标列含 `long_numeric_like_id`、前导 0 或格式化数字，profile 只能定位列，比较值必须改用 `+cells-get` 或 `+table-get` |
| 多块表、表头不确定、存在合并 / 汇总 / 空行 / 备注块、选区是单格但任务语义是整表 | 先 `lark_detect_subtables.py` 或补充 CLI 确认候选范围，再对目标 range 跑 `lark_profile_table.py` |
| 需要公式、样式、批注、数据验证、精确原始值、长数字 ID 精确比较 | 直接使用能返回所需字段的 `+cells-get` / `+table-get`；纯值批量读取可用 `+csv-get` |

推荐链路（大表先定窗口，脚本不接受截断结果）：

```bash
python3 scripts/lark_inspect_workbook.py --url "<表格URL>"
# 先用 +workbook-info 和小窗口 +csv-get 确认真实 sheet、列边界和起始区域；大表按行窗口推进。
python3 scripts/lark_detect_subtables.py --url "<表格URL>" --sheet-name "<子表名>" --range "A1:H200"
python3 scripts/lark_profile_table.py --url "<表格URL>" --sheet-name "<子表名>" --range "A1:H200"
```

`lark_detect_subtables.py` / `lark_profile_table.py` 显式传小 `--max-chars` 控制体量，因此仍可能命中 `has_more`；命中时它们以错误退出并报告已读取的 `actual_range`，绝不基于半截数据给出候选范围或画像。遇到此错误，以 `actual_range` 为已完成窗口，缩小列数或从其末行之后继续读；跨窗口的候选范围、汇总行和写入落点必须再用 CLI 核对，不能把单个窗口结果当整表结论。

脚本只读，不做任何写入。它们的输出用于降低 token 和定位错误；后续需要公式、样式、批注、精确原始值时，仍按本文件规则直接调用 `+cells-get` / `+table-get` / `+csv-get`。写入前如果使用了 `lark_profile_table.py`，至少读取并使用这些字段：`summary.header_row`、`summary.data_range`、`summary.data_row_segments`、`field_map`、`risk_warnings`、`visibility`、`write_hints.safe_append_col` 和 `special_rows`。`data_range` 保留表头后至最后非空行，`data_rows` 是该候选范围内实际读到的行数；`special_rows` 只是关键词线索，确认语义后再排除真实汇总 / 签名行，不按关键词删记录。确认业务边界且 `risk_warnings` 不含 `data_range_has_gaps` 时，才可按连续范围写入；有缺口时按 `data_row_segments` 分段读写。

**关联前检查键与返回值集合**：已确认范围和表头、且比较值在 CSV 中保真时，可同时画像并检查键关系：

```bash
python3 scripts/lark_profile_table.py --url "<表格URL>" --sheet-name "<子表名>" \
  --range "A1:H200" --header-row 1 --key-cols A,C --value-cols F,G
```

`--header-row` 是工作表绝对行号，`0` 表示所读范围没有表头；键诊断必须显式给出，避免把首条记录误作表头。列参数是工作表列字母；`key_profile` 区分同键同值重复与同键不同返回值，样例保留整组字段对应和源行号，不自动取首项、去空格或转换类型；样例有展示上限，生成结果须使用完整来源。疑似汇总行不会自动排除，先按任务确定范围；仅窗口内唯一不代表全表唯一。长数字或格式化显示值仍按上文改用精确原值读取，并对全量键做同样分组核验。

脚本关键 flag：

| Flag | 脚本 / 默认 | 何时调整 |
| --- | --- | --- |
| `--skip-hidden` | profile / detect，关闭（默认包含隐藏行列） | 只分析可见数据时开启；此时必须使用 profile 的 `data_row_segments`，不要把连续 `data_range` 直接用于写入。 |
| `--max-chars` | inspect `8000`；profile / detect `25000` | 输出过大时缩小范围或降低值；profile / detect 若截断会报错并给 `actual_range`，按窗口继续。 |
| `--header-row` / `--key-cols` / `--value-cols` | profile，默认不启用键诊断 | 显式表头（0为无表头）、联合键列及整组返回字段；返回字段可省略，此时只统计重复键。 |
| `--header-scan-rows` | profile `20` | 表头前有多行标题、说明或空行时提高；过大时结合 `possible_multi_row_header` 补读确认，不要仅凭评分结果写入。 |
| `--max-sheets` | inspect `3` | 未指定 sheet 时仅前 N 个 sheet 带 layout / preview，其余仍返回摘要并在 warnings 说明。 |
| `--max-merge-components` | detect `2000` | 超限会跳过 gap 合并并告警；需缩小窗口或人工复核子表边界。 |
| `--gap-rows` / `--gap-cols` | detect `1` / `0` | 子表被切碎或粘连时调整；每次调整后复核候选范围。 |

detect 最多确认 10 个跨窗口合并锚点；超限会在 `warnings` 中说明跳过的数量。遇到该 warning，缩小扫描窗口后再复核受影响的子表边界。

`lark_profile_table.py` 输出触发补读的规则：

- `risk_warnings` 非空时，不要把画像当最终事实；按下表补读或调整，不在表内的 warning 也先保守复核。

| Warning | 必做动作 |
| --- | --- |
| `mixed_value_types` / `long_numeric_like_id` / `formula_or_value_errors` | 补 `+cells-get` 或 `+table-get`，确认原始值、类型和公式。 |
| `duplicate_headers` / `unnamed_columns` / `header_not_detected` / `header_row_not_first` / `many_empty_cells` | 补 `+csv-get` 读取表头附近和空值样本，确认真正表头与字段列。 |
| `data_range_not_detected` / `special_rows_present` / `empty_rows_present` | 补 `+csv-get` 读取尾部和特殊行样本，确认有效数据末行。 |
| `possible_multi_row_header` | 补读表头上下各 1-2 行；必要时 `+sheet-info --include merges` 核对跨列合并。 |
| `hidden_rows_in_range` / `hidden_columns_in_range` | 写入前用 `+sheet-info --include hidden_rows,hidden_cols` 确认是覆盖还是跳过隐藏内容。 |
| `data_range_has_gaps` | 不按连续 `data_range` 写；用 `summary.data_row_segments` 对每个实际读取行段单独读写。 |
| `data_range_has_col_gaps` | 返回的列不连续（`--skip-hidden` 跳过了隐藏列）；不要把 `data_range` 当连续列区写回，按 `summary.data_col_segments` 分列段处理，否则缺口右侧的值会整体错位。 |

- `write_hints.safe_append_col` 只是候选追加列。新增列或覆盖区域前，依据已有的值、公式、样式、隐藏列和对象信息确定目标占用及授权范围；信息不足时才用 `+csv-get` / `+cells-get` / `+sheet-info` 补读。该字段已跳过隐藏列（见 `write_hints.skipped_hidden_cols`）；`--skip-hidden` 下，数据右边缘的隐藏列可能不在返回网格中，也不触发 `data_range_has_col_gaps`，不能直接用「最后一列 +1」推落点。

⚠️ **解析 CLI 输出只读 stdout**：数据走 stdout、诊断与警告走 stderr，解析 JSON 时别用 `2>&1` 合流（警告混进去会解析失败），用管道或单独重定向 stdout。命令失败先读 stderr 再调整，别原样重发。

⚠️ **大数据不要灌进上下文**：`+csv-get` / `+cells-get` 都受调用方 Bash / 终端的单命令 stdout 输出上限约束（常见默认约 30000 字符）。默认读全量时，结果超出 stdout 阈值会自动落盘，回执给出 `output_path`，后续用本地脚本处理该文件、再用 `+csv-put` 分批回写。只要结果直接进上下文，就显式给 `--max-chars 25000` 主动截断取样本。

> **`complete` 是唯一读全判据**——内联结果与落盘回执都带这个字段（没有单独的 `truncated` 标志，那是同一事实的第二个名字；要做什么看 `note`）。别拿 `warning_message` 的文字当判据：它是上游文案、随语言变化。`--output-path` 只决定落点，不影响读多少。内部分批有任一批重试耗尽时命令以非零码退出，回执 `complete:false` 并给出已完成边界；多子表读取还会用 `unread_sheets` 列出没读到的子表。**不要用文件行数或 `wc -l` 判断读全**——多行文本单元格会让物理行数虚高于逻辑行数。

**`+csv-get` 返回值核心设计**：
- `csv` — **CSV 数据入口**，标准 RFC4180，可直接喂 csv.reader / pandas。
- `annotated_csv` — 每一逻辑行前加 `[row=N] ` 前缀（N = 真实表格行号）的同一份数据，**仅在 `--include-row-prefix` 时返回**。需要把行号填进下游工具参数时加这个 flag，读前缀比按序推算可靠。
- `col_indices` — **定位列字母唯一入口**。在表头中找到目标字段是第 j 个（0-based），用 `col_indices[j]` 取列字母。**禁止手数逗号**——列数超过 10 时极易 off-by-one（例如把 W 误判为 X）。
- `row_indices` — 与 `csv` 数据行一一对应的真实行号数组。不开 `--include-row-prefix` 时行号从这里取；按下标取值即可，不要自己从 `actual_range` 心算累加。
- `current_region` — 从请求范围扩展到被空行空列包围的连续数据区域（等价于 Excel Ctrl+Shift+*）。它**遇表中部整行空行 / 整列空列就截断**，可能遗漏空行之后的数据，不能单独作为整表边界。已确认范围直接复用；边界不明时按下方「确定数据范围的正确流程」定位。

注意：

- `+csv-get` 和 `+cells-get` 默认返回全量；只有显式给了 `--max-chars` 才会截断并带 `has_more`。两者在处理返回数据之前都必须先读 `warning_message`（上游 schema 要求先读它再用其它字段，内含定位与截断续读提示），`+cells-get` 还要用每个 range 的 `actual_range` / `row_indices` / `col_indices` 判断真实位置
- 隐藏行列默认包含在返回结果中（`--skip-hidden=false`），如需只看可见数据设为 `true`。读取原语本身不标注哪些行列被隐藏：若要识别隐藏区间（以决定是否过滤、或如何解读混入的隐藏数据），用 `+sheet-info --include hidden_rows,hidden_cols` 取隐藏行列集合，再结合 `+csv-get` / `+cells-get` 返回的 `row_indices` / `col_indices` 判断每行 / 每列是否隐藏
- 要判断单元格内容是否被行高列宽挤到显示不全（排版检查、调整行高列宽前），给 `+cells-get` 加 `--include truncation`：会按字号 / 自动换行 / 行高列宽估算并返回被截断单元格的 `isRowTruncated` / `isColTruncated`（未返回视为未截断）。有额外计算开销，仅需要时才开

**常见配置错误（必须注意）**：
- **别把大表读进上下文**：大表（数百行以上）默认读全量会自动落盘，用回执里的 `output_path` 交给本地脚本处理，不要试图让整表进上下文；只需要样本时显式给 `--max-chars`。`scripts/lark_sheet_read_cli.py` 的 `run_sheets()` 已透明处理这个回执（自动读回文件），基于它的脚本无需各自适配
- **了解结构与业务取数分开**：已有信息能确定目标字段、行标签与范围时直接复用；结构不明时按本次任务补读：
  - **横向（列头）**：读取待处理字段的完整表头层级；任务涉及全表字段或目标列未知时才扩展列范围，不默认读到物理末列。
  - **纵向（行标）**：需要按日期、类别或编号定位行时，读取目标范围内尚未知的行标签；涉及全部行时才读全，已知指定行不另扫整列。业务范围不明时按下方「确定数据范围的正确流程」定位。
  - 数据量大时按回执的 `output_path` 走本地处理 + 分批回写，不要一口气拉全表到上下文。
- **`+cells-get` 滥用**：当只需要数据值时，使用 `+csv-get`（token 开销约为 `+cells-get` 的 1/5）。只有确实需要公式、样式或批注时才用 `+cells-get`
- **拿部分数据当全量**：`has_more=true` 只在显式给了 `--max-chars` 时出现，说明这是你主动要的样本；任务需要完整数据就去掉 `--max-chars` 重读，不要拿样本直接写入
- **直接按 `+cells-get` 返回二维数组下标推导真实位置**：`ranges[n].cells[i][j]` 里的 `i/j` 只是返回数组下标，不等于真实表格行列。定位真实行号必须用 `ranges[n].row_indices[i]`，定位真实列字母必须用 `ranges[n].col_indices[j]`；若 `--skip-hidden=true`、请求范围越界被裁剪，或最后一行是部分返回，错误地自己数下标会立刻错位
- **CSV 行号计数错误**：`+csv-get` 返回的 CSV 遵循 RFC 4180 标准，被双引号 `"..."` 包裹的字段中的换行符属于**字段内容的一部分**（即单元格内换行），不代表新的一行。计算行号时必须按**逻辑记录**计数，而非按物理换行符 `\n` 计数
- **手动数列确定列号**：禁止通过在 CSV 表头中手动数逗号/字段来确定目标列的列字母。当列数超过 10 时，手动计数极易产生 off-by-one 偏移（例如把 W 列误判为 X 列）。**必须使用 `col_indices`**：先在 CSV 表头中找到目标字段名是第 j 个字段（0-based），再用 `col_indices[j]` 获取该列的实际列字母
- **用数据列的值推导行号（常被巧合掩盖）**：CSV 中常见"序号 / ID / 编号 / No."等形似行号的列，其值与实际表格行号**没有任何绑定关系**——序号可能跳号（1,2,3,5,6...）、可能从非 1 开始、可能有重复或被中途重置。此规则适用于**所有需要行号的下游操作**：合并单元格、区间写入/清空/格式化、插入/删除行、条件格式范围、筛选器范围、图表数据源、透视表范围、搜索替换范围等等——**凡是要把行号填进任何工具参数的场景，行号一律取自 `row_indices`（或加 `--include-row-prefix` 后读行首 `[row=N]` 前缀）**，禁止用"序号=行号"、"表头占 1 行所以数据从第 2 行开始"、"第 N 个序号就在第 N+1 行"等心算，也禁止先心算再"事后核对"。**危险特征**：前几十行中序号恰好等于表格行号（典型成因：表头 +1 与一次跳号 -1 的偏移互相抵消形成巧合），模型一旦把这个巧合当作规律，会在后续所有行沿用；而中间再出现跳号时，从该行起整块区域全部错位。**正确工作流**：①在 `csv` 里定位目标逻辑行（按字段内容匹配）；②取同下标的 `row_indices[i]` 得到真实表格行号（开了 `--include-row-prefix` 就直接读该行的 `[row=N]`）；③把这个行号填进下游工具参数。区间操作时，起止行各取各自的行号。
- **`row_count` 与 `current_region` 都不能单独定末行**：`+workbook-info` 的 `row_count` 是网格物理行数，通常大于真实数据末行；`current_region` 遇整行空行会截断，可能小于业务范围。二者分别是上界和连续块参考；已有完整读取或用户指定范围时直接使用，边界仍不明时再按下方流程定位。
- **current_region 当作纯数据范围**：`current_region` 返回的是从请求范围向四周扩展到被空行空列包围的**连续非空区域**，等价于 Excel 的 Ctrl+Shift+\*。它包含该区域内**所有非空行**——不仅包含数据行，还可能包含标题行、汇总行（如"总计"）、签名行（如"编制人/审批人"）、脚注等非数据内容。**严禁直接将 `current_region` 的末尾行作为数据范围的结束行**。正确做法见下方「确定数据范围的正确流程」

### 确定数据范围的正确流程（边界不明时补读）

排序、筛选、删除或批量写入使用用户指定或已确认的业务范围；已有信息足够时不重复读取。仅在范围不明时，补齐以下信息：

1. **起始行与字段**：读取相关表头及相邻数据，按真实行号识别完整表头层级和首条记录，不固定读取行数。
2. **结束行**：任务覆盖整表且边界未知时，可用不带 `--range` 的 `+table-get` 探测 used range 并按完整性回执取数；超出工具限制时，以物理 `row_count` 为上界分段读取必要字段。中间空白区不证明后面没有数据，未覆盖的部分不能宣称已读全。
3. **业务记录范围**：结合内容与结构区分明细、合计、签名和备注，不只凭名称排除。排序、聚合等需要纯明细时去掉非明细行；美化或用户要求保留的范围仍包含相应合计、备注。只对归属不明的边界补读。

**示例**：`current_region` 返回 `A1:N51`，读取 Row 48~51 发现：

- Row 49: 序号=47, 姓名=xxx, 有正常数据 → ✅ 数据行
- Row 50: "总计", 有合并单元格 → ❌ 汇总行
- Row 51: "总经理：...", "编制人：..." → ❌ 签名行
- **正确数据范围 = A3:N49**（而非 A3:N51）

## Shortcuts

| Shortcut | Risk | 分组 |
| --- | --- | --- |
| `+cells-get` | read | 单元格 |
| `+dropdown-get` | read | 对象 |
| `+csv-get` | read | 单元格 |
| `+table-get` | read | 单元格 |

## Flags

### `+cells-get`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--range` | string | required | A1 范围，如 `A1:F10`（不带 sheet 前缀；用 `--sheet-id` / `--sheet-name` 指定 sheet） |
| `--include` | string_slice | optional | 要返回的信息类别，逗号分隔多个。`truncation` 会额外按行高列宽 / 字号 / 自动换行估算每个单元格是否被截断显示，返回 `isRowTruncated` / `isColTruncated`（有额外计算开销，仅排版检查 / 调整行高列宽前才开）（可选值：`value` / `formula` / `style` / `comment` / `data_validation` / `conditional_format` / `truncation`） |
| `--max-chars` | int | optional | 单次返回字符上限。**不传即读全量**——CLI 内部按 1000000 字符分批取回并拼接，返回始终完整。**显式传值则视为要求截断**：只返回该上限内的内容并给出 `has_more`，用于取样本或控制进入上下文的体量（如 25000）。传 0 等价于不传。 |
| `--output-path` | string | optional | 把完整读取结果写入本地路径（如 `./out.json`），文件内容为 data 载荷的 JSON；stdout 只回含 `output_path` / 字节数 / `complete` 的确认信息。读取本身默认就是全量（CLI 内部自动分页拼接），本 flag 只决定落点，不再影响字符上限。结果超出 stdout 阈值时即使不传本 flag 也会自动落盘，路径见回执。 |
| `--skip-hidden` | bool | optional | 跳过隐藏行列，默认 `false` |

### `+dropdown-get`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--range` | string | required | A1 范围，如 `A2:A100`（不带 sheet 前缀；用 `--sheet-id` / `--sheet-name` 指定 sheet） |

### `+csv-get`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--range` | string | optional | A1 范围，如 `A1:F30`（不带 sheet 前缀；用 `--sheet-id` / `--sheet-name` 指定 sheet）。**可省略：缺省读取整个子表**（按表格实际边界裁剪，返回的 actual_range 标注实际读取范围）；大表配合 --max-chars / --output-path 控制体量 |
| `--max-chars` | int | optional | 单次返回字符上限。**不传即读全量**——CLI 内部按 1000000 字符分批取回并拼接，返回始终完整。**显式传值则视为要求截断**：只返回该上限内的内容并给出 `has_more`，用于取样本或控制进入上下文的体量（如 25000）。传 0 等价于不传。 |
| `--output-path` | string | optional | 把完整读取结果写入本地路径（如 `./out.json`），文件内容为 data 载荷的 JSON；stdout 只回含 `output_path` / 字节数 / `complete` 的确认信息。读取本身默认就是全量（CLI 内部自动分页拼接），本 flag 只决定落点，不再影响字符上限。结果超出 stdout 阈值时即使不传本 flag 也会自动落盘，路径见回执。落盘的是 data 载荷的 JSON（CSV 文本是其中一个字段），不是直接可用的 .csv 文件。 |
| `--include-row-prefix` | bool | optional | 额外输出带 `[row=N]` 行号前缀的 `annotated_csv`，默认 `false`。主载荷 `csv` 恒为标准 CSV（可直接喂 csv.reader）；行号按 `actual_range` 起始行 + 行序推算，行号不连续时（如 `--skip-hidden`）读 `row_indices`。只有要按字面行号逐行定位、又不想自己算时才开——它会让返回体大约翻倍。 |
| `--skip-hidden` | bool | optional | 跳过隐藏行列，默认 `false` |

### `+table-get`

_公共：URL/token（无 sheet 定位） · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--sheet-id` | string | optional | 只读该子表（按 id）；省略则读所有子表 |
| `--sheet-name` | string | optional | 只读该子表（按名）；省略则读所有子表 |
| `--range` | string | optional | 读取的 A1 范围；省略则读每个子表的完整 used range（会跨过表中部的整行空行 / 整列空列，不会被截断） |
| `--max-chars` | int | optional | 单次返回字符上限。**不传即读全量**——CLI 内部按 1000000 字符分批取回并拼接，返回始终完整。**显式传值则视为要求截断**：只返回该上限内的内容并给出 `has_more`，用于取样本或控制进入上下文的体量（如 25000）。传 0 等价于不传。 |
| `--output-path` | string | optional | 把完整读取结果写入本地路径（如 `./out.json`），文件内容为 data 载荷的 JSON；stdout 只回含 `output_path` / 字节数 / `complete` 的确认信息。读取本身默认就是全量（CLI 内部自动分页拼接），本 flag 只决定落点，不再影响字符上限。结果超出 stdout 阈值时即使不传本 flag 也会自动落盘，路径见回执。 |
| `--no-header` | bool | optional | 把第一行当数据而非表头（列名取 col1/col2 …） |

## Examples

### `+csv-get`

以下 `+csv-get` / `+cells-get` 示例要求工作簿与子表两组定位；`+table-get` 的子表定位可选，见其调用说明。

示例：

```bash
# 简单读（sheet 定位必填：--sheet-name 或 --sheet-id 必给一个；range 的 Sheet1! 前缀不能替代它）
lark-cli sheets +csv-get --url "https://example.feishu.cn/sheets/shtXXX" --sheet-name "Sheet1" --range "A1:F30"

# 用 sheet-name 模糊定位（运行时框架会先解析到 sheet-id）
lark-cli sheets +csv-get --spreadsheet-token shtXXX --sheet-name "销售明细" --range "A1:F30"

# 全量读：省略 --range 即读整个子表（按实际边界裁剪，返回 actual_range 标注实读范围），
# 无需先 +workbook-info 探行列再拼 range；默认读全量，大表自动落盘
lark-cli sheets +csv-get --spreadsheet-token shtXXX --sheet-name "销售明细"
```

输出契约（envelope.data）：

- `csv` — 标准 CSV 主入口；`annotated_csv` — 含 `[row=N]` 前缀的同一份数据，仅 `--include-row-prefix` 时返回
- `col_indices` / `row_indices` — 列字母 / 行号映射数组
- `current_region` — 从锚点扩展到被空行空列包围的连续区域的 A1 范围。它不是整表真实边界：中间空行 / 空列可能使范围偏小，表尾汇总 / 签名 / 脚注可能使其大于纯明细范围。已有业务边界直接复用，未知时按上方「确定数据范围的正确流程」定位。
- `actual_range` — **本次实际读到的 A1 范围**。续读 / 校验覆盖度一律以它为准：`actual_range` 小于请求范围时，哪怕 `has_more=false` 也说明只拿到部分窗口，不能把 `row_count` 当成"已读全"
- `row_count` / `col_count` — **本次返回的行 / 列数**（= `actual_range` 的尺寸，随 `--range` 变），**不是整表物理总行列数**；整表物理尺寸取 `+workbook-info`
- `has_more` — 仅在显式给了 `--max-chars` 时才可能为 true，表示本次按你要求截断了；不传 `--max-chars` 时恒为 `false`（已读全量）。它不反映整表边界——覆盖到哪里一律看 `actual_range`

> 要按列类型结构化读出（喂 DataFrame、或 round-trip 回 `+table-put`）用 `+table-get`（见下）；`+csv-get` 给的是带 `[row=N]` 前缀的纯值快照，下游需要行号/列坐标时直接从前缀与 `col_indices` 取。

### `+cells-get`

示例：

```bash
# 读 A1:F10 的公式 + 样式（sheet 定位必填）
lark-cli sheets +cells-get --url "https://example.feishu.cn/sheets/shtXXX" --sheet-name "Sheet1" \
  --range "A1:F10" --include formula,style
```

> ⚠️ 调用方在 `cells[i][j]` 中**不能**用下标推真实行列：必须读 `ranges[n].row_indices[i]` / `ranges[n].col_indices[j]`。

### `+table-get`（飞书 → DataFrame，类型保真读出）

`+table-put`（写入侧，见 write-cells reference）的镜像：把表格读回与 `--sheets` 完全同构的 typed 协议（`sheets[]` + `columns:[列名]` + `data:[[行]]` + `dtypes:{列名:pandas_dtype}` + `formats?:{列名:number_format}` + `range`），可直接喂回 `+table-put` 或一行还原 DataFrame。

**默认（不带 `--range`）先按整张子表物理网格探测 used range**：可跨过表中部空行 / 空列定位真实数据边界，再读取该区域。不传 `--max-chars` 时读全量；显式给了才截断，此时 `truncated=true` / `complete=false` 表示只有部分数据，去掉 `--max-chars` 重读即可。每个子表的 `range` 只表示本次目标区域，不能单独证明内容已完整返回。

列类型从每列 `number_format` 推断（日期格式→`date`/`datetime64[ns]`、数值→`number`/`float64`、bool→`bool`），`date` 列的序列号转回 ISO `yyyy-mm-dd`——日期、数字往返不丢类型。**列类型只在该列所有非空值一致时才定（`number` / `date` / `bool`）；一列混了类型（如数字列混入「暂无」、日期列混入裸数字）会降为 `string`（dtypes 输出 `object`），让 `dtypes` 与 `data` 里每个值自洽——能 round-trip 回 `+table-put`、不让 pandas `astype` 崩。降级是无损的（脏值原样保留为文本）；若要把零星脏值转成数值列，交给调用方在 pandas 侧做（`to_numeric(errors='coerce')`），那里原始值仍在、可追溯。** 默认读所有子表、第一行当表头（`--no-header` 把首行当数据、列名取 `col1` / `col2` …）。

```bash
# 默认读所有子表 → sheets[]（与 +table-put 的 --sheets 同构，可喂回或转 DataFrame）
lark-cli sheets +table-get --url "<表URL>"
# 可选：--sheet-name / --sheet-id 限定只读某一个子表（不给则读全部）
lark-cli sheets +table-get --url "<表URL>" --sheet-name "销售"
```

#### 输出 → DataFrame（用 `sheet_to_df` helper）

输出形状对齐 pandas split：`columns` 是列名数组、`data` 是二维数据、`dtypes` 是 `{列名: pandas_dtype_str}` 映射；子表级 `truncated` 与回执的 `complete` 说明覆盖度。未截断时可直接喂给 `pd.DataFrame(...).astype(...)`。本 skill 提供 [`scripts/lark_sheets_df.py`](../scripts/lark_sheets_df.py)：

```python
import sys; sys.path.insert(0, "scripts")  # cwd 不在 skill 根时改成 scripts/ 的实际路径
from lark_sheets_df import sheet_to_df

# 单 sheet
df = sheet_to_df(out["data"]["sheets"][0])

# 多 sheet——按名字取
sheets = {s["name"]: sheet_to_df(s) for s in out["data"]["sheets"]}
df_sales = sheets["销售"]
```

> 显示格式（千分位、百分比、自定义日期）在 `sheet["formats"]`，pandas 不消费；改完数据 round-trip 回去时透传给 `+table-put` 即可，飞书侧显示不变。

#### round-trip：读 → 改 → 写回（写读对偶）

`sheet_to_df` 和 `df_to_sheet` 一对镜像 helper（[`scripts/lark_sheets_df.py`](../scripts/lark_sheets_df.py)）让 round-trip 三段读 / 改 / 写各一行：

```python
import json, subprocess
import sys; sys.path.insert(0, "scripts")  # cwd 不在 skill 根时改成 scripts/ 的实际路径
from lark_sheets_df import df_to_sheet, sheet_to_df

# 1. 读
out = json.loads(subprocess.check_output(
    ["lark-cli","sheets","+table-get","--url",URL,"--sheet-name","销售"]))
sheet = out["data"]["sheets"][0]
df = sheet_to_df(sheet)

# 2. 改（pandas 操作）
df["营收"] = df["营收"] * 1.1

# 3. 写回（formats 是飞书侧显示格式，pandas 不消费，透传保留显示）
payload = {"sheets": [df_to_sheet(df, sheet["name"], formats=sheet.get("formats"))]}
subprocess.run(["lark-cli","sheets","+table-put","--url",URL,"--sheets","-"],
               input=json.dumps(payload).encode(), check=True)
```

`sheet_to_df(sheet)` 消费 `(columns, data, dtypes)`，`df_to_sheet(df, name, formats=...)` 重新生成同样三个字段——读 / 写完全对偶，只有 `formats` 需要手工透传一次。

### Validate / DryRun / Execute 约束

- `Validate` 阶段只做 XOR 检查、Enum 合法性、防爆参数上限校验；**禁止**联网（如不能用 `--sheet-name` 提前去查 `sheet-id`）。
- `DryRun` 输出请求模板：`--sheet-name` 在 dry-run 输出里生成为 `<resolve:销售明细>` 占位符，不实际解析。
- `Execute` 阶段才进行 sheet-name → sheet-id 解析与 API 调用。

===== 全文完（共 321 行）=====
