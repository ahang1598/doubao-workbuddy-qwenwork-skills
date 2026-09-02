# 输出规范

本文件包含三部分，彼此独立：

- **§§A** DOCX 排版规范——Phase 7 用户选择 A 或 C 时适用
- **§§B** Markdown 排版规范——Phase 7 用户选择 B 或 C 时适用
- **§§C** SOFT_DEGRADED 降级定义——降级时适用
- **§§D** 报告内容结构规范——所有输出格式通用

---

## §§D 报告内容结构规范（所有格式通用）

### D1 报告日期规则

报告必须同时标注两个日期：

- **审查基准日**：输入材料/事实的基准日期（如"基于截至 202X年X月X日的材料"）
- **报告出具日**：实际输出报告的日期

若基准日与出具日之间已过关键节点（许可证到期日、比例整改截止日等），出具前必须检查基准日结论是否仍有效。若关键节点已过期，必须以出具日现状重新判断该层结论，并在引言中明确标注"基准日结论已因xxx过期而更新"。

### D2 九部分强制结构（三段式框架）

报告九部分按三段式框架组织——引言→正文→结尾→附件。九大部分标题对应 DOCX 一级标题（"一、""二、"…"九、"），二级标题为"（一）（二）（三）"，三级标题为"1. 2. 3."。

**引言**

1. 引言
   - **审查基准日** / **出具日**（两个日期必须同时标注）
   - 综合风险等级（按 D3 风险等级标注）
   - 角色识别（用工单位/派遣单位）
   - **用工全景快照（强制输出）**：用工总人数 | 正式:派遣:外包比例 | 核心风险一句话总结
     > 示例：用工总人数365人 | 正式260:派遣80:外包25（71.2%:21.9%:6.8%） | 派遣比例超标（21.9%>10%）+3岗位三性不成立+许可证即将到期，综合风险🔴高风险

**正文**

2. 主体资格与资质审查（含历史履约审查结果）
3. 派遣岗位合规性审查（逐岗位三性分析表，禁止批量结论）
4. 派遣用工比例审查（含两种罚款计算口径）
5. 劳动报酬与福利待遇审查（含四要素分析+倾向性判断）
6. 派遣协议及劳动合同审查（含管辖条款利益分析）
7. 外包用工穿透审查（条件性输出——仅在有外包/假外包嫌疑时输出，否则注明"不适用"）

**结尾**

8. 综合风险评估与建议
   - **审查结论汇总表（强制输出，置于第8部分最前面，作为执行摘要）**：

   | 审查事项 | 结论 | 风险等级 | 核心问题 | 法条依据 | 紧迫度 | 整改方向 | 计算过程 | 备注 |
   |----------|------|----------|----------|----------|--------|----------|----------|------|
   | 主体资质 | 合规/不合规/待核 | 高风险·存亡/整改/中/低 | 一句话 | 法条编号 | 立即/限期/建议 | 整改措施简述 | — | — |
   | 派遣岗位 | 合规/不合规/待核 | ... | ... | ... | ... | ... | — | — |
   | 派遣比例 | X.X% | ... | ... | ... | ... | ... | 派遣N人÷总量M人 | — |
   | 同工同酬 | 合规/不合规/待核 | ... | ... | ... | ... | ... | — | — |
   | 协议文件 | 合规/不合规/待核 | ... | ... | ... | ... | ... | — | — |
   | …… | … | … | … | … | … | … | … | … |

   - **风险权重分层排序**：按存亡问题→限期整改→可快速修复三层排序，每层不超过4项
   - **风险传导链分析**：揭示风险连锁效应
   - **最坏情况法律后果量化**：叠加所有高风险项的最大法律后果估算
   - **整改方案对比矩阵**：每方案含成本估算/过渡期/法律残留风险三维度 + 最优/次优排序 + "不整改会怎样"对照

**附件**

9. 附件
   - **（一）材料清单**：列出本次审查所依据的全部材料名称及来源
   - **（二）审查方法说明（强制输出）**：
     - **审查方法**：说明本次审查使用的方法（如：文件审阅/人员访谈/联网检索/数据计算/同类比对），逐项标注各审查环节所用方法
     - **信息来源**：列出全部信息来源（如：客户提供材料/公开官网查询/裁判文书网检索/人社部门网站/第三方数据库），标注各来源的使用范围
     - **假设前提声明**：声明本次审查所依赖的假设前提（如："假设客户提供的材料真实、完整、有效""假设未提供材料的环节不存在重大风险""比例计算基于客户提供的用工数据，未经独立核实"），并在假设变化可能影响结论时标注风险提示

