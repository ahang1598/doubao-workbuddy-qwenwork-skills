# 金融/财务建模与财务数据整理规范

## 定位与优先级

本文是**财务/金融场景的操作与视觉规范**，与执行引擎无关——无论产物是 Python（openpyxl）生成的本地 `.xlsx`，还是飞书在线表格，只要表格里承载的是财务性质的数据，就必须遵守本文。

### 动手前先分叉：新建模型 vs 美化已有表

本文的规则怎么用，取决于输入是"从零建"还是"已成型"——先判断再动手：

- **从零构建，或把零散数据整理成一张新表**（用户未提供成型模型表，或明确要你新建）→ 本文全套适用：报表结构、公式写法、年份布局、多 sheet 拆分、Sensitivity 布局都由你按规范搭建。
- **输入已是一张成型的模型表**（给了在线表格或附件文件，要求"美化 / 规范化 / 保留计算逻辑 / 更新到原表"）→ 这是**美化已有表，不是重建**：只在原表上就地调整样式属性（字体 / 填充 / 边框 / 对齐 / 数字格式），本文关于报表结构、公式、Sensitivity 与布局、多 sheet 拆分的规则**只用于你新增的内容，不得用来改动原表的既有结构、公式和布局**。此分支下必须守住两条：
  - **原表已有公式一律原样保留**（各类 IRR / 汇总 / 引用公式等），禁止用你认为更规范的写法替换。"公式优先"针对的是"新算的派生值别写成死值"，**不是**"重写原表已有的公式"；保留原计算逻辑优先于任何格式规范。
  - **禁止"重建"反模式**：从零重建整张表再整体覆盖原表；清空原表区域再灌入重建版；新建一张"美化版"子表承载重排后的布局。这些都会丢掉原表的合并单元格、图表数据源列、原公式与原布局。具体的就地样式化实现，按下方「落地提示（按引擎）」选择对应方式。

适用范围（看到这些信号一律适用，不要因为"任务看起来只是整理数据"就跳过）：

- **估值与建模**：DCF / LBO / Comps / Precedent、资本结构、Unit Economics、Market Sizing。
- **财务报表**：三张财务报表（IS / BS / CFS）、财务预测、预算与 Variance Analysis、Sensitivity / Scenario Analysis。
- **财务数据整理 / 标准化 / 汇总**：把某公司的营收、成本、利润、现金流、估值等数据整理成一张表（哪怕用户只说"整理成 Excel""做个表"），也属于本规范——它是"财务报表整理"，不是普通数据表。
- **以财务数据为输入的推算 / 经营分析**：例如从财务成本反推算力、产能、获客成本、单位经济等。即使核心难点是业务推算、Python 只是用来算数，**最终承载财务数字的那张表仍必须按本规范呈现**。
- 投研 / 投行 / PE / Equity Research / FP&A / 咨询场景的任何表格产出。

> ⚠️ **三个最常见的误判，先纠正：**
> 1. **"这只是数据整理 / 推算，不是专业财务建模，用不上规范。"** —— 错。只要表里是财务数字（营收、成本、利润、现金流、估值、算力成本反推等），就按本规范呈现。数据整理表 = 简化版财务报表，同样要颜色编码、数字格式、单位标注、年份横向、合计边框。
> 2. **"我是用 Python/openpyxl 生成 .xlsx，不是在表格里直接搭可交互模型，所以规范不适用。"** —— 错。本规范是**呈现与逻辑规范**，与用什么工具生成无关。openpyxl 写出来的财务表，同样要遵守。
> 3. **"规范全在讲 DCF/LBO/三表勾稽这种重模型，我这个简单表用不上。"** —— 错。见下方「按任务裁剪」：简单表只取轻量规则（颜色、数字格式、单位、合计边框），但**不是一条都不用**。

优先级从高到低：

1. 用户明确指令或既有模板样式。
2. 本金融/财务建模规范。
3. 通用核心操作、视觉规范与公式规则。

