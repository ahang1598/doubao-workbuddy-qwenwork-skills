> ⚠️ **强制前置条件**：本文档共 603 行，指令与约束分散在各处。必须读到末行「全文完」再执行任何其它操作——即使已找到当前所需的指令也不得提前停止；未见该标记前不得调用 Bash、`--help` 或任何其它工具，被截断就调整 `offset` 续读。本技能所有文档末行均有该标记。

# Excel 文件技术工作流（xlsx workflow）

本文件覆盖 Excel 文件的创建、编辑、公式重算与验证的完整技术流程。

## 工具选择

| 工具 | 适用场景 |
|------|---------|
| **pandas** | 数据分析、批量读写、简单数据导出 |
| **openpyxl** | 复杂格式、公式写入、Excel 特性（合并单元格、颜色、样式） |

两者可组合：pandas 处理数据逻辑，openpyxl 负责格式与公式。

**openpyxl 保存会丢 x14 扩展**：源文件用「其他工作表的区域」做下拉数据源时，规则存在 `x14:dataValidation` 扩展节点里，openpyxl 读得进、存不回——`load_workbook` 后 `save` 一次就归零，而同一份文件走 `+workbook-import` / `+workbook-export` 反而保留。含这类下拉的文件不要用 openpyxl 落盘。

**openpyxl 读不出东亚内置日期格式**：`numFmtId` 27–58（`m"月"d"日"` 这类中文区内置格式）在 openpyxl 里全部回落成 `General`，日期格因此被读成 4 万上下的整数。这类列参与判断前先按 Excel 纪元换算回日期，别当成普通数值处理，也别据此断定它被谁改过。

**源文件是旧版 `.xls` 时先转格式**：openpyxl 只认 OOXML，直接 `load_workbook` 会抛 `InvalidFileException`，xlrd 新版也已不支持 xlsx 之外的读法，两条都不是重试能绕过的。用 `lark-cli sheets +workbook-import --file ./src.xls` 导入后按飞书表格引擎做；确实需要本地 `.xlsx` 时，再对导入得到的 URL 跑 `+workbook-export --url "<新表 URL>" --output-path ./src.xlsx`，之后走本文流程。


## 读取 Excel

```python
import pandas as pd

df = pd.read_excel('file.xlsx')                        # 第一个 sheet
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)  # 全部 sheet → dict

# 指定类型，避免推断错误
df = pd.read_excel('file.xlsx', dtype={'id': str}, parse_dates=['date_col'])
```

### 处理合并单元格

合并单元格的值只存在左上角第一格，其余格读取为 `NaN`，读取后需向下/向右填充：

```python
from openpyxl import load_workbook

wb = load_workbook('file.xlsx')
ws = wb.active

# 查看合并区域
print(list(ws.merged_cells.ranges))

# 拆开合并单元格并填充值（适合提取类任务）
ws.unmerge_cells('A1:A3')
# 或使用 pandas ffill 填充 NaN
df = pd.read_excel('file.xlsx')
df.ffill(inplace=True)
```

当需要在合并单元格上写入公式，或需要把带公式的区域合并时，按以下规则处理，避免 `#REF!`、公式丢失或显示为空：

1. 合并区域在 Excel 语义上只保留左上角单元格（anchor）。合并后只有 anchor 单元格允许存放值/公式，其余单元格必须为空。
2. 对合并区域写公式：把公式写到 anchor 单元格，再执行 `merge_cells` 合并区域。
3. 对“带公式的区域”做合并：先把希望保留的公式移动/写到 anchor 单元格，把区域内其他单元格的 `value` 清空，再执行合并。
4. 引用合并区域做计算：引用时使用 anchor 坐标；如果你拿到的坐标在合并范围内，先解析到 anchor 再生成公式引用。

```python
from openpyxl.utils.cell import range_boundaries

def merged_anchor_cell(ws, row, col):
    for merged_range in ws.merged_cells.ranges:
        if merged_range.min_row <= row <= merged_range.max_row and merged_range.min_col <= col <= merged_range.max_col:
            return (merged_range.min_row, merged_range.min_col)
    return (row, col)

def write_formula_to_merged(ws, cell_range, formula):
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    ws.cell(row=min_row, column=min_col).value = formula
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            if r == min_row and c == min_col:
                continue
            ws.cell(row=r, column=c).value = None
    ws.merge_cells(cell_range)
```

