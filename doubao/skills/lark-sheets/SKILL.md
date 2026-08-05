---
name: lark-sheets
version: 3.0.2
description: "表格全场景处理：本地 Excel/CSV 与在线表格（飞书、doubao.com 的 /sheets/ 链接）的创建、读写、分析、计算、建模、语义处理、可视化与美化。**只要用户输入包含表格类附件——上传 .xlsx/.xls/.csv 文件，或给出 feishu/doubao.com 的 /sheets/ 链接或 token——必须加载本技能。** 此外，用户口述数据要整理成表，或要求计算/统计/建模/预测/透视/可视化/美化/公式等任何表格操作时，也加载本技能。一切与 Excel/表格相关的任务都必须加载。本技能不负责获取外部信息，如需补充数据须先通过其他途径获得。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "lark-cli sheets --help"
---

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
| 用户上传 `.xlsx` / `.xls` / `.csv` 文件 | 本地 Excel/CSV | Excel 引擎；需飞书产物见 0.2 |
| 用户给出飞书 / doubao 的 `/sheets/` 链接或 token | 飞书在线表格 | 飞书引擎（「三」） |
| 用户口述 / 粘贴数据，无文件 | 待结构化 | 先结构化，再按产物载体（0.2）选引擎 |
| 无数据 | 信息不足 | 向用户询问，或先用其它工具获取数据 |

> ⚠️ **doubao.com 的 `/sheets/` 链接也走飞书引擎**：路由依据是 URL 路径模式（`/sheets/`）和 token，而不是域名。不要因为域名不是飞书就回退到 WebFetch。

### 0.2 表格产物载体决策与导入（默认飞书在线表格）

> **核心策略，优先级高于其它交付说明。**

- **默认载体 = 飞书在线表格**。当用户需要一个表格产物时（哪怕用户说“做个 Excel”“整理成表格”“给我个表”），**默认产出飞书在线表格**，方便在线预览、协作和编辑。
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

### 0.3 三条实现路径

根据「输入来源 × 产物载体」选择路径：

| 场景 | 实现路径 |
| --- | --- |
| 默认飞书产物，从零创建 / 口述数据整理 | 默认用飞书引擎（`lark-cli sheets`，见「三」）**一步到位**：`+workbook-create --sheets`（typed）建表 + `--styles` 美化，**不经 `.xlsx`**。仅当涉及「重数据加工」（定义见表下，**纯结构化整理 + 美化不算**）才先用 Python 算完，再用 `+table-put --sheets` 把结果写回飞书（pandas DataFrame 一行打成 `--sheets` 的 typed JSON，见 [`scripts/sheets_df.py`](scripts/sheets_df.py)） |
| 默认飞书产物，但输入是本地 Excel | 默认先用 `+workbook-import --file ./file.xlsx` 把本地 Excel 导入为飞书在线表格，再用飞书引擎（「三」）就地操作，保留原格式、避免本地往返。仅当涉及「重数据加工」才先用 Python 读文件算完，再用 `+table-put --sheets` 写回飞书 |
| 默认飞书产物，输入已是飞书表格 | 全程用飞书引擎（「三」）就地操作 |
| 用户明确禁止飞书表格 | 用 Excel 引擎（Python）产出本地文件，按「四」的质量规范交付，**不导入飞书** |

> **「重数据加工」判定——看操作性质，不看数据量**：只有多表 merge / join、回归 / 聚类等统计建模、大规模脏数据清洗（去重、字段拆分合并、异常修复等）这类**计算**才算。此时先用 Python（pandas / numpy / scikit-learn）算完，再用 `+table-put --sheets`（pandas DataFrame 经 [`scripts/sheets_df.py`](scripts/sheets_df.py) 打成 typed JSON，列类型 / `number_format` 一并透传）写回飞书，**不经 `.xlsx`**。
>
> 反过来，**把搜索 / 口述 / 已有的数据排进表格并美化（表头样式、边框、列宽、配色、公式、图表 / 透视表 / 条件格式）不算重数据加工**，哪怕有几十组、上千行也一样——一律用飞书引擎一步到位（`+workbook-create --sheets` + `--styles`，见 `references/lark-sheets-visual-standards.md`），**不要因为「数据多 / 想加样式」就转去 Python 生成 `.xlsx` 再导入**。用飞书引擎一步到位时无需经 openpyxl / `.xlsx`。但若实际走了「生成 `.xlsx` 再 `lark-cli sheets +workbook-import` 导入」这条路（无论是重数据加工路径、还是用户给的既有 `.xlsx` 资产），那张 `.xlsx` 仍须满足「四」的质量规范（含财务场景），因为导入后的飞书表格质量取决于源 `.xlsx`。

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

### 场景分派表

| 场景 | 典型信号词 / 意图 | 引擎 & 读取的 reference |
|------|----------------|-----------------|
| **表格创建与整理** | “做个表”、“整理成表格/Excel”、“生成报表”、“做个模板”、“整理一下格式” | 默认飞书：「三」+ `references/lark-sheets-write-cells.md` / `references/lark-sheets-visual-standards.md`；若产物为 `.xlsx`：`references/ref-xlsx-workflow.md`（含行高/列宽/截断默认规则） |
| **文本语义处理** | “提炼要点”、“归类”、“贴标签”、“标准化文本”、“语义抽取”、“分类观点”、“汇总文字” | `references/guide-semantic-analysis.md`（方法学引擎无关；Excel 用 Python，飞书用 lark-cli 读写） |
| **数据洞察 / 数值计算 / 量化建模 / 数据挖掘** | “分析一下/有什么发现/给出洞察”、“计算/统计/求和/公式”、“建模/预测/排名打分/优化”、“挖掘/聚类/关联/找规律” | 按「二、通用执行流程」执行；表格读写按载体选引擎（飞书=「三」，Excel=「四」+ `references/ref-xlsx-workflow.md`）；分析报告输出模板见 `references/template-report.md` |
| **数据透视表** | “透视表/数据透视表/pivot”、“交叉分析/多维汇总”、“按 X 统计 Y 并对比”、“分组对比” | 飞书原生：`references/lark-sheets-pivot-table.md`（Excel 输入先按 0.2 导入飞书，再 `+pivot-create` 建原生透视表，交付在线链接） |
| **公式迁移 / 飞书公式生成** | “把 Excel 公式改写成飞书公式”、“ARRAYFORMULA”、“数组函数”、“INDEX/OFFSET/MAP/LAMBDA” | 飞书：`references/lark-sheets-formula-translation.md` |
| **财务 / 金融建模、报表与财务数据整理**（叠加层） | “财务模型”、“估值/DCF/LBO/Comps”、“三张报表/IS/BS/CFS”、“财务预测”、“预算/Variance”、“Sensitivity/情景分析”、“投行/PE/Equity Research/FP&A/咨询场景”；**也包括“把某公司财务数据整理成表/Excel”“整理营收成本利润现金流估值”以及“以财务数据为输入做推算（如从成本反推算力/产能/单位经济）”** | **无论产物是飞书还是 Python 生成的 `.xlsx`，无论任务看起来是“专业建模”还是“只是数据整理/推算”，都必须先读 `references/ref-financial-modeling-standards.md` 并遵守**（引擎无关的财务操作+视觉规范，叠加于上述场景之上） |


