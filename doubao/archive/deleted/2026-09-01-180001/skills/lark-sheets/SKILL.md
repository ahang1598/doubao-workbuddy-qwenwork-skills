---
name: lark-sheets
version: 3.1.6
description: "表格全场景（本地 Excel/CSV 与飞书/doubao 在线表格）：创建、读写、分析、计算、建模、语义处理、可视化与美化。若用户上传附件、提供表格链接/token，或要求任何表格操作，必须加载。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "lark-cli sheets --help"
---
> ⚠️ **强制前置条件**：本文档共 296 行，指令说明和约束分散在各部分。必须先读到末行「全文完」，再执行任何其他操作；即使已找到当前任务所需的指令，也不得提前停止。未见该标记时，下一步必须继续调用 Read，在读完之前不得调用 Bash、`--help` 或任何其他工具。读取工具能一次取全文就一次取全，被截断则调整偏移量（`offset`）续读。本技能所有文档末行均有该标记。

> ⚠️ **平台差异**：SystemPrompt 里若出现 `Computer OS: Windows`，**在阅读完本 SKILL后，无论后续是否执行lark-cli操作都必须先完整 Read [`references/ref-windows-compat.md`](references/ref-windows-compat.md)，查看在 windows 平台上执行命令所必须要注意的问题，否则会出现大面积报错**。


# 表格全场景处理技能（lark-sheets）

一套场景方法论、两套执行引擎：上传的本地 `.xlsx` / `.xls` / `.csv` 走 **Excel 引擎**（Python `pandas` / `openpyxl` + `scripts/`）读入，交付仍按下方「产物载体」转在线；在线表格与 doubao.com 的 `/sheets/` 链接走 **飞书引擎**（`lark-cli sheets`，详见「三」），按路径模式和 token 判定、**不看域名**。两者经 `+workbook-import` 打通。

当用户预期要表格产物时（哪怕用户说“做个 Excel”“整理成表格”“给我个表”“原表格/原文件”），默认必须交付**经过检查的**飞书在线表格，方便在线预览、协作和编辑。都需要按以下执行来交付表格/Excel产物：
   - 调用 `lark-cli sheets +workbook-import` 将本地 Excel 文件（.xlsx）导入为飞书在线表格；
   - 在使用交付工具交付给用户飞书表格 URL 之前，必须执行`scripts/lark_sheet_selfcheck.py "<url>"` 对飞书表格进行检查，然后核对检查结果并修复。在调用交付工具交付给用户之前，确保脚本输出的检查结果符合预期。禁止把自检发现的差异、公式计算逻辑错误、合计对不上等问题以"注意"、"差异说明"、"请您核对"等形式仅写在回复文字里而不处理产物本身；发现的每一处差异必须在产物内闭环 —— 追查到具体错源并改正。
   - 注意：只要本轮实际执行了对飞书类内容（文档/表格/多维表格等）或豆包文档/豆包表格的写入、编辑或更新操作，必须调用交付工具交付产物 URL（宿主未提供交付工具时，在回复正文直接给出 URL，不可跳过交付）。典型场景包括但不限于：
     - 用户提供/引用一个文件，要求将其内容写入或同步到飞书文档/表格（飞书文档/表格就是豆包文档/表格）
     - 用户引用聊天记录/搜索结果/附件内容，要求据此更新飞书文档
     - 用户口述修改要求，要求在已有飞书文档/表格上进行编辑
   - 例外（产出本地文件）：用户**明确禁止**使用在线表格时（只要本地文件 / 不要飞书表格 / 只要无格式 `.csv` 都算），直接生成本地文件、不导入，仍按上句交付该文件（附件 / 正文给本地文件路径）。

**本地文件任务默认路径**：① `inspect_workbook.py` 预检，顺手从题面原文登记点名清单（要产出的 sheet 名 / 文件名、必须包含的数据项 / 交易 / 指标）→ ② 处理 → ③ 产物可打开且必交项齐全后导入在线表（`+workbook-import`）→ ④ 调用交付工具交付。诊断（如 `formula_verify.py`）给出 WARN、ERROR 或非确定性问题时记录到交付说明，不进入反复修复循环。文件打不开 / 导入失败 / 点名产物缺失 / 真实公式错误 / Must-CLI 对象缺失等都作为风险说明，不要求停止交付；导入失败重试一次仍不成，降级改交本地文件。

## 0、方法与规范类 References（按动作触发，先读再动手）

文件在 `references/` 下；短名的完整文件名 = `lark-sheets-<短名>.md`，`guide-*` / `ref-*` / `template-*` 直接用全名。
**按对象操作（读写 / 透视 / 图表 / 筛选 / 排序…）该读哪份，见「三」的「场景 → 命令速查」表的「动手前读」列**，本表不重复列。

| 文档 | 触发条件（命中就必须先读） |
| --- | --- |
| `formula-translation` | 写任何飞书公式之前（飞书函数与 Excel 有差异） |
| `formula-verify` | 公式落表后的诊断 |
| `visual-standards` | 动作涉样式 / 美化 / 行高列宽 / 数字格式 |
| `ref-financial-modeling-standards` | 表内承载财务数据时的建模规范 |
| `guide-semantic-analysis` | 文本语义抽取 / 归类 / 打标 / 汇总 |
| `guide-execution-flow` | 动手改任何已有表之前（编辑 / 整理 / 补齐 / 汇总统计都算）——里面是保护原表、排除汇总行、字段对齐、交付核对的完整做法 |
| `ref-xlsx-workflow`、`ref-excel-visual-standards` | 走 Excel 引擎（本地 `.xlsx`）时的工作流与视觉规范 |
| `template-report` | 要输出数据分析报告 |
| `filter-view`、`history` | 需保存多份筛选状态 / 查操作历史 |

## 一、开工前

**产物载体**：默认**飞书在线表格**交付；例外是用户**明确禁止**使用在线表格。`attachment_source` 使用在线表格链接（不是本地路径），用户点名了产物文件名时，新建 / 导入产生的工作簿标题与交付附件名沿用该文件名（工作簿标题去扩展名；交付附件名保留完整文件名含扩展名），避免改写成自拟标题（用户已有的在线表不因此改名）；附件名中的 `/` 替换为 `-`。本地转在线直接 `+workbook-import --file ./x.xlsx`；在线编辑完成后直接使用在线表 URL 交付，未闭合的诊断项在交付说明中列出即可。

