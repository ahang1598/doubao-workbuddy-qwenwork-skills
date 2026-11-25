# 金融/财务建模与财务数据整理规范

## 定位与优先级

本文是**财务/金融场景的操作与视觉规范**，与执行引擎无关——无论产物是 Python（openpyxl）生成的本地 `.xlsx`，还是飞书表格，只要表格里承载的是财务性质的数据，就必须遵守本文。

本地建立固定利率、等间隔期末偿付的逐期还款表时，优先用随包 `scripts.loan_schedule.write_schedule` 一次写本金、利息、还款额及期末余额，再从函数返回的明细区间生成合计；已有模板以 `column_map` 匹配列序，不覆盖日期列。仅当利率、周期或合同计息方式不适用该函数时自行构建；具体可运行用法见下文「假设值与公式」。

### 动手前先分叉：新建模型 vs 美化已有表

本文的规则怎么用，取决于输入是"从零建"还是"已成型"——先判断再动手：

- **从零构建，或把零散数据整理成一张新表**（用户未提供成型模型表，或明确要你新建）→ 本文全套适用：报表结构、公式写法、年份布局、多 sheet 拆分、Sensitivity 布局都由你按规范搭建。
- **输入已是一张成型的模型表**（给了飞书表格或附件文件，要求"美化 / 规范化 / 保留计算逻辑 / 更新到原表"）→ 这是**美化已有表，不是重建**：只在原表上就地调整样式属性（字体 / 填充 / 边框 / 对齐 / 数字格式），本文关于报表结构、公式、Sensitivity 与布局、多 sheet 拆分的规则**只用于你新增的内容，不得用来改动原表的既有结构、公式和布局**。此分支下必须守住两条：
  - **原表已有公式一律原样保留**（各类 IRR / 汇总 / 引用公式等），禁止用你认为更规范的写法替换。"公式优先"针对的是"新算的派生值别写成死值"，**不是**"重写原表已有的公式"；保留原计算逻辑优先于任何格式规范。
  - **禁止"重建"反模式**：从零重建整张表再整体覆盖原表；清空原表区域再灌入重建版；新建一张"美化版"子表承载重排后的布局。这些都会丢掉原表的合并单元格、图表数据源列、原公式与原布局。具体的就地样式化实现，按下方「落地提示（按引擎）」选择对应方式。

适用范围（看到这些信号一律适用，不要因为"任务看起来只是整理数据"就跳过）：

- **估值与建模**：DCF / LBO / Comps / Precedent、资本结构、Unit Economics、Market Sizing。
- **财务报表**：三张财务报表（IS / BS / CFS）、财务预测、预算与 Variance Analysis、Sensitivity / Scenario Analysis。
- **财务数据整理 / 标准化 / 汇总**：把某公司的营收、成本、利润、现金流、估值等数据整理成一张表（哪怕用户只说"整理成 Excel""做个表"），也属于本规范——它是"财务报表整理"，不是普通数据表。
- **以财务数据为输入的推算 / 经营分析**：例如从财务成本反推算力、产能、获客成本、单位经济等。需要表格产物时，即使核心难点是业务推算、Python 只是用来算数，**最终承载财务数字的那张表仍必须按本规范呈现**。
- 投研 / 投行 / PE / Equity Research / FP&A / 咨询场景的任何表格产出。

优先级从高到低：

1. 用户明确指令或既有模板样式。
2. 本金融/财务建模规范。
3. 通用核心操作、视觉规范与公式规则。

如果本文与通用视觉规范冲突，以本文为准。典型冲突：

| 通用规范 | 财务模型规范 |
| --- | --- |
| 可用数据条、色阶强化可视化 | Sensitivity 禁止色阶、数据条和图标集 |
| 列宽按内容自适应 | 年份列必须紧凑等宽；标签列才加宽 |
| 通用规范已减少竖线，仅在必要结构中使用边框 | 财务模型进一步禁止年份列竖线；Sensitivity 矩阵浅灰细框是唯一例外 |

