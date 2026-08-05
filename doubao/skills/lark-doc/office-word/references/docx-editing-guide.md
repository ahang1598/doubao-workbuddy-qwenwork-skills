# DOCX 编辑指南 — 编辑已有文档

本指南说明如何通过操作 XML 来编辑 .docx 文件，在修改内容的同时完美保持原始格式。

## 目录

1. [工作流：解包 → 编辑 → 回包](#工作流)
2. [编辑原则](#编辑原则)
3. [XML 结构参考](#xml-结构参考)
4. [图片处理](#图片处理)

---

## 工作流

**按顺序执行以下 3 步。**

### 第 1 步：解包

```bash
uv run skills/lark-doc/office-word/scripts/docx_edit.py unpack document.docx unpacked/
```

解压 XML、格式化、合并相邻文本节点、转换智能引号为 XML 实体。需要先看纯文本结构时，用 `uv run skills/lark-doc/office-word/scripts/extract_docx.py document.docx`。

### 第 2 步：编辑 XML

编辑 `unpacked/word/` 下的文件，主要内容在 `document.xml`。

**直接用编辑工具做字符串替换，不要写 Python 脚本。** 编辑工具能精确展示替换内容。

**添加含引号/撇号的文本时使用 XML 实体：**
```xml
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```
| 实体 | 字符 |
|------|------|
| `&#x2018;` | ' (左单引号) |
| `&#x2019;` | ' (右单引号/撇号) |
| `&#x201C;` | " (左双引号) |
| `&#x201D;` | " (右双引号) |

### 第 3 步：回包

```bash
uv run skills/lark-doc/office-word/scripts/docx_edit.py pack unpacked/ output.docx
```

自动修复空格、压缩 XML、生成 DOCX。

---

## 编辑原则

### 替换已有字段的文本

保持格式的关键：只修改 `<w:t>` 元素中的文本，不碰 `<w:rPr>`（格式属性）。

```xml
<!-- 修改前 -->
<w:r>
  <w:rPr>
    <w:b/>
    <w:sz w:val="24"/>
  </w:rPr>
  <w:t>placeholder text</w:t>
</w:r>

<!-- 修改后 — 只有文本变了，格式完全保留 -->
<w:r>
  <w:rPr>
    <w:b/>
    <w:sz w:val="24"/>
  </w:rPr>
  <w:t>Zhang San</w:t>
</w:r>
```

### 填写空白字段

模板可能用下划线、空格或空 `<w:t>` 作占位符。替换占位内容，保持外层 XML 结构不变：

```xml
<!-- 模板中的下划线占位符 -->
<w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>____________</w:t></w:r>

<!-- 填入内容 -->
<w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>1990-01-15</w:t></w:r>
```

### 复选框字段

签证表格常用复选框：
```xml
<w:r><w:t>☐</w:t></w:r>  <!-- 未选中 -->
<w:r><w:t>☑</w:t></w:r>  <!-- 已选中 -->
```

替换字符即可切换选中状态。有些模板用 Wingdings 字体符号，原理相同。

### 空格规则

- 文本有前导/尾随空格时，给 `<w:t>` 加 `xml:space="preserve"`
- 不要用 `\n` — 新行用单独的 `<w:p>` 元素
- 不要把文本直接放在 `<w:p>` 里 — 始终用 `<w:r><w:t>...</w:t></w:r>` 包裹

### 常见陷阱

- **保留 `<w:rPr>` 格式** — 复制原始 run 的 `<w:rPr>` 块到替换的 run 中
- 表格路径：`<w:tbl>` → `<w:tr>` → `<w:tc>` → `<w:p>` → `<w:r>` → `<w:t>`

---

## XML 结构参考

### 文档结构

```
document.xml
  └── w:body
      ├── w:p (段落)
      │   ├── w:pPr (段落属性：样式、对齐、行距)
      │   └── w:r (run — 一段具有相同格式的文本)
      │       ├── w:rPr (run 属性：字体、大小、粗体、斜体等)
      │       └── w:t (文本内容)
      └── w:tbl (表格)
          └── w:tr (表格行)
              └── w:tc (单元格)
                  └── w:p (单元格内的段落)
```

### Schema 合规

- **`<w:pPr>` 中的元素顺序**：`<w:pStyle>`, `<w:numPr>`, `<w:spacing>`, `<w:ind>`, `<w:jc>`, `<w:rPr>` 放最后
- **空格**：含前导/尾随空格的 `<w:t>` 要加 `xml:space="preserve"`
- **RSID**：必须是 8 位十六进制（如 `00AB1234`）

---

## 图片处理

1. 将图片文件放到 `word/media/`
2. 在 `word/_rels/document.xml.rels` 添加关系：
```xml
<Relationship Id="rId5" Type=".../image" Target="media/image1.png"/>
```
3. 在 `[Content_Types].xml` 添加内容类型：
```xml
<Default Extension="png" ContentType="image/png"/>
```
4. 在 document.xml 中引用：
```xml
<w:drawing>
  <wp:inline>
    <wp:extent cx="914400" cy="914400"/>  <!-- EMU 单位：914400 = 1 英寸 -->
    <a:graphic>
      <a:graphicData uri=".../picture">
        <pic:pic>
          <pic:blipFill><a:blip r:embed="rId5"/></pic:blipFill>
        </pic:pic>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>
```
