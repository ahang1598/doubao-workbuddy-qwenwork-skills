# 小红书笔记爆款拆解

**触发词**：提取笔记图片、下载小红书图片、获取笔记正文、笔记爆款拆解、识别图片文字

## 支持的链接格式

直接粘贴小红书分享链接，自动解析 `feed_id` 和 `xsec_token`：
- `https://www.xiaohongshu.com/explore/{feed_id}?xsec_token=xxx`
- `https://www.xiaohongshu.com/discovery/item/{feed_id}?xsec_token=xxx`

---

## Step 1：获取笔记数据

> ⚠️ **优先方式**：先用 `curl` + Desktop UA 获取 SSR HTML 中的 `__INITIAL_STATE__`（无需浏览器），仅在 curl 失败时才降级到 browser_use。

### 方式零（推荐优先）：curl + Desktop UA 提取 __INITIAL_STATE__

```bash
# 1. 下载页面 HTML
curl -sL -o /tmp/xhs_note.html \
  -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  "https://www.xiaohongshu.com/explore/FEED_ID?xsec_token=XXX"

# 2. 从 HTML 中提取 __INITIAL_STATE__ JSON
python3 -c "
import re, json, sys
html = open('/tmp/xhs_note.html', encoding='utf-8').read()
m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
if not m:
    print('ERROR: __INITIAL_STATE__ not found in HTML'); sys.exit(1)
# 小红书用 undefined 代替 null，需要替换
raw = m.group(1).replace('undefined', 'null')
state = json.loads(raw)
note_map = state.get('note', {}).get('noteDetailMap', {})
if not note_map:
    print('ERROR: noteDetailMap empty'); sys.exit(1)
note_id = list(note_map.keys())[0]
note = note_map[note_id].get('note', {})
result = {
    'title': note.get('title', ''),
    'content': note.get('desc', ''),
    'note_type': note.get('type', 'normal'),
    'image_urls': [img.get('urlDefault') or img.get('url', '') for img in note.get('imageList', [])],
    'video_url': note.get('video', {}).get('media', {}).get('stream', {}).get('h264', [{}])[0].get('masterUrl', ''),
    'like_count': note.get('interactInfo', {}).get('likedCount', 0),
    'collect_count': note.get('interactInfo', {}).get('collectedCount', 0),
    'comment_count': note.get('interactInfo', {}).get('commentCount', 0),
    'author': note.get('user', {}).get('nickname', ''),
}
print(json.dumps(result, ensure_ascii=False))
"
```

> ⚠️ **curl 失败时**（返回空 HTML、`__INITIAL_STATE__` 未找到、JSON 解析失败、或被反爬拦截返回登录页），**立即降级到 browser_use 方式**。

---

### 方式一（browser_use 降级方案）：

> 仅当 curl 失败时才执行以下步骤。

## Step 1B：Agent 通过 browser_use 获取笔记数据

### 1.1 打开笔记页面

```
browser_use(action="open_tab", url="https://www.xiaohongshu.com/explore/641c5a6a000000000800d77c?xsec_token=ABF7SQH...")
```

### 1.2 等待页面加载

```
browser_use(action="wait_for", timeMs=5000)
```

### 1.3 检查页面是否可访问

```javascript
browser_use(action="evaluate", fn="JSON.stringify({url: window.location.href, title: document.title})")
```

> 如果 URL 被重定向到登录页或首页，说明登录状态失效，执行 SKILL.md 中的「登录墙处理流程」：通过 ask_human 提示用户在浏览器窗口中登录小红书，等待确认后重试。

### 1.4 从 `window.__INITIAL_STATE__` 提取笔记数据

小红书在服务端渲染时会将笔记数据注入到 `window.__INITIAL_STATE__` 全局变量中：

