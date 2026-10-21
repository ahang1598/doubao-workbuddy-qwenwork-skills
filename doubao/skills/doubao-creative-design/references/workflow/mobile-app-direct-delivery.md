# Mobile App 直接文件交付

仅当 system 上下文明示 `Device platfrom: Mobile` 时使用。在 Workspace、Brief 存储或任何生成／编辑前确定 `delivery_environment=mobile_direct`；“手机尺寸”“移动端作品”不构成环境标记。未命中时继续默认 Canvas 交付。

## 生产与本地记录

保留主 SKILL 的全部品类路线和 short 顺序：HTML 路线执行唯一最小自然语言 Brief → 通用澄清并补全原 Brief → Spec／Visual 完善候选 Brief → 适用品类 KV → 冻结 Brief → ai-coding 轻量素材清单 → 素材生产 → 完整 HTML → 验证。纯 Coding 直接从冻结 Brief 进入 HTML，不建立图片清单。默认社媒套图走 pure-image，读取现有纯图平台 Ref 与 pure-image-sequence，以同一轻量 Brief 规划整套后逐页生成完整图片，不读取 Coding Spec／Visual。用户要求可编辑设计或文字时，套图才走 ai-coding，封面与内页均按正常素材生产和 HTML 原生文字组装；指定可编辑区域必须原生排字，封面不例外。已有 HTML 编辑保留原格式，不新增套图 KV，Mobile 交付权限与顺序不变。

本环境使用任务目录中的同一份 `brief.md` 和适用的 `asset-manifest.json`；连续编辑定位并增量更新原文件。事实、参考继承、核心身份母版、准确文案与资产版本规则不变。身份锚点保存可核验的真实来源与本地关联，不要求 Canvas ID。既有 HTML 输入沿完整 HTML 编辑；输入内容或资产不可取得时只阻塞依赖步骤，不为回读素材调用 Canvas CLI。

禁止调用 `+workspace-create`、`+get-workspace` 或任何 `design-cli`；不绑定、查询、复用或写入 Canvas，不创建 Item／Frame，不输出 Workspace ID 或画布卡片。已有画布上下文只作输入依据；当前对话存在唯一有效 Workspace ID 时，每次 `image_gen`／`image_edit` 调用必须将原始 ID 作为工具参数透传，仅用于媒体工具上下文，不授权 Canvas 操作。没有 ID 时不创建，直接调用并交付；ID 冲突、已有 ID 但参数不支持或校验失败时，按主 SKILL 停止，不省略 ID 降级重试。不得要求 Canvas path、Item ID、画布同步状态或创建 Workspace 中间文件。

## 能力预检

媒体生成／编辑需真实媒体工具及宿主可用的 `RichMediaCard` 交付能力，使用实际接口契约，不猜造字段。HTML 路线还需随包 `scripts/runtime/shot.py`（内部依赖 Playwright／Chromium、Pillow） 及用于上传预览截图的 `FileBatchUpload`；不把它误当作 Canvas 写入依赖而省略。缺少当前路线所需能力时按主 SKILL 返回 `RUNTIME_CAPABILITY_MISSING`，不假造交付。

## 图片与视频

图片／视频的每个成功结果使用 `RichMediaCard` 立即分别交付；用户另需的正式渲染／导出媒体同样适用，HTML 专用预览仍按下文 CDN＋Markdown 展示。串行任务当前项交付成功后才继续；并行仅限事先锁定且无依赖的批次，全部交付完成才进入依赖步骤。同锚点的 N 个同源变体分别调用 N 次 `image_edit`，每次使用同一已确认锚点。效果不佳或有图内文字问题的成功结果也先交付并标明问题；图内错字按原规则等待用户提出修改要求。交付失败停止后续生成、选图和依赖操作，保留真实部分完成状态。

## HTML

冻结 Brief 前检查是否要求点击跳转、提交、筛选或其他可运行交互。本环境只交付静态预览，不能完成这些运行目标；明确说明缺口，用户接受静态稿后在同一 Brief 更新目标再生产。未接受时保持该任务未完成，不以 PNG 冒充可运行作品。

1. 完整 HTML 仍须满足固定画布、准确文字和素材准出规则；样式遵循 HTML 协议。
2. 运行 `scripts/runtime/shot.py`，取得与声明宽高完全一致、包含页尾安全区的完整 PNG；完成真实视觉验收。
3. 用 `FileBatchUpload` 上传合格预览图到 CDN，核验返回的公网 HTTP(S) 链接，再逐项用 `![设计预览](https://cdn.example.com/preview.png)` 展示。图片 URL 逐字使用上传结果。
4. HTML 专用预览截图仅按 CDN＋Markdown 展示，不创建 IMAGE Item、不进入画布资产目录。工具临时预览、本地路径、普通链接不替代 CDN 图片展示。
5. 不上传或交付原始 `.html`，不创建 HTML Item，不输出画布卡片。完整源留在任务目录，供后续授权编辑。

## 完成条件

媒体分别通过 `RichMediaCard` 交付成功；每个 HTML 分别完成同尺寸完整预览、CDN 上传与 Markdown 图片展示，并通过自身内容和质量检查。记录 `delivery_environment=mobile_direct`、源版本、生成／编辑结果与交付状态，不伪造 Canvas 状态。预览失败时可保留本地源，但不得宣称 HTML 交付完成。

页面自检仅使用 shot.py；执行失败可跳过检查，保留未验证状态。Mobile 若无可用预览，不声称可视交付完成；不转用其他截图工具或创建画布。
