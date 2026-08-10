# 在线网站视频解析与下载

当用户提供在线视频网站链接、短链、分享文本、本地视频文件或视频直链，且目标是解析视频地址、下载 MP4、保存本地视频，或后续要上传飞书妙记时，先使用本参考。

## 通用流程

- 仅支持抖音、快手、B 站、视频直链和本地视频。其他网站的普通视频页面不要尝试浏览、搜索、下载或排障，直接且只回复 `抱歉，不支持解析该网站的视频`。不要追加解释、建议、命令或具体域名。
- 只下载视频、保存 MP4、拿视频直链、解析分享链接：只执行本参考，不进入飞书妙记链路。
- 提取字幕、逐字稿、文案、脚本、总结、章节或时间轴：抖音纯脚本/逐字稿/总结先按 `references/website/douyin.md` 处理；其余不要先单独下载，直接进入 `references/lark-minutes-handoff.md` 并使用 `--run-lark`。
- 画面理解、关键帧、物体/动作出现判断：先按本参考下载本地 MP4；如果还需要脚本或时间轴，再进入飞书妙记链路。
- 本地视频文件无需下载，直接作为后续媒体输入。
- 在线链接进入妙记链路时必须先转换为音频，禁止上传下载得到的视频文件；本地文件才允许直接上传视频。
- 默认使用统一入口；平台 downloader 只用于统一入口失败后的专项排障。

预检输入、平台识别和依赖：

```bash
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --check --json
```

下载视频到本地：

```bash
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video
```

注意：不加 `--run-lark` 时不会上传飞书妙记。在线链接使用 `--media-mode video` 仅用于下载，不会生成视频上传命令。

## 通用输出规范

解析或下载成功时，保留能拿到的结构化字段。不要因为后续只需要 MP4 就丢弃元数据。

基础字段：

- `platform`
- `video_url` 或 `url`
- `file_path`
- 平台 ID，例如 `video_id`、`note_id`、`photo_id`、`bvid`、`aid`、`cid`
- `page_url` / `share_url`

附加字段放入 `metadata`：

- 标题、描述、作者、作者 ID
- 封面 URL
- 时长、宽高、发布时间
- 统计数据
- B 站分页信息

字段以实际平台返回为准；拿不到时返回空对象或省略，不要编造。

## 通用实现约束

- 所有下载器都应支持整段分享文本中的首个 URL。
- 脚本不会安装依赖、浏览器扩展或登录凭证。
- 链接需要登录、私密、删除或平台风控时，不要编造视频地址，向用户说明限制。

## 平台说明

根据输入来源读取对应平台说明：

- 抖音：`references/website/douyin.md`
- 快手：`references/website/kuaishou.md`
- B 站：`references/website/bilibili.md`
- 直链视频：`references/website/direct-video.md`
- 本地视频：`references/website/local-video.md`
