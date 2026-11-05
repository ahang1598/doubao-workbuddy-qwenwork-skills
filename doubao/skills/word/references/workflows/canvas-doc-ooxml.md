# Canvas OOXML 编辑与提交

- **读取条件**：仅在 [`canvas-doc.md`](canvas-doc.md#路由总表唯一判定入口) 已选中 `open_ooxml` 后读取。
- **输入与输出**：接收本轮 token、路由记录中的获取结果、剩余目标、已验收目标和已知副作用，返回提交结果及必要同步证据。
- **边界**：不重新评估 Local，不转入文件分支。用户可见表述遵循 [`canvas-doc.md`](canvas-doc.md#用户可见表达)，只描述内容处理和检查，不说“通道可用”“正在运行 audit”或“正在提交 OOXML”。

> 使用前须完整读取本页；未见末行「全文完」时，继续读取至该标记。

固定顺序：**准备任务依据 → 取回唯一候选 → 建立 baseline 与计划 → 原地增量编辑 → audit 与验收 → 提交 → 按门禁决定是否同步校验**。同步校验默认不执行。先完整读取命令契约 [`../cli/canvas-doc-ooxml.md`](../cli/canvas-doc-ooxml.md)。入口已在取回前完成与候选无关的附件、写作指南、素材和依赖准备；已有 ready 候选时复用这些结果，不重复准备。复用入口已有的暂停同时编辑提示，不重复提示或增加确认等待。

目录不在本流程执行。既有目录结构和缓存作为非目标内容保留；提交并确认同步后，计划内目录才进入 [`canvas-doc-toc.md`](../xml/canvas-doc-toc.md) 的独立阶段。

## 取回并锁定唯一目标

入口已有本周期 `ooxml_fetch=ready` 时直接复用其路径与成功信封；只有状态为 unknown 时执行下列命令。ready 路径失效时停止本周期，不能另取一份并混用原基线；unavailable 交回入口。

```bash
lark-cli docs +ooxml-fetch --doc "<token>"
```

按[获取契约](../cli/canvas-doc-ooxml.md#获取-docx-文件路径)校验成功信封、返回路径与可读性，记录 `OOXML_DOCX` 和 ready；路径暂不可读时只按 recovery 预算等待同一路径，不重发取回。

- 返回的 `OOXML_DOCX` 是本周期唯一 `TARGET_DOCX`，原地编辑并提交；不推断路径、不扫描候选目录。
- 取回后不再正文 Local 写入，失败不回退 Local 或文件分支。修正须结束旧周期并重新取回；提交后不读旧候选。跨周期证据保存在任务子目录。

### 第 1 步 · 理解现状和用户需求

在首次修改前：

1. 在任务子目录中将 `OOXML_DOCX` 二进制复制为只读 `SOURCE_DOCX`，核对大小和摘要；TARGET 始终是原 `OOXML_DOCX`。
2. 按 [文件读取流程](../../SKILL.md#二读取-word) 用 `read.py` 按任务涉及维度读取 SOURCE；`python-docx` / `lxml` 只补齐脚本未覆盖的结构证据。
   > **修订读取**：维度 0 输出修订后正文投影，保留插入/移入、排除删除/移出；仅需该投影时直接复用，不再手工解析 OOXML。逐条检查修订节点、属性或边界时才读维度 9；它不配对前后文本，且 `w:del` 与内部 `w:delText` 不重复计数。
3. 沿用 [`canvas-doc-editing.md`](canvas-doc-editing.md#第-1-步--理解任务并读取定位) 的用户材料、写作指南和事实边界；同轮完整材料不重复提取。
4. 若从 Local 切入，只带入剩余目标、已验收目标和恢复已知副作用所需的修改。缺少可靠证据时停止，不把当前降级状态当作原始 baseline。

SOURCE 只用于比较，不参与写路径。后续修复在 TARGET 上增量完成，禁止用 SOURCE 或备份覆盖 TARGET 后“整份重来”。

### 第 2 步 · 定位并规划修改

定位来自真实结构，不凭历史摘录或页码直接修改。首次读取 SOURCE 后一次建立任务所需的正文、对象、样式和编号索引，规划、编辑和验收共用；SOURCE 未变化时不重复运行同一 `read.py` 维度或遍历相同 part，TARGET 变化后只更新受影响索引。每个目标记录 story/part、唯一文字或身份、相邻结构、格式、命中数和必要关联项。

在上下文维护唯一 `edit_plan`，执行和验收都回填此表：

| 目标区域 | 当前证据与稳定定位 | 目标状态 | 内容依据 | 操作 | 必要关联项 | 必须保留 | 验收条件 |
|---|---|---|---|---|---|---|---|
| `<region>` | `<story + unique text/style/id>` | `<result>` | `<source>` | `<operation>` | `<field/reference/layout>` | `<structure/style>` | `<evidence>` |

规划要求：

1. 用语义、story/part、书签、样式、图片 alt text 等稳定证据定位；歧义时枚举 body 直接子节点，仍不唯一则停止。
2. 仅当上下文存在 `selection` 且用户目标与之相关时，将选区转为 `edit_plan` 的语义定位证据：文本记录选中文字及前后相邻内容，图片、表格、图表记录对象类型、可用稳定特征及前后相邻文字或结构；无关或残留选区不得绑定目标，Canvas block ID/range 不得充当 OOXML 身份，证据在最新 SOURCE 中不能唯一命中时通过 `local-fetch` 补读目标内容与相邻内容。
3. 只修改目标和必要关联项；历史问题不妨碍本次任务时不顺手修复。
4. 新内容沿用最近同类结构、语言和格式；唯一 ID、关系和成对边界按目标 part 重建。
5. 标题、编号、图表、分页、书签或引用变化时，把受影响的目录、域、交叉引用、页眉页脚和邻页纳入计划；不手写缓存冒充刷新结果。
6. 在 `<workdir>/edit_plan.json` 只登记写前已计划且可精确定位的 audit 豁免；计划外差异不得事后加入白名单。

### 第 3 步 · 执行编辑操作

- 所有写入只落到 `TARGET_DOCX`，使用 `python-docx` / `lxml`；辅助脚本和数据放任务子目录，正文数据不拼进 shell 命令。
- 编辑脚本启动后、首次保存前先完成预检：导入全部依赖，确认实际存在的 package parts（可选的 `customXml`、comments、footnotes 等不得按固定路径假定存在），集中声明并验证 namespace，统计每个目标的唯一命中数，并为 bookmark、drawing `docPr`、comment、relationship 等身份建立按目标 part/story 分域的无冲突分配器。
- 一次编辑组先在内存或受控工作副本完成全部变换；只有脚本正常结束且组内检查通过，才一次保存回唯一 `TARGET_DOCX`。不得在逐段/逐表循环中反复覆盖 TARGET；异常退出、断言失败或只完成部分目标时丢弃该组未提交候选，保留原始错误，不继续 audit 或提交。
- 按 `edit_plan` 原地增量编辑。不得切到副本、重建整份文件，或用备份覆盖后重跑。
- 保留所有计划外 part、关系、媒体、样式、编号、分节、页眉页脚、书签、内容控件、批注、修订和自定义 XML。
- 新增对象继承最近同类结构；跨 part 关系使用目标 part 的新/既有 `rId`。分裂 run 时复制完整 `rPr`；新增分节默认继承相邻节设置。
- 每组相关修改后回读目标区域；写入状态不明时先确认 TARGET，不继续追加修改。
- 保存前至少检查：XML 可解析、package 关系目标存在、书签 start/end 唯一配对且顺序合法、`wp:docPr/@id` 在无符号 32 位范围 `0..4294967295` 内且全局唯一（已有 0 合法，新增 ID 可从 1 分配）、表格属性子元素满足 schema 顺序、修订/批注边界完整。命中任一失败即停止，不能把后续 audit 当作允许先提交半成品的补救步骤。

#### 新增批注与修订

- 使用本次 `+ooxml-fetch` 返回的 `current_user`，原生 `w:author` 写 `name`。新增批注的 `w:date` 写本次操作的本地墙钟时间，格式为 `YYYY-MM-DDTHH:mm:ssZ`，不得换算为 UTC；修订的 `w:date` 写本次操作的真实 UTC 时间。不得照抄样例或硬编码。导入时仅通过 `userId` 识别用户；首次缺少有效 `user_id` 时立即重新取回并替换候选，再次缺失时仅保留原生 `w:author`，不写身份映射。
- 批注作者身份写入标准 `word/commentsPeople.xml`，不使用 `customXml`：
```xml
<w15:people xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">
  <w15:person w15:author="<current_user.name>"><w15:presenceInfo w15:providerId="<current_user.provider>" w15:userId="<current_user.user_id>"/></w15:person>
</w15:people>
```
  已有同名 `person` 时更新并复用，否则新增；缺少该 part 时创建，并在 `document.xml.rels` 添加类型 `http://schemas.microsoft.com/office/2011/relationships/people` 的关系，在 `[Content_Types].xml` 添加 `/word/commentsPeople.xml`、类型 `application/vnd.openxmlformats-officedocument.wordprocessingml.people+xml` 的声明。不得把 relationship 或 Content Type 写成 `commentsPeople`。普通批注在 `word/comments.xml` 创建 `w:comment`，正文 `w:commentRangeStart`、`w:commentRangeEnd`、`w:commentReference` 的 `w:id` 必须与其一一对应。
- 修订替换仅切分普通文字 run，不跨书签、域或已有修订；复制原 run 的完整 `w:rPr`。插入使用 `w:ins/w:r/w:t`，删除使用 `w:del/w:r/w:delText`；`w:id` 全文档唯一且作为 `nativeId`。`w:ins` 的 `nativeKind` 为 `textInsert`，`w:del` 为 `textDelete`。
- 修订作者身份使用以下 `customXml`，`userId/userName/userProvider` 分别写 `user_id/name/provider`；`partUri` 写原生修订所在 part。替换修订的 `w:ins` 和 `w:del` 必须分别写一项，即使作者相同也不得省略或合并：
```xml
<tto:revisionAuthors xmlns:tto="http://schemas.bytedance.com/office/word/2026/revisionAuthor">
  <tto:revisionAuthor partUri="word/document.xml" nativeKind="textInsert" nativeId="<w:ins 的 w:id>" userId="<current_user.user_id>" userName="<current_user.name>" userProvider="<current_user.provider>"/>
  <tto:revisionAuthor partUri="word/document.xml" nativeKind="textDelete" nativeId="<w:del 的 w:id>" userId="<current_user.user_id>" userName="<current_user.name>" userProvider="<current_user.provider>"/>
</tto:revisionAuthors>
```
- 按 `itemPropsN.xml` 的 `schemaRef` URI 定位并复用 `revisionAuthors` 部件；缺失时使用无冲突编号创建对应 `customXml` 部件并补齐 package 声明。必须在 `word/_rels/document.xml.rels` 中以类型 `http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml`、目标 `../customXml/itemN.xml` 建立关系，不得写入包根 `_rels/.rels`；`itemN.xml` 再通过 `customXml/_rels/itemN.xml.rels` 中类型为 `http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps` 的关系关联 `itemPropsN.xml`。

### 第 4 步 · 提交

```bash
lark-cli docs +ooxml-update --doc "<token>" --file-path "<OOXML_DOCX>"
```

只有 returncode=0、完整 JSON、`ok == true` 且 warnings 已核对，才表示提交已受理；受理不等于同步，但这一语义差异本身不构成同步校验的触发理由。请求仍运行时跟踪同一 task；超时、响应丢失或终态不明时不重发整份提交，按 recovery 输出已受理、明确未派发、`unknown_write` 或 `local_blocked`。这些结果不重新开启引擎选择。

提交前将 `sync_validation.required` 设为 `false`。仅当下列任一条件明确成立时改为 `true`，并记录唯一主原因：

1. `user_requested`：用户明确要求确认当前打开内容已更新；
2. `dynamic_result`：动态域、页码或分页结果必须由宿主更新后才能核对；
3. `downstream_dependency`：后续目录或其他计划内操作必须读到本次更新后的状态；
4. `visual_validation`：提交前已按 [`canvas-doc-editing.md`](canvas-doc-editing.md#第-4-步--回读验收) 明确判定必须检查宿主最终页面。

“确认修改生效”、“受理不等于同步”、“为了保险”、“出清稿”或已在 TARGET 上完成的内容/结构验收都不是触发条件。不得在提交成功后临时补造理由。`sync_validation.required=false` 时，在成功回执和 warnings 核对后立即交付，不再 Fetch、不轮询，也不声称已确认同步。

交付遵循 [`canvas-doc.md`](canvas-doc.md#交付披露)。

===== 全文完 =====
