> ⚠️ **强制前置条件**：本文档共 221 行，指令说明和约束分散在各部分。必须先读到末行「全文完」，再执行任何其他操作；即使已找到当前任务所需的指令，也不得提前停止。未见该标记时，下一步必须继续调用 Read，在读完之前不得调用 Bash、`--help` 或任何其他工具。读取工具能一次取全文就一次取全，被截断则调整偏移量（`offset`）续读。本技能所有文档末行均有该标记。

# Excel 视觉输出规范

## 0. 先判断是否需要美化

**美化是为了降低阅读成本，不是默认动作。** 按以下顺序执行：理解用户目标 → 判断新建或修改源文件 → 决定是否美化 → 选择最少的视觉手段 → 写入并保存 → 重新加载和视觉检查。

> **最高优先级：用户 Prompt 中明确提出的格式要求。** 当用户指定颜色、字体、字号、边框、列宽、合并方式、图表或其他视觉格式时，如与本规范冲突，必须以用户要求为准；本规范只补充用户未明确指定的部分。

- 以下场景默认只保留必要的数字格式和列宽适配，无需额外添加背景色、斑马纹、冻结、数据条或图表：
  - 用户只要求计算、补充或统计结果。
  - 临时明细、原始数据导出。
  - 用户提供的源文件本身无样式，且没有要求制作正式报表。
- 需要主动进行**最小充分的可视化增强**的场景：
  - 用户明确要求美化、可视化、报表、模板、汇报或打印展示。
  - 产物需要交付他人阅读、填写。
  - 产物属于分组明细、排行、对比、经营分析或统计汇总，格式能明显表达数据关系。
- **斑马纹或交替行底色不属于默认美化手段，不要主动添加。** 适用例外仅限用户明确要求，或源文件已经使用且新增内容需要延续；不能因为行数多、表格长或“看起来更专业”而启用。
- 不要给简单小表同时套用深色表头、冻结窗格、数据条和多套底色。每一种格式都必须有明确含义。

## 1. 保护用户源文件

- 修改已有文件前，先观察字体、颜色、边框、对齐、列宽、数字格式和整体布局；源文件风格优先于通用样式。
- 新增内容遵循相邻区域和同列的样式体系，不要对整个工作簿重新套用主题、列宽、字体或配色。
- 保留公式、数据验证、条件格式、筛选、表格、合并区域、隐藏行列和 Sheet 结构；不要修改任务范围外的内容。
- 插入、删除或移动行列后，检查相关公式和功能范围。无法安全保持时，采用不改变原结构的方案。
- 本规范中的辅助函数默认用于新建表或用户明确要求重排的区域；处理源文件时必须限制作用范围并保留既有样式。

## 2. 基础样式与数据格式

### 标题、表头和数据区

- 先根据主体表格的实际字段确定统一视觉边界 `min_col:max_col`。同一纵向报表中的大标题、分节标题、表头、底色带和分项汇总行必须复用该边界；如在允许场景使用外边框，也必须与该边界左右对齐。不要分别按标题文字长度或局部内容决定范围。
- 标题行可在统一视觉边界内跨列合并，使用主题深色、白字、加粗和居中；普通筛选表头不得合并。
- 视觉边界以最宽的有效主体表格为准，不使用 `ws.max_column` 直接推断，并排除长标题、备注、隐藏列、残留格式和任务范围外的内容。例如主体表格只有 A:B 时，即使长标题文字很多，也只合并和填充 A:B，不延伸到 C:D。
- 表头与数据区保持明确层级，使用低饱和度底色、加粗和居中。
- **数据区默认不使用斑马纹或交替行底色。** 只有用户明确要求，或源文件已经使用且新增内容需要延续时才保留；数据行较多、表格较长或希望提升可读性，都不能单独作为添加斑马纹的理由。
- 普通明细行之间不逐行添加分隔线，普通明细表末行也不添加收尾线。仅在表头底部、分组起始和汇总行使用连续实线，并减少垂直线；除非用户明确要求或源文件已有同类样式，不使用 `hair`、`dotted`、`dashed`、`dashDot` 等点状或虚线边框。只有合计行、允许使用的打印外框或用户明确要求时，表格底部才可出现边框。
- 文本左对齐，数值右对齐，日期和短分类居中，所有内容垂直居中。
- 沿用源文件字体；完全新建文件时默认中文使用`微软雅黑`，英文、数字使用 `Arial`。

### 数据类型与显示

- 百分比必须同时转换**存储值**并设置显示格式：Excel 的 `0%`、`0.0%` 只负责显示，并会把存储值乘以 100；要显示 `50%`，单元格实际值必须是 `0.5`。
  - 来源是 `"50%"` 或语义明确的“百分数 50”时，写入 `0.5`；来源已经是比例值 `0.5` 时直接写入，不要再次除以 100。
  - 严禁写入数值 `50` 后直接设置百分比格式（会显示为 `5000%`），也不要把 `"50%"` 作为文本写入，否则无法可靠参与计算。
  - 纯数值的量纲不明确时，不要猜测它是百分数还是比例值；根据列名、单位、上下文或用户说明确认。
