# CLI 命令参考手册

微信视频号自动化 CLI 完整命令参考。

## 全局选项

所有命令均支持以下全局选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--host` | string | `127.0.0.1` | Chrome 远程调试主机地址 |
| `--port` | int | `9222` | Chrome 远程调试端口 |
| `--account` | string | (空) | 账号名称，用于多账号隔离 |

## Exit Code 规范

| Exit Code | 含义 |
|-----------|------|
| 0 | 成功 |
| 1 | 未登录 |
| 2 | 错误 |

所有命令输出均为 JSON 格式。

---

## 认证命令

### check-login

检查当前登录状态。会导航到创作者中心页面检测登录状态。

```bash
uv run python scripts/cli.py check-login
```

**输出示例**：

```json
// 已登录 (exit code 0)
{"logged_in": true, "message": "已登录"}

// 未登录 (exit code 1)
{"logged_in": false, "message": "未登录，请扫码登录"}
```

**注意**：此命令会刷新页面，在登录流程（login / check-scan-status）进行中时禁止调用。

---

### login

获取微信扫码登录二维码。导航到视频号首页，获取登录二维码图片。

```bash
uv run python scripts/cli.py login
```

**输出示例**：

```json
// 需要登录
{
  "logged_in": false,
  "qrcode_src": "data:image/png;base64,...",
  "qrcode_file": "/tmp/wechat-channels/login_qrcode.png",
  "message": "请使用微信扫描二维码登录。二维码已保存到: /tmp/wechat-channels/login_qrcode.png",
  "next_step": "扫码完成后执行 check-scan-status"
}

// 已登录
{"logged_in": true, "message": "已登录，无需重复登录"}
```

**注意**：执行后不会关闭浏览器连接，保持页面状态等待扫码。

---

### check-scan-status

检查用户扫码后的页面状态。在用户告知已完成微信扫码后调用。

```bash
uv run python scripts/cli.py check-scan-status
```

**输出示例**：

```json
// 登录成功 (exit code 0)
{"logged_in": true, "message": "登录成功"}

// 仍在等待 (exit code 1)
{"waiting_scan": true, "message": "仍在等待扫码，请使用微信扫描二维码后再次执行 check-scan-status"}
```

---

### delete-cookies

删除指定账号的 cookies 文件。用于退出登录或切换账号前清除状态。

```bash
uv run python scripts/cli.py delete-cookies [--account NAME]
```

**输出示例**：

```json
{"success": true, "message": "Cookies 已删除"}
```

---

### close-browser

关闭浏览器 tab。所有操作完成后调用。

```bash
uv run python scripts/cli.py close-browser
```

**输出示例**：

```json
{"success": true, "message": "浏览器 tab 已关闭"}
```

---

## 发布命令

### fill-publish-video

填写视频发布表单，不点击发布按钮。用于分步发布流程，让用户在浏览器中确认内容后再发布。

```bash
uv run python scripts/cli.py fill-publish-video \
  --title-file /path/to/title.txt \
  --video /path/to/video.mp4 \
  [--tags 话题1 话题2 话题3] \
  [--original] \
  [--category 生活] \
  [--schedule "2025-01-15 18:00"]
```

**参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--title-file` | 是 | 标题文件路径（绝对路径），文件内容为标题文本 |
| `--video` | 是 | 视频文件路径（绝对路径） |
| `--tags` | 否 | 话题标签（空格分隔，不含 #） |
| `--original` | 否 | 声明原创（flag） |
| `--category` | 否 | 原创类型（如：生活、科技、美食），仅 `--original` 时有效 |
| `--schedule` | 否 | 定时发布时间（格式：`YYYY-MM-DD HH:MM`） |

**输出示例**：

```json
{
  "success": true,
  "title": "视频标题",
  "video": "/path/to/video.mp4",
  "status": "表单已填写，等待确认发布",
  "next_step": "确认内容无误后执行 click-publish 或 save-draft"
}
```

**注意**：
- 标题内容需先写入文件，通过 `--title-file` 传入
- 执行后不会关闭浏览器连接，保持页面状态
- 视频上传后需等待平台处理完成（最长 10 分钟）