## 按任务裁剪

不要把全套 DCF 规范套到简单费用表；但也**不要因为任务"简单"就一条规范都不用**。先判断任务类型，再选择规则。

| 任务类型 | 必用规则 | 不要做 |
| --- | --- | --- |
| **财务数据整理 / 汇总 / 标准化**（含"把某公司财务数据整理成 Excel"） | 科目分类、颜色编码、数字格式、单位与来源、年份横向布局、小计/合计边框 | 不需要 Sensitivity；不强行拆多 sheet |
| 三表整理 / 标准化 | 上一行全部 + 三表结构 | 不需要 Sensitivity |
| DCF / LBO / 估值模型 | 假设/计算/输出分层，多 sheet 拆分，横向年份，假设单独落地，公式引用假设，Sensitivity 按需独立 | 不要把假设硬编码进公式 |
| Comps / Precedent | 科目口径、颜色编码、数字格式、单位、分区和小计样式 | 通常不需要三表勾稽，不强制拆多 sheet |
| 预算 / Variance Analysis | 颜色编码、数字格式、横向期间、差异列公式、汇总边框 | 不需要 Terminal Value / WACC |
| 以财务为输入的推算（算力/产能/单位经济反推等） | 承载财务数字的表按"财务数据整理"规则；推算的关键中间量与结果也用表格呈现并标注来源/口径 | 不要只把结果硬写成一团数字、缺颜色编码与单位 |
| 单项 Sensitivity / Scenario | 假设分离、Sensitivity 专用视觉规范、baseline 标注 | 不使用色阶/数据条 |

## 财务逻辑规范

### 按结构、时点与口径构建模型

模型的组成项、计提时点和指标口径按任务及来源定义构建。真实观测值未达业务标准不等于录入错误，除非用户要求调整，不把实际数改成达标值；应计值、缺口及建议在结果区另列：

- **结构关系按组成项计算**：来源与用途、资产与负债权益、期初到期末滚动按原始输入和对应公式构建，权益或融资按模型定义作为 plug，所有组成项及其正负号分别引用对应来源。
- **资金桥接区分余额与追加资金**：交易保留现金、目标期初现金和需补足的差额分别列示，模型约定补足最低现金时，以 `MAX(0,目标现金-保留现金)` 落格并计入约定来源 / 用途，权益plug引用包含该项的合计；债务表使用同一口径的期初现金，避免漏补或把目标余额重复计为新增资金。费用按合同发生时点区分交割支出与持有期支出，不将所有费率都套进交割用途。
- **先画时间轴，再写第一期**：交割日 / 起始日、首个完整期间、退出或结束日各自落格。起点余额与期间流量分列，计息、偿还和分配各有生效时点；交割落在期末且未约定当期计提时，本次融资的计息和偿还从下一期起算，交割余额作为首期起点；逐期滚动引用上期期末，交割当期其他经营流量仍按来源保留，不对全列统一清零。债券 / 贷款现金流按合同或附件的实际付息日期及计息基准展开；付息频率不代表估值日恰为付息日，未约定简化模型时，不用剩余年限乘频率取整代替现金流日历。
- **资格与豁免判定先于费率档**：涉及费率资格、减免、优惠、起征点或分档累进时，将来源中的适用条件与阈值绑定到实际输入格，按优先级计算不适用 / 豁免 / 正常计提，再由最终金额公式引用判定及费率；不把结论只放备注，也不用手工选档代替资格逻辑。费用重分类或金额调整后，资格分子 / 分母、扣除限额与应税金额须引用调整后的对应明细，不能继续使用调整前缓存。先套费率再补判定，多算的金额会一路传导到最终结果。
- **同名指标的多个口径分列**：含税与不含税、全口径与剔除某类、期间累计与全年预计，各自单独取数并标注用途，不复用同一个总额当所有分母。填写指定指标时按其期间与实绩 / 预计状态选数，取数时把数值、单位、期间、实绩 / 预计状态与来源页绑定，口径写在表内，不以期间累计替代全年预计；需并列解释其他口径时放在允许的说明区域，不挤占指定结果位置。
- **跨期模拟按状态切换计算**：价格口径、现金流符号及生效时点保持可追溯；资产、持仓或计量规则切换时，分别按切换前、当期与下一期的口径计算，不能把不同口径的直接相减当作期间变动。
- **回撤计算保持峰值分母**：最大回撤默认取各时点 `(截至当期峰值−当前值)/截至当期峰值` 的最大值，正数表示跌幅；分母是峰值，不是当前值。用户或原模板已有符号约定时沿用，不因此改换分母。

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

