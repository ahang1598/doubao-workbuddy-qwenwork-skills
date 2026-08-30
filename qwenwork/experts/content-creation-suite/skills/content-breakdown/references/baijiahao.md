# 百家号图文提取流程

## 概述

百家号（baijiahao.baidu.com）图文提取采用「curl 优先 + 脚本解析」模式：
- **Step 1**：优先用 `curl` + Desktop UA 获取页面 HTML，失败时降级到 browser_use
- **Step 2**：调用 CLI 脚本解析 HTML，提取正文、图片、OCR

> ⚠️ 百家号有百度安全验证，curl 可能被拦截。优先尝试 curl，失败后快速降级到 browser_use。

## 支持的链接格式

- `https://baijiahao.baidu.com/s?id=1234567890`
- `https://mbd.baidu.com/newspage/data/landingsuper?id=xxx`

---

## Step 1：获取页面 HTML

> ⚠️ **优先方式**：先用 `curl` + Desktop UA 获取页面 HTML（无需浏览器），仅在 curl 失败（被百度安全验证拦截或返回空内容）时才降级到 browser_use。

### 方式零（推荐优先）：curl + Desktop UA

```bash
curl -sL -o /tmp/baijiahao_xxx.html \
  -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  "https://baijiahao.baidu.com/s?id=xxx"
```

> **验证 curl 是否成功**：检查 HTML 文件是否包含 `article-content` 或 `article` 标签：
> ```bash
> python3 -c "html=open('/tmp/baijiahao_xxx.html').read(); print('✅ OK' if 'article-content' in html or 'article' in html else '❌ 内容缺失')"
> ```
> 如果内容为空或包含"百度安全验证"字样，说明被反爬拦截，**立即降级到 browser_use 方式**。

---

### 方式一（browser_use 降级方案）：

> 仅当 curl 失败时才执行以下步骤。

## Step 1B：Agent 通过 browser_use 获取页面 HTML

### 1.1 打开文章页面

```
browser_use(action="open_tab", url="https://baijiahao.baidu.com/s?id=xxx")
```

### 1.2 等待页面加载

```
browser_use(action="wait_for", timeMs=5000)
```

### 1.3 获取完整页面 HTML

```javascript
browser_use(action="evaluate", fn="document.documentElement.outerHTML")
```

### 1.4 保存 HTML 到临时文件

将获取到的 HTML 内容保存到临时文件（如 `/tmp/baijiahao_{article_id}.html`）。

### 1.5 关闭页面

```
browser_use(action="close_tab")
```

---

**降级执行步骤**（browser_use 失败时）：

```
ask_human("⚠️ 需要通过 Chrome 浏览器提取百家号文章内容。即将弹出浏览器窗口。")
```

用户确认后执行：
```bash
python3 scripts/cdp_extract.py --url "https://baijiahao.baidu.com/s?id=xxx"
```

CDP 返回 JSON，从中提取 `page_html` 字段保存为文件，继续 Step 2。

---

## Step 2：调用脚本处理

```bash
python3 scripts/cli.py extract-baijiahao \
  --url "https://baijiahao.baidu.com/s?id=xxx" \
  --page-html-file /tmp/baijiahao_xxx.html
```

**可选参数：**
- `--output-dir <dir>`：自定义输出目录
- `--no-download-images`：不下载图片，只返回 URL
- `--no-ocr`：跳过图片 OCR 识别

脚本自动完成：
1. 从 HTML 文件解析 `div.article-content`（BeautifulSoup 优先，正则降级）
2. 提取标题、作者、发布时间、正文文本
3. 提取文章内嵌图片 URL（过滤头像/图标/logo）
4. 下载原图到本地
5. 图片 OCR 文字识别（rapidocr → macOS Vision → pytesseract 三级降级）
6. 生成 Markdown 分析报告

## 输出结果

- `{article_id}_content.txt`：纯文本正文
- `{article_id}_images/`：下载的图片目录
- `{article_id}_report.md`：Markdown 分析报告

## 技术细节

- **数据源**：浏览器渲染后的完整 HTML
- **内容定位**：`div.article-content` → `div#article` → `article` 标签逐级降级
- **SSR 数据**：部分页面有 `window.__INITIAL_STATE__` JSON 数据，可作为补充
- **图片过滤**：自动过滤 avatar/icon/logo/emoji 等非正文图片
- **编码处理**：UTF-8

## 注意事项

- ⛔ 百家号优先尝试 `curl`，被百度安全验证拦截时再降级到 **browser_use 获取 HTML**
- **不得自行添加 `--no-ocr`**，除非用户明确要求跳过 OCR
- 部分文章可能需要滑块验证，需用户在浏览器中手动完成

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 返回"百度安全验证" | 纯 HTTP 被拦截 | 通过 browser_use 获取 HTML |
| 正文为空 | HTML 结构不匹配 | 检查 `div.article-content` 选择器 |
| 图片下载失败 | 防盗链 | 图片 URL 已自动携带 Referer |