- 日期：写入 `date`/`datetime` 并保持用户需要的日期格式。
- 货币和普通数值：保持数值类型，按需要使用货币符号、千分位和一致的小数位。
- 身份证号、电话号码、邮编、员工编号、订单号等虽然可能只包含数字，但属于标识符而非可计算数值。必须以字符串写入并设置文本格式 @，以保留前导零、完整位数和原始字符 
- 用户要求标准化或转换格式时，以用户指令为准；否则保持原始显示。

```python
from copy import copy
from openpyxl.styles import Alignment, Font, PatternFill, Side

# 新建表头示例；修改源文件时先继承原样式，不要整表套用。
palette = {'header': '17365D', 'second': '5B9BD5', 'line': 'B8C7D9'}
line = Side(style='thin', color=palette['line'])
for cell in ws[header_row][min_col - 1:max_col]:
        cell.fill = PatternFill('solid', fgColor=palette['second'])
        cell.font = Font(name=cell.font.name, bold=True, color='FFFFFF', size=11)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border = copy(cell.border)
        border.bottom = line
        cell.border = border

def write_percentage(cell, value, source_scale='percent', decimals=0):
    if isinstance(value, str) and value.strip().endswith('%'):
        stored_value = float(value.strip()[:-1].replace(',', '')) / 100
    else:
        stored_value = float(value) / 100 if source_scale == 'percent' else float(value)
    cell.value = stored_value
    cell.number_format = '0%' if decimals == 0 else '0.' + '0' * decimals + '%'
```

## 3. 布局与主动可视化

### 列宽、换行和冻结

- 根据实际内容计算列宽；中文和全角字符按 2 个字符估算。
- 横向合并标题不参与单列宽度计算，避免长标题撑宽首列；纵向合并标签仍参与所在列计算。
- 新建表的列宽通常限制在 8~50；超出上限时启用换行，不无限加宽。
- 修改源文件时默认保留已有列宽。不要调整隐藏列或任务范围外的列。
- 冻结窗格默认关闭；长明细需要滚动定位表头或关键标识列时才启用。

### 主动做可视化增强场景

- 同量纲数值需要比较：对销售额、完成率、数量、占比等明细区使用数据条或色阶；排除编号、日期、标题和小计。
- 存在业务阈值：使用条件格式突出未达标、超预算或逾期；阈值必须来自用户规则或数据语义。
- 行数据存在连续分组：使用同一主题的浅色层级、顶部边框、小标题或分项汇总行；不要插入纯空白行分隔。
- “维度—类别—数值/占比”汇总：可纵向合并维度名称，并增加简短的特征说明列。
- 长明细：突出表头、保持筛选区域连续，必要时增加小计行。

### 合并和分组边界

- 操作型明细需要排序、筛选或逐行复制时，不使用纵向合并；保留重复分类值并用边框或底色分组。
- 展示型汇总才使用纵向合并。合并前确认目标区域没有不同值，避免数据丢失。
- 分组底色使用同一主题的 2~3 个浅色层级；不要为每组使用一种高饱和主色。
- 常规的单一连续表格不添加闭合外边框。仅在用户提及打印，或同一 Sheet 存在多个相互独立且容易混淆的内容区域时，才为每个完整区域添加浅灰色细实线外边框；连续表格内的分组不是独立区域，不要逐组套框。
- 修改边框时复制原边框并只替换目标边，避免覆盖其他边框。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

```python
import unicodedata
from copy import copy
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Side
from openpyxl.utils import get_column_letter

def display_width(value):
    return sum(2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
               for ch in str(value or ''))

def fit_one_column(ws, col, min_row, max_row, min_w=8, max_w=50):
    cells = [ws.cell(row, col) for row in range(min_row, max_row + 1)]
    values = [cell.value for cell in cells
              if cell.value is not None and not isinstance(cell, MergedCell)]
    ws.column_dimensions[get_column_letter(col)].width = max(
        min_w, min(max((display_width(v) for v in values), default=0) + 3, max_w))

def set_top_border(cell, color='B8C7D9'):
    border = copy(cell.border)          # 只替换目标边，保留其余三边
    border.top = Side(style='thin', color=color)
    cell.border = border

def merge_group_label(ws, start_row, end_row, col=1):
    values = [ws.cell(row, col).value for row in range(start_row, end_row + 1)
              if ws.cell(row, col).value not in (None, '')]
    if len({str(value) for value in values}) > 1:
        raise ValueError('合并区域包含不同值，停止合并')
    value = values[0] if values else None
    ws.merge_cells(start_row=start_row, start_column=col,
                   end_row=end_row, end_column=col)
    ws.cell(start_row, col, value=value).alignment = Alignment(
        horizontal='center', vertical='center', wrap_text=True)
```

## 4. 配色

- 优先沿用源文件配色；新建文件再从第 2 节色板中选择接近任务语境的一套，色板不是强制映射。
- 深色背景使用白字，浅色背景使用深灰字，次要信息使用中性灰。
- 同一张表通常不超过 3 种主色；分组优先使用同一主题的深浅变化。
- 条件格式、状态色和分组色不要争夺注意力；已有明确状态色时减少其他填充。
- 颜色不能是唯一信息载体，异常和状态同时保留文字、数值或符号。

