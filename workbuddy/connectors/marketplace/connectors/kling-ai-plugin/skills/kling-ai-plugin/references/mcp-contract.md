# 可灵 MCP 输入输出契约

本文件用于核对工具面和参数结构，不把动态模型配置写死。每次操作均按以下顺序读取事实：

1. 当前连接的 `tools/list` 决定实际可调用的工具、工具说明和 `inputSchema`。
2. `who_am_i.availableModels` 决定每个生成工具的模型、模型参数、必填项、默认值、枚举值、数量限制和素材输入。
3. 实际工具响应决定新增输出字段。没有 `outputSchema` 或真实响应时，不猜字段。

本包参数快照版本为 `1.3.1`。当 `who_am_i.mcpVersion` 更高时，实时 schema 仍是参数事实来源，不得仅因版本号较高形成重复重启循环。当前 `tools/list` 与实时模型 schema 能完整描述目标调用时继续；只有目标工具缺失、顶层 `inputSchema` 与实时模型要求冲突，或宿主明确报告工具列表过期时，才停止并提示重启宿主、在新会话刷新连接器。

## 当前 Skill 使用的工具

- 发现与账户：`who_am_i`、`query_membership_and_credits`、`logout`
- 生成与查询：`text_to_image`、`image_to_image`、`text_to_video`、`image_to_video`、`motion_control`、`query_tasks`
- 素材与复用：`motion_library_list`、`element_create`、`element_list`、`element_get`、`element_update`、`element_delete`
- 异常报告：`feedback`

只有当前 `tools/list` 中真实存在的工具才可调用。不同区域或账号等级的工具、模型和值域可能不同，不得假设与国际端完全一致。

## 固定工具级输入

- 五个生成工具的顶层白名单只有：`model`、`arguments`、`inputs`、`rationale`、`taskTraceId`。不得把 `prompt`、分辨率、时长、画幅或图片数量直接放在顶层，它们只能作为所选模型声明的 `arguments[]` 项。
  - `model` 必须来自该工具当次 `who_am_i` 清单，不使用猜测的默认模型。
  - `arguments[]` 每项为 `{name, value}`，所有 `value` 均为字符串；名称、必填、默认值、枚举和 `maxItems` 以所选模型为准。
  - `inputs[]` 每项为 `{name, inputType, url}`；只传所选模型声明的输入名，`inputType` 使用实时 schema 声明的值；所选模型没有 inputs 时省略顶层 `inputs`。
  - `rationale` 说明用户目标和选参理由，不代替用户提示词。
- `query_tasks`：`generationId` 必填，`taskTraceId` 选填。
- `who_am_i`、`query_membership_and_credits`、`logout`、`motion_library_list`、`element_list`：仅有可选 `taskTraceId`。
- `element_get`、`element_delete`：`id` 和可选 `taskTraceId`；调用前按工具说明检查实际必填规则。
- `element_create`：`name`、`description`、`resource`、`tags`、`taskTraceId`。
- `element_update`：在 create 字段基础上增加 `id`。先 `element_get`，再按完整对象更新，避免缺失字段被清空。

`taskTraceId` 使用 RFC 4122 UUIDv7。同一用户目标的发现、素材准备、生成和查询复用同一个值；用户切换到无关目标时创建新值。

## 动态模型参数

提交生成前必须调用 `who_am_i`，按目标工具与模型逐项读取：

- `arguments[]`：`name`、`required`、`default`、`allowedValues` / `allowed_values`、`maxItems` 和 `description`；
- `inputs[]`：`name`、`required` 和 `description`；
- 模型别名只用于理解用户意图，提交时只传规范 `model` 名称。

当前区域的完整模型名、参数、默认值、枚举、数量上限和 inputs 见[模型参数快照](model-parameters.md)。每次生成前读取它作为封闭白名单和已知冲突基线，再以当次 `who_am_i` 覆盖其中可能变化的模型、默认值和值域；实时结果始终优先。

当工具说明与 `who_am_i` 冲突时，采用更严格的工具级限制并停止不安全提交。当前必须保留的门禁包括：

- `text_to_image` 和 `text_to_video` 不使用 Element，不传 `elements` 或 `<<<id>>>`；
- Element 先 `element_get`，图片 Element 只交给实时 schema 明确支持 `elements` 的 `image_to_image` / `image_to_video`；视频 Element 只交给实时 schema 明确支持的 `image_to_video` 模型；
- `motion_control` 必须有主体 `image`，并在动作库 `motionId` 与动作来源 `video` 中二选一；其余方向、分辨率和声音参数从实时模型 schema 获取；
- 某模型要求特定素材 URL 来源而宿主无法提供时，该模型当前不可用于这次图片请求；不得用本地路径或任意外链绕过；
- 不得传实时模型未声明的参数、输入名或枚举值。

## 生成请求预检