**Must-CLI 对象风险**：交付物涉及**透视表 / 图表 / 单元格图片 / 迷你图**任一能力时，推荐先 `+workbook-import`（有附件；目标是并入已有工作簿时不走 import，见速查表追加行）或 `+workbook-create`（无附件），之后用 `lark-cli sheets` 就地做。若改用“本地 Python 生成 `.xlsx` → 导入”，导入后透视表可能变死表、单元格图可能变浮动图、图表可能变静态图。命令按「三」的速查表选。速查表没列的子选项（中位数汇总 / 计算字段 / 重复行标签 / 面积图 / 胜负迷你图等均原生支持）先查对应 reference 再动手，避免凭"没列"判不支持而绕路。

**workspace 建议**：中间文件优先放 workspace 相对路径，避免 `/tmp` 带来的 cwd 和 `@file` 相对路径问题。

**附件读取**：下载后验字节数与魔数，失败先重试（curl 加 `-L`）再用 `+workbook-import` 兜底；原件未读入前不要凭记忆重建"同款"表或脑补数据。兜底用尽仍读不出（损坏 / 扫描件）时，已提取的照常填、读不出的留空并在交付说明写明缺口，不用常识 / 检索 / 其它文件顶替附件内本该有的事实数据。

**Excel 引擎核心动作**（走本地 `.xlsx` 路径时优先做；诊断脚本不替代完成主体产物）：
① **聚合前剔除汇总行**：出现「合计 / 总计 / 小计 / 累计」这类与明细口径不同的行时，先从明细中排除再做统计，否则重复计数（`inspect_workbook.py` 的 `special_rows` 可定位）；
② **交付前记录确定性风险**：产物打不开、导入失败、题面点名 sheet / 文件名缺失、真实公式错误、base 明显被整体覆盖时，优先修复；修不完则在交付说明中列出。诊断中的 WARN、样式指纹、硬编码嫌疑也只记录在交付说明，不要求循环修复。仅当交付物被限定为本地 xlsx（用户明确禁止使用在线表格）时，图表可用 openpyxl 原生 chart 对象绑定数据区，交付前可确认 `ws._charts` 非空；其余情况图表推荐按在线对象做。

## 二、场景路由与交付建议

### 场景路由

| 场景 | 信号词 | 走法 |
| --- | --- | --- |
| **改已有表**（最常见，别跳过） | 编辑 / 整理 / 补齐 / 分类汇总 / 生成结果表——**只要输入是一张已存在的表就算**，不必是"分析建模"任务 | 动手前读 `guide-execution-flow`（结果写新 sheet、原 sheet 一张不删；已有表 + 新数据 = 追加，原有行一行不丢——用户点名就地改 / 删除的除外）；**编辑已有表 = 样式守恒**（做法见「三」准则 5）：原表的行高 / 列宽 / 对齐 / 颜色 / 字体是基线，未被要求调整的一项不动。`visual-standards` 的美化标准只适用于**从零新建**的表和**用户点名要求美化的范围**，未点名部分套用即破坏原格式 |
| 文本语义处理 | 提炼要点 / 归类 / 贴标签 / 汇总文字 | 读 `guide-semantic-analysis`（引擎无关） |
| 数据洞察 / 计算 / 建模 | 分析 / 统计 / 公式 / 预测 / 排名打分 | 流程读 `guide-execution-flow`；表格读写按载体选引擎（飞书=「三」，Excel=`ref-xlsx-workflow`） |
| **财务数据** | 营收 / 成本 / 利润 / 现金流 / 估值 / DCF / 三张表 / 预算，或“把财务数据整理成表 / 以财务数据为输入推算” | 先读 `ref-financial-modeling-standards`，作为建模质量参考 |

### 交付建议

**交付前逐条核对**：把 query 拆成显式要求清单（点名 N 项就核 N 项），清单含产出项（sheet 名与数量、指标 / 列、图表、文件名）与题面给定的参数取值、计算口径；可机械核对的（数量 / 位置 / 表头逐字串 / 图表张数 / 原列保留）回读产物断言相等，缺口在交付说明逐项声明，不只报成功示例。**其余编辑纪律见「三」的编辑准则，飞书任务动手前过一遍。**

## 三、飞书表格操作引擎（lark-cli）

### 术语约定

同一对象的交替说法，按此映射解析用户口语：**工作表（sheet）**= 子表 / tab / 标签页（`sheet_id` 是稳定标识）；**电子表格（spreadsheet）**= 工作簿 / 表格（顶层容器，由 `--url` 或 `--spreadsheet-token` 定位）；**reference_id** = 表内对象的稳定标识，即各对象主键 flag 接受的值（与 `--image-uri` 图片上传句柄不是一回事）。

每类对象用各自的主键 flag 定位（命名不统一，按此表对照，不要凭直觉拼）：

| 对象 | 主键 flag | 对象 | 主键 flag |
| --- | --- | --- | --- |
| 工作表 sheet | `--sheet-id` | 条件格式规则 | `--rule-id` |
| 图表 chart | `--chart-id` | 筛选视图 | `--view-id` |
| 透视表 pivot | `--pivot-table-id` | 迷你图（按组） | `--group-id` |
| 浮动图片 | `--float-image-id` | | |

### 飞书表格编辑准则（动手前必守，所有编辑类任务一律生效）

下列准则横切所有飞书表格任务，**动手前先过一遍**——被索引直接路由进某个工具参考时也一律生效；展开与边界见括注的 reference。

