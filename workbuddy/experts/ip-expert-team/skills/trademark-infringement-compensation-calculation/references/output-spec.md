# 输出格式与写作红线 — tm-damage-calc

> **所属技能**：tm-damage-calc | **文件角色**：输出规格 | **版本**：v1.3.0
>
> **Emoji 禁令（强制）**：输出报告中**禁止使用任何 emoji**。法条标注仅使用 `[已核实]` / `[需核实]` / `[存疑]`，不得写成 `[✅已核实]` / `[📋需核实]` / `[⚠️存疑]`。所有段落标题、列表项、表格中均不得出现 emoji。

---

## 一、三输出架构

| 输出 | 说明 | 渲染条件 | 格式严肃度 | 输出格式 |
|------|------|---------|-----------|---------|
| **测算报告** | 四路径递进测算+惩罚性评估+合理开支+推荐方案 | 始终输出 | I-Practical | Markdown + docx |
| **撰写指引** | 证据补充建议+举证策略+律师注意事项 | L1/L2 时输出 | I-Practical | Markdown |
| **证据清单** | 缺失证据+补充建议+举证妨碍提示 | 有缺失计算基础时输出 | I-Practical | Markdown |

---

## 二、测算报告输出结构模板

```markdown
# 商标侵权赔偿测算报告

## 案件概况

### 案件背景（有则体现，无则省略本节）
<!-- 以下字段仅当用户提供时才输出，不提供则整节省略，不使用"[待补充]"占位 -->
- 权利人：[plaintiff_name]
- 注册商标：[trademark_name]（注册号：[trademark_reg_no]，第[trademark_class]类）
- 注册日期：[trademark_reg_date]，续展截止：[trademark_renewal_deadline]
- 商标知名度：[trademark_fame]
- 侵权人：[defendant_name]

### 侵权概况
- 侵权持续时间：[期间]（共[X]个月）
- 侵权范围：[描述]

### 计算基础概况
- 可用计算基础：[路径1/2/3/4]
- 数据时间口径说明：[如：年销售额为年度数据已折算为实际期间 / 数据已为实际期间数据]

## 四路径递进测算

### 路径1：权利人实际损失（优先级1）
- 计算基础：[损失金额]元（[实际期间]，如为年度折算则注明折算过程）
- 计算依据：[描述]（商标法第六十三条第一款[已核实]）

#### 年度损失测算明细表
| 项目 | 原始计算 | 扣除因素 | 扣除金额 | 保守取值 |
|------|---------|---------|---------|---------|
| 销量减少损失 | [金额]元 | [因素说明+扣除比例] | [金额]元 | [金额]元 |
| 价格侵蚀损失 | [金额]元 | [因素说明+扣除比例] | [金额]元 | [金额]元 |
| 其他损失（如商誉） | [金额]元 | [因素说明] | [金额]元 | [金额]元 |
| **合计** | **[金额]元** | | **[金额]元** | **[保守合计]元** |

- 测算结果：保守取值约[金额区间]元（[实际计算期间标注]）
  - 原始计算：[金额区间]元（供参考，含不确定性因素）
  - 保守取值：[金额区间]元（已扣除[具体因素]，建议以此为准）
- 证据充分性：[高/中/低]

### 路径2：侵权人获利（优先级2）
- 计算基础：[获利金额]元（[实际期间]，如为年度折算则注明折算过程）
- 计算依据：[描述]（商标法第六十三条第一款[已核实]）
- 测算结果：[金额区间]元（[实际计算期间标注]）
- 证据充分性：[高/中/低]

### 路径3：商标许可使用费倍数（优先级3）
- 许可费基础：[金额]元/年（年度）→ 折算为 [金额]元（[实际期间]）
- 建议倍数：[X]倍
- 测算结果：[金额区间]元（[实际计算期间标注]）
- 证据充分性：[高/中/低]

### 路径4：法定赔偿（优先级4，兜底）
- 建议金额：[金额区间]元（500万元以下）
- 适用理由：[描述]（商标法第六十三条第三款[已核实]）

## 惩罚性赔偿评估
- 恶意认定：[是/否/临界]，[证据/理由]
- 情节严重认定：[是/否]，[证据/理由]
- 基数选择：[路径X]的[原始计算/保守取值]结果
- 基数选择理由：
  1. [证据充分性对比：各路径证据充分性排序及选择依据]
  2. [路径优先级考量：所选路径的优先级优势]
  3. [排除其他路径的原因：为何不选路径Y和路径Z]
- 如适用：基数[X]元（取自路径[Y]） × [1-5]倍 = [金额区间]元

## 合理开支
| 项目 | 金额(元) | 凭证 |
|------|---------|------|
| 律师费 | [金额] | [有/待补充] |
| 公证费 | [金额] | [有/待补充] |
| 调查费 | [金额] | [有/待补充] |
| 购买侵权产品费 | [金额] | [有/待补充] |
| 差旅费 | [金额] | [有/待补充] |
| 其他 | [金额] | [有/待补充] |
| **合计** | **[金额]** | |

## 推荐方案
- 推荐计算路径：路径[X]
- 推荐赔偿总额：[金额区间]元（含惩罚性赔偿[金额]+合理开支[金额]）
- 理由：[证据最充分/法院采纳可能性最高]

## 程序性事项提示
- **诉讼时效**：商标侵权诉讼时效为三年，自权利人知道或应当知道权利受损及义务人之日起计算（《民法典》第一百八十八条[已核实]）。侵权行为持续的，各阶段侵权可能独立计算时效。如侵权发生至今已超过三年，须提醒律师核查是否存在时效中断/中止事由。
- **管辖权**：商标侵权案件通常由侵权行为地或被告住所地中级人民法院管辖（《民事诉讼法》第二十九条[已核实]；《最高人民法院关于审理商标案件有关管辖和法律适用范围问题的解释》[已核实]）。涉及驰名商标认定的案件管轄级别另有规定。建议提示律师确认管辖法院的级别和地域是否适当。
- **举证责任**：权利人须就侵权事实、损失数额、合理开支等承担举证责任；侵权人须就获利数额、合法来源等承担举证责任。建议提示律师准备相应证据材料。
- **诉前保全**：如有证据证明侵权人可能转移财产或销毁证据，可申请诉前财产保全和/或证据保全（《民事诉讼法》第一百零三条、第一百零四条[已核实]）。建议提示律师评估保全必要性。

> **注意**：程序性事项提示为诉讼准备辅助信息，不构成程序性法律意见。具体时效计算、管辖确定须由律师根据案件具体情况判断。

## 免责声明
本测算为参考性分析，不构成法律意见。赔偿金额须由律师审核，最终以法院裁定为准。
```