```javascript
browser_use(action="evaluate", fn="(() => { const state = window.__INITIAL_STATE__; if (!state || !state.note || !state.note.noteDetailMap) return JSON.stringify({error: 'no_initial_state'}); const noteId = Object.keys(state.note.noteDetailMap)[0]; const note = state.note.noteDetailMap[noteId]?.note; if (!note) return JSON.stringify({error: 'no_note_data'}); return JSON.stringify({ title: note.title, content: note.desc, note_type: note.type, image_urls: (note.imageList || []).map(img => img.urlDefault || img.url), video_url: note.video?.media?.stream?.h264?.[0]?.masterUrl || note.video?.url, like_count: note.interactInfo?.likedCount || 0, collect_count: note.interactInfo?.collectedCount || 0, comment_count: note.interactInfo?.commentCount || 0, author: note.user?.nickname || '' }); })()")
```

### 1.5 提取评论（可选）

```javascript
// 先滚动页面触发评论加载
browser_use(action="evaluate", fn="window.scrollTo(0, document.body.scrollHeight)")
browser_use(action="wait_for", timeMs=2000)

// 提取评论
browser_use(action="evaluate", fn="JSON.stringify(Array.from(document.querySelectorAll('.comment-item, [class*=commentItem]')).slice(0, 30).map(el => ({author: el.querySelector('[class*=name], .author-name')?.textContent?.trim() || '', content: el.querySelector('[class*=content], .comment-content')?.textContent?.trim() || ''})))")
```

### 1.6 browser_use 失败时降级到 CDP 提取

> ⚠️ **降级触发条件**（满足**任一**即判定 browser_use 失败，**立即降级**，禁止无限重试）：
>
> | 信号 | 判定方式 |
> |------|---------|
> | 页面未就绪 | `evaluate` 返回含 `page is not ready`、`navigation_in_flight`、`Target closed` 等错误 |
> | 数据获取失败 | `__INITIAL_STATE__` 返回 `no_initial_state` 或 `no_note_data` 错误（且已尝试刷新一次） |
> | 登录墙 + browser_use 无法处理 | 页面被重定向到登录页，且 `references/login-wall.md` 流程执行后用户仍无法登录 |
> | 验证码/空白页 | 截图/snapshot 显示验证码拦截页或完全空白 |
> | browser_use 连接失败 | 浏览器启动失败或连接中断 |
>
> ⚠️ **注意**：如果 browser_use 本身可用，只是页面重定向到登录页，应先走 `references/login-wall.md` 流程引导登录。仅当 login-wall 流程也无法解决（如 browser_use 环境不支持用户手动登录）时才降级到 CDP。

**降级执行步骤**：

**执行命令**：

```
ask_human("⚠️ 需要通过 Chrome 浏览器提取小红书笔记数据。即将弹出浏览器窗口，如果需要登录，请在窗口中完成登录操作。脚本会自动检测登录状态并提取数据。")
```

用户确认后执行：
```bash
python3 scripts/cdp_extract.py --url "<小红书笔记URL>"
```

> **说明**：脚本内部会自动检测登录状态。如果未登录，浏览器窗口会保持打开（最长 300 秒），等用户完成登录后自动提取数据。全程只需打开一次浏览器。

**处理返回结果**：

- `success: true` → 从 JSON 读取 `metadata`（title, author, statistics, tags）和 `content`（desc, image_list, video_url），拼接为 `--metadata-json` 继续下方 Step 2
- `success: false` → `ask_human` 告知用户具体原因

> **说明**：`cdp_extract.py` 返回的数据结构示例：
> ```json
> {
>   "success": true,
>   "metadata": {"title": "...", "author": "...", "type": "normal", "note_id": "...", "statistics": {...}, "tags": [...]},
>   "content": {"desc": "正文...", "image_list": ["https://...", ...], "video_url": ""}
> }
> ```
> 将 `metadata` 和 `content` 合并后拼接为 Step 2 的 `--metadata-json` 参数即可。
> 登录状态持久化到 `~/.content-breakdown/chrome-profile-uc/`，首次使用需手动登录一次，后续自动复用。

---

### 1.7 整理数据

Agent 整理以下信息传给脚本：
- `title`：笔记标题
- `content`：正文内容
- `note_type`：`"normal"`（图文）或 `"video"`（视频）
- `image_urls`：图片 URL 列表（图文笔记）
- `video_url`：视频直链（视频笔记）
- 互动数据（like_count, collect_count, comment_count）
- `comments`：评论列表