如果本文与通用视觉规范冲突，以本文为准。典型冲突：

| 通用规范 | 财务模型规范 |
| --- | --- |
| 数据行较多时可使用斑马纹 | 财务模型默认禁止斑马纹，避免干扰小计/合计识别 |
| 可用数据条、色阶强化可视化 | Sensitivity 禁止色阶、数据条和图标集 |
| 列宽按内容自适应 | 年份列必须紧凑等宽；标签列才加宽 |
| 可用柔和竖线分隔区域 | 普通财务模型禁止竖线；Sensitivity 矩阵浅灰细框是唯一例外 |

## 按任务裁剪

不要把全套 DCF 规范套到简单费用表；但也**不要因为任务"简单"就一条规范都不用**。先判断任务类型，再选择规则。

| 任务类型 | 必用规则 | 不要做 |
| --- | --- | --- |
| **财务数据整理 / 汇总 / 标准化**（含"把某公司财务数据整理成 Excel"） | 科目分类、颜色编码、数字格式、单位与来源、年份横向布局、小计/合计边框 | 不需要 Sensitivity；不强行拆多 sheet |
| 三表整理 / 标准化 | 上一行全部 + 三表结构、勾稽验证 | 不需要 Sensitivity |
| DCF / LBO / 估值模型 | 假设/计算/输出分层，多 sheet 拆分，横向年份，假设单独落地，公式引用假设，Sensitivity 按需独立 | 不要把假设硬编码进公式 |
| Comps / Precedent | 科目口径、颜色编码、数字格式、单位、分区和小计样式 | 通常不需要三表勾稽，不强制拆多 sheet |
| 预算 / Variance Analysis | 颜色编码、数字格式、横向期间、差异列公式、汇总边框 | 不需要 Terminal Value / WACC |
| 以财务为输入的推算（算力/产能/单位经济反推等） | 承载财务数字的表按"财务数据整理"规则；推算的关键中间量与结果也用表格呈现并标注来源/口径 | 不要只把结果硬写成一团数字、缺颜色编码与单位 |
| 单项 Sensitivity / Scenario | 假设分离、Sensitivity 专用视觉规范、baseline 标注 | 不使用色阶/数据条 |

## 财务逻辑规范

### 科目标准分类

整理原始科目时，不能把 raw data 机械拼接成报表。必须按 GAAP / IFRS 和财务建模惯例分类。

Income Statement 关键分类：

| 分类 | 示例 | 常见错误 |
| --- | --- | --- |
| Revenue | Product Revenue、Service Revenue、Subscription、License | 把 Other Income 混入主营收入 |
| COGS | 直接人工、直接材料、制造费用、SaaS hosting/infrastructure、支付处理费 | 把 Implementation SG&A / Customer Success 误归 COGS |
| SG&A | G&A、Sales & Marketing、Implementation SG&A、Customer Success、Operations SG&A、Shared Service | 把 Marketing 误归 COGS；漏掉分摊费用 |
| R&D | Research、Product Development、Engineering Payroll | 并入 G&A |
| D&A | Depreciation、Amortization | 埋在 COGS 或 SG&A 里 |
| Non-operating | Interest、FX、One-time Items | 和 Operating Income 混淆 |
| Tax | Income Tax Expense / Benefit | 当作经营费用 |

Balance Sheet 按 Current / Non-current 拆分 Assets、Liabilities、Equity；Cash、AR、Inventory、Prepaids 属 Current Assets，PP&E / Goodwill / Intangibles 属 Non-current Assets，AP / Accrued / ST Debt / Deferred Revenue 属 Current Liabilities，LT Debt / Deferred Tax 属 Non-current Liabilities。

Cash Flow Statement 使用间接法：Net Income 起步，加回 D&A / SBC，调整 Working Capital 和 Deferred Tax，分 CFO / CFI / CFF，最终 Ending Cash 必须等于 BS Cash。

### 标准报表结构

Income Statement 自上而下：