### D3 风险等级标注

风险等级使用文字标签（DOCX）或 emoji + 文字标签（Markdown），不得混用。共四级，与 A9 颜色体系、D2 汇总表风险等级列一致：

| 层级 | DOCX | Markdown | 含义 |
|------|------|----------|------|
| 存亡级 | 【高风险·存亡】 | 🔴**高风险·存亡** | 资质归零，立即处理 |
| 限期整改级 | 【高风险·整改】 | 🔴**高风险·整改** | 违法用工，限期整改 |
| 可修复级 | 【中风险】 | 🟡**中风险** | 合同瑕疵，可快速修复 |
| 合规级 | 【低风险】 | 🟢**低风险** | 基本合规，无需整改 |

---

## §§A DOCX 排版规范

> **核心理念**：DOCX 输出对标金杜/方达等顶级律所审查报告排版标准。所有间距通过 paragraph spacing（段前/段后/行距）精确控制，禁止空段落充当间距。表格、颜色、法条引用均按照此规范严格执行。

---

### A0 核心排版原则（最高优先级）

本节为 DOCX 生成的**强制约束**，所有 python-docx 代码必须遵守，违反任一规则即为排版不合格。

**🔴 禁止空段落做间距（规则1）**
- **绝对禁止**在正文段落之间插入空 `<w:p>` 充当间距。
- 段落间距一律通过 `paragraph_format.space_before` / `paragraph_format.space_after` 控制。
- 封面、目录、正文、签章栏——全文任一位置均不得出现内容为空的段落。
- 违例：`doc.add_paragraph("")` 或 `doc.add_paragraph()` 填充空 run。

**🔴 行距使用倍数不写死 DXA（规则2）**
- 正文行距使用 `paragraph_format.line_spacing = 1.5`（1.5 倍行距），不得写死为 DXA 值（如 `Pt(22.5)`）。
- 表格内文字使用 `paragraph_format.line_spacing = 1.0`（单倍行距）。

**🔴 字号使用 Pt() 不硬编码 DXA（规则3）**
- 所有字号通过 `Pt(N)` 设置，由 python-docx 自动转换为 DXA（1pt = 2 DXA）。
- 禁止在代码中直接出现 DXA 数值（如 `w:sz w:val="28"` 之类的硬编码）。

**🔴 封面整体一页，不手动分页（规则4）**
- 封面所有元素放在一个 page 内，通过 `space_before` 控制各元素间距。
- 封面末元素后使用 `doc.add_page_break()` 进入正文。

---

### A1 封面

**主标题：**
- 文字：`"关于[公司名称]劳务派遣用工合规审查之法律审查报告"`
- 字体：方正小标宋简体（`FZXiaoBiaoSong-B05S`）
- 字号：`Pt(22)`（二号 ≈ 22pt）
- 加粗：是
- 对齐：居中
- 段前：`Pt(120)`（封面顶部留白）

**副标题**（可选，如"截至202X年X月X日"）：
- 字体：楷体_GB2312（`KaiTi_GB2312`）
- 字号：`Pt(16)`（三号 ≈ 16pt）
- 对齐：居中
- 段前：`Pt(24)`

**委托方信息/出具日期/密级：**
- 字体：楷体_GB2312
- 字号：`Pt(16)`（三号）或 `Pt(14)`（四号，用于密级）
- 对齐：居中
- 段前：`Pt(12)`，段后：`Pt(6)`
- 密级标注位于封面右上角（通过右对齐 tab stop 定位）

**页面尺寸：**
- A4：`section.page_width = Cm(21.0)`，`section.page_height = Cm(29.7)`
- 上/下边距：`Cm(2.54)`，左/右边距：`Cm(3.17)`
- 内容宽度 = 21.0 − 2×3.17 = 14.66 cm ≈ 8310 DXA

**密级分类标准**（封面右上角标注）：

