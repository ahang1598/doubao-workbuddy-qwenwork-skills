# 微博图文提取流程

## 概述

微博内容提取采用移动端 API（m.weibo.cn/detail/{mid}）获取 JSON 数据，无需浏览器，无需登录。

## 提取流程

### 1. 获取微博链接

用户提供微博链接，支持格式：
- `https://m.weibo.cn/detail/5129390123456789`
- `https://m.weibo.cn/status/5129390123456789`
- `https://weibo.com/1234567890/PxxxxYyyy`
- `https://weibo.com/detail/5129390123456789`

### 2. 执行提取命令

```bash
python3 scripts/cli.py extract-weibo --url "https://m.weibo.cn/detail/xxx"
```

**可选参数：**
- `--output-dir <dir>`：自定义输出目录
- `--no-download-images`：不下载图片，只返回 URL
- `--no-ocr`：跳过图片 OCR 识别

### 3. 提取内容

脚本自动完成：
1. 从链接解析微博 ID（mid）
2. 请求移动端页面 `m.weibo.cn/detail/{mid}`
3. 从页面 HTML 中提取 `$render_data` JSON 数据
4. 解析 status 对象，提取正文、作者、配图、互动数据
5. 自动展开长文（`longText.longTextContent`）
6. 下载大图到本地（自动带 Referer 防盗链）
7. 图片 OCR 文字识别
8. 生成 Markdown 分析报告

### 4. 输出结果

- `{weibo_id}_content.txt`：纯文本正文
- `{weibo_id}_images/`：下载的配图目录
- `{weibo_id}_report.md`：Markdown 分析报告（含互动数据）

## 技术细节

- **数据源**：移动端页面 `var $render_data = [{...}][0]`，包含完整的 status JSON
- **正文处理**：HTML 格式，保留 @用户名 和 #话题#，清理表情标签
- **长文展开**：自动检测 `status.longText.longTextContent` 替换短正文
- **图片策略**：优先取 `pics[].large.url` 大图
- **防盗链**：下载图片时携带 `Referer: https://m.weibo.cn/`

## 注意事项

- 移动端 API 无需登录即可访问大部分公开微博
- 私密微博或设置权限的微博可能无法提取
- 部分旧微博的 `$render_data` 格式可能不同，脚本会自动降级到 HTML 解析
- 如遇频率限制，建议间隔一段时间后重试
