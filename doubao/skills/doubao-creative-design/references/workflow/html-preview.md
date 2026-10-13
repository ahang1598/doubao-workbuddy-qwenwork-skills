# HTML 页面自检与预览

唯一入口为 `python3 <SKILL_DIR>/scripts/runtime/shot.py <html_path>`。脚本直接使用 Playwright＋Chromium 和 Pillow；不依赖或调用 artifact-preview／artifacts-preview Skill。Agent 不另用 Browser Use、其他截图脚本或浏览器检查器进行页面自检。交付前运行一次，修改后重跑；按报告定位具体问题，不进入反复更换工具的调试循环。

## 输入与尺寸

输入当前完整本地 HTML。脚本读取 html 的 data-canvas-width/height，以声明宽度、DPR=1 渲染，输出同尺寸无损 PNG。没有 desktop/mobile 双视口、JPEG 压缩或降到 1000px 的默认行为。固定画布在 Mobile 环境同样保持作品尺寸，交付环境不改变构图。

依赖为 Python 包 playwright、Pillow；渲染直接使用系统已安装的 **chromium-1169**，不执行浏览器下载安装。脚本从 `PLAYWRIGHT_BROWSERS_PATH` 和常见系统缓存位置定位该版本；非标准安装位置使用 `--exec-path` 指向该版本的真实可执行文件。找不到时报告失败，不静默切换其他版本。默认输出位于 HTML 同目录的 `_shots/`，无需删除。可用 `-o` 指定 PNG 路径，`--slice-height` 控制内部分片高度（默认 3200）。

HTML 的 `<html>` 标签必须显式包含 `data-canvas-width` 和 `data-canvas-height`，值为正整数、单位 px（属性值不写单位）。例如 `<html lang="zh-CN" data-canvas-width="574" data-canvas-height="7920">`。html、body 和作品根的行内宽高必须与属性一致；缺失属性时脚本报错，不猜测或退回网页默认尺寸。完整要求见 [HTML 规范](../html/coding-rendering.md)。

## 先测高再锁定画布

脚本在内存页面中暂时解除 html、body 和作品根的高度限制，读取自然高度后恢复原样，再检查正式固定画布。作品根优先使用 data-canvas-root，其次 main，最后 body 首元素；应提供唯一明确的作品根。

报告 measurement.natural.height 供未锁高作品参考。Agent 仅在必要时将确认的高度写回 data-canvas-height 及 html/body/作品根三处行内 height，再运行同一脚本。用户锁高时保持尺寸并重排。脚本不自动修改源文件，不用截图高度反推自然高度。

作品末尾保留唯一正常流 data-canvas-bottom-safe-area 收尾元素；默认最小高度 max(24, ceil(width × 0.04))，有更大设计留白时沿用。不得用隐藏内容、绝对定位底栏、裁切正文或无关装饰通过检查。natural.height 是布局测量结果，复杂布局仍结合报告和完整截图核对。

## 报告与完整截图

先读 consoleErrors、resourceErrors 和 issues 中的 code/hint，再读完整主图；主图无法读取时才依序读取 slices。脚本先分段捕获声明画布、核验每段像素并无缩放拼接，保留完整主图与诊断分片。尺寸一致仅证明输出边界，需同时检查内容溢出及底部安全区。

脚本等待字体、图片与布局稳定；超时会报告未就绪，不静默当成通过。不强制重写滚动揭示元素的 opacity、transform 或 visibility。图片必须静态引用已准出的短链，HTTP(S) 格式检查不证明来源与素材清单一致，仍须核对真实工具结果。

退出码 `0` 表示自动检查通过，`1` 表示已完成检查但发现内容或布局问题，`3` 表示脚本无法完成执行。自动检查不能证明审美、事实或身份正确。Agent 看截图核对最终视觉；退出码 `1` 的问题必须按 hint 与实际截图修正并重跑，不把合理的有意出血或光学对齐误改为错误。

## 交付与失败

有当前版本合格的同尺寸完整预览时，由主 Agent 上传 CDN、核验公网 HTTP(S) 链接并用 Markdown 图片展示；不合格或缺失预览不得展示，预览截图不使用 present_files、不创建 IMAGE Item。默认 Canvas 的 HTML 上传、Item 创建与回读按独立门禁执行，不以预览展示完成作为统一前置条件；create/get 后由主 Agent 用 present_files 交付 workspace_id?item_id=xxx 卡片。Mobile 仅走预览出口，不创建画布。没有合格预览、未完成其 CDN＋Markdown 展示或当前环境所需卡片未交付时，不得宣称完整完成。

只有退出码 `3` 的执行失败允许跳过自检并记录“预览未验证”，继续默认 Canvas 中未被独立规则阻断的可完成部分，不得伪造截图或宣称验证通过。退出码 `1` 表示检查完成并发现问题，必须按 hint 与实际截图修正并重跑，不得改记为“预览未验证”；退出码 `1` 本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读。上述 HTML 上传指 `FileBatchUpload`；是否阻断这些步骤，由源码硬门禁、媒体门禁或其他独立规则决定，已完成写入也不免除修正与重跑义务。禁止为执行失败改用其他预览 Skill 或截图工具。Mobile 如果没有合格预览图，则只说明可视交付未完成，不启用 Canvas；连续出现同一问题时保留诊断和真实交付状态，不盲目增减高度。