## 创建 Excel 文件

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active

ws['A1'] = '标题'
ws['B2'] = '=SUM(B3:B10)'   # 写公式，不写硬编码计算值

# 视觉样式与列宽按 ref-excel-visual-standards.md 处理；技术示例不另设默认配色。

wb.save('output.xlsx')
```

### 标准 Excel Table（ListObject）

把数据范围注册为原生 Excel Table，自带筛选/排序，且后续公式可用结构化引用（`=表名[列名]`）。条带样式默认关闭；仅在用户明确要求或源表已有同类样式时开启：

```python
from openpyxl.worksheet.table import Table, TableStyleInfo

tbl = Table(displayName="销售明细", ref="A1:F100")  # 必须包含表头行
tbl.tableStyleInfo = TableStyleInfo(
    name="TableStyleLight9",    # 轻量样式；具体视觉取值见 ref-excel-visual-standards.md
    showRowStripes=False,
    showColumnStripes=False,
)
ws.add_table(tbl)
```

注意：`displayName` 在工作簿内必须唯一；`ref` 必须是矩形区域且第一行为表头。

## 单元格排版（行高 / 列宽 / 换行）

本技术工作流不另设视觉默认值。只要新建或重新排版 `.xlsx` 区域，先读取 `references/ref-excel-visual-standards.md`，使用其中的 `fit_one_column()` 和 `display_width()` 等相关规则统一处理显示宽度、列宽上限、换行与行高。

- 新建 sheet 或新建表格区域：按实际内容计算列宽；中文和全角字符按 2 个字符估算；超出上限时换行，不修改单元格原始文本。
- 修改已有模板：除非用户明确要求整理格式，否则保留原有行高、列宽、隐藏状态和对齐方式，只调整新增或确实显示不全的目标区域。
- 禁止为了版面整齐而截断、改写或追加省略号到原始单元格值；视觉问题通过列宽、换行和必要的行高调整解决。

## 编辑已有 Excel 文件

**在源工作簿上改**：`load_workbook` 打开源文件，结果写进新 sheet 或新区域后保存（本地就地编辑时，动手前先复制一份备份留作回滚）。用 `Workbook()` 新建空工作簿再把结果写进去，源表就整张消失了——分析、统计、建模类任务同样适用，产物要既有结果也有原始数据。交付前用 `--baseline` 让工具替你比（见下方交付门禁）。

```python
from openpyxl import load_workbook

wb = load_workbook('existing.xlsx')
ws = wb.active  # 或 wb['SheetName']

ws['A1'] = '新值'
ws.insert_rows(2)
ws.delete_cols(3)

new_ws = wb.create_sheet('新Sheet')
new_ws['A1'] = '数据'

wb.save('modified.xlsx')
```

> **注意**：用 `data_only=True` 打开再保存会永久丢失公式，只保留数值。

## 范围复制（含样式）

直接 `tcell.value = scell.value` 只搬数据，不带格式。要保留字体/底色/边框/数值格式，必须复制 `_style`：

```python
from copy import copy

def copy_range(ws_src, src_range, ws_dst, anchor_cell):
    """src_range 形如 'A1:C5'；anchor_cell 形如 'E10'，作为目标左上角。"""
    from openpyxl.utils.cell import range_boundaries, coordinate_from_string, column_index_from_string
    sc, sr, ec, er = range_boundaries(src_range)
    col_letter, row = coordinate_from_string(anchor_cell)
    target_row = row
    target_col = column_index_from_string(col_letter)
    row_offset = target_row - sr
    col_offset = target_col - sc
    for r in range(sr, er + 1):
        for c in range(sc, ec + 1):
            sc_cell = ws_src.cell(row=r, column=c)
            tc_cell = ws_dst.cell(row=r + row_offset, column=c + col_offset)
            tc_cell.value = sc_cell.value
            if sc_cell.has_style:
                tc_cell._style = copy(sc_cell._style)
```

跨工作簿复制时，`_style` 引用的是源 wb 的 styles 表，目标 wb 保存前会自动落表，可以直接使用。

## 公式写入前自检（事前校验）

`excel_formula_verify.py` 是**事后重算**——在交付前确认无 `#REF!`/`#NAME?`。但事前也要做一次廉价的语法校验，能拦住大部分手写笔误，避免重算阶段才暴露错误：

