# DOCX 排版规范

> format_seriousness: I-Practical
> 引用体系: base/rule/format-docx/
> 说明：I-Practical 内部级，不适用 style-authority-retrieval.md 权威检索，但庭审打印携带需DOCX排版。参照 evidence 族 F-Strict 质证表格排版但自定义布局。
> 版本：v2.2.0

---

## 1. 排版参数

### 1.1 页面设置

| 参数 | 值 | 说明 |
|------|---|------|
| 纸张 | A4 纵向 | 标准法律文书纸张 |
| 页边距-上 | 2.0cm | 与 base I-Practical 规范一致 |
| 页边距-下 | 1.5cm | 与 base I-Practical 规范一致 |
| 页边距-左 | 3.0cm | 宽边距便于装订+庭审手写批注 |
| 页边距-右 | 1.5cm | 与 base I-Practical 规范一致 |
| 页眉 | 微软雅黑 9pt（小五号），居右，内容："质证提纲 [案号简称]" + 日期 | I-Practical 允许可选页眉 |
| 页脚 | 页码居中，"— X —"格式，微软雅黑 9pt（小五号），距底端1.5cm | 多页文书需页码保护页序 |
| 装订线 | 无（左3.0cm页边距已含装订空间） | — |

### 1.2 字体方案

| 用途 | 中文字体 | 西文字体 | 字号 | 粗细 | 说明 |
|------|---------|---------|------|------|------|
| 文档标题 | 微软雅黑 | — | 18pt（小二号） | 加粗 | 居中，与 base I-Practical 一级标题对齐 |
| 证据标题 | 微软雅黑 | — | 14pt（四号） | 加粗 | 左对齐，如"证据一：被害人李某陈述（被害人陈述）—— E-Oral-01" |
| 三性段标题 | 微软雅黑 | — | 12pt（小四号） | 加粗 | 左对齐，如"（一）合法性（证据能力）" |
| 正文 | 微软雅黑 | Calibri | 10.5pt（五号） | 常规 | 中文微软雅黑+西文Calibri |
| 表格内容 | 微软雅黑 | Calibri | 10.5pt（五号） | 常规 | 与正文一致 |
| 表头 | 微软雅黑 | — | 10.5pt（五号） | 加粗 | 灰底RGB(230,230,230) |
| 备注列小字 | 微软雅黑 | — | 9pt（小五号） | 常规 | 勾选框文字+批注区标注 |
| 草稿声明 | 微软雅黑 | — | 9pt（小五号） | 常规 | 页眉右对齐或文档开头声明 |
| 落款 | 微软雅黑 | — | 10.5pt（五号） | 常规 | 右对齐，签名行+日期 |

### 1.3 行距与段落

| 用途 | 行距 | 段前 | 段后 | 说明 |
|------|------|------|------|------|
| 正文 | 1.15倍 | 0pt | 3pt | 适中密度，便于庭审快速浏览 |
| 标题 | 1.15倍 | 6pt | 3pt | 段前略留空间 |
| 三性段标题 | 1.15倍 | 4pt | 2pt | 段前略留空间 |
| 表格内 | 单倍 | 0pt | 0pt | 紧凑排列 |
| 草稿声明 | 1.0倍 | 0pt | 6pt | 声明后留空间 |

---

## 2. 文档结构

### 2.1 组件序列

| 顺序 | 内容 | 格式 | 字号 | 对齐 |
|------|------|------|------|------|
| 1 | 草稿声明 | 居中，灰色文字 | 9pt | 居中 |
| 2 | 标题："质证提纲" | 微软雅黑加粗居中 | 18pt | 居中 |
| 3 | 案件元信息行（被告人/案号/开庭日期/辩护方向） | 微软雅黑，右对齐 | 10.5pt | 右对齐 |
| 4 | 证据清单-编号对照表（三列：编号/证据名称/证据类型） | 微软雅黑，小字 | 9pt | 左对齐 |
| 5 | 质证主表格 | 五列表格 | 10.5pt | — |
| 6 | 质证小结段 | 正文格式 | 10.5pt | 左对齐 |
| 7 | exclusion转交提示（如有） | 正文格式，🔴标记 | 10.5pt | 左对齐 |
| 8 | 交叉询问问题清单（独立表格，如有） | 三列表格 | 10.5pt | — |
| 9 | 落款："辩护人：[签名]" + 日期 | 右对齐 | 10.5pt | 右对齐 |