## 5. 图表

- 只有图表能比表格更快表达关系时才添加；简单明细和小型对照表不主动加图。
- 类别比较优先条形图/柱形图，时间趋势使用折线图，构成占比仅在类别不超过 5 个且互斥时使用饼图/环形图。
- 不给每个点都加数据标签；只标注关键点、末值、异常或用户要求的值。
- 标题、坐标轴标签与多系列图例是必备项，不因「图意已明显」省略；单位等补充信息避免与轴标签重复表达。
- **图表默认放在新建的独立工作表中**，命名为“图表”或与主题对应的“XX分析”；源数据保留在原工作表，图表跨 Sheet 引用数据。存在两张及以上图表时必须使用独立工作表，并按网格排列，禁止重叠或遮挡。
- 只有用户明确要求图表与数据同屏，或仅有一张小型图表且已确认存在足够的连续空白区域时，才允许嵌入数据工作表；嵌入后必须通过视觉检查确认不覆盖标题、数据、表头、备注或其他对象。

## 6. Sheet 组织

- 一个 Sheet 应有清晰的阅读主题，但不要机械拆分相关的小型内容。
- 原始明细与正式汇总、不同对象/周期且阅读路径明显不同、单表过长难以浏览时，拆分到独立 Sheet。
- 相关的简短摘要、说明和同主题明细可以放在同一 Sheet，通过标题、间距和分区表达层级。
- 不要把大量逻辑无关的表堆叠在同一 Sheet，也不要为了“整洁”创建大量只有几行内容的 Sheet。

## 7. 打印场景的可见版式

用户提及“打印 / A4 / 纸质版 / 可打印”时，只优化打开 Excel 即可看到的视觉层，无需修改打印配置。

- 先确定视觉版式方向：用户明确指定纵向或横向时严格遵循；只提及 A4/打印而未指定时默认纵向。仅当宽表在纵向下会出现截字、过度换行或字号低于 10pt 时，才采用横向视觉密度，并在交付说明中注明。
- 以一页 A4 的信息密度为目标：纵向列宽总和约 95，横向约 140；内容过多时重组为摘要，不压成不可读的小字。这里的方向只控制可见版式密度，不写入纸张方向或其他打印配置。
- 默认不使用斑马纹和大面积装饰底色，只保留表头、分组、小计和异常等语义强调。
- 为完整内容区增加浅灰色细实线闭合外边框；保证字号不小于 10pt。
- 标题、正文、备注和合计必须完整可见，不得截字、溢出、显示 `####` 或被图表/图片遮挡。
- 修改源文件时只清除已确认属于斑马纹的行，不要清除状态色、分组色或其他语义填充。

```python
from copy import copy
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

def prepare_print_visual_layout(ws, min_row, max_row, min_col, max_col,
                                confirmed_zebra_cells=()):
    """只调整可见版式；不要写入打印配置或清除语义填色。"""
    ws.sheet_view.showGridLines = False
    for cell in confirmed_zebra_cells:  # 仅清除已确认的斑马纹单元格
        cell.fill = PatternFill(fill_type=None)

    for row in ws.iter_rows(min_row=min_row, max_row=max_row,
                            min_col=min_col, max_col=max_col):
        for cell in row:
            font = copy(cell.font)
            font.size = max(font.size or 10, 10)
            cell.font = font
            if isinstance(cell.value, str) and not cell.value.startswith('='):
                alignment = copy(cell.alignment)
                alignment.wrap_text = True
                cell.alignment = alignment

    for col in range(min_col, max_col + 1):
        letter = get_column_letter(col)
        width = ws.column_dimensions[letter].width or 10
        ws.column_dimensions[letter].width = max(6, min(width, 24))
```

## 8. 最终检查

保存前必须检查：

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

- 无截字、文本溢出、`####`、异常超宽列、不合理行高或对象遮挡。
- 图表默认位于独立工作表；两张及以上图表不得留在数据工作表。允许嵌入的单张图表已确认不覆盖标题、数据、表头、备注或其他对象，多个图表之间不重叠。
- 同一纵向报表的大标题、分节标题、表头、底色带和汇总行左右端点一致；如有外边框，其范围必须对齐，且只用于打印区域或区隔同一 Sheet 中的多个独立区域，不得给常规表格或连续分组逐个套框。
- 合并单元格未丢失数据，且没有破坏必要的筛选、排序和复制。
- 条件格式只覆盖可比较的明细数据，不包含标题、小计和文本编号。
- 百分比显示值与存储值一致：例如显示 `50%` 时实际值为 `0.5`，且仍可参与公式计算。
- 公式、数据验证、条件格式、筛选、表格和引用范围仍然有效。
- 新增内容与源文件字体、颜色、边框、列宽和数字格式协调。
- 保存后重新加载工作簿，确认关键值、公式和样式仍存在；对正式交付物再进行一次逐 Sheet 的可视化检查。

===== 全文完（共 221 行）=====
