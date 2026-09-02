# 量刑建议对比表模板

> criminal-plea-negotiation | DOCX 模板 | v2.1.0
> 排版规范见 docx-format-spec.md §8.1

## 模板结构

```
[表格标题]  黑体小四号居中加粗 "量刑建议对比表"

| 对比项 | 检察院建议 | 辩方意见 | 差距分析 |
|--------|-----------|---------|---------|
| 主刑   | [填入]     | [填入]  | [填入]  |
| 附加刑 | [填入]     | [填入]  | [填入]  |
| 缓刑   | [填入]     | [填入]  | [填入]  |
| 罚金   | [填入]     | [填入]  | [填入]  |

表格样式：三线表（顶线粗1.5pt+表头下线粗1pt+底线粗1.5pt），无竖线。
表头：黑体小四号居中加粗。
表格内容：仿宋小四号。
列宽：第1列3cm / 第2列4cm / 第3列4cm / 第4列4cm。
```

## 填写指南

| 对比项 | 检察院建议列 | 辩方意见列 | 差距分析列 |
|--------|------------|-----------|-----------|
| 主刑 | 检察院建议的刑期+刑种 | 辩方主张的刑期+刑种 | 差距大小+争议核心 |
| 附加刑 | 剥夺政治权利/没收财产等 | 辩方对附加刑的意见 | 是否存在争议 |
| 缓刑 | 是否建议缓刑 | 是否争取缓刑 | 缓刑条件的差距 |
| 罚金 | 检察院建议的罚金数额 | 辩方对罚金的意见 | 罚金数额的差距 |

## python-docx 渲染提示

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn

def create_sentencing_comparison_table(doc, data):
    """创建量刑建议对比表（三线表）
    
    data = {
        "主刑": {"检察院": "8-10年", "辩方": "4-6年", "差距": "差距较大，核心争议在第3笔"},
        "附加刑": {...},
        "缓刑": {...},
        "罚金": {...}
    }
    """
    # 表格标题
    title = doc.add_paragraph("量刑建议对比表")
    title.style = doc.styles['Table Title']
    
    # 创建4列N行表格
    table = doc.add_table(rows=len(data)+1, cols=4)
    
    # 表头
    headers = ["对比项", "检察院建议", "辩方意见", "差距分析"]
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        # 黑体小四号居中加粗
    
    # 数据行
    for row_idx, (key, values) in enumerate(data.items(), 1):
        table.rows[row_idx].cells[0].text = key
        table.rows[row_idx].cells[1].text = values["检察院"]
        table.rows[row_idx].cells[2].text = values["辩方"]
        table.rows[row_idx].cells[3].text = values["差距"]
        # 仿宋小四号
    
    # 三线表边框设置
    # ... (详见 docx-format-spec.md §8.1)
```