| 密级 | 适用条件 | 字体 | 字号 | 颜色 |
|------|----------|------|------|------|
| 绝密 | 涉及上市公司未披露重大合规风险/可能引发股价波动 | 方正小标宋简体 | Pt(16) | 红色 `RGBColor(0xCC, 0x00, 0x00)` + 加粗 |
| 机密 | 涉及客户核心商业秘密/重大法律风险/敏感劳动关系 | 黑体 | Pt(16) | 红色 `RGBColor(0xCC, 0x00, 0x00)` |
| 秘密 | 涉及一般商业秘密/内部管理制度 | 黑体 | Pt(16) | 默认黑色 |
| 内部 | 仅限客户内部使用，不得对外披露 | 楷体 | Pt(14) | 默认黑色 |
| 公开 | 无特殊保密要求 | — | — | 不标注 |

默认密级为"内部"。

---

### A2 页面设置

**页眉：**
- 内容：`"[律所名称] | 报告编号：〔YYYY〕XX法审字第XXX号"`
- 字体：宋体，`Pt(9)`（小五号 ≈ 9pt）
- 对齐：居中
- 报告编号格式：`〔2026〕XX法审字第XXX号`（年份+律所简称+法审字+序号）
  > 示例：〔2026〕金杜法审字第012号

**页脚：**
- 内容：页码（`Page X / Total Y` 或仅页码）
- 字体：宋体，`Pt(9)`
- 对齐：居中

**正文区域：**
- 行距：`paragraph_format.line_spacing = 1.5`（1.5倍行距）
- 段前间距：`Pt(6)`（约0.5行，基于小四号字 12pt × 0.5 = 6pt）
- 段后间距：`Pt(6)`
- 首行缩进：`Cm(0.74)`（2字符 ≈ 7.4mm，基于仿宋_GB2312 小四号）
  - 标题、表格内容、注释不缩进

**python-docx 关键代码：**
```python
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

section = doc.sections[0]
section.top_margin = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin = Cm(3.17)
section.right_margin = Cm(3.17)
```

---

### A3 字体字号体系（含字号-DXA-pt 换算表）

**字号换算速查表**（python-docx 使用 `Pt()`，不直接使用 DXA）：

| 中文字号 | pt | DXA | 用途 |
|----------|-----|-----|------|
| 二号 | 22 | 44 | 一级标题（居中） |
| 小二 | 18 | 36 | 一级标题（备选） |
| 三号 | 16 | 32 | 二级标题 |
| 小三 | 15 | 30 | 三级标题 |
| 四号 | 14 | 28 | 四级标题 |
| 小四 | 12 | 24 | 正文 |
| 五号 | 10.5 | 21 | 表格内容 |
| 小五 | 9 | 18 | 注释/脚注/页眉页脚 |

**字体层级体系：**

| 层级 | 字体 | 字号 | 加粗 | 首行缩进 | 对齐 |
|------|------|------|------|----------|------|
| 一级标题（"一、"） | 黑体 `SimHei` | `Pt(22)` | ✅ | 无 | 居中 |
| 二级标题（"（一）"） | 黑体 `SimHei` | `Pt(16)` | ✅ | 无 | 左对齐 |
| 三级标题（"1."） | 黑体 `SimHei` | `Pt(15)` | ✅ | 无 | 左对齐 |
| 四级标题（"（1）"） | 楷体 `KaiTi_GB2312` | `Pt(14)` | ✅ | 无 | 左对齐 |
| 正文 | 仿宋_GB2312 `FangSong_GB2312` | `Pt(12)` | ❌ | `Cm(0.74)` | 两端对齐 |
| 表格内容 | 仿宋_GB2312 | `Pt(10.5)` | ❌ | 无 | 左对齐（表头居中） |
| 注释/脚注 | 仿宋_GB2312 | `Pt(9)` | ❌ | 无 | 左对齐 |
| 法条引用块 | 楷体_GB2312 | `Pt(12)` | ❌ | `Cm(0.74)` | 两端对齐 |

**python-docx 通用字体设置函数：**
```python
def set_run_font(run, font_name='FangSong_GB2312', size=Pt(12), bold=False, color=None):
    """统一设置 run 字体属性"""
    run.font.name = font_name
    run.font.size = size
    run.bold = bold
    if color:
        run.font.color.rgb = color
    # 设置中文字体（重要：西文字体设置后必须设置 east_asian）
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
```

