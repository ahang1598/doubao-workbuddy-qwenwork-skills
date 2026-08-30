# 微信公众号图文提取

**触发词**：提取公众号文章、获取公众号内容、提取微信文章、公众号图文提取

> ✅ 无需登录，无需浏览器，直接 HTTP 请求，速度最快

## 默认执行命令

```bash
python3 scripts/cli.py extract-wechat \
  --url "https://mp.weixin.qq.com/s/AbCdEfGhIjKlMnOpQrStUv" \
  --output-dir ~/.content-breakdown/output
```

## 内部执行步骤

1. 直接 HTTP 请求文章页面 HTML（无需浏览器，无需登录）
2. BeautifulSoup 解析 `<div id="js_content">` 提取正文文本
3. 提取文章标题、作者、公众号名称、发布时间
4. 下载文章内嵌图片（CDN 直链，无防盗链限制）
5. 对图片进行 OCR 文字识别（rapidocr 优先，macOS Vision 降级）
6. 生成 Markdown 分析报告

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--url` | 公众号文章链接（必填） | `https://mp.weixin.qq.com/s/xxxxx` |
| `--no-download-images` | 不下载图片，只返回图片 URL | — |
| `--no-ocr` | 跳过图片 OCR 识别（⚠️ 不得自行添加，除非用户明确要求跳过 OCR） | — |
| `--output-dir` | 输出目录 | `~/.content-breakdown/output` |

## 执行完成后

命令执行成功后，读取结果中的 `content`（正文）和 `image_texts`（图片 OCR 文字）字段，**按 `references/output-format.md` 的格式输出给用户**。

> ⚠️ 图片 OCR 已由命令自动完成，直接读取 `image_texts` 字段即可，无需额外执行 OCR 命令。

## 预计耗时

~5-15s（含图片下载和 OCR）
