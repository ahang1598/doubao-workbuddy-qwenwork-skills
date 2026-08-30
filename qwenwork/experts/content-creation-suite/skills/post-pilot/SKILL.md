---
name: post-pilot
description: |
  跨平台内容发布工具：通过 mcp-autocli 的 publish 工具向 6 个平台
  （小红书 / Twitter / Instagram / 抖音 / 微博 / 微信公众号）发布图文或视频内容，
  支持 draft 安全模式、话题标签、封面图。
  TRIGGER when: 用户说 "发布到小红书"、"发推文"、"发微博"、"发抖音"、
  "发微信公众号"、"发布到 Instagram"、"跨平台发布"、"post to ..."、
  "publish ..."、"发一条..."（涉及多平台发布）；上传图文素材要求发布。
  DO NOT TRIGGER when: 用户只想搜内容/看热榜（调 mcp-autocli 的 search/hot，不走本 skill）；
  用户只想拆链接内容（走 content-breakdown-mcp）。
version: 1.0.0
display_name: Post Pilot — 跨平台发布助手
metadata:
  routing_priority: normal
  depends_on_mcp: mcp-autocli
---

# Post Pilot — 跨平台发布助手

通过 mcp-autocli 的 `publish` 工具，向 **6 个平台** 发布图文或视频内容。
默认 `draft=true` 安全模式：自动填好表单后停在发布页，用户手动点击发布。

## 版本查询功能

本技能提供版本号查询服务，供其他技能（如 content-breakdown、content-radar）获取所需的 mcp-autocli 版本号。

版本号来源：
- **版本号直接从 assets/mcp_autocli-1.0.6-py3-none-any.whl 文件名中提取**
- **版本号 = 1.0.6**（从 wheel 文件名解析得出）

版本查询方法：
- 从 assets/mcp_autocli-1.0.6-py3-none-any.whl 文件名解析版本号
- 无需运行时查询已安装版本，直接使用文件名中的版本号

## 不触发场景

- 用户只想搜内容 → 调 mcp-autocli 的 `search` / `hot`
- 用户只想拆链接内容 → 走 content-breakdown-mcp

---

## 前置条件

发布前需确保 mcp-autocli 已注册且连通，**版本号不低于 1.0.6**（click_draft_btn 等新特性支持）：

```python
# 1. 检查 MCP 服务状态
mcp_runtime(action="list_servers", snippet="检查 MCP 服务状态")
```

如未注册或 status != connected，先走 MCP 安装流程（见 [references/mcp-install.md](references/mcp-install.md)）。

**已连通但版本 < 1.0.6** → 需要升级：

```python
execute_shell(command="python -c \"import mcp_autocli; print(mcp_autocli.__version__)\"", snippet="检查 mcp-autocli 版本")
```

版本低于 bundled 时，走 [references/mcp-install.md](references/mcp-install.md) 中的安装流程升级（Step 2 卸旧装新 → Step 3 setup → Step 4 注册 → Step 5 验证）。

**版本号来源**：本 skill 自带 `assets/mcp_autocli-1.0.6-py3-none-any.whl`，bundled 版本 = `1.0.6`。

---

## 发布流程

### Step 1: 收集发布需求

需要知道的信息（不全时 `ask_human` 补）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `platform` | ✅ | 目标平台：`xiaohongshu` / `twitter` / `instagram` / `douyin` / `weibo` / `weixin` |
| `content` | ✅ | 正文内容 |
| `media_type` | ✅ | `text`（仅 twitter/weibo）/ `image`（默认）/ `video` |
| `title` | 小红书/抖音/微信公众号必填 | 标题（小红书 ≤20 字，抖音 ≤30 字，微信公众号 ≤64 字） |
| `author` | 微信公众号必填 | 文章作者名 |
| `images` | media_type=image 时必填 | 本地图片文件绝对路径列表 |
| `video` | media_type=video 时必填 | 本地视频文件绝对路径 |
| `topics` | 可选 | 话题标签列表（不含 #），仅小红书/抖音 |
| `draft` | 默认 true | `true` = 填好表单停住让用户手动发；`false` = 直接发布 |