---

### A4 目录

- 自动生成，制表位引导线"……"
- 显示至三级标题
- 页码右对齐
- **目录不使用空行分隔条目**——通过 `space_after=Pt(2)` 微调间距

---

### A5 表格（扩展规范）

**A5.1 表格整体设置（每个表格强制应用）：**

```python
from docx.shared import Pt, Cm, Inches
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# 表格宽度 = A4内容宽度 = 21.0 − 2×3.17 = 14.66 cm ≈ 8310 DXA
TABLE_WIDTH_CM = Cm(14.66)

table.autofit = False  # 🔴 必须关闭自动调整
tbl = table._tbl
tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}></w:tblPr>')
# 固定表格宽度
tblW = parse_xml(f'<w:tblW {nsdecls("w")} w:w="8310" w:type="dxa"/>')
# 移除已有的 tblW
for existing in tblPr.findall(qn('w:tblW')):
    tblPr.remove(existing)
tblPr.append(tblW)
```

**A5.2 表格边框：**
- 外边框：0.5pt 单实线（`w:sz="4"`，0.5pt = 4 八分之一点）
- 内边框：0.5pt 单实线
- **表格内不使用不同的边框粗细**，保持一致

```python
def set_table_borders(table):
    """设置表格统一边框"""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}></w:tblPr>')
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '  <w:top w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '  <w:left w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '  <w:right w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="333333"/>'
        '</w:tblBorders>'
    )
    # 移除已有 borders
    for existing in tblPr.findall(qn('w:tblBorders')):
        tblPr.remove(existing)
    tblPr.append(borders)
```

**A5.3 表头样式：**
- 背景色：浅灰 `RGBColor(0xD9, 0xD9, 0xD9)`（仅表头行，一个颜色）
- 字体：仿宋_GB2312，`Pt(10.5)`，加粗
- 文字对齐：居中（水平+垂直）
- **强制跨页重复表头**：

```python
# 设置表头行跨页重复
header_row = table.rows[0]
tr = header_row._tr
tblPr = tr.find(qn('w:trPr'))
if tblPr is None:
    tblPr = parse_xml(f'<w:trPr {nsdecls("w")}></w:trPr>')
    tr.insert(0, tblPr)
tblHeader = parse_xml(f'<w:tblHeader {nsdecls("w")}/>')
tblPr.append(tblHeader)
```

**A5.4 数据行样式（斑马条）：**
- 奇数行（0-based index 为偶数）：白色背景 `RGBColor(0xFF, 0xFF, 0xFF)`
- 偶数行（0-based index 为奇数）：浅灰背景 `RGBColor(0xF2, 0xF2, 0xF2)`
- 字体：仿宋_GB2312，`Pt(10.5)`，不加粗
- 垂直对齐：居中

```python
def set_cell_shading(cell, color_hex):
    """设置单元格背景色"""
    shading = parse_xml(
        f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color_hex}"/>'
    )
    cell._tc.get_or_add_tcPr().append(shading)
```

**A5.5 单元格内边距：**
- 上下：`Pt(2)`，左右：`Pt(4)`（确保文字不贴边框）
- **每个单元格强制设置**：

```python
def set_cell_margins(cell, top=Pt(2), bottom=Pt(2), left=Pt(4), right=Pt(4)):
    """设置单元格内边距"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{int(top/914400*1440)}" w:type="dxa"/>'
        f'  <w:bottom w:w="{int(bottom/914400*1440)}" w:type="dxa"/>'
        f'  <w:left w:w="{int(left/914400*1440)}" w:type="dxa"/>'
        f'  <w:right w:w="{int(right/914400*1440)}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)
```

简便方法（推荐）：
```python
from docx.oxml.ns import qn
# 为整个表格设置默认 cell margins
table.style.paragraph_format.space_before = Pt(2)
table.style.paragraph_format.space_after = Pt(2)
# 每个单元格的段落
for row in table.rows:
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.paragraph_format.space_after = Pt(2)
```

**A5.6 列宽设置：**
- 所有列使用百分比或固定 DXA 分配，总宽 = 8310 DXA
- **禁止**使用 `w:type="auto"` 或 `w:w="0"`（必须 `w:type="dxa"` + 非零固定值）

