# generate-video：生视频

适用于文生视频、参考图/视频/音频生成新视频以及首尾帧生成。仅处理已有视频的清晰度或字幕时，分别使用 [超分](video-super-resolution.md)、[擦字幕](erase-video-subtitle.md)。

## 输入与参数

| 参数 | 必填 | 规则 |
| --- | --- | --- |
| `--prompt` | 是 | 用户原始描述，不能全为空白 |
| `--model` | 是 | 用户指定的准确模型枚举；未明确模型时先确认，不猜测 |
| `--image` | 否 | 本地图片路径，重复参数 |
| `--video` | 否 | 本地参考视频路径，重复参数 |
| `--audio` | 否 | 本地 `.mp3/.wav` 音频路径，重复参数 |
| `--duration` | 按模型 | 整数秒；MiniMax、Wan、HappyHorse 可省略由服务端补齐默认值，其他模型需明确提供；用户只给时长范围时先确认具体秒数 |
| `--ratio` | 按模式 | 比例字符串，不转换为生图枚举；MiniMax、Wan、HappyHorse 可省略使用服务端配置默认值；其他模型需明确提供 |
| `--resolution` | 按模型 | `Seedance_2.0_mini`、`Seedance_2.0_mini_lite` 可省略，服务端默认 `720p`；MiniMax、Wan、HappyHorse 可省略使用服务端配置默认值；其他模型需明确提供 |
| `--generate-type` | 否 | 首尾帧任务传 `1`；其他显式值交服务端处理 |

当前支持的模型以 `pippit-tool-cli model list` 为准，完整参数配置用 `pippit-tool-cli model describe MODEL_KEY` 查询；缓存有效期为 5 分钟，需要最新结果时加 `--refresh`。详情见 [模型发现](model.md)。CLI 不自行维护模型白名单或分辨率组合校验。

本地图片支持 `.jpg/.jpeg/.png/.gif/.bmp/.webp/.svg`；视频支持 `.mp4/.avi/.mov/.wmv/.flv/.webm/.mkv/.m4v`。CLI 内部上传参考素材。

## 模型与模式

先从模型列表取得准确 key，再查看配置中的分辨率、时长、比例和创作模式。配置会随服务端调整，本页示例不作为可用模型或参数范围清单。

MiniMax、Wan、HappyHorse 可省略分辨率、时长、比例，由服务端配置补默认值。MiniMax 的兼容输入 `720p` 会映射到 `768p`，Wan/HappyHorse 的 `720p` 保持不变。Max 首尾帧模式会按素材采用自适应比例。素材可用组合以当前配置和服务端校验为准，CLI 不限制素材数量。

```bash
pippit-tool-cli model list
pippit-tool-cli model describe MiniMax-H3
pippit-tool-cli generate-video --prompt "用户原始描述" --model MiniMax-H3 --ratio 16:9
```

模型查询失败时提示重试，不从本文示例推定模型仍然可用，不自行替换用户指定的模型。Wan 同样必须有提示词；文件和网页链接输入不在本命令范围内。

## 最小调用

`Seedance_2.0_mini` 和 `Seedance_2.0_mini_lite` 可以省略分辨率，CLI 不补值，交由服务端默认使用 `720p`：

```bash
pippit-tool-cli generate-video --prompt "用户原始描述" --model Seedance_2.0_mini --duration 5 --ratio 16:9
```

`seedance2.0_vision` 仍需指定分辨率：

```bash
pippit-tool-cli generate-video --prompt "用户原始描述" --model seedance2.0_vision --duration 5 --ratio 16:9 --resolution 720p
```

首尾帧场景：明确两张图片的角色，按首帧、尾帧顺序传两次 `--image`，固定传 `--generate-type 1`。MiniMax 只给首帧时也可传一张图片，仍需 `--generate-type 1`。缺少图片、角色不清或无法确定原始描述时先询问。完整示例见 [首尾帧生视频](../examples/first-last-frame.md)。

## 返回与处理

成功返回 `thread_id`、`run_id`、`web_thread_link`，继续 [异步结果与媒体交付](../workflows/async-delivery.md)。素材、权限或参数失败时说明原因，不自动降低用户指定的模型、分辨率或删减素材。无法确认提交是否成功时，不重复生成。

`--source` 是可选来源统计参数，由宿主 Agent 根据真实环境静默填写（如 `doubao_office`、`workbuddy`、`codex`）；来源不明时省略，不询问用户，不改变 prompt 或创作参数。详见 [宿主来源统计](../SKILL.md#宿主来源统计)。