> **多场景叠加**：若任务横跨多个场景，按主诉求选主场景，次要场景的相关说明也可参考对应 reference 文件。
>
> **财务/金融为叠加层（强制读规范）**：「财务/金融建模与报表」不是独立场景，而是一层**视觉与操作规范叠加**。**只要表里承载的是财务性质的数据（营收、成本、利润、现金流、估值、以财务为输入的推算等），不管最终产物是飞书在线表格还是 Python/openpyxl 生成的 `.xlsx`，也不管任务被描述成“专业财务建模”还是“只是数据整理 / 工程推算”，都必须先读 `references/ref-financial-modeling-standards.md` 再动手**，并按其要求落实颜色编码、数字格式、单位与来源、年份横向、合计边框等。该规范是引擎无关的，其优先级高于通用视觉规范。
>
> ⚠️ **不要因为下列借口跳过规范**：①“这只是把数据整理成 Excel，不算建模”——财务数据整理表就是简化版财务报表，同样适用；②“我用 Python 生成 .xlsx，不是在表格里搭可交互模型”——规范是呈现/逻辑规范，与生成工具无关；③“规范都在讲 DCF/三表这种重模型”——简单表只取轻量规则（颜色/数字格式/单位/合计边框），但不能一条都不用。规范内「按任务裁剪」已给出每类任务的最小规则集。

---

## 二、通用执行流程

以下流程适用于所有场景，**引擎无关**——只给通用概述；具体的读写命令、飞书侧的**编辑准则**与**执行要点**（读取路径 / 原生工具优先 / 易漏陷阱）由对应引擎章节提供（「三」飞书 / 「四」Excel）。**飞书任务动手前先过「三」的「飞书表格编辑准则」**，本节不与之重复展开。

### 2.0 基本原则

1. **源数据默认必须保留**：除非用户明确要求删除、覆盖或替换原数据，表格编辑/整理/统计任务都不能破坏源明细。对已有表做“按指定维度统计整理”“分类汇总”“透视分析”“生成结果表”时，默认保留原 sheet 和原始行列，把统计结果写到新 sheet、新区域或明确命名的结果表；不要只反馈统计结果、清空明细、覆盖原 sheet，或把原始数据口径改掉。
2. **输出区域注意保护原表**：用户要求“直接在指定位置修改/覆盖原文件”时，才在指定位置就地修改；用户没有指定落点时，优先追加结果而不是覆盖输入，典型做法是新建 `统计结果` / `整理结果` sheet，或在原表右侧/下方追加结果区并保留清晰标题。
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
   - **飞书表格**：先 `lark-cli sheets +workbook-info` 拿子表清单与元数据，再 `+cells-get` / `+csv-get` 预览数据与结构（合并/行高列宽见 `+sheet-info`）。详见 `references/lark-sheets-read-data.md`。
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

### 2.5 交付

- **改动策略匹配诉求**：默认可在必要范围内修改；若用户要求“只改指定位置/保留原表”，则通过新建 sheet/复制 sheet/另存等方式实现
- **公式在交付表**：计算结果用公式写在最终交付的表格位置，不在临时表/中间 sheet 计算后回填数值
- **公式零错误（生成 `.xlsx` 时强制）**：只要本流程生成了 `.xlsx`（无论作为最终交付物，还是先生成再 `lark-cli sheets +workbook-import` 导入飞书的中间产物），**交付前必须运行 `python scripts/formula_verify.py <文件路径>` 重算校验，确保 0 公式错误**（`#REF!` / `#DIV/0!` / `#VALUE!` / `#N/A` / `#NAME?` / `#NUM!` / `#NULL!`）。有任何报错先定位修复（常见原因：引用错列/错 sheet、`$` 锁定写错、除数为空、查找未命中、函数名拼错），修好后重新校验，直到归零再交付/导入。不要把带报错的表交付，也不要把带报错的 `.xlsx` 导入飞书。
- **载体按 0.2**：默认交付飞书在线表格链接，只要涉及飞书表格产物，无论 URL 是新生成还是已有的，都必须调用 NotifyHuman 工具交付产物给用户；用户明确要本地文件时交付 `.xlsx` / `.csv`
- **结论优先于过程**：最终交付聚焦用户需要的结论和建议，过滤中间过程
- **格式专业**：图表须有中文标题/坐标轴/图例；新建表格的行高/列宽须自适应（Excel 见「四」，飞书见 `references/lark-sheets-visual-standards.md`）
- **不主动做外部搜索补全**：信息不足时先向用户确认

### 2.6 信息合理性校验（生成/推断信息时必做）

当任务需要“生成信息/补全缺失值/把口述信息整理成表/输出结论建议/构造示例数据”时，交付前必须做合理性校验：

1. **单位合理**：液体优先体积（ml/L），非液体优先质量（g/kg）；货币/数量/百分比/温度单位一致；表头写清单位（如 `Revenue (¥)`、`Weight (g)`）。
2. **取值范围**：时间/时长/数量一般不为负；百分比一般在 `[0,1]` 或 `[0%,100%]`，异常值判断是否格式混淆并统一。
3. **日期时间一致**：结束时间不得早于开始时间；跨天需显式说明或拆分。

---

## 三、飞书表格操作引擎（lark-cli）

### 术语约定

下列词在本 skill 各文档中可能交替出现，但**指同一对象**；解析用户口语时按此映射，不要当成不同概念：

