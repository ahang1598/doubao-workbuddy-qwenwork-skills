---
name: lark-sheets
version: 3.1.2
description: "表格全场景处理：本地 Excel/CSV 与在线表格（飞书、doubao.com 的 /sheets/ 链接）的创建、读写、分析、计算、建模、语义处理、可视化与美化。**只要用户输入包含表格类附件——上传 .xlsx/.xls/.csv 文件，或给出 feishu/doubao.com 的 /sheets/ 链接或 token——必须加载本技能。** 此外，用户口述数据要整理成表，或要求计算/统计/建模/预测/透视/可视化/美化/公式等任何表格操作时，也加载本技能。一切与 Excel/表格相关的任务都必须加载。本技能不负责获取外部信息，如需补充数据须先通过其他途径获得。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "lark-cli sheets --help"
---
> ⚠️ **先读完再动手**：本文档共 454 行，单次 Read 读不完；没见到末行「全文完」标记＝没读完，必须调整 offset 续读直到该标记。本技能所有文档（含 references）末行均有此标记。

# 表格全场景处理技能（lark-sheets）

本技能统一处理两类表格，**一套场景方法论、两套执行引擎**：

| 引擎 | 适用对象 | 工具 |
| --- | --- | --- |
| **Excel 引擎** | 本地 `.xlsx` / `.xls` / `.csv` 文件 | Python（pandas / openpyxl）+ `scripts/` 下脚本 |
| **飞书引擎** | 飞书在线表格、doubao.com 的 `/sheets/` 链接 | `lark-cli sheets`（详见「三」） |

两套引擎通过 `lark-cli sheets +workbook-import` 打通：本地 Excel 可一键导入为飞书在线表格。

---

## 0、开工前：先定「输入来源」与「产物载体」

任何表格任务，先回答两个问题：数据从哪来（输入）、产物以什么形式交付（载体）。这决定走哪套引擎。

### 0.1 识别输入来源

| 输入信号 | 来源判定 | 走哪套引擎 |
| --- | --- | --- |
| 用户上传 `.xlsx` / `.xls` / `.csv` 文件 | 本地 Excel/CSV | Excel 引擎；默认导入为飞书表格交付，见 0.2 |
| 用户给出飞书 / doubao 的 `/sheets/` 链接或 token | 飞书在线表格 | 飞书引擎（「三」） |
| 用户口述 / 粘贴数据，无文件 | 待结构化 | 先结构化，再按产物载体（0.2）选引擎 |
| 无数据 | 信息不足 | 向用户询问，或先用其它工具获取数据 |

> ⚠️ **doubao.com 的 `/sheets/` 链接也走飞书引擎**：路由依据是 URL 路径模式（`/sheets/`）和 token，而不是域名。不要因为域名不是飞书就回退到 WebFetch。

### 0.2 表格产物载体决策与导入（默认飞书在线表格）

> **核心策略，优先级高于其它交付说明。**

- **默认载体 = 飞书在线表格**。当用户需要一个表格产物时（哪怕用户说“做个 Excel”“整理成表格”“给我个表”“需要打印”，“需要导出成excel”），**默认产出飞书在线表格**，方便在线预览、协作和编辑。
- **唯一的例外（产出本地文件）**：用户**直接明确禁止**使用飞书表格
- 上述例外之外，一律以飞书在线表格交付。

**`.xlsx` → 飞书表格导入（`lark-cli sheets +workbook-import`）**：当需要把本地 Excel 变成飞书在线表格时，用 Python 生成 `.xlsx` 后调用 `lark-cli sheets +workbook-import` 导入（固定导入为电子表格类型）：

**导入参数纪律（先按 `--help` 校准，避免凭直觉传参）**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--file` | 是 | 本地文件相对路径，如 `./file.xlsx` / `data/file.xlsx`；支持 `.xlsx` / `.xls` / `.csv` |
| `--folder-token` | 否 | 目标文件夹 token；不传则导入到云空间根目录 |
| `--name` | 否 | 导入后的在线文档名称；不传默认用本地文件名去扩展名 |

- `+workbook-import --file` 只接受当前工作目录内的相对路径，按下方示例传参。先 `cd` 到文件所在目录或项目工作目录，再传 `./file.xlsx` / `data/file.xlsx`；不要传 `/home/.../file.xlsx`、`C:\...\file.xlsx` 这类绝对路径。

```bash
# 正确：导入当前目录下的本地文件
lark-cli sheets +workbook-import --file "./file.xlsx" --name "<在线表格名称>"

