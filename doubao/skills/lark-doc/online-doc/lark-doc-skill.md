# docs

## 场景与 Shortcut 路由

**CRITICAL：先判断场景，再读取该场景的参考文件；不要在任务开始时一次性读取全部参考文件。每个文件只在首次进入对应阶段时读取一次。**

**所有表示本地文件的 `@path` 均使用 `@./xxx` 形式的相对路径，并以运行 `lark-cli` 时的当前工作目录（CWD）为基准。**

**MUST — Windows 兼容性**：SystemPrompt 出现 `Computer OS: Windows` 时，Bash 工具实际按 PowerShell 语法执行：

- 每次 Bash 调用只执行一条外部命令；禁止使用 `&&` / `||` 串联命令，多步操作拆成多次 Bash 调用。
- 禁止使用 PowerShell `Get-Content` 读取待传给 `lark-cli` 的本地文件，也不得通过变量或管道中转文件内容；参数支持文件输入时，必须直接使用上述 `@file` 形式，避免文本解码或重编码导致内容损坏。

**身份：文档操作推荐显式指定 `--as user`。**

### 文档内容

- **读取 / 摘要 — [`+fetch`](references/lark-doc-fetch.md)**：先读参考再获取文档。
- **从零创作 — [`创建工作流`](references/lark-doc-create-workflow.md)**：先完整执行创建工作流，**简单任务不是跳过的理由**；
- **导入 / 空文档 — [`+create`](references/lark-doc-create.md)**：仅创建空文档或原样导入用户提供的完整内容时，跳过创建工作流。
- **编辑 / block 直达链接 — [`+update`](references/lark-doc-update.md)**：语义改写、润色、重组、补写或排版均按 update 参考完成。

### 辅助能力

- **草稿初始化、解析与统计 — [`+script`](references/lark-doc-script.md)**：支持解析文档 URL / token 与本地 XML，统计字数并返回字符诊断；不支持 Markdown 输入。
- **历史版本 — [`+history-list` / `+history-revert` / `+history-revert-status`](references/lark-doc-history.md)**：查询、回滚文档历史版本或检查回滚任务状态。

### 资源、画板与思维笔记

- **插入本地素材 — [`+media-insert`](references/lark-doc-media-insert.md)**：在文末插入本地图片或文件。
- **预览素材 — [`+media-preview`](references/lark-doc-media-preview.md)**：预览文档或评论中的图片、附件或素材。
- **下载素材 — [`+media-download`](references/lark-doc-media-download.md)**：下载文档中的图片、附件、素材或画板缩略图。
- **Docx 封面 — [`+resource-download` / `+resource-update` / `+resource-delete`](references/lark-doc-resource-cover.md)**：下载、更新或删除 Docx 封面。
- **画板 — [`画板工作流`](references/lark-doc-whiteboard.md)**：创建或更新画板时先读取工作流；更新已有画板必须复用现有 token，禁止新建空白画板；使用 [`whiteboard +update`](../../lark-whiteboard/references/lark-whiteboard-update.md) 写入。
- **思维笔记 — `mindnotes`**：已有思维笔记走 [`思维笔记链路`](references/lark-doc-mindnote.md)；新建思维笔记走 [`lark-doc-whiteboard`](references/lark-doc-whiteboard.md)。

## 不在本 Skill 范围

- **Drive 文件级操作**：找文档、导入导出、云空间文件上传 / 下载 / 权限管理 → [`lark-drive`](../../lark-drive/SKILL.md)。复制文档、创建副本或另存为副本时，按其指引使用 `lark-cli drive files copy`；不要用 `docs +fetch` + `docs +create` 重建正文。
- **独立评论操作**：添加、分页查看、回复评论或增删 reaction → [`lark-drive`](../../lark-drive/SKILL.md)；只需紧凑评论上下文时，直接使用默认 JSON 响应的 `docs +fetch`。