```text
Revenue
  Total Revenue
- COGS
  Total COGS
= Gross Profit
  Gross Margin %
- Operating Expenses
  Total OpEx
= EBITDA
  EBITDA Margin %
- D&A
= EBIT
- Interest / Other Income (Expense)
= Pre-tax Income
- Tax
= Net Income
  Net Income Margin % / EPS
```

Balance Sheet 必须有 `Total Assets`、`Total Liabilities`、`Total Equity`、`Total Liabilities & Equity` 和 `Check: Total Assets - Total L&E = 0`。

Cash Flow Statement 必须有 CFO、CFI、CFF、Net Change in Cash、Beginning Cash、Ending Cash，并校验 Ending Cash = BS Cash。

DCF 标准骨架：

```text
1. Key Assumptions
2. Revenue / EBITDA / EBIT / NOPAT
3. + D&A - CapEx - Change in NWC = UFCF
4. Discount Factor / PV of UFCF
5. Terminal Value
6. Enterprise Value -> Equity Value -> Implied Share Price
7. Sensitivity / Scenario
```

### 多 sheet 拆分

专业模型按 Input -> Calc -> Output 分层，复杂模型必须拆分：

- DCF / LBO：`Assumptions`、`DCF - Calc`、`Sensitivity`、`Output / Summary`，可选 `Source Data`。
- 三表模型：`Assumptions`、`IS`、`BS`、`CFS`、`Supporting Schedules`、`Check`。
- 带 Sensitivity 的任何模型：Sensitivity 必须独立 sheet 或独立清晰区块。

简单报表整理、费用汇总、Variance Analysis、单页 Comps/Precedent、总行数小于 40 的单一逻辑块可以不拆 sheet。

跨 sheet 引用规则：

1. 引用路径写完整 sheet 名，如 `='Assumptions'!$B$7`；sheet 名含空格或特殊字符时加单引号。
2. 数据流单向：`Assumptions -> Calc -> Sensitivity -> Output`。
3. 禁止循环引用；Sensitivity 直接引用 Calc 结果，不链式穿透多个中间 sheet。

```python
# ── 跨 sheet 引用示例（openpyxl）──
# Assumptions 表：蓝色输入（严禁写公式）
ws_asm['B7'] = 0.10                                          # WACC
ws_asm['B7'].font = blue_font
ws_asm['B8'] = 0.05                                          # Revenue Growth
ws_asm['B8'].font = blue_font

# Calc 表：含跨表引用 → 绿色
ws_dcf['E20'] = "='Assumptions'!$B$7"                        # WACC（纯跨表）
ws_dcf['E20'].font = green_font
ws_dcf['F7']  = "=E7*(1+'Assumptions'!$B$8)"                # 上年 Revenue × (1+增长率)
ws_dcf['F7'].font = green_font                              # 混了跨表 → 绿色
ws_dcf['F20'] = "=F18*(1-'Assumptions'!$B$9)"              # EBIT × (1-Tax Rate)
ws_dcf['F20'].font = green_font
```

### 年份横向布局

时间必须横向排布，科目纵向排布。所有相关 sheet 的年份列必须对齐。

正确示例：

```text
                FY2023A   FY2024A   FY2025E   FY2026E
Revenue             500       575       644       708
EBITDA              125       155       180       205
```

假设值如果按年度变化，也必须横向排布并与计算 sheet 的年份列一一对齐：

```text
                        FY2025E   FY2026E   FY2027E
Revenue Growth %          12.0%     10.0%      9.0%
EBITDA Margin %           25.0%     26.0%     27.0%
CapEx % of Revenue         5.0%      5.0%      4.5%
Tax Rate                  25.0%     25.0%     25.0%
```

永续性假设如 WACC、Terminal Growth 可以单独放在 Assumptions 上方，不按年份展开。

历史与预测用年份后缀 + 字体颜色区分（A=Actual / E=Estimate / B=Budget），不靠竖线：历史数值黑色；预测期公式黑色、预测期假设输入蓝色。

