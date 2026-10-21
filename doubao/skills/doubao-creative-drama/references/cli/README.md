# Design CLI 命令 Reference

## 素材资产读取：`design-asset +get`

用户引用素材资产 ID 时，读取 [素材资产读取协议](design-asset-get.md)，使用 `design-cli design-asset +get --asset-ids <真实资产ID>`。该命令独立于画布命令，不需要 Workspace ID，不查询、创建或写入 Workspace；资产 ID 与 Workspace ID 不混用。返回的 `resource_url` 是云盘文件页，不是媒体下载地址。

下文的命令数量、domain、公共参数及请求约定均针对 `design-workspace`；`design-asset +get` 以单独的命令页为准。

> 状态：CLI 与服务端均已实现（`+ls` / `+tree` / `+get` / `+create` / `+create-batch` / `+update` / `+update-batch` 七个接口已上线，不再是 mock）。请求与响应结构以 Alice IDL 的 `ItemContent` / `FrameContent` 为准。

本目录逐条记录九个 Canvas Workspace 命令的参数、请求体与返回结构。共用的调用约定写在本文，各命令页只描述自己的差异。

## 调用形状

所有命令都属于 `design-workspace` 这个 domain，且命令名**带 `+` 前缀**：

```bash
design-cli design-workspace +<command> [flags]
```

domain 名与 `+` 都不可省略。三层 `--help` 都可用：`design-cli --help` 列出 domain，
`design-cli design-workspace --help` 列出九个命令，`design-cli design-workspace +ls --help` 列出该命令的 flag。

🔴 **漏掉 `+`（`design-workspace ls`）或拼错命令名（`+lst`）都是退出码 `2` 的错误**，
不是「默认行为」—— 错误信息里带候选命令名，照它改。

## 命令一览

| 命令 | 作用 | Reference | HTTP path |
|---|---|---|---|
| `+get-workspace` | 查会话上挂的画布；没有时回 `exists=false` | [`get-workspace.md`](get-workspace.md) | `/creativity/canvas_workspace/cli/get_workspace` |
| `+workspace-create` | 建一张新画布，返回画布 ID | [`workspace-create.md`](workspace-create.md) | `/creativity/canvas_workspace/cli/create_workspace` |
| `+ls` | 展开一层目录，返回子目录与直属对象摘要 | [`ls.md`](ls.md) | `/creativity/canvas_workspace/cli/ls` |
| `+tree` | 一次拉完整棵目录骨架 | [`tree.md`](tree.md) | `/creativity/canvas_workspace/cli/tree` |
| `+get` | 按 ID 读取完整内容 | [`get.md`](get.md) | `/creativity/canvas_workspace/cli/get` |
| `+create` | 创建一个 Item 或 Frame | [`create.md`](create.md) | `/creativity/canvas_workspace/cli/create` |
| `+create-batch` | 一次创建多个 | [`create-batch.md`](create-batch.md) | `/creativity/canvas_workspace/cli/create_batch` |
| `+update` | 修改顶层 Item／Frame 的 brief／path | [`update.md`](update.md) | `/creativity/canvas_workspace/cli/update` |
| `+update-batch` | 批量修改顶层 brief／path | [`update-batch.md`](update-batch.md) | `/creativity/canvas_workspace/cli/update_batch` |

**先从当前对话确定画布 ID**：当前对话已有唯一有效 `canvas_workspace_id` 时直接复用；没有时调用 `+workspace-create` 建一张并取得 ID。`+get-workspace` 只用于显式查询、恢复或排障，不代替“对话无 ID 时必须创建”的初始化规则。`+get-workspace` 与 `+workspace-create` 都不带 `--canvas-workspace-id`，其余七个命令消费它。`+workspace-create` 的名字不叫 `+create` 是因为后者已经是“建节点”。

### Workspace 初始化与画布卡片交付

若当前对话没有 Workspace ID，立即调用 `design-cli design-workspace +workspace-create --title "<title>"`；从响应 XML 读取唯一 ID，再由主 Agent 调用 `present_files(<workspace_id>)`，将原始 Workspace ID 作为唯一输入并交付新建画布卡片。不得先调用 `+get-workspace`，不得创建 `workspace-id.txt` 或其他中间文件，也不得附字段名、标题、版本、XML、JSON 或说明。画布卡片交付成功前不得生成／编辑媒体，也不得执行 Item／Frame 写命令。多个 ID 冲突且未指定当前目标时必须先确认，不得猜测。

