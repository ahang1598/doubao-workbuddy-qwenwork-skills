---
name: page-crafter
description: "Professional high-end Landing Page generation tool. Creates visually stunning, Awwwards-level web pages with cinematic hero sections, modern animations. Trigger keywords: landing page, 落地页, web page, hero section, product launch page, brand showcase."
install_source: official
install_method: download
skill_id: official_y8n9mYv2
enabled_at: 1791893766935
version: 1.0.0
name_zh: 落地页生成器
---

# Landing Page Generator

## 语言规则

- 检测用户对话语言，所有输出跟随用户语言
- 中文用户 → 中文回复、中文注释
- 英文用户 → 英文回复
- 代码变量名保持英文

## 快速触发示例

| 你可以这样说 | 触发场景 |
|------------|------|
| "帮我做一个产品落地页" | 产品推广页 |
| "生成一个活动报名页面" | 活动页 |
| "做个SaaS产品官网首页" | 官网首页 |

---

## 功能概述
A professional Landing Page generation assistant that creates visually striking, "Awwwards-level" web experiences. It handles the full pipeline: gathering requirements, generating a design spec, producing visual assets (cinematic hero videos and images), writing clean HTML/CSS/JS code, and delivering the final page files to the user.

## 环境预检（首次执行一次）

在开始生成前，快速探测可用工具：

| 能力 | 检测方式 | 不可用时降级策略 |
|------|---------|----------------|
| `ImageGen` | 尝试调用 | 使用 CSS 渐变/几何图案替代 |
| `generate_video` | 尝试调用 | Hero 降级为 Image-Led 或 Type-Led 模式 |
| Python + matplotlib | `python3 -c "import matplotlib"` | 仅用 HTML/CSS 内嵌图表 |

**快速失败原则**：任何工具不可用，立即跳过对应路径，不尝试安装或等待。

## 执行流程

### Step 1: Gather User Requirements

Collect the following from the user:

1. **Project theme / brand** — name, identity, brand assets
2. **Page purpose** — product launch, brand showcase, event promotion, etc.
3. **Target audience** — demographics, expectations
4. **Style preference** (optional) — mood, references, aesthetic direction
5. **Content materials** — copy, brand guidelines, logos, images, etc.

If the user provides only a brief description, expand it into a rich, specific design spec yourself. Do not ask excessive clarifying questions — make expert creative decisions and proceed.

### Step 2: Create Design Spec (`spec.md`)

Create a `spec.md` file as the strict blueprint for all subsequent work.

The spec must include:

1. **Expanded Prompt**:
   - Project Context
   - Hero Section design (Video-First — see Hero Section rules below)
   - Typography plan
   - Layout structure
   - Motion / animation plan

2. **Tech Strategy**:
   - Stack choices
   - Asset protocol

3. **Design System**:
   - **Color Palette** — MUST comply with the Color Constraint (see below)
   - **Typography** — scale and font pairing
   - **Layout** — grid system and spacing

### Step 3: Generate Visual Assets

Based on the spec, generate all required visual assets. **Prioritize the Hero visual.**

**For Videos:**
> **QoderWork 适配说明**：QoderWork 当前无视频生成工具（`generate_video` 不存在），Video-Led Hero 模式不可用，默认走 Image-Led Hero 路径。以下视频生成说明保留供未来能力扩展参考。
- 使用 `generate_video` 工具（Text-to-Video / Image-to-Video）
- 默认时长 5 秒
- Enhance prompts with cinematic keywords: "Shot on Arri Alexa, 35mm lens, f/1.8 shallow depth of field, slow-motion, cinematic lighting, hyper-realistic, 8k resolution"
- Add specific camera gear and focal lengths (e.g., "Close-up texture shot, 85mm lens", "Wide angle landscape, 16mm lens")
- Store in: `project_name/videos/`
- **如果 `generate_video` 不可用**：降级为 Image-Led Hero（使用 `ImageGen` 生成高质量全屏背景图）

**For Images:**
- Use `ImageGen` tool
- Store in: `project_name/imgs/`

**Directory Structure:**
```
project_name/
├── imgs/
├── videos/
├── spec.md
└── index.html
```

### Step 4: Generate Code (HTML/CSS/JS)

- Read `spec.md` and implement requirements exactly
- Write clean, semantic HTML5 with modern CSS
- Mobile-first responsive design
- Minimize external dependencies; inline critical CSS

**Path Safety (Zero Tolerance for Broken Links):**

1. **Exact Match**: Before writing HTML, verify the exact filenames generated in Step 3. Do NOT hallucinate filenames.
2. **Relative Paths**: Use simple, relative paths (e.g., `./videos/hero_loop.mp4`).
3. **Fallback Strategy**:
   - Images: `loading="lazy"` AND `onerror="this.style.display='none'"`
   - Videos: NO static image overlays or poster images blocking the video. Set a background color on the video container as fallback.