---

## 三、写作红线（WR-01~11）

> 本技能遵守 `base/shared/writing-redlines.md` 全部 11 条通用红线。

| # | 红线 | 说明 | 本技能具体应用 | 违反后果 |
|---|------|------|--------------|---------|
| WR-01 | **不使用绝对化表述** | 禁止"必然""一定""保证""肯定" | 不得出现"一定能拿到""保证判赔" | 误导当事人 |
| WR-02 | **结论留边界** | 加限定语 | "建议""供参考""最终以法院裁定为准" | 无限定结论构成不当保证 |
| WR-03 | **事实与意见分离** | 事实不加主观评价 | 计算过程客观描述，意见用"我们认为" | 混淆导致计算不可信 |
| WR-04 | **不替代律师判断** | "建议""供参考" | "建议优先采用路径X""供律师选择" | 替代判断违反律师法 |
| WR-05 | **法条引用须标注来源** | 全称+条号+三标注 | 《中华人民共和国商标法》第六十三条第一款[已核实] | 引用错误损害可信度 |
| WR-06 | **金额须标注计算依据** | 注明计算公式或法律依据 | "实际损失=因侵权减少的销量×单位利润（第63条第1款）" | 无依据数字构成虚假陈述 |
| WR-07 | **不编造法条或判例** | 不确定时标注[需核实] | 不确定时标注"[需核实]" | 编造是最严重的专业事故 |
| WR-08 | **不提供胜诉保证** | 禁止"必胜""一定会拿到" | 不得出现"本案一定能拿到50万" | 违反律师执业规范 |
| WR-09 | **保守测算优于激进** | 选保守者 | 金额区间取保守端 | 激进表述易被反噬 |
| WR-10 | **避免不利自认** | 不主动承认不利事实 | 不得出现"我方确实无法证明损失" | 不利自认损害当事人利益 |
| WR-11 | **文书风格统一，禁止混搭** | 选定一种风格贯彻到底 | 选定**结构化测算报告风格** | 混搭导致报告"四不像" |
| WR-12 | **禁止 emoji** | 报告中不得出现任何 emoji | 法条标注用[已核实]/[需核实]/[存疑]，禁止用[✅已核实]/[📋需核实]/[⚠️存疑]；任何标题/段落/表格禁止 emoji | 降低报告专业性 |

**偏离项**：[无偏离]

---

## 四、TypeSpec 独立配置

### calculation_path（计算路径声明）