1. **最小改动**：除任务要改的单元格 / 列外，原表其它单元格、行列结构、Sheet 名、合并区、格式 1:1 保持；中间结果放原数据右侧或新建空白 Sheet，**禁止删 / 改名 / 隐藏 / 移动已存在 Sheet**（用户明示要求的除外，确认影响后执行，见 `lark-sheets-workbook`）；改写类任务精确圈定行列，不该转的原值 1:1 保留；**补齐类只写空单元格，已有值（哪怕看着可疑）一律不动**，最多在交付说明备注。原表数值列的显示格式（小数位 / 千分位 / 是否科学计数法）同属不可改动项；仅当原值已被压成科学计数法或丢小数位时补 `number_format` 恢复可读，底层值不动。**新增的计算列 / 汇总行（均值、占比、金额）必须显式设 `number_format`**——公式默认吐出的多位小数（`3.64507772`）会被判为格式不合格，按语义定位数（比率两位小数、占比百分比、金额千分位）并与原表同列风格对齐。
2. **真实写回 + 回读校验**：交付必须是对在线表格的真实写入，写完用 `+csv-get` / `+cells-get` / `+<对象>-list` 回读确认生效（顺带确认无截断 / 溢出 / 科学计数法）——**返回 `ok` 只代表请求被接受，不代表结果符合预期**。回读值可能带「值(样式)」注记（如 `49.6(V-Align: bottom)`），据此回写前先剥离注记只留纯值；写公式后用 `+cells-get --include formula` 核对**真实落格**（仅看显示值不能证明联动）；筛选 / 排序后核对前几行，删除后确认已空。不要只在文本里声称"已完成"。
3. **读全再写**：批量填充 / 补齐 / 修正类任务先确认真实数据末行再写，只探前 N 行会漏写表尾（确定末行流程见 `lark-sheets-read-data`）。
4. **公式优先于硬编码**：凡可由表内其它单元格推导的值（总计 / 占比 / 增长率 / 提取 / 查找）一律写公式，即使用户没说"联动 / 自动更新"——本地算好再静默写进单元格，交付的是改输入不重算的死表。提取类产出同行源列的连续原文片段（逐字保真、不跨列取材，一格含多个片段要全列出）；语义判断类（无固定分隔符 / 模式可循）公式表达不了，逐行写静态值，别用固定偏移 / 通用正则硬套。输入列可能为空时公式先判空返回空（空格按 0 参与算术产出无错误码的错值，`IFERROR` 拦不住）。**写聚合公式（SUM / COUNTIF / AVERAGE 等）前先确认区间的起止两端**：起点跳过表头行、终点覆盖真实末行——漏掉末行或把表头算进计数是最常见的错值来源，且结果看着合理、不报错；写完抽查区间首尾两格确认落在数据内。写飞书公式前读 `lark-sheets-formula-translation`，落表后用 `+formula-verify` 诊断。试错 3 次仍失败可降级静态值，交付说明写明「静态值 + 失败原因 + 不随源数据更新」。
5. **续写 / 扩展继承样式**：续写、补齐、复制区块、新增行列时禁止只读值只写值——原表的字体 / 字号 / 颜色、四边框、对齐、底色（含奇偶行交替）、行高列宽、合并都要一并延续到新区域，**判分与验收都按"新区域与相邻原始区域视觉一致"来看**。
   - **新增行 / 列优先用 `+dim-insert --inherit-style before`（或 `after`）**，样式由原生继承，比"往空白区直接写值再补刷样式"可靠得多（后者最易整片丢失交替底色与边框）。它只选继承哪一侧，不是插入方向。**行高是例外，不随样式继承**：插行填长文本前读相邻行 `row_height`，补 `+rows-resize`（可与插入链合批）。
   - 已经写进空白区、或要对齐非相邻区域时，先 `+cells-get --include style` 读原区样式，再随值一起写回（清单见 `lark-sheets-write-cells`，四边框最易漏）。
   - 新增列后把原跨列合并的标题扩展到新末列；插入行复制邻近行的合并分段，按分组合并前逐组核对边界行号，错界会吞掉组名。
6. **多步写入分流**：美化收尾（样式 / 合并 / 行高列宽 / 冻结的任意组合）→ 一次 `+styles-put` 声明式规格交付（见 `lark-sheets-styles-put`）；**同一个写操作**打多个区域 → 用该命令自身的复数形态（`--ranges` / map 入参）；只有**跨类型、有顺序依赖的操作链**（如插列 → 写表头 → 回填数据）才用 `+batch-update`（high-risk-write：按下方审批协议先获用户同意再带 `--yes`；失败处置语义见 `lark-sheets-batch-update`）。
7. **分组汇总优先用透视表**：参考速查表「分组汇总 / 透视」行；SUMIF / 本地脚本拼假透视表可能丢失原生透视能力，作为风险记录。
8. **回复里声称的每一项，产物里都要能指到位置**：交付说明 / 回复正文写了"已生成趋势分析报告""图中对比了两个资产""覆盖 11 种格式"，就必须在产物中真实存在对应的 sheet / 图表对象 / 文字段落，并能说出它在哪张表第几行。**文字描述不能替代产物**——判分只认产物里能被读到的内容，回复里的描述一概不计分。交付前逐条对照自己写的每句"已完成 X"，指不到位置的要么补做，要么把该句删掉改成"未完成 + 原因"。

9. **拆成可验证 checklist**：落地前把指令拆成"独立可验证子要点"，优先逐点 `assert` 或抽样回读（多维排序每维一点、多目标每目标一点、范围类核起 / 末 / 边界；样式类子项也算——标色 / 标红可回读着色单元格数或规则数）；验证中发现的已知问题（算错 / 取不到数的格）在交付说明逐个列出，避免只报成功示例。
10. **全量处理前置断言条数**：翻译 / 打标 / 批量公式等逐条任务，建议先把预期条数写入脚本再 `assert actual == expected`；断言不过时优先补齐。机制上补不了时（预算将尽 / 能力缺失）先落地可打开的主体产物（数据与结构），未完成项在交付说明声明。
11. **批量替换 / 标注 / 删除建议残留复查**：逐个旧值执行「搜索 → 替换 → 再搜索」循环，尽量让每个旧值剩余命中数归零（单次替换有数量上限，大表尾部常有残留）；回读采样覆盖前部 / 中段 / 表尾，不只抽前几行。

