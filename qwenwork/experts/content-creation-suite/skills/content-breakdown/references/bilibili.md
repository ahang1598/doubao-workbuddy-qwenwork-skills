# B 站视频爆款拆解

**触发词**：提取B站视频、获取B站字幕、B站视频转录、bilibili 视频内容

## 字幕提取策略（自动降级）

> ⚠️ **无 API 字幕时必须继续 ASR 转录，不得直接告诉用户"该视频没有字幕"后停止。** 只有在加了 `--skip-transcript` 参数时才允许跳过。

1. **API 字幕**：AI 字幕 / UP 主上传字幕，最快，无需下载视频
2. **必剪云端 ASR**：无字幕时**必须**触发，下载最低画质视频提取音频

---

## Step 1：获取视频数据

> ⚠️ **优先方式**：先用 B 站公开 API（无需登录、无需 Cookie）获取视频信息 + 360P 视频流 + ASR 转录，仅在需要字幕时才降级到 browser_use 获取 Cookie。

### 方式零（推荐优先）：B 站公开 API + --no-cookie 模式

B 站的 `View API` 和 `Player API` 在无登录态时也可返回数据：
- **View API**（`/x/web-interface/view`）：获取标题、UP 主、时长、cid、播放量、点赞、投币等 —— **无需 Cookie**
- **Player API**（`/x/player/playurl`）：获取 360P 视频直链 —— **无需 Cookie**（有 Cookie 可获取更高画质）
- **字幕 API**（`/x/player/v2`）：获取 AI 字幕 —— **需要 Cookie**（无 Cookie 时返回空列表）

```bash
# 直接使用 --no-cookie 模式，脚本内部调用公开 API
python3 scripts/cli.py extract-bilibili \
  --url "https://www.bilibili.com/video/BV1GJ411x7h7" \
  --no-cookie \
  --output-dir ~/.content-breakdown/output
```

> **--no-cookie 模式的工作流程**：
> 1. 调用 View API 获取视频基本信息（标题、UP 主、时长、互动数据）—— 无需 Cookie ✅
> 2. 跳过字幕 API（因为无 Cookie 拿不到字幕）
> 3. 调用 Player API 获取 360P 视频直链 —— 无需 Cookie ✅
> 4. 下载视频 → ffmpeg 提取音频 → 必剪云端 ASR 转录 —— 无需 Cookie ✅

> ⚠️ **什么时候需要 browser_use 获取 Cookie**：仅当用户明确要求获取 AI 字幕（跳过 ASR）、或需要更高画质（720P+）时，才走 browser_use 获取 Cookie 路径。

> ⚠️ **--no-cookie 失败时**（API 返回错误、视频被删除、或地区限制），**降级到 browser_use 方式**。

---

### 方式一（browser_use 降级方案，仅需要字幕时使用）：

> 仅当 --no-cookie 模式失败、或用户明确要求获取字幕时才执行以下步骤。

## Step 1B：Agent 通过 browser_use 获取 B 站 Cookie

B 站的字幕 API 和视频直链 API 都需要登录态 Cookie，Agent 通过 browser_use 获取：

---
> ⛔ **强制执行清单（必须按此顺序逐项完成，不可跳过任何一项）**：
>
> 1. ✅ `open_tab` 打开 B 站首页
> 2. ✅ `wait_for(3000)` 等待加载
> 3. ✅ 检查登录状态（Cookie 中是否有 `DedeUserID`）
> 4. ✅ 未登录 → 走 login-wall 流程引导用户登录，**不得直接降级**
> 5. ✅ 已登录 → 提取完整 Cookie 字符串
> 6. ✅ 关闭 browser_use 页面：`browser_use(action="close_tab")`
> 7. 🔻 browser_use 本身不可用（启动失败/连接中断/Target closed）→ 降级 CDP
>
> **第 3 步未执行时，禁止进入第 5 步。未登录时必须先引导登录（第 4 步），禁止跳过直接降级。仅 browser_use 本身无法工作时才允许降级到 CDP。**
---

### 1.1 打开 B 站页面

```
browser_use(action="open_tab", url="https://www.bilibili.com")
```

### 1.2 等待页面加载

```
browser_use(action="wait_for", timeMs=3000)
```

### 1.3 检查登录状态

```javascript
browser_use(action="evaluate", fn="JSON.stringify({isLogin: document.cookie.includes('DedeUserID'), avatar: document.querySelector('.header-avatar-wrap img')?.src || ''})")
```

> 如果 `isLogin` 为 false，说明未登录，执行 SKILL.md 中的「登录墙处理流程」：通过 ask_human 提示用户在浏览器窗口中登录 B 站，等待确认后重试。

### 1.4 提取 Cookie

```javascript
browser_use(action="evaluate", fn="document.cookie")
```

> 提取完整的 Cookie 字符串，传给脚本使用。关键 Cookie 字段：`SESSDATA`、`bili_jct`、`DedeUserID`。

---

### 1.5 browser_use 失败时降级到 CDP 提取

> ⚠️ **降级触发条件**（满足**任一**即判定 browser_use 失败，**立即降级**，禁止无限重试）：
>
> | 信号 | 判定方式 |
> |------|---------|
> | 页面未就绪 | `evaluate` 返回含 `page is not ready`、`navigation_in_flight`、`Target closed` 等错误 |
> | 验证码/空白页 | 截图/snapshot 显示验证码拦截页或完全空白 |
> | browser_use 连接失败 | 浏览器启动失败或连接中断 |
>
> ⚠️ **注意区分**：如果 browser_use 本身可用，只是 Cookie 中不含 `SESSDATA`（未登录），应先走 `references/login-wall.md` 流程引导登录，**不要直接降级**。仅当 browser_use 本身无法工作时才降级到 CDP。