```
四路径优先级递进：
路径1（优先级1）：权利人实际损失 → 第63条第1款
路径2（优先级2）：侵权人获利 → 第63条第1款
路径3（优先级3）：许可使用费倍数 → 第63条第1款
路径4（优先级4）：法定赔偿 → 第63条第3款（500万元以下）
```

### punitive_conditions（惩罚性赔偿条件声明）

```
惩罚性赔偿适用条件（须同时满足）：
条件1：恶意侵权
条件2：情节严重
赔偿金额 = 基数 × 1-5倍
基数取自路径1/2/3（不含合理开支）
```

### required_fields（计算核心要素）

| 字段 | 用途 |
|------|------|
| `infringement_duration` | 侵权持续时间，影响所有路径计算 |
| `infringement_scope` | 侵权范围，影响法定赔偿评估 |
| 至少一项计算基础 | 四路径递进测算的数据基础 |

### type_specific_fields

**惩罚性赔偿专用字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_malicious` | boolean | 是否恶意侵权 |
| `malicious_evidence` | string | 恶意证据描述 |
| `is_serious` | boolean | 是否情节严重 |
| `serious_evidence` | string | 情节严重证据描述 |
| `punitive_multiple` | number | 建议惩罚倍数（1-5） |

**合理开支专用字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `lawyer_fee` | number | 律师费（元） |
| `notary_fee` | number | 公证费（元） |
| `investigation_fee` | number | 调查费（元） |
| `purchase_fee` | number | 购买侵权产品费（元） |
| `travel_fee` | number | 差旅费（元） |
| `other_fee` | number | 其他费用（元） |

---

## 五、格式规范

### 案件背景条件渲染规则

| 用户是否提供 | 行为 | 示例 |
|------------|------|------|
| 提供了权利人+商标+侵权人信息 | 输出完整的"案件背景"小节 | 见 example-001 |
| 仅提供部分信息（如仅有商标名称） | 仅输出已有字段，不编造缺失字段 | "注册商标：云智" |
| 完全未提供背景信息 | **整节省略**，不输出"案件背景"标题 | 见 example-002 |

> **禁止行为**：无信息时不得编造权利人名称/商标信息；不得标注"[待补充权利人信息]"占位。

### I-Practical 排版要求

| 项目 | 规范 |
|------|------|
| 金额表达 | 金额区间，非确定值 |
| 表格使用 | 合理开支部分允许表格 |
| 法条融入正文 | 法条引用融入计算说明 |
| 数值格式 | 金额标注"元"，千位以上使用逗号分隔 |
| 免责声明 | 每次输出必须附带三要素免责 |
| 表情符号 | 禁止使用任何 emoji（包括 ✅❌⚠️🔴📋 等），法条标注仅用纯文本 |
| docx 输出 | 测算报告支持 docx 格式输出，规范详见 §六 |

---

## 六、docx 输出格式规范

> **适用范围**：测算报告支持 docx 格式输出（可选）。撰写指引和证据清单仅 Markdown 输出。
>
> **规范来源**：严格依照《Richee 文档设计规范 v1.2》（docx-format-spec 技能 `references/design-spec.md`）。
>
> **技术栈**：python-docx（`pip install python-docx`）。禁止使用 docx-js。

### 6.1 页面设置

| 属性 | 值 |
|------|-----|
| 纸张大小 | A4（21.0 × 29.7 cm）纵向 |
| 上边距 | 2.54 cm |
| 下边距 | 2.54 cm |
| 左边距 | 3.18 cm |
| 右边距 | 3.18 cm |
| 页眉距边界 | 1.50 cm |
| 页脚距边界 | 1.75 cm |

**python-docx 代码示例**：

```python
from docx.shared import Cm

s = doc.sections[0]
s.page_width = Cm(21.0)
s.page_height = Cm(29.7)
s.top_margin = Cm(2.54)
s.bottom_margin = Cm(2.54)
s.left_margin = Cm(3.18)
s.right_margin = Cm(3.18)
s.header_distance = Cm(1.50)
s.footer_distance = Cm(1.75)
```

### 6.2 文本层级

> **全局字体**：宋体 | **全局颜色**：#0A0D12 | **全局行距**：1.5 倍（表头除外）

#### 6.2.1 文档标题

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 小二（18 pt） |
| 字重 | 加粗 |
| 颜色 | #0A0D12 |
| 对齐 | 居中 |
| 行距 | 1.5 倍 |
| 段前 | 36 pt |
| 段后 | 27 pt |
| 首行缩进 | 无 |

> **适用**：报告主标题（如"商标侵权赔偿测算报告"），对应 Word 样式 Title。

#### 6.2.2 章节标题（Heading 1 / Heading 2）

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 四号（14 pt） |
| 字重 | 加粗 |
| 颜色 | #0A0D12 |
| 对齐 | 两端对齐 |
| 行距 | 1.5 倍 |
| 段前 | 12 pt |
| 段后 | 6 pt |
| 首行缩进 | 无 |

> **适用**：Markdown 中的 `#` 和 `##` 标题，对应 Word 样式 Heading 1 / Heading 2。

