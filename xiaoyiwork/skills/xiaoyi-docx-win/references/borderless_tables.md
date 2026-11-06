# Borderless Table Layout (无边框表格排版)

Word 中最稳定的对齐技术。用看不见的表格实现精确排版，比 Tab Stops 更可靠。

---

## 核心原理

**为什么用无边框表格？**

| 问题 | Tab Stops 方案 | 无边框表格方案 |
|------|----------------|----------------|
| 多行内容对齐 | 每行独立设置，容易错位 | 整行作为单元格，天然对齐 |
| 图文混排 | 基线难以对齐 | 单元格内垂直居中 |
| 内容长度变化 | 可能溢出或留白 | 自动适应 |

**基本思路**：创建表格 → 设置列宽 → 填充内容 → 移除边框

---

## 基础用法

```python
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx_utils import remove_table_borders

# 创建无边框表格
table = doc.add_table(rows=1, cols=2)
table.autofit = False                          # Must disable for custom widths
table.columns[0].width = Inches(3.25)          # Set column widths
table.columns[1].width = Inches(3.25)

table.rows[0].cells[0].text = "Left content"
table.rows[0].cells[1].text = "Right content"

remove_table_borders(table)                    # Remove all borders
```

---

## 必备注意事项

### 1. 列宽设置

```python
table.autofit = False  # 必须先关闭，否则自定义宽度不生效
```

总宽度参考（A4 页面，1英寸边距）：
- 单栏内容区：约 6.5 英寸
- 双栏布局：3.25 + 3.25
- 标签+值：1.5 + 5.0

### 2. 单元格边距

使用 `docx_utils.py` 中的函数：

```python
from docx_utils import set_cell_margins

# 参数单位：twips（1 pt = 20 twips）
set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
```

### 3. 局部边框（下划线效果）

```python
from docx_utils import set_cell_border

# 只保留下边框，其他无边框
set_cell_border(cell, bottom='000000')  # 黑色下划线
```

### 4. 垂直对齐

```python
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
```

---

## 何时用什么方案

| 场景 | 推荐方案 |
|------|----------|
| 单行左右对齐 | Tab Stops |
| 多行标签对齐 | 无边框表格 |
| 图文并排 | 无边框表格 |
| 下划线填空 | 无边框表格 + 局部边框 |
| 复杂网格布局 | 无边框表格 |