```python
def set_col_widths(table, widths_dxa):
    """设置表格列宽
    widths_dxa: [width1, width2, ...]，总和 = 8310
    """
    for row in table.rows:
        for idx, width in enumerate(widths_dxa):
            if idx < len(row.cells):
                row.cells[idx].width = Cm(width / 567)  # 1cm ≈ 567 DXA
```

**九列审查结论汇总表列宽分配**（总和 8310）：
| 列 | 宽度(DXA) | 占比 |
|----|-----------|------|
| 审查事项 | 900 | 10.8% |
| 结论 | 800 | 9.6% |
| 风险等级 | 900 | 10.8% |
| 核心问题 | 1300 | 15.6% |
| 法条依据 | 1100 | 13.2% |
| 紧迫度 | 700 | 8.4% |
| 整改方向 | 1300 | 15.6% |
| 计算过程 | 700 | 8.4% |
| 备注 | 610 | 7.3% |

**A5.7 表格前/后空白：**
- 表格前后各 `Pt(6)` 的段间距（通过表格前后段落的 `space_before`/`space_after` 控制）
- **禁止**在表格前后插入空段落

---

### A6 层级符号

- 一级：一、二、三、…九、
- 二级：（一）（二）（三）
- 三级：1. 2. 3.
- 四级：（1）（2）（3）
- 五级：①②③

---

### A7 签章栏

- 位于报告末尾（第9部分"附件"之后）
- 使用无边框表格，左对齐
- 字体：仿宋_GB2312，`Pt(12)`

**签章栏模板**（2列 × 3行无边框表格）：

| 审查人（签字）：____________ | 复核律师（签字）：____________ |
| 日期：____年____月____日 | 日期：____年____月____日 |
| 律所盖章： | |

```python
# 签章栏生成代码模板
sig_table = doc.add_table(rows=3, cols=2, style='Table Grid')
sig_table.autofit = False
# 移除边框
for row in sig_table.rows:
    for cell in row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            '  <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '</w:tcBorders>'
        )
        tcPr.append(tcBorders)
```

---

### A8 保密声明（DOCX）

签章栏之后，单页独立。格式：

- 标题："保密声明"，黑体，`Pt(16)`，加粗，左对齐，段后 `Pt(12)`
- 正文：仿宋_GB2312，`Pt(12)`，`line_spacing = 1.5`，`Cm(0.74)` 首行缩进
- 内容：
  > 本报告仅供委托方内部使用，未经本所书面同意，不得向第三方披露、复制或分发本报告的全部或部分内容。本报告所载分析基于截至审查基准日的材料和信息，不构成正式法律意见。具体法律决策请咨询执业律师。材料真实性由提供方负责，本所不对材料本身的真实性、准确性和完整性承担核查责任。

---

### A9 风险标注（精简双色体系）

DOCX 中**不使用 emoji**，统一使用文字标签。**颜色仅使用两种**（红色+橙色），删除绿色和深灰色。

| 级别 | 标签 | 字体颜色 | 加粗 | 适用位置 |
|------|------|----------|------|----------|
| 高风险·存亡 | 【高风险·存亡】 | `RGBColor(0xCC, 0x00, 0x00)` 暗红 | ✅ | 表格"风险等级"列、正文风险评估段落、引言摘要 |
| 高风险·整改 | 【高风险·整改】 | `RGBColor(0xCC, 0x00, 0x00)` 暗红 | ✅ | 同上 |
| 中风险 | 【中风险】 | `RGBColor(0xE0, 0x6C, 0x00)` 橙棕 | ❌ | 同上 |
| 低风险 | 【低风险】 | **默认黑色**（不设颜色） | ❌ | 同上 |

**颜色使用约束：**
- 🔴 **红色仅用于"高风险"标签文字**和封面密级（绝密/机密），不得用于正文普通文字。
- 🟠 **橙色仅用于"中风险"标签文字**，不得用于其他文字。
- ⚫ **黑色为默认**：正文、标题、表格普通文字、法条引用等一律使用默认黑色，不得额外设置颜色属性。
- **表格内风险标注**：仅"风险等级"列使用红/橙色标注风险标签，其他列一律黑色。
- **禁止逐单元格着色**：表格斑马条（A5.4）用浅灰，风险标签列用红/橙文字，不得给数据单元格加额外颜色背景。