---

## Step 2：调用脚本处理

### 图文笔记

```bash
python3 scripts/cli.py extract-xhs \
  --metadata-json '{"feed_id": "641c5a6a000000000800d77c", "title": "笔记标题", "content": "正文...", "note_type": "normal", "image_urls": ["https://...", "https://..."], "like_count": 100, "collect_count": 50, "comment_count": 20, "comments": []}' \
  --output-dir ~/.content-breakdown/output
```

脚本会自动下载图片到本地。

### 视频笔记

```bash
python3 scripts/cli.py extract-xhs \
  --metadata-json '{"feed_id": "xxx", "title": "笔记标题", "content": "正文...", "note_type": "video", "video_url": "https://...", "like_count": 100}' \
  --output-dir ~/.content-breakdown/output
```

脚本会下载视频 → 提取音频 → ASR 转录。

---

## Step 3：对图文笔记执行图片 OCR（必须执行）

> ⛔ **强制规则**：如何判断是图文还是视频笔记 → Step 2 执行完成后，检查返回结果：
> - 如果 `image_files` 不为空（有图片文件列表）→ **图文笔记，必须执行 OCR，不可跳过**
> - 如果有 `transcript_text` 字段（有转录文本）→ **视频笔记**，跳过 OCR
>
> ⛔ 图文笔记下载图片后**必须**执行 OCR，否则图片中的文字内容会丢失。**跳过此步骤视为严重错误。不得以"图片已下载"或"正文已有内容"为由跳过 OCR。**

```bash
python3 scripts/cli.py extract-xhs-image-texts \
  --image-dir "~/.content-breakdown/output/641c5a6a000000000800d77c_images" \
  --output-dir ~/.content-breakdown/output
```

执行后获得：每张图片的 OCR 文字（`image_texts`）。

---

## Step 4：按 `references/output-format.md` 输出结果给用户

将 Step 2 的正文 + Step 3 的图片 OCR 文字合并为"提取内容原文"，再进行内容分析。

> 视频笔记跳过 Step 3，直接用 Step 2 的 ASR 转录文本作为原文。

---

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--metadata-json` | 笔记元数据 JSON（从 browser_use 获取） | `'{"feed_id":"...", "title":"...", ...}'` |
| `--no-download-images` | 不下载图片，只返回图片 URL | — |
| `--extract-keyframes` | 提取关键帧截图（仅视频笔记有效） | — |
---

## 关键帧截图（可选功能）

> ⚠️ **触发条件**：仅当用户明确说出以下词语时才加 `--extract-keyframes` 参数，默认不执行：
> - "逐帧分析"、"关键帧"、"帧分析"、"截帧"、"每一帧"、"帧截图"

**工作原理**：视频笔记 ASR 转录完成后，根据每句话的时间戳，用 ffmpeg 在对应时间点截取视频帧，生成图文对照的关键帧报告。

**使用示例**（用户要求关键帧分析时）：

```bash
python3 scripts/cli.py extract-xhs \
  --metadata-json '{"feed_id": "xxx", "note_type": "video", "video_url": "https://..."}' \
  --extract-keyframes \
  --output-dir ~/.content-breakdown/output
```

**注意**：
- 仅对**视频笔记**有效，图文笔记无视频，不支持关键帧截图
- 关键帧截图依赖 ASR 转录结果，需要 ffmpeg 已安装

---

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `__INITIAL_STATE__` 为空 | 页面未完全渲染或被反爬拦截 | 增加等待时间，刷新页面重试 |
| 页面重定向到登录页 | 登录状态失效 | 提示用户在 browser_use 浏览器中登录小红书 |
| 图片下载 403 | CDN 防盗链（需 Referer 头） | 脚本已内置正确的 Referer，通常不会出现 |
| 视频直链为空 | `__INITIAL_STATE__` 中视频字段路径变化 | 检查 `note.video` 下的子字段结构 |

## 预计耗时

- 图文笔记：~15-20s（browser_use + 图片下载 + OCR）
- 视频笔记：~20-25s（browser_use + 视频下载 + ASR 转录）
- 关键帧截图：额外 +5-10s