### 假设值与公式

可被用户修改的假设必须集中放在 Assumptions 区或 sheet，用蓝色字体标识，并由公式引用。禁止把 Growth、Margin、WACC、Tax Rate、CapEx %、Terminal Growth、倍数等硬编码在公式里。

只有三类单元格可直接写静态值：

1. 历史真实数据。
2. 蓝色输入假设。
3. 外部来源的静态取数，且必须标注来源。

> 🚨 **公式优先是财务建模的铁律，最高频违规是"用 Python 算好再写死"。**
> 凡是由其他单元格推导出来的数（增长率、占比、同比、各种推算的中间量和结果、GPU 数量/算力换算等），**必须写成引用其他单元格的 Excel 公式**，而不是在 Python 里算出数值再写进单元格。
>
> **不要用下面这些理由给硬编码开脱：**
> - "我先用 Python 算准了（还跑了校验脚本）再写入，结果是对的。" —— 结果对≠合规。硬编码的表**没有动态计算能力**：用户改一个假设，全表不会联动更新，等于交付了一张"死表"。Python 脚本可以用来验证，但**最终落到单元格里的必须是公式**。
> - "这是推算任务，逻辑在 Python 里更好写。" —— 推算逻辑可以在 Python 里推导，但把它**翻译成单元格公式**写进表里；关键输入做成蓝色假设格，让用户能改、能联动重算。
>
> 唯一可直接写静态值的就是本节列的三类：历史真实数据、蓝色输入假设、标注来源的外部静态取数。除此之外**一律写公式**。

```python
# ❌ 错误：假设值硬编码进公式 / 在 Python 里算好写死
ws['E7'] = '=D7*1.05'                  # 5% 增长率藏在公式里
ws['E7'] = 644                          # 直接写死 Python 算出来的结果（最高频违规）
ws['F9'] = 1250                         # GPU 数量：在 Python 里算好写死 → 改成本无法联动

# ✅ 正确：假设独立（蓝色输入）+ 公式引用，全部可联动
ws['B7'] = 0.05                         # 假设单元格
ws['B7'].font = blue_font
ws['B7'].number_format = '0.0%'
ws['E7'] = '=D7*(1+$B$7)'               # 公式引用假设
ws['E7'].font = black_font              # 本表公式用黑色
ws['F9'] = '=F8/$B$12'                  # GPU 数量 = 总算力成本 / 单卡成本（引用假设）
ws['F9'].font = black_font
```

横向拉公式时必须正确使用 `$`：

| 被引用内容 | 正确模式 | 说明 |
| --- | --- | --- |
| 同行逐年变化值 | `A1` | 向右复制时跟随年份变动 |
| 单一永续假设 | `$B$7` | 向右/向下都锁定 |
| 同列假设、逐行变化 | `$B7` | 锁列不锁行 |
| 年份标题行 | `B$4` | 锁行不锁列 |

```python
# ✅ 横向填充时锁死假设、年份相对
for col in ['E', 'F', 'G', 'H', 'I']:
    ws[f'{col}20'] = f'={col}18*(1-$B$9)'   # E18=EBIT, $B$9=Tax Rate
```

写完横向公式后，必须用 `load_workbook(..., data_only=False)` 回读 2-3 个相邻年份列的公式字符串，确认年份引用跟随列移动、被锁定的假设保持不变；再用 `data_only=True`（或 `formula_verify.py`）确认无 `#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?`、`#N/A`。

## 视觉规范

### 字体颜色编码

财务模型用字体颜色表达单元格性质。

openpyxl 的颜色参数用不带 `#` 的 6 位 hex（如 `Font(color='0000FF')`）。

