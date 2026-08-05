# Scenario: Mobile Design & Media Editing（设计 / 媒体编辑工具）

> **研究来源**：基于对 Adobe Photoshop iOS（flow_id 4766、4804）、Luminar AI（flow_id 5084、5090、5101）、Playground（flow_id 8991）、Denim（flow_id 5911）、VSCO 等真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: Consumer-facing Mobile App for creating, editing, and sharing visual content — including photo editing, graphic design, and AI-assisted image creation — using a touch-first canvas editor with tools, layers, templates, and export capabilities.

**Canonical Examples**: Adobe Photoshop for iOS（专业图片编辑）、VSCO（滤镜 + 图像编辑）、Canva iOS（模板创意设计）、Luminar（AI 图像增强）、Playground（AI 图像生成 + 设计）

**Not this scenario if**: 产品是视频剪辑（改用 mobile/entertainment 的 Media Editing 变体）；产品是文档/写作工具（改用 mobile/ai-assistant）；产品是社交相机发布（改用 mobile/consumer-social）；产品是 Web 端 Figma/Canva（改用 web/design-tools）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Creator / Designer（内容创作者，需要定制图片物料）；Non-designer（依赖模板和 AI 辅助）|
| **核心目标** | 选择模板或导入图片 → 在触摸屏上编辑（滤镜 / 文字 / 形状 / AI 增强）→ 导出分享 |
| **心智模型** | 熟悉 Instagram 滤镜概念；部分用户了解图层/蒙版；移动端使用手势（捏合缩放 / 拖拽）|
| **使用频率** | 中频（内容发布前处理，每次会话 10~30 分钟）|
| **决策模式** | 视觉驱动型：实时预览 → 调整 → 满意即导出；重视即时反馈 |
| **容错期望** | 低：误操作 = 严重；必须有 Undo/Redo；媒体库权限失效 = 无法工作 |

---

## IA Template

**导航模式**: 全屏 Canvas Editor（无传统 Tab Bar）+ Projects Gallery Home

- **Home / Projects Gallery**：用户的设计稿缩略图列表 + 创建入口（`+` 按钮）
- **Canvas Editor**：全屏编辑区域，底部 Tools Toolbar（可滚动），顶部 Top Bar（标题 + 保存 + 分享/导出）
- **Layer Panel**（可选）：Bottom Sheet，显示图层层级

**页面层级**: 2 级（极浅，L2 即主工作区）
```
L1: Projects Gallery（项目列表 + 创建入口）
L2: Canvas Editor（全屏编辑器，Touch-first）
    ├── Tools Toolbar（底部可滚动）
    ├── Properties Sheet（选中元素后展开）
    └── AI Generation / Template Sheet（特定工具触发）
```

注：移动端设计工具没有 Web 版的三栏布局，所有面板以 Bottom Sheet 呈现，Canvas 全屏为主。

**权限角色结构**:
```
Free User    → 基础工具 + 有限模板 + 有水印导出
Pro / Premium → 全量模板 + 高级 AI 功能 + 无水印导出（应用内订阅）
```

**媒体权限请求（按需请求）**:
```
媒体库（读取）→ 用户点击「Import from Photos」时触发
摄像头       → 用户点击「Camera Capture」时触发
媒体库（写入）→ 用户点击「Save to Camera Roll」时触发
```

**数据密度**: 低（Gallery：卡片式缩略图；Canvas：工作区主导，底部工具栏收起时 UI 极简）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 新建项目 / 选择模板 | Bottom Sheet（Large）或全屏页面 |
| 工具属性设置（颜色 / 字体 / 透明度）| Bottom Sheet（Medium）或动态 Bottom Sheet |
| 图层管理（Layer Panel）| Bottom Sheet（Large，从底部弹出）|
| 元素操作（Context Menu）| 长按弹出上下文菜单 |
| 导出设置（格式 / 质量）| Bottom Sheet（Medium，不离开 Canvas）|
| 分享 | 系统分享面板 + 自定义导出选项 |
| Premium 功能 Paywall | Bottom Sheet（应用内订阅，有 X 关闭按钮）|
| AI 生成（Prompt 输入）| Bottom Sheet（Large）或全屏 Modal |

