# 简历工作流编排器

帮用户处理简历的完整流程：读取文件内容 → 理解和优化文本 → 以正确格式回填到原文件中。

## 核心原则

**保留原始格式。** 用户给的文件（Word 简历、简历模板）自带排版和样式。优化内容后必须回填到原文件中，而不是生成一个全新文件丢掉原有格式。

## 第一步：判断用户给了什么

| 用户给的东西 | 下一步 |
|---|---|
| Word 文件（.docx） | 用 `../scripts/extract_docx.py` 提取文本 |
| PDF 文件（.pdf） | 用 `../scripts/extract_pdf.py` 提取文本 |
| 简历模板（空白 .docx） | 解包模板，理解结构，帮用户填入内容 |
| 纯文本/对话描述 | 直接在对话中处理 |
| 什么都没给 | 问用户要文件，或从对话开始构建 |

**用户提供 Word 或 PDF 时，第一步永远是运行提取脚本。** 不要尝试直接"阅读"二进制文件。

## 第二步：判断用户想做什么

| 用户意图 | 对应工作流 | 详细指南 |
|---|---|---|
| "帮我改改简历" / "优化一下" | 读取 → 优化内容 → 回填 | `references/优化简历.md` |
| "帮我填一下这个模板" | 解包模板 → 填入内容 → 打包 | `references/构建简历.md` |
| "帮我从头写一份" | 对话收集信息 → 生成文件 | `references/构建简历.md` |
| "我不知道该写什么" | 辅导发掘成就 → 组织内容 | `references/简历辅导.md` |
| "帮我看看有什么问题" | 读取 → 分析内容 → 给出建议 | `references/优化简历.md` |
| "针对这个职位优化" | 读取 → 对比 JD → 定制内容 → 回填 | `references/优化简历.md` |

## 工具箱

### 内容提取（读取用户的文件）

```bash
# Word — 保留标题层级、加粗、列表等结构
uv run skills/lark-doc/office-word/scripts/extract_docx.py resume.docx
uv run skills/lark-doc/office-word/scripts/extract_docx.py resume.docx --format structured   # JSON 格式

# PDF — 自动检测多栏、提取表格
uv run skills/lark-doc/office-word/scripts/extract_pdf.py resume.pdf
uv run skills/lark-doc/office-word/scripts/extract_pdf.py resume.pdf --format structured

# Word 含修订标记时
pandoc --track-changes=all resume.docx -o resume.md
```

### Word 文件编辑（解包 → 修改 → 打包）

这是回填内容到原 Word 文件的核心流程。详细规范见 `references/格式检查.md`。

```bash
# 1. 解包：将 .docx 解压为可编辑的 XML 文件
uv run skills/lark-doc/office-word/resume-writing/scripts/docx_edit.py unpack resume.docx unpacked/

# 2. 编辑：在 unpacked/word/document.xml 中修改文本
#    （用编辑工具做字符串替换，不要写脚本）

# 3. 打包：重新生成 .docx
uv run skills/lark-doc/office-word/resume-writing/scripts/docx_edit.py pack unpacked/ resume_updated.docx
```

## 回填流程（最重要的部分）

当用户给了 Word 文件并要求优化内容时，完整流程：

1. **提取文本** — 运行 `extract_docx.py` 看到全部内容
2. **理解结构** — 识别各板块（联系信息、摘要、经历、技能等）
3. **优化内容** — 参照 `references/优化简历.md` 改进文本
4. **解包原文件** — 运行 `docx_edit.py unpack` 得到 XML
5. **在 XML 中替换文本** — 用编辑工具直接替换 `document.xml` 中的对应文本
6. **打包** — 运行 `docx_edit.py pack` 生成新文件

关键：第 5 步是在 XML 中做**文本替换**，而不是重建文档结构。这样原有的字体、字号、颜色、间距、模板样式全部保留。

**XML 编辑注意事项（详见 `references/格式检查.md`）：**
- 替换整个 `<w:r>` 元素时，必须保留原始的 `<w:rPr>`（格式属性）
- 引号用 XML 实体：`&#x201C;` `&#x201D;`
- 含空格的文本确保 `<w:t xml:space="preserve">`

## 参考文档索引

| 文档 | 内容 |
|---|---|
| `references/构建简历.md` | 从零构建、模板填写、内容组织 |
| `references/优化简历.md` | 内容改进、ATS 优化、职位定制 |
| `references/简历辅导.md` | 对话引导、STAR 方法、成就发掘 |
| `references/格式检查.md` | Word 解包/编辑/打包规范、PDF 生成、XML 编辑规则 |

## 脚本索引

| 脚本 | 用途 |
|---|---|
| `../scripts/extract_pdf.py` | 从 PDF 提取文本（多栏检测、表格） |
| `../scripts/extract_docx.py` | 从 Word 提取文本（保留结构信息） |
| `scripts/docx_edit.py` | Word 解包/打包（解包为 XML → 编辑 → 打包回 .docx，简历专用简化版） |