读取三个命令是渐进式披露：`+tree` 看骨架 → `+ls` 展开分支 → `+get` 读完整内容。不要用 `+get` 试探性地拉大量对象。

### 视频／图像工具结果直接交付例外

所有成功图片结果立即原样直接交付；视频的可见范围、字幕处理与每集唯一最终版本以主 `SKILL.md` 和 `../media-delivery.md` 为准，下方直接交付例外不要求展示内部视频烧录源或中间件。工具关联不等于用户已收到，不把内部关联对象归档为额外最终版本。

`text_to_video`、`image_to_video`、`media_to_video`、`video_edit` 及等价视频生成／编辑工具，以及 `image_gen`／`image_edit` 的成功结果，使用调用时透传的 Workspace ID 关联画布。mainagent 立即将所有成功图片结果的原始对象／句柄逐项交给 `present_files`，再保存、登记和检查；视频保留原有基础可交付检查及必要字幕处理后，未处理版本使用原始视频短链，处理后版本使用当前真实处理资源短链，逐项交给 `present_files`；不再为同一结果调用 `+create`／`+create-batch`，不在交付前插入媒体 `+get`，也不通过下载、复制、`FileBatchUpload` 或重传另建 VIDEO／IMAGE Item。

非 Mobile 本轮已确认批次全部直交后，必须按 [媒体直接交付与产后目录整理](../media-delivery.md#产后目录整理) 用 `+tree`／`+ls` 定位真实对象、分批 `+get` 读取实际内容、仅更新顶层绝对 `path`，再回读核验。目录由 path 自动形成，没有独立 `mkdir`；不得创建空 Item 充当目录。目录整理不改变单项媒体已经交付的状态。Mobile 禁止这些画布操作。

本目录中的媒体创建与 `source_ids` 协议用于用户上传、本地剪辑／拼接／渲染／导出等确需手工入画布的非直接关联工具资产；不适用于重复登记上述生成／编辑结果。其他对象类型仍按各自协议处理。

## 内容模型

**Item** 是可以独立理解和修改的内容，六种 `type`：`IMAGE`、`VIDEO`、`TEXT`、`SHAPE`、`LINE`、`HTML`。HTML 只能是顶层 Item。

**Frame** 是多个非 HTML Item 的组合边界，由成员 Item 组成并整体创建、整体读取。内容变化须创建不带旧 Frame／成员 ID 的完整新版本；`+update` 只修改顶层 brief／path，不能修改内容。Frame 只支持 `LAYERED`、`BLANK`；禁止 `<frame type="HTML">`。

**Directory 不是实体**，由 Item 与 Frame 的 `path` 自动构成。写一个不存在的 path 就形成对应目录，不需要 mkdir；改 path 就是移动目录归属，ID 不变。`path` 只表达归档关系，顶层对象位置由服务端安排，Frame 成员由相对 `transform` 表达，两者无关。

所有写入请求的顶层 Item／Frame `path` 必须是以 `/` 开头的画布绝对路径，例如 `/deliverables/key-visuals`；Frame 成员不填 `path`。相对路径禁止写入。

## 公共参数

| 参数 | 适用命令 | 必填 | 说明 |
|---|---|---:|---|
| `--title` | `+workspace-create` | 是 | 新画布标题；空值或纯空白按缺失处理，退出码 `2` |
| `--canvas-workspace-id` | 除 `+get-workspace` / `+workspace-create` 外全部 | 是 | 目标 Canvas Workspace；空值或纯空白按缺失处理 |
| `--path` | `+ls`、`+tree` | 否 | 画布绝对目录路径，非空值必须以 `/` 开头；未传或为空时取默认根路径 `/` |
| `--item-ids` | `+get` | 条件 | 逗号分隔或重复传入；与 `--frame-ids` 至少一项，合计最多 10 个 |
| `--frame-ids` | `+get` | 条件 | 同上 |
| `--input` | 四个写命令 | 是 | 固定为 `-`，XML 只从 stdin 读取 |

参数值两端的空白会被去除；`--item-ids` / `--frame-ids` 中的空项会被丢弃。

## 请求

九个命令都是 `POST`，Body 为 JSON，`Content-Type: application/json`。

出站请求由 `internal/gateway` 统一注入公共 Query 参数、`X-Cli-Source`、`X-Cli-Version`，以及按环境变量决定的 PPE 与 logid Header。完整清单见 CLI 仓库根目录 README 的「当前 CLI 出站请求」一节。

相关环境变量：

| 变量 | 作用 |
|---|---|
| `DOUBAO_OFFICE_USER_ACCESS_TOKEN` | 非空时构造 `Authorization: Bearer <token>` |
| `PPE_ENV` | 非空时发送 `X-Tt-Env` 与 `X-Use-Ppe: 1` |
| `DOUBAO_OFFICE_LOG_ID` | 非空时发送 `X-Tt-Logid`；CLI 输出里不含 logid |
| `DOUBAO_OFFICE_CLI_FORWARD_PROXY` | 非空时请求改发到该正向代理入口（裸 Host 加 Path，缺 scheme 按 `https` 补齐） |
| `DOUBAO_CANVAS_NO_PROXY` | 非空时禁用 HTTP 代理 |
| `MCP_VM_CONVERSATION_ID` | 沙箱注入的会话 ID，被 `+get-workspace` 与 `+workspace-create` 使用：随请求体发出，**不是 CLI 参数**；未设或纯空白时回退 `SESSION_ID` |
| `SESSION_ID` | 会话 ID 的回退来源，仅在 `MCP_VM_CONVERSATION_ID` 未设或纯空白时生效；两者都没有时该字段省略。取值须为十进制数字 |

网关地址内置为 `https://api5-normal-lq.doubao.com`，不由环境变量提供。`X-Cli-Proxy-Target`、`X-Cli-Proxy-Path`、`X-Cli-Proxy-Method` 始终发送，与 `DOUBAO_OFFICE_CLI_FORWARD_PROXY` 是否有值无关。

## 输出与退出码

CLI 不改写 HTTP 返回，完整响应体原样输出。响应结构是 Alice IDL 的：

```json
{"code":0,"msg":"ok","xml_data":"<directory>...</directory>"}
```

| 情况 | 输出位置 | 退出码 |
|---|---|---:|
| `code == 0` | 完整 Body 写 stdout | `0` |
| `code != 0` 或 HTTP 非 2xx | 完整 Body 写 stderr | `1` |
| CLI 参数错误 | 错误信息与 usage 写 stderr | `2` |

**判据是 `code`，不是 HTTP 状态** —— 业务失败时 HTTP 可能仍是 200。

一期服务端对所有非网络逻辑错误固定返回「请你仔细阅读 SKILL 再来调用」，`msg` 没有诊断价值。按退出码分支，不要匹配文案：

- 退出码 `2` → 参数拼错了，对照本目录检查 flag 与取值
- 退出码 `1` → 重读对应命令页与 XML 结构约定，核对后重试

## XML 约定

写命令的输入与读命令的返回都遵守同一套结构。

**标量用 XML 属性，有结构的用子元素。**

```xml
<item item_id="123" type="IMAGE" path="/characters/female-lead" title="林夏立绘" brief="林夏的标准人物立绘">
  <size width="640" height="960" />
  <asset url="https://cdn.example.com/s/a1B2c3" />
</item>
```

`item` 的 `item_id` / `type` / `path` / `title` / `brief` 以及几何节点中的值都是属性；
`size`（顶层）／`transform`（成员）与内容分支（`asset` / `inline` / `shape` / `line`）是子元素。

**`title` 与 `brief` 分工不同**：`title` 是端上展示给用户的短名（几个字），
`brief` 只给你自己消费、用来判断要不要继续 `+get`。`+create` 时两个都要给，
**不要填成一样的内容**；详见 [`../items/README.md`](../items/README.md)。

**数组套一层容器**：`<items>` 装 `<item>`、`<points>` 装 `<point>`、`<stops>` 装 `<stop>`、
`<contents>` 装 `<content>`。单个对象的根节点用单数，与容器成员同形。

**空值不渲染**：没有标题就没有 `title` 属性，没有摘要就没有 `brief` 属性，没有描边就没有 `<stroke>` 子元素。
`rotation` 与 `z_index` 例外——`0` 是有意义的取值（不旋转、最底层），恒有。

**`type` 用字符串枚举名**，不用数字。写错的值不会落到 `UNKNOWN`，服务端直接拒绝。

**内容分支由 `type` 决定，四选一**：

| `type` | 分支节点 |
|---|---|
| `IMAGE` / `VIDEO` | `<asset>` |
| `TEXT` | `<inline>` |
| `SHAPE` | `<shape>` |
| `LINE` | `<line>` |

**`transform` 是扁平结构**：`x`、`y`、`width`、`height`、`rotation`、`z_index`。没有 `offset` / `size` 这两层。顶层 Item／Frame 使用 `<size width height>`，不携带位置；仅 Frame 成员使用 `<transform>`，x／y 是相对 Frame 左上角的偏移。

**Frame 成员不填 `path`** —— 它在目录中不可独立寻址。

**仅对确需手工创建的对象，`<source_ids>` 声明来源对象**，成员是 `<source_id>`，取值可以是 `item_id` 也可以是 `frame_id`：

```xml
<source_ids>
  <source_id>201</source_id>
  <source_id>560</source_id>
</source_ids>
```

它**只在 `+create` 系生效**，且不只是记血缘 —— 服务端用它决定新对象落在画布的哪个位置。
详见 [`create.md`](create.md#source_ids声明来源同时决定落位)。

> 兼容性提示：引入本规则的上游提交注明，`<source_ids>`／`<source_id>` 依赖新版 `canvas_xml_define`，文档可能暂时领先于线上 SDK。实际调用若因标签未被当前运行时识别而失败，必须保留错误并停止依赖步骤，不得伪造成功、静默删除本应存在的来源关系或改用 `+update` 补写血缘。

各类型的字段、取值与示例见 [`../items/README.md`](../items/README.md)。

## 写命令的根节点与 ID

| 命令 | 根节点 | 对象 ID |
|---|---|---|
| `+create` | `<item>` 或 `<frame>` | 不得提供，服务端生成 |
| `+create-batch` | `<batch>` | 每个都不得提供 |
| `+update` | `<item>` 或 `<frame>` | 必须提供 |
| `+update-batch` | `<batch>` | 每个都必须提供 |

`<batch>` 内部固定包含 `<items>` 与 `<frames>` 两个容器，成员装在容器里；没有内容的那一侧输出空容器。

返回值带 ID，**不能直接抄回去当 `+create` 的输入**。读回来的 `<source_ids>` 同样不能原样重提 ——
它在 `+create` 里会被重新当成本次的落位锚点，而不是「保留原来的血缘」。

## 资产

以下只用于确需手工入画布的资产；上述视频／图像工具结果禁止重复创建。CLI **不上传文件**。`IMAGE` / `VIDEO` 的 `<asset url="…">` 只接受可持久访问的短链，已有工具原始短链或回读短链直接复用；仅有本地文件时按交付门禁取得持久短链，禁止重复上传已有短链。

CLI 只把 stdin 中的 XML 当作不透明字符串转发：不解析、不校验结构、不改写其中的任何引用。它只检查 stdin 非空。

## 写入的公共约束

四个写命令（`+create` / `+create-batch` / `+update` / `+update-batch`）共享下面几条：

| 约束 | 取值 | 超限行为 |
|---|---|---|
| 单次 `input` 大小 | 1MB | 直接拒，不截断 |
| 单批对象数（`*-batch`） | 50，按顶层 Item + Frame + Frame 成员合计 | 直接拒，不截断 |

两处都**拒而不截断**：截断出来是「少写了几个对象的成功响应」，调用方不会知道后面那些没生效。

**批量是全成或全败**，没有部分成功状态。`+update-batch` 额外要求**同一个 ID 在一批里只出现一次**（`item_id` 与 `frame_id` 共用一个 ID 空间，仅在顶层对象之间判；update 不接受 Frame 成员）—— 详见 [`update-batch.md`](update-batch.md)。

**`+create` 系不接受 ID，`+update` 系必须带 ID**。所以读命令与写命令的返回（都带 ID）不能直接抄回去当 `+create` 的输入。