**Canvas Editor 骨架图（ASCII）**:
```
┌─────────────────────────────────────────┐
│  ✕  My Design — Summer Post    💾  ↑  │  ← Top Bar（标题 + 保存状态 + 导出）
├─────────────────────────────────────────┤
│                                         │
│                                         │
│           ┌─────────────┐               │
│           │             │               │
│           │  [CANVAS]   │  ← 手势: 捏缩 │
│           │  [selected] │    拖拽移动   │
│           │  □·······□  │               │
│           └─────────────┘               │
│                                         │
├─────────────────────────────────────────┤
│  [Select][Text][Image][Shape][Draw][AI] │  ← Tools Toolbar（横向滚动）
└─────────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **全屏 Canvas + Bottom Sheet 是移动端设计工具的核心 IA 约束，不是 Web 三栏布局的简化版** — Web 设计工具（Figma、Canva Web）采用固定三栏布局（Left Panel + Canvas + Right Properties），这在手机全屏空间下无法实现。移动端必须使用：全屏 Canvas 为主视图 + 底部可滚动 Tools Toolbar + 选中元素后动态弹出 Bottom Sheet（属性面板）。用户每次调整属性都在「Canvas 操作」和「Bottom Sheet 输入」之间切换，因此 Bounding Box 上的直接操作手柄（旋转 / 缩放圆点）至关重要——它让用户在不触发 Sheet 的情况下完成最频繁的变换操作。

2. **Properties Sheet 必须「内容感知型」切换，选中什么显示什么** — 选中文字图层 → Sheet 显示字体 / 颜色 / 对齐；选中图片图层 → 显示裁剪 / 滤镜 / 透明度；选中形状 → 显示填充 / 描边 / 圆角；未选中任何 → 显示画布属性。切换必须无感知（< 100ms）。Adobe Photoshop iOS（flow_id 4766）的文字属性 Bottom Sheet 是标准实现参考。如果 Properties Sheet 的内容不随选中对象切换（保持同一套工具），用户会持续在工具间切换浪费操作步骤，大幅降低编辑效率。

3. **AI 生成必须在 Canvas Editor 内就地完成，不能跳出到独立 AI 页面** — Adobe Photoshop iOS（flow_id 4804）是正确范本：AI 工具入口在 Tools Toolbar → Prompt 输入 + 生成进度在 Bottom Sheet → 多变体结果在 Sheet 内选择 → 直接插入 Canvas 为新图层，全程不离开 Canvas Editor。如果 AI 功能跳出到独立工具页面，用户完成生成后需要下载再导入，摩擦极大；且生成结果在「独立 AI 页」的空间上下文中丧失了「尺寸是否合适」的判断依据——只有在 Canvas 内才能直观看到生成图像与当前设计的比例关系。

4. **导出流程有三条路径，必须在 Export Sheet 顶层明确分叉** — Luminar（flow_id 5099）展示了正确的三路径模式：「Save to Photos」（替换原图，需媒体库写入权限）/ 「Save a Copy」（生成新文件，也需权限）/ 「Share」（系统分享面板，无需媒体库权限）。三条路径对应截然不同的用户意图，必须在 Export Sheet 顶层以清晰的选项卡或分组按钮呈现，不能合并后再在深层步骤分叉。关键点：媒体库权限被用户拒绝时，「Share」必须作为无障碍 fallback 始终可用——否则拒绝了权限的用户彻底无法导出文件。

5. **Undo/Redo 必须支持多级历史（30步+）且通过手势触发，不只依赖 Top Bar 按钮** — 设计工作涉及大量 A/B 探索（尝试 → 不满意 → 撤销 → 再试），Undo 历史必须足够深（30步以上）。移动端手势是三指左扫 Undo / 三指右扫 Redo（与系统级撤销手势同级）——手势让用户不移手就能快速撤销，而 Top Bar 按钮则作为「可发现的入口」供不知道手势的用户使用。两者必须共存：只有 Top Bar 按钮意味着用户需要频繁将手从画布移至导航区，打断创作节奏。

---

## Canonical Flows

### Flow 1: 从模板创建并编辑（Create from Template & Edit）

**在此场景的特殊性**: 移动端设计工具的模板选择是视觉化网格（不是文字列表）；模板加载时必须有明确进度指示（大模板文件可能需要 1-3 秒）；进入编辑器后 Auto-save 在后台持续工作，用户不需要手动保存；Properties Sheet 根据选中元素自动切换内容（文字工具 vs 形状工具 vs 图片工具的底部 Sheet 完全不同）

**Entry**: 用户在 Projects Gallery 点击「Create New Design」或「+」按钮

**Screens**:
```
Screen 1: Projects Gallery
  主操作: 点击「+ Create New」或浏览已有项目
  关键组件:
    - NavigationBar: App Logo + Button「+」（Create New，右上角突出）
    - 最近项目 Grid（2 列缩略图 + 项目名 + 编辑时间）
    - Button「Create New Design」（若无项目则全屏 CTA）
    - 长按 Card: 上下文菜单（Rename / Duplicate / Delete）
  → 点击「+ Create New」: Bottom Sheet → Screen 2（模板选择）
  → 点击已有项目 Card: → Screen 3（Canvas Editor 直接打开）

