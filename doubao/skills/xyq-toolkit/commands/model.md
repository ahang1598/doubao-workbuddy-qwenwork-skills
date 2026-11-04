# model：发现可用图片与视频模型

需要有效登录或 `XYQ_ACCESS_KEY`。生成前可查询当前账号可用的模型及参数配置。`--type image` 查询图片，`--type video` 查询视频；省略时保持查询视频。两类查询共用 Skill 模型接口，图片请求的 `scene=web_image_agent`，视频请求的 `scene=web_turbo_video_generator`，`source_model_key` 为空。身份沿用当前 AK；团队空间请求携带 `X-Team-Id`（可用 `--team-id` 单次指定），API 内部仍按个人身份查询，模型列表不代表团队生成权限。

使用旧版 CLI 时先检查 `model --help` 是否支持图片名称查询，并确认 `generate-image --help` 的 `--model` 接受完整名称；仅支持视频或仍要求图片 key 时先升级，不能用视频结果回答图片模型问题。

```bash
# 图片模型列表、按名称检索、按完整名称查看详情
pippit-tool-cli model list --type image
pippit-tool-cli model search "智能图片" --type image
pippit-tool-cli model describe "智能图片V2.5 Fast" --type image
pippit-tool-cli model "智能图片V2.5 Fast" -t image
pippit-tool-cli model list --type image --refresh

# 全部可见视频模型
pippit-tool-cli model list

# 按 key 或展示名检索；search 是 list 的别名
pippit-tool-cli model search MiniMax --type video

# 按准确 key 查看参数详情；两种写法等价
pippit-tool-cli model describe MiniMax-H3
pippit-tool-cli model MiniMax-H3

# 强制重新查询服务端
pippit-tool-cli model list --refresh
pippit-tool-cli model describe MiniMax-H3 --refresh
```

`list` 输出 `models`。图片每项只用 `name` 展示模型名称，另保留 `kind`，不输出底层模型枚举。图片搜索按名称不区分大小写匹配；`describe` 和 `generate-image --model` 使用列表中的完整名称，包含空格时加引号。名称示例以实际查询结果为准；不硬编码名称到枚举的映射。

视频每项继续包含 `key`、`name`、`kind`；关键词与 key 完全一致时优先返回该项，否则按 key / name 不区分大小写检索，`describe` 使用准确 key。

向用户列模型、展示详情或解释选择时只称图片模型名称，例如“智能图片V2.5 Fast”，不补充对应底层模型值。即使旧版工具仍返回枚举，也不要向用户展示；执行当前名称契约需要升级 CLI。

列表与详情不输出模型级 `is_default`；服务端默认标记不代表用户授权自动选模型。用户未明确模型且未授权代选时先确认，不按列表顺序代选；比例、分辨率、时长、推理强度等参数默认值继续展示，但不据此自动填入用户未指定的生成参数。

两种输出均包含 `scene`、`cached`、`fetched_at`、`expires_at`。合法空列表输出 `models: []`，表示当前没有可见模型。

## 缓存与失败处理

成功结果在系统用户缓存目录的 `pippit-cli/models/` 下保留 5 分钟，命中不会延长有效期；按凭证指纹、API 地址、接口、场景及 CLI 版本隔离。缓存不保存 AK 原文。切换凭证或退出登录后，不读取先前凭证的缓存。

`--refresh` 跳过缓存重新查询。缓存过期、损坏或时间戳异常时重新请求；服务端查询失败返回非零退出状态并提示重试，不返回过期缓存或静态模型列表，也不缓存失败响应。可稍后重试原命令或加 `--refresh`；若是登录错误，先恢复登录。单次查询最长 30 秒，不自动重复请求。

缓存写入失败不丢弃本次服务端成功结果，stderr 会提示；stdout 仍为 JSON。

## 图片参数配置

图片详情的 `ratio`、`resolution`、`effort` 提供可用于生图命令的 `options/default`。以下只是结构示例，不代表任意模型都有这些选项：

```json
{
  "name": "智能图片V2.5 Fast",
  "kind": "image",
  "ratio": {
    "options": [0, 2, 6],
    "default": 6,
    "option_labels": {"0": "adaptive", "2": "16:9", "6": "1:1"}
  },
  "resolution": {"options": ["2K", "4K"], "default": "2K"},
  "effort": {"options": ["low", "high"], "default": "low"}
}
```

