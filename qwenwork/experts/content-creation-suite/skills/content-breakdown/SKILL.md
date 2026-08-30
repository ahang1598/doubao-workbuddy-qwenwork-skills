---
name: content-breakdown
description: |
  爆款拆解技能：从抖音、小红书、微信公众号、B站、小宇宙、百家号、微博、今日头条拆解内容（字幕/转录/正文/图片OCR），也支持本地视频/音频文件转录。
  当用户说"拆解视频内容"、"获取字幕"、"拆解笔记图片"、"获取笔记正文"、"识别图片文字"、
  "拆解公众号文章"、"拆解B站视频"、"拆解播客内容"、"转录这个视频文件"、"提取本地视频内容"、
  "拆解百家号文章"、"提取微博内容"、"拆解头条文章"时触发。
  依赖：Python 3.10+、requests
  
  【不适用场景】
  - 关键词搜索拆解（如"搜爆款"、"找爆款"、"搜一下xx的爆款"、"竞品分析"、"搜热门"）→ 请使用「内容雷达 content-radar」技能
  - 通用网页搜索 → 使用 web_search
  - 内容发布 → 使用发布技能
  - 只想清洗 ASR 逐字稿 → 走逐字稿润色技能
---

# 爆款拆解技能 Content Breakdown

**架构**：优先使用 `curl` / `yt-dlp` / HTTP API 直接获取数据（无需浏览器），仅在 curl 失败时降级到 Agent（browser_use）获取页面数据。Python 脚本（`scripts/cli.py`）负责下载/转录/OCR。脚本不含任何浏览器操作。

---

## 平台路由

> ⛔ **强制规则**：收到 URL 后，识别平台，**必须先 `read_file` 读取对应 reference 文件再执行**。
> **禁止凭记忆执行任何平台的提取流程**。每次提取都必须重新读取文档，无论之前是否执行过同平台的提取。
> 未读取 reference 文件就开始操作视为严重错误。

| 平台识别 | 命令 | 优先方式（curl/API） | 降级方式（browser_use） | 必须先读取 |
|---------|------|-----------|---------|---------|
| `douyin.com` / `v.douyin.com` | `extract-douyin` | `yt-dlp` 获取元数据 + 视频直链 | `browser_use` 获取直链 | **`references/douyin.md`** |
| `xiaohongshu.com` / `xhslink.com` | `extract-xhs` | `curl` + Desktop UA 获取 `__INITIAL_STATE__` | `browser_use` 获取正文+图片 | **`references/xhs.md`** |
| `bilibili.com` / `b23.tv` / BV号 | `extract-bilibili` | B 站公开 API（`--no-cookie` 模式，360P + ASR） | `browser_use` 获取 Cookie + 字幕 API | **`references/bilibili.md`** |
| `mp.weixin.qq.com` | `extract-wechat` | `curl` + Desktop UA 获取 SSR HTML | 无需降级 | **`references/wechat.md`** |
| `xiaoyuzhoufm.com` | `extract-xiaoyuzhou` | `curl` 提取音频直链 | 无需降级 | **`references/xiaoyuzhou.md`** |
| `baijiahao.baidu.com` / `mbd.baidu.com` | `extract-baijiahao` | `curl` + Desktop UA 获取页面 HTML | `browser_use` 获取 HTML + 脚本解析 | **`references/baijiahao.md`** |
| `weibo.com` / `m.weibo.cn` | `extract-weibo` | 移动端 API（m.weibo.cn） | 无需降级 | **`references/weibo.md`** |
| `toutiao.com` / `m.toutiao.com` | `extract-toutiao` | 移动端 API（`m.toutiao.com/i{id}/info/`）返回 JSON | `browser_use` 获取 HTML + 脚本解析 | **`references/toutiao.md`** |

不支持的平台：单条时提示不支持并列出支持列表；批量时跳过（`⏭️ 跳过：{链接} — 暂不支持`），不中断整体流程。

## 各平台关键注意事项

| 平台 | 关键注意事项 |
|------|------------|
| 抖音 | 优先用 `yt-dlp --dump-json` 获取元数据，失败再降级 browser_use；无 API 字幕时**必须**继续 ASR 转录 |
| 小红书 | 优先用 `curl` + Desktop UA 从 SSR HTML 提取 `__INITIAL_STATE__`；图文笔记需执行**两条命令**（提取 + OCR）；`image_files` 不为空即为图文 |
| B 站 | 优先用 `--no-cookie` 模式（公开 API + 360P + ASR），无需浏览器；需要字幕时再用 `--cookie` + browser_use 获取 Cookie |
| 微信公众号 | `curl` + Desktop UA 即可获取 SSR HTML（已验证），**不得自行添加 `--no-ocr`** |
| 小宇宙 | 默认下载音频并转录 |
| 百家号 | 优先尝试 `curl` + Desktop UA，失败再降级 browser_use；**不得自行添加 `--no-ocr`** |
| 微博 | 使用移动端 API（m.weibo.cn），自动展开长文；**不得自行添加 `--no-ocr`** |
| 今日头条 | 优先通过移动端 API（`m.toutiao.com/i{id}/info/`）获取 JSON 数据，失败再降级 browser_use；图片 URL 可能缺少协议前缀，脚本自动补全 |