---

### A10 段落间距硬约束（生成代码强制规则）

**🔴 核心约束表：**

| 段落类型 | space_before | space_after | line_spacing | 首行缩进 | 说明 |
|----------|-------------|-------------|-------------|----------|------|
| 一级标题（"一、"） | `Pt(24)` | `Pt(12)` | 1.5 | 无 | 居中 |
| 二级标题（"（一）"） | `Pt(18)` | `Pt(6)` | 1.5 | 无 | |
| 三级标题（"1."） | `Pt(12)` | `Pt(6)` | 1.5 | 无 | |
| 四级标题（"（1）"） | `Pt(10)` | `Pt(4)` | 1.5 | 无 | |
| 正文 | `Pt(6)` | `Pt(6)` | 1.5 | `Cm(0.74)` | |
| 正文首段（紧跟标题后） | `Pt(0)` | `Pt(6)` | 1.5 | `Cm(0.74)` | 标题后首段不加段前间距 |
| 表格前段落 | `Pt(6)` | `Pt(3)` | 1.5 | — | 表格前留3pt间隙 |
| 表格后段落 | `Pt(3)` | `Pt(6)` | 1.5 | — | 表格后留3pt间隙 |
| 表格内段落 | `Pt(2)` | `Pt(2)` | 1.0 | 无 | 单元格内文字 |
| 法条引用块 | `Pt(8)` | `Pt(8)` | 1.5 | `Cm(0.74)` | 左右各缩进 `Cm(0.5)` |
| 签章栏段落 | `Pt(6)` | `Pt(6)` | 1.5 | 无 | |
| 页眉/页脚 | `Pt(0)` | `Pt(0)` | 1.0 | 无 | |

**🔴 交互规则：**
- **标题后紧跟的正文首段**：`space_before = Pt(0)`（因为标题已有 `space_after`）
- **两个连续正文段落**：各 `space_before=Pt(6)`, `space_after=Pt(6)`
- **正文后紧跟二级/三级标题**：正文 `space_after=Pt(6)` + 标题 `space_before=Pt(18)`，间距自然形成，**不插入空段落**

**通用代码模板：**
```python
def add_paragraph_with_spacing(doc, text, font_name='FangSong_GB2312', size=Pt(12),
                                bold=False, space_before=Pt(6), space_after=Pt(6),
                                line_spacing=1.5, first_line_indent=Cm(0.74),
                                alignment=WD_ALIGN_PARAGRAPH.JUSTIFY):
    """添加带完整格式的段落，禁止空段落"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = space_before
    p.paragraph_format.space_after = space_after
    p.paragraph_format.line_spacing = line_spacing
    if first_line_indent:
        p.paragraph_format.first_line_indent = first_line_indent
    p.alignment = alignment
    run = p.add_run(text)
    set_run_font(run, font_name, size, bold)
    return p
```

---

### A11 法条引用块（独立样式）

法条引用应使用独立段落样式，与正文明显区分，提升可读性。

**样式规范：**
- 字体：楷体_GB2312，`Pt(12)`
- 行距：1.5 倍
- 首行缩进：`Cm(0.74)`
- 左缩进：`Cm(0.5)`，右缩进：`Cm(0.5)`
- 段前：`Pt(8)`，段后：`Pt(8)`
- 左侧竖线点缀（可选，通过段落底纹模拟 2pt 灰色左边线）：
   - 若实现困难，可省略，仅凭楷体+左右缩进区分即可。

**法条引用格式模板：**

> **《中华人民共和国劳动合同法》第六十六条**
> 劳动合同用工是我国的企业基本用工形式。劳务派遣用工是补充形式，只能在临时性、辅助性或者替代性的工作岗位上实施。

**法条引用规则：**
1. 法条名称使用全称（如《中华人民共和国劳动合同法》），不得使用简称（如《劳动合同法》），除非同一法条在同段落已出现全称后可使用简称。
2. 法条编号使用中文数字（如"第六十六条"），不使用阿拉伯数字。
3. 法条正文使用楷体，与原文措辞一致。
4. **不得在正文段落中内联法条引用**——法条引用必须为独立段落块，不与正文混排。

