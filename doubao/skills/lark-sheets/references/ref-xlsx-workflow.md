# Excel 文件技术工作流（xlsx workflow）

本文件覆盖 Excel 文件的创建、编辑、公式重算与验证的完整技术流程。

## 工具选择

| 工具 | 适用场景 |
|------|---------|
| **pandas** | 数据分析、批量读写、简单数据导出 |
| **openpyxl** | 复杂格式、公式写入、Excel 特性（合并单元格、颜色、样式） |

两者可组合：pandas 处理数据逻辑，openpyxl 负责格式与公式。


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
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active

ws['A1'] = '标题'
ws['B2'] = '=SUM(B3:B10)'   # 写公式，不写硬编码计算值

ws['A1'].font = Font(bold=True, color='FF0000')
ws['A1'].fill = PatternFill('solid', start_color='FFFF00')
ws['A1'].alignment = Alignment(horizontal='center')
ws.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

### 标准 Excel Table（ListObject）

把数据范围注册为原生 Excel Table，自带筛选/排序/条带样式，且后续公式可用结构化引用（`=表名[列名]`）：

```python
from openpyxl.worksheet.table import Table, TableStyleInfo

tbl = Table(displayName="销售明细", ref="A1:F100")  # 必须包含表头行
tbl.tableStyleInfo = TableStyleInfo(
    name="TableStyleMedium9",   # Light/Medium/Dark + 编号，可在 Excel 中预览
    showRowStripes=True,
    showColumnStripes=False,
)
ws.add_table(tbl)
```

注意：`displayName` 在工作簿内必须唯一；`ref` 必须是矩形区域且第一行为表头。

## 单元格设置（行高 / 列宽 / 截断）

如果你是在**新建 sheet 或新建表格区域**输出结果，且用户未指定行高/列宽等细节，可以按表格形态做统一排版；如果你是在修改用户现有模板且用户未要求“整理格式/统一行高列宽”，则应保持原有行高列宽与对齐方式不变。

### 规则（默认）

- 多行多列（行 > 1 且列 > 1）：行高 50，列宽 80，截断
- 单列表格（列 = 1）：列宽 150，截断
- 单行表格（行 = 1）：行高 50，截断

### 截断含义

- 不换行：`wrap_text=False`
- 对超长字符串做字符截断并加省略号，避免溢出影响阅读

```python
from __future__ import annotations

from typing import Optional, Tuple

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def _used_range(ws: Worksheet) -> Tuple[int, int]:
    max_row = 0
    max_col = 0
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            if cell.value is None:
                continue
            max_row = max(max_row, cell.row)
            max_col = max(max_col, cell.column)
    return max_row, max_col


def _truncate_text(value: object, max_chars: int) -> object:
    if not isinstance(value, str):
        return value
    s = value.strip()
    if len(s) <= max_chars:
        return value
    if max_chars <= 1:
        return "…"
    return s[: max_chars - 1] + "…"


def _col_width_chars(ws: Worksheet, col_index: int, default_width: int = 10) -> int:
    letter = get_column_letter(col_index)
    width = ws.column_dimensions[letter].width
    if width is None:
        return default_width
    try:
        return max(1, int(round(float(width))))
    except (TypeError, ValueError):
        return default_width


def apply_table_cell_settings(
    ws: Worksheet,
    *,
    target_range: Optional[Tuple[int, int]] = None,
) -> None:
    max_row, max_col = target_range or _used_range(ws)
    if max_row <= 0 or max_col <= 0:
        return

    set_row_height = (max_row == 1) or (max_row > 1 and max_col > 1)
    set_col_width = (max_col == 1) or (max_row > 1 and max_col > 1)

    row_height = 50
    col_width = 150 if max_col == 1 else 80

    align = Alignment(wrap_text=False, vertical="center")

    if set_col_width:
        for c in range(1, max_col + 1):
            ws.column_dimensions[get_column_letter(c)].width = col_width

    if set_row_height:
        for r in range(1, max_row + 1):
            ws.row_dimensions[r].height = row_height

    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            if cell.value is None:
                continue
            max_chars = col_width if set_col_width else _col_width_chars(ws, c)
            cell.value = _truncate_text(cell.value, max_chars)
            cell.alignment = align
```