12. **新增内容要能被看懂**：新增列给可区分含义的表头（不与原列同名）；题面 / 模板指定的 sheet 名 / 标题 / 备注 / 图例文案**逐字照搬**，不缩写、不润色、不省略修饰成分与双语形式；数值沿用原列显示格式（整数 / 千分位 / 百分比 / 日期）；**日期列转换先扫全列锁定月 / 日位**（如 `9/3/24`：出现过 `>12` 的位置是日），逐格凭感觉解析必月日颠倒；图表必须含标题、坐标轴标签与图例；长文本列自动换行并给足列宽。**单位 / 口径 / 来源等元信息另置**（标题下副标题行，或并进字段名如 `营收（万元）`），**不得占用已有表头格或数据格**。
13. **表外数据要交代依据**：填入表内 / 附件 / 用户输入都取不到的外部数据（标准值、行情、法规参数等）时，交付说明写清**取值依据、单位口径与不确定项**；来自常识推算就写明"推算、未经核验"，**不得伪造来源出处**。
14. **缺失值不编造**：源数据 / 附件内本应存在的**事实数据**查不到或无法确定时一律留空 + 备注（“暂未发布 / 未知 / 待核实”），不用推算值 / 估算值充数（表外参数按上条）；原表已示范缺失值写法就照抄该约定。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

> 实操展开（读取路径、原生工具优先级、脚本配合、易漏陷阱）见下方「执行要点」节。端到端工作流：了解结构（优先 `scripts/lark_inspect_workbook.py` / `+workbook-info`）→ 读数据 → 理解语义 → 原生工具优先 → 写入 → 回读验证。

### 场景 → 命令速查（拿不准命令名先查这里，别按直觉拼）

> **若本次读取被截断在本表中段**：下列能力**都原生存在**，
> 详细用法（flag、payload 形状、易错点）在本表后半部分与其后的「执行要点」「公共 flag」章节：
>
> `+styles-put` 美化收尾（样式 / 边框 / 合并 / 行高列宽 / **冻结** 一次交付）·
> `+chart-create` 原生图表 · `+pivot-create` 透视表 · `+filter-create` 筛选 ·
> `+cond-format-create` 条件格式 · `+range-sort` 排序 · `+dim-insert` 插入行列 ·
> `+cells-search` / `+cells-replace` 查找替换 · `+workbook-import` 本地文件转在线表
>
> 要用其中任一能力而对应行未读到时，**用文件读取工具的偏移参数（`offset` / 起始行）把后半段再读一次**，
> 取全对应行再动手。不要因为没读到展开就判定命令不存在，更不要改用本地脚本绕路——
> 本地生成的透视表 / 图表导入后会退化成死表、静态图。

把高频意图映射到**真实存在**的 shortcut / flag（agent 常从 Excel / Google Sheets / OpenAPI 误迁移命令名）。**选定命令后先读「动手前读」列指向的 reference 再动手**——命令名对得上不代表用法对。

