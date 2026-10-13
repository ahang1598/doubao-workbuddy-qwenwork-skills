---
name: design-md
version: 1.0.0
description: AI UI 设计系统助手。当用户需要生成特定品牌风格的 UI、选择设计系统、应用设计规范、让页面看起来像某个知名网站、或提到 DESIGN.md 时使用。支持 68 个品牌风格（内置离线模板），包括 Stripe、Vercel、Airbnb、Apple、Tesla、Notion、Linear 等。
install_source: official
install_method: download
skill_id: official_vUIqvhox
enabled_at: 1791893745723
name_zh: 大厂设计系统
---

# Design.md — AI UI 设计系统 Skill

通过 `npx getdesign@latest` 命令为项目安装品牌级设计系统（DESIGN.md），让 AI Agent 生成像素级还原的 UI。

## 什么是 DESIGN.md

DESIGN.md 是 Google Stitch 提出的概念：一个纯 Markdown 格式的设计系统文档，AI Agent 读取后即可生成风格一致的 UI。无需 Figma、无需 JSON，零配置。

| 文件 | 读者 | 定义 |
|------|------|------|
| `AGENTS.md` | 编码 Agent | 如何**构建**项目 |
| `DESIGN.md` | 设计 Agent | 项目应该**长什么样** |

## 严格禁止 (NEVER DO)

- 不要编造设计 token（颜色、字号、间距等），必须从 DESIGN.md 中提取
- 不要同时安装多个品牌的 DESIGN.md 到同一项目（会冲突）
- 不要修改已安装的 DESIGN.md 内容，除非用户明确要求定制

## 严格要求 (MUST DO)

- 安装前必须确认用户的项目根目录路径
- 安装前检查项目根目录是否已存在 DESIGN.md，如已存在需告知用户会被覆盖
- 生成 UI 时必须严格遵循 DESIGN.md 中定义的色彩、字体、组件规范
- 推荐品牌时至少给出 2-3 个选项，附带风格描述，让用户选择
- 生成 HTML 后必须保存文件并引导用户在浏览器中打开查看完整效果

## 品牌总览

共 66+ 个品牌，按行业分类。完整目录见 [brand-catalog.md](./references/brand-catalog.md)。

| 行业 | 代表品牌 | 风格关键词 |
|------|---------|-----------|
| AI & LLM | Claude, Cohere, Mistral AI, Ollama, xAI | 暗色/科技感/极简 |
| 开发工具 | Cursor, Vercel, Raycast, Warp, Expo | 暗色/代码风/渐变 |
| 后端 & DevOps | Supabase, MongoDB, Sentry, PostHog | 暗色/数据密集/开发者友好 |
| 效率 & SaaS | Notion, Linear, Cal.com, Zapier | 极简/温暖/阅读优化 |
| 设计工具 | Figma, Framer, Miro, Webflow | 多彩/活泼/创意 |
| 金融科技 | Stripe, Coinbase, Revolut, Wise | 渐变/信任感/精致 |
| 电商 & 零售 | Airbnb, Shopify, Nike | 摄影驱动/圆角/品牌色强烈 |
| 媒体 & 消费 | Apple, Spotify, Uber, SpaceX | 高端留白/全屏图片/未来感 |
| 汽车 | Tesla, BMW, Ferrari, Lamborghini | 暗色奢华/电影感/定制字体 |

## 意图判断决策树

用户提到"做个像 XX 的页面/风格" → 从品牌目录匹配 XX
用户提到"暗色/科技感/极简" → 推荐 AI & LLM 或开发工具类品牌
用户提到"温暖/友好/圆角" → 推荐 Airbnb / Notion / Cal.com
用户提到"高端/奢华/电影感" → 推荐 Apple / Tesla / Ferrari
用户提到"数据密集/仪表盘" → 推荐 Sentry / PostHog / Kraken
用户提到"支付/金融" → 推荐 Stripe / Coinbase / Revolut
用户提到"渐变/活泼/多彩" → 推荐 Figma / Framer / Spotify
用户提到"极简/黑白" → 推荐 Vercel / SpaceX / Uber
用户提到"开发者文档" → 推荐 Mintlify / Hashicorp / ClickHouse
用户提到"设计系统/DESIGN.md" 但未指定品牌 → 展示品牌总览让用户选择
用户直接说品牌名 → 直接安装对应品牌

## 核心流程

### Step 1 — 理解需求

判断用户意图：
- **明确品牌**：用户说"用 Stripe 风格" → 直接进入 Step 3
- **描述风格**：用户说"暗色科技感" → 进入 Step 2 推荐
- **模糊需求**：用户说"帮我选个设计系统" → 询问场景和偏好

### Step 2 — 推荐品牌

根据意图判断决策树，从 [brand-catalog.md](./references/brand-catalog.md) 中选出 2-3 个匹配品牌，展示给用户：

```
推荐以下设计系统：
1. **Stripe** — 标志性紫色渐变，font-weight 300 优雅感，适合支付/SaaS
2. **Linear** — 极致极简，精确紫色点缀，适合工程师工具
3. **Vercel** — 纯黑白精确，Geist 字体，适合开发者平台

请选择一个，或告诉我更多偏好。
```