### 2.2 层级视觉差

| 层级 | 字号 | 粗细 | 层级差（相对正文） |
|------|------|------|-------------------|
| 文档标题 | 18pt | 加粗 | 1.71倍（与 base I-Practical 一级标题对齐） |
| 证据标题 | 14pt | 加粗 | 1.33倍 |
| 三性段标题 | 12pt | 加粗 | 1.14倍 |
| 正文 | 10.5pt | 常规 | 1.00倍（基准） |

---

## 3. 表格排版

### 3.1 证据清单-编号对照表（三列）

| 列名 | 列宽 | 对齐 | 说明 |
|------|------|------|------|
| 编号 | 3cm | 居中 | E-Oral-01等编号 |
| 证据名称 | 7cm | 左对齐 | 证据全称 |
| 证据类型 | 6cm | 居中 | 如"被害人陈述"/"书证"/"鉴定意见" |

- 字号：9pt（小五号），紧凑排列
- 边框：0.5pt实线（与 base F-Strict 对齐），表头加粗灰底 RGB(230,230,230)
- 无需勾选框

### 3.2 质证主表格（五列）

| 列名 | 宽度比例 | 具体cm值（A4可用宽度~16cm） | 对齐 | 说明 |
|------|---------|---------------------------|------|------|
| 证据编号 | 10% | 1.6cm | 居中 | E-Oral-01等7字符编号 |
| 证据名称 | 20% | 3.2cm | 左对齐 | 证据简称 |
| 质证意见 | 38% | 6.08cm | 左对齐 | 三性分段内容+综合评价 |
| 法律依据 | 17% | 2.72cm | 居中 | 法条编号引用 |
| 备注 | 15% | 2.4cm | 左对齐 | 庭审查看勾选框+手写批注区 |

- 字号：10.5pt（五号）
- 边框：0.5pt实线（与 base F-Strict 对齐），表头加粗灰底 RGB(230,230,230)
- 每行一个证据，质证意见按合法性→真实性→关联性顺序用序号分段
- 单元格内换行使用`<br>`或换行符

### 3.3 交叉询问问题清单（独立表格，按需输出）

| 列名 | 宽度比例 | 说明 |
|------|---------|------|
| 证据编号 | 15% | 对应主表格编号 |
| 交叉询问问题 | 60% | 3-5个开放性问题 |
| 备注 | 25% | 庭审记录用 |

- 字号：10.5pt（五号）
- 边框：0.5pt实线
- 仅在证据较多或交叉询问问题较长时独立输出

---

## 4. 备注列设计（庭审现场区）

### 4.1 庭审查看勾选框

每行备注列包含三选一勾选框：
```
□ 同意  □ 部分同意  □ 异议
```

**实现方式**：使用 Unicode 字符 □ (U+25A1) 作为勾选框占位符，律师庭审时手写打勾或使用Word批注标记。不使用 Content Control 或表单域（兼容性问题）。

### 4.2 手写批注区

勾选框下方留两行空白（"___________"），供律师庭审时记录：
- 对方回应要点
- 法官态度和追问方向
- 当庭调整策略备忘

### 4.3 备注列字体

- 勾选框文字：微软雅黑 9pt（小五号）
- 批注区下划线：9pt，浅灰色 RGB(200,200,200)

---

## 5. 特殊格式

### 5.1 三性质证标准表述（DOCX内）

- **合法性（证据能力）**：证据的收集主体/程序/形式是否合法，是否存在刑讯逼供/暴力取证等应排除情形
- **真实性（证明力）**：证据内容是否真实可靠，是否与原件/原物核对一致
- **关联性（证明力）**：证据与待证事实之间的逻辑关系与证明方向

### 5.2 重大违法标记

发现重大违法时在质证意见中加"🔴"前缀标识。