**微信公众号 author 特殊处理**：
- 所有模式 `author` 均**必填**
- 先看用户输入是否已提供 author，有则直接使用
- `html_file` 模式：用户未提供时，先尝试从 HTML 标签（`<meta name="author">`、`<meta property="og:article:author">` 等）提取
- 仍获取不到 → `ask_human` 向用户询问作者

当用户没有提供完整信息时，调用 `ask_human`：

```python
ask_human(
  question_type="form",
  questions=[
    {
      "id": "platform",
      "input_type": "single_select",
      "question": "要发布到哪个平台？",
      "options": [
        {"label": "小红书", "value": "xiaohongshu"},
        {"label": "Twitter / X", "value": "twitter"},
        {"label": "Instagram", "value": "instagram"},
        {"label": "抖音", "value": "douyin"},
        {"label": "微博", "value": "weibo"},
        {"label": "微信公众号", "value": "weixin"}
      ]
    },
    {
      "id": "media_type",
      "input_type": "single_select",
      "question": "发布什么类型？",
      "options": [
        {"label": "图文", "value": "image", "default": True},
        {"label": "视频", "value": "video"},
        {"label": "纯文本", "value": "text"}
      ]
    },
    {
      "id": "title",
      "input_type": "text",
      "question": "标题（小红书/抖音/微信公众号必填）"
    },
    {
      "id": "content",
      "input_type": "text",
      "question": "正文内容"
    }
  ],
  snippet="收集发布需求"
)
```

### Step 1.5: 微信公众号作者处理

当平台为 `weixin` 时，`author` **必填**。

1. **先看用户输入是否已提供 author** — 如 Step 1 的需求中已包含，直接使用
2. **html_file 模式且未提供 author** — 尝试从 HTML 标签（`<meta name="author">`、`<meta property="og:article:author">` 等）提取
3. 上述两步都获取不到 → `ask_human` 询问：

```python
ask_human(
  question_type="form",
  questions=[{
    "id": "author",
    "input_type": "text",
    "question": "请输入本文作者"
  }],
  snippet="询问微信公众号文章作者"
)
```

### Step 2: 确认用户已登录目标平台

发布操作需要目标平台的 Edge 已登录。

```python
mcp_runtime(
  server="mcp-autocli",
  tool="publish",
  arguments={
    "platform": "<platform>",
    "content": "<正文内容>",
    "media_type": "image",
    "title": "<标题>",
    "images": ["/abs/path/to/img1.jpg", "/abs/path/to/img2.png"],
    "topics": ["话题1", "话题2"],
    "draft": true
  },
  snippet="发布内容到<platform>"
)
```

如果 MCP 返回 `login_required` 或 autocli_error → 先打开登录页：

```python
mcp_runtime(
  server="mcp-autocli",
  tool="launch_login",
  arguments={"platforms": ["<platform>"]},
  snippet="打开平台登录页面"
)
```

然后 `ask_human` 确认用户已完成登录，重新调 publish。

### Step 3: 确认发布结果

**draft=true（默认）** → Edge 窗口中发布表单已填好，告诉用户：
> "已在 Edge 中打开 `<platform>` 发布页，内容已填好，请检查后手动点击发布。"

**draft=false（直接发布）** → 报告发布成功状态。

---

## 各平台参数速查

| 平台 | media_type | 图片上限 | 标题要求 | 正文限制 | 话题 |
|---|---|---|---|---|---|
| xiaohongshu | image/video | 1-9 张 | **必填 ≤20字** | - | ✅ |
| twitter | text/image/video | 1-4 张 | - | ≤280 字符 | - |
| instagram | image/video | 1-10 张（轮播） | - | ≤2200 字符，无纯文本 | - |
| douyin | image/video | 1-35 张 | **必填 ≤30字** | - | ✅ |
| weibo | text/image/video | 1-9 张 | - | ≤2000 字符 | ✅ `#话题#` 格式 |
| weixin | text/image | 1 张（封面） | **必填 ≤64字** | ≤20000 字符，支持 HTML 富文本 | - |

