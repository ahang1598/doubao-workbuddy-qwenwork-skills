# 抖音视频爆款拆解

**触发词**：提取视频字幕、视频说了什么、转录视频、视频爆款拆解

## 支持的链接格式

自动识别，无需手动转换：
- **短链接**（最常见）：`https://v.douyin.com/mQ_4LTDAGwE`
- **标准链接**：`https://www.douyin.com/video/7631434873172987176`
- **精选页链接**：`https://www.douyin.com/jingxuan/knowledge?modal_id=7612309120535809318`（自动提取 modal_id）

## 字幕提取策略（自动降级）

> ⚠️ **无 API 字幕时必须继续 ASR 转录，不得直接告诉用户"该视频没有字幕"后停止。** 只有在加了 `--no-transcript` 参数时才允许跳过。

1. **API 字幕**（`subtitle_infos`）：从视频详情 API 中提取，最快，无需下载视频
2. **必剪云端 ASR**：无 API 字幕时**必须**触发，下载视频提取音频，调用必剪免费 ASR，中文识别准确率高
3. **Whisper 本地转录**：必剪 ASR 失败时兜底，需安装 `openai-whisper`。**必须使用 medium 模型**（base 中文效果极差，详见下方 Whisper 转录指南）

> ⚠️ **抖音视频无内嵌字幕**：yt-dlp 返回的 `subtitles` 字段为空字典 `{}`。抖音不通过 API 暴露字幕数据，即使视频画面上有硬字幕也无法直接提取。必须走"下载视频 → 音频提取 → ASR/Whisper 转录"路线。

### Whisper 转录指南（必剪 ASR 失败时）

| 要点 | 说明 |
|------|------|
| ⛔ **模型选择** | **始终使用 `medium`**（1.5B 参数，约 1.42GB）。base 模型（74M）在有背景音乐、方言、快速口语的抖音视频中输出几乎全是乱码，medium 可显著提升中文转录质量 |
| **initial_prompt** | 将视频标题作为 `initial_prompt` 传入，帮助模型理解上下文语境，提升专有名词、品牌名、地名的识别率（脚本自动处理） |
| **性能** | medium 模型在 CPU 上转录 3 分钟音频约需 5-10 分钟；有 NVIDIA GPU 时自动使用 CUDA 加速 |
| **超长视频** | >10 分钟的视频可考虑分段处理（`yt-dlp --download-sections "*0:00-5:00"`）或使用 `large-v3` 模型 |
| **安装** | `pip install openai-whisper`，medium 模型首次使用时自动下载 |

```bash
# 如需手动指定 Whisper 模型（默认已设为 medium）
python3 scripts/cli.py extract-douyin \
  --play-url "https://v26-web.douyinvod.com/..." \
  --whisper-model medium
```

---

## Step 1：获取视频数据

> ⚠️ **优先方式**：先用 `yt-dlp` 获取元数据和视频直链（无需浏览器），仅在 yt-dlp 失败时才降级到 browser_use。

### 方式零（推荐优先）：yt-dlp 直接提取

```bash
# 1. 解析短链接获取完整 URL（短链接场景）
curl -sL -o /dev/null -w '%{url_effective}' -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1' "https://v.douyin.com/xxx"

# 2. 获取元数据（标题、作者、时长、互动数据、字幕信息）
yt-dlp --dump-json --no-download "https://www.douyin.com/video/VIDEO_ID"

# 3. 如果有字幕信息，传给脚本处理（情况 B）
# 4. 如果无字幕，直接下载视频走 ASR（情况 A）
yt-dlp -f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best' -o "/tmp/douyin_%(id)s.mp4" --no-playlist "URL"
```

> **yt-dlp 返回的关键字段映射**：
> - `title` → 视频标题
> - `uploader` → 作者
> - `duration` → 时长（秒）
> - `like_count` / `comment_count` / `repost_count` → 互动数据
> - `subtitles` → 字幕信息（通常为空，需走 ASR）

> ⚠️ **yt-dlp 失败时**（返回非零退出码、JSON 解析失败、或超时 15 秒），**立即降级到 browser_use 方式一**。

---