**emoji渲染备选方案**：鉴于🔴等彩色emoji在不同Word版本/打印环境下可能显示为方框或黑白方块，提供文字备选方案：
- 🔴 → 【严重】（纯文字替代，加粗红色 RGB(255,0,0)）
- 🟡 → 【注意】（纯文字替代，加粗橙色 RGB(255,165,0)）

**渲染策略**：优先使用emoji，同时在emoji后附文字备选。如：
```
🔴【严重】合法性存在刑讯逼供嫌疑
🟡【注意】程序瑕疵，提请法庭注意
```

### 5.3 exclusion转交提示格式

在质证主表格后附单独段落：
```
🔴【严重】建议同步调用 criminal-evidence-exclusion 起草《非法证据排除申请书》
证据：[证据编号] [证据名称]
理由：[简要理由]
```

### 5.4 草稿声明

文档开头居中声明：
```
⚠️ 此质证提纲仅为草稿，未经律师审核不得直接用于庭审。
```
字号：9pt，颜色：灰色 RGB(150,150,150)

---

## 6. 分页与打印规则

### 6.1 分页规则

| 规则 | 说明 |
|------|------|
| 不允许表格行跨页断裂 | 当一个证据的质证内容超过当前页剩余空间时，整行移至下一页 |
| 表头每页重复 | 质证主表格表头在每页顶部重复显示 |
| 证据间分页 | 证据较多时，每份证据的质证内容不强制分页，但建议在关键证据间插入分页符便于庭审翻阅 |
| 证据清单对照表不分页 | 证据清单对照表应在一页内完成，如超长则缩小字号至8pt |

### 6.2 打印适配

| 设置 | 值 | 说明 |
|------|---|------|
| 打印方向 | 纵向 | A4纵向 |
| 缩放比例 | 100%（不缩放） | 10.5pt字号打印后清晰可读 |
| 双面打印 | 允许 | 左3.0cm宽边距已考虑装订需求 |
| 奇偶页边距 | 对称（不设奇偶页差异） | 简化打印流程 |
| 页边距对称性 | 左3.0cm/右1.5cm | 单面打印时左侧留装订空间；双面打印时奇数页左3.0cm右1.5cm，偶数页左1.5cm右3.0cm |

### 6.3 页码规则

- 格式："— X —"居中
- 字号：微软雅黑 9pt
- 位置：页脚居中，距底端1.5cm
- 首页不计页码（草稿声明页不编页码）

---

## 7. 差异覆盖声明

### 7.1 与 base/rule/format-docx/ I-Practical 规范的差异

| 参数 | base I-Practical 规范 | 本技能自定义值 | 覆盖理由 |
|------|---------------------|--------------|---------|
| 一级标题字号 | 18pt(小二)加粗居中 | 18pt(小二)加粗居中 | ✅ 一致 |
| 标题字号(旧版) | — | ~~14pt~~ | v2.1.2已修正为18pt对齐base |
| 行距 | 未规定（F-Strict=固定28磅，C-Professional=1.5倍） | 1.15倍 | 庭审携带需紧凑排版，1.15倍兼顾可读性与信息密度 |
| 表格边框 | F-Strict=0.5pt实线 | 0.5pt实线 | ✅ 对齐F-Strict |
| 表头灰底 | — | RGB(230,230,230) | 指定色值避免渲染差异 |
| 页眉 | 允许可选 | 质证提纲+案号+日期 | 庭审多页文书需页眉标识 |
| 页脚 | I-Practical默认无 | — X — 页码居中 | 多页文书需页码保护页序 |
| 西文字体 | Calibri 或 Arial | Calibri | 明确指定 |

### 7.2 与 L3 类型规格卡 T-examination-opinion.md 的差异

| 维度 | T-examination-opinion（F-Strict） | 本技能（I-Practical） | 说明 |
|------|--------------------------------|---------------------|------|
| 列数 | 5列（序号/对方证据编号/质证意见/质证理由/法律依据） | 5列（证据编号/证据名称/质证意见/法律依据/备注） | I-Practical自定义布局，增加备注列用于庭审批注 |
| 权威来源 | T1（最高法） | T3（内部文书） | 质证提纲属私人法律文书，无T1级别统一格式 |
| 勾选框 | 无 | 有（□同意/□部分同意/□异议） | 庭审现场查看功能 |