```python
def add_legal_citation(doc, law_name, article_num, article_text):
    """添加法条引用块"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Cm(0.74)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.5)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # 法条标题（加粗）
    title_run = p.add_run(f'{law_name}第{article_num}条')
    set_run_font(title_run, 'KaiTi_GB2312', Pt(12), bold=True)

    # 换行
    p.add_run('\n')

    # 法条正文
    text_run = p.add_run(article_text)
    set_run_font(text_run, 'KaiTi_GB2312', Pt(12), bold=False)
    return p
```

---

### A12 python-docx 代码约束（全局规则）

**A12.1 导入与依赖：**
```python
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
```

**A12.2 全局样式设置（在创建 Document 后立即执行）：**
```python
doc = Document()

# 设置默认字体
style = doc.styles['Normal']
style.font.name = 'FangSong_GB2312'
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), 'FangSong_GB2312')
style.paragraph_format.line_spacing = 1.5
style.paragraph_format.space_before = Pt(6)
style.paragraph_format.space_after = Pt(6)
```

**A12.3 禁止事项：**
- ❌ 禁止 `doc.add_paragraph()` 不带参数（会产生空段落）
- ❌ 禁止 `doc.add_paragraph("")`（空文本段落充当间距）
- ❌ 禁止直接设置 `w:sz` 等 DXA 值（使用 `Pt()` 代替）
- ❌ 禁止 `table.style = 'Table Grid'` 后不改边框（应使用自定义边框函数）
- ❌ 禁止使用绿色 `RGBColor(0x00, 0x80, 0x00)` 标注任何文字
- ❌ 禁止使用深灰 `RGBColor(0x33, 0x33, 0x33)` 标注任何文字
- ❌ 禁止逐单元格单独设置背景色（仅表头行全体浅灰 + 斑马条）

**A12.4 分页控制：**
- 每个一级标题（"二、"至"九、"）前使用 `doc.add_page_break()` 之外的轻微方式分页——通过标题 `space_before` 自然区分。
- 确实需要强制分页的场景：封面→目录、目录→正文、正文→保密声明。
- 分页方法：`run.add_break(docx.enum.text.WD_BREAK.PAGE)` 或 `doc.add_page_break()`。

---

### A13 排版自检清单（Phase 7 生成后强制执行）

生成 DOCX 后，LLM 必须**逐项自检**以下 12 项。任一未通过则视为排版不合格，需要修正代码后重新生成。

| # | 检查项 | 通过标准 | 检查方法 |
|---|--------|----------|----------|
| 1 | 无空段落 | 全文无内容为空的 `<w:p>` 元素 | 搜索 `doc.add_paragraph()` 无参数调用 |
| 2 | 段落间距正确 | 正文 `space_before=Pt(6)`, `space_after=Pt(6)` | 检查 `paragraph_format.space_before/after` |
| 3 | 表格宽度固定 | 每个表格 `tblW w:type="dxa"` `w:w="8310"` | 检查 XML `w:tblW` 属性 |
| 4 | 表格跨页表头 | 每个表格首行有 `<w:tblHeader/>` | 检查 XML `w:tblHeader` 元素 |
| 5 | 表格斑马条 | 奇数行白色, 偶数行 `#F2F2F2` | 检查 `set_cell_shading` 调用 |
| 6 | 颜色仅红+橙 | 全文 color 引用仅限 `0xCC0000` 和 `0xE06C00` | 搜索 `RGBColor` 调用，不应出现绿色/深灰 |
| 7 | 风险标签正确 | 高风险用红色+加粗, 中风险用橙色, 低风险用黑色 | 检查 `set_run_font` 的 color 参数 |
| 8 | 法条引用独立块 | 法条在独立段落中，楷体+左右缩进 | 检查 `add_legal_citation` 调用 |
| 9 | 字号正确 | 正文 `Pt(12)`, 标题 `Pt(22/16/15/14)`, 表格 `Pt(10.5)` | 检查 `set_run_font` 的 size 参数 |
| 10 | 行距正确 | 正文 `line_spacing=1.5`, 表格内 `line_spacing=1.0` | 检查 `paragraph_format.line_spacing` |
| 11 | 首行缩进正确 | 正文 `Cm(0.74)`, 标题/表格内容无缩进 | 检查 `paragraph_format.first_line_indent` |
| 12 | 封面元素完整 | 主标题/副标题/委托方/日期/密级 均有 | 检查封面段落数量 ≥ 4 |