### 方式一至三（browser_use 降级方案）：

> 仅当 yt-dlp 失败时才执行以下步骤。

## Step 1B：Agent 通过 browser_use 获取数据

### 1.1 打开页面

```
browser_use(action="open_tab", url="https://www.douyin.com/video/7631434873172987176")
```

> 如果是短链接（`v.douyin.com`），直接打开即可，浏览器会自动跳转到标准链接。
> 如果是精选页链接（含 `modal_id=`），先提取 modal_id，拼接为 `https://www.douyin.com/video/{modal_id}` 再打开。

### 1.2 等待页面加载

```
browser_use(action="wait_for", timeMs=5000)
```

> 等待视频播放器加载和 API 请求完成。抖音页面通常需要 3-5 秒加载。

---

> ⛔ **强制执行清单（必须按此顺序逐项完成，不可跳过任何一项）**：
>
> 1. ✅ `open_tab` 打开 URL
> 2. ✅ `wait_for(5000)` 等待加载
> 3. ✅ **`scrollBy(0, 300)` + `wait(1000)` + `scrollBy(0, -100)` + `wait(2000)`**（防反爬滚动）
> 4. ✅ 方式一：RENDER_DATA（最多尝试 2 次）
> 5. ✅ 方式二：Performance API + 详情 API XHR（最多尝试 2 次）
> 6. ✅ 方式三：DOM 提取（1 次）
> 7. 🔻 全部失败 → 降级 CDP
>
> **第 3 步（滚动）未执行时，禁止进入第 4-6 步。第 4 步失败后，禁止跳过第 5 步直接降级。**

---

### 1.3 模拟用户行为（防反爬）

> ⛔ **此步骤必须执行，不可跳过或省略**。抖音前端 JS 会检测用户交互事件，只有检测到真人行为（滚动/点击等）后才会激活并注入视频数据（RENDER_DATA）和触发 CDN 请求。
> **如果跳过此步骤，§1.4 的所有提取方式都将返回空数据，导致死循环。**

```
browser_use(action="evaluate", fn="window.scrollBy(0, 300)")
browser_use(action="wait_for", timeMs=1000)
browser_use(action="evaluate", fn="window.scrollBy(0, -100)")
browser_use(action="wait_for", timeMs=2000)
```

> 滚动后需要等待 2 秒让抖音前端完成数据注入和 CDN 请求触发。

### 1.4 获取视频元数据和直链

> ⚠️ **获取策略**：按以下优先级依次尝试，成功即停止。每种方式各有优劣，必须按顺序尝试。

#### 方式一（推荐）：从 RENDER_DATA 全局变量提取

抖音 SSR 页面会将视频完整数据注入到 `window.RENDER_DATA` 或 `window.__INITIAL_STATE__` 中，**无需额外网络请求，最稳定**：

```javascript
browser_use(action="evaluate", fn="(() => { try { const rd = window.RENDER_DATA || window.__RENDER_DATA__; if (rd) { const keys = Object.keys(rd); for (const k of keys) { const val = typeof rd[k] === 'string' ? JSON.parse(decodeURIComponent(rd[k])) : rd[k]; if (val?.awemeDetail || val?.aweme) { const d = val.awemeDetail || val.aweme; return JSON.stringify({ title: d.desc, author: d.author?.nickname, play_url: d.video?.play_addr?.url_list?.[0], download_url: d.video?.download_addr?.url_list?.[0], subtitle_infos: d.video?.subtitle_infos, duration: d.video?.duration, statistics: d.statistics }); } } } return JSON.stringify({error: 'RENDER_DATA not found'}); } catch(e) { return JSON.stringify({error: e.message}); } })()")
```

> **注意**：RENDER_DATA 中的值通常是 URL 编码的 JSON 字符串，需要 `decodeURIComponent` 后再 `JSON.parse`。

> ⛔ **重试限制**：方式一 evaluate 如果返回 `page is not ready`、`navigation_in_flight`、`request_failed` 等错误，**最多重试 1 次**（等待 5 秒后重试）。重试后仍失败 → **立即放弃方式一，切换到方式二**。禁止在方式一上循环重试超过 2 次总计。