---

## 提取流程

> ⛔ **以下 6 步必须严格按顺序逐步执行，禁止跳过任何一步，禁止合并步骤，禁止在未完成前一步时开始下一步。**

1. ⛔ **读取文档**：`read_file` 读取对应平台的 `references/*.md`。**此步骤不可跳过**，未读取就开始操作视为严重错误。
2. **获取数据**：按文档 Step 1 的方式零（curl/yt-dlp/API）优先获取数据。**优先方式失败时**才降级到 browser_use，browser_use 失败再降级到 CDP。**必须严格按照 reference 文件中的步骤顺序执行，包括滚动防反爬等所有前置操作。**
3. **脚本处理**：按文档 Step 2 调用 `python3 scripts/cli.py extract-{平台}` 处理
4. **格式化输出**：读取 `references/output-format.md`，按**三部分格式**输出：
   - **📋 内容元数据**：标题、作者、平台、时长、互动数据等
   - **📄 提取内容原文**：转录文本 / 正文 / OCR 文本
   - ⛔ **📊 内容分析**：**此部分必须包含且不可省略**，需输出核心主题、主要观点、适用场景、内容结构分析。缺少此部分视为报告不完整。
5. **保存报告**：⛔ 报告文件中**三部分必须全部写入**（📋 + 📄 + 📊），缺少任何一部分禁止保存。写入路径：`~/.content-breakdown/output/{平台}_{标题摘要}_{YYYYMMDD}.md`
6. ⛔ **进入后续流程**：**保存报告 ≠ 任务完成！保存报告后绝对不得结束任务**，必须继续执行下方「后续流程」章节。在后续流程全部完成前结束任务视为严重错误。

---

## 批量提取模式

≥ 2 条链接时进入批量模式。

| 行为 | 单条模式 | 批量模式 |
|------|---------|---------|
| 对话展示原文 | ✅ 完整展示 | ❌ 只展示元数据+分析摘要 |
| 口播脚本生成 | ✅ 自动判断+use_skill | ❌ 汇总后由用户选择 |
| 分镜/风格分析 | ✅ 逐步询问 | ❌ 汇总后由用户选择 |
| 汇总报告 | ❌ | ✅ 自动生成 |

⛔ 每条视频类内容（转录 ≥ 100 字）**必须**判断是否口播并标记（✅/❌），不可跳过此标记步骤。

**口播判断标准**（满足 2 条及以上即为口播）：
1. 有持续的人声叙述（连贯完整句子为主）
2. 有明确的表达主题（围绕一个中心论点展开）
3. 有结构化的信息传递（有开头引入、中间展开、结尾总结）
4. **不属于**：纯音乐/MV、游戏实况、Vlog 日常、影视剪辑、搞笑段子集锦

批量完成后生成汇总报告（**必须读取** `references/batch-report-template.md`），然后询问：

```
ask_human("📊 汇总拆解报告已生成。共 {M} 条成功，{K} 条跳过，{P} 条口播。\n\n(A) 分镜/制作分析（输入序号）\n(B) 批量生成视频脚本（共 {P} 条口播）\n(C) 选择特定内容生成视频脚本（输入序号）\n(D) 结束")
```

- A → 分镜分析（需先提取关键帧）
- B → 逐条通过 use_skill 调用 video-script-generator（失败时降级到 `references/oral-template.md`）
- C → 指定内容通过 use_skill 调用 video-script-generator
- D → 结束

> 选 A/B/C 执行完后回到此询问继续。

---

## 后续流程（单条模式专用）

> ⛔ **保存报告 ≠ 任务完成**：单条提取保存报告后**必须执行以下流程，全部完成后才允许结束任务**。
> 在步骤一和步骤二全部完成之前结束任务视为严重错误。批量模式跳过此章节。

### 步骤一：分镜分析（视频类内容专用）

**触发条件**：视频类内容（有转录/音频）。图文/文章类跳过此步骤，直接进入步骤二。

```
ask_human("📝 爆款拆解报告已生成。是否需要进行分镜分析？（需提取关键帧）\n\n(A) 进行分镜分析\n(B) 不需要，跳过")
```