| 标准用语 | 同义 / 口语（均指同一对象） | 说明 |
| --- | --- | --- |
| 工作表（sheet） | 子表、tab、标签页 | spreadsheet 内的单张表；`sheet_id` 是其稳定标识 |
| 电子表格（spreadsheet） | 工作簿、表格 | 顶层容器；由 `--url` 或 `--spreadsheet-token` 定位 |
| reference_id | id | **表内对象**的稳定标识，即各对象主键 flag 接受的值（见下表）。⚠️ 与 `lark-sheets-float-image` 的 `--image-uri`（图片上传句柄）不是一回事，后者不属于 reference_id |

每类对象用各自的主键 flag 定位（命名不统一，按此表对照，不要凭直觉拼）：

| 对象 | 主键 flag | 对象 | 主键 flag |
| --- | --- | --- | --- |
| 工作表 sheet | `--sheet-id` | 条件格式规则 | `--rule-id` |
| 图表 chart | `--chart-id` | 筛选视图 | `--view-id` |
| 透视表 pivot | `--pivot-table-id` | 迷你图（按组） | `--group-id` |
| 浮动图片 | `--float-image-id` | | |

### 飞书表格编辑准则（动手前必守，所有编辑类任务一律生效）

下列准则横切所有飞书表格任务，**动手前先过一遍**——即使你是被索引直接路由进某个工具参考也一律生效。每条只给一句话纲要，展开与边界见括注的 reference。

1. **最小改动**：除任务要改的单元格 / 列外，原表其它单元格、行列结构、Sheet 名、合并区、格式 1:1 保持；中间结果放原数据右侧或新建空白 Sheet，**禁止删 / 改名 / 隐藏 / 移动已存在 Sheet**；改写类任务精确圈定行列，不该转的原值 1:1 保留。
2. **真实写回 + 回读校验**：交付必须是对在线表格的真实写入，写完用 `+csv-get` / `+cells-get` / `+<对象>-list` 回读确认实际生效——**写操作返回 `ok` 只代表请求被接受、不代表结果符合预期**；写公式后查错误码、筛选 / 排序后核对前几行、删除 / 清空后确认已空。禁止只在文本里声称"已完成"。
3. **读全再写**：批量填充 / 补齐 / 修正类任务先确认真实数据末行再写，只探前 N 行会漏写表尾（确定末行流程见 `lark-sheets-read-data`）。
4. **公式优先于硬编码**：能用公式表达的计算（总计 / 占比 / 增长率 / 提取 / 查找）一律写公式而非静态值；**凡可由表内其它单元格推导的派生值默认就用公式，即使用户没说"联动 / 自动更新"**；写任何飞书公式前先读 `lark-sheets-formula-translation`，而且**只要公式真实写入表格，收尾默认就要继续跑 `lark-sheets-formula-verify` 的 `+formula-verify`，直到 `status='success'`**。
5. **续写 / 扩展继承样式**：续写、补齐、复制区块、新增行列时禁止只读值只写值，必须连带 `cell_styles` + `border_styles` + 合并 + 行高一起继承（清单见 `lark-sheets-write-cells`，四边框最易漏）。
6. **多步写入合并 `+batch-update`**：多个连续写入、或同一工具对多区域重复调用，合并为单次原子 `+batch-update`（语义见 `lark-sheets-batch-update`）。
7. **分组汇总用透视表**："按 X 统计 Y / 分组汇总 / 各类数量金额"用 `+pivot-{create|update|delete}`，禁止用 SUMIF / 本地脚本拼一张假透视表。
8. **拆成可验证 checklist**：落地前把指令拆成所有"独立可验证子要点"，逐点 `assert` 全过才交付（多维排序每维一点、多目标每目标一点、范围类核起 / 末 / 边界）；只做第一个要点属违规。
9. **全量处理前置断言条数**：翻译 / 打标 / 批量公式落地等逐条任务，先把预期条数硬编码再 `assert actual == expected`，禁止输出"已完成前 N 条，剩余继续"的半成品。

> 上述准则的实操展开——读取路径、原生工具优先级、脚本配合、易漏陷阱——见下方「执行要点」节；端到端工作流为：了解结构（`+workbook-info`）→ 读数据 → 理解语义 → 原生工具优先 → 写入 → 回读验证。

### 场景 → 命令速查（拿不准命令名先查这里，别按直觉拼）

把高频意图映射到**真实存在**的 shortcut / flag。agent 常从 Excel / Google Sheets / 飞书 OpenAPI 误迁移命令名或 flag，先对照本表，避免一次必然失败的试错。完整 shortcut 见各工具参考。**选定命令后别急着写——先读「动手前读」列指向的 reference 再动手**：命令名对得上不代表用法对，写入 / 清除 / 透视类尤其容易漏掉 reference 里的防错、类型与样式继承规则。