- 画面比例的 `options/default` 保留服务端数字枚举，可直接用于图片 `--ratio`；`option_labels` 标注每个数字的比例含义，不作为输入值。存在 `ratio` 参数维度时优先使用该维度，否则读取模型级 `supported_ratio_list/default_ratio`。未知枚举和没有宽高参数支持的 Custom 不展示为可选值。
- 图片分辨率统一为大写（如 `2K`），推理强度统一为小写（如 `high`）。模型没有下发 `effort` 时不展示该能力，也不添加推理强度参数。档位以配置为准，不固定为所有协议档位。
- 展示有效选项及合法默认值；保留维度 `label/description/required_field/active_when_any`。维度有生效条件时先判断条件，不能将条件必选误当作始终必填。
- 图片详情完整保留原始 `parameter_config`，其中的选项文案、未知维度、`default_combination`、`need_available_combinations`、`combination_dimension_keys` 和 `available_combinations` 都可供核对。原始条件和组合里的值保留服务端格式；比对时将比例值按整数枚举解析，并统一分辨率/推理强度大小写。
- 顶层可选值不表示可以任意组合；只在用户提供参数时，按生效条件及合法组合选择。原始配置中的 disabled 选项不可用；未知维度不能直接拼成 CLI 参数。图片创作模式保留原始配置，不套用视频的 `generate_type`。

生成参数见 [生图命令](generate-image.md)。CLI 使用查询配置解析图片模型名称；名称缺失、重复或未找到时失败，刷新后重试，不回退猜测。最终模型准入和参数校验由服务端执行，用户未指定的参数不自动补齐。

## 视频参数配置

`describe` 将配置整理成可直接选择生成参数的结构。以下为示例片段，实际值以查询为准：

```json
{
  "key": "MiniMax-H3",
  "ratio": {
    "options": ["adaptive", "16:9", "21:9", "9:16", "4:3", "3:4", "1:1"],
    "default": "9:16"
  },
  "resolution": {"options": ["768p", "2k"], "default": "768p"},
  "duration": {"min": 4, "max": 15, "step": 1, "default": 10, "unit": "seconds"}
}
```

- `ratio.options/default` 按 IDL 转为字符串，可直接用于 `--ratio`。支持全部有对应生成参数的已有比例枚举；`0` 为 `adaptive`。自定义比例 `1` 没有对应的 CLI 尺寸参数，和未知枚举一样跳过；未知默认值不输出，不猜测替代值。
- `resolution.options` 去除 disabled 选项，默认值必须在有效选项内。
- 参数维度统一保留 `label/description/required_field/active_when_any`；显式的 `required_field: false` 仍输出，未下发时省略。通用元数据不因图片或视频类型而被丢弃。
- `Seedance_2.0_mini`、`Seedance_2.0_mini_lite` 的生成请求可以省略 `--resolution`，服务端默认 `720p`。查询未返回分辨率维度时，不因此要求用户补填，也不在查询结果中伪造选项。
- `duration` 来自参数维度：范围输出 `min/max/step`，选项输出数字 `options`，均以秒为单位，不把选项枚举号当秒数。若只下发旧 `supported_duration_list`，暂保留该原始字段并明确提示不能直接用于 `--duration`。
- `material_limits` 保留数量字段；大小字段使用 `max_image_size_bytes`，视频时长字段使用 `min_video_duration_ms/max_video_duration_ms/max_total_video_duration_ms`。字段未返回与值为 `0` 保持区别。
- `creation_modes` 保留 `enabled`、素材校验等服务端策略，并为文本/参考/首尾帧模式标注对应 `generate_type`。按服务端下发的模式 key，为 `reference_generation`、`video_edit`、`video_extend` 分别输出 `task_type: reference/edit/extend`，可直接用于 `--task-type`；首尾帧使用 `generate_type: 1`，不传 `task_type`。`creation_modes.key` 本身不是提交值。`smart` 比例策略显示 `adaptive`；其他可识别模式继承模型比例。MiniMax 的文本模式排除 `adaptive`，纯文生视频使用固定比例。素材和参数要求见[生成说明](generate-video.md#seedance-25-四种模式)，实际可用性仍以目标服务端开放情况为准。
- 条件维度的 `active_when_any`、参数组合约束及其他未转换字段保留；模型级选项不保证任意组合都可用。配置不一致时通过 `warnings` 提示刷新，未知比例枚举直接跳过。

内部 `config_key` 不输出。缓存仍保存服务端原始配置，列表/详情展示时转换。图片模型标识仅在提交时从名称解析，视频请求契约保持不变，不新增静态模型准入限制。生成参数格式见 [生视频命令](generate-video.md)。

查询结果反映当前账号的服务端可见配置与 Skill 准入范围；最终提交仍由服务端判断权限、参数、余额等条件。缓存最多滞后 5 分钟，需要最新值时使用 `--refresh`。图片生成在上传前使用当前凭证的有效缓存解析完整名称；没有有效缓存时先请求图片模型列表。解析失败时不上传、不提交，不把名称直接传给服务端。视频生成仍不自动查询模型列表。

图片查询依赖服务端 Skill 接口开放 `web_image_agent`，生成依赖对应模型和参数的提交支持。接口返回场景不支持或参数拒绝时如实报告；不能用 Web 模型截图、静态列表或视频目录替代真实查询结果。