Screen 2: Template Selection（模板选择 Sheet）
  主操作: 选择模板或创建空白画布
  容器: Bottom Sheet（Large）或全屏页面
  关键组件:
    - 搜索框（模板名搜索）
    - Category Tabs（横向滚动：All / Social Post / Story / Poster / Card / Custom）
    - 网格模板卡片（可视化缩略图 + 名称 + 尺寸）
    - 「Blank Canvas」选项（网格第一个，纯色带 + 号）
    - 尺寸选项（Custom 选项：Width × Height 输入，单位 px/cm）
  → 点击模板: → Screen 3（Canvas Editor，模板加载动画）

Screen 3: Canvas Editor
  主操作: 在 Canvas 上编辑元素
  关键组件:
    - Top Bar: 「✕」返回 / 关闭 + 项目标题（可点击重命名）+ 自动保存状态 + 「↑」导出按钮
    - Canvas（全屏工作区，触摸手势：单指拖拽元素，双指捏合缩放画布，双击进入编辑）
    - 选中元素时显示 Bounding Box（圆形控制手柄，拖拽缩放/旋转）
    - Bottom Tools Toolbar（横向 ScrollView）: Select / Text / Image / Shape / Draw / Sticker / AI
    - Properties Sheet（元素选中后动态展开）: 属性随选中类型变化
    - Undo / Redo（Top Bar 或三指手势）
  → 点击 Text 工具: Bottom Sheet 展开 → Screen 3a（文字编辑）
  → 点击 Image 工具: 触发媒体库权限 → 图片选择器 → Screen 3b（图片编辑）
  → 点击 AI 工具: Bottom Sheet → Screen 3c（AI 生成）
  → 点击导出按钮: Bottom Sheet → Screen 4（导出设置）

Screen 3a: Text Layer Properties（动态 Bottom Sheet）
  主操作: 输入并设置文字样式
  关键组件:
    - 系统键盘（文本输入区域）
    - Font 选择 Carousel（横向滚动，字体名预览）
    - Bold / Italic / Underline Toggle Row
    - Text Size Slider（实时更新 Canvas）
    - Color Picker（Swatch 圆点横排 + 自定义颜色选择）
    - Alignment ToggleGroup（Left / Center / Right / Justify）
    - Button「Done」（收起键盘，确认文字）