```python
import re

UNSAFE_FUNCS = {"INDIRECT", "HYPERLINK", "WEBSERVICE", "DGET", "RTD"}

def validate_formula(formula: str) -> tuple[bool, str]:
    """返回 (是否合法, 原因)。"""
    if not formula.startswith("="):
        return False, "公式必须以 '=' 开头"
    body = formula[1:]
    parens = 0
    for ch in body:
        if ch == "(":
            parens += 1
        elif ch == ")":
            parens -= 1
            if parens < 0:
                return False, "右括号多于左括号"
    if parens > 0:
        return False, "左括号未闭合"
    for func in re.findall(r"([A-Z]+)\(", body):
        if func in UNSAFE_FUNCS:
            return False, f"禁用函数: {func}"
    return True, "ok"

def safe_set_formula(ws, cell, formula):
    """统一入口：自动补 '='、做语法校验后再写入。"""
    if not formula.startswith("="):
        formula = "=" + formula
    ok, msg = validate_formula(formula)
    if not ok:
        raise ValueError(f"{cell} 公式非法: {msg}")
    ws[cell] = formula
```

写公式时另有两条与引擎无关的硬约束，写错了在 Excel 里直接是错误值：

- **Excel 2010 起的新函数在 xlsx 文件里必须带 `_xlfn.` 前缀**（`FILTER` / `SORT` / `SORTBY` / `UNIQUE` 再多一层，写成 `_xlfn._xlws.FILTER`）。写文件的库不替你补前缀，`=STDEV.S(A2:A9)` 这样存进去，Excel 与重算引擎打开都是 `#NAME?`，而文件里没有缓存值、事后扫不出来。要么写入时补前缀，要么改用同语义的经典函数（`STDEV.S` → `STDEV`、`PERCENTILE.INC` → `PERCENTILE`、`CONCAT` → `CONCATENATE`）。
- **多区域函数的各区域必须同形**：`SUMIFS` / `COUNTIFS` / `AVERAGEIFS` / `MAXIFS` / `MINIFS` 的条件区与求和区行列数一致，`SUMPRODUCT` 的各数组也一致，否则求值返回 `#VALUE!`。横向年度块与纵向单列条件混用时尤其容易写错，按目标区域重新框定全部引用，不要只改其中一个参数。

## 导入或交付前必须过这条门禁

含公式或基于已有文件编辑的产物，导入或交付前跑这一条命令：

```bash
# 编辑已有文件：--baseline 给改前快照（就地改原文件时给动手前复制的那份备份），--scope 给本轮允许改动的范围
python3 scripts/excel_formula_verify.py ./output.xlsx 60 --baseline ./改前快照.xlsx --scope '明细!G:I'
# 从零新建：没有源可比，省掉后两个参数
python3 scripts/excel_formula_verify.py ./output.xlsx 60
```

一次查完五件事：公式重算、新函数前缀与数组形状（不依赖 LibreOffice）、推导区静态值嫌疑、源表被改写或丢失、公式覆盖率事实；传了 `--checkpoints` 时另按检查点逐条回读产物。两个非零码的处置相反，别混：

- **退出 3 是确定性错误，修完重跑**：`status='errors_found'`（公式错误值）、`static_risks.status='issues_found'`（缺前缀 / 形状不一致）、`baseline.blocking=true`（源 sheet 丢失、范围外改写或新增、原公式退化成静态值，或源文件 / 产物读不到导致这条门禁根本没跑成）、`checkpoints.blocking=true`（产物读不到，检查点没跑成）、`checkpoints.status='failed'`、文件读不了。stderr 会打印命中的格址与改法。
- **退出 4 是重算未完成或诊断信号，不要反复重跑**：`formula_execution_verified=false`（`inconclusive` / `skipped_no_libreoffice` / `skipped_no_workspace`，常见于宿主没装 LibreOffice）说明只拿到了只读诊断，交付说明写明公式未重算、提示在 Excel 中刷新即可，不得声称 zero-error；高置信静态值嫌疑同属这档，能公式化就改写，属历史 / 外部数据就在交付说明写明原因，不进入无止境修复。`checkpoints.status='inconclusive'`（有判不了的检查点）、`baseline.truncated_sheets` 非空（超上限只比了前半部分）、以及只给了 `--scope` 没给 `--baseline`（`baseline.degraded=true`，原表保护没有判据）也归这档：都表示还没判到，不能当成判过。
- 只有 `status='success'` 且 `formula_execution_verified=true` 才表示重算验证完成。
- 无论哪个非零码，都不得改用 Python 同源复算、公式字符串检查或公式计数冒充验证——同一套错误口径既生成又复算，只会证明错误模型自洽。