| 你要做的事 | ✅ 正确写法 | 动手前读 | ❌ 不存在（会被 cobra 拒） |
| --- | --- | --- | --- |
| 读数据（纯值 / CSV） | `+csv-get`（范围用 `--range`） | `lark-sheets-read-data` | `+get-range`、`+range-get`、`+cells-read` |
| 读值 + 公式 / 样式 / 批注 | `+cells-get --include value,formula,style,comment,data_validation` | `lark-sheets-read-data` | `+get-cell`、`+cell-get`、`--with-styles`、`--with-merges`、`--include-merged-cells` |
| 写纯文本值（整块 CSV 平铺；列里**没有**需字面保真的数值 / 日期标签 / 编号——点分日期 `12.10`、编号 `001` 会被 csv-put 数值化，不算纯文本） | `+csv-put`（定位用 `--start-cell`，单个左上角锚点格；也接受 `--range` 别名，区间自动取左上角） | `lark-sheets-write-cells` | 把含点分日期(`12.10`)/编号(`001`)的列裸灌 `+csv-put`——会被数值化（`12.10`→`12.1`、`001`→`1`，尾零/前导零丢失），改用 `+table-put` 声明 `dtypes:object` |
| 写带类型的数据到**已有**表（列里有数字 / 金额 / 百分比 / 日期 / 计数等**本质是量值**的数据——不看当下要不要排序 / 求和，量值一律走这里） | `+table-put --sheets` 完整 payload `{"sheets":[{...}]}`（列名走 `columns`、二维数据走 `data`、列 pandas dtype 走 `dtypes`、列展示格式走 `formats`；来源不限 DataFrame——Counter / dict / list 同理；要同时美化加 `--styles` 一步带样式（区域底色 / 边框 / 列宽 / 行高 / 合并），不必事后再刷；payload 里不存在的 sheet 名会自动建子表，详见 write-cells） | `lark-sheets-write-cells` | 在本地把数字拼成 `"$1,234"` / `"30.5%"` 字符串再 `+csv-put`（会落成文本、丢失计算能力；常见借口见下方 ⚠️） |
| **新建**电子表格并写带类型的数据（类型保真需求同上，但目标表还不存在） | `+workbook-create --sheets`（协议与 `+table-put` 同构、一步建表 + typed 写入，无需先建空表再 `+table-put`；date / number 不丢；`--styles` 同样可在建表同一步带全套样式，详见 workbook） | `lark-sheets-workbook` | 用 `--values` 灌日期 / 数字（会落成文本、丢类型） |
| 写公式 / 富写入（样式 · 批注 · 图片 · 富文本），或需精确矩形定位的值 | `+cells-set`（定位用 `--range`；批注 / 图片 / 富文本只能用它，公式也可；**公式落表后继续 `+formula-verify` 收尾**） | `lark-sheets-write-cells` | — |
| 插图：图片**绑定到某条记录**、随行走（凭证 / 证件照 / 商品图 / 头像 / 二维码 / 每行配图） | `+cells-set-image`（单格 `--range`，嵌入单元格内） | `lark-sheets-write-cells` | — |
| 插图：**自由摆放、不绑数据**的装饰 / 标识（logo / 水印 / 封面大图 / banner） | `+float-image-create`（浮动图片，自由定位 + 尺寸 + 层级） | `lark-sheets-float-image` | — |
| 查找 / 替换文本 | `+cells-search`（找，关键字用 `--find`）、`+cells-replace`（替换） | `lark-sheets-search-replace` | `+cells-find`、`+find`、`--query` |
| 看子表结构（合并 / 行高列宽 / 冻结 / 隐藏） | `+sheet-info` | `lark-sheets-sheet-structure` | `+sheet-get`、`+structure-get`、`+sheet-structure-get` |
| 看工作簿 / 子表清单 | `+workbook-info` | `lark-sheets-workbook` | `+sheet-list`、`+workbook-get`、`+workbook-list` |
| 复核某次（AI）编辑改了什么 / 取两个版本间的变更 | `+changeset-get --start-revision <编辑前版本>`（省略 `--end-revision` 取到最新；版本差 ≤ 20） | `lark-sheets-changeset` | — |
| 取当前文档 revision（版本号） | `+revision-get` | `lark-sheets-workbook` | — |
| 导出 xlsx / 单表 csv | `+workbook-export` | `lark-sheets-workbook` | — |
| 导入本地 xlsx/xls/csv 文件为飞书电子表格 | `+workbook-import --file ./x.xlsx`（本地表格文件 → 飞书电子表格的正解；仅要导成多维表格 bitable 时才用 `drive +import --type bitable`） | `lark-sheets-workbook` | `drive +import`（导电子表格时绕了 drive 通道、还要多给 `--type`，应直接用 `+workbook-import`）、把 .xlsx 在本地读成数据再 `+workbook-create` 重灌（多此一举，应直接 `+workbook-import`）、要把文件并入某个**已有在线工作簿**（给它加子表）却用它——import 只会新建独立表，加子表应走 `+sheet-copy` / `+sheet-create` |
| 参考某个**已有在线表**、把多个本地文件 / 数据各作为一张子表**追加**进去（不另起独立表） | 先 `+workbook-info` 拿模板子表 `sheet_id` → `+sheet-copy` 逐张复制模板子表（公式 / 合并 / 分组底色 / 列宽 / 条件格式全继承）再用 `+cells-*` 只改数据；无模板可继承时 `+sheet-create` 建空子表 + `+table-put --sheets/--styles` 写入 | `lark-sheets-workbook` | 把文件 `+workbook-import` / `+workbook-create` 另起一张**独立新表**（目标是并入已有工作簿时就跑偏了；这两条只产新表、不接受已有表定位） |
| 清除内容 / 格式 | `+cells-clear`（范围维度用 `--scope`，取值 content / formats / all） | `lark-sheets-range-operations` | `--type` |
| 批量清除多区域 | `+cells-batch-clear`（`--scope`） | `lark-sheets-batch-update` | `--target` |
| 调整列宽 / 行高 | `+cols-resize` / `+rows-resize`（行、列是两个独立命令） | `lark-sheets-range-operations` | `--dimension`（无此 flag） |
| 分组汇总 / 透视 | `+pivot-create`（默认不传落点 flag → 自动新建子表，零覆盖） | `lark-sheets-pivot-table` | 用 SUMIF / 本地脚本拼一张假透视表 |
| 画图表 / 可视化（柱 / 折线 / 饼 / 条 / 散点 / 组合…） | `+chart-create` | `lark-sheets-chart` | matplotlib / 本地画图再贴图（原生图表可交互、随数据更新） |
| 条件高亮 / 数据条 / 色阶 / 重复值标记 | `+cond-format-create` | `lark-sheets-conditional-format` | `+highlight`、`+conditional-format`、逐格 `+cells-set-style` 硬凑 |
| 筛选 / 只看符合条件的行 | `+filter-create` | `lark-sheets-filter` | pandas filter 后覆盖写回（会毁原数据；要保存多份筛选状态用 `+filter-view-create`） |