# 错误：--file 传绝对路径会被判定为 unsafe file path
lark-cli sheets +workbook-import --file "/home/user/.../file.xlsx"
```
要点：
- 导入成功后，调用 NotifyHuman 工具把飞书在线表格链接提供给用户。
- 仅产出无格式 `.csv` 且用户明确只要本地文件时，直接生成即可，无需导入。

### 0.3 必须走 lark-cli 的能力面（Must-CLI List）

以下 **4 组能力面** 属于两类之一：
**(a)** Python 本地根本做不了对等功能（openpyxl或本地python代码里没有该功能）；
**(b)** 本地能写进 xlsx，但 `+workbook-import` 导入飞书时会发生 **有损兼容**（丢失、退化、语义变形）——例如透视表变成死表、插入到单元格的图片变成浮动图片等。

**只要交付物需要触发下列任一能力面，一律先 `+workbook-import`（有附件）或 `+workbook-create`（无附件），之后全程用 `lark-cli sheets` 就地做，禁止走"本地 python 代码生成 / 修改 `.xlsx` → import"这条路径**。

| # | 能力面 | 触发关键词 / 判定信号 | 具体 lark-cli shortcut | Python 兜底为何不行 |
|---|--------|--------------------|----------------------|----------------------|
| 1 | **透视表**（含中位数汇总、计算字段-汇总层、计算字段-自定义 formula、排版重复项 4 个子选项） | 透视表 / 数据透视 / 分组汇总 / 交叉分析 / 按 X 统计 Y / 中位数汇总 / 计算字段 / 重复项标签 | `+pivot-create` / `+pivot-update` / `+pivot-delete` / `+pivot-list`（子选项挂在 `--properties`：`values[].summarize_by="median"` / `calculated_fields[].summarize_by ∈ {sum, custom}` / `repeat_row_labels: true`） | `pandas.pivot_table + df.to_excel` 出的是**死表**：源数据变了不重算、无拖字段/折叠交互；硬手写 xlsx `pivotTableDefinition` XML 导入飞书也不兼容 |
| 2 | **单元格中插入图片**（图随所在行排序 / 筛选 / 复制粘贴走） | 证件照 / 凭证图 / 每行配图 / 商品图片列 / 图片作为单元格值 | `+cells-set-image`（首选，`--range` 必须单 cell + `--image` 本地路径），或 `+cells-set` 的 `--cells` 里走 `rich_text` + `type: "embed-image"` | `openpyxl.drawing.image.Image + ws.add_image` 写的是**浮动图**（floating drawing），导入飞书被识别成浮动图对象——行排序 / 筛选时不会跟着走 |
| 3 | **图表**（柱 / 条 / 折线 / 面积 / 饼 / 雷达 / 散点 / 组合；面积图 area 是子类型） | 数据可视化 / 图表 / 趋势图 / 对比图 / 占比图 / 面积图 / 内嵌图表 | `+chart-create` / `+chart-update` / `+chart-delete` / `+chart-list`；面积图挂 `snapshot.plotArea.plot.type="area"` | matplotlib / seaborn 生成的 PNG 是**静态图片**，无法随源数据更新，且飞书里失去交互能力；openpyxl chart 导入飞书**有损兼容** |
| 4 | **迷你图 sparkline**（含胜负图 win_loss / count 子类型） | 迷你图 / sparkline / 单元格内趋势线 / 胜负图 / count 迷你图 | `+sparkline-create` / `+sparkline-update` / `+sparkline-delete` / `+sparkline-list`；胜负子类型走 `config.type="win_loss"`（Excel 的 count / 胜负 = 飞书 `win_loss`） | 文本字符（▁▂▃▅▇）拼接、`SPARKLINE()` 公式、matplotlib PNG 都是死东西；openpyxl 没有 SparklineGroup 公开 API，硬写底层 XML 导入飞书也不识别 |

**强调一次**：
1. **已有表格排序必须走 CLI**：仅当对已存在的表格进行排序时，必须使用 `+range-sort`，`--range` 覆盖需要一起移动的完整行数据，多级排序一次写入 `--sort-keys`，首行为表头时传 `--has-header`。禁止用 Python / pandas 本地排序后再覆盖写回，否则可能破坏公式、空值类型、样式及整行字段对应关系；新建表格时不受此限制。
2. **公式/原生联动优先**：表内可推导的派生结果必须使用公式或合适的原生对象；仅外部事实、固定常量、循环引用或表内无法表达的结果可写静态值。
3. **公式写入与回读验证**：写公式必须确认引号、反斜杠及解析后的公式文本正确；推荐用 JSON serializer 序列化到本地临时文件，校验通过后通过 stdin 写入，禁止手工拼接多层转义。写入公式后总是检查公式是否有编译或运行错误，并回读确认计算结果是否符合用户需求、必要时写代码验算。
4. **交付必调 NotifyHuman**：默认交付飞书在线表格链接，只要涉及飞书表格产物，无论 URL 是新生成还是已有的，都**必须调用 NotifyHuman 工具**交付产物给用户；用户明确要本地文件时交付 `.xlsx` / `.csv`；仅产出无格式 `.csv` 且用户明确只要本地文件时，直接生成即可，无需导入。
5. **附件相关**：附件下载后先 `ls -la`+`file` 验字节数与魔数；<1KB、魔数不符或 file 报 JSON/HTML 即为下载失败——**先重试**（curl 记得加 `-L` 跟随重定向，或换 wget），仍失败则用 `+workbook-import` 兜底走飞书导入服务。原件未成功读入前，**禁止 openpyxl 从零重建“同款”表**，尽量在原表上修改或将原表上传到飞书文档进行修改；也**禁止凭记忆 / WebFetch 片段脑补数据**，不得交付伪造榜单或汇总。

**新建参数纪律（先按 `--help` 校准，避免凭直觉传参）**：
- 新建在线表格用 `+workbook-create --title "<在线表格名称>"`，不是 `--name`；`--name` 只用于 `+workbook-import` 的导入后文档名。
```bash
# 正确：新建在线表格
lark-cli sheets +workbook-create --title "<在线表格名称>"