## 各平台发布细节

### 小红书（xiaohongshu）

- 图文：`images=[1-9 张 jpg/png/gif/webp]` + title 必填（≤20 字）
- 视频：`video` 一个 mp4/mov/flv/mkv 文件 + title 必填
- 支持 `topics` 标签
- draft 模式下停在 `creator.xiaohongshu.com/publish`

### Twitter / X

- 纯文本：`media_type=text` + content（≤280 字符）
- 图文：`images=[1-4 张 jpg/png/gif/webp]`
- 视频：`video` 一个 mp4/mov
- 无 title 字段
- draft 模式下停在 `x.com/compose`

### Instagram

- 无纯文本帖子
- 图文：`images=[1-10 张 jpg/png/webp]` 轮播，caption ≤2200 字符
- 视频：`video` 一个 mp4/mov，发布为 Reel

### 抖音（douyin）

- 图文：`images=[1-35 张 jpg/png/gif/webp]` + title 必填（≤30 字）
- 视频：`video` 一个 mp4/mov + title 必填
- 支持 `topics` 标签

### 微博（weibo）

- 文字：`media_type=text` + content（≤2000 字符）
- 图文：`images=[1-9 张]`
- 视频：`video` 一个 mp4/mov
- 支持 `topics`（`#话题#` 格式）

### 微信公众号（weixin）

- 不支持视频
- 图文：`images` 一张封面图（jpg/png/webp）
- title **必填**（≤64 字符）
- `author` **必填**（先检查用户输入，html_file 模式可尝试从 HTML 提取，获取不到则 ask_human）
- content（≤20000 字符，支持 HTML 富文本）
- 支持 `html_file` 模式：直接传一个 HTML 文件路径发布（自动内联 CSS、提取封面图、base64 图片上传）
- draft 模式下可传 `click_draft_btn=true` 自动点击"保存为草稿"按钮

---

## 跨平台批量发布

用户要同时发到多个平台时：

1. 按平台逐个调 `publish`
2. 每个平台独立 `draft=true`，用户逐个确认
3. 每个平台发完后报状态再继续下一个

```python
for p in ["xiaohongshu", "twitter", "weibo"]:
  mcp_runtime(
    server="mcp-autocli",
    tool="publish",
    arguments={"platform": p, "content": "...", "draft": true, ...},
    snippet=f"发布到 {p}"
  )
```

---

## 异常处理

| 现象 | 处理 |
|---|---|
| mcp-autocli 未注册 | 见 [references/mcp-install.md](references/mcp-install.md) |
| `login_required` | 调 `launch_login` 打开登录页，等用户确认后再发 |
| `extension_disconnected` | 调 `launch_login` 唤起 Edge 扩展 |
| `skip_reason` 返回 autocli 错误 | 转述错误给用户，检查文件路径/内容长度 |
| 图片/视频文件不存在 | 用 `list_files` 确认文件存在，不存在则 ask_human |
| 内容超长被截断 | 按平台限制截断或 ask_human 让用户精简 |

---

## 参考文档

- [MCP 安装入口](references/mcp-install.md) — mcp-autocli 安装流程（本 skill 是唯一安装入口，自带 wheel）
- [publish 使用说明](references/publish.md) — 各平台 publish 参数和返回结构

## 版本管理

- **当前支持的 mcp-autocli 版本**：1.0.6
- **版本号来源**：直接从 assets/mcp_autocli-1.0.6-py3-none-any.whl 文件名提取
- **其他技能集成**：content-breakdown 和 content-radar 可通过 useSkill 调用本技能获取版本号