`--scope` 划的是「本轮允许改动」的完整边界：范围外的原值改写、原公式丢失，以及**从空白新增内容、新增整张子表**，都会被判为阻断。新增子表按格判定——范围精确写到该表的格（如 `新表!A1:A1`）就算获准，不必整表放行；没传 `--scope` 时新增只作为改动事实列出、不定性。

`--baseline` 可以重复传，多份会先并成一份联合快照再比一次，所以「另一份源里本来就有」的内容不会被误判成新增。同一坐标在两份源里取值不同时报 `baseline_conflicts`，状态为 `conflicted_baseline` 并阻断，且**跳过逐格对照**：基准不唯一时，那些差异只会建立在碰巧先读到的那份上，先确认该传哪一份再跑。在线自检同一套语义，冲突时把逐格对照记入未完成项。

`--scope` 的范围必须落在 Excel 的真实边界内（行 1..1048576、列 A..XFD），越界一律退出 3、不做 clamp——`A0:XFD9999999` 这类写错的范围若被接受，所有合法坐标都算范围内，等于把它放大成整表授权。

`--scope` 写法：`子表名!G:I`（整列）、`子表名!A2:C10`（区域）、`子表名`（整表），逗号分隔或重复本参数。子表名含逗号或感叹号时用单引号包起来（`'Sales,2026'!A1:A2`、`'Sales!2026'!A1:A2`），内部的单引号写成 `''`——逗号与分隔用的感叹号都只在引号外才生效。整列与整行范围必须正序（`A:Z`、`2:9`），写反了会退出 3 而不是被悄悄纠正；单元格范围仍按两端归一，`C10:A2` 等价于 `A2:C10`；范围在动手前就定下。不传 `--scope` 时工具只列改动清单、不定性。**范围写错会当场退出 3**（`明细!G2:G200x`、`明细!` 这类都算写错），不会退化成整表——否则范围外的改写会被判成允许。

### 检查点：把用户点名的数交给工具判

`--checkpoints @./cp.json`（也可内联 JSON）逐条回读产物。四种条目，同一份契约在线自检也认：

```json
[{"cell": "汇总!B12", "label": "含税收入合计", "expect": 1234.56, "tolerance": 0.01},
 {"range": "明细!G2:G200", "all_formula": true},
 {"range": "汇总!A1:D20", "non_empty": true},
 {"sheets": ["明细", "汇总", "说明"]}]
```

- 期望值只写用户明确给出的数，或你独立复算出来的数。把产物里读到的数抄进期望值，判出来的通过没有任何信息量。
- 引用必须带子表名；`expect` 只能对单格写，范围拆成多条。
- 一条只能写一个目标（`cell` / `range` / `sheets` 三选一），多写会被拒绝——判定只认一个，其余的连同判据会被静默跳过。
- `cell` / `range` 条目必须带至少一个判据（`expect` / `non_empty` / `formula` / `all_formula`），只写位置、或把 `non_empty` / `formula` / `all_formula` 写成 `false` 的条目都会被拒绝——它什么都不查，却会让整份契约看起来跑过了。`expect` 例外，期望值可以是 0 / false / 空串。
- `sheets` 必须是非空数组；`tolerance` 必须是非负有限数（`true` 会被当成 1，静默把比较放宽）。
- `all_formula` 要求区域内**每一格**都有公式，夹着的空格同样不合格；只想要求「非空格都是公式」时用 `formula`，它允许区域里留空。
- 本地新写的公式没有缓存值，值类条目会记为 skipped 并说明原因，不算通过也不算失败；重算完成后或导入在线表回读才判得了。
- 任一条不符即退出 3，stderr 列出格址、期望与实际。
- **有 skipped 就不算全过**：整体 `checkpoints.status='inconclusive'`，退出 4。判不了不等于通过，重算完成或导入在线表回读后重跑把它们判掉，在此之前不得声称检查点全过。

## 重算的依赖、降级与其余参数

