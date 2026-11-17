# HTML Web 字体契约

HTML 字体先从 [推荐入口](font-recommendation-list.md) 选择视觉候选，再按本文解析、注入和验证；本地安装、下载与注册按 [本地字体资源](font-family-library.md) 处理。字体选择保持已确定的产物格式，pure-image 只使用视觉建议。

## 为什么必须经过 Resolver

浏览器可以直接加载字体 CDN，但模型不能自行猜测 family、字重、格式或对象路径。`assets/fonts/web-font-manifest.json` 与无限画布前端的生成字体目录对齐；`scripts/runtime/resolve_font.py --target html` 从该白名单选择一个真实 face，并确定性返回 `@font-face`、字体栈和回退信息。模型消费解析结果，不手工遍历、改写或拼接 manifest URL。

## 解析

使用最终可见文案，按实际需要的字体、字重和样式去重后解析；同任务中参数、资源和目标环境未变的成功结果可复用，失败只处理对应项。传入精确字体 ID、展示名或 CSS family：

```bash
python3 scripts/runtime/resolve_font.py "douyin-sans" \
  --target html \
  --weight 700 \
  --style normal \
  --text "让美好发生" \
  --require-ready
```

`--require-ready` 或 `--check-cdn` 会执行 CDN 探测；未探测时返回 `cdn_listed_not_rechecked`，失败时返回 `cdn_check_failed` 并以非零状态退出。CDN 探测通过不代表浏览器 CORS/CSP 或逐字覆盖验证通过。

只使用目录支持的真实 weight/style；推荐字重范围不代表该字体具备所有实例。实例缺失时按返回结果选用受支持的 face，或按下文回退规则处理，不合成粗体或斜体。

Windows 先读 [`windows-compat.md`](../workflow/windows-compat.md)，不用上述 Bash 的 `\` 续行；从 Skill 根目录使用已确认解释器执行单行命令，参数按实际文案替换：

```powershell
python -X utf8 "./scripts/runtime/resolve_font.py" "douyin-sans" --target html --weight 700 --style normal --text "让美好发生" --require-ready
```

Resolver JSON 与字体声明由 Python 显式按 UTF-8 捕获和保存，不用 Shell 重定向或管道。其他字体／CSS 库／素材脚本的 `python3` 示例同样替换解释器；XML 字体和 HTML Web 字体契约保持原样。

只有 `package_status=cdn_ready` 且 `web_font_contract_entry` 非空时才能注入。Web 模式不会下载字体到模型本地，也不会返回 Canvas `font_contract_entry`。

`coverage_status=not_checked` 表示未做本地二进制 cmap 检查。HTML 继续使用匹配语种的字体与返回的回退栈，在 `shot.py` 中检查实际加载、缺字和排版；仅明确需要离线处理或二进制核验时进入本地流程。

## HTML 注入

1. 将页面所需 face 的 `web_font_contract_entry.font_face_css` 写入普通样式块或可加载的样式表；可合并或分块，不限定专用标记、数量或与普通 CSS 分离。
2. 仅 HTML 规范要求的三个根节点固定宽高必须行内声明；其他视觉 CSS 可使用行内样式、普通样式块、选择器或外部样式表。
3. 文字元素使用 `web_font_contract_entry.font_stack`，并写入解析所得的真实 `font-weight` 与 `font-style`；主 family 名不得改写。
4. 同一页面使用多个 weight/style 时，每个真实 face 分别解析，可放在同一或不同样式块；避免相互冲突的声明。
5. 加载失败按下文回退规则处理。
6. 不使用 manifest 之外的 URL，不把本地绝对路径、`file://` 或临时缓存路径写入 HTML。

## 许可与回退

- 核对字体元数据中的来源、许可及当前用途；目录或 CDN 可用不等于许可通过。非标许可、条款不清、禁止再分发或核验失败时先确认授权／替代方案；子集化、修改及再分发另核对相应许可。系统字体可记录来源，不复制进 Skill 或交付包。
- 用户指定字体加载失败时，先按错误原因尝试恢复；仍失败则采用可加载的回退字体，检查排版，并在交付时说明目标字体未生效及实际字体。用户另外锁定必须保留的关键字形无法满足时，先确认替代方案。
- 模型自选字体不可用时，自行选择适合语种、角色与设计气质的可加载字体，复查排版后交付。

Brief 记录字体选择与搭配理由；具体声明写入 HTML，检查结论写入既有验收记录。HTML 无需本地安装、Canvas Item 字体注册或独立 `font-contract.json`；已有可选契约或用户明确要求时按需提供，不替代实际渲染。

## 验证与前端边界

- 字体 URL 仍须精确存在于 Web manifest，同域名下的猜测路径也不通过；不因普通样式块、外部样式表、字体块名称、数量或混合普通规则而报错。
- CDN 探测、FontFace 加载或截图正常均不能单独证明目标字体命中与逐字覆盖；结合目标环境诊断、实际字形和截图判断，证据不足记未验证。多语种分别核对真实文案。
- 预览和截图前等待 `document.fonts.ready`，再检查实际字体、缺字、替换、换行、基线、伪粗体和裁切；源码声明不能代替渲染证据。
- 字体二进制由最终用户浏览器从 CDN 加载，不作为独立 CanvasWorkspace Asset 上传。前端需要允许该字体 CDN 的 CORS/CSP，并在首屏 ready、截图和导出前等待字体加载完成。