| 你要做的事 | ✅ 正确写法 | 动手前读 | ❌ 不存在（会被 cobra 拒） |
| --- | --- | --- | --- |
| 读数据（纯值 / CSV） | `+csv-get`（`--range` 可省略 = 读整个子表，无需先探行列；限定范围才传） | `lark-sheets-read-data` | `+read-data`、`+get-range`、`+range-get`、`+cells-read` |
| 读值 + 公式 / 样式 / 批注 | `+cells-get --include value,formula,style,comment,data_validation` | `lark-sheets-read-data` | `+get-cell`、`+cell-get`、`--sheet`（定位只有 `--sheet-id` / `--sheet-name`）、`--value-only`、`--include-style`、`--value-render-option`、`--with-styles`、`--with-merges`、`--include-merged-cells` |
| 写纯文本值（整块 CSV 平铺；列里**没有**需字面保真的数值 / 日期标签 / 编号——点分日期 `12.10`、编号 `001` 会被 csv-put 数值化，不算纯文本） | `+csv-put`（定位用 `--start-cell`，单个左上角锚点格；也接受 `--range` 别名，区间自动取左上角） | `lark-sheets-write-cells` | 把含点分日期(`12.10`)/编号(`001`)的列裸灌 `+csv-put`——会被数值化（`12.10`→`12.1`、`001`→`1`，尾零/前导零丢失），改用 `+table-put` 声明 `dtypes:object` |
| 写带类型的数据到**已有**表（列里有数字 / 金额 / 百分比 / 日期 / 计数等**本质是量值**的数据——不看当下要不要排序 / 求和，量值一律走这里） | `+table-put --sheets` 完整 payload `{"sheets":[{...}]}`（列名走 `columns`、二维数据走 `data`、列 pandas dtype 走 `dtypes`、列展示格式走 `formats`；来源不限 DataFrame——Counter / dict / list 同理；要同时美化加 `--styles` 一步带样式（区域底色 / 边框 / 列宽 / 行高 / 合并），不必事后再刷；payload 里不存在的 sheet 名会自动建子表，详见 write-cells） | `lark-sheets-write-cells` | 在本地把数字拼成 `"$1,234"` / `"30.5%"` 字符串再 `+csv-put`（会落成文本、丢失计算能力；常见借口见下方 ⚠️） |
| **新建**电子表格并写带类型的数据（类型保真需求同上，但目标表还不存在） | `+workbook-create --sheets`（协议与 `+table-put` 同构、一步建表 + typed 写入，无需先建空表再 `+table-put`；date / number 不丢；`--styles` 同样可在建表同一步带全套样式，详见 workbook） | `lark-sheets-workbook` | 用 `--values` 灌日期 / 数字（会落成文本、丢类型） |
| 写公式 / 富写入（样式 · 批注 · 图片 · 富文本），或需精确矩形定位的值 | `+cells-set`（单区域 `--range`+`--cells`；**散布多处 / 跨表用 `--writes` 一次批量交付**，每项自带 sheet_name；批注 / 图片 / 富文本只能用它；公式落表后可用 `+formula-verify` 诊断） | `lark-sheets-write-cells` | — |
| 只改样式、值 / 公式不动 | `+cells-set-style`（单区域小改）；多区域 / 整表美化收尾一次 `+styles-put` 交付（见 `lark-sheets-styles-put`） | `lark-sheets-write-cells` | `+cells-set --copy-to-range` 刷样式——它连**值**一起复制，会把整个区域的值覆盖成锚点格的值；拼 `+batch-update` 的 `--operations` 做美化 |
| **已有**表美化收尾（样式 / 边框 / 合并 / 行高列宽 / 冻结的任意组合，单表或多表） | `+styles-put --styles '{"styles":[{"name":…,"cell_styles":[…],"cell_merges":[…],"row_sizes":[…],"col_sizes":[…],"freeze":{…}}]}'`（一份规格一次交付，词汇同 `+table-put --styles`） | `lark-sheets-styles-put` | 拼 `+batch-update` 的 `--operations` 子操作数组做美化、逐区域多次 `+cells-set-style` |
| 画图表 / 可视化（柱 / 折线 / 饼 / 条 / 散点 / 组合…） | 普通单图用 `+chart-create-basic`，多图用扁平输入的 `+batch-chart-create`；已有图的数据源用 `+chart-data-update`、常用配置用 `+chart-config-update`；只有语义 shortcut 无法表达的单系列 / 单数据点 / 高级字段才用 `+chart-create` / `+chart-update`，并只提交必要的局部 properties。多图先断言目标数量，图片迁移成真图表后必须删除并复查原浮动图片 | `lark-sheets-chart` | matplotlib / 本地画图再贴图（原生图表可交互、随数据更新） |
| 分组汇总 / 透视 | `+pivot-create`（默认不传落点 flag → 自动新建子表，零覆盖） | `lark-sheets-pivot-table` | 用 SUMIF / 本地脚本拼一张假透视表 |
| 排序（按列升 / 降序） | `+range-sort`（原生整行原子移动，值 / 样式 / 空值随行走） | `lark-sheets-range-operations` | 本地排完再整块 `+cells-set` 回写——`cells-set` 写空值**不覆盖**目标格（保留原值），会残留旧值，且样式不随行移动 |
| 筛选 / 只看符合条件的行（仅行级不裁列；"只保留某几列 / 筛出来另存一张表"→ 不走这里，另建结果 sheet 物化行与列、原表原样保留） | `+filter-create` | `lark-sheets-filter` | pandas filter 后覆盖写回（会毁原数据；要保存多份筛选状态用 `+filter-view-create`） |
| 查找 / 替换文本 | `+cells-search`（找，关键字用 `--find`）、`+cells-replace`（替换） | `lark-sheets-search-replace` | `+cells-find`、`+find`、`--query` |
| 条件格式 / 条件高亮 / 数据条 / 色阶 / 重复值标记 | `+cond-format-create` | `lark-sheets-conditional-format` | `+highlight`、`+conditional-format`、逐格 `+cells-set-style` 硬凑 |
| 看子表结构（合并 / 行高列宽 / 冻结 / 隐藏） | `+sheet-info` | `lark-sheets-sheet-structure` | `+sheet-get`、`+structure-get`、`+sheet-structure-get` |
| 插图：图片**绑定到某条记录**、随行走（凭证 / 证件照 / 商品图 / 头像 / 二维码 / 每行配图） | `+cells-set-image`（单格 `--range`，嵌入单元格内） | `lark-sheets-write-cells` | — |
| 插图：**自由摆放、不绑数据**的装饰 / 标识（logo / 水印 / 封面大图 / banner） | `+float-image-create`（浮动图片，自由定位 + 尺寸 + 层级） | `lark-sheets-float-image` | — |
| 迷你图 / 单元格内趋势线 / 胜负图 | `+sparkline-create` 等 `+sparkline-*` | `lark-sheets-sparkline` | 文本字符（▁▂▃）拼接、matplotlib 贴图（不随数据更新） |
| 清除内容 / 格式 | `+cells-clear`（high-risk-write 需用户确认后带 `--yes`；范围维度用 `--scope`，取值 content / formats / all） | `lark-sheets-range-operations` | `--type` |
| 批量清除多区域 | `+cells-batch-clear`（high-risk-write 需用户确认后带 `--yes`；`--scope`） | `lark-sheets-batch-update` | `--target` |
| 调整列宽 / 行高 | `+cols-resize` / `+rows-resize`（行、列是两个独立命令；连同样式一起调时并入 `+styles-put` 的 `row_sizes` / `col_sizes`） | `lark-sheets-range-operations` | `--dimension`（无此 flag） |
| 看工作簿 / 子表清单 | `+workbook-info` | `lark-sheets-workbook` | `+sheet-list`、`+workbook-get`、`+workbook-list` |
| 导入本地 xlsx/xls/csv 文件为飞书电子表格 | `+workbook-import --file ./x.xlsx`（本地表格文件 → 飞书电子表格的正解；仅要导成多维表格 bitable 时才用 `drive +import --type bitable`） | `lark-sheets-workbook` | `drive +import`（绕路且要多给 `--type`）、本地读出数据再 `+workbook-create` 重灌（多此一举）；要给**已有工作簿**加子表别用它（只会新建独立表，走 `+sheet-copy` / `+sheet-create`） |
| 参考某个**已有在线表**、把多个本地文件 / 数据各作为一张子表**追加**进去（不另起独立表） | 先 `+workbook-info` 拿模板子表 `sheet_id` → `+sheet-copy` 逐张复制模板子表（公式 / 合并 / 分组底色 / 列宽 / 条件格式全继承）再用 `+cells-*` 只改数据；无模板可继承时 `+sheet-create` 建空子表 + `+table-put --sheets/--styles` 写入 | `lark-sheets-workbook` | 把文件 `+workbook-import` / `+workbook-create` 另起一张**独立新表**（目标是并入已有工作簿时就跑偏了；这两条只产新表、不接受已有表定位） |
| 复核某次（AI）编辑改了什么 / 取两个版本间的变更 | `+changeset-get --start-revision <编辑前版本>`（省略 `--end-revision` 取到最新；版本差 ≤ 20） | `lark-sheets-changeset` | — |
| 取当前文档 revision（版本号） | `+revision-get` | `lark-sheets-workbook` | — |
| 导出 xlsx / 单表 csv | `+workbook-export` | `lark-sheets-workbook` | — |