```bash
python3 scripts/excel_formula_verify.py output.xlsx
# 指定超时（默认 30 秒；保留旧 positional timeout）
python3 scripts/excel_formula_verify.py output.xlsx 60
# 历史 / 外部静态数据 sheet 显式降 WARN（逗号分隔、sheet 名精确匹配）
python3 scripts/excel_formula_verify.py output.xlsx 60 --static-source-sheets "Comment History Snapshot,External Snapshot"
```

依赖：需要安装 LibreOffice（`soffice` 命令可用）。脚本首次运行时会自动配置宏。重算在临时副本上进行，**原文件不被修改**——公式缓存值因此不会写回产物，交付时可提示用户在 Excel 中刷新（`Ctrl+Alt+F9`）；确需把缓存值写进原文件时才加 `--in-place`——它由 LibreOffice 存回，会顺带重置行高、列宽、数字格式、颜色、底纹等视觉设置，样式敏感的产物不要用。

**LibreOffice 不可用或重算未完成时**：脚本仍扫描已有缓存错误、静态值嫌疑与可判定不变量，返回 `formula_execution_verified: false` 并以退出码 4 结束（状态为 `inconclusive` / `skipped_no_libreoffice` / `skipped_no_workspace`）。这只表示拿到了部分只读诊断，不能证明公式可执行；交付时必须标明风险并要求在 Excel 中刷新（`Ctrl+Alt+F9`），不得写“公式已验证无错误”。装不上 LibreOffice 的宿主上，退出 4 是这条门禁的正常终态，重跑几次都不会变成 0。

**图表按最终载体分流**：默认交付飞书表格时，不在本地 xlsx 创建图表；先导入，再按 Must-CLI 桥接用 `+chart-create` 建真实在线对象。只有用户明确只要本地 xlsx、或 Canvas 模式下 `lark-cli` 不可用时，才用 openpyxl 创建原生 chart，并在交付前重新打开文件确认 `ws._charts` 非空及数据引用、标题、图例、坐标轴符合用户要求。

### excel_formula_verify.py 输出解读

```json
{
  "status": "success",        // 或 "errors_found" / "inconclusive"
  "formula_execution_verified": true,
  "total_errors": 0,
  "total_formulas": 42,
  "error_summary": {          // 仅在有错误时出现
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  },
  "hardcode": {               // 硬编码嫌疑扫描
    "status": "clean",        // 或 "suspected"
    "total_suspects": 0,
    "high_confidence": 0,
    "details": []             // 命中的 sheet / 行列表头 / 静态数值个数
  },
  "static_risks": {           // 不依赖 LibreOffice 的静态判定，两条路径都有
    "status": "clean",        // 或 "issues_found"（缺 _xlfn 前缀 / 区域不同形）
    "compat": {"count": 0, "details": []},
    "shape": {"count": 0, "details": []},
    "coverage": {             // 公式覆盖率事实，不阻断
      "formula_cells": 42, "static_numeric_cells": 380, "formula_share": 0.0996
    }
  },
  "baseline": {               // 仅在传了 --baseline 时出现
    "status": "clean",        // 或 "differences_found" / "conflicted_baseline" / "partial" / "skipped"
    "truncated_sheets": [],   // 非空 = 该 sheet 超 20 万格上限只比了前半部分，此时状态为 partial 而非 clean
    "blocking": false,        // true = 源 sheet 丢失 / 范围外改写 / 原公式变静态值
    "scoped": true,
    "missing_sheet_count": 0,
    "changed_cells": 0,
    "formula_lost_cells": 0,
    "out_of_scope_changes": 0,
    "details": []
  },
  "invariants": {             // 公式不变量抽查（诊断信号，不阻断交付）
    "status": "ok",           // 或 "warn"（存在 mismatched）/ "skipped"
    "supported": 1,
    "mismatched": 0,
    "categories": {}          // arithmetic / tieout / sensitivity 三类明细
  }
}
```

`status='success'` 且 `formula_execution_verified=true` 才表示重算完成且未发现公式错误；`errors_found` 时按 `error_summary` 中的位置逐一修复。`formula_execution_verified=false` 时，即使 `total_errors=0` 也只是缓存扫描未命中错误，不得按通过处理。

`static_risks` 与 `baseline` 命中时，stderr 会打印命中的格址与改法；这两段是确定性判定，改完重跑。`coverage.formula_share` 是事实字段：要求联动的派生区如果整片都落在静态数值里，这个比值会很低，据此回头把派生格改成引用其他格的公式，并把关键输入集中成可修改的输入格。