# 错误：+workbook-create 不存在 --name
lark-cli sheets +workbook-create --name "<在线表格名称>"
```

---

## 一、场景识别与分派

识别场景后，**读取对应 reference 文件**，按其指导执行。下表的 reference 已按「飞书引擎（lark-sheets-*）」与「Excel 引擎 / 引擎无关方法学（guide-* / ref-* / template-*）」标注；具体走哪套引擎由 0.2 的产物载体与输入来源决定。

**基础创建与编辑**：涉及 python 生成`.xlsx` 读取 `references/ref-xlsx-workflow.md`，涉及格式、美化、报表、模板或打印展示时再读取 `references/ref-excel-visual-standards.md`。直接操作飞书在线表格读取 `references/lark-sheets-write-cells.md`，涉及样式时再读取 `references/lark-sheets-visual-standards.md`；

### 场景分派表

| 场景 | 典型信号词 / 意图 | 引擎 & 读取的 reference |
|------|----------------|-----------------|
| **文本语义处理** | “提炼要点”、“归类”、“贴标签”、“标准化文本”、“语义抽取”、“分类观点”、“汇总文字” | `references/guide-semantic-analysis.md`（方法学引擎无关；Excel 用 Python，飞书用 lark-cli 读写） |
| **数据洞察 / 数值计算 / 量化建模 / 数据挖掘** | “分析一下/有什么发现/给出洞察”、“计算/统计/求和/公式”、“建模/预测/排名打分/优化”、“挖掘/聚类/关联/找规律” | 按「二、通用执行流程」执行；表格读写按载体选引擎（飞书=「三」，Excel=`references/ref-xlsx-workflow.md`）；分析报告输出模板见 `references/template-report.md` |
| **数据透视表** | “透视表/数据透视表/pivot”、“交叉分析/多维汇总”、“按 X 统计 Y 并对比”、“分组对比” | 飞书原生：`references/lark-sheets-pivot-table.md`（Excel 输入先按 0.2 导入飞书，再 `+pivot-create` 建原生透视表，交付在线链接） |
| **公式迁移 / 飞书公式生成** | “把 Excel 公式改写成飞书公式”、“ARRAYFORMULA / 数组函数”、“INDEX/OFFSET/MAP/LAMBDA” | 飞书：`references/lark-sheets-formula-translation.md` |
| **财务 / 金融建模、报表与财务数据整理**（叠加层） | “财务模型”、“估值/DCF/LBO/Comps”、“三张报表/IS/BS/CFS”、“财务预测”、“预算/Variance”、“Sensitivity/情景分析”、“投行/PE/Equity Research/FP&A/咨询场景”；**也包括“把某公司财务数据整理成表/Excel”“整理营收成本利润现金流估值”以及“以财务数据为输入做推算（如从成本反推算力/产能/单位经济）”** | **无论产物是飞书还是 Python 生成的 `.xlsx`，无论任务看起来是“专业建模”还是“只是数据整理/推算”，都必须先读 `references/ref-financial-modeling-standards.md` 并遵守**（引擎无关的财务操作+视觉规范，叠加于上述场景之上） |

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。


> **多场景叠加**：若任务横跨多个场景，按主诉求选主场景，次要场景的相关说明也可参考对应 reference 文件。
>
> **财务/金融为叠加层（强制读规范）**：「财务/金融建模与报表」不是独立场景，而是一层**视觉与操作规范叠加**。**只要表里承载的是财务性质的数据（营收、成本、利润、现金流、估值、以财务为输入的推算等），不管最终产物是飞书在线表格还是 Python/openpyxl 生成的 `.xlsx`，也不管任务被描述成“专业财务建模”还是“只是数据整理 / 工程推算”，都必须先读 `references/ref-financial-modeling-standards.md` 再动手**，并按其要求落实颜色编码、数字格式、单位与来源、年份横向、合计边框等。该规范是引擎无关的，其优先级高于通用视觉规范。
>
> ⚠️ **不要因为下列借口跳过规范**：①“这只是把数据整理成 Excel，不算建模”——财务数据整理表就是简化版财务报表，同样适用；②“我用 Python 生成 .xlsx，不是在表格里搭可交互模型”——规范是呈现/逻辑规范，与生成工具无关；③“规范都在讲 DCF/三表这种重模型”——简单表只取轻量规则（颜色/数字格式/单位/合计边框），但不能一条都不用。规范内「按任务裁剪」已给出每类任务的最小规则集。

---

## 二、通用执行流程

以下流程适用于所有场景，**引擎无关**——只给通用概述；具体读写命令与执行细节由对应 reference 提供，飞书侧的**编辑准则**与**执行要点**见「三」。**飞书任务动手前先过「三」的「飞书表格编辑准则」**，本节不与之重复展开。

### 2.0 基本原则

1. **源数据默认必须保留**：除非用户明确要求删除、覆盖或替换原数据，表格编辑/整理/统计任务都不能破坏源明细。对已有表做“按指定维度统计整理”“分类汇总”“透视分析”“生成结果表”时，默认保留原 sheet 和原始行列，把统计结果写到新 sheet、新区域或明确命名的结果表；不要只反馈统计结果、清空明细、覆盖原 sheet，或把原始数据口径改掉。
2. **最小改动、保护原表**：操作前明确目标范围；除非用户明确要求删除、覆盖或替换，原表值、公式、行列结构、合并单元格、行高列宽、冻结、隐藏、分组、条件格式和筛选状态均须保持，检查 `lark-cli` 返回值中更新的单元格数量、位置是否符合预期。禁止为处理方便重建整表、清空明细、整块覆盖或重置默认样式；结果优先写入用户指定位置；未指定时先确认是否有语义匹配且可安全写入的空结果列，非必要不新增列 / Sheet；确无安全落点或结果需要独立展示时，才在原表右侧 / 下方追加或新建明确命名的结果 Sheet。
   - **写入类型按值本质**：量值（%/金额/计数）走数值 + `number_format`（禁 `"40%"`/`"¥1,234"` 等预 format 字符串）；标识符（`001`/`12.10`/单据号）走文本 + `"@"`（防 `001→1`/`12.10→12.1`/科学计数）；日期走 typed 协议 `datetime64[ns]` 落真日期，别在 `+csv-put`/`+cells-set` 里裸传 `"2026-01-05"` 存成文本。写完用 `+cells-get --include value,style` 抽样回读 `cell_styles.number_format` 与渲染值，不符则重写。
3. **公式优先原则**：凡是需要计算，优先写公式到最终交付的表格对应单元格，保持动态计算能力。
   - Excel 引擎：写 Excel 公式（如 `ws['C2'] = '=A2+B2'`），不要在 Python 中算好数值再写入。
   - 飞书引擎：写飞书公式；Excel 公式到飞书公式的迁移规则见 `references/lark-sheets-formula-translation.md`。
   - **例外**（允许直接写静态值）：从外部抓取的数据、永不变化的常量、用公式会产生循环引用。
   - 🚨 **最高频违规：用 Python 算好结果再硬编码写入单元格。** “我先在 Python 里算准（甚至跑了校验脚本）再写进表”**不能**作为硬编码的理由——结果对≠合规，硬编码出来的是一张没有联动能力的“死表”，用户改任何输入都不会重算。Python 可用于推导和验证，但**落进单元格的必须是引用其他单元格的公式**，关键输入要做成可修改的输入格。这一条在财务/金融场景尤其严格，详见 `references/ref-financial-modeling-standards.md`。

### 2.1 判断数据来源（对应 0.1）

按 0.1 判断来源后进入 2.2：上传 Excel/CSV → 走 Excel 引擎预检；飞书 / doubao 链接 → 走飞书引擎预检；口述/粘贴数据 → 先结构化并按 0.2 选载体，需进一步分析再进入 2.2；信息不足 → 先向用户确认或先用其它工具取数。

### 2.2 数据结构和内容的预先检查

拿到数据后，**先检查结构再动手处理**：

1. **运行结构预检**了解数据概况（预检只为了解数据，具体执行仍需读取完整内容）：
   - **Excel 文件**：`python scripts/inspect_workbook.py <文件路径>`；若 openpyxl / pandas 等本地库都打不开（文件损坏 / 加密 / 老式 `.xls` / 非标准结构），**不要改用解压 xlsx 直读 XML、手写底层解析等本地绕路**——一律用 `+workbook-import --file <本地路径>` 导入为飞书在线表格，再走飞书引擎（「三」）读取处理
   - **CSV 文件**：用 `pd.read_csv(..., nrows=15)` 预览，注意编码（优先尝试 utf-8-sig、gbk、gb18030）
   - **飞书表格**：优先运行 `python scripts/lark_inspect_workbook.py --url "<表格URL>"` 做只读预检，拿子表清单、布局、预览和 `current_region`；多块表 / 汇总块 / 备注块先用 `scripts/lark_detect_subtables.py` 识别候选 range；批量写入、公式/计算、排序/筛选、去重/lookup、透视/图表/汇总、整表语义或表头不确定时，再用 `scripts/lark_profile_table.py` 对目标区域画像。也可以直接调用 `+workbook-info` / `+sheet-info` / `+csv-get` / `+cells-get` 做等价读取。详见 `references/lark-sheets-read-data.md`。
2. **评估数据规模**，决定执行策略：
   - **小数据**（行数 ≤ 1000，文件 ≤ 5MB）：一次性加载处理
   - **大数据**（行数 > 1000 或文件 > 5MB）：分批策略（分 sheet / 分行批处理 / 流式读取 / 列裁剪）
   - **多 sheet 文件**：逐个 sheet 单独执行完整的「预检 → 处理 → 输出」流程
3. **识别合并单元格**：合并单元格的值仅存储在左上角；提取类任务需 `ffill` 填充；写公式/做合并时只允许在左上角单元格写值/公式。Excel 见 `references/ref-xlsx-workflow.md`，飞书见 `references/lark-sheets-sheet-structure.md`。
4. **识别“表头不清晰”并做字段理解**：若出现无表头/空表头列/多行表头/前几行是标题说明：
   - Excel 用 `scripts/preview_excel_rows.py` 对可疑 sheet 预览更多行（如前 30 行），结合数据形态判断真正表头行
   - 对空表头列，观察该列前 20 个非空值的类型与模式，推断临时列名（如 `未命名_金额`、`未命名_日期`）
   - 后续映射与计算优先用“列坐标/列字母 + 行号范围”锁定字段来源，避免引用错列
5. **识别“特殊行/特殊单元格”并特殊处理**：出现“合计/总计/小计/汇总/累计”等与明细口径不同的行时，做聚合/统计/建模前从明细中排除这些汇总行，避免重复统计（`inspect_workbook.py` 的 `special_rows` 可辅助定位）。

### 2.3 字段语义对齐

动手前，确认用户的指标/概念与数据中字段如何对应。用户说的“收入”是哪一列？“完成率”怎么算？避免“答非所问”。

### 2.4 按场景执行

读取场景分派表（「一」）中对应的 reference 文件，按其工作流程执行任务。

### 2.5 专业格式与视觉规范

专业格式用于降低阅读成本、提高产物质量，不是默认装饰动作，避免过度使用斑马纹/交替行颜色等装饰。用户明确的格式要求与既有模板样式优先；只使用能够表达层级、数据类型、状态或对比关系的必要格式。

- **Excel**：`.xlsx` 涉及格式、美化、报表、模板、汇报或打印展示时，读取 `references/ref-excel-visual-standards.md`。
- **飞书表格**：涉及上述场景时时，读取 `references/lark-sheets-visual-standards.md`。
- **财务数据**：无论产物载体，均叠加读取 `references/ref-financial-modeling-standards.md`；财务规范优先于通用视觉规范。
- **无需主动美化**：仅计算、补值、临时明细或原始数据导出时，通常只保证必要的数字格式、列宽与基本可读性。
- **最低验收**：无截字、`####`、异常溢出或对象遮挡；数字、日期、百分比和标识符格式正确；图表具有清晰的中文标题、坐标轴与必要图例。