Cash Flow Statement 必须有 CFO、CFI、CFF、Net Change in Cash、Beginning Cash、Ending Cash；三表关联关系为 Ending Cash = BS Cash。

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

专业模型按 Input -> Calc -> Output 分层，在用户允许的子表与区域内组织；多个报表复用的同口径期间汇总先在计算区落格，展示、比率和排名引用这些结果，不把同一大段取数表达式反复展开进每个公式。不同筛选维度各自取数，不混用当前选择与全体数据。用户限定新增子表数量或名称时，用该表内清晰分区承载辅助计算，不擅自增加 Calc / Check 等子表。未限定时可按以下结构拆分：

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

**同一输入贯穿明细与方案汇总**：可调本金、日期、规模等公共输入只设一个来源；明细和各方案行都以公式引用该输入，不能复制当前默认值充当方案假设。各方案特有的期限、费率等仍按该方案取值，不引用当前选中方案代替全部方案。

**明细、合计与展示使用同一舍入口径**：只要求显示小数位时保留计算精度，用数字格式控制显示；用户明确四舍五入金额时，实际用 ROUND 舍入指定金额，不以数字格式代替。逐期舍入时，汇总引用实际逐期金额，尾期处理本金余差，并保持每期付款=本金+利息、期末余额与累计本金一致。不能明细先ROUND、汇总另用未舍入闭式公式，再把不一致当成“舍入误差可忽略”；也不为消除差异删除用户要求的逐期舍入。场景对比需沿用同一口径；题意不明确时说明采用的口径，不为凑预期值切换算法。

例如逐期金额由两项组成时，先分别落格 `C2=ROUND(组成项1,2)`、`D2=ROUND(组成项2,2)`，本期合计用 `=C2+D2`，跨期合计用 `=SUM(E2:E13)`；不要独立舍入三项。需要尾期结清的余额，本金取尾期期初余额，尾期付款再加本期利息。各方案在允许的计算区分别展开自己的逐期金额，汇总引用各自明细，不把当前选中方案明细复制给所有方案。

本地固定利率、等间隔期末还款建模可直接用随包 `scripts.loan_schedule.write_schedule` 写公式，免手写逐期舍入和尾差。每方案分别传自己的利率与期数格、相同本金格；函数不打开或保存文件、不写表头与日期。默认连续六列依次为期数、期初本金、本金、利息、付款、期末本金；已有模板列序不同（如另有日期列）时，传完整 `column_map` 映射实际列号，只写指定六列，其余不动。写入区须已授权且能容纳 `capacity` 期；各方案汇总分别引用其自身的返回列位，不用闭式公式另算合计。

```python
from scripts.loan_schedule import write_schedule

schedule = write_schedule(calc_ws, principal="'输入'!$B$2", rate="'输入'!$B$3",
                          periods="'输入'!$B$4", method="annuity", capacity=60,
                          start_row=2, digits=2,
                          column_map={'period': 1, 'opening': 3, 'payment': 4,
                                      'principal': 5, 'interest': 6, 'closing': 7})
summary_ws['B2'] = schedule['input_formula']
summary_ws['C2'] = schedule['totals']['payment']
summary_ws['D2'] = schedule['totals']['interest']
```