#### 方式二：从 Performance API 拦截详情 API 响应

如果方式一失败，通过 Performance API 找到详情 API URL，然后用 `XMLHttpRequest`（而非 `fetch`）重新请求：

```javascript
browser_use(action="evaluate", fn="JSON.stringify(performance.getEntriesByType('resource').filter(e => e.name.includes('douyinvod.com') || e.name.includes('aweme/v1/web/aweme/detail')).map(e => ({name: e.name, type: e.initiatorType})))")
```

从结果中找到详情 API URL 后，**用 XMLHttpRequest 同步请求**（避免 fetch 的 CORS 问题）：

```javascript
browser_use(action="evaluate", fn="(() => { const url = '找到的详情API_URL'; const xhr = new XMLHttpRequest(); xhr.open('GET', url, false); xhr.withCredentials = true; xhr.send(); if (xhr.status === 200) { const d = JSON.parse(xhr.responseText); const detail = d.aweme_detail || d.aweme_details?.[0]; return JSON.stringify({ title: detail?.desc, author: detail?.author?.nickname, play_url: detail?.video?.play_addr?.url_list?.[0], download_url: detail?.video?.download_addr?.url_list?.[0], subtitle_infos: detail?.video?.subtitle_infos, duration: detail?.video?.duration, statistics: detail?.statistics }); } return JSON.stringify({error: 'XHR failed: ' + xhr.status}); })()")
```

> ⚠️ **关键区别**：使用 `XMLHttpRequest` 而非 `fetch`，设置 `withCredentials=true`，这样浏览器会自动携带 cookie，避免签名验证和 CORS 问题。

#### 方式三（兜底）：从 DOM 提取基本信息 + Performance API 获取直链

当方式一和方式二都失败时：

```javascript
// 从 DOM 提取标题、作者、互动数据
browser_use(action="evaluate", fn="JSON.stringify({ title: document.querySelector('h1')?.textContent || document.querySelector('[data-e2e=\"video-desc\"]')?.textContent || document.querySelector('.video-info-detail')?.textContent, author: document.querySelector('[data-e2e=\"video-author-nickname\"]')?.textContent || document.querySelector('.author-card-user-name')?.textContent, likes: document.querySelector('[data-e2e=\"digg-count\"]')?.textContent, comments: document.querySelector('[data-e2e=\"comment-count\"]')?.textContent, collects: document.querySelector('[data-e2e=\"collect-count\"]')?.textContent, shares: document.querySelector('[data-e2e=\"share-count\"]')?.textContent })")
```

> DOM 中的互动数据可能显示为"1.2w"格式，Agent 需要自行转换为数字（万=×10000）。

**直链**从 Performance API 的 `douyinvod.com` 资源中获取（参见下方 DASH 分离处理）。

### 1.5 DASH 音视频分离处理

从 Performance API 获取到的 `douyinvod.com` URL 可能是 DASH 分离的轨道：

| URL 特征 | 类型 | 说明 |
|----------|------|------|
| 包含 `media-video-avc1` | **纯视频轨**（无声音） | 下载后 ffmpeg 无法提取音频 |
| 包含 `media-audio-und-mp4a` | **纯音频轨**（无画面） | 可直接用于 ASR 转录，使用 `--audio-url` |
| 不含以上关键词的 `douyinvod.com` URL | **合并流**（音视频一体） | 最理想，使用 `--play-url` |

**优先级**：
1. 详情 API / RENDER_DATA 中的 `play_addr`（通常是合并流）→ `--play-url`
2. Performance API 中的纯音频轨（`media-audio-und-mp4a`）→ `--audio-url`（DASH 场景最快路径）
3. Performance API 中不含 DASH 关键词的 `douyinvod.com` URL → `--play-url`
4. Performance API 中的纯视频轨 → **不要使用**（无法转录）

### 1.6 关闭页面并整理数据

> 数据提取完成后，关闭 browser_use 打开的抖音页面 tab：
```
browser_use(action="close_tab")
```

> ⚠️ **Step 1.4 返回的所有字段都必须保留**，分为两组用途：