**降级执行命令**：

```bash
python3 scripts/cdp_extract.py --url "<B站视频URL>"
```

**处理返回结果**：

- `success: true` 且 `cookie_string` 不为空 → 使用返回的 `cookie_string` + `bvid` 直接继续下方 Step 2。
  脚本内部会自动处理：有字幕则用字幕，无字幕则降级 ASR 转录。
- `success: true` 但 `login_status` 为 `not_logged_in` → **仍可继续执行 Step 2**（脚本会用公开 API 获取元数据，字幕 API 失败时自动降级 ASR）。
  如果脚本返回"视频下载失败"或"Cookie 失效"错误，再引导登录：
  ```
  ask_human("⚠️ B站字幕获取失败，需要登录。即将弹出 Chrome 窗口，请登录B站后回复「已登录」。")
  ```
  用户确认后重新执行 `python3 scripts/cdp_extract.py --url "<URL>"`
- `success: false` → `ask_human` 告知用户具体原因

> **说明**：B站大部分功能不强制登录（公开 API + 低画质视频下载可用），登录主要影响字幕获取。
> `cookie_string` 格式为 `"SESSDATA=xxx; bili_jct=xxx; ..."`，可直接传给 `--cookie` 参数。
> 登录状态持久化到 `~/.content-breakdown/chrome-profile-uc/`。

---

## Step 2：调用脚本处理

### 情况 A：--no-cookie 模式（推荐，无需浏览器）

```bash
python3 scripts/cli.py extract-bilibili \
  --url "https://www.bilibili.com/video/BV1GJ411x7h7" \
  --no-cookie \
  --output-dir ~/.content-breakdown/output
```

或使用 BV 号：

```bash
python3 scripts/cli.py extract-bilibili \
  --bvid "BV1GJ411x7h7" \
  --no-cookie \
  --output-dir ~/.content-breakdown/output
```

### 情况 B：有 Cookie（需要字幕时）

将获取到的 Cookie 传给脚本，脚本内部会：
1. 调用 B 站公开 API 获取视频基本信息（标题、UP 主、播放量等）
2. 带 Cookie 请求字幕 API，检查是否有 AI 字幕或 UP 主上传字幕
3. **有字幕** → 下载字幕 JSON → 解析文本 → 生成报告
4. **无字幕** → 带 Cookie 获取视频直链（更高画质）→ 下载视频 → 提取音频 → 必剪云端 ASR 转录

```bash
python3 scripts/cli.py extract-bilibili \
  --url "https://www.bilibili.com/video/BV1GJ411x7h7" \
  --cookie "SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx" \
  --output-dir ~/.content-breakdown/output
```

---

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--url` | B 站视频链接（与 --bvid 二选一） | `https://www.bilibili.com/video/BV1xxx` |
| `--bvid` | B 站视频 BV 号（与 --url 二选一） | `BV1GJ411x7h7` |
| `--no-cookie` | 无 Cookie 模式：跳过字幕 API，直接通过公开 API 下载视频走 ASR（360P） | 无需参数值 |
| `--cookie` | B 站登录 Cookie（从 browser_use 获取，仅需要字幕时使用） | `"SESSDATA=xxx; bili_jct=xxx"` |
| `--skip-transcript` | 无字幕时跳过 ASR 转录 | — |
| `--extract-keyframes` | 提取关键帧截图 | — |
| `--output-dir` | 输出目录 | `~/.content-breakdown/output` |

---

## 关键帧截图（可选功能）

> ⚠️ **触发条件**：仅当用户明确说出以下词语时才加 `--extract-keyframes` 参数，默认不执行：
> - "逐帧分析"、"关键帧"、"帧分析"、"截帧"、"每一帧"、"帧截图"

**使用示例**（用户要求关键帧分析时）：

```bash
python3 scripts/cli.py extract-bilibili \
  --url "https://www.bilibili.com/video/BV1xxx" \
  --cookie "SESSDATA=xxx; bili_jct=xxx" \
  --extract-keyframes \
  --output-dir ~/.content-breakdown/output
```

**输出结果**：
- `keyframes`：关键帧列表，每项包含 `timestamp_str`（时间戳）、`transcript`（对应文案）、`screenshot`（截图路径）
- 截图保存在 `~/.content-breakdown/output/{bvid}_keyframes/` 目录下

**注意**：
- 关键帧截图依赖 ASR 转录结果，`--skip-transcript` 与 `--extract-keyframes` 不可同时使用
- 需要 ffmpeg 已安装

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

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Cookie 中无 SESSDATA | 未登录 B 站 | 提示用户在 browser_use 浏览器中登录 B 站 |
| 字幕 API 返回空 | 视频无字幕（正常） | 脚本自动降级到 ASR 转录 |
| 视频直链 403 | Cookie 过期或 Referer 不对 | 重新通过 browser_use 获取 Cookie |
| 获取 BV 号失败 | URL 格式不标准 | 确认 URL 包含 `/video/BVxxx` |

## 预计耗时

有字幕 ~3-5s，无字幕 ~15-25s，关键帧截图额外 +5-10s