### 2.6 交付

- **改动策略匹配诉求**：默认可在必要范围内修改；若用户要求“只改指定位置/保留原表”，则通过新建 sheet/复制 sheet/另存等方式实现
- **公式在交付表**：计算结果用公式写在最终交付的表格位置，不在临时表/中间 sheet 计算后回填数值
- **公式零错误（生成 `.xlsx` 时强制）**：只要本流程生成了 `.xlsx`（无论作为最终交付物，还是先生成再 `lark-cli sheets +workbook-import` 导入飞书的中间产物），**交付前必须运行 `python scripts/formula_verify.py <文件路径>` 重算校验，确保 0 公式错误**（`#REF!` / `#DIV/0!` / `#VALUE!` / `#N/A` / `#NAME?` / `#NUM!` / `#NULL!`）。有任何报错先定位修复（常见原因：引用错列/错 sheet、`$` 锁定写错、除数为空、查找未命中、函数名拼错），修好后重新校验，直到归零再交付/导入。不要把带报错的表交付，也不要把带报错的 `.xlsx` 导入飞书。
- **载体按 0.2**：默认交付飞书在线表格链接，只要涉及飞书表格产物，无论 URL 是新生成还是已有的，都必须调用 NotifyHuman 工具交付产物给用户
- **结论优先于过程**：最终交付聚焦用户需要的结论和建议，过滤中间过程

### 2.7 信息合理性校验（生成/推断信息时必做）

当任务需要“生成信息/补全缺失值/把口述信息整理成表/输出结论建议/构造示例数据”时，交付前必须做合理性校验：

1. **单位合理**：货币/数量/百分比/温度单位一致；表头写清单位（如 `Revenue (¥)`、`Weight (g)`）。
2. **取值范围**：时间/时长/数量一般不为负；百分比一般在 `[0,1]` 或 `[0%,100%]`，异常值判断是否格式混淆并统一。
3. **日期时间一致**：结束时间不得早于开始时间；跨天需显式说明或拆分。

---

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

下列准则横切所有任务，**动手前先过一遍**——被索引直接路由进某个工具参考也一律生效；展开与边界见括注的 reference。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

1. **最小改动**：除任务要改的单元格 / 列外，原表其它单元格、行列结构、Sheet 名、合并区、格式 1:1 保持；中间结果放原数据右侧或新建空白 Sheet，**禁止删 / 改名 / 隐藏 / 移动已存在 Sheet**；改写类任务精确圈定行列，不该转的原值 1:1 保留。
2. **真实写回 + 回读校验**：交付必须是对在线表格的真实写入，写完用 `+csv-get` / `+cells-get` / `+<对象>-list` 回读确认实际生效——**写操作返回 `ok` 只代表请求被接受、不代表结果符合预期**；写公式后查错误码、筛选 / 排序后核对前几行、删除 / 清空后确认已空。禁止只在文本里声称"已完成"。
3. **读全再写**：批量填充 / 补齐 / 修正类任务先确认真实数据末行再写，只探前 N 行会漏写表尾（确定末行流程见 `lark-sheets-read-data`）。
4. **公式优先于硬编码**：能用公式表达的计算（总计 / 占比 / 提取 / 查找）一律写公式而非静态值——**凡可由表内其它单元格推导的派生值默认用公式，即使用户没说"联动"**；写公式前先读 `lark-sheets-formula-translation`，**公式落表后收尾必跑 `+formula-verify` 直到 `status='success'`**。
5. **续写 / 扩展继承样式**：续写、补齐、复制区块、新增行列时禁止只读值只写值，必须连带 `cell_styles` + `border_styles` + 合并 + 行高一起继承（清单见 `lark-sheets-write-cells`，四边框最易漏）。
6. **多步写入分流**：美化收尾（样式 / 合并 / 行高列宽 / 冻结的任意组合）→ 一次 `+styles-put` 声明式规格交付（见 `lark-sheets-styles-put`）；**同一个写操作**打多个区域 → 用该命令自身的复数形态（`--ranges` / map 入参）；只有**跨类型、有顺序依赖的操作链**（如插列 → 写表头 → 回填数据）才用 `+batch-update`（high-risk-write：按下方审批协议先获用户同意再带 `--yes`；fail-fast 不回滚，语义见 `lark-sheets-batch-update`）。
7. **分组汇总用透视表**："按 X 统计 Y / 分组汇总 / 各类数量金额"用 `+pivot-{create|update|delete}`，禁止用 SUMIF / 本地脚本拼一张假透视表。
8. **拆成可验证 checklist**：落地前把指令拆成所有"独立可验证子要点"，逐点 `assert` 全过才交付（多维排序每维一点、多目标每目标一点、范围类核起 / 末 / 边界）；只做第一个要点属违规。
9. **全量处理前置断言条数**：翻译 / 打标 / 批量公式落地等逐条任务，先把预期条数硬编码再 `assert actual == expected`，禁止输出"已完成前 N 条，剩余继续"的半成品。
10. **缺失值不编造**：补齐 / 扩展 / 按原表格式续填时，查不到或无法确定的值一律留空 + 备注注明（"暂未发布 / 未知 / 待核实"），禁止用推算值 / 估算值 / 凭空数据充数；原表若已示范缺失值写法（空值 + 备注），照抄该约定。宁可留空标注，不填不可靠的数。