**传给脚本的字段**（metadata-json 或命令行参数）：
- `play_url`：视频直链（合并流，`douyinvod.com` 开头）
- `audio_url`：音频轨直链（DASH 分离场景备选）
- `title`：视频标题
- `subtitle_infos`：字幕信息列表

**必须用于报告元数据表格的字段**（输出报告时**强制展示**）：
- `author`：作者昵称 → 报告中的"作者"
- `duration`：视频时长（毫秒，需转换为 mm:ss 格式）→ 报告中的"时长"
- `statistics.digg_count`：点赞数 → 报告中的"点赞"
- `statistics.comment_count`：评论数 → 报告中的"评论"
- `statistics.share_count`：转发/分享数 → 报告中的"转发"
- `statistics.collect_count`：收藏数 → 报告中的"收藏"

> ⚠️ 如果方式一/二获取到了 statistics 字段，必须全部展示在报告元数据表格中，不得省略。
> 如果只能通过 DOM（方式三）获取到互动数据，也要填入报告中。

---

**降级执行步骤**：

**执行命令**：

```
ask_human("⚠️ 需要通过 Chrome 浏览器提取抖音视频数据。即将弹出浏览器窗口，如果需要登录，请在窗口中完成登录操作。脚本会自动检测登录状态并提取数据。")
```

用户确认后执行：
```bash
python3 scripts/cdp_extract.py --url "<原始视频URL>"
```

> **说明**：脚本内部会自动检测登录状态。如果未登录，浏览器窗口会保持打开（最长 300 秒），等用户完成登录后自动提取数据。全程只需打开一次浏览器。

**处理返回结果**：

- `action: waiting_for_login` → 脚本正在等待用户登录，不要中断，等待最终结果
- `success: true` 且 `play_url` 不为空 → 使用 `play_url` + `metadata` + `subtitle_infos`，继续下方 Step 2（情况 A 或 B）
- `success: true` 但 `play_url` 为空，`audio_url` 不为空 → 使用 `audio_url` 走 `--audio-url` 路径（DASH 分离场景）
- `success: false` 且 `error` 为 `login_required`（超时未登录）→ `ask_human` 提示用户重新执行
- `success: false` → `ask_human` 告知用户具体原因

---

## Step 2：调用脚本处理

### 情况 A：拿到了视频直链

```bash
python3 scripts/cli.py extract-douyin \
  --play-url "https://v26-web.douyinvod.com/..."
```

### 情况 B：拿到了完整元数据（含字幕信息）

```bash
python3 scripts/cli.py extract-douyin \
  --metadata-json '{"title": "视频标题", "play_url": "https://...", "subtitle_infos": [...]}'
```

### 情况 C：有本地视频文件（无需浏览器）

```bash
python3 scripts/cli.py extract-douyin \
  --video-file /path/to/video.mp4
```

---

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--play-url` | 视频直链（**优先用详情 API 的 `play_addr` 合并流**，备选 Performance API 资源） | `https://v26-web.douyinvod.com/...` |
| `--audio-url` | 音频轨直链（DASH 分离场景，直接下载音频进行 ASR，更快） | `https://v26-web.douyinvod.com/.../media-audio-und-mp4a/...` |
| `--metadata-json` | 完整元数据 JSON（含 title/play_url/subtitle_infos） | `'{"title":"...", ...}'` |
| `--video-file` | 本地视频文件路径 | `/path/to/video.mp4` |
| `--no-transcript` | 跳过 ASR 转录 | — |
| `--extract-keyframes` | 提取关键帧截图（按 ASR 时间戳截帧） | — |
| `--output-dir` | 输出目录（默认 `~/.content-breakdown/output/douyin`） | 不传则使用默认路径 |

---

## 关键帧截图（可选功能）

> ⚠️ **触发条件**：仅当用户明确说出以下词语时才加 `--extract-keyframes` 参数，默认不执行：
> - "逐帧分析"、"关键帧"、"帧分析"、"截帧"、"每一帧"、"帧截图"

> ⚠️ **前置要求**：关键帧截图需要**视频文件**，因此：
> - **必须使用 `--play-url`**（下载完整视频）才能提取关键帧
> - `--audio-url` 只下载音频，**无法截帧**，不要与 `--extract-keyframes` 同时使用
> - 如果当前只有 DASH 音频轨 URL，需要先获取合并流的 `play_addr` 或视频轨 URL