**检查不通过时的处理：**
1. 定位违反的规则编号
2. 修正对应 python-docx 代码段
3. 重新生成 DOCX
4. 再次执行全部 12 项自检

---

## §§B Markdown 排版规范

### B1 标题层级

- `#` 报告标题
- `##` 九大部分
- `###` 各部分内章节
- `####` 细分项

### B2 表格

- 使用标准 Markdown 表格
- 风险标注列使用 emoji：🔴高风险 / 🟡中风险 / 🟢低风险

### B3 风险标注

- 行内标注：🔴高风险·存亡 / 🔴高风险·整改 / 🟡中风险 / 🟢低风险
- 综合风险等级使用醒目块：

```markdown
> **综合风险等级：🔴高风险**
> - 🔴高风险·存亡：1项（许可证到期——立即处理）
> - 🔴高风险·整改：2项（三性不成立/比例超标——限期1-3个月整改）
> - 🟡中风险：3项（协议条款缺失/管辖约定不利/同工同酬待核——可快速修复）
```

- 风险传导链使用引用块 + 箭头链：

```markdown
> **风险传导链**
> 许可证到期 → 派遣协议失去合法基础 → N名派遣工劳动关系归属争议 → 事实劳动关系认定 → 追溯性社保补缴 + 经济补偿金 + 第92条连带赔偿责任
```

- 整改方案对比使用标准表格（含成本/过渡期/风险三维度）

### B4 列表

- 审查项使用有序列表
- 整改建议使用无序列表
- 法条引用使用引用块 `>`

### B5 法条引用块

```markdown
> **《中华人民共和国劳动合同法》第六十六条**
> 劳动合同用工是我国的企业基本用工形式。劳务派遣用工是补充形式，只能在临时性、辅助性或者替代性的工作岗位上实施。
```

### B6 无封面/签章栏/页码

Markdown 输出不含封面、签章栏、页码。报告首部为标题 + 引言。

### B7 保密声明（Markdown）

报告末尾必须附标准化保密声明，使用引用块格式：

```markdown
> **保密声明**
>
> 本报告仅供委托方内部使用，未经授权不得向第三方披露、复制或分发。
> 本报告所载分析基于截至审查基准日的材料和信息，不构成正式法律意见。具体法律决策请咨询执业律师。
> 材料真实性由提供方负责。
```

---

## §§C SOFT_DEGRADED 降级定义

### 🔴 触发前置条件

SOFT_DEGRADED 仅在 IG-1 交互门控追问已完成（即用户已明确回复"跳过"或超时未回复）后触发。**禁止未经 IG-1 追问直接进入 SOFT_DEGRADED 模式**——管线必须先与用户完成至少一次交互（确认材料齐备或追问缺口），仅在用户明确选择跳过后方可降级。

### 降级级别

| 级别 | 代号 | 触发条件 | 降级行为 |
|------|------|----------|----------|
| C-材料不足 | C | IG-1追问后用户跳过，且第一层必备材料缺失 ≥2 项 | 缺失层标记"待补充"，仅审查有材料支持的层，报告首部标注降级 |
| D-核验受限 | D | 法条无法联网检索/核验 | 法条结论标注"待核查"，建议律师复核，不得凭记忆引用 |
| G-工具不可用 | G | [skill:docx] 不可用 | 回退 Markdown 输出，提示后续可补生成 DOCX |

### 降级组合

- C+D：材料不足+核验受限——局部审查+待核查标注
- C+D+G：全降级——Markdown局部审查报告+待核查+提示补生成
- 最小骨架（C+D+G）：至少输出引言+有材料的层的结论+缺口清单+免责声明

### 降级报告标注格式

报告首部必须包含：

```markdown
> **⚠️ 降级说明**
> 本报告因以下原因降级执行：
> - [C-材料不足] 缺失：xxx、xxx
> - [D-核验受限] 无法核验法条：xxx
> - [G-工具不可用] DOCX生成不可用，已回退Markdown
> 降级部分结论仅供参考，建议补充材料后重新审查。
```

### 降级后补全

用户补充材料后，可重新执行对应 Phase 更新结论，无需重跑全部管线。
