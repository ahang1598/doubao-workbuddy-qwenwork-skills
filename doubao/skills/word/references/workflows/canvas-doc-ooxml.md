# 取回整份 DOCX 再修改

提交的是整份 DOCX，会替换当前 Canvas 的内容。先备齐要用的材料，取回文件后直接开始改，尽量缩短两次操作之间的时间。

## 第 1 步 · 确定文档模式

修改前先确定文档模式。已有当前模式就复用，不明时用 `+local-fetch --scope revisions` 读 `data.command_result.document_mode`。

`reading` 模式只读，仍无法确定模式时暂停修改。

## 第 2 步 · 取回并编辑文件

用 [`+ooxml-fetch`](../protocol/cli/ooxml.md) 取回文件。

- 打开返回的路径，在原结构上改目标和必要关联项，保留其余部件和关系。
- 需要改选区时，用选区内容和相邻结构在 DOCX 中定位。Canvas 块 ID 不能当作 OOXML ID。
- `revising` 模式下把改动写成修订，无法合法写成修订时停止。
- 新批注和修订的作者信息来自本次取回的 `current_user`。

## 第 3 步 · 提交文件

用 `+ooxml-update --doc "<token>" --file-path "<返回的 DOCX 路径>"` 提交。

收到受理回执后可以回复「已提交」。

后续操作需要用到新内容，就等客户端应用这份 DOCX 后再做。例如要更新目录，先等正文改动生效，再用 [Canvas 目录命令](../protocol/canvas-doc-toc.md)。

**保存与提交**：

编辑脚本保存成功后执行第 3 步提交，可以在同一次工具调用中依次执行；保存失败就先处理错误，不提交旧文件。只保存这份工作文件还没有修改当前 Canvas。

**工作文件与交付**：

用于编辑和提交的 DOCX 是工作文件，客户端可能在提交后清理。提交后按 [Canvas 的交付规则](canvas-doc.md#交付)回复。用户另要副本时，等客户端应用后再取当前版本。

## 编辑约束

**同一份底稿与并发改动**：

- 取回文件后，正文改动都写进这份 DOCX。提交前别穿插 Canvas 写入，只有编辑完成才提交这一路径。
- 如果 Canvas 已有新改动，从最新版本重新取回并定位目标，原快照不能继续提交。整份提交接口无法保证拦住并发改动。
- 提交结果不明时，先[跟进原请求](canvas-doc-recovery.md)。

**对象结构与 ID**：

- 新增对象可沿用最近同类结构。
- 关系使用目标部件的关系 ID，新增书签与批注使用各自范围内的唯一 ID。
- 绘图 `wp:docPr/@id` 使用全局唯一的无符号 32 位值。

只需读取修订后的正文时可用 `read.py -d 0`；需要修订节点和边界时用维度 `9`。

## 新增批注与修订

### 作者与时间

使用本次 `+ooxml-fetch` 返回的 `current_user`，原生 `w:author` 写 `name`。

- 新增批注的 `w:date` 写本次操作的本地墙钟时间，格式为 `YYYY-MM-DDTHH:mm:ssZ`，不得换算为 UTC。
- 修订的 `w:date` 写本次操作的真实 UTC 时间。

不得照抄样例或硬编码。导入时仅通过 `userId` 识别用户。按取回协议处理缺少 `user_id` 的情况。

### 批注作者与锚点

批注作者身份写入标准 `word/commentsPeople.xml`，不使用 `customXml`：

```xml
<w15:people xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">
  <w15:person w15:author="<current_user.name>"><w15:presenceInfo w15:providerId="<current_user.provider>" w15:userId="<current_user.user_id>"/></w15:person>
</w15:people>
```

- 已有同名 `person` 时更新并复用，否则新增。

缺少该 part 时，创建部件并补齐关系与类型声明：

| 位置 | 操作 |
| --- | --- |
| `word/commentsPeople.xml` | 创建上面的作者身份部件 |
| `document.xml.rels` | 添加类型为 `http://schemas.microsoft.com/office/2011/relationships/people` 的关系 |
| `[Content_Types].xml` | 添加 `/word/commentsPeople.xml`，类型为 `application/vnd.openxmlformats-officedocument.wordprocessingml.people+xml` |

- 不得把 relationship 或 Content Type 写成 `commentsPeople`。
- 普通批注在 `word/comments.xml` 创建 `w:comment`，正文 `w:commentRangeStart`、`w:commentRangeEnd`、`w:commentReference` 的 `w:id` 必须与其一一对应。

### 修订节点

- 修订替换仅切分普通文字 run，不跨书签、域或已有修订；复制原 run 的完整 `w:rPr`。
- 插入使用 `w:ins/w:r/w:t`，删除使用 `w:del/w:r/w:delText`。
- `w:id` 全文档唯一且作为 `nativeId`。
- `w:ins` 的 `nativeKind` 为 `textInsert`，`w:del` 为 `textDelete`。

### 修订作者与部件关系

修订作者身份使用以下 `customXml`，`userId/userName/userProvider` 分别写 `user_id/name/provider`。

`partUri` 写原生修订所在 part。

替换修订的 `w:ins` 和 `w:del` 必须分别写一项，即使作者相同也不得省略或合并：

```xml
<tto:revisionAuthors xmlns:tto="http://schemas.bytedance.com/office/word/2026/revisionAuthor">
  <tto:revisionAuthor partUri="word/document.xml" nativeKind="textInsert" nativeId="<w:ins 的 w:id>" userId="<current_user.user_id>" userName="<current_user.name>" userProvider="<current_user.provider>"/>
  <tto:revisionAuthor partUri="word/document.xml" nativeKind="textDelete" nativeId="<w:del 的 w:id>" userId="<current_user.user_id>" userName="<current_user.name>" userProvider="<current_user.provider>"/>
</tto:revisionAuthors>
```

- 按 `itemPropsN.xml` 的 `schemaRef` URI 定位并复用 `revisionAuthors` 部件。
- 缺失时使用无冲突编号创建对应 `customXml` 部件并补齐 package 声明。
- 必须在 `word/_rels/document.xml.rels` 中以类型 `http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml`、目标 `../customXml/itemN.xml` 建立关系，不得写入包根 `_rels/.rels`。
- `itemN.xml` 再通过 `customXml/_rels/itemN.xml.rels` 中类型为 `http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps` 的关系关联 `itemPropsN.xml`。
