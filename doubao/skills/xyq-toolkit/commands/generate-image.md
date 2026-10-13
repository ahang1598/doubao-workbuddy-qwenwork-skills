# generate-image：生图与参考图编辑

适用于普通文生图、指定模型生图和基于参考图片的编辑。目标是生成视频时读取 [生视频](generate-video.md)。

## 输入与参数

| 参数 | 必填 | 规则 |
| --- | --- | --- |
| `--prompt` | 是 | 用户原始描述，不能全为空白 |
| `--model` | 是 | 用户选择的图片模型；缺少时先询问 |
| `--image` | 否 | 本地参考图路径，多张图重复此参数，保留用户指定的角色与顺序 |
| `--ratio` | 否 | 整数枚举，按下表转换明确的比例要求 |
| `--resolution` | 否 | 仅 `seedream_5.0_pro` 支持 `1K`、`2K`、`4K` 选项 |
| `--generate-image-count` | 否 | 用户指定的生成数量 |

比例映射：`0=原始比例/自动`、`2=16:9`、`13=21:9`、`3=9:16`、`4=4:3`、`5=3:4`、`6=1:1`。此命令接收整数，不传 `--ratio "16:9"`。用户未给比例时省略；不明确的比例先确认，不猜枚举。

当前 CLI 帮助列出的模型包括 `seedream_5.0_pro`、`seedream_5.0`、`seedream_4.3`、`nova2`、`seedream_4.5`、`seedream_4.1`、`seedream_4`。用于提示选择，实际支持情况以当前帮助和服务端为准，不在 Skill 中增加模型白名单校验。

本地图片后缀支持 `.jpg/.jpeg/.png/.gif/.bmp/.webp/.svg`。参考图由命令内部上传，不需要自行获取资产 ID。

## 最小调用

```bash
pippit-tool-cli generate-image --prompt "用户原始描述" --model IMAGE_MODEL
```

只追加用户已提供的可选参数。多图编辑见 [参考图编辑示例](../examples/image-edit.md)。

## 返回与处理

成功返回 JSON 中的 `thread_id`、`run_id`、`web_thread_link`；随后执行 [异步结果与媒体交付](../workflows/async-delivery.md)。参数错误、上传失败或服务端拒绝时停止并说明原因，不切换模型或重新提交。仅在已明确失败、问题已修正且原授权仍适用时重试；提交结果不确定时避免重复收费。

`--source` 是可选来源统计参数，由宿主 Agent 根据真实环境静默填写（如 `doubao_office`、`workbuddy`、`codex`）；来源不明时省略，不询问用户，不改变 prompt 或创作参数。详见 [宿主来源统计](../SKILL.md#宿主来源统计)。