按以下顺序构造请求，避免把一个模型的合法参数带到另一个模型：

1. 先确定生成工具，再从该工具当次 `availableModels` 选择规范 `model`；`model` 不得缺省或使用别名。
2. 只从所选模型的 `arguments[]` 建立封闭的参数白名单。补齐必填项；用户明确要求或专业 Skill 已从用途可靠推导出合法值时采用该值，否则有 `default` 的参数传精确默认值。不得让默认值覆盖已确定的画幅、单/多镜头或音频意图。无默认值的可选参数只在用户意图确实需要时传。逐项检查 `allowedValues` / `allowed_values`、范围和 `maxItems`，参数名不得重复，所有 `value` 最终均为字符串。未声明的参数禁止传递，不得用空值占位。
3. 只从所选模型的 `inputs[]` 建立允许输入集合。逐项满足必填输入，并拒绝未声明名称。图片角色不能直接推导字段名：图生图常用 `image_1`，图生视频可能用 `image_1` 或 `first_image`，动作控制使用 `image`。
4. 切换工具或模型后，废弃已构造的 arguments 和 inputs，依据新 schema 重新构造。

分辨率必须同时匹配参数名和值域：图像只在模型声明时使用 `img_resolution`，视频只在模型声明时使用 `resolution`。`image_to_image` 的 `kling-image-v2_1` 当前没有分辨率参数；`image_to_video` 的 3.0 与 3.0 Turbo 当前没有 `aspect_ratio`。不得因为同工具的另一个模型支持某个参数或值就沿用。当前逐模型允许值见[分辨率矩阵](model-parameters.md#分辨率矩阵)。

## 图片 URL 生命周期

- 当前会话图片：优先使用宿主已经提供且所选模型 schema 接受的引用。本地路径、Markdown 图片地址和宿主界面临时 URL 不能在未经 schema 允许时直接作为 input。
- Kling 返回的资源 URL 有效期为 24 小时，不能作为跨会话资产标识。生成成功时保存 `generationId`；若 `works[]` 有多个作品，还要保存用户看到的作品对应的数组序号和 `contentType`。宿主支持消息或附件元数据时，将这组信息绑定到展示结果；否则把任务编号明确显示给用户。
- 复用任何历史 Kling 结果时，不判断旧 URL 看起来是否仍有效，也不把旧 URL 直接放进 inputs。紧邻新生成提交前调用一次 `query_tasks(generationId)`，确认任务成功，按保存的作品序号与 `contentType` 选择非空的当前 URL，并在同一轮立即使用；只有所选模型接受该 URL 来源时才继续。
- 没有任务编号、无法确定具体作品、重新查询失败、目标作品不存在，或使用本轮查询到的 URL 仍返回 `ResourceNotFound`：停止并请求用户重新附图。不要再次查询、不要尝试同任务的其他 URL 字段，也不要自动改成文生模式。
- 多图输入：先记录每张图的语义角色，再按所选模型声明的 input 名称和数量限制映射。URL 不要写入 prompt 代替结构化 input。

## Element 资源

- 图片 Element：`resource.cover` 加 1–3 个 `resource.secondary[{name,inputType,url}]`，不与 `resource.video` 同传。
- 视频 Element：`resource.video`，可按实时工具说明附带 `resource.voice`；不与 `cover` / `secondary` 同传。
- `tags` 至少一个，并且只能使用实时工具说明给出的标签。
- `element_delete` 会删除用户素材，必须在调用前获得明确确认。
- 图片 Element 的主图无法通过普通更新安全替换时，应先说明需要删除并重建，再等待用户确认。

## 已知输出

- 生成提交：`generationId`、`status`，可能含 `creditsConsumed` 和 `message`。
- `query_tasks`：`generationId`、`status`、`createTime`、`finishTime`、`works[]`；作品可能含 `status`、`contentType`、`url`、`urlWithoutWatermark`、`coverUrl`、`coverUrlWithoutWatermark`。状态按大小写不敏感处理，并以实时响应判断终态。
- `query_membership_and_credits`：`userId`、`membershipType`、`availableRemainCredits`。
- `motion_library_list`：`motions[{id,name,motionUrl,coverUrl,duration,hasAudio}]`，`duration` 单位为毫秒。
- `element_list`：`elements[{id,name}]`。
- `element_get`：`id`、`name`、`description`、`resource`、`tags`。
- `motion_control`：普通生成提交结果，之后用 `query_tasks` 查询。
- `element_create`：工具说明保证返回 Element `id`。
- `feedback`：仅报告异常，不重试、退款或修复原任务；一次异常最多调用一次。

`element_update`、`element_delete` 和 `logout` 当前没有可依赖的公开完整 `outputSchema`。读取真实返回并按原样处理，不声称存在未声明字段。如果发布要求机器校验全部成功输出，需要服务端补充 `outputSchema` 或提供脱敏成功 fixture。
