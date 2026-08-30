# 今日头条图文提取流程

## 概述

今日头条文章提取采用「移动端 API 优先 + 脚本解析」模式：
- **Step 1**：优先调用移动端 API（`m.toutiao.com/i{id}/info/`）直接获取 JSON 数据，无需浏览器、无需解析 HTML
- **Step 2**：调用 CLI 脚本处理内容

> ⚠️ 头条桌面端（`www.toutiao.com`）是纯 CSR（客户端渲染），curl 获取的 HTML 是空壳。**必须通过移动端 API 获取数据**。

## 支持的链接格式

- `https://www.toutiao.com/article/1234567890/`
- `https://www.toutiao.com/a1234567890/`
- `https://m.toutiao.com/i1234567890/`

---

## Step 1：获取文章数据

> ⚠️ **优先方式**：直接调用移动端 API 获取 JSON（无需浏览器），脚本内部自动完成。仅在 API 失败时才降级到 browser_use。

### 方式零（推荐优先）：移动端 API 直接获取 JSON

**无需手动 curl**，脚本内部自动调用移动端 API：

```bash
# 直接调用脚本，脚本自动走移动端 API
python3 scripts/cli.py extract-toutiao \
  --url "https://www.toutiao.com/article/xxx" \
  --output-dir ~/.content-breakdown/output
```

> **API 端点**：`GET https://m.toutiao.com/i{article_id}/info/`
> 返回完整 JSON 含 title、content（HTML 格式）、source、media_user、publish_time、互动数据等。

> **手动验证 API 是否可用**：
> ```bash
> curl -sL -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1' \
>   "https://m.toutiao.com/i7651554238635491874/info/" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'✅ title={d[\"title\"]}, content={len(d[\"content\"])} chars')"
> ```

> ⚠️ **移动端 API 失败时**（返回非 200、非 JSON、或 content 为空），**立即降级到 browser_use 方式**。

---

### 方式一（browser_use 降级方案）：

> 仅当 curl 失败时才执行以下步骤。

## Step 1B：Agent 通过 browser_use 获取页面 HTML

### 1.1 打开文章页面

```
browser_use(action="open_tab", url="https://www.toutiao.com/article/xxx")
```

### 1.2 等待页面加载

```
browser_use(action="wait_for", timeMs=8000)
```

> 头条文章需要较长的加载时间（JS 渲染），建议等待 8 秒。

### 1.3 模拟用户行为（防反爬）

```
browser_use(action="evaluate", fn="window.scrollBy(0, 500)")
browser_use(action="wait_for", timeMs=2000)
browser_use(action="evaluate", fn="window.scrollBy(0, -200)")
browser_use(action="wait_for", timeMs=2000)
```

### 1.4 获取完整页面 HTML

```javascript
browser_use(action="evaluate", fn="document.documentElement.outerHTML")
```

### 1.5 保存 HTML 到临时文件

将获取到的 HTML 内容保存到临时文件（如 `/tmp/toutiao_{article_id}.html`）。

### 1.6 关闭页面

```
browser_use(action="close_tab")
```

---

**降级执行步骤**（browser_use 失败时）：

```
ask_human("⚠️ 需要通过 Chrome 浏览器提取头条文章内容。即将弹出浏览器窗口。")
```

用户确认后执行：
```bash
python3 scripts/cdp_extract.py --url "https://www.toutiao.com/article/xxx"
```

CDP 返回 JSON，从中提取 `page_html` 字段保存为文件，继续 Step 2。

---

## Step 2：调用脚本处理

### 情况 A：直接使用（推荐，脚本自动走移动端 API）

```bash
python3 scripts/cli.py extract-toutiao \
  --url "https://www.toutiao.com/article/xxx" \
  --output-dir ~/.content-breakdown/output
```

### 情况 B：browser_use 降级（移动端 API 失败时）

```bash
python3 scripts/cli.py extract-toutiao \
  --url "https://www.toutiao.com/article/xxx" \
  --page-html-file /tmp/toutiao_xxx.html
```

**可选参数：**
- `--output-dir <dir>`：自定义输出目录
- `--no-download-images`：不下载图片，只返回 URL
- `--no-ocr`：跳过图片 OCR 识别

脚本内部处理流程：
1. **移动端 API 获取 JSON**（自动，无需手动操作）
2. 从 JSON 中提取标题、作者、发布时间、正文（HTML）、图片、互动数据
3. 正文 HTML 清理为纯文本
4. 下载图片到本地
5. 图片 OCR 文字识别
6. 生成 Markdown 分析报告

## 输出结果

- `{article_id}_content.txt`：纯文本正文
- `{article_id}_images/`：下载的图片目录
- `{article_id}_report.md`：Markdown 分析报告（含阅读/评论/点赞数据）

## 技术细节

- **数据源**：移动端 API（`m.toutiao.com/i{id}/info/`）返回 JSON，降级到 SSR JSON 解析（`__INITIAL_PROPS__` 等），最终降级 HTML 解析
- **移动端 API 返回字段**：title, content(HTML), source, media_user, publish_time, comment_count, digg_count, impression_count 等
- **正文格式**：API 返回的 content 为 HTML 格式，自动清理标签并保留段落结构
- **图片来源**：正文 `<img>` 标签 + `image_list` 字段双路提取
- **时间戳处理**：自动将 Unix 时间戳转换为 `YYYY-MM-DD HH:MM` 格式
- **图片协议补全**：头条图片 URL 可能缺少协议前缀（`//`），脚本自动补全为 `https:`

## 注意事项

- ⛔ 头条桌面端是纯 CSR，curl 桌面端 URL 只能得到空壳 HTML。**必须通过移动端 API 获取数据**（脚本内部自动完成）
- **不得自行添加 `--no-ocr`**，除非用户明确要求跳过 OCR

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 移动端 API 返回空数据 | 文章被删除或限制访问 | 降级到 browser_use 方式 |
| 移动端 API 返回非 JSON | 被反爬拦截或网络问题 | 降级到 browser_use 方式 |
| 桌面端 curl 返回空壳 HTML | 正常现象，桌面端是纯 CSR | 这是预期行为，脚本自动走移动端 API |
| 正文为空 | JS 未渲染完成（browser_use 降级时） | 增加等待时间到 10 秒，或加滚动触发懒加载 |
| 图片 URL 不完整 | 缺少协议前缀 | 脚本自动补全 `https:` |
| 被重定向到首页 | 反爬触发（browser_use 降级时） | 重试或增加滚动模拟 |