`rate` 是每期利率格，`periods` 是总期数格，`capacity` 按支持的最大期数预留，不按当前值截断。`method` 为 `annuity`（PPMT/IPMT组成）、`equal_principal` 或 `interest_only`；`digits=None` 仅在无需逐期舍入时使用。非法输入或超容量返回 `#N/A`，不交付截断的还款表。非等间隔、日计息、浮动利率或合同指定不同尾差口径时沿用匹配合同的实现；模块不存在时按上述组成项、余额及明细汇总关系写公式。

用户明确要求固定结果时写值；其余情况下，仅以下三类单元格可直接写静态值：

1. 历史真实数据。
2. 蓝色输入假设。
3. 外部来源的静态取数，且必须标注来源。

> **公式优先是财务建模的基础纪律：用 Python 算好数值再写进单元格，交付的是改输入不重算的死表。**
> 用户未要求固定结果时，由其他单元格推导出来的数（增长率、占比、同比、各种推算的中间量和结果、GPU 数量/算力换算等）**必须写成引用其他单元格的 Excel 公式**，而不是在 Python 里算出数值再写进单元格。
>
> **不要用下面这些理由给硬编码开脱：**
> - "我先用 Python 算准了再写入，结果是对的。" —— 硬编码的表没有动态计算能力；需要保留联动时，Python 可用于推导，最终落格仍应是公式。
> - "这是推算任务，逻辑在 Python 里更好写。" —— 推算逻辑可以在 Python 里推导，但把它**翻译成单元格公式**写进表里；关键输入做成蓝色假设格，让用户能改、能联动重算。
>
> 默认静态值范围为本节列的三类：历史真实数据、蓝色输入假设、标注来源的外部静态取数。用户明确要求固定结果时写值；其余派生结果写公式。

```python
# ❌ 错误：假设值硬编码进公式 / 在 Python 里算好写死
ws['E7'] = '=D7*1.05'                  # 5% 增长率藏在公式里
ws['E7'] = 644                          # 直接写死 Python 算出来的结果 → 改输入不重算
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

新写公式尚无缓存时，`data_only=True` 读到的是 `None`；需取计算值时，使用可用引擎完成重算后的副本，本地缺少引擎时按 `references/ref-local-compat.md` 处理。

### 说明注释

复杂估值/预测模型（如 DCF、LBO）或计算口径无法从表内直接看清时，在表尾增加紧凑的说明区；简单财务数据整理不强制添加。按需从以下四项中选择：

- `Methodology`，关键计算口径及时间口径
- `Key assumptions`，作为重要预测驱动及变化方式的关键假设说明
- `Sources`，**重要**，历史值、外部数据、硬编码来源，包括用户提供的数据，必须在注释中标注：`Source: [来源], [日期], [页/表/字段]`。FY、CY、LTM、NTM、CAGR、YoY、QoQ 等缩写必须使用一致口径。**做财务推算时尤其重要**：每个外部取数与关键假设都要可追溯到来源
- `Color convention`，颜色含义，注意解释颜色时依然要遵循注释内容的字体颜色风格，不许使用对应的颜色

说明注释区不设总标题，不用"Notes"开头，直接开始写注释正文，通过字体颜色风格与表格正式内容区分

使用`Methodology:`等选项名称作为对应内容的开头，每段内容是一段连续文本。

用户明确要求各指标定义、公式或特定章节结论时逐项写齐；其余只写理解和复核模型所需的信息，不复述普通公式；注意，说明区是额外的说明解释，不能替代可编辑引用的 Assumptions 区域数据。

## 视觉规范

### 字体颜色编码

财务模型用字体颜色表达单元格性质。

openpyxl 的颜色参数用不带 `#` 的 6 位 hex（如 `Font(color='0000FF')`）。

