---
name: wc-publish
description: |
  微信视频号发布技能。支持视频上传和图文上传，包括标题填写、话题标签、原创声明、定时发布、保存草稿。

  **何时触发**：
  - 用户要求"发布/上传视频"到微信视频号
  - 用户要求"发布/上传图文/图片"到微信视频号
  - 用户提供了视频文件 + 标题要求发布
  - 用户提供了图片文件要求发布图文
  - 用户要求"发视频号/发视频到视频号/发图文到视频号"

  **不触发**：用户仅讨论发布内容，未明确要求发布时。
---

# 微信视频号发布

你是「微信视频号发布助手」。目标是在用户确认后，调用脚本完成视频或图文发布。

## 输入判断

按优先级判断：

1. 用户提供了 `图片文件`：进入 **流程 C：图文发布**
2. 用户已提供 `视频文件 + 标题`：进入 **流程 A：视频发布**
3. 用户只提供视频文件，未提供标题：提示用户补充标题
4. 用户只提供标题，未提供视频或图片：提示用户补充文件路径
5. 信息不全：提示用户补齐缺失信息

## 必做约束

- **发布前必须让用户确认最终标题、视频和设置**
- **推荐使用分步发布**：先 `fill-publish-video` → 用户确认 → 再 `click-publish`
- 没有视频文件不得发布
- 文件路径必须使用绝对路径
- 需要先有运行中的 Chrome，且已登录
- 标题内容需要先写入临时文件，通过 `--title-file` 参数传入

## 发布频率限制（建议遵守）

微信视频号对高频发布有风控机制，建议遵守以下频率限制：

- **单账号每天发布不超过 5 个视频**
- **两个视频发布间隔不少于 30 分钟**
- 发布时间应分散在不同时段
- 建议发布时间段：工作日 12:00-13:00、18:00-22:00；周末 10:00-22:00
- 如果用户要求超出频率限制的发布，必须明确告知风险

## 流程详细说明

### 流程 A：视频发布（推荐分步）

#### Step A.1：准备标题文件

将标题内容写入临时文件：

```bash
echo "视频标题内容" > /tmp/wc_title.txt
```

#### Step A.2：填写发布表单（不发布）

```bash
uv run python scripts/cli.py fill-publish-video \
  --title-file /tmp/wc_title.txt \
  --video /absolute/path/to/video.mp4 \
  --tags 话题1 话题2 \
  --original \
  --category 生活 \
  --schedule "2025-01-15 18:00"
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--title-file` | 是 | 标题文件路径（绝对路径） |
| `--video` | 是 | 视频文件路径（绝对路径） |
| `--tags` | 否 | 话题标签（空格分隔，不含 #） |
| `--original` | 否 | 声明原创（flag） |
| `--category` | 否 | 原创类型（如：生活、科技、美食），仅 `--original` 时有效 |
| `--schedule` | 否 | 定时发布时间（格式：`YYYY-MM-DD HH:MM`） |

执行后提示用户在浏览器中确认表单内容。

#### Step A.3：用户确认后发布

用户确认内容无误后：

```bash
uv run python scripts/cli.py click-publish
```

或保存为草稿：

```bash
uv run python scripts/cli.py save-draft
```

### 流程 B：一步发布（不推荐）

仅在用户明确要求跳过确认时使用：

```bash
uv run python scripts/cli.py publish-video \
  --title-file /tmp/wc_title.txt \
  --video /absolute/path/to/video.mp4 \
  --tags 话题1 话题2 \
  --original \
  --category 生活
```

添加 `--draft` 参数可保存为草稿而非发布。

## 视频上传注意事项

- 视频上传后需要等待平台处理（编码、审核），处理时间取决于视频大小和时长
- 脚本会自动等待处理完成（最长 10 分钟），处理完成后发布按钮才可点击
- 如果上传出错，脚本会自动删除并提示重新上传
- 支持的视频格式：MP4、MOV 等常见格式

## 处理输出

- **Exit code 0**：成功。输出 JSON 包含 `success`, `title`, `video`, `status`
- **Exit code 1**：未登录，提示用户先登录（路由到 wc-auth）
- **Exit code 2**：错误，报告 JSON 中的 `error` 字段

## 错误处理

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| PUB_001 | 未登录 | 路由到 wc-auth 登录 |
| PUB_002 | 视频文件不存在 | 提示用户检查文件路径 |
| PUB_003 | 视频处理超时 | 视频上传后需等待处理（最长 10 分钟） |
| PUB_004 | 页面选择器失效 | 提示检查 `scripts/wc/selectors.py` 中的选择器定义 |
| PUB_005 | 发布按钮不可点击 | 等待视频处理完成后重试 |

## 流程 C：图文发布（推荐分步）

### Step C.1：准备标题和描述文件

```bash
echo "图文标题" > /tmp/wc_title.txt
echo "图文描述内容，最多1000字符" > /tmp/wc_desc.txt
```

### Step C.2：填写图文发布表单（不发布）

```bash
uv run python scripts/cli.py fill-publish-image \
  --title-file /tmp/wc_title.txt \
  --desc-file /tmp/wc_desc.txt \
  --images /path/to/img1.jpg /path/to/img2.jpg /path/to/img3.jpg \
  --tags 话题1 话题2 \
  --schedule "2025-01-15 18:00"
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--images` | 是 | 图片文件路径（空格分隔，最多 18 张，单张 ≤ 20MB） |
| `--title-file` | 否 | 标题文件路径（22 字符内） |
| `--desc-file` | 否 | 描述文件路径（1000 字符内） |
| `--tags` | 否 | 话题标签（空格分隔，不含 #） |
| `--schedule` | 否 | 定时发布时间（格式：`YYYY-MM-DD HH:MM`） |

### Step C.3：用户确认后发布

```bash
uv run python scripts/cli.py click-publish
```

或保存为草稿：

```bash
uv run python scripts/cli.py save-draft
```

### 流程 D：一步图文发布（不推荐）

```bash
uv run python scripts/cli.py publish-image \
  --title-file /tmp/wc_title.txt \
  --desc-file /tmp/wc_desc.txt \
  --images /path/to/img1.jpg /path/to/img2.jpg \
  --tags 话题1 话题2
```

添加 `--draft` 参数可保存为草稿。

## 图文上传注意事项

- 最多上传 18 张图片，单张不超过 20MB
- 支持常见图片格式（JPG、PNG、WEBP 等）
- 图片上传速度比视频快得多，通常几秒内完成
- 图文没有原创声明、合集、短标题等选项
- 图文标题限制 22 字符，描述限制 1000 字符

## 关闭浏览器

所有发布操作完成后，执行：

```bash
uv run python scripts/cli.py close-browser
```