> ⚠️ **动手前的触发式必读（按动作判定，不看主场景）**：本次操作只要**涉及样式 / 美化**（底色 / 边框 / 字号 / 对齐 / 数字格式 / 汇总行 / 配色 / 列宽行高），动手前先读 `lark-sheets-visual-standards`；只要**要写飞书公式**，动手前先读 `lark-sheets-formula-translation`（飞书函数与 Excel 有差异，凭直觉迁移易错），**写完后再读 `lark-sheets-formula-verify` 并执行 `+formula-verify` 收尾**。哪怕主任务是"建表 / 展开数据 / 录入"，只要动作里含美化或写公式就适用——别因"这不算专门的美化 / 公式任务"而跳过。
> ⚠️ **两种图片别选错**：图若**绑定某条记录、要随行排序 / 筛选 / 增删**（凭证 / 证件照 / 每行配图，话里带「对应 / 每行 / 这列」等绑定词）→ 单元格图片 `+cells-set-image`；只是自由摆放的装饰（logo / 水印 / 封面）→ 浮动图片 `+float-image-create`。别因「浮动图更好控制 / 更熟」默认选浮动图。
> ⚠️ **纯文本还是数值语义（看数据本质，不看当下用途）**：金额 / 百分比 / 比率 / 计数 / 日期等**本质是量值**的数据 → 一律数值写入，常规二维表用 `+table-put`（`dtypes` 声明类型 + `formats` 设展示格式），版式装不下（多级 / 合并表头的宽表 leaderboard 等）改用 `+cells-set` 传数字（百分比传小数 `0.4`）+ `number_format`，照样显示 `40%` 且数值无损。只有编号 / 身份证 / 单据号这类**本质是标识符**、要字面保真的才用 `+csv-put` 平铺。**几个常见借口都不成立**——"只是 leaderboard / 报表展示不用算""版式复杂""样式以后再刷、先铺文本"都不是把百分比写成 `"40%"` 字符串灌 `+csv-put` 的理由（展示不改变它是数值；类型不能后补，落成文本就回不来）。判据与操作展开见 `lark-sheets-write-cells`「数字还是文本」。
> ⚠️ **要新建子表 / 整表美化 → 别默认「`+csv-put` 写值再事后刷样式」**：`+table-put` / `+workbook-create` 的 `--styles` 能在写数据的**同一步**带全套样式（区域底色 / 边框 / 列宽 / 行高 / 合并），且 `+table-put` 的 payload 里若 sheet 名不在工作簿中会自动新建子表——**纯文本表要新建子表 + 美化时同样走这里**（`--styles` 与列是否 typed 无关），比「`+csv-put` 写值 + 多次 `+cells-batch-set-style` / `+*-resize` 刷样式」少好几次调用（冻结行列等 sheet 级属性仍需 `+dim-freeze` 单独一步）。
> ⚠️ **定位 flag**：`+cells-get` / `+cells-set` / `+csv-get` 用 `--range`；`+csv-put` 规范用 `--start-cell`（单个左上角锚点格），也接受 `--range` 别名（区间自动取左上角），二者择一即可。
> ⚠️ **读取附加信息**一律走 `+cells-get --include …`，**没有** `--with-styles` 这类 flag；**看合并单元格**用 `+sheet-info` 的 `merged_cells`，不要在 `+cells-get` 里找 merge flag。

### 执行要点（读取 / 原生工具 / 陷阱）

准则的实操展开。端到端工作流：了解结构 → 读数据 → 理解语义 → 原生工具优先 → 写入 → 回读验证。

#### 读取：按需求选路径（细则见 `lark-sheets-read-data`）

| 用户需求 | 读取路径 |
|---|---|
| "完善 / 补齐 / 填空 / 修正所有 XX"、分析 / 清洗 / 大数据 | 原生优先（公式 / `+pivot` / `+filter`）；表达不了再分批 `+csv-get` 导出 + 脚本处理 + 分批回写（默认覆盖所有对应数据行，不以用户选区为准） |
| "查一下 / 看看 / 统计 / 汇总"等只读 | `+csv-get` 读到上下文 |
| 需要公式 / 样式 / 批注 | `+cells-get` |
| 续写 / 扩展已有内容 | `+csv-get` 看结构 + `+cells-get` 读源区样式 + `+sheet-info --include row_heights,merges`（见准则 5） |

> "补齐 / 填空"类用只读路径探 10 行就写会漏写表尾——写入前先按 `lark-sheets-read-data` 确认真实数据末行（准则 3）。

#### 计算：原生工具优先，代码兜底（强化准则 7）

| 用户需求 | 用原生 | 禁止的替代 |
|---|---|---|
| 按 X 统计 Y、分组汇总 | `+pivot-{create\|update\|delete}` | pandas groupby → 写值 |
| 求和 / 计数 / 平均 / 占比 | 公式 | Python 算 → 写静态值 |
| 图表 / 可视化 | `+chart-*` | matplotlib |
| 条件高亮 / 色阶 | `+cond-format-*` | 逐格设样式 |
| 筛选 | `+filter-*` | pandas filter → 覆盖写入 |
| 文本提取 / 转换 / 查找 | 公式（REGEXEXTRACT / TEXT / VLOOKUP 等） | Python → 写静态值 |

只有多步清洗、统计建模、公式试错 3 次仍失败时才用代码。

#### 用脚本配合 CLI 时

- **只读 stdout**：CLI 数据走 stdout、诊断走 stderr；解析 JSON 别 `2>&1`（警告混入会解析失败），用管道或单独重定向 stdout。
- **喂 CLI 的 CSV / JSON 用 UTF-8 无 BOM**；临时文件放系统临时目录、勿落项目目录。
- **命令失败先读 stderr 再调整**，别原样重发。
- **回写纯单元格值**：剥离 `值(V-Align: bottom)` 这类"值(样式)"串与残留引号再写；排序优先 `+range-sort` 原生工具，别"读出本地排完再整列写回"。

#### 易漏陷阱

- **`+dim-insert` 不继承行高**：只继承值 / 公式 / 边框，新行回落默认高度截断长文本；插行填长文本前读相邻行 `row_height`，用 `+batch-update` 合 `+rows-resize` 补齐。
- **公式容错**：日期 / 查找 / 数值转换公式用 `IFERROR` 包裹；写完读结果列首末各 5 行查 `#VALUE!` / `#REF!` / `#DIV/0!`，然后继续跑 `+formula-verify` 直到 `status='success'`；同一方案试错上限 3 次。
- **循环引用**：聚合公式引用范围不能含目标 cell 自身或其传递依赖。
- **隐藏行列**：`+csv-get` 默认含隐藏行列；设 `--skip-hidden=true` 只看可见，但返回行序号与实际行号不再对应。
- **跨 sheet 对象**：图表 / 条件格式 / 透视表 / 浮动图片可能分布在多个子表，操作前先 `+workbook-info` 掌握全局。
- **NLP 任务分批**：语义理解 / 翻译 / 改写 / 分类等用 NLP 处理（代码只做分批 / 行号映射 / 写回）；数据量大必须分批（通常 30 行 / 批），每批处理完即时写回，单批生成通常 ≤ 300 行，多批用 `+batch-update`。

### References

本 skill 的 reference 分两组：先读**通用方法与规范**（横切所有任务的样式、公式规则，不含具体 shortcut），它们规定了"怎么做对"；再按操作对象进入**工具参考**查具体 shortcut 与调用细节。编辑类任务务必先过一遍通用方法与规范，连同上方「飞书表格编辑准则」对所有工具参考一律生效。