## 编辑已有 Excel 文件

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

`formula_verify.py` 是**事后重算**——在交付前确认无 `#REF!`/`#NAME?`。但事前也要做一次廉价的语法校验，能拦住大部分手写笔误，避免重算阶段才暴露错误：

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

**双重校验闭环**：写入时套用上文 `safe_set_formula` 函数（需自行纳入脚本，事前） → 保存后跑独立脚本 `formula_verify.py`（事后）。两道关卡基本能消灭所有公式错误。

## 公式重算（必做步骤）

openpyxl 写入的公式只是字符串，单元格中没有计算值。**凡包含公式的交付文件必须执行重算**：

```bash
python scripts/formula_verify.py output.xlsx
# 或指定超时（默认30秒）
python scripts/formula_verify.py output.xlsx 60
```

依赖：需要安装 LibreOffice（`soffice` 命令可用）。脚本首次运行时会自动配置宏。

**LibreOffice 不可用时的降级行为**：若 `soffice` 未安装，脚本自动降级——跳过重算，仅扫描文件中已有的公式错误值，返回 `status: "skipped_no_libreoffice"` 并附带警告。此时公式单元格不含计算值，交付文件需告知用户在 Excel 中手动刷新（`Ctrl+Alt+F9`）。

### formula_verify.py 输出解读

```json
{
  "status": "success",        // 或 "errors_found"
  "total_errors": 0,
  "total_formulas": 42,
  "error_summary": {          // 仅在有错误时出现
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

`status` 为 `errors_found` 时，按 `error_summary` 中的位置逐一修复，再重新执行重算直到 `status` 为 `success`。

## 公式验证检查清单

写公式前核对：

- [ ] **测试 2-3 个引用**：确认引用值正确后再批量构建
- [ ] **列号映射**：Excel 列从 1 开始，DataFrame 从 0 开始；列 64 = BL，不是 BK
- [ ] **行号偏移**：Excel 行从 1 开始；DataFrame 第 5 行 = Excel 第 6 行（含表头）
- [ ] **NaN 处理**：除法前用 `pd.notna()` 检查分母
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
from openpyxl import load_workbook
from openpyxl.styles import Alignment

def process_excel(input_file, output_file):
    df = pd.read_excel(input_file)
    df = df.dropna(thresh=len(df.columns) * 0.5)
    cols_to_drop = [col for col in df.columns if "Unnamed" in str(col)]
    df = df.drop(columns=cols_to_drop)
    if "收入" in df.columns and "成本" in df.columns:
        df["利润"] = df["收入"] - df["成本"]
        df["利润率"] = (df["利润"] / df["收入"] * 100).round(2)
    df.to_excel(output_file, index=False)

    wb = load_workbook(output_file)
    ws = wb.active
    for col in ws.columns:
        lengths = []
        needs_wrap = False
        for cell in col[:501]:
            s = str(cell.value or "")
            if len(s) > 40:
                needs_wrap = True
            lengths.append(min(len(s), 100))
        lengths.sort()
        p95 = lengths[int(0.95 * (len(lengths) - 1))] if lengths else 0
        width = max(8, min(p95 + 2, 40))
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = width
        if needs_wrap:
            for cell in col[1:501]:
                cell.alignment = Alignment(wrap_text=True)
    wb.save(output_file)
```

### 范围清空与重置

仅清 value 不够时（残留底色/数值格式会污染后续输出），用以下函数把范围彻底重置：

```python
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.utils.cell import range_boundaries

def reset_range(ws, range_str: str, *, shift: str | None = None):
    """清空 value + 重置 Font/Border/Fill/number_format/alignment。
    shift='up' 上移整行；shift='left' 左移整列；None 仅清内容。"""
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
    if shift == "up":
        ws.delete_rows(sr, er - sr + 1)
    elif shift == "left":
        ws.delete_cols(sc, ec - sc + 1)
```

`shift='up'/'left'` 相当于 Excel 的「删除并上移/左移」，常用于剔除整段空行/空列。

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
