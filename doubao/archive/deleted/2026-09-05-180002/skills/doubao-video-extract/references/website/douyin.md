# 抖音视频解析与下载

## 支持输入

- `douyin.com`
- `v.douyin.com`
- 抖音分享文本
- `modal_id` / `model_id` 链接

## 实现说明

抖音下载器通过移动端分享页解析 `window._ROUTER_DATA`。

## 文本快速解析

当用户仅要求获取抖音视频的脚本、逐字稿或总结，且没有要求时间轴、时间点、截图或画面理解时，直接使用 `web.fetch`：

1. 用户提供分享文本时，先提取其中的抖音视频链接；用户已提供链接时直接使用。
2. 调用 `web.fetch`，将抖音视频链接作为唯一输入参数。不要先下载视频，不要运行 `--run-lark`。
3. 脚本或逐字稿只使用 `web.fetch` 返回的视频文本；总结只基于该文本生成。
4. 不要使用网页标题、描述、评论或其他页面信息补写视频内容，也不要根据返回文本推测时间轴或画面内容。
5. 如果 `web.fetch` 调用失败、没有返回可用的视频文本或内容明显不完整，回退到 `references/lark-minutes-handoff.md` 的 `--run-lark` 链路。

以下任一情况禁止使用本快速路径，改用飞书妙记；涉及画面时再按 `references/video-understanding.md` 抽帧：

- 要求时间轴、时间点、关键词位置或某句话出现的时间。
- 要求截图、关键帧或画面证据。
- 询问人物、物体、动作、场景、地点或界面等视觉内容。
- 同一请求同时包含文本提取和时间定位或视觉理解。

快速路径直接返回用户要求的脚本、逐字稿或总结，无需提供 `minute_url`、媒体文件或 `doubao_doc_file`。

## 解析命令

```bash
python3 scripts/downloader/douyin_downloader.py "<douyin_url_or_share_text>" --print-url --json
```

## 下载命令

```bash
python3 scripts/downloader/douyin_downloader.py "<douyin_url_or_share_text>" --output-dir downloads --json
```

## 故障处理

- 短链解析失败时，先用 `--print-url --json` 查看 normalized / page URL 或错误信息。
- 文本快速解析失败时，按“文本快速解析”的回退规则使用 `--run-lark`，不要用网页元数据代替逐字稿。