> ⚠️ **动手前的触发式必读（按动作判定，不看主场景）**：本次操作只要**涉及样式 / 美化**（底色 / 边框 / 字号 / 对齐 / 数字格式 / 汇总行 / 配色 / 列宽行高），动手前先读 `lark-sheets-visual-standards`；只要**要写飞书公式**，动手前先读 `lark-sheets-formula-translation`（飞书函数与 Excel 有差异，凭直觉迁移易错），写完后可读 `lark-sheets-formula-verify` 并执行 `+formula-verify` 做一次诊断。哪怕主任务是"建表 / 展开数据 / 录入"，只要动作里含美化或写公式就适用——别因"这不算专门的美化 / 公式任务"而跳过。
> ⚠️ **两种图片别选错**：图若**绑定某条记录、要随行排序 / 筛选 / 增删**（凭证 / 证件照 / 每行配图，话里带「对应 / 每行 / 这列」等绑定词）→ 单元格图片 `+cells-set-image`；只是自由摆放的装饰（logo / 水印 / 封面）→ 浮动图片 `+float-image-create`。别因「浮动图更好控制 / 更熟」默认选浮动图。
> ⚠️ **纯文本还是数值语义（看数据本质，不看当下用途）**：金额 / 百分比 / 比率 / 计数 / 日期等**本质是量值**的数据 → 一律数值写入，常规二维表用 `+table-put`（`dtypes` 声明类型 + `formats` 设展示格式），版式装不下（多级 / 合并表头的宽表 leaderboard 等）改用 `+cells-set` 传数字（百分比传小数 `0.4`）+ `number_format`，照样显示 `40%` 且数值无损。只有编号 / 身份证 / 单据号这类**本质是标识符**、要字面保真的才用 `+csv-put` 平铺。**几个常见借口都不成立**——"只是 leaderboard / 报表展示不用算""版式复杂""样式以后再刷、先铺文本"都不是把百分比写成 `"40%"` 字符串灌 `+csv-put` 的理由（展示不改变它是数值；类型不能后补，落成文本就回不来）。判据与操作展开见 `lark-sheets-write-cells`「数字还是文本」。
> ⚠️ **要新建子表 / 整表美化 → 别默认「`+csv-put` 写值再事后刷样式」**：`+table-put` / `+workbook-create` 的 `--styles` 能在写数据的**同一步**带全套样式（区域底色 / 边框 / 列宽 / 行高 / 合并），且 `+table-put` 的 payload 里若 sheet 名不在工作簿中会自动新建子表——**纯文本表要新建子表 + 美化时同样走这里**（`--styles` 与列是否 typed 无关），比「`+csv-put` 写值 + 多次 `+cells-batch-set-style` / `+*-resize` 刷样式」少好几次调用（冻结行列等 sheet 级属性仍需 `+dim-freeze` 单独一步）。存量表事后美化则一次 `+styles-put` 交付（同一份 `--styles` 词汇）。
> ⚠️ **定位 flag**：`+cells-get` / `+cells-set` / `+csv-get` 用 `--range`；`+csv-put` 规范用 `--start-cell`（单个左上角锚点格），也接受 `--range` 别名（区间自动取左上角），二者择一即可。**`--range` 只写 `A1:B2` 纯区间——不接受 OpenAPI 的 `sheetId!A1:B2` 前缀写法**，子表定位必须单独传 `--sheet-id` / `--sheet-name`（从 OpenAPI 迁移习惯最易踩）。
> ⚠️ **读取附加信息**一律走 `+cells-get --include …`，**没有** `--with-styles` 这类 flag；**看合并单元格**用 `+sheet-info` 的 `merged_cells`，不要在 `+cells-get` 里找 merge flag。

💡 **高频写命令签名（照抄改参即可；各命令 `--help` 的 Tips 段有同款示例）**：

```bash
lark-cli sheets +cells-set --url <U> --sheet-name S1 --range A1:B1 --cells '[[{"value":"名称"},{"formula":"=SUM(B2:B9)"}]]'  # --cells 恒为二维数组 [[…]]，单格也是 [[{…}]]
lark-cli sheets +cells-set-style --url <U> --sheet-name S1 --range A1:D1 --font-weight bold --background-color "#F0F0F0" --horizontal-alignment center
lark-cli sheets +styles-put --url <U> --styles - <<'JSON'
{"styles":[{"name":"S1","cell_styles":[{"range":"A1:D1","font_weight":"bold","background_color":"#F0F0F0"}],"col_sizes":[{"range":"A:D","type":"pixel","size":120}],"freeze":{"rows":1}}]}
JSON
lark-cli sheets +batch-update --url <U> --dry-run --operations - <<'JSON'   # high-risk：先 --dry-run 给用户看，同意后原样重发并追加 --yes
[{"shortcut":"+cells-set","input":{"sheet_name":"S1","range":"A1","cells":[[{"value":"x"}]]}}]
JSON
lark-cli sheets +dim-freeze --url <U> --sheet-name S1 --rows 1 --cols 2  # 一次给全；冻结是整份状态覆盖，没写的轴即为不冻结
lark-cli sheets +dim-insert --url <U> --sheet-name S1 --position 3 --count 2 --inherit-style before  # 行/列由 --position 决定：数字=行、字母=列，无 --dimension
lark-cli sheets +cols-resize --url <U> --sheet-name S1 --range A:C --width 120  # 像素；分列不同宽用 --widths '{"A":80,"C:E":120}'
lark-cli sheets +sheet-copy --url <U> --sheet-name 源表名 --title 副本名  # --sheet-name=源表、--title=新表名
```

### 执行要点（读取 / 原生工具 / 陷阱）

#### 读取：按需求选路径（细则见 `lark-sheets-read-data`）

