# HTML 页面自检与预览

唯一入口为 `python3 <SKILL_DIR>/scripts/runtime/shot.py <html_path>`，一次完成自然高度测量、固定画布复核和截图。输入当前完整 HTML，交付前运行；修改后只重跑受影响的文件，共用字体、样式或素材变化时覆盖其消费者。未变文件及依赖的有效结果可复用。

## 输入与尺寸

脚本使用 Playwright、Pillow 与已安装的 Chromium。HTML 路线开始时用 `shot.py --check-runtime` 检查依赖；环境未变时复用结果。预检不读取作品，也不代替页面自检。页面检查始终使用同一渲染器，不另用 Browser Use、其他截图脚本或预览 Skill。

Windows 先读 [平台兼容说明](windows-compat.md)，使用已确认的 Python 3 入口：
```powershell
python -X utf8 "./scripts/runtime/shot.py" --check-runtime
python -X utf8 "./scripts/runtime/shot.py" "./task/design.html"
```

Chromium 从 `PLAYWRIGHT_BROWSERS_PATH` 与系统缓存定位，Windows 包括 `%LOCALAPPDATA%\ms-playwright`；非标准安装用 `--exec-path` 指定实际可执行文件。缺失时报告执行失败，不下载或切换浏览器。

输入按 [HTML 协议](../html/coding-rendering.md) 声明固定画布。脚本按声明宽高、DPR=1 输出同尺寸无损 PNG，Canvas／Mobile 均保持作品尺寸；缺少尺寸属性时报错。默认输出 `_shots/`，用 `-o` 指定路径，`--slice-height` 控制诊断分片高度（默认 3200）。

## 先测高再锁定画布

同次调用中，脚本临时解除 html、body 和作品根的高度限制，读取 `measurement.natural` 后恢复，再以 `measurement.final` 检查固定布局。作品根依次按 `data-canvas-root`、main、body 首元素定位；源文件不会被修改。

未锁高时，Agent 对照自然高度、实际内容和页尾安全区，仅在需要改高时向上取整，将同一值写回 `data-canvas-height` 和 html／body／作品根三处行内 height，再运行同一入口。锁高作品在原尺寸内重排。局部修改未影响高度时直接复查当前渲染，不另发起测高。

页尾收尾元素遵循 [HTML 协议](../html/coding-rendering.md#html-验收与交付)。分别核对声明尺寸、自然高度、正式内容底边和安全区；截图尺寸正确不代表内容完整。复杂布局、隐藏祖先或字体回退等未覆盖项结合截图判断，证据不足记未验证。

## 报告与完整截图

先读 `consoleErrors`、`resourceErrors` 和 `issues` 的 code／hint，再看完整主图；主图无法读取时依序读取 slices。脚本等待字体、图片与布局稳定，分段捕获声明画布后无缩放拼接；保留完整图与诊断分片。超时记录未就绪，不改写元素的 opacity、transform 或 visibility 掩盖问题。

源码与资产按 [HTML 协议](../html/coding-rendering.md) 检查，画面按 [HTML 检查](html-validation.md) 复核。短链格式、自动报告和几何边界不能单独证明素材来源、身份、事实或视觉质量。

## 交付与失败

| 退出码 | 处理 |
| --- | --- |
| `0` | 自动检查通过，继续视觉复核。 |
| `1` | 检查完成并发现问题；对照截图与设计意图定位，修正后重跑，不改记为“预览未验证”。合理出血、局部裁切及光学对齐按实际可见效果判断。 |
| `3` | 执行失败，记录“预览未验证”，继续未被其他规则阻断的可完成部分。 |

集中处理同次检查发现的问题，再重跑受影响文件；连续出现同一告警时保留诊断并定位原因，不盲目增减高度。只有当前版本合格的完整预览进入 CDN＋Markdown；缺失或不合格时不展示，也不宣称完整完成。

预览问题本身不阻断默认 Canvas 的 HTML 上传、Item 创建与回读；源码和媒体门禁仍独立生效，已写入不免除修复。Mobile 无合格预览时说明可视交付未完成。具体上传、归档与卡片步骤统一执行 [交付验证](validation.md#4-默认-canvas-写入与媒体交付)。
