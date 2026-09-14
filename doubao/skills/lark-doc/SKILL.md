---
name: lark-doc
description: 飞书/豆包在线文档（`/docx`、`/wiki`）的阅读、新建和修改以及操作思维笔记，使用此技能。不处理 Office Word(.docx)、PDF文件；创建文档副本走 drive
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli docs --help;lark-cli mindnotes --help"
---

# lark-doc

## skill 边界

明确本 skill 的适用边界，并非所有写作任务都适用于此 skill，对于不应使用本文能力的情况请选择更加合适的 skill

- 典型应该使用本 skill 的情况：
  - 明确要求交付的是飞书/豆包在线文档
  - 明确给定的是飞书/豆包在线文档要求基于此编辑
  - 读取在线云文档

- 典型不应该使用本 skill 的情况：
  - 应路由到 [`word`](../word/SKILL.md) Skill：
    - 给定 PDF 文件要求转换为 Word 文件
    - 用户明确要求交付 Word 文件
    - 用户提供一份 Word 文件作为模板要求基于此进行 Word 写作
    - 用户提供一份 Word 文件要求基于此进行修改编辑
  - 应路由到 [`lark-drive`](../lark-drive/SKILL.md):
    - 要求把一个飞书/豆包在线文档导出为 Word 文件
    - 添加、分页查看、回复评论或增删 reaction
    - 给定一个 Word 文件要求上传为在线文档
    - 找文档、导入导出、云空间文件上传 / 下载 / 权限管理
    - 复制文档、创建副本或另存为副本时，按其指引使用 `drive +copy`

- 对于一个**写作类**任务，但用户没有明确告知交付载体时，应该遵循如下判断

  | 体裁 | 典型场景 | 默认交付载体 |
  |---|---|---|
  | 学术教研与基础教育教学 | 学习计划、备考路径、复习讲义、试卷与讲评、教案、公开课、教学设计、课程材料、论文写作与指导 | Word |
  | 党政公文和其他正式文书写作 | 党政机关、事业单位、基层党组织面向体系内或公共部门的正式文书；企业、社会组织等境内法人向党政部门、事业单位提交的正式文书及党建材料；个人向政府、基层村居或党组织提交的思想汇报、申请等材料 | Word |
  | 商务与项目合同 | 采购、服务、合作、买卖、租赁、承揽、补充协议、履约约定 | Word |
  | 专业领域文书 | 专利、司法文书及其他法定法律文书、招投标、报价、简历 | Word |
  | 媒体与传播 | 微信公众号推文、小红书图文笔记、邮件、短视频口播稿、短视频分镜脚本、平台标题、封面文案和标题库 | 在线文档 |
  | 创意写作 | 网文、小说、故事、同人、剧本、互动叙事、故事大纲 | 在线文档 |
  | 品牌营销 | 营销策划、品牌认知、产品上市、内容种草、活动战役、增长转化、客户经营、渠道动销与整合营销 | 在线文档 |
  | 生活应用与攻略 | 旅行计划、旅行路书、城市或景点攻略、健身计划、减脂计划、生活指南 | 在线文档 |
  | 分析报告与决策支持 | 基于表格、数据、调研材料、多个附件或可核验来源形成详细分析、研究、比较、诊断或建议 | 在线文档 |
  | 企业与职场文书 | 制度、工作总结、正式汇报、项目提案、岗位说明、培训材料、会议纪要（非政务党建类） | 在线文档 |
  | 无法判断 | 没有明确载体要求，且无法匹配以上体裁 | 在线文档 |

> ⚠️ 交付载体为在线文档的才应该使用本 skill，本 skill 可以与其他 skill 一起共同解决用户的问题。比如使用别的 skill/工具获取用户提供的非在线文档信息，再使用本 skill 的能力输出在线文档；或者使用本 skill 的能力先读取在线文档，然后交由别的 skill/工具完成后续的非在线文档产物交付。

## 在线文档场景与 Shortcut 路由

- **CRITICAL：先判断场景，再读取该场景的参考文件；不要在任务开始时一次性读取全部参考文件。每个文件只在首次进入对应阶段时读取一次。**
- 用户附件必须**逐一盘点**，完整提取结果可以落盘保存，只把当前任务需要的证据载入上下文。
- **所有表示本地文件的 `@path` 均使用 `@./xxx` 形式的相对路径，并以运行 `lark-cli` 时的当前工作目录（CWD）为基准。**
- **Windows 兼容性**：SystemPrompt 出现 `Computer OS: Windows` 时，Bash 工具实际按 PowerShell 语法执行：每次 Bash 调用只执行一条外部命令；禁止使用 `&&` / `||` 串联命令，多步操作拆成多次 Bash 调用。禁止使用 PowerShell `Get-Content` 读取待传给 `lark-cli` 的本地文件，也不得通过变量或管道中转文件内容；参数支持文件输入时，必须直接使用上述 `@file` 形式，避免文本解码或重编码导致内容损坏。
- **身份：文档操作推荐显式指定 `--as user`。**

### 文档内容

- **读取 / 摘要 — [`+fetch`](references/lark-doc-fetch.md)**：先读参考再获取文档。
- **创建 — [`+create` 工作流](references/lark-doc-create-workflow.md)**：从零创作时完整执行 Authoring 流程，**简单任务不是跳过的理由**；仅创建空文档或原样导入用户提供的完整内容时，按其中的 Shortcut 直接创建。
- **编辑 / block 直达链接 — [`+update`](references/lark-doc-update.md)**：语义改写、润色、重组、补写或排版均按 update 参考完成。

### 辅助能力

- **草稿初始化、解析与统计 — [`+script`](references/lark-doc-script.md)**：支持解析文档 URL / token 与本地 XML，统计字数并返回字符诊断；不支持 Markdown 输入。
- **历史版本 — [`+history-list` / `+history-revert` / `+history-revert-status`](references/lark-doc-history.md)**：查询、回滚文档历史版本或检查回滚任务状态。

### 资源、画板与思维笔记

- **插入本地素材 — [`+media-insert`](references/lark-doc-media-insert.md)**：在文末插入本地图片或文件。
- **预览素材 — [`+media-preview`](references/lark-doc-media-preview.md)**：预览文档或评论中的图片、附件或素材。
- **下载素材 — [`+media-download`](references/lark-doc-media-download.md)**：下载文档中的图片、附件、素材或画板缩略图。
- **Docx 封面 — [`+resource-download` / `+resource-update` / `+resource-delete`](references/lark-doc-resource-cover.md)**：下载、更新或删除 Docx 封面。
- **画板 — [`画板工作流`](references/lark-doc-whiteboard.md)**：创建或更新画板时先读取工作流；更新已有画板必须复用现有 token，禁止新建空白画板；使用 [`whiteboard +update`](../lark-whiteboard/references/lark-whiteboard-update.md) 写入。
- **思维笔记 — `mindnotes`**：已有思维笔记走 [`思维笔记链路`](references/lark-doc-mindnote.md)；新建思维笔记走 [`lark-doc-whiteboard`](references/lark-doc-whiteboard.md)。

### 认证与 Scope

执行 Shortcut 时，不预读 [`lark-shared`](../lark-shared/SKILL.md) 或预跑 `auth status --verify`；仅遇到未认证、token / 身份或 scope 错误时读取该 skill，修复后重试。认证、身份或 scope 管理请求则直接使用该 skill。
