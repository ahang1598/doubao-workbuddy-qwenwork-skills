# generate-image：生图与参考图编辑

适用于普通文生图、指定模型生图和基于参考图片的编辑。目标是生成视频时读取 [生视频](generate-video.md)。

## 输入与参数

| 参数 | 必填 | 规则 |
| --- | --- | --- |
| `--prompt` | 是 | 用户原始描述，不能全为空白 |
| `--model` | 是 | 用户选择的图片模型完整名称；包含空格时加引号，缺少时先询问 |
| `--image` | 否 | 本地参考图路径，多张图重复此参数，保留用户指定的角色与顺序 |
| `--ratio` | 否 | 查询返回的数字枚举（如 `3` 表示 `9:16`）；比例含义见 `option_labels` |
| `--resolution` | 否 | 对应模型查询返回的分辨率；提交时转为大写 |
| `--effort` | 否 | 对应模型查询返回的推理强度；提交为 `general_agent_settings.image_effort`，转为小写 |
| `--generate-image-count` | 否 | 用户指定的生成数量 |

先用 `pippit-tool-cli model list --type image` 查询模型，再用 `pippit-tool-cli model describe "模型名称" --type image` 查询比例、分辨率和可选推理强度。对用户只展示名称，不提供底层模型枚举。生成命令用 `--model "完整名称"`，CLI 负责从当前配置中解析提交标识；名称不存在或重复时停止。查询失败时按错误处理，不回退静态模型目录；细节见 [模型发现](model.md)。

图片比例只传数字，例如用户指定 `9:16` 时使用 `--ratio 3`。从模型查询的 `option_labels` 确认含义，再将对应的数字 `options` 传入；`0` 表示自动比例。CLI 校验整数格式，模型是否支持该枚举由服务端决定。

推理强度只有部分模型包含；未下发 `effort` 维度时不主动提供档位选择。用户未指定的比例、分辨率、推理强度均省略，不从查询默认值自动补齐。条件维度和参数组合以服务端下发为准，不将每个维度的选项任意组合；不在 Skill 或 CLI 维护模型白名单。

使用旧版 CLI 时先检查 `generate-image --help`；若 `--model` 仍要求 key，或缺少用户指定的 `--effort`，先升级，不能把底层枚举交给用户或静默丢弃推理强度。

本地图片后缀支持 `.jpg/.jpeg/.png/.gif/.bmp/.webp/.svg`。参考图由命令内部上传，不需要自行获取资产 ID。

## 最小调用

```bash
pippit-tool-cli generate-image --prompt "用户原始描述" --model "智能图片V2.5 Fast"
```

上例名称须存在于实际查询结果，不能当作静态可用列表。CLI 在上传前复用当前凭证下的有效缓存或查询模型列表，提交时才使用底层枚举，不让用户填写枚举。只追加用户已提供的可选参数。多图编辑见 [参考图编辑示例](../examples/image-edit.md)。

## 返回与处理

成功返回 JSON 中的 `thread_id`、`run_id`、`web_thread_link`；随后执行 [异步结果与媒体交付](../workflows/async-delivery.md)。参数错误、上传失败或服务端拒绝时停止并说明原因，不切换模型或重新提交。仅在已明确失败、问题已修正且原授权仍适用时重试；提交结果不确定时避免重复收费。

`--source` 是可选来源统计参数，由宿主 Agent 根据真实环境静默填写（如 `doubao_office`、`workbuddy`、`codex`）；来源不明时省略，不询问用户，不改变 prompt 或创作参数。详见 [宿主来源统计](../SKILL.md#宿主来源统计)。
