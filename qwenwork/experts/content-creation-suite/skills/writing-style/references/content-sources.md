# 内容提取能力矩阵与子技能调用说明

本文件说明如何从 6 种输入来源中提取用户原创内容的纯文本，供风格分析使用。

---

## 能力矩阵

| 来源类型 | 识别方式 | 提取工具 | 输出 |
|----------|----------|----------|------|
| 纯文本 | 用户在对话中直接粘贴 | 无需工具 | 直接使用 |
| Word (.docx) | 文件扩展名 `.docx` | `parse_file(file_path)` | 提取正文文本 |
| PDF | 文件扩展名 `.pdf` | `parse_file(file_path)` | 提取正文文本 |
| 图片（含文字） | 文件扩展名 `.png/.jpg/.jpeg/.webp` | `understand_media(media_path, question="提取图片中的所有文字内容")` | OCR 文字 |
| 微信公众号链接 | URL 包含 `mp.weixin.qq.com` | `read_url(url)` | 提取文章正文 |
| 小红书链接 | URL 包含 `xiaohongshu.com` 或 `xhslink.com` | **xhs-content-reader (CDP)** | 笔记标题+正文+标签+评论+互动数据 |

---

## 各来源详细处理

### 1. 纯文本

用户直接在对话中粘贴的文字，无需额外处理。保存为临时文件供定量分析脚本使用。

### 2. Word / PDF

```
parse_file(file_path="<文件路径>", query="提取文档正文内容")
```

注意事项：
- 跳过目录、页眉页脚、参考文献等非正文部分
- 如果文档包含多篇文章，按标题拆分为独立样本

### 3. 图片

```
understand_media(media_path="<图片路径>", question="请提取图片中的所有文字内容，保持原始排版格式")
```

适用场景：用户截图的小红书笔记、公众号文章截图、手写笔记照片等。

### 4. 微信公众号链接

```
read_url(url="<公众号文章链接>")
```

注意事项：
- `read_url` 可直接提取公众号文章正文
- 过滤掉文末的广告、推荐阅读等非正文内容
- 提取作者名用于标注来源

### 5. 小红书链接（xhs-content-reader 子技能）

小红书链接通过调用内置的 `xhs-content-reader` 子技能进行提取。该方案基于 CDP 协议，能获取更完整的结构化数据（包括互动数、评论等）。

#### 调用流程

**必须严格按以下顺序执行：**

#### Step 1：检查登录状态

```bash
cd skills/xhs-content-reader/scripts
python cli.py check-login
```

如果返回 `{"logged_in": false}`，需先引导用户在浏览器中登录小红书，或手动提供 Cookie。

#### Step 2：搜索/定位笔记

如果用户提供的是关键词，先执行搜索：
```bash
python cli.py search-feeds --keyword "<关键词>" --count 1
```
从输出中获取 `feed_id` 和 `xsec_token`。

如果用户直接提供了笔记链接，通常需要从链接中提取 ID，或通过 `search-feeds` 匹配标题来获取配对的 `xsec_token`。

#### Step 3：获取笔记详情

```bash
python cli.py get-feed-detail --feed-id <ID> --xsec-token <TOKEN>
```

输出包含：标题、正文、作者、互动数据（点赞/收藏/评论）、标签、图片列表等。

#### Step 4：关闭浏览器

```bash
python cli.py close-browser
```

#### 错误处理与兜底方案

| 错误/场景 | 处理方式 |
|------|----------|
| **权限不足/环境受限** | 若 CDP 协议因权限或沙箱限制无法启动，自动切换至 **browser_use + OCR** 兜底方案。 |
| 未登录 | 提示用户：“检测到小红书未登录，请先在浏览器中登录后再试。” |
| Token 不匹配 | `feed_id` 和 `xsec_token` 必须配对。若失效，重新执行 `search-feeds` 获取最新配对。 |
| CDP 连接失败 | 尝试重启 Chrome 调试端口；若仍失败，触发兜底方案。 |

#### 兜底方案：browser_use + OCR

当 CDP 方案不可用时，执行以下流程：
1. **打开页面**：使用 `browser_use(action="openTab", url="<笔记链接>")`。
2. **提取文本**：通过 `browser_use(action="readability")` 或 `extract` 获取标题和正文摘要。
3. **图片 OCR**：截取笔记核心长图，调用 `understand_media(media_path, question="提取图片中的所有文字内容")` 补全干货内容。
4. **局限性说明**：兜底方案可能无法获取深层评论和精确的互动计数，但足以支持基础的风格分析。

---

## 内容来源自动识别

当用户提供内容时，按以下优先级自动判断来源类型：

```
1. 是否为 URL？
   ├─ 包含 xiaohongshu.com 或 xhslink.com → 小红书链接
   ├─ 包含 mp.weixin.qq.com → 微信公众号链接
   └─ 其他 URL → 尝试 read_url
2. 是否为文件？
   ├─ .docx → Word
   ├─ .pdf → PDF
   └─ .png/.jpg/.jpeg/.webp → 图片 OCR
3. 以上都不是 → 纯文本
```