> 端到端工作流：了解结构（`scripts/lark_inspect_workbook.py` / `+workbook-info`）→ 读数据 → 理解语义 → 原生工具优先 → 写入 → 回读验证；实操展开见下方「执行要点」。

### 场景 → 命令速查（拿不准命令名先查这里，别按直觉拼）

把高频意图映射到**真实存在**的 shortcut / flag（agent 常从 Excel / Google Sheets / OpenAPI 误迁移命令名）。**选定命令后先读「动手前读」列指向的 reference 再动手**——命令名对得上不代表用法对。

| 你要做的事 | ✅ 正确写法 | 动手前读 | ❌ 不存在（会被 cobra 拒） |
| --- | --- | --- | --- |
| 读数据（纯值 / CSV） | `+csv-get`（`--range` 可省略 = 读整个子表，无需先探行列；限定范围才传） | `lark-sheets-read-data` | `+get-range`、`+range-get`、`+cells-read` |
| 读值 + 公式 / 样式 / 批注 | `+cells-get --include value,formula,style,comment,data_validation` | `lark-sheets-read-data` | `+get-cell`、`+cell-get`、`--with-styles`、`--with-merges`、`--include-merged-cells` |
| 写纯文本值（整块 CSV 平铺；列里没有需字面保真的编号 / 点分日期） | `+csv-put`（定位用 `--start-cell` 左上角锚点格，也接受 `--range` 别名） | `lark-sheets-write-cells` | 把含点分日期(`12.10`)/编号(`001`)的列裸灌 `+csv-put`——会被数值化（`12.10`→`12.1`、`001`→`1`），改用 `+table-put` 声明 `dtypes:object` |
| 写带类型的数据到**已有**表（列里有数字 / 金额 / 百分比 / 日期等**量值**——不看当下要不要排序求和，量值一律走这里） | `+table-put --sheets '{"sheets":[{"name":…,"columns":[…],"dtypes":{…},"formats":{…},"data":[[…]]}]}'`（不存在的 sheet 名自动建子表；同时美化加 `--styles` 一步带样式，详见 write-cells） | `lark-sheets-write-cells` | 在本地把数字拼成 `"$1,234"` / `"30.5%"` 字符串再 `+csv-put`（落成文本、丢计算能力，见下方 ⚠️） |
| **新建**电子表格并写带类型的数据（类型保真需求同上，但目标表还不存在） | `+workbook-create --sheets`（协议与 `+table-put` 同构、一步建表 + typed 写入，无需先建空表再 `+table-put`；date / number 不丢；`--styles` 同样可在建表同一步带全套样式，详见 workbook） | `lark-sheets-workbook` | 用 `--values` 灌日期 / 数字（会落成文本、丢类型） |
| 写公式 / 富写入（样式 · 批注 · 图片 · 富文本），或需精确矩形定位的值 | `+cells-set`（单区域 `--range`+`--cells`；**散布多处 / 跨表用 `--writes` 一次批量交付**，每项自带 sheet_name；公式落表后继续 `+formula-verify` 收尾） | `lark-sheets-write-cells` | — |
| 插图：图片**绑定到某条记录**、随行走（凭证 / 证件照 / 商品图 / 头像 / 二维码 / 每行配图） | `+cells-set-image`（单格 `--range`，嵌入单元格内） | `lark-sheets-write-cells` | — |
| 插图：**自由摆放、不绑数据**的装饰 / 标识（logo / 水印 / 封面大图 / banner） | `+float-image-create`（浮动图片，自由定位 + 尺寸 + 层级） | `lark-sheets-float-image` | — |
| 查找 / 替换文本 | `+cells-search`（找，关键字用 `--find`）、`+cells-replace`（替换） | `lark-sheets-search-replace` | `+cells-find`、`+find`、`--query` |
| 看子表结构（合并 / 行高列宽 / 冻结 / 隐藏） | `+sheet-info` | `lark-sheets-sheet-structure` | `+sheet-get`、`+structure-get`、`+sheet-structure-get` |
| 看工作簿 / 子表清单 | `+workbook-info` | `lark-sheets-workbook` | `+sheet-list`、`+workbook-get`、`+workbook-list` |
| 复核某次（AI）编辑改了什么 / 取两个版本间的变更 | `+changeset-get --start-revision <编辑前版本>`（省略 `--end-revision` 取到最新；版本差 ≤ 20） | `lark-sheets-changeset` | — |
| 取当前文档 revision（版本号） | `+revision-get` | `lark-sheets-workbook` | — |
| 导出 xlsx / 单表 csv | `+workbook-export` | `lark-sheets-workbook` | — |
| 导入本地 xlsx/xls/csv 文件为飞书电子表格 | `+workbook-import --file ./x.xlsx`（仅要导成多维表格 bitable 时才用 `drive +import --type bitable`） | `lark-sheets-workbook` | `drive +import`（绕路）、本地读 .xlsx 再 `+workbook-create` 重灌（多此一举）、想并入**已有工作簿**却用它（import 只会另起新表，加子表走 `+sheet-copy` / `+sheet-create`） |
| 参考某个**已有在线表**、把多份数据各作为一张子表**追加**进去 | 先 `+workbook-info` → `+sheet-copy` 复制模板子表（公式 / 合并 / 底色 / 列宽全继承）再 `+cells-*` 只改数据；无模板可继承时 `+sheet-create` + `+table-put --sheets/--styles` | `lark-sheets-workbook` | `+workbook-import` / `+workbook-create` 另起独立新表（这两条只产新表、不接受已有表定位） |
| **已有**表美化收尾（样式 / 边框 / 合并 / 行高列宽 / 冻结的任意组合，单表或多表） | `+styles-put --styles '{"styles":[{"name":…,"cell_styles":[…],"cell_merges":[…],"row_sizes":[…],"col_sizes":[…],"freeze":{…}}]}'`（一份规格一次交付，词汇同 `+table-put --styles`） | `lark-sheets-styles-put` | 拼 `+batch-update` 的 `--operations` 子操作数组做美化、逐区域多次 `+cells-set-style` |
| 清除内容 / 格式 | `+cells-clear`（high-risk-write 需用户确认后带 `--yes`；范围维度用 `--scope`，取值 content / formats / all） | `lark-sheets-range-operations` | `--type` |
| 批量清除多区域 | `+cells-batch-clear`（high-risk-write 需用户确认后带 `--yes`；`--scope`） | `lark-sheets-batch-update` | `--target` |
| 调整列宽 / 行高 | `+cols-resize` / `+rows-resize`（行、列是两个独立命令；连同样式一起调时并入 `+styles-put` 的 `row_sizes` / `col_sizes`） | `lark-sheets-range-operations` | `--dimension`（无此 flag） |
| 分组汇总 / 透视 | `+pivot-create`（默认不传落点 flag → 自动新建子表，零覆盖） | `lark-sheets-pivot-table` | 用 SUMIF / 本地脚本拼一张假透视表 |
| 画图表 / 可视化（柱 / 折线 / 饼 / 条 / 散点 / 组合…） | `+chart-create`（先 `+chart-create --print-example <column\|bar\|line\|pie\|combo…>` 本地拿最小可用 `--properties` 模板，改 refs / index 即可用） | `lark-sheets-chart` | matplotlib / 本地画图再贴图（原生图表可交互、随数据更新） |
| 条件高亮 / 数据条 / 色阶 / 重复值标记 | `+cond-format-create` | `lark-sheets-conditional-format` | `+highlight`、`+conditional-format`、逐格 `+cells-set-style` 硬凑 |
| 筛选 / 只看符合条件的行 | `+filter-create` | `lark-sheets-filter` | pandas filter 后覆盖写回（会毁原数据；要保存多份筛选状态用 `+filter-view-create`） |