`hardcode.status` 为 `suspected` 时，脚本会在 stderr 列出「表头表明是推导值、但整行/整列没有一个公式」的区域。这是诊断信号：能用公式表达且成本可控时改写；若属于历史快照 / 外部静态数据 / 公式表达困难，交付说明写明静态值原因即可。`--static-source-sheets "<sheet1>,<sheet2>"` 可用于点名这些来源，使命令输出更干净。

`invariants` 是三类公式不变量的抽查结果：`arithmetic`（行内四则 / 区间聚合公式重算对比）、`tieout`（资产负债表勾稽：资产总计 = 负债合计 + 权益合计，只认带「总计 / total」字样的标签行）、`sensitivity`（敏感性分析表数值单调性）。`mismatched > 0` 时对照 `categories.*.samples` 里的 sheet / 预期值 / 实际值核对公式区间；确认无误或属于刻意设计的，在交付说明记录即可，不进入反复修复循环。

**大表扫描上限**：硬编码扫描的表头 / 列画像取每 sheet 前 2000 行；「整表是否存在公式」单独做全表短路扫描，上限 50 万格——超限且仍未见公式时不会升级为 high（避免大表误判「整表无公式」），此时 hardcode 结论按抽样解读，公式存在性以你对表的实际了解为准。

## 公式验证检查清单

写公式前核对：

- [ ] **测试 2-3 个引用**：确认引用值正确后再批量构建
- [ ] **列号映射**：Excel 列从 1 开始，DataFrame 从 0 开始；列 64 = BL，不是 BK
- [ ] **行号偏移**：Excel 行从 1 开始；DataFrame 第 5 行 = Excel 第 6 行（含表头）
- [ ] **NaN 处理**：除法前用 `pd.notna()` 检查分母
- [ ] **空输入判空**：公式引用的输入列可能为空时先判空返回空（空格参与算术按 0 计，产出看似正常的错值且无错误码）
- [ ] **跨 sheet 引用**：格式为 `Sheet1!A1`
- [ ] **避免循环引用**：检查公式依赖链

## 常见错误及修复

| 错误 | 原因 | 修复方向 |
|------|------|---------|
| `#REF!` | 引用了不存在的单元格/区域 | 检查行列号是否越界或被删除 |
| `#DIV/0!` | 分母为零或空 | 加 `IF` 判断：`=IF(B2=0,"",A2/B2)` |
| `#VALUE!` | 数据类型不匹配（如文本参与计算） | 确保参与计算的列为数值型 |
| `#NAME?` | 函数名拼写错误 | 检查公式函数名 |
| `#N/A` | VLOOKUP/MATCH 找不到匹配项 | 加 `IFERROR` 或检查数据源 |

## 代码风格

生成 Excel 操作代码时：
- 代码精简，不加冗余注释
- 不打印中间过程日志
- 复杂公式或关键假设在旁边单元格加说明

---

## 时间格式转换

遇到 Excel 原始时间序列数时，用以下函数转换为可读格式：

```python
import datetime
from typing import Union

def excel_time_to_readable(excel_time: Union[float, int, str], date1904: bool = False) -> str:
    """将 Excel 时间序列数转换为人类可读时间（如 2023-12-31 12:00:00）"""
    excel_time = float(excel_time)
    base_date = datetime.datetime(1904, 1, 1) if date1904 else datetime.datetime(1899, 12, 30)
    days = int(excel_time)
    time_fraction = excel_time - days
    target_date = base_date + datetime.timedelta(days=days)
    seconds = int(time_fraction * 86400)
    time_obj = datetime.timedelta(seconds=seconds)
    if days == 0:
        return str(time_obj)
    return (target_date + time_obj).strftime("%Y-%m-%d %H:%M:%S")
```

**时间段拆分**：遇到 `09:00-18:00` 格式时，先拆分为开始/结束两列再计算时长：

```python
df[['start_time', 'end_time']] = df['time_range'].str.split('-', expand=True)
df['start_time'] = pd.to_datetime(df['start_time'], format='%H:%M')
df['end_time'] = pd.to_datetime(df['end_time'], format='%H:%M')
df['duration_hours'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600
```

---

## 行列操作

### openpyxl 行列操作