| 颜色 | openpyxl hex | 含义 |
| --- | --- | --- |
| 蓝色字体 | `0000FF` | **直接键入数值的输入格（即假设/驱动项，用户可手动修改）**，如增长率、WACC、税率、单卡成本——这类格子本就该写值不写公式，是"公式优先"原则唯一的例外 |
| 黑色字体 | `000000` | 本 sheet 公式或普通文本 |
| 绿色字体 | `008000` | 同工作簿跨 sheet 引用；公式中只要出现跨 sheet 引用就用绿色 |
| 红色字体 | `FF0000` | 外部文件/外部系统链接，慎用 |
| 灰色斜体 | `808080` + italic | YoY、Margin、Notes、单位说明、数据来源（仅字体，灰色不做背景） |
| 浅黄背景 | `FFF2CC` | 待确认 / 待复核的假设（临时标记，交付前应清除或确认）|

```python
from openpyxl.styles import Font, PatternFill
FONT, SIZE = 'Calibri', 10

blue_font  = Font(name=FONT, size=SIZE, color='0000FF')                   # 直接输入的假设/驱动项
black_font = Font(name=FONT, size=SIZE)                                    # 本表公式
black_bold = Font(name=FONT, size=SIZE, bold=True)                         # 小计/合计
green_font = Font(name=FONT, size=SIZE, color='008000')                   # 跨表引用
red_font   = Font(name=FONT, size=SIZE, color='FF0000')                   # 外部文件引用
aux_font   = Font(name=FONT, size=SIZE, color='808080', italic=True)       # 辅助行：同字号，仅色+斜体
highlight_fill = PatternFill('solid', fgColor='FFF2CC')                    # 待确认（浅黄，临时标记）
```

辅助行字号与正文一致，只靠灰色和斜体区分层级。除 sheet 顶部大标题外，全表正文、分区标题、副标题、辅助行使用统一字号。

> ⚠️ 上表是**字体**颜色编码；**背景填充**另有一套统一配色，见下「背景色与配色」。两者不要混淆：绿 / 红只用于字体（跨表 / 外链），**绝不用于背景**。

### 背景色与配色（统一商务蓝）

除非用户有特殊要求，财务模型的背景填充默认使用**商务蓝配色**；除下表列出的用途外，所有格子一律白底（无填充）。

| 用途 | openpyxl hex | 说明 |
| --- | --- | --- |
| 主表头 / 大标题行 / 一级分区标题 | `0F3B5D` | 深蓝底 + 白色加粗字 |
| 二级表头 / 分组标题 | `3288B9` | 中蓝底 + 白色加粗字 |
| 信息区 / 汇总行 / 三级标题（浅底） | `CFE3F1` | 浅蓝底 + 黑字 |
| 分隔线 | `D0D8E8` | 需细分隔线时用此色（结构仍以边框为主，见「边框」） |
| 浅黄高亮 | `FFF2CC` | Sensitivity baseline 交点 / 需浅色标注的复核项——唯一允许的非蓝高亮 |

硬性规则（直接对应常见翻车点）：

- **大标题行必须有背景色**：sheet 顶部的报表总标题行用 `0F3B5D` 深蓝底 + 白色加粗，不能留白底。（常见错误：大标题没填背景，整张表"没有头"。）
- **禁止用绿色 / 红色做背景色**：区分情景 / 版本（Bull / Base / Bear、乐观 / 中性 / 悲观）也**不要**用绿底 / 红底——太扎眼、不专业。统一用商务蓝，靠**文字标签**（如 "Bull Case" / "Bear Case"）区分；如确需层次区分，在 `0F3B5D` / `3288B9` / `CFE3F1` 三档里选深浅。绿 / 红仅作字体颜色编码（跨表 / 外链），不用于背景。
- **普通数据行白底**：收入 / 费用 / 各类明细行不加任何填充。
- 同层级分区标题用相同背景色 + 相同左右填充列范围；不同层级靠这三档蓝色深浅区分，不靠填充长短区分。