```

**Exit State**: 设计稿自动保存，返回 Gallery 出现新缩略图（带标题和编辑时间）
**Empty State**: Gallery 无项目时显示空状态：「No designs yet」+ Button「Create your first design」

---

### Flow 2: 图像编辑 + 导出（Photo Edit & Export）

**在此场景的特殊性**: 移动端图像编辑的工具操作必须实时更新预览（不是点击「Preview」才更新）；调节类工具（亮度 / 对比度 / Slider）通过弧形 Slider 或水平 Slider 精确控制；导出前须请求媒体库写入权限（用户有可能拒绝，须有 fallback：「Share instead」）；导出完成通过 Toast + 通知告知用户（不阻塞 Canvas）

**Entry**: 用户在 Canvas Editor 点击 Top Bar「↑」导出按钮，或在 Photo Editor 完成编辑后点击「Done」

**Screens**:
```
Screen 1: Canvas Editor（完成编辑状态）
  主操作: 点击「↑」Export / Done 按钮
  关键组件（同 Flow 1 Screen 3，已完成编辑）
  → 点击导出按钮: Bottom Sheet → Screen 2

Screen 2: Export Settings Sheet
  主操作: 配置导出参数，选择导出路径
  容器: Bottom Sheet（Medium），Canvas 仍在背景可见
  关键组件:
    - Sheet Header: 「Export」+ Button「✕」
    - 三路径分叉（顶层选择，分段控件或三个按钮）:
        「Save to Photos」— 替换原图（需媒体库写入权限）
        「Save a Copy」— 生成新文件保存到相册（需媒体库写入权限）
        「Share...」— 系统分享面板（无需媒体库权限，直接发往其他 App）
    - 文件格式选择（RadioGroup / Picker）: JPEG / PNG / TIFF / HEIF（图片类）；MP4 / GIF（含动画时）
    - 质量 Slider（JPEG: Low / Medium / High / Best；PNG / TIFF: 无压缩选项）
    - 尺寸倍率 SegmentedControl（1x / 2x / 3x，仅静态图片）
    - 预计文件大小（Label 实时更新）
    - Button「Export」（主 CTA，全宽，选定路径后激活）
    - 媒体库权限被拒时: 前两条路径显示 disabled + 说明文字「Photos access required」+ Button「Open Settings」；「Share...」路径始终可用作 fallback
  → 选择「Save to Photos / Save a Copy」: 请求媒体库写入权限 → 权限同意 → Screen 3
  → 选择「Share...」: 系统分享面板（无权限门槛）

Screen 3: Export Progress / Completion（Toast 或 Banner）
  主操作: 等待导出完成（后台）
  关键组件:
    - Canvas 保持可用（用户可继续编辑）
    - Top Banner 或 Toast（导出中...）
    - 导出完成: Toast「Saved to Photos · View」（tap 可跳转至系统相册）
  Exit: Canvas 保持打开，用户可继续编辑或返回 Gallery
```

**Exit State**: 图片已保存至相册；Canvas 保持打开；Toast 提供「View」快捷入口
**Empty State**: 不适用

---

### Flow 3: AI 生成图像并插入（AI Image Generation & Insert）

**在此场景的特殊性**: AI 生成是移动端设计工具最新的差异化功能；用户必须先同意 AI 生成使用条款（一次性，之后不再弹出）；Prompt 输入后有明确的生成等待状态（进度指示 + 动画，通常 3-10 秒）；生成结果以多个变体展示（4 张缩略图供选择，不是直接插入）；选择变体后图像以新图层形式插入 Canvas，用户可继续编辑

**Entry**: 用户在 Canvas Editor 点击 Tools Toolbar 的「AI」工具按钮

**Screens**:
```
Screen 1: AI Tools Picker（工具选择）
  主操作: 选择 AI 功能类型
  容器: Bottom Sheet（Medium）弹出
  关键组件:
    - AI 功能列表: 「Generate Image」/ 「Background Removal」/ 「Style Transfer」/ 「Enhance」
    - 每项功能有简短说明和示例缩略图
  → 点击「Generate Image」: → Screen 2（AI 同意 + Prompt）