```python
from openpyxl import load_workbook

wb = load_workbook("data.xlsx")
ws = wb.active

ws.insert_rows(5, 3)   # 在第5行位置插入3行
ws.delete_rows(5, 2)   # 从第5行开始删除2行
ws.insert_cols(3, 2)   # 在第3列位置插入2列
ws.delete_cols(3, 1)   # 从第3列开始删除1列
ws.column_dimensions['C'].hidden = True  # 隐藏C列
```

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

### pandas 行列操作

```python
import pandas as pd

df = pd.read_excel("data.xlsx")

# 添加/删除列
df["利润"] = df["收入"] - df["成本"]
df.insert(2, "插入列", value=0)
df = df.drop(columns=["不需要的列"])
df = df.rename(columns={"旧列名": "新列名"})

# 添加/删除行
new_row = {"字段A": "值", "字段B": 100}
df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
df = df.drop(index=[0, 5])
df = df.reset_index(drop=True)
```

### 批量处理示例（pandas + openpyxl 组合）

```python
import pandas as pd
from copy import copy
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

def process_excel(input_file, output_file):
    df = pd.read_excel(input_file)
    df = df.dropna(thresh=len(df.columns) * 0.5)
    cols_to_drop = [col for col in df.columns if "Unnamed" in str(col)]
    df = df.drop(columns=cols_to_drop)
    df.to_excel(output_file, index=False)

    wb = load_workbook(output_file)
    ws = wb.worksheets[0]
    # 派生列（利润 / 利润率）写公式而非静态值——源数据变更后联动重算（公式优先原则）
    if "收入" in df.columns and "成本" in df.columns:
        rev_i = df.columns.get_loc("收入") + 1
        cost_i = df.columns.get_loc("成本") + 1
        rev, cost = get_column_letter(rev_i), get_column_letter(cost_i)
        # 复用已有的同名派生列位置，不存在才在末尾追加，避免生成重复列
        headers = [c.value for c in ws[1]]
        def col_of(name):
            if name not in headers:
                headers.append(name)
                ws.cell(row=1, column=len(headers), value=name)
            return headers.index(name) + 1
        # ⚠️ df.to_excel 重写整个文件，原表样式不会带过来（output 里全是默认样式），
        # 样式模板必须回到**原文件**取；且清洗已删行删列，行列号会位移，
        # 只能按表头名定位原成本列、取表头格 + 首个数据格当模板统一刷——原表有奇偶条纹等
        # 逐行差异样式时会被拉平（删行后无可靠行映射），这是 pandas 往返路径的固有限制。
        # （需要保留原表全部样式的编辑任务，应改用 openpyxl 原地修改，不走 pandas 往返。）
        def clone_style(dst, src):
            dst.font, dst.fill = copy(src.font), copy(src.fill)
            dst.border, dst.alignment = copy(src.border), copy(src.alignment)
            dst.number_format = src.number_format
        p_col, r_col = col_of("利润"), col_of("利润率")
        p, r = get_column_letter(p_col), get_column_letter(r_col)
        # 样式来源与 pd.read_excel 的数据来源必须是同一张 sheet：
        # read_excel 默认读第一个 sheet，这里同样取 worksheets[0]，不能用 .active
        # （active 是文件保存时的活动 sheet，可能不是第一张）
        src_ws = load_workbook(input_file).worksheets[0]
        src_hdr = [c.value for c in src_ws[1]]
        # 样式模板按「已有列优先」选：原表已有同名派生列 → 恢复它自己的样式 / 列宽 /
        # 数字格式（最小改动，不许拿成本列样式覆盖人家专门设计过的列）；
        # 原表没有该列（真正新建）→ 才用相邻成本列当模板
        def tpl_col(name):
            if name in src_hdr:
                return src_hdr.index(name) + 1
            if "成本" in src_hdr:
                return src_hdr.index("成本") + 1
            return None
        dat_tpls = {}
        for name, cidx, letter in (("利润", p_col, p), ("利润率", r_col, r)):
            si = tpl_col(name)
            if si is None:
                continue
            dat_tpls[cidx] = src_ws.cell(row=2, column=si)
            clone_style(ws.cell(row=1, column=cidx), src_ws.cell(row=1, column=si))
            w = src_ws.column_dimensions[get_column_letter(si)].width
            if w:
                ws.column_dimensions[letter].width = w
        for row in range(2, ws.max_row + 1):
            pc, rc = ws.cell(row=row, column=p_col), ws.cell(row=row, column=r_col)
            if p_col in dat_tpls:
                clone_style(pc, dat_tpls[p_col])
            if r_col in dat_tpls:
                clone_style(rc, dat_tpls[r_col])
            pc.value = f"={rev}{row}-{cost}{row}"
            rc.value = f'=IF({rev}{row}=0,"",{p}{row}/{rev}{row})'
            if "利润率" not in src_hdr:
                rc.number_format = "0.00%"  # 新建列才设默认百分比；已有列保留原格式

    # 新建区域的列宽、换行与行高按 ref-excel-visual-standards.md 中
    # fit_one_column() 的统一规则处理，不在技术工作流中重复定义视觉参数。
    wb.save(output_file)
```