> ⚠️ **动手前的触发式必读（按动作判定，不看主场景）**：动作里**含样式 / 美化**（底色 / 边框 / 字号 / 对齐 / 数字格式 / 配色 / 列宽行高）→ 先读 `lark-sheets-visual-standards`；**要写飞书公式** → 先读 `lark-sheets-formula-translation`，写完跑 `+formula-verify` 收尾（见 `lark-sheets-formula-verify`）。主任务是建表 / 录入也一样适用。
> ⚠️ **两种图片别选错**：图**绑定某条记录、随行走**（凭证 / 证件照 / 每行配图）→ `+cells-set-image`；自由摆放的装饰（logo / 水印 / 封面）→ `+float-image-create`。别因「浮动图更熟」默认选浮动图。
> ⚠️ **纯文本还是数值语义（看数据本质，不看当下用途）**：金额 / 百分比 / 日期 / 计数等**量值**一律数值写入——常规二维表用 `+table-put`（`dtypes` + `formats`），宽表 / 合并表头版式用 `+cells-set` 传数字（百分比传小数 `0.4`）+ `number_format`。只有编号 / 身份证等**标识符**才 `+csv-put` 平铺。"只是展示不用算 / 样式以后再刷"不构成把量值写成字符串的理由——类型不能后补。判据见 `lark-sheets-write-cells`「数字还是文本」。
> ⚠️ **要新建子表 / 整表美化 → 别「`+csv-put` 写值再事后刷样式」**：`+table-put` / `+workbook-create` 的 `--styles` 在写数据**同一步**带全套样式（底色 / 边框 / 列宽行高 / 合并 / 冻结），payload 里不存在的 sheet 名自动建子表，纯文本表同样适用；比事后多次刷样式少好几次调用。存量表事后美化则一次 `+styles-put` 交付（同一份 `--styles` 词汇）。
> ⚠️ **定位 flag**：`+cells-get` / `+cells-set` / `+csv-get` 用 `--range`；`+csv-put` 用 `--start-cell`（也接受 `--range` 别名，区间取左上角）。
> ⚠️ **读取附加信息**一律走 `+cells-get --include …`（无 `--with-styles` 这类 flag）；**看合并单元格**用 `+sheet-info` 的 `merged_cells`。

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
| "完善 / 补齐 / 修正所有 XX"、分析 / 清洗 / 大数据 | 先 `scripts/lark_profile_table.py` 确认目标区域与字段画像，再原生优先（公式 / `+pivot` / `+filter`）；表达不了再分批 `+csv-get` 导出 + 脚本处理 + 分批回写（默认覆盖所有对应数据行） |
| "查一下 / 统计 / 汇总"等只读 | 小表 `+csv-get` 读到上下文；大表先 `+workbook-info` + 小窗口 `+csv-get` 定边界，再对未截断窗口跑 `scripts/lark_detect_subtables.py` / `scripts/lark_profile_table.py` |
| 需要公式 / 样式 / 批注 | `+cells-get` |
| 续写 / 扩展已有内容 | `+csv-get` 看结构 + `+cells-get` 读源区样式 + `+sheet-info --include row_heights,merges`（见准则 5） |

> "补齐 / 填空"类只探前 10 行就写会漏写表尾——先按 `lark-sheets-read-data` 确认真实数据末行（准则 3）。

#### 计算：原生工具优先，代码兜底（强化准则 7）

| 用户需求 | 用原生 | 禁止的替代 |
|---|---|---|
| 按 X 统计 Y、分组汇总 | `+pivot-{create\|update\|delete}` | pandas groupby → 写值 |
| 求和 / 计数 / 平均 / 占比 | 公式 | Python 算 → 写静态值 |
| 图表 / 可视化 | `+chart-*` | matplotlib |
| 条件高亮 / 色阶 | `+cond-format-*` | 逐格设样式 |
| 筛选 | `+filter-*` | pandas filter → 覆盖写入 |
| 文本提取 / 转换 / 查找 | 公式（MID / FIND / TEXT / VLOOKUP 等） | Python → 写静态值 |

只有多步清洗、统计建模、公式试错 3 次仍失败时才用代码。

#### 用脚本配合 CLI 时

- **只读 stdout**：CLI 数据走 stdout、诊断走 stderr；解析 JSON 别 `2>&1`（警告混入会解析失败），用管道或单独重定向 stdout。
- **读表理解优先用 `scripts/lark_*.py`（若可用）**：`lark_inspect_workbook.py` / `lark_detect_subtables.py` / `lark_profile_table.py` 是只读脚本，用来把在线表格整理成结构摘要。**可选增强，不是必经步骤**——`scripts/` 只随仓库版 skill 分发，二进制内嵌版没有这些文件；本地不存在时直接用 CLI 等价路径（对照表见 `lark-sheets-read-data`：`+workbook-info` / `+sheet-info` / 小窗口 `+csv-get`）。它们不替代写入类 shortcut；确认目标区域后，写入仍按对应 reference 执行。
- **喂 CLI 的 CSV / JSON 用 UTF-8 无 BOM**；临时文件放系统临时目录、勿落项目目录。
- **命令失败先读 stderr 再调整**，别原样重发。
- **回写纯单元格值**：剥离 `值(V-Align: bottom)` 这类"值(样式)"串与残留引号再写；排序优先 `+range-sort` 原生工具，别"读出本地排完再整列写回"。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

#### 易漏陷阱