```python
from openpyxl.styles import Alignment
HEADER_BG = '0F3B5D'   # 主表头 / 大标题 / 一级分区
SECOND_BG = '3288B9'   # 二级表头 / 分组标题
LIGHT_BG  = 'CFE3F1'   # 信息区 / 汇总行 / 三级标题（浅底）
LINE_CLR  = 'D0D8E8'   # 分隔线
BASELINE_BG = 'FFF2CC' # Sensitivity baseline（唯一非蓝高亮）

title_font = Font(name=FONT, size=SIZE+2, bold=True, color='FFFFFF')   # 大标题：放大白字加粗
hdr_font   = Font(name=FONT, size=SIZE,   bold=True, color='FFFFFF')   # 分区标题：白字加粗

def section_header(ws, row, c_start, c_end, text, bg=HEADER_BG, font=hdr_font):
    """分区 / 标题行：填背景色 + 合并 + 加粗；所有层级左右边界（c_start~c_end）保持一致。"""
    ws.merge_cells(start_row=row, start_column=c_start, end_row=row, end_column=c_end)
    for c in range(c_start, c_end + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = PatternFill('solid', fgColor=bg)
        cell.font = font
        cell.alignment = Alignment(horizontal='left', vertical='center')
    ws.cell(row=row, column=c_start).value = text

# 大标题行必须有深蓝底；一/二/三级分区左右边界都用同一 c_start~c_end，仅背景色深浅不同
section_header(ws, 1, 2, 14, 'OpenAI 算力推算模型', bg=HEADER_BG, font=title_font)   # 大标题：深蓝 + 放大白字
section_header(ws, 4, 2, 14, '一、训练算力推算',     bg=HEADER_BG)                    # 一级：深蓝
section_header(ws, 5, 2, 14, '训练算力',             bg=SECOND_BG)                    # 二级：中蓝
section_header(ws, 6, 2, 14, '说明 / 信息区',         bg=LIGHT_BG, font=black_font)    # 三级 / 信息区：浅蓝 + 黑字
```

### 数字格式

| 数据类型 | 推荐格式 |
| --- | --- |
| 年份 | `0`，不得显示千分位 |
| 整数 | `#,##0;(#,##0);"-"` |
| 小数 | `#,##0.0;(#,##0.0);"-"` 或 `#,##0.00;(#,##0.00);"-"` |
| 货币 | `$#,##0;($#,##0);"-"` 或 `$#,##0.00;($#,##0.00);"-"` |
| 百分比 | `0.0%` 或 `0.00%`，同一表内保持一致 |
| 估值倍数 | `0.0" x"` |
| 人数/股数 | `#,##0` |

零值显示为 `-`，负数使用括号法 `(123)`。如采用窄货币符号列，符号列单独放 `$` / `¥`，数值列不再带货币符号。

```python
num_int  = '#,##0;(#,##0);"-"'
num_1d   = '#,##0.0;(#,##0.0);"-"'
usd_int  = '$#,##0;($#,##0);"-"'
pct_1d   = '0.0%'
mult_fmt = '0.0" x"'
year_fmt = '0'

# 年份必须防千分位：
for col in year_cols:
    ws[f'{col}{year_row}'].number_format = year_fmt
```

### 单位与来源

单位必须清晰标注：

- 全表单位统一时，在标题下方用灰色斜体副标题标注，如 `($ in Millions, Except Per Share Data)`。
- 同一表存在多种单位时，在字段名后直接标注，如 `Revenue ($mm)`、`Gross Margin (%)`、`员工人数（万人）`、`ARPU, 元/月`。

历史值、外部数据和硬编码来源必须在表尾或注释中标注：`Source: [来源], [日期], [页/表/字段]`。FY、CY、LTM、NTM、CAGR、YoY、QoQ 等缩写必须使用一致口径。**做财务推算时尤其重要**：每个外部取数与关键假设都要可追溯到来源。

### 布局与列宽

**必须关闭默认网格线**。专业财务模型绝不带 Excel 默认网格线，视觉结构完全由边框和背景色表达。每个 sheet 都要执行：

```python
ws.sheet_view.showGridLines = False    # 财务模型硬性要求，逐个 sheet 都要关
```

推荐列宽（openpyxl 的 `column_dimensions[col].width`，约等于字符数）：

