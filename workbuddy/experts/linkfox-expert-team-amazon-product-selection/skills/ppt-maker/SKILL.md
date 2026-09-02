---
name: ppt-maker
description: Use when the user asks to create a PPT, slide deck, presentation, or proposal from some content (e.g. "做个PPT", "帮我做演示", "生成幻灯片", "make a PPT", "create slides", "create proposal"). Generates a single self-contained HTML presentation file (no PowerPoint/Keynote output) with a fullscreen scroll or paged layout, using bundled themes and templates.
license: MIT
---

# PPT Maker

将用户内容生成专业的 HTML 演示稿/PPT。

## 触发条件

当用户说以下任何一种时触发：
- "做个 PPT" / "做个演示" / "做个幻灯片"
- "帮我做 PPT" / "生成 PPT" / "生成演示稿"
- "make a PPT" / "create slides" / "create presentation"
- "做个提案" / "做个方案" / "create proposal"

## 默认配置

- **风格**：entrepreneur（大字、粗体、冲击力强）
- **主题**：black-fire（黑底 + 白字 + 橙/红强调色）
- **布局**：fullscreen 满屏滚动（每节 100vh）
- **尺寸**：1920×1080 优化
- **字体**：大（标题 3-5rem，正文 1.1-1.25rem）

用户可通过以下方式覆盖默认：
- "用亮色主题" → ocean-blue
- "用紫色" → royal-purple  
- "用翻页模式" → slides 模式
- "正式风格" → corporate
- "简约风" → minimal

## 执行流程

### 1. 读取生成指南
```
Read references/generation-guide.md
```

### 2. 从用户输入提炼内容
- 拆分章节，提炼核心要点
- 每章生成标题（≤12字）
- 确定页面类型组合

### 3. 读取主题 CSS
```
Read themes/black-fire.css  # 或用户指定的主题
```

### 4. 参考基础模板结构
```
Read assets/proposal-template.html
```

### 5. 生成完整 HTML
- 单个 HTML 文件
- 内联所有 CSS + JS
- Google Fonts CDN (Inter + Noto Sans SC + JetBrains Mono)
- 右侧导航圆点
- 动态光斑背景
- 卡片 hover 动效

### 6. 输出
- 保存到 `output/` 目录
- `open` 命令预览
- `message` 工具发送文件给用户


## 可用主题

| 主题 | 背景 | 强调色 | 适用场景 |
|------|------|--------|---------|
| **black-fire** | #000 黑 | 橙+红 | 默认，科技感，冲击力 |
| ember-orange | 白/黑 | 橙色 | 活力，创业公司 |
| slate-dark | #0f172a 深蓝 | 银灰 | 沉稳，商务 |
| ocean-blue | 白 | 蓝色 | 专业，可信赖 |
| forest-green | 白 | 绿色 | 环保，成长 |
| royal-purple | 白 | 紫色 | 创意，高端 |
| trust-navy | 白 | 深蓝 | 企业，政府 |

每个主题除了 primary/accent/bg 等基础变量外，还内置了 4 个图表辅助色
`--theme-chart-blue/green/purple/yellow`，用于图表、多色 badge、多角色对比等需要
2 种以上颜色区分的场景。生成输出时按该主题的取值抄成 `--blue/--green/--purple/--yellow`，
不要自己现编颜色。详见 [references/generation-guide.md](references/generation-guide.md)。

## 可用风格

| 风格 | 特征 | 适用 |
|------|------|------|
| **entrepreneur** | 大字粗体，行动导向 | 默认，大多数场景 |
| corporate | 正式严谨，结构化 | 企业汇报 |
| creative | 视觉化，不对称布局 | 创意提案 |
| consultant | 专业顾问，选项卡片 | 咨询方案 |
| minimal | 极简，等宽字体 | 快速报价 |

## 注意事项

- [ ] 单个 HTML，双击即用，不依赖外部文件
- [ ] 1920×1080 满屏优化，移动端响应式
- [ ] 字体要大，排版要松，不堆字
- [ ] 用 emoji 代替图标，不依赖外部图片
- [ ] 每节 100vh 满屏，右侧导航圆点
- [ ] 先 `open` 预览，再发文件给用户