Screen 2: AI Image Generation（Prompt 输入）
  主操作: 输入描述文字，生成 AI 图像
  容器: Bottom Sheet（Large）或 Full-screen Modal
  关键组件:
    - AI 使用条款说明（首次，Button「I agree」/ 「Learn More」）
    - TextArea「Describe the image you want...」（Prompt 输入）
    - Chips（预设建议 Prompt：「Sunset landscape」/ 「Abstract pattern」/ 「Neon city」）
    - Style 选择（可选：Photo / Illustration / Art / 3D）
    - Button「Generate」（主 CTA，输入不为空时激活）
    - 生成中: 圆形进度指示 + 文字「Creating your image...」
  → 点击「Generate」: 生成中 → Screen 3

Screen 3: AI Generation Results（结果选择）
  主操作: 选择一个 AI 生成变体插入 Canvas
  关键组件:
    - 2×2 结果网格（4 个变体缩略图）
    - 选中态（蓝色边框 + 对勾）
    - Button「Regenerate」（ghost，用同一 Prompt 重新生成）
    - Button「Use This Image」（主 CTA，选中后激活）
  → 点击「Use This Image」: Sheet dismiss，图像作为新图层插入 Canvas，Toast「Image added」
  → 点击「Regenerate」: 回到生成中状态
```

**Exit State**: AI 生成的图像作为新图层出现在 Canvas，图层被选中可继续编辑（移动 / 缩放 / 遮罩）
**Empty State**: 生成失败（网络错误）：Toast「Generation failed · Try again」，Button「Retry」

---

### Flow 4: Share to Social with Branded Card（导出分享卡片到社交平台）

**在此场景的特殊性**: 设计工具 App 的「导出到社交平台」与 Flow 2 的「原始文件保存」是两套截然不同的路径——Flow 2 关注文件质量（格式/分辨率），Flow 4 关注平台适配（长宽比/品牌水印）。Chance AI（flow_id 7356，7 屏）是该模式的最完整实现：Share Card 页面提供横向模板 Carousel（1:1 正方形 / Instagram Post / Instagram Story 9:16），切换时预览即时更新（< 200ms）；操作区永远有两个并列 CTA：「Save Image」（蓝色主按钮，需媒体库权限）和「More」（白色次要按钮，打开 iOS 系统分享面板，无需媒体库权限）。komoot（flow_id 8412，10 屏）的「Activity Share Composer」展示了在生成合成图像前先选择布局（All/Stats/Map）、再选背景图的「分步合成」模式，适合内容更复杂的设计作品分享。Tilt（flow_id 3082，5 屏）记录了「生成进度 → 完成 → 才触发媒体库权限」的异步权限时机——权限请求应在内容准备就绪、用户明确看到价值后触发，而非提前弹出。**平台模板预计算长宽比**（1:1、4:5、9:16、16:9）是该 flow 的核心设计——用户只需选「Instagram 贴文」，不需要知道 1080×1080px 这样的技术参数。

**行业共识**：Chance AI（flow_id 7356）和 TIDE（flow_id 6758）均将「Save Image」（主色，需权限）和「More」（次要，系统分享）并列展示，「More」永远作为无权限 Fallback；模板切换时预览即时刷新是行业共识（无「确认」步骤）。

**Entry**: Canvas Editor Top Bar → 点击「↑ Share」或「分享」图标（与 Flow 2 的「↑ Export / Save」是不同的入口）

```
Screen 1: Canvas Editor（完成编辑）
  主操作: 点击 Top Bar「分享」图标（↑ 或 社交分享图标）
  关键组件（同 Flow 1 Screen 3，已完成编辑状态）
  区分 Flow 2 的「Save to Photos」与 Flow 4 的「Share」: Top Bar 通常有两个不同图标
    - 「↓」或「💾」: 保存原始文件（Flow 2 路径）
    - 「↑」或「⊕ 分享」: 社交分享卡片（Flow 4 路径）
  → 点击「分享」图标: 进入 Screen 2（Share Card Composer）