#### 通用方法与规范（先读，横切所有任务，不含具体 shortcut）

| Reference | 描述 |
| --- | --- |
| [飞书表格样式与配色规范](references/lark-sheets-visual-standards.md) | 飞书表格样式与配色规范：表头/数据区/汇总行的颜色、字号、对齐、边框、数字格式等取值标准，以及从零新建表格的版式美化、新增汇总行、追加行列继承原表风格、已有区域美化等典型场景的决策流程与样式要点。工具调用参数细节请参考对应的 lark-sheets-write-cells / lark-sheets-range-operations / lark-sheets-batch-update。条件格式（高亮、标红、数据条、色阶）请使用 lark-sheets-conditional-format。 |
| [飞书表格公式生成规则](references/lark-sheets-formula-translation.md) | Excel 公式到飞书表格公式的迁移与生成规则。核心目标不是保留 Excel 原语法，而是按飞书表格可执行规则重写公式，并在结果上尽量对齐 Excel。当用户要求把 Excel 公式改写成飞书表格公式，或需要生成飞书公式（尤其涉及 ARRAYFORMULA、原生数组函数、INDEX/OFFSET、MAP/LAMBDA、日期差、多层范围结果与二次展开）时使用。本文只负责把公式写对，落表后的强制收尾请接 `lark-sheets-formula-verify`。 |
| [金融/财务建模与财务数据整理规范](references/ref-financial-modeling-standards.md) | **引擎无关**的金融/财务/估值建模专业结构与视觉规范，**飞书在线表格与 Python/openpyxl 生成的 `.xlsx` 同样适用**：DCF / LBO / Comps / Precedent、三张财务报表、预算与 Variance Analysis、Sensitivity / Scenario、FP&A 等，**以及“把财务数据整理成表/Excel”“以财务为输入的推算”等看似“只是数据整理”的任务**。覆盖科目分类、三表勾稽、Assumptions / Calc / Sensitivity 拆分、年份横向布局、假设颜色编码、财务数字格式、Sensitivity 禁色阶等（含 Python 代码示例）。与通用视觉规范冲突时以本文为准；用户明确样式或既有模板优先。**做任何财务性质表格前必读必守。** |

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

各 reference 的每个 shortcut 标题下用一行徽章标注该 shortcut 支持的公共 / 系统 flag，例如：

- `_公共四件套 · 系统：--dry-run_` — URL/token + sheet 定位（两组各**必给一个**，详见下方「公共 flag」），加 `--dry-run`
- `_公共：URL/token（无 sheet 定位） · 系统：--yes、--dry-run_` — 只接 URL/token，常见于 `+batch-update` 等不强制 sheet 定位的 shortcut

徽章里只列名字。type / 必填 / 描述都在本段统一声明：

#### 公共 flag（定位资源）

**公共四件套** = `--url` / `--spreadsheet-token` / `--sheet-id` / `--sheet-name`，分成两组 XOR，**每组都必须给且只能给一个**（XOR = 二选一必填，不是"可选"）：

1. **spreadsheet 定位（必填）**：`--url` 与 `--spreadsheet-token` 二选一，**必须给其中之一**。两个都不给 → 校验报错 `specify at least one of --url or --spreadsheet-token`；两个都给 → 互斥冲突。
   - **`--url` 解析 `/sheets/`、`/spreadsheets/` 与 `/wiki/` 三种链接**（从路径里抽出 token；也可以直接把裸 token 传给 `--spreadsheet-token`）。其它形态的链接不会被解析成表格 token。
   - **`/wiki/` 知识库链接可直接传 `--url`**：会自动定位到链接背后的电子表格；若该链接背后不是电子表格（而是文档 / 多维表格等），则报错。
   - **例外**：`+workbook-create`（新建表 + 可选写入数据）与 `+workbook-import`（把本地文件导入为新表）都产出一张**还不存在**的表格，**不接受任何 spreadsheet / sheet 定位 flag**——`+workbook-create` 只有 `--title` / `--folder-token` / `--values` / `--styles` / `--sheets`，`+workbook-import` 只有 `--file`（必填）/ `--folder-token` / `--name`。
