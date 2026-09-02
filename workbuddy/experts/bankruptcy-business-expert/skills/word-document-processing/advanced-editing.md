# 高级编辑：现有文档修订

> 本文档仅在需要**编辑现有 Word 文档**或执行 **Redlining 修订跟踪**时阅读。新建文档场景无需参考。

---

## 复杂：编辑现有 Word 文档（Document 库）

编辑现有 Word 文档时，使用 **Document 库**（一个用于 OOXML 操作的 Python 库）。该库自动处理基础设施设置，并提供文档操作方法。对于复杂场景，可通过该库直接访问底层 DOM。

> **前置准备**：执行本节命令前，先 `cd` 到 skill 根目录（含 `ooxml/` 和 `scripts/` 的目录），不是 `scripts/` 子目录。

### 工作流

1. **必须 - 完整阅读文件**：从头到尾完整阅读 [`ooxml.md`](ooxml.md)（约600行）。**读取此文件时切勿设置任何范围限制。** 阅读完整内容以了解 Document 库 API 和直接编辑文档文件的 XML 模式。
2. 解包文档：`python ooxml/scripts/unpack.py <office_file> <output_directory>`
3. 使用 Document 库创建并运行 Python 脚本（参见 ooxml.md 中的"Document 库"部分）
4. 打包最终文档：`python ooxml/scripts/pack.py <input_directory> <office_file>`

Document 库既提供常用操作的高级方法，也支持通过直接 DOM 访问处理复杂场景。

## 复杂：Redlining 修订工作流（文档审阅）

此工作流允许你先用 Markdown 规划全面的修订跟踪，再在 OOXML 中实现。**关键**：要实现完整的修订跟踪，必须系统性地实现所有修改。

> **前置准备**：执行本节命令前，先 `cd` 到 skill 根目录（含 `ooxml/` 和 `scripts/` 的目录），不是 `scripts/` 子目录。

**批处理策略**：将相关修改分成 3-10 条一批。这使调试可控的同时保持效率。每批处理完后测试再进入下一批。

**原则：最小化精确编辑**
实现修订跟踪时，仅标记实际发生变化的文本。重复未变化的文本会使修订更难审查且显得不专业。将替换拆分为：[未变化文本] + [删除] + [插入] + [未变化文本]。对于未变化的文本，通过从原文中提取 `<w:r>` 元素并复用来保留原始 run 的 RSID。

示例 - 将句子中的 "30 days" 改为 "60 days"：

```python
# 错误 - 替换了整个句子
'<w:del><w:r><w:delText>The term is 30 days.</w:delText></w:r></w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'

# 正确 - 仅标记变化的部分，为未变化文本保留原始 <w:r>
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

### 修订跟踪工作流

1. **获取 Markdown 表示**：将文档转换为 Markdown，保留修订跟踪：

   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **识别并分组修改**：审查文档，识别所有需要修改的地方，将它们组织为逻辑批次：

   **定位方法**（用于在 XML 中查找修改位置）：
   - 章节/标题编号（如"第3.2节"、"第四条"）
   - 段落标识符（如有编号）
   - 用唯一上下文文本的 Grep 模式
   - 文档结构（如"第一段"、"签署栏"）
   - **不要使用 Markdown 行号** - 行号与 XML 结构不对应

   **批次组织**（每批 3-10 条相关修改）：
   - 按章节："批次1：第2节修订"、"批次2：第5节更新"
   - 按类型："批次1：日期修正"、"批次2：当事人名称变更"
   - 按复杂度：先处理简单文本替换，再处理复杂结构性修改
   - 按顺序："批次1：第1-3页"、"批次2：第4-6页"

3. **阅读文档并解包**：
   - **必须 - 完整阅读文件**：从头到尾完整阅读 [`ooxml.md`](ooxml.md)（约600行）。**读取此文件时切勿设置任何范围限制。** 特别关注"Document 库"和"修订跟踪模式"部分。
   - **解包文档**：`python ooxml/scripts/unpack.py <file.docx> <dir>`
   - **生成预扫描报告**（**强烈推荐，避免后续 grep**）：
     ```bash
     # 完整扫描（适合小文档 <50 段落）
     python scripts/scan_revisions.py <unpacked_dir> -o <scan_report.md>

     # 按关键词过滤（强烈推荐，只看相关段落，大幅减少 token 消耗）
     python scripts/scan_revisions.py <unpacked_dir> --filter 违约金 -o <scan_report.md>

     # 完整模式（含所有 run，适合需要全局视角时）
     python scripts/scan_revisions.py <unpacked_dir> --full -o <scan_report.md>
     ```
     报告包含：段落清单（含行号+样式+文本）、Run 级清单（含行号+文本片段）。
     - **默认紧凑模式**：过滤纯标点/单字等无修订价值的 run，文本截断到 30-40 字
     - **`--filter <关键词>`**：只返回含关键词的段落/run，**对大文档强烈推荐**（如 460 段招标文件全量扫描 80KB，按关键词过滤后 1-2KB）
     - **`--full`**：完整模式，保留所有内容（不截断、不过滤）
     AI 看报告后可直接用 `get_node(line_number=...)` 定位，无需 grep `document.xml`。
   - **记录建议的 RSID**：解包脚本会建议一个用于修订跟踪的 RSID。复制此 RSID 供步骤 4b 使用。

4. **分批实现修改**：按步骤 2 的批次组织策略（按章节/类型/复杂度/顺序）在单个脚本中实现每组 3-10 条相关修改。此方法：
   - 使调试更容易（批次越小 = 越容易隔离错误）
   - 允许渐进式进展
   - 保持效率

   对于每批相关修改：

   **a. 定位目标文本**（**推荐顺序**）：
   1. **首选 `find_text()`**：对跨 run 的碎片化文本（Word 生成文档常见），用 `find_text("目标文本")` 搜索段落级文本，无视 run 拆分
   2. **次选 `get_node(line_number=N, contains="...")`**：用预扫描报告的行号精确定位单 run 文本
   3. **兜底 `grep`**：前两者都失败时再用 grep `document.xml`

   **b. 实施修订**（**推荐方式**）：
   1. **首选 `replace_text_in_paragraph()`**：高层 API，自动处理碎片化 + 生成 `<w:del>`/`<w:ins>` 修订标记
   2. **次选手动 `replace_node()`**：需要精确控制 XML 结构时用

   **c. 保存修改**：`doc.save()`（默认 `validate=False`，避免 Word 文档自身 Schema 兼容性问题误报）

   **注意**：
   - 每次脚本运行后行号会变化，**不要跨脚本依赖行号**——在同一脚本内用 `find_text` 拿到段落引用后直接操作
   - `save(validate=False)` 是默认行为，Word 生成的复杂文档常有 Schema 兼容性问题（非标准但 Word 能容忍），开启校验会误报

5. **打包文档**：所有批次完成后，将解包目录转换回 .docx：

   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **最终验证**：确认所有修改已正确应用，无遗漏。