Screen 2: Share Card Composer（分享卡片合成器）
  主操作: 选择社交平台模板 → 调整水印设置 → 选择导出方式
  容器: Bottom Sheet（Large）或全屏页面
  关键组件:
    - 顶部导航: 「← 返回」+ 标题「分享」（Share）
    - 卡片预览区（居中，全宽，带圆角阴影）:
        根据选中模板实时更新长宽比和布局
        内容: 设计作品缩略图 + 应用 Logo 水印（右下角）
        样式: 品牌背景色/渐变覆盖层 + 白色文字（项目名 + 创建日期）
    - 平台模板横向 Carousel（单行，可滚动）:
        每个模板项: 平台图标 + 名称（如 Instagram 图标 + 「Instagram 帖子」）
        选中状态: 蓝色边框高亮，其他灰色
        选项（从左到右）: 「1:1 正方形」/ 「Instagram 帖子 4:5」/ 「Instagram Story 9:16」/ 「Twitter/X 16:9」/ 「TikTok 9:16」
    - 水印选项（Toggle 行）:
        「显示应用水印」Toggle（Free 用户: 强制开启，已锁定，点击 → Paywall Sheet）
        （Pro 用户: 可关闭）
    - 底部操作区（两个并列 Button）:
        Button("More", 次要样式，白底黑字): 打开 iOS 系统分享面板（无需媒体库权限）
        Button("Save Image ↓", 主色，蓝底白字): 保存到相册（需媒体库权限）
    - 底部提示文字（灰色小字，居中）: 「分享即传播创意 ✨」
  → 点击模板项: 卡片预览即时更新（< 200ms，不需要点「确认」）
  → 点击「More」: iOS 系统分享面板弹出（Screen 3a）
  → 点击「Save Image」: 检查权限 → 首次触发 Screen 3b（权限弹窗），已授权则直接 Screen 4
  → 点击水印 Toggle（Free 用户）: Paywall Bottom Sheet 弹出（订阅解锁水印关闭）

Screen 3a: iOS 系统分享面板（点击「More」触发）
  主操作: 选择分享目标
  容器: iOS 原生 Share Sheet（底部弹出）
  关键组件（iOS 原生 UI，App 无法自定义）:
    - 顶部 App 横排（AirDrop / Messages / Mail / Instagram / 更多...）
    - 下方操作列表（Copy / Save to Files / Open in...）
    - 「Cancel」关闭按钮（右上角 X）
  → 点击 Instagram: 打开 Instagram 分享 Composer（传递图像）
  → 点击「Save to Files」: 文件保存到 iCloud Drive
  → 点击 Messages: Messages Composer 打开，图像作为附件插入
  → 关闭 Sheet: 返回 Screen 2（Share Card Composer 保持打开）

Screen 3b: 媒体库写入权限（首次点「Save Image」触发）
  主操作: 授权媒体库写入
  容器: iOS 系统原生权限弹窗
  关键组件（iOS 原生 UI）:
    - 标题: 「"[App 名]"想访问你的照片」
    - 说明: 「允许应用将图片保存到你的相册」
    - 选项: 「允许访问全部照片」/ 「允许添加照片」/ 「不允许」
  → 允许: 进入 Screen 4（保存确认）
  → 「不允许」: Toast 提示「相册权限已拒绝，可通过系统设置开启」+ Button「打开设置」；Share Card Composer 保持开启，「More」路径始终可用

Screen 4: 保存确认
  主操作: 确认图像已保存
  容器: Toast（非阻塞，3 秒后自动消失）
  关键组件:
    - Toast（底部浮层）: 「已保存到相册」+ Button「查看」（点击 → 跳转系统相册该图片）
    - Share Card Composer 保持在后台（可继续切换模板保存其他尺寸）
    - 可选 Toast 快捷操作: Button「发布到 Instagram」（深链接跳转 Instagram，传递已保存图片）
  Exit: Toast 消失，Sheet 保持开启；用户可继续切换模板保存其他平台尺寸，或关闭 Sheet 返回 Canvas
