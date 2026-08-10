---
name: doubao-video-extract
description: 可提取、下载、解析、理解在线视频或本地视频文件。在线视频包含抖音、快手、B 站、视频直链。可提取内容包含视频的音频、字幕、逐字稿、文案、脚本、总结、时间轴。可理解的视频内容包含画面、人物、物体、动作、界面等视觉元素。
---

# 视频提取

## 执行目录

执行本 Skill 的任何命令前，先将工作目录切换到包含本 `SKILL.md` 的当前 Skill 根目录：

```bash
cd "<当前 doubao-video-extract Skill 文件夹的绝对路径>"
```
例如：
```bash
cd /*/workspace/skills/doubao-video-extract/
```

下文的 `scripts/`、`references/`、`downloads/`、`minutes/` 和 `evidence/` 等路径均相对于该 Skill 根目录

## 先选命令

| 用户目标 | 默认动作 | 不要做 |
| --- | --- | --- |
| 只下载、保存 MP4、解析视频地址 | 读 `references/website_extract.md`，运行 `python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video` | 不要进入妙记链路 |
| 要字幕、逐字稿、原文、文案、总结、关键词、时间轴 | 抖音纯脚本/逐字稿/总结先读 `references/website/douyin.md`；其余读 `references/lark-minutes-handoff.md` | 不要先单独下载再转写；不要使用未在参考中允许的转写工具 |
| 要截图、画面证据、某物/某人/某动作是否出现 | 先判断是否需要口播/原文定位；需要则先 `--run-lark`，再读 `references/video-understanding.md` 抽帧取证 | 不要全片均匀抽帧大海捞针；不要用浏览器搜索或页面查找替代视频取证 |

## 意图路由

先判断用户要的是 **下载视频**、**转写/提取文本**，还是 **视频画面理解**。

### 视频口令

当用户上传视频口令、暗号、淘口令式文本或平台分享口令，但内容中不包含可访问的视频链接时，不要尝试解析、搜索、猜测或要求联网排障，直接提醒用户：

```text
无法支持对视频口令的解析，请提供视频链接
```

### 不支持的网站

仅支持抖音、快手、B 站、视频直链和本地视频。用户要求解析其他网站的普通视频页面时，不要尝试浏览、搜索、下载或排障，直接且只输出：

```text
抱歉，不支持解析该网站的视频
```

不要在这句话前后添加解释、建议或命令，不要提及具体域名。可直接访问的视频文件 URL 不属于“不支持的网站”，继续按视频直链处理。

### 下载视频

当用户只要求下载/保存视频，或只是给出在线视频链接并询问能否解析时：

1. 读取 `references/website_extract.md`。
2. 默认使用统一入口下载/解析：`python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video`。
3. 只有统一入口失败且需要专项排障时，才使用对应平台 downloader 的 `--print-url --json` 或 `--json`。
4. 下载视频的任务无需进入文本提取链路，除非用户明确需要字幕、逐字稿、总结或时间轴。

### 转写与文本提取

当用户要求提取视频的音频、字幕、逐字稿、文案、脚本、总结、章节、关键词或时间轴时：

1. 抖音链接仅要求脚本、逐字稿或总结，且不需要时间轴或画面理解时，读取 `references/website/douyin.md`；其他情况读取 `references/lark-minutes-handoff.md`。
2. 未命中抖音纯文本快速路径时，使用统一入口：`python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark`。
3. 在线链接必须成功转换为音频后才能上传妙记，禁止上传视频文件；只有用户提供本地文件时才能使用视频上传。
4. 授权预检只在首次使用、排障、用户明确要求，或 `--run-lark` 返回授权错误时执行。
5. 未命中抖音纯文本快速路径时，内容提取结果必须来自 `--run-lark` 的转写产物，禁止用浏览器页面或网页元数据代替。

### 视频理解

当用户询问画面、多模态内容、关键帧、某物/某人/某动作是否出现时：

1. 先读取 `references/website_extract.md`，确保有本地 MP4。
2. 如果还需要脚本或时间轴，继续读取 `references/lark-minutes-handoff.md`。
3. 再读取 `references/video-understanding.md`。
4. 禁止用浏览器页面搜索、站内搜索、开发者工具搜索、字幕面板搜索或网页 OCR 结果替代本地 MP4、转写脚本和抽帧证据。

## 脚本布局

- `scripts/downloader/`：B 站、抖音、快手、直链视频下载器。
- `scripts/convert/`：视频转音频。
- `scripts/minutes/`：飞书妙记上传、生成与产物读取。
- `scripts/video_extract/`：脚本解析、关键词时间窗匹配、视频抽帧。
- `scripts/util/`：共享工具函数。

## 快速命令

```bash
# 默认预检入口，先看 references/website_extract.md 或 references/lark-minutes-handoff.md。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --check --json

# 只下载或解析在线视频。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video

# 未命中抖音纯文本快速路径时，执行飞书妙记链路。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark
```

## 反模式

- 不要手工 import `scripts.*` 内部函数；使用脚本 CLI。
- 不要手工拼平台直链、curl 平台 API 或从浏览器右键提取视频；失败时先运行统一入口 `--check --json`，再运行平台 downloader 的 `--print-url --json` 排障。
- 不要把“准备本地视频”和“转写文本”拆成两次执行；未命中 `references/website/douyin.md` 快速路径时直接跑 `--run-lark`。
- 不要使用参考文档未明确允许的第三方转写工具。
- 即使 `--run-lark` 返回飞书授权错误，也必须停止并报告授权问题，禁止绕过飞书妙记自行转写。
- 不要全片均匀抽帧找答案；先用逐字稿匹配时间窗，再抽帧取证。
- 不要用浏览器搜索、页面内查找、站内搜索、评论/标题/描述检索或网页字幕面板检索来代替视频分析；浏览器最多用于打开用户给出的链接或辅助获取原始 URL，不能作为“视频内容提取/关键词定位/截图证据”的来源。

## 输出要求

- 报告下载结果时，包含来源平台、保存后的视频文件或解析得到的视频URL。
- 如果解析过程中拿到标题、描述、作者、封面、时长、统计、分页等附加字段，应随下载结果一起返回为结构化字段，不要丢弃。
- 报告文本提取结果时，包含来源平台和提取结果；生成了脚本文件时一并提供，无法取得文本产物时说明限制。
- 除抖音纯文本快速路径外，用户要求脚本或逐字稿时默认提供豆包文档格式产物，并报告 `doubao_doc_file` 路径。
- 报告飞书妙记结果时，包含来源平台、提取结果、使用到的音频/视频文件、飞书妙记 URL、提取产物文件/路径。
- 报告视频理解结果时，包含检查的结论、时间段、脚本摘录、抽帧图片。