- A → 执行以下**完整分镜分析流程**：
  1. 使用 `--extract-keyframes` 提取关键帧
  2. ⛔ **必须基于关键帧生成完整的分镜分析报告**，不能只列出时间轴/截图列表。报告必须包含：
     - **分镜结构分析**：各段落的镜头构成、转场方式
     - **画面风格分析**：色调、构图、字幕使用、品牌元素
     - **剪辑节奏分析**：节奏变化、时长分布、高潮/缓冲交替
  3. 保存为 `~/.content-breakdown/output/{平台}_分镜分析_{标题摘要}_{YYYYMMDD}.md`
  > ⛔ 只提取关键帧但不生成深度分析报告视为未完成。
- B → 跳过，进入步骤二

> ⛔ 分镜分析完成（或用户选择跳过）后，**必须继续执行步骤二**，禁止在此结束任务。无论用户选择 A 还是 B，步骤二都必须执行。

### 步骤二：视频脚本生成

**触发条件**：视频类内容且转录 ≥ 100 字。图文/文章类跳过此步骤，直接结束。

**内部判断标准**（后台判断，不在对话中向用户展示判断过程）：
满足 2 条及以上即判定为适合生成脚本：
1. 有持续的人声叙述（连贯完整句子为主）
2. 有明确的表达主题（围绕一个中心论点展开）
3. 有结构化的信息传递（有开头引入、中间展开、结尾总结）
4. **不属于**：纯音乐/MV、游戏实况、Vlog 日常、影视剪辑、搞笑段子集锦

**判断结果**（对用户透明，不输出判断过程）：
- 适合生成脚本 → 直接询问
- 不适合 → 直接结束任务（不需要告诉用户"不是口播所以跳过"）

**询问**：

```
ask_human("是否调用「视频脚本生成器」生成新脚本？\n\n(A) 生成视频脚本\n(B) 不需要，结束")
```

- A → 通过 `use_skill(name="video-script-generator")` 调用。如果技能不在本地，先 `search_skills` 搜索。调用前确保对话上下文已有提取报告（📋 元数据 + 📄 原文 + 📊 分析）。
- B → 结束任务

**降级**（use_skill 失败时）：`ask_human` 告知用户，询问是否降级到 `references/oral-template.md` 本地生成。仅降级路径才允许使用该模板。

---

## 核心约束

> ⛔ 以下规则优先级最高，**不可违反，不可以任何理由绕过**：

- ⛔ **必须先读取 reference 文件**：每次提取前必须 `read_file` 读取对应平台的 reference 文件，禁止凭记忆执行
- ⛔ **curl/yt-dlp 优先，browser_use 降级**：抖音优先用 `yt-dlp`，小红书/百家号/头条优先用 `curl`，B 站优先用 `--no-cookie` 模式。**优先方式失败后才降级到 browser_use**，browser_use 必须按 reference 文件中的方式一→方式二→方式三全部尝试失败后才允许降级到 `scripts/cdp_extract.py`（详见：`douyin.md` §1.4、`bilibili.md` §1.5、`xhs.md` §1.6）。跳过任何一种方式直接降级视为严重错误。
- ⛔ **Whisper 必须使用 medium 模型**：base 模型（74M）在有背景音乐、方言、快速口语的视频中输出几乎全是乱码。medium（1.5B，约 1.42GB）是中文转录的最低可用模型。脚本默认已设为 medium，**禁止改回 base**。
- ⛔ **browser_use 必须执行滚动防反爬**：进入页面后必须先执行滚动操作（scrollBy + wait），未执行滚动就开始提取数据视为严重错误
- ⛔ **禁止截图代替下载**：图片必须下载原图后 OCR
- ⛔ **禁止猜测参数**：不确定时必须查阅对应 reference 文件
- ⛔ **禁止跳过输出格式**：必须按三部分格式输出（📋 元数据 + 📄 原文 + 📊 分析），缺少任何一部分禁止保存
- ⛔ **禁止编造数据**：互动数据必须从页面提取，无法获取时标注"未获取"而非编造
- ⛔ **禁止在脚本中操作浏览器**：脚本只处理已获取的数据
- ⛔ **报告必须保存文件**：每次提取都必须生成 Markdown 文件并写入磁盘
- ⛔ **保存报告后必须继续后续流程**：单条模式保存报告后必须执行步骤一（分镜询问）和步骤二（口播判断），在后续流程全部完成前结束任务视为严重错误
- ⛔ **browser_use 提取完成后必须关闭页面**：执行 `browser_use(action="close_tab")` 关闭打开的页面
- ⛔ **登录墙处理**：检测到登录墙时必须读取 `references/login-wall.md` 并按其流程执行
- ⛔ **脚本失败处理**：`cli.py` 返回失败时查看 error 字段，按下方异常处理表操作，最多重试 2 次

