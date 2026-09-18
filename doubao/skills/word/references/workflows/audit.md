# Word 包体、结构与项目排版自动审计

Word 审计用于检查 DOCX 包体、已建模的 OOXML 结构、项目排版规则，以及明确指定的字数范围。统一使用`audit.py`脚本执行校验。

> **结果获取方式（重要）**：完整审计结果会直接打印到标准输出（stdout），位于 `----- BEGIN AUDIT REPORT JSON (complete; do not read any file) -----` 与 `----- END AUDIT REPORT JSON -----` 之间。直接解析其中的 JSON，不要从文件读取审计结果。

## 一、审计方式与参数选择

每次审计都需要提供待检查的目标 DOCX 文件。根据文档来源和任务要求，按以下规则增加参数。

### 1. 新建或重新设计的文档

如果文档是新建的，或者没有需要保持的可编辑 DOCX 源文件，直接审计目标文件，不添加 `--source` 参数。

### 2. 基于模板或既有文档编辑

如果目标文件是在某个可编辑 DOCX 模板或既有文档基础上修改得到的：

- 修改前保留一份未经改动的源文件；
- 审计目标文件时，增加 `--source SOURCE_DOCX`；
- `SOURCE_DOCX` 必须指向修改前的源文件，并且不能与目标文件是同一个文件；
- PDF、图片或其他不可编辑样稿不能作为源文件；
- 审计及修复过程中必须保持源文件不变。更换源文件后，之前的对比审计结果全部失效。

### 3. 有明确字数要求

只有任务明确提出字数限制时，才增加字数参数：

- 要求不少于 N 字：增加 `--word-count-min N`；
- 要求不超过 N 字：增加 `--word-count-max N`；
- 要求字数在 N～M 之间：同时增加 `--word-count-min N` 和 `--word-count-max M`；
- 字数上下限均包含边界值；
- 最小值不能大于最大值；
- 字数参数可以单独使用，也可以与 `--source` 同时使用。

任务没有明确字数要求时，不添加任何字数参数。

## 二、默认检查

两种方式都会执行以下检查：

- DOCX 是否为可读 ZIP，必需 part 是否存在，XML 是否可解析，ZIP member 是否重复；
- 关系 Id、Type、Target、TargetMode 是否符合 OPC，内部目标是否存在，关系引用的类型和模式是否符合使用它的 OOXML 元素；
- 所有正文、页眉、页脚、脚注、尾注和批注中的 `wp:docPr/@id` 是否为32位无符号整数且全局唯一；绘图尺寸不能是非法整数；
- 编号实例和抽象编号引用是否存在且标识合法，书签/编号整数ID按数值匹配（`+01` 与 `1` 相同）；
- 字段 begin/separate/end、书签 start/end 是否成对；
- `w:tblPr`、`w:tcPr` 中已建模的表格属性节点是否符合 OOXML 相对顺序；
- 页面尺寸和表格网格列宽是否使用合法的 `ST_TwipsMeasure`：
- 表格单元格内的“正文段落”，其最终生效的首行缩进是否为 0；
- 字体是否有错误；
- 中文段落中是否包含英文双引号

## 三、`--source` 额外检查

源文件模式在默认检查之外，增加 `E_COMPARE_ADDED_CONTENT_STYLE_MISMATCH`，检查编辑场景中新插入章节的标题或正文格式，是否与源文档同类内容的统一格式不一致。

## 四、`--edit-plan`（仅 Canvas OOXML）

[`Canvas OOXML 编辑`](canvas-doc-ooxml.md) 可传 `--edit-plan <path>`；原有新建和文件编辑流程不传，行为不变。

- JSON 格式为 `{"planned_changes": [{"code": "错误码", "location": "精确位置"}]}`；可用 `location_prefix` 代替或补充 `location`。每条规则必须有非空 `code` 和至少一个非空位置条件，否则退出 `2`；同时提供两个位置条件时按 AND 匹配。
- `location` 精确匹配；`location_prefix` 匹配完整节点及后代，边界为 `#` 或 `/`，也支持以边界符结尾。例如 `word/document.xml#p1` 不匹配 `#p10`，run/char 编号同理。
- 仅允许豁免 `E_COMPARE_ADDED_CONTENT_STYLE_MISMATCH`、`E_CHINESE_ASCII_DOUBLE_QUOTE`、`E_TABLE_PARAGRAPH_FIRST_LINE_INDENT`，且必须对应用户要求和写前计划。首次 audit 后可补充计划内差异的精确位置，不得扩大计划或用宽泛前缀掩盖其他错误。
- 命中项不进入 `errors` / `error_summary`，也不阻断；其余错误仍阻断。`error_count` 保留全部错误数，`edit_plan` 返回计划内外计数及计划内按码摘要；头行增加 `in_plan/out_of_plan`。`automated_status`、`automated_checks_passed` 和退出码按剩余阻断错误判断。

## 五、产物、退出码与修复循环

通过命令行与路径前置校验后，`audit` 会把结果直接打印到 stdout 的 `----- BEGIN AUDIT REPORT JSON ... -----` 与 `----- END AUDIT REPORT JSON -----` 之间，直接解析这段 stdout JSON。缺少 `lxml`、输入不存在、`SOURCE_DOCX` 与 `TARGET_DOCX` 相同等前置错误会以退出码 `2` 和 stderr 中的 `[INPUT ERROR]` 结束。结果包含：

- `error_count`：本次发现的错误实例总数（真实条数，不受聚合影响）；
- `error_summary`：始终存在的紧凑摘要——`total_findings`、`distinct_codes`、
  `by_code`（每个错误码的实例数）。即使结果被裁剪，这里也保留完整的按码计数；
- `errors`：按“同一根因”（错误码、message、expected、actual、修复建议相同）聚合后的
  分组列表。每组含 `occurrences`（该根因的实例数）和至多 3 个 `sample_locations`，
  单实例组保留原始 `location` 与完整 `evidence`；

退出码定义：

- `0`：本次自动检查没有剩余阻断错误；
- `1`：发现需要修改的确定性错误或命中明确阈值的版式错误；
- `2`：DOCX、依赖或审计输入无效，本轮检查未完整执行。

每次修改 `TARGET_DOCX` 后都必须重新运行完整 `audit`，并直接解析 stdout 的
`BEGIN/END AUDIT REPORT JSON` 块。退出码 `1` 时要看 `error_summary.by_code`
获取完整实例数，以及 `errors` 中保留的聚合详情。若 `report_budget.trim_level=3`，`errors` 可能为空，此时以
`error_summary` 为完整计数依据。退出码 `2` 时 stdout 不会有结果，直接读取
stderr 中的 `[INPUT ERROR]`。修复后再次运行，直到最新文件取得退出码 `0`。
源文件模式下，`SOURCE_DOCX` 必须保持不变；更换源文件后旧结果失效。

===== 全文完 =====