---

### click-publish

点击发表按钮。在 `fill-publish-video` 填写表单并经用户确认后调用。

```bash
uv run python scripts/cli.py click-publish
```

**输出示例**：

```json
{"success": true, "message": "视频已发布"}
```

---

### save-draft

保存为草稿。在 `fill-publish-video` 填写表单后，如果不想立即发布，可保存为草稿。

```bash
uv run python scripts/cli.py save-draft
```

**输出示例**：

```json
{"success": true, "message": "已保存为草稿"}
```

---

### publish-video

一步完成视频发布（填写表单 + 发布/保存草稿）。不推荐使用，建议使用分步发布流程。

```bash
uv run python scripts/cli.py publish-video \
  --title-file /path/to/title.txt \
  --video /path/to/video.mp4 \
  [--tags 话题1 话题2] \
  [--original] \
  [--category 生活] \
  [--schedule "2025-01-15 18:00"] \
  [--draft]
```

**参数**：与 `fill-publish-video` 相同，额外支持：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--draft` | 否 | 保存为草稿而非发布 |

**输出示例**：

```json
{
  "success": true,
  "title": "视频标题",
  "video": "/path/to/video.mp4",
  "status": "已发布"
}
```

---

## 图文发布命令

### fill-publish-image

填写图文发布表单，不点击发布按钮。用于分步发布流程，让用户在浏览器中确认内容后再发布。

```bash
uv run python scripts/cli.py fill-publish-image \
  --images /path/to/img1.jpg /path/to/img2.jpg \
  [--title-file /path/to/title.txt] \
  [--desc-file /path/to/desc.txt] \
  [--tags 话题1 话题2] \
  [--schedule "2025-01-15 18:00"]
```

**参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--images` | 是 | 图片文件路径（空格分隔，最多 18 张，单张 ≤ 20MB） |
| `--title-file` | 否 | 标题文件路径（22 字符内） |
| `--desc-file` | 否 | 描述文件路径（1000 字符内） |
| `--tags` | 否 | 话题标签（空格分隔，不含 #） |
| `--schedule` | 否 | 定时发布时间（格式：`YYYY-MM-DD HH:MM`） |

**输出示例**：

```json
{
  "success": true,
  "title": "图文标题",
  "images": ["/path/to/img1.jpg", "/path/to/img2.jpg"],
  "image_count": 2,
  "status": "表单已填写，等待确认发布",
  "next_step": "确认内容无误后执行 click-publish 或 save-draft"
}
```

**注意**：
- 图片上传比视频快得多，通常几秒内完成
- 执行后不会关闭浏览器连接，保持页面状态
- 图文没有原创声明、合集、短标题等选项

---

### publish-image

一步完成图文发布（填写表单 + 发布/保存草稿）。不推荐使用，建议使用分步发布流程。

```bash
uv run python scripts/cli.py publish-image \
  --images /path/to/img1.jpg /path/to/img2.jpg \
  [--title-file /path/to/title.txt] \
  [--desc-file /path/to/desc.txt] \
  [--tags 话题1 话题2] \
  [--schedule "2025-01-15 18:00"] \
  [--draft]
```

**参数**：与 `fill-publish-image` 相同，额外支持：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--draft` | 否 | 保存为草稿而非发布 |

**输出示例**：

```json
{
  "success": true,
  "title": "图文标题",
  "images": ["/path/to/img1.jpg", "/path/to/img2.jpg"],
  "image_count": 2,
  "status": "已发布"
}
```

---

## Chrome 管理

Chrome 进程管理通过独立脚本 `chrome_launcher.py` 完成：

### 启动 Chrome

```bash
uv run python scripts/chrome_launcher.py [--port 9222] [--headless]
```

### 关闭 Chrome

```bash
uv run python scripts/chrome_launcher.py --kill [--port 9222]
```

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 9222 | 远程调试端口 |
| `--headless` | false | 无头模式 |
| `--kill` | false | 关闭 Chrome |
