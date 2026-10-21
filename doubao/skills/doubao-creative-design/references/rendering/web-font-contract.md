# HTML Web 字体契约

本契约只在生产轨道已经锁定为 HTML 后使用。字体选择不得创建、切换或推断产物格式；既有 XML 多图层编辑仍使用本地／系统字体契约，不把 CDN URL 写入 XML。

## 为什么必须经过 Resolver

浏览器可以直接加载字体 CDN，但模型不能自行猜测 family、字重、格式或对象路径。`assets/fonts/web-font-manifest.json` 与无限画布前端的生成字体目录对齐；`scripts/runtime/resolve_font.py --target html` 从该白名单选择一个真实 face，并确定性返回 `@font-face`、字体栈和回退信息。模型消费解析结果，不手工遍历、改写或拼接 manifest URL。

## 解析

使用最终可见文案选择字体；传入精确字体 ID、展示名或 CSS family，并显式指定实际需要的字重和样式：

```bash
python3 scripts/runtime/resolve_font.py "douyin-sans" \
  --target html \
  --weight 700 \
  --style normal \
  --text "让美好发生" \
  --require-ready
```

`--require-ready` 或 `--check-cdn` 会执行 CDN 探测；未探测时返回 `cdn_listed_not_rechecked`，失败时返回 `cdn_check_failed` 并以非零状态退出。CDN 探测通过不代表浏览器 CORS/CSP 或逐字覆盖验证通过。

只支持目录中明确列出的 weight/style 实例；缺失实例明确报错，不合成、不静默替换。

只有 `package_status=cdn_ready` 且 `web_font_contract_entry` 非空时才能注入。Web 模式不会下载字体到模型本地，也不会返回 Canvas `font_contract_entry`。

`coverage_status=not_checked` 表示没有下载字体二进制执行逐字 cmap 检查，不等于覆盖完整。选择与文案语种匹配的 `language_group`，保留 Resolver 返回的系统回退栈，并在`shot.py` 的截图中检查缺字、换行和布局。

## HTML 注入

1. 将页面所需 face 的 `web_font_contract_entry.font_face_css` 写入普通样式块或可加载的样式表；可合并或分块，不限定专用标记、数量或与普通 CSS 分离。
2. 仅 HTML 规范要求的三个根节点固定宽高必须行内声明；其他视觉 CSS 可使用行内样式、普通样式块、选择器或外部样式表。
3. 文字元素使用 `web_font_contract_entry.font_stack`，并写入解析所得的真实 `font-weight` 与 `font-style`；主 family 名不得改写。
4. 同一页面使用多个 weight/style 时，每个真实 face 分别解析，可放在同一或不同样式块；避免相互冲突的声明。
5. 字体加载失败时，返回的系统回退栈仅用于临时显示兜底；最终字体按 [字体回退规则](font-family-library.md#7-回退规则) 处理：用户锁定精确字体或关键字形时先请求确认，未锁定时在原约束内重选并核验后定稿。不得静默换成另一个远程字体，也不通过 CSS 合成不存在的粗体或斜体。
6. 不使用 manifest 之外的 URL，不把本地绝对路径、`file://` 或临时缓存路径写入 HTML。

Resolver 输出示例：

```json
{
  "target": "html",
  "package_status": "cdn_ready",
  "coverage_status": "not_checked",
  "font_contract_entry": null,
  "web_font_contract_entry": {
    "font_family": "DouyinSans",
    "font_weight": 700,
    "font_style": "normal",
    "source": {
      "url": "https://lf-flow-web-cdn.doubao.com/obj/flow-doubao/doubao/infinite-canvas/fonts/v1/douyin-sans/douyin-sans-bold.ttf",
      "format": "truetype",
      "crossorigin": "anonymous"
    },
    "font_face_css": "@font-face { ... }",
    "font_stack": "\"DouyinSans\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
  }
}
```

## 验证与前端边界

- 字体 URL 仍须精确存在于 Web manifest，同域名下的猜测路径也不通过；不因普通样式块、外部样式表、字体块名称、数量或混合普通规则而报错。
- 自动检查 FontFace 加载状态不能证明每个文字节点实际使用了目标字体，也不能证明逐字覆盖完整；这些项目需要结合截图检查。
- 预览和截图前等待 `document.fonts.ready`，再检查实际字体、缺字、替换、换行、基线、伪粗体和裁切；源码声明不能代替渲染证据。
- 字体二进制由最终用户浏览器从 CDN 加载，不作为独立 CanvasWorkspace Asset 上传。前端需要允许该字体 CDN 的 CORS/CSP，并在首屏 ready、截图和导出前等待字体加载完成。