### Step 3 — 获取 DESIGN.md

本 Skill 已内置全部 68 个品牌的 DESIGN.md 模板，位于 `references/brands/` 目录。

**方式 A — 读取内置模板（优先）**

使用 `read_file` 直接读取 Skill 内置的品牌模板：
```
read_file: references/brands/<brand>.md
```
读取后将内容写入用户项目根目录的 `DESIGN.md`。

**方式 B — curl 下载（内置文件不可用时）**
```bash
cd <project_root>
curl -o DESIGN.md "https://cdn.jsdelivr.net/npm/getdesign@latest/templates/<brand>.md"
```

**方式 C — npx 安装（完整环境可用时）**
```bash
cd <project_root>
npx getdesign@latest add <brand>
```

> **品牌文件名对照**：文件名即品牌标识（如 `stripe.md`、`vercel.md`、`posthog.md`、`linear.app.md`）。完整列表见 [brand-catalog.md](./references/brand-catalog.md)。

安装后确认项目根目录已存在 `DESIGN.md` 文件。

### Step 4 — 读取并应用

安装完成后：
1. 使用 `read_file` 读取项目根目录的 `DESIGN.md`
2. 理解其中的色彩体系、字体规则、组件样式、布局原则
3. 按照规范生成或修改用户的 UI 代码

> **关于汉化**：安装的 DESIGN.md 默认为英文，不影响 AI 生成 UI 的质量。读取完成后需主动告知用户："DESIGN.md 已安装，当前为英文版。需要我翻译为中文方便您查看吗？"用户同意则执行汉化（章节标题保留英文+中文，技术值不动），用户拒绝或未回应则直接进入 Step 5。

### Step 5 — 生成 UI

根据 DESIGN.md 中的规范，生成完整的、可独立运行的 HTML 文件。生成时必须严格遵循：
- 使用 DESIGN.md 中定义的精确 HEX 颜色值
- 使用指定的字体族和字号层级
- 遵循组件样式（按钮圆角、阴影、hover 状态等）
- 遵循布局原则（间距比例、网格、留白）
- 遵循 Do's and Don'ts 设计护栏

**HTML 自包含要求**：
- 生成的 HTML 必须是完整的单文件，包含 `<!DOCTYPE html>`、内联 `<style>` 和 `<script>`
- 样式必须内联写在 `<style>` 标签中，不依赖外部 CSS 文件
- 外部字体通过 Google Fonts CDN 引入（`<link>` 标签），如加载失败需设置合理的 fallback 字体
- 不依赖外部 JS 库，除非功能必需（如图表库）

使用 `create_file` 将 HTML 保存到 workspace 目录（相对路径），如 `output/<brand>-<page>.html`。

### Step 6 — 预览与展示

生成 HTML 文件后，按以下策略向用户展示效果：

1. **保存文件**：确认 HTML 已通过 `create_file` 保存到 workspace，告知用户文件路径
2. **文字描述设计亮点**：用 3-5 句话描述页面的视觉特征，包括：
   - 主色调和配色方案（引用具体 HEX 值）
   - 字体选择和排版风格
   - 关键布局特征（如全屏 hero、卡片网格、渐变背景等）
   - 品牌标志性设计元素（如 Stripe 的渐变、Linear 的紫色点缀）
3. **引导浏览器查看**：告诉用户"请在浏览器中打开该 HTML 文件查看完整效果，包括字体渲染、渐变、动画等细节"
4. **可选截图**：如果当前环境有 `browser_use` 工具可用，则使用它打开 HTML 并截图展示；如不可用，跳过此步即可

> 不要使用 Artifacts 代码块预览（CSS 限制会严重降低视觉效果），优先引导用户在真实浏览器中查看。

## DESIGN.md 格式说明

每个 DESIGN.md 包含 9 大章节，详见 [design-md-format.md](./references/design-md-format.md)。

| # | 章节 | 生成 UI 时的用途 |
|---|------|----------------|
| 1 | Visual Theme & Atmosphere | 确定整体基调和设计哲学 |
| 2 | Color Palette & Roles | 提取精确的颜色值用于 CSS |
| 3 | Typography Rules | 设置字体族、字号、行高 |
| 4 | Component Stylings | 按钮、卡片、输入框的具体样式 |
| 5 | Layout Principles | 间距、网格、容器宽度 |
| 6 | Depth & Elevation | 阴影、层级、表面区分 |
| 7 | Do's and Don'ts | 避免违反设计规范 |
| 8 | Responsive Behavior | 断点、移动端适配 |
| 9 | Agent Prompt Guide | 快速颜色参考和即用 prompt |

## 错误处理

1. 内置模板读取失败 → 使用 curl 降级：`curl -o DESIGN.md "https://cdn.jsdelivr.net/npm/getdesign@latest/templates/<brand>.md"`
2. curl 下载失败 → 检查网络连接，或尝试 npx：`npx getdesign@latest add <brand>`
3. 品牌名不存在 → 从品牌目录中查找最接近的品牌名，提示用户确认
4. 项目根目录已有 DESIGN.md → 告知用户将被覆盖，获得确认后再执行