| 颜色 | openpyxl hex | 含义 |
| --- | --- | --- |
| 蓝色字体 | `0000FF` | **直接键入数值的输入格（即假设/驱动项，用户可手动修改）**，如增长率、WACC、税率、单卡成本——这类格子本就该写值不写公式（属默认静态值范围中的第 2 类） |
| 黑色字体 | `000000` | 本 sheet 公式或普通文本 |
| 绿色字体 | `008000` | 同工作簿跨 sheet 引用；公式中只要出现跨 sheet 引用就用绿色 |
| 红色字体 | `FF0000` | 外部文件/外部系统链接，慎用 |
| 灰色斜体 | `808080` + italic | 说明注释内容，YoY、Margin、Notes、单位说明、数据来源（仅字体，灰色不做背景） |
| 浅黄背景 | `FFF2CC` | 待确认 / 待复核的假设（临时标记，交付前应清除或确认）|

```python
from openpyxl.styles import Font, PatternFill
FONT, SIZE = 'Calibri', 10

blue_font  = Font(name=FONT, size=SIZE, color='0000FF')                   # 直接输入的假设/驱动项
black_font = Font(name=FONT, size=SIZE)                                    # 本表公式
black_bold = Font(name=FONT, size=SIZE, bold=True)                         # 小计/合计
green_font = Font(name=FONT, size=SIZE, color='008000')                   # 跨表引用
red_font   = Font(name=FONT, size=SIZE, color='FF0000')                   # 外部文件引用
aux_font   = Font(name=FONT, size=SIZE, color='808080', italic=True)       # 说明注释、辅助行：同字号，灰色+斜体
highlight_fill = PatternFill('solid', fgColor='FFF2CC')                    # 待确认（浅黄，临时标记）
```

说明注释、辅助行字号与正文一致，只靠灰色和斜体区分层级。除 sheet 顶部大标题外，全表正文、分区标题、副标题、说明注释、辅助行使用统一字号。

> ⚠️ 上表是**字体**颜色编码；**背景填充**另有一套统一配色，见下「背景色与配色」。两者不要混淆：绿 / 红只用于字体（跨表 / 外链），**绝不用于背景**。

### 背景色与配色（统一商务蓝）

除非用户有特殊要求，财务模型的背景填充默认使用**商务蓝配色**；除下表列出的用途外，所有格子一律白底（无填充）。

| 用途 | openpyxl hex | 说明 |
| --- | --- | --- |
| 主表头 / 大标题行 / 一级分区标题 | `006185` | 深蓝底 + 白色加粗字 |
| 二级表头 / 分组标题 | `049FD7` | 中蓝底 + 白色加粗字 |
| 信息区 / 汇总行 / 三级标题（浅底） | `D9F3FD` | 浅蓝底 + 黑字 |
| 分隔线 | `D0D8E8` | 需细分隔线时用此色（结构仍以边框为主，见「边框」） |
| 浅黄高亮 | `FFF2CC` | Sensitivity baseline 交点 / 需浅色标注的复核项——唯一允许的非蓝高亮 |

硬性规则：

- **大标题行必须有背景色**：sheet 顶部的报表总标题行用 `006185` 深蓝底 + 白色加粗，不能留白底。（常见错误：大标题没填背景，整张表"没有头"。）
- **禁止用绿色 / 红色做背景色**：区分情景 / 版本（Bull / Base / Bear、乐观 / 中性 / 悲观）也**不要**用绿底 / 红底——太扎眼、不专业。统一用商务蓝，靠**文字标签**（如 "Bull Case" / "Bear Case"）区分；如确需层次区分，在 `006185` / `049FD7` / `D9F3FD` 三档里选深浅。绿 / 红仅作字体颜色编码（跨表 / 外链），不用于背景。
- **普通数据行白底**：收入 / 费用 / 各类明细行不加任何填充。
- 同层级分区标题用相同背景色 + 相同左右填充列范围；不同层级靠这三档蓝色深浅区分，不靠填充长短区分。