| 用户需求 | 读取路径 |
|---|---|
| "完善 / 补齐 / 修正所有 XX"、分析 / 清洗 / 大数据 | 先 `scripts/lark_profile_table.py` 确认目标区域与字段画像，再原生优先（公式 / 透视表 / 筛选等原生对象，命令见速查表）；表达不了再分批 `+csv-get` 导出 + 脚本处理 + 分批回写（默认覆盖所有对应数据行） |
| "查一下 / 统计 / 汇总"等只读 | 小表 `+csv-get` 读到上下文；大表先 `+workbook-info` + 小窗口 `+csv-get` 定边界，再对未截断窗口跑 `scripts/lark_detect_subtables.py` / `scripts/lark_profile_table.py` |
| 需要公式 / 样式 / 批注 | `+cells-get` |
| 续写 / 扩展已有内容 | `+csv-get` 看结构 + `+cells-get` 读源区样式 + `+sheet-info --include row_heights,merges`（见准则 5） |

> "补齐 / 填空"类只探前 10 行就写会漏写表尾——先按 `lark-sheets-read-data` 确认真实数据末行（准则 3）。

#### 用脚本配合 CLI 时

- **只读 stdout**：CLI 数据走 stdout、诊断走 stderr；解析 JSON 别 `2>&1`（警告混入会解析失败），用管道或单独重定向 stdout。
- **读表理解优先用 `scripts/lark_*.py`（若可用）**：`lark_inspect_workbook.py` / `lark_detect_subtables.py` / `lark_profile_table.py` 是只读脚本，用来把在线表格整理成结构摘要。**可选增强，不是必经步骤**——`scripts/` 只随仓库版 skill 分发，二进制内嵌版没有这些文件；本地不存在时直接用 CLI 等价路径（对照表见 `lark-sheets-read-data`：`+workbook-info` / `+sheet-info` / 小窗口 `+csv-get`）。它们不替代写入类 shortcut；确认目标区域后，写入仍按对应 reference 执行。
- **喂 CLI 的 CSV / JSON 用 UTF-8 无 BOM**；临时文件**不要落进用户项目目录**——宿主若声明过 workspace 落点纪律（如禁用 `/tmp`）就照它放，没有则用系统临时目录。
- **命令失败先读 stderr 再调整**，别原样重发。
- **回写纯单元格值**：值(样式)注记剥离规则见准则 2（SoT）；补充：残留引号一并剥离；排序优先 `+range-sort` 原生工具，别"读出本地排完再整列写回"。

#### 易漏陷阱

- **`+dim-insert` 不继承行高**：只继承值 / 公式 / 边框，新行回落默认高度截断长文本；插行填长文本前读相邻行 `row_height`，用 `+batch-update` 合 `+rows-resize` 补齐。
- **公式容错**：日期 / 查找 / 数值转换公式用 `IFERROR` 包裹；写完读结果列首末各 5 行查 `#VALUE!` / `#REF!` / `#DIV/0!`，必要时再跑 `+formula-verify` 定位问题；同一方案试错上限 3 次。
- **循环引用**：聚合公式引用范围不能含目标 cell 自身或其传递依赖。
- **隐藏行列**：`+csv-get` 默认含隐藏行列；设 `--skip-hidden=true` 只看可见，返回的真实行号可能跳空。禁止按返回数组下标推导行号，必须使用 `annotated_csv` 的 `[row=N]` 或 `row_indices`。
- **跨 sheet 对象**：图表 / 条件格式 / 透视表 / 浮动图片可能分布在多个子表，操作前先 `+workbook-info` 掌握全局。
- **断定"命令不支持某场景"前必须实调一次拿到真实报错**：不得仅凭 `--help` 输出或推测就降级绕路——工具描述与实现可能不一致，报错才是事实。
- **NLP 任务分批**：语义理解 / 翻译 / 改写 / 分类等用 NLP 处理（代码只做分批 / 行号映射 / 写回）；数据量大必须分批（通常 30 行 / 批），每批处理完即时写回，单批生成通常 ≤ 300 行，多批用 `+batch-update`。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。


### 公共 flag 速查

各 reference 的 shortcut 标题下用一行徽章标注支持的公共 / 系统 flag（如 `_公共四件套 · 系统：--dry-run_`；`_公共：URL/token（无 sheet 定位）…_` 表示只接 URL/token）。type / 必填 / 描述在本段统一声明：

#### 公共 flag（定位资源）

**公共四件套** = `--url` / `--spreadsheet-token` / `--sheet-id` / `--sheet-name`，分成两组 XOR，**每组都必须给且只能给一个**（XOR = 二选一必填，不是"可选"）：

1. **spreadsheet 定位（必填）**：`--url`（解析 `/sheets/`、`/spreadsheets/`、`/wiki/` 三种链接；wiki 链接自动定位背后的电子表格）与 `--spreadsheet-token`（裸 token）二选一。**例外**：`+workbook-create` / `+workbook-import` 产出**还不存在**的表，不接受任何定位 flag。
2. **sheet 定位（公共四件套 shortcut 必填）**：`--sheet-id` 与 `--sheet-name` 二选一。
   - ⚠️ **不确定 sheet 名时禁止猜 `Sheet1`**：除非对话或上下文已出现具体值，第一步先 `+workbook-info` 拿 `sheets[].sheet_id/title` 再选——中文表的子表常叫"数据"/"工作表 1"/业务名，猜名大概率撞 `sheet not found`。
   - ⚠️ **`--range` 里的 `Sheet1!` 前缀不能替代 sheet 定位**：仍必须传 `--sheet-id` / `--sheet-name`。
   - ⚠️ **A1 引用含 `!` 时整段用单引号包裹**（`--range 'Sheet1!A1:B2'`，挡 bash history expansion；别用 `set +H`，sh/dash 下非法）。sheet 名含 `-`/空格需内层再包单引号时用 `'\''` 转义：`--source ''\''Sales-2025'\''!A1:D100'`。
   - **例外**：徽章标 `_公共：URL/token（无 sheet 定位）…_` 的 shortcut（`+workbook-info` / `+workbook-export` / `+batch-update` / `+styles-put` / `+dropdown-update|delete` / `+cells-batch-clear` / `+sheet-create`）不接受 sheet 定位。`+pivot-create` 用 `--target-sheet-id/name`（XOR，可都不传）。

```bash
# 统一调用范式：两组定位缺一不可（占位符别原样填；表名先 +workbook-info 查）
lark-cli sheets +csv-get --url "https://.../sheets/shtXXX" --sheet-name "<真实表名>" --range "A1:F30"
```