**工作原理**：ASR 转录完成后，根据每句话的时间戳，用 ffmpeg 在对应时间点截取视频帧，生成图文对照的关键帧报告。

**使用示例**（用户要求关键帧分析时）：

```bash
python3 scripts/cli.py extract-douyin \
  --play-url "https://v26-web.douyinvod.com/..." \
  --extract-keyframes
```

**输出结果**：
- `keyframes`：关键帧列表，每项包含 `timestamp_str`（时间戳）、`transcript`（对应文案）、`screenshot`（截图路径）
- 截图保存在 `~/.content-breakdown/output/{video_stem}_keyframes/` 目录下

---

## 执行完成后

命令执行成功后，读取结果中的 `subtitle_text` 或 `transcript_text` 字段，**按 `references/output-format.md` 的格式输出给用户**。

如果有 `keyframes` 字段（用户要求了关键帧分析），额外输出关键帧时间轴：
```
🎞️ 关键帧时间轴：
[00:00] 文案内容 → 截图：/path/to/frame_001_0000.png
[00:03] 文案内容 → 截图：/path/to/frame_002_0003.png
...
```

---

## Pitfalls

### 短链解析必须用 mobile UA
桌面 UA 请求 `v.douyin.com` 短链可能不会正确跳转到包含视频 ID 的页面。使用 iPhone Safari UA 可稳定获取跳转链路：`v.douyin.com` → `iesdouyin.com/share/video/{VIDEO_ID}` → 从 URL 路径提取纯数字视频 ID。

### 下载 URL 有时效性
yt-dlp 返回的视频/音频下载 URL 包含过期时间戳（query 参数中的 `expire` 字段）。下载后应立即处理，不要隔太久再使用 URL。

### WebFetch 无法提取抖音页面
抖音页面是 JavaScript 动态渲染的 SPA，WebFetch 只能拿到静态 HTML 骨架，无法获取视频数据和文案内容。**必须使用 curl（解析短链）+ yt-dlp（提取元数据）方案。**

---

## 验证检查点

| 步骤 | 验证方式 |
|------|---------|
| 短链解析 | 确认最终 URL 包含纯数字视频 ID（通常 19 位） |
| 元数据提取 | yt-dlp JSON 输出中 `title` 和 `like_count` 不为空 |
| 视频下载 | 检查输出文件存在且大小 > 0 |
| 音频提取 | `ffprobe -show_format -show_streams <file>` 确认 sample_rate=16000, channels=1, codec=pcm_s16le |
| 转录结果 | 输出文本不为空，且内容语义连贯（非乱码） |

```bash
# 验证音频格式
ffprobe -show_format -show_streams ~/.content-breakdown/output/douyin_audio.wav 2>&1 | grep -E "sample_rate|channels|codec_name"
# 预期：sample_rate=16000, channels=1, codec_name=pcm_s16le
```

---

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Performance API 无视频 URL | 页面未完全加载，或视频未开始播放 | 增加等待时间到 8-10s，执行 `document.querySelector('video')?.play()` 触发播放 |
| 页面被重定向到首页 | 登录状态失效或触发反爬 | 提示用户在浏览器中重新登录抖音 |
| 视频直链下载 403 | 直链过期（通常 2 小时有效期） | 重新通过 browser_use 获取新的直链 |
| 详情 API 返回空数据 | Cookie 失效或视频被删除 | 确认视频链接可正常访问 |
| **音频提取失败（视频不包含音频流）** | 下载的是 DASH 纯视频轨（`media-video-avc1`），不含音频 | 从 Performance API 中筛选音频轨 URL（包含 `media-audio-und-mp4a`），使用 `--audio-url` 参数 |

## 预计耗时

- 有 API 字幕：~5s（browser_use 获取 + 字幕解析）
- 无字幕需 ASR：~15-20s（browser_use 获取 + 视频下载 + 转录）
- 关键帧截图：在 ASR 基础上额外 +5-10s（每帧约 0.5s）