#### 6.2.3 正文段落

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 12 pt |
| 字重 | 常规 |
| 颜色 | #0A0D12 |
| 对齐 | 左对齐 |
| 行距 | 1.5 倍 |
| 段前 | 0 pt |
| 段后 | 6 pt |
| 首行缩进 | 0.74 cm |

> **适用**：报告正文段落，对应 Word 样式 Normal / First Paragraph。

#### 6.2.4 项目符号列表

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 12 pt |
| 字重 | 常规 |
| 颜色 | #0A0D12 |
| 对齐 | 左对齐 |
| 行距 | 1.5 倍 |
| 段前 | 0 pt |
| 段后 | 6 pt |
| 首行缩进 | 无 |
| 左缩进 | 1.0 cm |

> **适用**：Markdown 中的 `-` 列表项，对应 Word 样式 Compact。

#### 6.2.5 表格标题

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 12 pt |
| 字重 | 加粗 |
| 颜色 | #0A0D12 |
| 对齐 | 左对齐 |
| 行距 | 1.5 倍 |
| 段前 | 12 pt |
| 段后 | 6 pt |

> **适用**：表格上方的标题行（如"【表1】合理开支明细"），紧跟章节标题后的表格前插入。

#### 6.2.6 免责声明

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 |
| 字号 | 10 pt |
| 字重 | 常规 |
| 样式 | 斜体 |
| 颜色 | #6B7280（灰色） |
| 对齐 | 左对齐 |
| 行距 | 1.5 倍 |
| 段后 | 6 pt |
| 首行缩进 | 0.74 cm |

> **适用**：报告末尾免责声明段落（"本测算为参考性分析，不构成法律意见..."），对应 Word 样式 Disclaimer。

### 6.3 表格规范

| 属性 | 值 |
|------|-----|
| 整体对齐 | 居中 |
| 边框 | 0.5 pt 单实线，色号 #C9CED6，全边框 + 内框 |
| 单元格水平对齐 | 居中 |
| 单元格垂直对齐 | 居中 |

**表头行**：

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 12 pt 加粗 |
| 行距 | 1.0 倍 |
| 段前 | 6 pt |
| 段后 | 6 pt |
| 底纹 | #ECFDF3（浅绿） |

**数据行**：

| 属性 | 值 |
|------|-----|
| 字体 | 宋体 12 pt 常规 |
| 行距 | 1.5 倍 |
| 底纹 | #FFFFFF（白） |

**python-docx 代码示例**（合理开支表格式化）：

```python
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# 表格整体居中
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# 全边框 + 内框：0.5pt 单实线 #C9CED6
border_xml = (
    f'<w:tblBorders {nsdecls("w")}>'
    f'<w:top w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'<w:left w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'<w:right w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="C9CED6"/>'
    f'</w:tblBorders>'
)
table._tbl.tblPr.append(parse_xml(border_xml))

# 逐行格式化
for ri, row in enumerate(table.rows):
    is_header = (ri == 0)
    for cell in row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        # 垂直居中
        tcPr.append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="center"/>'))
        # 底纹：表头 #ECFDF3，数据行 #FFFFFF
        fill = "ECFDF3" if is_header else "FFFFFF"
        tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill}" w:val="clear"/>'))
        # 单元格段落格式
        for para in cell.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 水平居中
            pf = para.paragraph_format
            if is_header:
                pf.line_spacing = 1.0   # 表头单倍行距
                pf.space_before = Pt(6)
                pf.space_after = Pt(6)
            else:
                pf.line_spacing = 1.5   # 数据行 1.5 倍行距
            for run in para.runs:
                run.font.name = "宋体"
                run.font.size = Pt(12)
                run.bold = is_header
                run.font.color.rgb = RGBColor(0x0A, 0x0D, 0x12)
```

### 6.4 页眉页脚

**页眉**：

| 属性 | 值 |
|------|-----|
| 文字 | 「Richee 生成」 |
| 字体 | 微软雅黑 |
| 字号 | 小五（9 pt） |
| 颜色 | #0A0D12 |
| 对齐 | 右对齐 |
| 底边下划线 | 0.5 pt 单实线，色号 #C9CED6 |

**页脚**：