```

**Exit State**:

- ✅ Save Image 成功：Toast「已保存到相册 · 查看」，Sheet 保持开启可继续切换模板
- ✅ 系统分享（More）：iOS Share Sheet 弹出，用户选择目标后 Sheet 关闭
- ❌ 媒体库权限拒绝：Toast 引导去系统设置，「More」路径始终可用作 Fallback
- ↩ 关闭 Share Card Composer：Sheet dismiss，返回 Canvas Editor

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `Popup`（medium / large）| `BottomSheet`（medium / large）| 模板选择 / 属性面板 / 导出 / AI 生成 / Paywall |
| ★★★ | `Grid` | `FlatList`（numColumns=2）| Projects Gallery（2 列缩略图）；模板选择网格；AI 结果网格 |
| ★★★ | `Slider` | `Slider` | 图像参数调节（亮度 / 对比度 / 透明度）；导出质量；AI 强度 |
| ★★★ | `Toast` | `Toast` | 「Saved to Photos」/ 「Image added」/ 「Undo」操作反馈 |
| ★★ | `Radio` + `RadioGroup` | `Radio` + `RadioGroup` | 导出格式选择（PNG / JPG / PDF）；订阅计划选择 |
| ★★ | `Selector` / `Tabs` | `SegmentedControl` | 导出倍率（1x / 2x / 3x）；对齐方式（Left / Center / Right）|
| ★★ | 图片选择器（原生桥接）| `ImagePickerAsset` / `expo-image-picker` | 导入照片（媒体库权限）|
| ★★ | 文件选择器（原生桥接）| `expo-document-picker` | 导入本地文件（PDF / SVG 等）|
| ★★ | 上下文菜单（长按触发）| `ContextMenu` / `Menu` | 项目卡片操作（Rename / Duplicate / Delete）；图层操作 |
| ★ | 颜色选择器（自定义）| `ColorPicker`（第三方）| 颜色选择（形状填色 / 文字颜色）|

---

## Anti-Patterns

- **进入编辑器不显示自动保存状态（No auto-save indicator in editor）**: 用户不知道修改是否已保存，焦虑频繁手动点保存或意外丢失工作 → 正确做法：Top Bar 始终显示自动保存状态（「Saved」/ 「Saving...」/ 「Unsaved」），进入编辑器后立即激活 Auto-save
- **调整工具不提供实时预览（No live preview for adjustments）**: 用户拖动 Slider 调节亮度/对比度，需点击「Preview」才能看到效果 → 正确做法：所有调节操作（Slider 拖动 / 颜色切换 / 样式选择）必须实时更新 Canvas 预览（无按钮确认步骤）
- **媒体库权限拒绝后无 fallback（No fallback when Photos denied）**: 用户拒绝媒体库权限后，导出 / 导入功能直接不可用，无任何引导 → 正确做法：权限拒绝时保持「Share...」路径始终可用（系统分享面板不需要媒体库权限），同时显示「Open Settings」引导用户手动开启权限
- **AI 生成直接插入无变体选择（AI generation inserts without preview）**: AI 图像生成后直接插入 Canvas，用户无法选择最满意的变体 → 正确做法：生成后展示多个变体（2-4 张缩略图）供用户选择，提供「Regenerate」重新生成，确认选择后才插入
- **导出路径未区分三种意图（Export paths not clearly separated）**: 导出 Sheet 只有「Save」和「Share」，用户想保留原图同时存副本时找不到对应选项 → 正确做法：Export Sheet 顶层明确列出「Save to Photos（替换原图）/ Save a Copy（新文件）/ Share（系统共享）」三条路径（Luminar flow_id 5099 模式），让用户在选择路径时就清楚操作后果
- **Undo 只有 Top Bar 按钮无手势支持（Undo limited to toolbar button）**: 用户在 Canvas 上编辑时需要反复将手移到 Top Bar 点击 Undo，打断创作节奏 → 正确做法：实现三指左扫 Undo / 三指右扫 Redo 手势（与移动端系统撤销手势一致），同时保留 Top Bar 按钮作为可发现入口；Undo 历史深度必须支持 30 步以上
