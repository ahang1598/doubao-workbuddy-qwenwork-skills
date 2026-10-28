# 字体加载

保留与题材匹配的 webfont，提前发现首屏字体，缩短系统字体切换为 webfont 的时间。`preconnect` / `preload` 只能提前加载，不能保证慢网下完全没有字体切换或布局位移。

## 先确定实际资源

1. 只选页面实际使用的少量字族和字重。用 `https://miaoda.feishu.cn/fonts/css2?family=…&display=swap` 获取 CSS；多字族重复 `family=`，不用 Google 域名。
2. **按目标浏览器的 User-Agent 读取这次 CSS 响应**，下载到任务目录后仅提取相关 `@font-face` 的字族、字重、样式、`src` URL、格式和 `unicode-range`，不把整份分片 CSS 读进上下文。镜像会按 User-Agent 协商：普通 curl 的响应可能与 Chromium 使用的 WOFF2 分片不同，不能拿它的 URL 给浏览器 preload。不能确认响应一致时，只做 preconnect，保留正常 stylesheet；不猜字体地址。
3. 从中选择首屏正文或主标题实际使用的 **1–2 个字体文件**。按 URL 去重；分片的 `unicode-range` 须包含该处实际字符，不要求这 1–2 片覆盖全部首屏文字，其余仍由 stylesheet 按需加载。不预加载未使用的字族、屏外字体或全部中文分片，它们会与首屏图片和样式争带宽。不能确认需要哪个分片时，只做 preconnect 和正常样式加载，不猜 preload 地址。

## 在 head 靠前加载

把资源提示放在 charset、viewport 之后、大段内联样式和脚本之前，顺序为 preconnect → 字体 preload → 正常 stylesheet。

下面是 Noto Sans SC 400 的结构示例。`FONT_FILE_URL_FROM_CSS` 必须替换为对应浏览器响应中首屏实际用到的 WOFF2 分片 URL；`FONT_CDN_ORIGIN` 替换为该 URL 的 origin。换字族、字重或样式表时重新读取响应，不把占位符或旧地址写进产物。

```html
<link rel="preconnect" href="https://miaoda.feishu.cn">
<link rel="preconnect" href="FONT_CDN_ORIGIN" crossorigin>
<link rel="preload" href="FONT_FILE_URL_FROM_CSS"
      as="font" type="font/woff2" crossorigin>
<link rel="stylesheet"
      href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Sans+SC:wght@400&amp;display=swap">
<style>
  body {
    font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.6;
  }
</style>
```

- preconnect 填 **origin**，样式服务和字体 CDN 不一定同域；字体 CDN 的连接加 `crossorigin`，与字体的匿名 CORS 请求匹配。
- preload 填 **字体文件完整 URL**，必须与 CSS 的 `src` 一致；`as="font"`、`crossorigin` 不省略，格式明确时用对应 `type`（WOFF2 为 `font/woff2`、TTF 为 `font/ttf`）。不要把 `css2` 样式表地址标成字体，也不要把 TTF 标成 WOFF2，否则提示可能被忽略或资源重复下载。
- 保留正常的 `<link rel="stylesheet">`，不用 CSS `@import` 或 `onload` 再切 `rel` 的异步技巧；额外发现层级和迟到样式会加剧首屏变化。preload 不代替字体声明。

## 回退与版式

每个 `font-family` 保留完整的系统 fallback，正文设明确行高；标签、按钮、表格保留换行和尺寸余量，不按加载前的字宽锁死布局。图片等非文字区域另设宽高，避免把其他重排误判为字体问题。

默认保留 `display=swap`，不以 `font-display:block`、隐藏 body、等待 `document.fonts.ready` 后才展示页面来掩盖抖动；字体失败时正文也必须可读。只有用户明确接受慢网下本次访问一直使用系统字体时才用 `optional`，不能同时承诺各平台使用同一 webfont。

静态检查 preload 的 URL、格式、CORS 和实际使用范围；按主 skill 跑 `shot.py` 核对最终排版。最终截图正常不等于首屏没有切换，不因此承诺 CLS 为零。
