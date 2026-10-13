# VI HTML 交付规范路由入口

本文件是 VI／品牌视觉识别系统命中 `ai-coding` 后的 HTML 交付规范入口。它只负责路由和优先级，不替代 VI Spec、VI Visual 或各被引用协议的正文。

## 何时读取

只要当前请求是新建、续做、修改、返修或交付 VI／品牌视觉识别系统，并且最终作品由完整 HTML 组织，就必须在任务初始 `required_refs` 阶段读取本文件。禁止等到素材完成、开始写 HTML、运行 `shot.py` 或准备交付时才读取。

读取本入口后，必须立即完整读取下列公共 Ref，不得懒加载：

1. [HTML 组装](html-assembly.md)：Subagent 的完整 HTML 组装、素材绑定与返修职责。
2. [HTML/CSS 固定画布与交付协议](../html/coding-rendering.md#html-fixed-canvas-delivery)：唯一完整 HTML、固定画布、同尺寸预览、顶层 HTML Item 和禁止直接交付源文件。
3. [HTML 检查执行流程](html-validation.md)：`shot.py` 自检、同尺寸完整预览和平台闭环验证。

随后按 system 环境立即补齐一个且仅一个分支：

- **默认 Canvas**：完整读取 [CLI 策略](../cli/README.md)、[create 协议](../cli/create.md) 与 [HTML Item 协议](../items/HTML.md)。需要新建 Workspace 时同时读取 CLI 策略中的 Workspace 创建入口。默认 Canvas 必须具备 `FileBatchUpload`、`design-cli` 和 `present_files`。
- **`Device platfrom: Mobile`**：完整读取 [Mobile 直接交付](mobile-app-direct-delivery.md)，不得再读取或执行默认 Canvas 的 Workspace／CLI／Item 创建分支。

本路由与 [VI Spec](../style/coding/scenarios/vi-spec.md) 的最高优先级门禁共同生效。若公共 HTML 规则允许多个独立作品或分页多 Item，完整 VI 在本任务中仍视为一个作品，以 VI Spec 的“唯一完整 HTML＋唯一顶层 HTML Item”覆盖。

## 执行主体

- **Subagent**：有且仅负责完整 HTML 生成／修改、同一 HTML 的返修，以及使用 `scripts/runtime/shot.py` 自检；完成后把本地 HTML、声明尺寸、同尺寸本地预览、校验状态、建议 `path`、完整 `brief` 和创建意图内部回传 Main Agent，然后停止。
- **Main Agent**：负责所有 CDN 上传、公网链接核验、Markdown 展示、`FileBatchUpload`、Workspace、CLI `+create`／`+get`、`present_files` 和最终用户交付。
- 除 HTML 生成／修改与 `shot.py` 自检外，VI 的其他阶段不得委派 Subagent；本入口不扩大 Subagent 权限。

## 用户可见交付与内部载荷

完整 `.html` 仅是内部作品源、`FileBatchUpload` 载荷和 HTML Item 内容来源。禁止通过聊天文件链接、Markdown、附件、压缩包、代码块、本地路径或 `present_files` 直接交付 `.html`。用户可见交付只有：

1. CDN 公网链接承载的同尺寸完整预览图，以 Markdown 图片语法展示；
2. 默认 Canvas 环境中唯一顶层 HTML Item 对应的画布卡片。

## 固定交付顺序

### 两种环境共同执行

1. Subagent 完成唯一完整 HTML，并使用 `shot.py` 自检。
2. Main Agent 核对预览图像素尺寸与 HTML 的 `data-canvas-width`、`data-canvas-height` 一致。
3. Main Agent 将完整预览图上传 CDN 并核验公网 HTTP(S) 链接，再以 Markdown 图片展示。预览图不得调用 `present_files`、不得创建 IMAGE Item、不得写入 Workspace 或资产目录。

### 默认 Canvas 继续执行

4. Main Agent 使用 `FileBatchUpload` 上传唯一完整 HTML，取得原始短链；该上传是内部持久化输入，不是源文件交付。
5. Main Agent 使用短链执行 `design-cli ... +create`，只创建一个顶层 `<item type="HTML">`。`HTML` 是 Item 类型，`+HTML` 不是命令；禁止 HTML Frame、Frame 成员 HTML、章节多 Item 和分页多 Item。
6. Main Agent 取得 Item ID 后执行 `design-cli ... +get`，回读核对对象 ID、`type`、`path`、`brief`、尺寸和 HTML 资产短链。
7. 回读成功后，Main Agent 将 `"<workspace_id>?item_id=<item_id>"` 作为单值传给 `present_files`，交付唯一画布卡片。

### Mobile 到此停止

Mobile 完成第 1–3 步后立即停止。禁止 `FileBatchUpload` HTML、Workspace、Canvas CLI、Item、回读和画布卡片；也禁止用直接交付 `.html` 补偿缺失的 Canvas 能力。

## 完成判定

- 缺少 CDN＋Markdown 同尺寸完整预览，不得标记 VI 交付完成。
- 默认 Canvas 缺少 HTML `FileBatchUpload`、唯一顶层 HTML Item、`+get` 回读或 `present_files("<workspace_id>?item_id=<item_id>")` 任一步，不得标记完成。
- Mobile 出现 HTML 上传、Workspace、CLI、Item 或画布卡片即为路由错误。
- 出现直接 `.html` 文件交付、HTML Frame、章节多 Item、分页多 Item、Subagent 上传／写入／交付，即为硬失败。