| 列类型 | 建议宽度 |
| --- | --- |
| 左侧留白列 | 2 |
| 缩进/货币符号窄列 | 3 |
| 标签/科目列 | 30-40 |
| 年份/期间列 | 8-9，最多约 10，且所有年份列等宽 |

```python
ws.column_dimensions['A'].width = 2      # 左侧留白
ws.column_dimensions['B'].width = 36     # 标签/科目列（宽）
ws.column_dimensions['C'].width = 3      # $ 符号独立列
for col in 'DEFGHIJKLMN':                # 年份列：紧凑且统一
    ws.column_dimensions[col].width = 9
```

分区标题行用于隔离 Key Assumptions、Core Calculation、Terminal Value、Sensitivity 等区块：

- 同层级标题使用相同背景色和**相同的左右填充列范围**（如都从 B 列到 N 列）。
- 不同层级也保持左右边界一致，只用背景色深浅区分层级（一级 `0F3B5D` 深蓝底白字加粗；二级 `3288B9` 中蓝；三级 `CFE3F1` 浅蓝黑字）。配色与 `section_header()` 见上方「背景色与配色」。
- **大标题行必须填 `0F3B5D` 深蓝底 + 白色加粗，不能留白底。**

父子层级通过缩进和加粗表达：父级/合计行加粗，子项正常字重并缩进（`Alignment(indent=1)`）。

### 边框

边框只表达结构，不做装饰。

| 场景 | 边框 |
| --- | --- |
| 小计行 | 上细线 |
| 关键小计，如 Gross Profit / EBITDA / NOPAT / UFCF | 上细线 + 加粗 |
| 最终合计，如 Net Income / Total Assets / Ending Cash / Implied Share Price | 上细线 + 下双线 + 加粗 |
| 普通数据行 | 无边框 |
| 年份列之间 | 禁止竖线 |

```python
from openpyxl.styles import Side, Border
thin, double = Side(style='thin'), Side(style='double')
bd_top   = Border(top=thin)                       # 小计
bd_final = Border(top=thin, bottom=double)        # 最终合计

for c in range(start_col, end_col + 1):
    ws.cell(row=subtotal_row, column=c).border = bd_top
    cell = ws.cell(row=final_row, column=c)        # Net Income / TA / Ending Cash
    cell.border, cell.font = bd_final, black_bold
# ❌ 禁止任何 left=/right= 竖线；禁止给普通数据行加满 4 条边框
```

Sensitivity 矩阵可使用浅灰细框作为唯一例外，目的是表达双轴矩阵结构，不得扩展到普通财务报表区域。

### Sensitivity / Scenario

Sensitivity 必须极简、对称、可读。

禁止：

- 条件格式色阶。
- 数据条。
- 斑马纹。
- 图标集。
- 彩虹配色。

推荐：

1. 行轴和列轴以 baseline 为中心等距展开，如 WACC: 8%, 9%, 10%, 11%, 12%。
2. baseline 交点用浅黄背景 `#FFF2CC` + 加粗标注。
3. 所有结果格使用同一 `number_format`。
4. 标题下方用灰色斜体说明输出指标。

```python
HEADER_BG, BASELINE_BG = 'CFE3F1', 'FFF2CC'    # 轴表头用浅蓝 light_bg；baseline 浅黄
thin_gray = Side(style='thin', color='BFBFBF')
bd = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)

for r in range(6, 11):                              # 数据格：纯白底 + 浅灰细框
    for c in range(3, 8):
        cell = ws.cell(row=r, column=c)
        cell.fill = PatternFill('solid', fgColor='FFFFFF')
        cell.border = bd
        cell.number_format = '$#,##0.00'
ws['E8'].fill = PatternFill('solid', fgColor=BASELINE_BG)   # baseline 交点
ws['E8'].font = black_bold
```

## 交付前检查

任何财务输出（含"数据整理表"和"推算结果表"）必须检查：