| 属性 | 值 |
|------|-----|
| 内容 | 居中页码（1, 2, 3...） |
| 字体 | 宋体 |
| 字号 | 11 pt |
| 颜色 | #0A0D12 |

**python-docx 代码示例**：

```python
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# ── 页眉 ──
header = doc.sections[0].header
header.is_linked_to_previous = False
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hr = hp.add_run("Richee 生成")
hr.font.name = "微软雅黑"
hr.font.size = Pt(9)
hr.font.color.rgb = RGBColor(0x0A, 0x0D, 0x12)
# 东亚字体设置
rpr = hr._r.get_or_add_rPr()
rpr.append(parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="微软雅黑"/>'))
# 底边下划线
pPr = hp._p.get_or_add_pPr()
pPr.append(parse_xml(
    f'<w:pBdr {nsdecls("w")}>'
    f'<w:bottom w:val="single" w:sz="4" w:space="1" w:color="C9CED6"/>'
    f'</w:pBdr>'
))

# ── 页脚（居中页码） ──
footer = doc.sections[0].footer
footer.is_linked_to_previous = False
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = fp.add_run()
fr.font.name = "宋体"
fr.font.size = Pt(11)
fr.font.color.rgb = RGBColor(0x0A, 0x0D, 0x12)
# PAGE 域代码
fr._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'))
fr._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>'))
fr._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))
```

### 6.5 样式映射表

> 测算报告 Markdown 元素须按以下映射转换为 Word 样式。

| Markdown 元素 | Word 样式 | 文本层级 | 说明 |
|---------------|----------|---------|------|
| 报告主标题（`# 商标侵权赔偿测算报告`） | Title | 文档标题 | 18pt 加粗居中 |
| `## 章节标题` | Heading 1 | 章节标题 | 14pt 加粗两端对齐 |
| `### 子节标题` | Heading 2 | 章节标题 | 14pt 加粗两端对齐 |
| 普通正文段落 | Normal / First Paragraph | 正文段落 | 12pt 首行缩进 0.74cm |
| `- 列表项` | Compact | 项目符号列表 | 12pt 左缩进 1.0cm |
| 表格上方标题 | （手动格式化） | 表格标题 | 12pt 加粗 |
| 免责声明段落 | Disclaimer | 免责声明 | 10pt 斜体灰色 |
| `\| 表格 \|` | Table | 表格 | 居中，全边框，表头底纹 |

> **未知样式处理**：遇到未映射的样式时，默认按正文段落处理。

### 6.6 东亚字体设置（强制）

> python-docx 设置中文字体须同时设置 `font.name` 和 `w:eastAsia` 属性，否则中文字符可能回退到默认字体。

```python
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

def set_east_asian_font(run, font_name):
    """设置 run 的东亚字体"""
    rpr = run._r.get_or_add_rPr()
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="{font_name}"/>')
        rpr.append(rFonts)
    else:
        rFonts.set(qn("w:eastAsia"), font_name)

# 使用示例
run.font.name = "宋体"                # 设置西文字体
set_east_asian_font(run, "宋体")       # 设置东亚字体（必须）
```

### 6.7 默认样式与颜色常量

**默认样式（Normal）**：

```python
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

sty = doc.styles["Normal"]
sty.font.name = "宋体"
sty.font.size = Pt(12)
sty.font.color.rgb = RGBColor(0x0A, 0x0D, 0x12)
sty.paragraph_format.line_spacing = 1.5
sty.paragraph_format.space_after = Pt(6)
# 设置东亚字体
rpr = sty.element.get_or_add_rPr()
rpr.append(parse_xml(f'<w:rFonts {nsdecls("w")} w:eastAsia="宋体"/>'))
```

**颜色常量速查**：

| 常量名 | 色值 | 用途 |
|--------|------|------|
| CLR_TEXT | #0A0D12 | 正文/标题/页眉/页脚 |
| CLR_DISC | #6B7280 | 免责声明（灰色） |
| CLR_BORDER | #C9CED6 | 表格边框/页眉下划线 |
| CLR_TH_BG | #ECFDF3 | 表头底纹（浅绿） |
| CLR_TD_BG | #FFFFFF | 数据行底纹（白） |

### 6.8 生成与验证

**方式一：直接运行格式化脚本**（推荐）：

```bash
python3 scripts/format_docx.py 输入.docx [输出.docx]
```

脚本自动按设计规范排版，省略输出路径则生成 `原名_格式版.docx`。

**方式二：python-docx API 编程生成**：

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor

doc = Document()
# 按 §6.1~§6.7 规范设置页面、文本层级、表格、页眉页脚
doc.save("测算报告.docx")
```

**依赖**：`pip install python-docx`