- **`+dim-insert` 不继承行高**：只继承值 / 公式 / 边框；插行填长文本前读相邻行 `row_height`，用 `+batch-update` 合 `+rows-resize` 补齐。
- **公式容错**：日期 / 查找 / 转换公式用 `IFERROR` 包裹；写完查首末各 5 行错误码，再跑 `+formula-verify` 到 `status='success'`；同一方案试错上限 3 次。
- **循环引用**：聚合公式引用范围不能含目标 cell 自身或其传递依赖。
- **隐藏行列**：`+csv-get` 默认含隐藏行列；`--skip-hidden=true` 只看可见，真实行号会跳空——禁止按返回数组下标推导行号，用 `annotated_csv` 的 `[row=N]` 或 `row_indices`。
- **跨 sheet 对象**：图表 / 条件格式 / 透视表 / 浮动图片可能分布在多个子表，先 `+workbook-info` 掌握全局。
- **NLP 任务分批**：语义理解 / 翻译 / 打标用 NLP 处理（代码只做分批 / 行号映射 / 写回）；大数据量分批（约 30 行 / 批）即时写回，多批用 `+batch-update`。

### References

reference 分两组：先读**通用方法与规范**（横切所有任务的样式 / 公式规则），再按操作对象进入**工具参考**查具体 shortcut。编辑类任务务必先过通用方法与规范，连同上方「飞书表格编辑准则」对所有工具参考一律生效。

#### 通用方法与规范（先读，横切所有任务，不含具体 shortcut）

| Reference | 描述 |
| --- | --- |
| [飞书表格样式与配色规范](references/lark-sheets-visual-standards.md) | 飞书表格样式与配色规范：表头/数据区/汇总行的颜色、字号、对齐、边框、数字格式等取值标准，以及从零新建表格的版式美化、新增汇总行、追加行列继承原表风格、已有区域美化等典型场景的决策流程与样式要点。工具调用参数细节请参考对应的 lark-sheets-write-cells / lark-sheets-range-operations / lark-sheets-batch-update。条件格式（高亮、标红、数据条、色阶）请使用 lark-sheets-conditional-format。 |
| [飞书表格公式生成规则](references/lark-sheets-formula-translation.md) | Excel 公式到飞书表格公式的迁移与生成规则。核心目标不是保留 Excel 原语法，而是按飞书表格可执行规则重写公式，并在结果上尽量对齐 Excel。当用户要求把 Excel 公式改写成飞书表格公式，或需要生成飞书公式（尤其涉及 ARRAYFORMULA、数组语义与逐行填充、原生数组函数、INDEX/OFFSET、MAP/LAMBDA、日期差、多层范围结果与二次展开）时使用。本文只负责把公式写对，落表后的强制收尾请接 `lark-sheets-formula-verify`。 |
| [金融/财务建模与财务数据整理规范](references/ref-financial-modeling-standards.md) | **引擎无关**的金融/财务/估值建模专业结构与视觉规范，**飞书在线表格与 Python/openpyxl 生成的 `.xlsx` 同样适用**：DCF / LBO / Comps / Precedent、三张财务报表、预算与 Variance Analysis、Sensitivity / Scenario、FP&A 等，**以及“把财务数据整理成表/Excel”“以财务为输入的推算”等看似“只是数据整理”的任务**。覆盖科目分类、三表勾稽、Assumptions / Calc / Sensitivity 拆分、年份横向布局、假设颜色编码、财务数字格式、Sensitivity 禁色阶等（含 Python 代码示例）。与通用视觉规范冲突时以本文为准；用户明确样式或既有模板优先。**做任何财务性质表格前必读必守。** |
| [Excel 可视化规范](references/ref-excel-visual-standards.md) | Excel 文件的通用格式与美化规范。生成或编辑 `.xlsx` 且涉及格式、美化、报表、模板或打印展示时读取；仅适用于 Excel，飞书在线表格使用上方飞书表格规范。 |

#### 按对象的工具参考（含 shortcut）