---

## 异常处理

| 异常 | 处理 |
|------|------|
| browser_use 页面重定向 | 提示用户登录 |
| browser_use evaluate 返回 `page is not ready` / `navigation_in_flight` | **不要立即降级**。等待 5 秒后重试**当前方式**，但**每种方式最多重试 1 次**（即最多 2 次尝试）。重试后仍失败 → 立即切换到下一种方式（方式一→方式二→方式三）。禁止在同一种方式上循环重试超过 2 次。三种方式全部失败后才降级到 CDP |
| browser_use 返回 `Target closed` / 页面崩溃 | 此时浏览器已不可用，直接降级到 `python3 scripts/cdp_extract.py --url <URL>` |
| Performance API 无直链 | 增加等待时间，多次滚动；仍失败则继续尝试 DOM 提取（方式三）。方式一二三全部失败后降级到 cdp_extract.py |
| cdp_extract.py 返回 `login_required` | `ask_human` 引导用户登录，登录后重试 |
| cdp_extract.py 返回 `data_completeness: partial` + `login_status: not_logged_in`（抖音/小红书） | ⛔ **绝对禁止使用 partial 数据继续执行，无任何例外**。不得以"简单任务"、"只需转录"等理由绕过。必须立即执行 `ask_human` 引导用户登录，登录后重新提取完整数据。违反此规则视为严重错误。 |
| cdp_extract.py 返回 `data_completeness: partial` + `login_status: logged_in`（抖音） | 已登录但仍只有 audio_url（DASH 分离场景），此时可以使用 `--audio-url` 继续转录。报告中元数据用脚本返回的 metadata 填充（可能不完整）。 |
| cdp_extract.py 返回 `Chrome not found` | Chrome 未安装，`ask_human` 提示用户安装：https://www.google.com/chrome/ |
| cdp_extract.py 返回 `chromedriver_blocked` | 执行返回的 `fix_command`（`codesign --force --sign - <path>`），然后重试 |
| ASR 失败 | 自动降级到 Whisper |
| 图片下载失败 | 记录失败 URL，继续处理其他图片 |
| 脚本返回"不包含音频流" | browser_use 获取音频轨 URL，用 `--audio-url` 重新调用 |
| "视频下载失败"/"链接过期" | browser_use 重新获取直链再调用 |
| 其他错误 | `ask_human` 告知用户 |

**对用户翻译技术错误**：`login_required` → "需要先登录"；`TimeoutError` → "网络超时"；Python traceback → "处理工具出错了"。

---

## 前置条件与依赖

browser_use Profile 自动持久化登录状态，首次使用需登录一次。

> ⛔ 在**首次调用 `cli.py` 前必须执行依赖检查**。如果本次会话中已检查过则可跳过，但首次调用时不可跳过。

```bash
# 依赖检查
python3 -c "import requests; print('✅ requests')" && \
python3 -c "import imageio_ffmpeg; print('✅ imageio-ffmpeg')" && echo "通过"

# 安装（如缺失）
pip install requests imageio-ffmpeg
pip install yt-dlp                # 抖音视频提取（优先方式）
pip install chromedriver-autoinstaller selenium  # CDP 降级方案(跨平台自动管理 ChromeDriver)
pip install rapidocr-onnxruntime    # OCR（推荐）
pip install openai-whisper          # Whisper 转录（可选兜底）
```

---

## 资源索引

| 文件 | 用途 | 何时读取 |
|------|------|---------|
| `references/douyin.md` | 抖音提取流程 | 识别到抖音链接时 |
| `references/xhs.md` | 小红书提取流程 | 识别到小红书链接时 |
| `references/bilibili.md` | B站提取流程 | 识别到B站链接时 |
| `references/wechat.md` | 微信公众号提取 | 识别到微信链接时 |
| `references/xiaoyuzhou.md` | 小宇宙提取 | 识别到小宇宙链接时 |
| `references/baijiahao.md` | 百家号提取流程 | 识别到百家号链接时 |
| `references/weibo.md` | 微博提取流程 | 识别到微博链接时 |
| `references/toutiao.md` | 今日头条提取流程 | 识别到头条链接时 |
| `references/output-format.md` | 输出格式规范 | 提取成功后 |
| `references/oral-template.md` | 口播模板（降级用） | use_skill 失败时 |
| `references/batch-report-template.md` | 汇总报告模板 | 批量提取完成后 |
| `references/login-wall.md` | 登录墙处理流程 | 检测到未登录时 |
