# 创作

## Creation Route

先判断 Creation Route，再选择或校验 Model。Model 和参数不决定 Agent 或 Tool 路由；两条路由都支持指定 Model 及其参数，`model list` 和 `model get` 是共享的实时发现能力。

- Agent：用户要的是业务交付物，或过程需要澄清、规划、多步骤、多产物或继续已有创作。下列十类业务意图通常优先走 Agent；它们只帮助选择 Creation Route，具体 Business Skill 由服务端 Agent 选择。
- Tool：任务是一个无需业务编排的原子单次图片、视频或文本调用，或用户明确要求直接调用 Tool。

业务意图参考（语义匹配，不是只能逐字命中）：

| 业务意图 | 常见说法 | 素材与边界 |
| --- | --- | --- |
| 电商主图套图 | 主图、主图套图、一套主图、主图设计、商品图 | 通常带商品图；区分场景图、海报、详情页、改图、包装设计和多角度图 |
| 电商详情页 | 详情页、电商详情、宝贝详情、产品详情、长图、卖点页、参数页、功能介绍、对比说明、购买理由 | 通常带商品图；出现“详情”类词时优先按电商详情页判断，不按主图套图处理 |
| 商品精修 | 精修、修一下、翻新、白底图、纯白背景、修复使用痕迹 | 必须提供商品实物图；加文字、去水印、抠图、局部编辑、海报、套版和仿图不按商品精修判断 |
| 电商模特 | 模特、试穿、上身、穿戴、佩戴、换模特、换姿势、换背景 | 商品图可选；没有商品图时可以生成纯模特 |
| 商品场景图 | 生成场景、换场景、换个背景、整合到一张图+背景 | 必须提供商品实物图；人像、风景和设计稿不算商品图，带卖点文字的主图不按商品场景图判断 |
| 主题照 | 主题照、写真、风格人像 | 人像图可选 |
| 形象照 | 形象照、职业照 | 人像图可选 |
| 证件照 | 证件照、报名照、头像照，包括换底色和改尺寸 | 人像图可选 |
| 电商图片提示词 | 写电商图片提示词、产品主图提示词 | 服务端按当前组织的 Business Skill 可用性处理 |
| 电商视频提示词 | 电商视频提示词、带货视频、产品宣传视频 | 服务端按当前组织的 Business Skill 可用性处理 |

这些参考不在 CLI 选择具体 Business Skill，也不代替服务端实时可用性。业务意图成立但缺少必需素材时，仍使用 Agent 并请用户提供素材；不要因此降级为 Tool。指定 Model、分辨率、比例、时长等参数也不改变路由。

状态映射：原“商品白底图”Business Skill 已下线，白底图或纯白背景需求按商品精修意图走 Agent；原“小红书人像封面”Business Skill 已下线，相关种草人像封面需求走 Agent 兜底。状态只解释路由，不表示 CLI 指定了服务端 Skill。

典型判断：

- “指定 Model 的电商主图套图”仍使用 Agent，因为目标是业务交付物且可能需要多产物编排。
- “规划三种风格，再分别生成图片”使用 Agent，因为它包含规划和多步骤。
- “指定 Model 生成一只猫”使用 Tool，因为它只是原子单次调用，而不是因为指定了 Model。
- 用户明确要求直接调用某个 Tool 时，使用 Tool。

不猜 Tool 名、Model 名或参数；以当前命令输出为准。用户询问推荐 Model、Model 能力、参数或稿豆价格时，先用 `model list` 筛选，再用 `model get` 核对实时详情。

## Agent 创作

先读取输入规范。需要指定 Model 时，也先读取实时 Model detail：

```bash
gd-cli agent send --schema
gd-cli model list --tool <tool>
gd-cli model get <model>
gd-cli agent send --input request.json
```

将用户要求放在 Text Part。指定 Model 和动态参数时，只增加一个 Generation Constraints Part；`model` 使用 Model 机器标识，`arguments` 的字段和值取自 `model get`，并如实保留用户指定值：

```json
{
  "message": {
    "parts": [
      { "text": "<用户要求>" },
      {
        "data": {
          "model": "<model>",
          "arguments": {
            "resolution": "2K"
          }
        }
      }
    ]
  }
}
```

`arguments` 可以在不指定 `model` 时单独提交，由服务端 Agent 选择 Model。指定 `model` 时，CLI 会按实时 Model detail 校验已提供参数；不要为了 Agent 调用补齐 Tool 的全部 required 字段。Prompt 使用 Text Part，素材使用独立 URL Part，不放入 `arguments`。素材保持消息 Part 的输入顺序；`metadata.role` 可标记 `reference`、`first_frame` 或 `last_frame`，不注入“首帧”或“尾帧”文本。例如：

```json
{
  "message": {
    "parts": [
      { "text": "生成一段转场视频" },
      { "url": "file:///absolute/first.png", "metadata": { "role": "first_frame" } },
      { "url": "file:///absolute/last.png", "metadata": { "role": "last_frame" } },
      { "data": { "model": "<model>", "arguments": { "mode": "<value>" } } }
    ]
  }
}
```

也可用 `--input -` 从 stdin 读取 JSON。成功结果包含 `message` 和本轮实际稿豆消耗 `usage`；将最终文本、资源、服务端续作标识和实际消耗交付给用户。

## Tool 创作

按顺序执行：

```bash
gd-cli tool list
gd-cli model list --tool <tool>
gd-cli model get <model>
gd-cli tool call <tool> --input request.json
```

`tool list` 给出可用 Tool；`model list` 和 `model get` 给出当前可用 Model、说明、费用、预估耗时和结构化参数。`model get` 的 `parameters` 是所选 Model 的实际调用元数据：遵循 `required`、`type`、`description`，SELECT 参数使用 `options[].value`，required 参数带 `default` 时在用户未指定时显式传入默认值。`usageDescription` 描述跨字段规则，例如视频 mode 对首尾帧或素材字段的要求；这类组合不能只从单个字段推断。不要把列表值固化在提示或脚本中。

按所选 Model detail 构造 JSON：提供全部 required 字段；SELECT 参数使用 `options[].value`；required 字段带 default 且用户未指定时，在输入中显式使用该 default。存在 width、height、resolution 等专用字段时，将用户要求写入对应结构化参数，不要只写在 prompt 中。`tool call <tool> --schema` 返回整个 Tool 下所有 Model 的参数并集，只用于 Tool 级发现；选定 Model 后以 `model get` 的参数和 `usageDescription` 为准。

务必将 `model get <model>` 返回的 `model` 原样放在请求 JSON 的顶层 `model` 字段（即运行时的 `arguments.model`），与所选 Model 的参数字段并列；不要只复制 `parameters`。例如：

```json
{
  "model": "<model>",
  "prompt": "<required prompt>",
  "<parameter>": "<value>"
}
```

成功结果包含 `content` 和 `usage`。`content` 是文本或资源链接；`usage` 包含所选模型及模型目录公布的稿豆价格区间，不表示实际扣费。

## 本地媒体

Agent 将本地媒体写成独立 `file://` URL Part；Tool 按所选 Model detail 写入对应媒体参数。CLI 会在内部通过 DAM 完成临时上传并把公网 URL 传给创作服务；不要自行伪造 URL，也不要读取用户未明确授权的路径。