### Step 5: 质量自检

在交付前，逐项检查：

1. **路径完整性**：所有 `<img>` src 和 `<video>` source 指向的文件确实存在
2. **控制台错误**：HTML 中无明显语法错误
3. **响应式**：检查 CSS 是否包含 media query / 弹性布局
4. **色彩合规**：确认无蓝/紫色调（见 Color Constraint）
5. 如发现路径错误，立即修正 HTML 中的引用

### Step 6: 交付

使用 `Write` 输出最终文件：
- `project_name/index.html` — 主页面
- `project_name/imgs/*` — 图片资源
- `project_name/videos/*` — 视频资源（如有）

向用户展示：
- 项目文件结构
- 主要页面的关键特性说明
- 如需在线预览，用户可自行使用本地服务器打开 `index.html`

---

## Color Constraint (NON-NEGOTIABLE)

**NO BLUE OR PURPLE HUES.**

| Forbidden | Allowed |
|-----------|---------|
| Standard Tech Blue | Earth tones (terracotta, sand, clay) |
| Indigo | Monochrome (Black / White / Greyscale) |
| Violet | Warm tones (Orange, Red, Cream, Gold) |
| Blurple | Nature Greens (olive, forest, sage) |
| Neon Purple | Rich neutrals (charcoal, taupe, ivory) |

**Reasoning**: The aesthetic must strictly avoid the "generic SaaS blue" look. Every page must feel bespoke and high-end.

Always verify the color palette in `spec.md` before proceeding to code generation.

---

## Hero Section Rules (CRITICAL)

The Hero Section is EVERYTHING. First impression determines success. Deliver overwhelming visual impact.

### Default Strategy: Image-Led Hero

> **QoderWork 适配说明**：QoderWork 当前无视频生成工具，Video-Led Hero（原默认策略）不可用。默认采用 Image-Led Hero——使用 `ImageGen` 生成全屏高质量背景图 + CSS 动画（如 Ken Burns 效果）制造动态感。

- The hero image is the **single most important asset**
- Use a 100vh full-screen hero image with text overlays and blend modes
- Add CSS animations (Ken Burns, parallax, subtle zoom) to create cinematic motion
- Use a solid background color matching the image's tone as the only technical fallback
- Video-Led Hero 的原始设计（atmospheric looping background video）保留供参考，待 QoderWork 支持视频生成后可启用

### Acceptable Hero Patterns

| Pattern | Description |
|---------|-------------|
| **Video-Led** (QoderWork 不可用) | Muted autoplay background, high-end cinematic feel, floating headline |
| **Image-Led** (默认) | 100vh hero image, text overlays with blend modes, CSS 动画制造动态感 |
| **Type-Led** | Giant typography IS the hero |
| **Split-Screen** | 50/50 dramatic tension |

### NEVER Do This in the Hero

- Small, contained hero images with excessive padding
- Static placeholder images obstructing the video
- Generic stock photos without artistic treatment
- Blue or Purple color schemes
- Broken image icons or 404 errors

---

## Code Quality Standards

### HTML/CSS
- Semantic HTML5 structure
- Mobile-first responsive approach
- Modern CSS (Grid, Flexbox, custom properties)
- Inline critical CSS for performance
- Clean, readable, well-commented code

### Animation & Interaction
- Use modern component/animation libraries where appropriate
- Aim for "wow" features: parallax, scroll-triggered animations, smooth transitions
- Keep performance in mind — no janky animations

### Asset Handling
- All media paths must exactly match generated filenames
- Images: use `loading="lazy"` and `onerror="this.style.display='none'"`
- Videos: background-color fallback on container, no poster images blocking autoplay
- Use relative paths only (e.g., `./imgs/photo.jpg`)

---

## Output Checklist

Before delivering to the user, verify every item:

1. `spec.md` generated (confirmed NO blue/purple in palette)
2. Visual assets generated (hero image is high-quality, Image-Led default)
3. HTML/CSS/JS code generated
4. Path integrity check: all media paths match generated files exactly
5. Quality self-check passed (no broken paths, no console errors)
6. Files delivered via `Write`

---

## Common Mistakes to Avoid

- Using blue or purple colors anywhere in the design
- Generating low-resolution hero images
- Hallucinating filenames that don't match actually generated assets
- Placing a static poster image over the hero video
- Using generic stock imagery without artistic treatment
- Creating small, padded hero sections instead of full-viewport impact
- Forgetting to verify all media paths before delivery
- 在对话中倾倒源代码（应使用 `Write` 输出文件）

## File & Output Conventions

- **Project directory**: `project_name/` (derived from brand/project name)
- **Images directory**: `project_name/imgs/`
- **Videos directory**: `project_name/videos/`
- **Main page**: `project_name/index.html`
- **Design spec**: `project_name/spec.md` (internal, not delivered)
- **Final deliverable**: source files via `Write`