- 已按任务类型选择规则，未过度套用复杂模型结构，也未因"简单"而完全不套规范。
- 每个 sheet 已关闭默认网格线（`showGridLines = False`）。
- 年份横向排布，历史/预测后缀清楚，如 A / E / B。
- 假设单独落地，蓝色字体，公式引用假设而非硬编码；计算用公式而非 Python 算好写死。
- 横向公式 `$` 锁定已回读验证。
- 蓝/黑/绿/红/灰色编码正确。
- 单位、币种、来源和口径已标注。
- 数字格式统一，负数括号，零值为 `-`，年份无千分位。
- 年份列等宽紧凑，标签列较宽。
- 普通数据行无装饰边框，无竖线。
- 小计/关键小计/最终合计的边框和加粗层级正确。
- 大标题行有深蓝底色，无灰色背景，无绿/红背景，普通数据行白底。
- **公式零错误（强制跑校验）**：财务模型公式密集、`$` 锁定与跨表引用极易写错，是 `#REF!` / `#DIV/0!` / `#VALUE!` / `#N/A` / `#NAME?` / `#NUM!` / `#NULL!` 的高发区。生成 `.xlsx` 后**必须运行 `python scripts/formula_verify.py <文件路径>` 重算校验，确保 0 错误**后再交付 / 导入飞书；有报错先定位修复（引用错列/错 sheet、`$` 写错、除数为空、查找未命中、函数名拼错），修好重验直到归零。

三表模型额外检查：

- BS 每期 `Total Assets = Total Liabilities + Total Equity`。
- CFS Ending Cash 每期等于 BS Cash。
- Retained Earnings 与 Net Income / Dividends 口径一致。

```python
# ── 三张表勾稽验证（生成后必跑）──
from openpyxl import load_workbook
wb = load_workbook('model.xlsx', data_only=True)        # 读取计算值
bs, cfs = wb['Balance Sheet'], wb['Cash Flow Statement']
for col in year_cols:
    ta  = bs[f'{col}{ta_row}'].value  or 0
    tle = bs[f'{col}{tle_row}'].value or 0
    assert abs(ta - tle) < 0.01, f"BS 不平衡（{col}）: TA={ta}, TL&E={tle}"
    ec = cfs[f'{col}{ec_row}'].value   or 0
    bc = bs [f'{col}{cash_row}'].value or 0
    assert abs(ec - bc) < 0.01, f"Cash 不匹配（{col}）: CFS={ec}, BS={bc}"
print("三张表勾稽验证全部通过")
```

多 sheet 模型额外检查：

- Assumptions 只放输入和说明，不写计算公式。
- Calc 引用 Assumptions，Output 引用 Calc，数据流单向。
- Sensitivity 独立 sheet 或独立区块。

Sensitivity 额外检查：

- 无色阶、无数据条、无斑马纹。
- 仅 baseline 交点高亮。
- 双轴范围围绕 baseline 对称。

## 落地提示（按引擎）

本规范的逻辑与视觉要求与引擎无关；具体写值/公式/样式时按产物载体选实现方式：

- **本地 `.xlsx`（Python 引擎）**：用 openpyxl 实现颜色、数字格式、边框、列宽、网格线、勾稽校验（见上方各 Python 示例）；批量样式可用 `scripts/format_range.py`，公式校验用 `scripts/formula_verify.py`。所有颜色用不带 `#` 的 6 位 hex（如 `'0000FF'`）。
- **飞书在线表格**：写值/公式/样式按 `lark-sheets-write-cells`，多区域用 `lark-sheets-batch-update`，列宽行高用 `lark-sheets-range-operations` / `lark-sheets-sheet-structure`，跨 sheet 公式按 `lark-sheets-formula-translation` 重写并校验；颜色用带 `#` 的 RGB hex（如 `#0000FF`）。
- 若先用 Python 生成 `.xlsx` 再导入飞书：在 `.xlsx` 阶段就把本规范全部落实，导入后只做必要的链接/预览处理。