2. **sheet 定位（公共四件套 shortcut 必填）**：`--sheet-id` 与 `--sheet-name` 二选一，**必须给其中之一**。两个都不给 → 校验报错 `specify at least one of --sheet-id or --sheet-name`。
   - ⚠️ **不确定 sheet 名时禁止直接猜 `Sheet1`**：除非用户对话明确说出 sheet 名 / id，或上下文（之前的工具调用 / URL 锚点 `?sheet=xxx`）已经出现过具体值，否则**第一步先调 `+workbook-info --url "..."`**（或 `--spreadsheet-token`）拿 `sheets[].sheet_id` / `sheets[].title` 列表再选。中文环境下子表常叫"数据" / "Sheet"（无数字）/ "工作表 1" / 业务名，猜 `Sheet1` 大概率撞 `sheet not found`，比先查多耗一次失败调用 + 重试。
   - ⚠️ **`--range` 里的 `Sheet1!` 前缀不能替代 sheet 定位**：即使写了 `--range 'Sheet1!A1:B2'`，仍**必须**额外传 `--sheet-id` 或 `--sheet-name`，否则照样报上面的错。
   - ⚠️ **A1 reference 含 `!`**（`--source` / `--range` / `--ranges`）**：整段用单引号包裹**，如 `--range 'Sheet1!A1:B2'`——单引号能挡住 bash 的 history expansion（`!` 被拦成 `event not found`；双引号挡不住；别改用 `set +H`，原因见下方「复合 JSON / 大入参」）。sheet 名含特殊字符（`-` / 空格 / 非 ASCII）需在内部按 A1 标准再包一层单引号时，用 `'\''` 转义保持外层单引号，如 `--source ''\''Sales-2025'\''!A1:D100'`。
   - **例外**：徽章标为 `_公共：URL/token（无 sheet 定位）…_` 的 shortcut（如 `+workbook-info` / `+workbook-export` / `+batch-update` / `+dropdown-update|delete` / `+cells-batch-set-style` / `+cells-batch-clear` / `+sheet-create`）**不接受也不需要** sheet 定位，只给一组 spreadsheet 定位即可。`+pivot-create` 用 `--target-sheet-id` / `--target-sheet-name`（XOR，可都不传，落点细节见 `lark-sheets-pivot-table`）。

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--url` | string | 二选一必填（与 `--spreadsheet-token`） | spreadsheet 或 wiki URL |
| `--spreadsheet-token` | string | 二选一必填（与 `--url`） | spreadsheet token |
| `--sheet-id` | string | 二选一必填（与 `--sheet-name`；仅公共四件套 shortcut） | 工作表 reference_id |
| `--sheet-name` | string | 二选一必填（与 `--sheet-id`；仅公共四件套 shortcut） | 工作表名称 |

**统一调用范式**（公共四件套 shortcut 的所有示例都遵循此形状，两组定位缺一不可）：

```bash
lark-cli sheets <shortcut> <workbook 定位> <sheet 定位> <其它 flag>
#   workbook 定位：--url "..."        或 --spreadsheet-token "..."           （二选一，必给）
#   sheet 定位：    --sheet-id "$SID"  或 --sheet-name "<真实表名>"            （二选一，必给；占位符不要原样填）
# 例：lark-cli sheets +csv-get --url "https://.../sheets/shtXXX" --sheet-name "<真实表名>" --range "A1:F30"
# 注意：真实表名不要直接填 "Sheet1"——大多数表的子表不叫这个；先 +workbook-info 拿 sheets[].title 再代入。
```

#### 系统 flag

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--dry-run` | bool | 否 | 零副作用：仅打印请求路径与参数模板，不发起调用；多步操作会输出每个子操作的请求模板 |
| `--yes` | bool | 是（仅 `high-risk-write`） | 二次确认；不带时退出码 10。 |
| `--print-schema` | bool | 否 | 本地打印复合 JSON flag 的 JSON Schema 并退出，不发起任何调用、不需要其它 required flag。与 `--flag-name <name>` 搭配指定要查哪个 flag；省略 `--flag-name` 时列出该 shortcut 所有可查询的 flag。**仅在 shortcut 含复合 JSON flag 时有效**——判断方法：该 shortcut 的 Flags 表里出现类型标注为「复合 JSON」的 flag（如 `--cells` / `--properties` / `--operations` / `--border-styles` / `--sort-keys` / `--options`）即支持；纯标量 flag 的 shortcut 不支持。 |
| `--flag-name` | string | 否 | 配合 `--print-schema` 使用，指定要打印 JSON Schema 的 flag 名（不带 `--` 前缀，如 `cells` / `properties` / `operations`）。 |

**Agent 使用提示**：写复合 JSON flag（`--cells` / `--properties` / `--operations` / `--border-styles` / `--sort-keys` / `--options` 等）时，如果对结构不确定，先跑 `lark-cli sheets <shortcut> --print-schema --flag-name <name>` 把完整 JSON Schema 读出来再构造 payload，比靠 reference 的速查表更精确，也避免因为字段拼写或缺失被服务端拒绝。reference 的 `## Schemas` 段只给一层结构，深层只能靠 `--print-schema` 或 `## Examples` 的真实示例。

#### flag 内容类型与输出约定（术语速记）

- flag 表里 JSON 类入参标三类：**复合 JSON** = 深层嵌套对象（用 `--print-schema` 取完整结构）；**简单 JSON** = 一维 / 二维标量数组（如 `["sheet1!A1:B2",...]` / `[["alice",95]]`，结构简单无需 print-schema）；**非 JSON 文本** = 原样文本（如 CSV）。`--print-schema` 只对**复合 JSON** flag 有效（同一 shortcut 的简单 JSON flag 如 `--colors` 不在此列）。
- **envelope**：所有 shortcut 返回统一外层结构 `{ok, identity, data, ...}`。正文里 `envelope.data` 指业务数据层（如 `+csv-get` 的 `annotated_csv`）；写操作不会自动回读，如需校验请自行调用对应的 `+*-list` / `+*-get` / `+cells-get`。

### 复合 JSON / 大入参：优先 stdin

flag 帮助里标注支持 **Stdin** 的入参，当 payload 较大、含换行 / 引号等特殊字符，或已经落在某个文件里时，优先用 stdin（`-`）传入，避免命令行超长与 shell 转义问题。

推荐写法：payload 写到用户项目目录之外的临时文件（放系统临时目录，避免污染项目），再用 stdin 喂进去：

```bash
# TMPFILE 指向系统临时目录下的 payload 文件（脚本里用 tempfile.gettempdir() / os.tmpdir() 等取临时目录）
lark-cli sheets +cells-set --url "..." --sheet-name "Sheet1" --range "A1:B2" --cells - < "$TMPFILE"
```

**参数含特殊字符（`!` / 引号 / 空格 / 非 ASCII）时，用单引号包裹该参数即可，不要起手 `set +H` 之类的 shell 开关来防转义。** `set +H`（关 bash history expansion）在 `sh` / `dash` 下是非法选项（`set: Illegal option -H`）、会让整条命令直接失败；而单引号挡得住 `!` 的 history expansion（否则报 `event not found`），对 bash 与 `sh` / `dash` 一致安全。参数本身含单引号、或 payload 较大时，按上文走 stdin。

**`@file` 接绝对路径会被拒，且被拒后不要照报错提示做。** `@file` 出于安全只接受 cwd 下的相对路径，传 cwd 之外的绝对路径会被拒。此时报错会建议"先 cd 到目标目录，或改用相对路径"——**两条都不要照做**：cd 过去、或把临时文件写进用户项目目录，都会污染工作目录。正解是改用 stdin（`--<flag> - < 文件`）。

---

## 四、Excel（.xlsx）输出质量规范（Python 引擎）

**只要本流程中生成了 `.xlsx` 文件，本部分就适用——不论该 `.xlsx` 是最终交付物，还是先生成再 `lark-cli sheets +workbook-import` 导入飞书的中间产物。** 具体包括两种情况：

1. 用户明确要本地 `.xlsx` / 禁止飞书（见 0.2），`.xlsx` 即最终交付物；
2. 最终产物是飞书在线表格，但实现路径是「先用 Python(openpyxl) 生成 `.xlsx`，再 `lark-cli sheets +workbook-import` 导入飞书」——因为导入后的飞书表格质量完全取决于源 `.xlsx`，所以**在 `.xlsx` 阶段就必须达到本部分标准**，不能指望导入后再补。

> 注：按 0.3，飞书产物**优先**用飞书引擎一步到位（`+workbook-create --sheets` + `--styles`），无需经 `.xlsx`；但只要实际走了「生成 `.xlsx` 再导入」这条路（如重数据加工、或既有 `.xlsx` 资产），该 `.xlsx` 就要满足本部分规范。