| Reference | 描述 |
| --- | --- |
| [Lark Sheet Formula Verify](references/lark-sheets-formula-verify.md) | 公式写入 / 批量填充 / `--copy-to-range` 扩展 / 导入含公式工作簿后的强制自检入口。对指定子表（或整本工作簿）扫描公式与单元格值，聚合所有 Excel 错误（#REF! / #DIV/0! / #VALUE! / #NAME? / #NULL! / #NUM! / #N/A），同时合并最近一次写入留下的编译失败（formula_errors），输出统一 JSON 让 AI 一次拿到完整健康度报告。只要任务涉及写公式，落表后就应调用 +formula-verify 收敛到 zero-error；`status='errors_found'` 或 `status='partial'` 时禁止把链路标为完成。 |
| [Lark Sheet Workbook](references/lark-sheets-workbook.md) | 管理飞书表格的工作簿结构（子表列表及元数据）。当用户提到"看看这个表格有什么"、"表格结构"、"有哪些 sheet"、"新建一个 sheet"、"删除这个工作表"、"重命名"、"复制一份"、"移动到前面"时使用。 |
| [Lark Sheet Sheet Structure](references/lark-sheets-sheet-structure.md) | 管理飞书表格的子表结构与布局。适用场景：查看行高、列宽、隐藏行列、合并单元格等布局信息，以及"插入一行"、"删除这列"、"隐藏行"、"冻结表头"、行列分组（大纲折叠/展开）等操作。行列大纲仅在用户明确提到"行分组"、"列分组"、"大纲"、"outline"时才触发，"按XXX分组"等数据分组场景请使用 lark-sheets-pivot-table。如需在表尾追加数据，应先通过此 skill 插入行，再通过 lark-sheets-write-cells 写入。 |
| [Lark Sheet Read Data](references/lark-sheets-read-data.md) | 读取飞书表格中的单元格数据。当用户需要"看看数据"、"分析数据"、"统计/汇总"时使用；也适用于需要查看公式、样式、批注等详细信息的场景。 |
| [Lark Sheet Search & Replace](references/lark-sheets-search-replace.md) | 在飞书表格中搜索和替换文本，支持限定范围、大小写匹配、精确匹配、正则表达式。当用户需要"查找"、"搜索"、"定位"某个值，或"替换"、"批量修改文本"、"把 A 改成 B"时使用。不要用于理解表格结构（应读取数据）、不要用于数据分析（应读取数据后计算）、不要把用户操作动作中的关键词（如"汇总金额""统计数量"）当作搜索词。 |
| [Lark Sheet Write Cells](references/lark-sheets-write-cells.md) | 向飞书表格的指定区域批量写入值、公式、样式、批注或单元格图片。适用场景：填写数据、设置公式、修改格式、添加批注、嵌入单元格图片（如需操作浮动图片，请使用 lark-sheets-float-image）；若只需把一块 CSV 批量铺到表格上（值或公式，不带样式/批注），直接使用 `+csv-put` 更短更快。追加数据需先通过 lark-sheets-sheet-structure 插入行列。只要这次写入真实落了公式，收尾默认继续执行 `lark-sheets-formula-verify`。 |
| [Lark Sheet Range Operations](references/lark-sheets-range-operations.md) | 对飞书表格中指定区域执行结构性操作（不涉及写入单元格数据值）。适用场景：清除内容或格式（"清空"、"删除内容"、"去掉格式"）、合并/取消合并单元格、调整行高列宽（"加宽列"、"自适应列宽"）、移动/复制/填充/排序数据（"移动数据"、"复制到"、"自动填充"、"按某列排序"）。写入单元格数据请使用 lark-sheets-write-cells。 |
| [Lark Sheet Styles Put](references/lark-sheets-styles-put.md) | 把一份声明式视觉规格（样式/边框/合并/行高列宽/冻结）一次性应用到已有飞书表格的多个子表，整份规格一次提交。当任务是对存量表做美化收尾、批量刷样式、统一版式时使用。样式取值标准见 lark-sheets-visual-standards；建新表带样式走 lark-sheets-workbook（+workbook-create --styles）、写数据同步带样式走 lark-sheets-write-cells（+table-put --styles），三者共用同一份 --styles 词汇。仅针对飞书表格。 |
| [Lark Sheet Batch Update](references/lark-sheets-batch-update.md) | 将多个飞书表格写入操作合并为一次批量执行，按顺序依次完成。适合需要连续执行多个写入操作的场景（如先修改结构再写入数据）。 |
| [Lark Sheet Chart](references/lark-sheets-chart.md) | 管理飞书表格中的图表（柱形图、折线图、饼图、条形图、面积图、散点图、组合图、雷达图等）。当用户需要创建图表、修改图表样式或数据源、查看已有图表配置、删除图表时使用。也适用于用户提到"数据可视化"、"画个图"、"趋势分析"、"对比图"、"占比分析"、"做个图表"等数据可视化相关场景。 |
| [Lark Sheet Pivot Table](references/lark-sheets-pivot-table.md) | 管理飞书表格中的数据透视表。当用户需要创建透视表、修改透视表的行列字段/聚合方式/筛选条件、查看已有透视表配置、删除透视表时使用。也适用于用户提到"分组汇总"、"交叉分析"、"按XXX统计"、"按字段分组"、"再分下组"、"多维分析"、"数据透视"等场景。 |
| [Lark Sheet Conditional Format](references/lark-sheets-conditional-format.md) | 管理飞书表格中的条件格式规则（重复值高亮、单元格值比较、数据条、色阶、排名、自定义公式等）。当用户需要创建条件格式、修改已有规则的范围或样式、查看当前条件格式配置、删除规则时使用。也适用于用户提到"高亮"、"标红"、"颜色标记"、"数据条"、"色阶"、"条件样式"等场景。 |
| [Lark Sheet Filter](references/lark-sheets-filter.md) | 管理飞书表格中的筛选器（filter）。当用户需要筛选数据（按文本/数值/颜色/日期条件过滤行）、查看已有筛选配置、修改或删除筛选器时使用。也适用于"只看"、"筛选出"、"仅保留符合条件的"等场景。 |
| [Lark Sheet Filter View](references/lark-sheets-filter-view.md) | 管理飞书表格中的筛选视图（filter view）。当用户需要"建一个 XX 视图"、"保存这个筛选状态"、"切换不同筛选"、维护一个 sheet 上多份独立筛选配置时使用。视图与筛选器（filter）相互独立，可在同一 sheet 共存；视图的隐藏行仅在用户进入该视图时本地生效，不影响其他协作者。 |
| [Lark Sheet Sparkline](references/lark-sheets-sparkline.md) | 管理飞书表格中的迷你图（折线迷你图、柱形迷你图、胜负迷你图）。当用户需要在单元格内嵌入小型图表来展示数据趋势时使用。也适用于"趋势线"、"单元格内图表"、"迷你图"等场景。注意：不等同于被禁用的 SPARKLINE() 公式函数。 |
| [Lark Sheet Float Image](references/lark-sheets-float-image.md) | 管理飞书表格中的浮动图片。当用户需要在表格中插入浮动图片、调整图片位置和大小、查看已有浮动图片、删除图片时使用。也适用于"插入图片"、"添加 logo"、"放一张图"等场景。注意：如果用户需要将图片嵌入到某个单元格内部（单元格图片），请阅读 lark-sheets-write-cells。 |
| [Lark Sheet History](references/lark-sheets-history.md) | 查询飞书表格的历史版本并回滚到指定版本。当用户需要查看一张表的编辑历史版本列表、回滚到某个历史版本、或查询回滚的异步状态（进行中/成功/失败）时使用。回滚为异步操作，发起后通过状态查询轮询结果。仅针对飞书表格。 |
| [Lark Sheet Changeset](references/lark-sheets-changeset.md) | 读取两个版本（CS revision）之间的 changeset（原始变更操作清单），用于复核某次编辑——尤其是 AI 编辑——是否真实满足用户诉求。传入起始版本（编辑前基线），可选结束版本（省略取最新），版本差上限 20；返回里最外层带当前表格最新版本号。当用户需要"看看这次改了什么"、"核对 AI 改动"、"对比两个版本的变更"时使用。 |

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

大 payload（`--operations` / `--cells` / `--sheets` / `--styles` / `--properties`…）、或含换行 / 引号 / `!` 等特殊字符时，优先 heredoc stdin（`-`）传入，避免命令行超长与 shell 转义问题：

```bash
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

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

---

## 四、References 与脚本总览

引擎无关 / Excel 引擎 reference：

| 文件 | 引擎 | 用途 |
| --- | --- | --- |
| `references/guide-semantic-analysis.md` | 引擎无关 | 文本语义抽取/归类/标准化/汇总方法学 |
| `references/template-report.md` | 引擎无关 | 数据分析报告输出模板 |
| `references/ref-xlsx-workflow.md` | Excel | Excel 创建/编辑/公式重算/范围复制/数据验证等技术工作流 |
| `references/ref-excel-visual-standards.md` | Excel | Excel 通用格式、美化、图表与打印展示的视觉输出规范 |

飞书引擎 reference（17 个）见「三、References」表，那里有更详的选用说明；完整文件清单以 `references/` 目录为准。

脚本（`scripts/`）按引擎分别标注：飞书引擎用 `lark_inspect_workbook.py`（在线表格结构预检）、`lark_detect_subtables.py`（候选子表块识别）、`lark_profile_table.py`（表头 / 数据范围 / 字段类型画像）、`sheets_df.py`（DataFrame → `--sheets` typed payload，含 `df_to_sheet`）；Excel 引擎用 `inspect_workbook.py`（结构预检）、`preview_excel_rows.py`（多行表头预览）、`formula_verify.py`（公式重算与校验）、`format_range.py`（批量样式/条件格式）、`_excel_utils.py` / `lo_runtime.py`（内部工具）。

===== 全文完（共 454 行）=====