```python
from openpyxl.styles import Alignment
HEADER_BG = '006185'   # 主表头 / 大标题 / 一级分区
SECOND_BG = '049FD7'   # 二级表头 / 分组标题
LIGHT_BG  = 'D9F3FD'   # 信息区 / 汇总行 / 三级标题（浅底）
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

### 数字格式与单位

| 数据类型 | 推荐格式 |
| --- | --- |
| 年份 | `0`，不得显示千分位 |
| 整数 | `#,##0;(#,##0);"-"` |
| 小数 | `#,##0.0;(#,##0.0);"-"` 或 `#,##0.00;(#,##0.00);"-"` |
| 货币 | `$#,##0;($#,##0);"-"` 或 `$#,##0.00;($#,##0.00);"-"` |
| 百分比 | `0.0%` 或 `0.00%`，同一表内保持一致 |
| 估值倍数 | `0.0" x"` |
| 人数/股数 | `#,##0` |

零值显示为 `-`，负数使用括号法 `(123)`。如采用窄货币符号列，符号列单独放 `$` / `¥`，数值列不再带货币符号。用户点名"保留 N 位小数"时，用固定 N 位的 `number_format`（如 `0.00`）落格、尾随零必须显示——不要让货币 / 千分位 / 默认显示盖掉要求的位数，也不要把数值与文本标记混进同一格。

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

**单位必须清晰标注**：

- 全表单位统一时，在标题下方用灰色斜体副标题标注，如 `($ in Millions, Except Per Share Data)`。
- 同一表存在多种单位时，在字段名后直接标注，如 `Revenue ($mm)`、`Gross Margin (%)`、`员工人数（万人）`、`ARPU, 元/月`。

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
- 不同层级也保持左右边界一致，只用背景色深浅区分层级（一级 `006185` 深蓝底白字加粗；二级 `049FD7` 中蓝；三级 `D9F3FD` 浅蓝黑字）。配色与 `section_header()` 见上方「背景色与配色」。
- **大标题行必须填 `006185` 深蓝底 + 白色加粗，不能留白底。**

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
5. 每个情景格都要按该组输入**全链路重算**，不要只在 baseline 结果上做线性扰动、也不要冻结 baseline 中间表后只改展示值。

```python
HEADER_BG, BASELINE_BG = 'D9F3FD', 'FFF2CC'    # 轴表头用浅蓝 light_bg；baseline 浅黄
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

## 模型联动关系

三表按各期资产 = 负债 + 权益、CFS Ending Cash = BS Cash 关联；Retained Earnings 按 Net Income / Dividends 的口径滚动。多 sheet 模型保持 Assumptions → Calc → Output 的单向数据流。Sensitivity 的情景格引用对应输入组合下的完整计算，baseline 交点与主输出使用同一组输入和计算口径。

## 落地提示（按引擎）

本规范的逻辑与视觉要求与引擎无关；具体写值/公式/样式时按产物载体选实现方式：

- **本地 `.xlsx`（Python 引擎）**：用 openpyxl 实现颜色、数字格式、边框、列宽、网格线（见上方各 Python 示例）；批量样式可用 `python3 scripts/excel_format_range.py`。所有颜色用不带 `#` 的 6 位 hex（如 `'0000FF'`）。
- **飞书表格**：写值/公式按 `references/lark-sheets-write-cells.md`；样式、合并、列宽行高、冻结的任意组合**一次** `references/lark-sheets-styles-put.md` 交付，不要拆成写值后多轮刷样式；同一个写操作打多个区域用该命令自身的复数形态（`--ranges` / map 入参），只有跨类型、有顺序依赖的操作链才用 `references/lark-sheets-batch-update.md`；跨 sheet 公式按 `references/lark-sheets-formula-translation.md` 重写；颜色用带 `#` 的 RGB hex（如 `#0000FF`）。
- 若先用 Python 生成 `.xlsx` 再导入飞书：在 `.xlsx` 阶段就把本规范全部落实；导入后按 `references/lark-sheets-workbook.md` 读取 `data.extra` 并处理不支持元素，成功后按交付规则交付。用户明确要求预览时，再按其范围提供预览。

===== 全文完（共 497 行）=====
