# video-super-resolution：视频超分

用于提升已有视频的分辨率或清晰度。将视频作为新内容参考时使用 [生视频](generate-video.md)。

| 参数 | 必填 | 规则 |
| --- | --- | --- |
| `--video` | 是 | 一个本地视频文件，命令内部上传 |
| `--output-resolution` | 是 | 用户选择的目标分辨率；帮助列出 `720p`、`1080p`、`2k`、`4k` |
| `--tool-version` | 否 | 用户指定时传入；帮助列出 `standard`、`professional_v1`、`professional_v2` |

用户只说“变清晰”且未给目标分辨率时先询问。模型版本或分辨率最终合法性由服务端判断。

```bash
pippit-tool-cli video-super-resolution --video "/path/to/source.mp4" --output-resolution 1080p
```

示例以用户要求 1080p 为前提。成功返回 `thread_id`、`run_id`、`web_thread_link`，按 [异步结果与媒体交付](../workflows/async-delivery.md) 查询、下载并交付。输入失败或服务端拒绝时停止，不擅自切换版本或分辨率。

`--source` 是可选来源统计参数，由宿主 Agent 根据真实环境静默填写（如 `doubao_office`、`workbuddy`、`codex`）；来源不明时省略，不询问用户，不改变 prompt 或创作参数。详见 [宿主来源统计](../SKILL.md#宿主来源统计)。