### 范围清空与重置

默认只清内容并保留样式；只有用户明确要求“重置格式”时才清除样式。将两种动作拆开，避免普通清空误删字体、边框、填充、数字格式和对齐：

```python
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.utils.cell import range_boundaries

def clear_values(ws, range_str: str):
    """仅清内容，保留样式和结构。"""
    sc, sr, ec, er = range_boundaries(range_str)
    for r in range(sr, er + 1):
        for c in range(sc, ec + 1):
            ws.cell(row=r, column=c).value = None

def reset_range(ws, range_str: str):
    """仅在用户明确要求重置格式时，清空内容并重置目标范围样式。"""
    sc, sr, ec, er = range_boundaries(range_str)
    for r in range(sr, er + 1):
        for c in range(sc, ec + 1):
            cell = ws.cell(row=r, column=c)
            cell.value = None
            cell.font = Font()
            cell.border = Border()
            cell.fill = PatternFill()
            cell.number_format = "General"
            cell.alignment = Alignment()
```

需要删除并上移/左移时，显式调用 `ws.delete_rows(...)` / `ws.delete_cols(...)`，不要把结构删除混入普通清空函数。

---

## 读取数据验证规则（下拉框 / 输入限制）

用户上传的表常带数据验证（下拉列表、整数范围、日期范围等）。修改这类表时**先读取规则**，避免写入与规则冲突的值导致 Excel 打开报错：

```python
from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

def get_cell_validation(filepath: str, sheet_name: str, cell_address: str) -> dict:
    """返回某单元格的数据验证元信息，未命中规则时 has_validation=False。"""
    wb = load_workbook(filepath)
    ws = wb[sheet_name]
    col_letter, row = coordinate_from_string(cell_address)
    col_idx = column_index_from_string(col_letter)
    for dv in ws.data_validations.dataValidation:
        for rng in dv.sqref.ranges:
            if rng.min_row <= row <= rng.max_row and rng.min_col <= col_idx <= rng.max_col:
                info = {
                    "cell": cell_address,
                    "has_validation": True,
                    "type": dv.type,                 # list / whole / decimal / date / time / textLength / custom
                    "operator": dv.operator,
                    "allow_blank": dv.allowBlank,
                    "formula1": dv.formula1,
                    "formula2": dv.formula2,
                }
                if dv.type == "list" and dv.formula1:
                    raw = dv.formula1.strip().strip('"')
                    if "," in raw and not raw.startswith("$"):
                        info["allowed_values"] = [v.strip().strip('"') for v in raw.split(",") if v.strip()]
                    else:
                        info["allowed_values_ref"] = raw
                return info
    return {"cell": cell_address, "has_validation": False}
```

常见数据验证类型：

| `type` | 含义 | `formula1` / `formula2` 示例 |
|--------|------|----|
| `list` | 下拉列表 | `"是,否,待定"` 或 `$A$1:$A$10` |
| `whole` | 整数范围 | `formula1=1, formula2=100`（配合 operator=`between`） |
| `decimal` | 小数范围 | 同上 |
| `date` | 日期范围 | `formula1=2024-01-01` |
| `textLength` | 文本长度 | `formula1=10` |
| `custom` | 自定义公式 | `=AND(A1>0,A1<100)` |

写入时若违反规则会出现 `Excel 已发现"file.xlsx"中的部分内容存在问题`。修改前先调用 `get_cell_validation` 拿到 `allowed_values`，再决定是直接使用合法值还是先 `ws.data_validations.dataValidation.remove(dv)` 移除规则。

===== 全文完（共 603 行）=====
