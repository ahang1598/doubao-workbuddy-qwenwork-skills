# 签证文件填写助手

帮用户填写签证申请文档、生成签证辅助材料，内置 .docx 格式处理能力。

## 核心原理

.docx 文件本质是一个 ZIP 压缩包，内含 XML 文件。要在保持格式的前提下修改内容，流程是：解压为 XML → 只修改文本节点 → 重新打包。本技能自带完成这一流程所需的全部脚本。

## 快速参考

| 任务 | 做法 |
|------|------|
| 填写用户提供的 .docx 模板 | 解包 → 编辑 XML → 回包（见下方工作流） |
| 快速查看 .docx 内容 | `uv run skills/lark-doc/office-word/visa-doc-filler/scripts/extract_docx.py template.docx` |
| 从零创建签证文档 | 用 `docx-js`（见 `../references/docx-creation-guide.md`） |
| 读取 PDF 文件 | 直接使用 Read 工具读取（原生支持 PDF 转文本） |
| 读取图片（护照、证件） | 直接使用 Read 工具查看（支持 jpg/png/gif/webp） |

---

## 脚本

只有 2 个脚本，零外部依赖（仅需 Python 3.9+ 标准库）：

| 脚本 | 用途 |
|------|------|
| `scripts/docx_edit.py` | 解包/打包 .docx（`unpack` 和 `pack` 两个子命令） |
| `scripts/extract_docx.py` | 提取 .docx 文本内容，保留表格结构信息 |

---

## 工作流（编辑已有文档）

用户给一份 .docx 模板或待修改的文档时，按以下步骤操作。

### 第一步：读取用户资料

用户可能同时提供个人资料文件（简历、护照扫描件等），格式可能是：
- **Word (.docx)** — `uv run skills/lark-doc/office-word/visa-doc-filler/scripts/extract_docx.py resume.docx` 或直接 Read 工具读取
- **PDF** — 直接使用 Read 工具读取（自动转文本）
- **图片** — 使用 Read 工具查看（支持 jpg/png/gif/webp）
- **纯文本** — 直接读取

从中提取姓名、护照号、出生日期、工作信息等关键字段。

### 第二步：提取并分析模板内容

先用提取脚本快速掌握文档全貌：

```bash
uv run skills/lark-doc/office-word/visa-doc-filler/scripts/extract_docx.py template.docx
```

输出带表格结构标注的文本，如：

```
--- 表格 1 ---
  行1: Surname (as in passport) | ____________
  行2: Given name | ____________
  行3: Date of Birth | ____/____/____
  行5: Gender | ☐ Male   ☐ Female
```

通过这个输出确认哪些字段需要填写。

### 第三步：解包模板文档

```bash
uv run skills/lark-doc/office-word/visa-doc-filler/scripts/docx_edit.py unpack template.docx unpacked/
```

解压 ZIP 到 `unpacked/` 目录，格式化 XML 使其可读，并合并相邻的相同格式文本节点。

### 第四步：收集缺失信息

向用户询问还缺的信息。注意：
- 将相关问题归类一起问
- 能推算的就推算（比如从出发日和回程日算出停留天数）
- 参考 `references/field-mappings.md` 确认需要哪些字段和格式

### 第五步：编辑 XML

用编辑工具直接修改 `unpacked/word/document.xml`（以及页眉页脚等其他 XML 文件）。

**核心原则：只改 `<w:t>` 元素内的文本，绝不碰 `<w:rPr>`（格式标签）。**

```xml
<!-- 修改前：占位符 -->
<w:r>
  <w:rPr><w:sz w:val="24"/><w:u w:val="single"/></w:rPr>
  <w:t>____________</w:t>
</w:r>

<!-- 修改后：填入内容，格式自动保持 -->
<w:r>
  <w:rPr><w:sz w:val="24"/><w:u w:val="single"/></w:rPr>
  <w:t>ZHANG SAN</w:t>
</w:r>
```

**处理重复占位符：** 模板中常有多个相同的 `____________`。编辑工具要求匹配唯一，所以在 old_string 中**包含足够的上下文**（占位符前后的标签和文本），确保每次替换精确命中目标。

更多 XML 编辑模式和注意事项见 `../references/docx-editing-guide.md`。

### 第六步：回包输出

```bash
uv run skills/lark-doc/office-word/visa-doc-filler/scripts/docx_edit.py pack unpacked/ filled.docx
```

回包时会自动修复空格问题（`xml:space="preserve"`），压缩 XML，生成最终 .docx 文件。

---

## 从零创建文档

当用户需要全新创建签证辅助材料（而非基于模板填写）时：

1. 参考 `references/common-visa-docs.md` 选择对应的文档结构
2. 参考 `../references/docx-creation-guide.md` 了解 docx-js API
3. 用 Node.js 脚本生成文档（`npm install -g docx`）

---

## 参考文件

按需读取，不要一次全部加载：

| 文件 | 何时读取 |
|------|---------|
| `../references/docx-editing-guide.md` | 编辑已有 .docx 的 XML 时（空格规则、图片插入等） |
| `../references/docx-creation-guide.md` | 用 docx-js 从零创建 .docx 时 |
| `references/common-visa-docs.md` | 需要生成求职信、行程单、邀请函、在职证明、资金证明时 |
| `references/field-mappings.md` | 需要了解各国日期格式、姓名顺序、字段中英日翻译、货币格式时 |

---

## 常见场景

### 场景一：用户提供已有内容的模板
1. 提取文本查看哪些已填、哪些为空
2. 只问缺失的信息
3. 解包 → 填入空白处 → 回包

### 场景二：用户提供空白模板
1. 提取文本识别所有字段
2. 系统性收集全部所需信息
3. 解包 → 逐一填入 → 回包

### 场景三：用户需要从零创建文档
1. 确定文档类型（求职信、行程单等）
2. 读取对应的参考文件
3. 用 docx-js 生成专业格式的文档

### 场景四：用户提供 PDF/图片格式的资料
1. 用 Read 工具直接读取 PDF 或图片
2. 从中提取需要的信息
3. 填入到 .docx 模板中

---

## 填写质量要点

- **姓名必须与护照完全一致** — 使用大写字母，注意顺序（姓在前 vs 名在前）
- **日期格式必须正确** — 不同国家要求不同（见 `references/field-mappings.md`）
- **金额要带货币代码**（RMB、EUR、USD 等）
- **地址一般用英文**（除非表格明确要求中文）
- **电话号码要加国家代码**（中国 +86）
- **护照有效期**要在计划回国日之后至少 6 个月 — 如果不满足要提醒用户
- 复选框使用 ☑ 和 ☐（或匹配模板自身使用的字符）
- 格式自动继承 — 通过 XML 编辑方式填入的内容会自动使用原模板的字体和大小

---

## 依赖

- **Python 3.9+**（仅标准库，无需安装第三方包）
- **docx**（npm）：`npm install -g docx` — 从零创建文档时需要