所有输出 Excel 必须满足以下标准（含格式、行高/列宽/截断、公式重算与验证）。详细技术工作流参见 `references/ref-xlsx-workflow.md`。

### 基础规范

| 项目 | 要求 |
|------|------|
| **字体** | 全文使用统一专业字体（如 Arial、宋体），不同区域字体一致 |
| **公式错误** | 交付前避免出现公式错误（`#REF!` `#DIV/0!` `#VALUE!` `#N/A` `#NAME?`），用 `scripts/formula_verify.py` 检查 |
| **现有模板** | 修改已有文件时，精确匹配其格式、样式和规范；现有模板约定优先于本规范 |
| **公式 vs 硬编码** | 计算结果必须写成 Excel 公式（如 `=SUM(B2:B9)`），**不得**在 Python 中算好再硬编码写入单元格 |

### 列宽行高自适应规范

生成或修改 Excel 表格时，列宽和行高必须根据内容自适应，确保表格不拥挤、不浪费空间。

**列宽**：扫描该列所有单元格，取最长内容的显示宽度（中文字符按 2 宽度）+ padding 3 字符。下限 8、上限 40。超过上限的列启用 `wrap_text=True` 自动换行。

**行高**：表头行 30、普通数据行 20、汇总行 26、含换行单元格的行 36。

**内边距**：通过列宽 padding（+3）和行标签列 `Alignment(indent=1)` 提供呼吸空间。

上述列宽/行高规则**适用于所有新建 Sheet 和表格区域**；可用 `scripts/format_range.py` 批量应用，单元格排版细节（行高/列宽/截断）见 `references/ref-xlsx-workflow.md`。修改用户现有模板时保持原有行高列宽不变（除非用户要求调整）。

### 样式与图表脚本（优先使用）

涉及单元格批量样式（字体/底色/边框/数值格式/条件格式）或图表生成时，**优先调用以下 CLI 脚本**，避免重复手写 openpyxl 代码：

| 脚本 | 用途 | 典型用法 |
|------|------|---------|
| `scripts/format_range.py` | 批量格式化范围（含条件格式、合并） | `python scripts/format_range.py <file> <sheet> A1:E1 --bold --bg-color FFFF00 --align center` |
| `scripts/create_chart.py` | 在 sheet 创建 bar/line/pie/scatter/area 图表 | `python scripts/create_chart.py <file> <锚点sheet> 'Data!A1:E6' bar G2 --title '季度销售'` |

两个脚本输出 JSON，失败时 `status: error`。详细参数见脚本 `--help`。条件格式参数走 JSON 串：`--cond-format '{"type":"color_scale","params":{...}}'`，支持 `color_scale / data_bar / icon_set / formula / cell_is`。

### ref-xlsx-workflow.md 中的进阶能力索引

下列场景出现时，**直接跳到** `references/ref-xlsx-workflow.md` 对应小节，不要从零写代码：

| 场景信号 | 跳到的小节 |
|---------|-----------|
| “复制这块/把 A 表的格式搬到 B 表/保留样式复制” | “范围复制（含样式）” |
| “把这一段清掉/删除并上移/重置区域格式” | “范围清空与重置” |
| 写公式前想拦住语法错/避免不安全函数 | “公式写入前自检” — 与 `formula_verify.py` 形成事前+事后闭环 |
| 用户上传表里有下拉框/限制输入/打开报错“内容存在问题” | “读取数据验证规则（下拉框 / 输入限制）” |
| “把这块做成可筛选的表/带表头排序/Excel Table” | “标准 Excel Table（ListObject）” |

### 财务/金融场景（Excel 产物）

> ⚠️ **产物为 `.xlsx` 时，`references/ref-financial-modeling-standards.md` 同样必读必守，不是飞书专属。** 该规范是引擎无关的财务呈现/逻辑规范，其 Python(openpyxl) 代码示例就是为 `.xlsx` 产物准备的。**只要表里是财务数据——哪怕任务被描述成“把某公司财务数据整理成 Excel”“以财务为输入做推算”——都要先读它再写代码。** 不要以“只是 openpyxl 生成数据表、不是可交互模型”为由跳过。

用 Python 生成 `.xlsx` 时，在「四」通用规范基础上，**完整套用** `ref-financial-modeling-standards.md` 的财务逻辑与视觉规范（科目标准分类、三表勾稽、颜色编码：蓝=输入/黑=公式/绿=跨表引用/红=外链、数字格式：货币/零值显示 `-`/负数括号/倍数 `0.0x`、单位与来源标注、Assumptions/Calc/Sensitivity 多 sheet 拆分、年份横向布局、合计边框、Sensitivity 禁色阶/数据条等）。简单的财务数据整理表按该文件「按任务裁剪」取最小规则集（颜色/数字格式/单位/合计边框），但不可一条不用。

**优先级**：用户指令 / 用户模板样式 > `ref-financial-modeling-standards.md`（金融行业惯例）> 本文档通用规范。与通用视觉规范冲突时以金融规范为准（典型冲突：财务模型禁斑马纹、Sensitivity 禁条件格式/色阶/数据条、年份列须紧凑等宽、不加竖线、主题色仅黑白+蓝/绿）。

---

## 五、References 与脚本总览

引擎无关 / Excel 引擎 reference：

| 文件 | 引擎 | 用途 |
| --- | --- | --- |
| `references/guide-semantic-analysis.md` | 引擎无关 | 文本语义抽取/归类/标准化/汇总方法学 |
| `references/template-report.md` | 引擎无关 | 数据分析报告输出模板 |
| `references/ref-xlsx-workflow.md` | Excel | Excel 创建/编辑/公式重算/范围复制/数据验证等技术工作流 |

飞书引擎 reference（17 个）见「三、References」表，那里有更详的选用说明；完整文件清单以 `references/` 目录为准。

脚本（`scripts/`）按引擎分别标注：飞书引擎用 `sheets_df.py`（DataFrame → `--sheets` typed payload，含 `df_to_sheet`）；Excel 引擎用 `inspect_workbook.py`（结构预检）、`preview_excel_rows.py`（多行表头预览）、`formula_verify.py`（公式重算与校验）、`format_range.py`（批量样式/条件格式）、`create_chart.py`（图表）、`_excel_utils.py` / `lo_runtime.py`（内部工具）。