---

## 8. python-docx 渲染指令

### 8.1 页面设置

```python
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
section = doc.sections[0]
section.page_width = Cm(21.0)   # A4
section.page_height = Cm(29.7)  # A4
section.top_margin = Cm(2.0)
section.bottom_margin = Cm(1.5)
section.left_margin = Cm(3.0)
section.right_margin = Cm(1.5)
```

### 8.2 页眉页脚

```python
# 页眉
header = section.header
header_para = header.paragraphs[0]
header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
header_run = header_para.add_run("质证提纲 [案号简称] YYYY-MM-DD")
header_run.font.size = Pt(9)
header_run.font.name = "微软雅黑"

# 页脚（页码）
footer = section.footer
footer_para = footer.paragraphs[0]
footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
# 使用Word域代码插入页码：— {PAGE} —
```

### 8.3 标题

```python
title = doc.add_heading("质证提纲", level=1)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.font.size = Pt(18)
    run.font.name = "微软雅黑"
    run.font.bold = True
```

### 8.4 案件元信息行

```python
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
meta_run = meta.add_run("被告人：[name] | 案号：[case_no] | 开庭日期：[date] | 辩护方向：[type]")
meta_run.font.size = Pt(10.5)
meta_run.font.name = "微软雅黑"
```

### 8.5 证据清单-编号对照表

```python
evidence_table = doc.add_table(rows=n+1, cols=3)
evidence_table.style = 'Table Grid'
# 表头
for i, header_text in enumerate(["编号", "证据名称", "证据类型"]):
    cell = evidence_table.rows[0].cells[i]
    cell.text = header_text
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.font.size = Pt(9)
            run.font.bold = True
            run.font.name = "微软雅黑"
    # 灰底
    from docx.oxml.ns import qn
    shading = cell._element.get_or_add_tcPr()
    shading_elem = OxmlElement('w:shd')
    shading_elem.set(qn('w:fill'), 'E6E6E6')  # RGB(230,230,230)
    shading.append(shading_elem)
```

### 8.6 质证主表格

```python
main_table = doc.add_table(rows=n+1, cols=5)
main_table.style = 'Table Grid'
# 列宽设置
col_widths = [Cm(1.6), Cm(3.2), Cm(6.08), Cm(2.72), Cm(2.4)]
for row in main_table.rows:
    for i, width in enumerate(col_widths):
        row.cells[i].width = width
# 表头
headers = ["证据编号", "证据名称", "质证意见", "法律依据", "备注"]
# 数据行：质证意见按三性分段
# 备注列：□ 同意 □ 部分同意 □ 异议\n___________
```

### 8.7 重大违法标记

```python
# 使用文字备选方案替代emoji
severity_run = para.add_run("【严重】")
severity_run.font.bold = True
severity_run.font.color.rgb = RGBColor(255, 0, 0)  # 红色
severity_run.font.size = Pt(10.5)

attention_run = para.add_run("【注意】")
attention_run.font.bold = True
attention_run.font.color.rgb = RGBColor(255, 165, 0)  # 橙色
attention_run.font.size = Pt(10.5)
```

### 8.8 落款

```python
signature = doc.add_paragraph()
signature.alignment = WD_ALIGN_PARAGRAPH.RIGHT
sig_run = signature.add_run("辩护人：[签名]\n日期：YYYY年MM月DD日")
sig_run.font.size = Pt(10.5)
sig_run.font.name = "微软雅黑"
```

### 8.9 表格分页设置

```python
# 不允许表格行跨页断裂
from docx.oxml.ns import qn
for row in main_table.rows:
    tr = row._element
    trPr = tr.get_or_add_trPr()
    cantSplit = OxmlElement('w:cantSplit')
    cantSplit.set(qn('w:val'), '1')
    trPr.append(cantSplit)

# 表头每页重复
main_table.rows[0]._element.get_or_add_trPr().append(
    OxmlElement('w:tblHeader')
)
```

---

*本文件遵循 compiler/ssot.md §17（SSOT）：I-Practical 内部级自定义排版，庭审打印携带专用*