#### 系统 flag

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--dry-run` | bool | 否 | 零副作用：仅打印请求路径与参数模板，不发起调用；多步操作会输出每个子操作的请求模板 |
| `--yes` | bool | 是（仅 `high-risk-write`） | 二次确认；不带时退出码 10。 |
| `--print-schema` | bool | 否 | 本地打印复合 JSON flag 的 JSON Schema 并退出，不发起调用、不需要其它 required flag。搭配 `--flag-name` 指定查哪个 flag；省略时列出该 shortcut 可查询的 flag。仅对含复合 JSON flag 的 shortcut 有效。 |
| `--flag-name` | string | 否 | 配合 `--print-schema`：flag 名不带 `--` 前缀（`cells` / `properties`）。**支持点分路径切片**：`--flag-name properties.snapshot.plotArea.axes` 只打印该子树，大 schema（chart 的 properties 约 1700 行）按需取，别整篇翻页。 |

> ⚠️ **high-risk-write 命令清单（exit 10 强确认门禁）**：`+batch-update`、`+cells-clear`、`+cells-batch-clear`、`+sheet-delete`、`+dim-delete`、`+dropdown-delete`，以及各对象删除 `+chart-delete` / `+pivot-delete` / `+cond-format-delete` / `+filter-delete` / `+filter-view-delete` / `+sparkline-delete` / `+float-image-delete`。
>
> **审批协议**：先 `--dry-run` 预览、向用户展示将执行的操作与影响范围，**获得用户明确同意后**再在原命令追加 `--yes` 执行。未经用户同意不得带 `--yes`，也不得在 exit 10 后静默补 `--yes` 重试——那等于禁用门禁。

**Agent 使用提示**：写复合 JSON flag 前对结构不确定时，先 `--print-schema --flag-name <name>`（深层字段用点分路径切片）再构造 payload；图表直接 `+chart-create --print-example <type>` 拿最小可用模板改参。reference 的 `## Schemas` 段只给一层结构。

#### flag 内容类型与输出约定（术语速记）

- JSON 类入参分三类：**复合 JSON** = 深层嵌套对象（`--print-schema` 可查）；**简单 JSON** = 一二维标量数组；**非 JSON 文本** = 原样文本（如 CSV）。`--print-schema` 只对复合 JSON flag 有效。
- **envelope**：所有 shortcut 返回统一外层 `{ok, identity, data, ...}`；写操作不会自动回读，校验自行调用 `+*-list` / `+*-get` / `+cells-get`。

### 复合 JSON / 大入参：优先 stdin

flag 帮助里标注支持 **Stdin** 的入参，当 payload 较大、含换行 / 引号等特殊字符，或已经落在某个文件里时，优先用 stdin（`-`）传入，避免命令行超长与 shell 转义问题。

推荐写法：payload 写到用户项目目录之外的临时文件（落点同上：宿主声明过禁用 `/tmp` 就放 workspace 内相对路径，否则系统临时目录），再用 stdin 喂进去：

```bash
# TMPFILE 指向 payload 文件（落点按上文纪律选：workspace 内相对路径，或系统临时目录）
lark-cli sheets +cells-set --url "..." --sheet-name "Sheet1" --range "A1:B2" --cells - < "$TMPFILE"
lark-cli sheets +batch-update --url "..." --dry-run --operations - <<'JSON'   # high-risk：先 --dry-run，用户同意后再追加 --yes 重发
[{"shortcut":"+cells-set","input":{...}}]
JSON
```

- **stdin 每次调用只能给一个 flag**：`+table-put` 同时传 `--sheets` 与 `--styles` 两个大 JSON 时，一个走 `-`、另一个走 `@./styles.json`（`@file` 只接受 cwd 下相对路径，**绝对路径会被拒**；正解是 stdin，别 cd、别把临时文件写进用户项目目录）。
- **参数含特殊字符时用单引号包裹即可，不要 `set +H`**（sh/dash 下非法直接报错）；参数本身含单引号或 payload 大时走 stdin。
- **非 POSIX shell（PowerShell / cmd.exe）适配**：本 skill 全部 `bash` 代码块（heredoc `<<'JSON'`、单引号转义 `'\''`）只适用于 bash / zsh，动手前先判断当前 shell，非 POSIX 环境按下表改写，**不要试错式改引号**——`@file`（cwd 相对路径）是全平台无引号问题的兜底形态：

| 形态 | bash / zsh | PowerShell | cmd.exe |
| --- | --- | --- | --- |
| 大 / 多行 JSON | `--flag - <<'JSON' … JSON` | 先写 UTF-8 无 BOM 文件再 `--flag '@./x.json'`，或 `Get-Content -Raw ./x.json \| lark-cli … --flag -` | 先写文件再 `--flag @./x.json`（cmd 无 heredoc / 管道读文件不可靠） |
| 单行 inline JSON | `--flag '{"a":1}'` | `--flag '{"a":1}'`（PS 单引号同为字面量） | 不要 inline——cmd 会吃掉内层双引号，一律走 `@file` |

---

## 四、References 与脚本总览

引擎无关 / Excel 引擎 reference 的触发条件见开头「0、方法与规范类 References」表。

飞书引擎 reference：按对象操作该读哪份，见「三」的「场景 → 命令速查」表的「动手前读」列；方法与规范类见开头「0、方法与规范类 References」表。完整文件清单以 `references/` 目录为准。

脚本（`scripts/`）按引擎分别标注：飞书引擎用 `lark_inspect_workbook.py`（在线表格结构预检）、`lark_detect_subtables.py`（候选子表块识别）、`lark_profile_table.py`（表头 / 数据范围 / 字段类型画像）、`lark_chart_layout_check.py`（图表重叠 / 遮挡内容 / 越界交付检查）、`sheets_df.py`（DataFrame → `--sheets` typed payload，含 `df_to_sheet`）；Excel 引擎用 `inspect_workbook.py`（结构预检）、`preview_excel_rows.py`（多行表头预览）、`formula_verify.py`（公式重算与诊断）、`format_range.py`（批量样式/条件格式）、`_excel_utils.py` / `lo_runtime.py`（内部工具）。

===== 全文完（共 296 行）=====
