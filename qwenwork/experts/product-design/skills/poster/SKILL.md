---
name: 营销海报
name_en: "poster"
argument-hint: "输入营销主题与目标平台，如：618 大促活动海报 / 公众号文章封面 / 小红书种草配图"
description: >
  从营销主题生成可直接发布的完成品海报图片（PNG）。AI 直出材质化字体海报，文字融入画面材质
  （霓虹/冰雕/木刻/水墨/玻璃/花卉/金箔/毛笔金 8 种材质风格），不用 Pillow 叠加。内置文字
  正确性二次校验，错字自动重试（≤ 2 次）。支持多尺寸（16:9 公众号 / 3:4 小红书 / 1:1 朋友圈
  / 9:16 故事）。可选消费 design-tokens.json 约束色彩。

  触发关键词：营销图、头图、海报、banner、poster、封面图、hero image、公众号封面、小红书配图、
  营销头图、活动海报、推广图、宣传图、社交媒体图。

  排除（反向）：UI / UX 页面设计（用 /Web页面设计 或 /mobile页面设计）、数据可视化图表（用 /数据可视化）、
  数字人头像（用 /数字人头像）、视觉情绪板（用 /视觉情绪板）、Logo / icon 设计（不在套件范围）。

description_en: >
  Marketing poster generator — from theme to publish-ready PNG with materialized typography. AI directly
  renders text as part of the image material (neon / ice sculpture / wood carving / ink wash / glass morphism
  / floral / gold foil / brush-gold — 8 material styles). No Pillow compositing. Built-in character-level
  text verification with auto-retry on errors (up to 2 retries). Supports multiple aspect ratios
  (16:9 WeChat cover / 3:4 Xiaohongshu / 1:1 social feed / 9:16 story). Optionally consumes
  design-tokens.json to constrain brand colors.

  Triggers when a designer says: "marketing poster", "banner", "hero image", "cover image",
  "social media graphic", "campaign poster", "promotional image", "营销海报", "活动海报",
  "公众号封面", "小红书配图", "推广图", "宣传图".

  Excludes: UI / UX page design (use /flow-web or /flow-mobile), data visualization (use /chart),
  digital avatar (use /avatar), visual moodboard (use /board), logo or icon design (out of toolkit scope).

triggers:
  mode: suggest
  keywords: [海报, banner, poster, 封面图, 公众号封面, 小红书配图, 活动海报, 推广图, 营销图, 宣传图]
  suggestion_text: "检测到你可能需要营销海报设计，试试 /营销海报 技能？"
  min_confidence: 2

allowed-tools:
  - Read
  - Write
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, board]
  writes: poster
  schema:
    skill: string
    generated_at: string
    project_name: string
    theme: string
    target_sizes: array<enum [16x9, 3x4, 1x1, 9x16]>
    style:
      material_id: enum [neon, ice, wood-carve, ink-wash, glass-morph, floral, gold-foil, brush-gold]
      color_source: enum [design-tokens, auto-match, manual-pick]
      brand_color_hex: string
    text_content:
      title: string
      subtitle: string
    variants_generated:
      - variant_id: string
        size_id: string
        scene_description: string
        prompt_used: string
        file_path: string
    user_selection:
      chosen_variant_id: string
    text_verification:
      status: enum [pass, retry-1, retry-2, accepted-with-flaw]
      issues_found: array<string>
    final_outputs:
      - size_id: string
        file_path: string
        resolution: string
---

# Marketing Poster Generator

营销主题 → AI 直出材质字体海报（2-3 变体）→ 用户选择 → 文字校验 → 交付

---

## CRITICAL RULES

1. 最终产出必须是**可直接发布的 PNG 图片**。
2. **文字由 ImageGen 直接渲染为材质化字体**——文字是画面的一部分，不是叠加层。
3. **禁止使用 Pillow 合成文字**。
4. **必须有二次确认环节**：先生成 2-3 张变体让用户选择。
5. **必须有文字校验环节**：选定后逐字核对，错字则重试。
6. 每次生成**同一尺寸出 2-3 张不同变体**（同材质，变构图/场景/光影）。
7. 输出语言跟随用户输入语言。
8. design-tokens.json 是**可选输入**——有则用其色彩约束 prompt。

---

## Chain Context

### 上游读取（Phase 0.5，在 Phase 1 之前执行）

按以下顺序尝试读取上下文，找到即提取可复用字段并告知用户已沿用：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:board -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `spark-output/context/board.json`
3. 都没有则跳过，按无上下文流程执行（Phase 1 正常问用户）

**从 brief 提取**：`project_name`、`brand_tone`、`target_user` → 预填 Phase 1 的营销主题和品牌调性
**从 board 提取**：`design-tokens.json` 路径 → 跳过 Phase 1 第 4 问，自动消费 tokens 色彩约束 prompt

告知用户："检测到 [brief / board] 上下文（来自 [文件 / 会话 marker]），已沿用以下字段：[字段列表]，可继续或修改。"

### 下游输出（Phase 5.5，在 Phase 5 交付之后执行）

**Step 1 · 写盘**（必做）：调用 Write 工具把完整 JSON 写到 `spark-output/context/poster.json`

**Step 2 · 自检行**：输出 `✅ poster.json 已写盘到 spark-output/context/poster.json`

**Step 3 · 紧凑 marker（必须在 chat 中输出）**：

⛔ 即使 Step 1 写盘成功，也**必须**在 chat 中输出以下 marker（让下游 Skill 在纯对话场景下也能发现 poster 上下文）：

```
<!-- spark-context:poster ref="spark-output/context/poster.json" -->
Poster 已保存：project=[项目名]，material=[材质]，sizes=[尺寸列表]，text_verified=[pass/retry/flaw]
<!-- /spark-context:poster -->
```

**Step 4 · 更新链路面板**（如 `_shared/dashboard-template.html` 存在）：扫描 `spark-output/context/*.json` 聚合状态，克隆模板到 `spark-output/dashboard.html` 并注入。面板生成失败不阻断 Skill 完成。

**Step 5 · Handoff 提示（必须输出，紧跟 Step 4 之后）**：

```
✅ 营销海报已完成（[N] 张成品 PNG + 文字校验 [pass/accepted-with-flaw]）
📊 链路面板已更新：spark-output/dashboard.html

📋 下一步建议：
1. 🎯 推荐：`/设计提案` — 把海报主视觉装进决策者汇报
2. 💡 备选：`/Web页面设计` — 把海报嵌入营销落地页
3. 💡 备选：`/设计复盘` — 营销活动结束后复盘效果
```

---

## 执行流程

### Phase 1: 收集需求

用 AskUserQuestion 一次性确认（已知的跳过）：

1. **营销主题**：一句话描述
2. **目标尺寸**：16:9 / 3:4 / 1:1 / 9:16
3. **文案内容**：标题（必填，建议 ≤ 8 字最佳）、副标题（可选）
4. **design-tokens 路径**（可选）

**数字混排风险告知（必做）**：如果用户提供的标题或副标题含数字（如"199元""5折""618"），必须在 Phase 1 主动告知：
> "含数字的文案 AI 渲染出错率较高。建议：纯中文核心文案交给 AI 材质化渲染，数字利益点（如'满199减50'）建议后期用设计工具叠加，确保准确无误。"
用户确认后再进入 Phase 2。如果用户坚持要 AI 渲染数字混排文案，则正常执行但在 Phase 4 校验时**重点关注数字部分**。

### Phase 2: 确定材质风格

**自动匹配规则**（agent 根据主题判断，告知用户选了什么及原因）：

| 材质 ID | 视觉效果 | 适用场景 |
|---------|----------|---------|
| neon | 霓虹灯管发光，光晕溢出砖墙 | 夜店/酒吧/潮牌/夜经济 |
| ice | 透明冰雕，水珠+棱镜折射 | 冷饮/冰品/夏季促销 |
| wood-carve | 3D木刻立体，木纹+凿痕 | 咖啡馆/手作/茶室/自然品牌 |
| ink-wash | 水墨飞白毛笔+金墨飞溅 | 中秋/春节/茶/文化品牌 |
| glass-morph | 磨砂玻璃透光+彩虹折射 | SaaS/AI/科技发布 |
| floral | 真花填充字形，花瓣溢出笔画 | 美妆/春季/母亲节/婚庆 |
| gold-foil | 3D金属立体，金箔反光 | 周年庆/高端/奢侈/地产 |
| brush-gold | 毛笔书法+金色飞白 | 传统节庆/白酒/国潮 |

如主题模糊或有多个可能匹配，用 AskUserQuestion 让用户从 2-3 个候选材质中选。

### Phase 3: 生成海报（2-3 张变体）

**Prompt 结构（LOCKED）：**
```
[场景类型] promotional poster,
large Chinese text "[标题全文]" [材质 prompt 关键词],
[副标题处理：below it "[副标题]" in [对比风格描述]],
[场景/产品/背景描述],
[光影/氛围/色调],
[整体风格修饰词],
[构图指令]
```

**材质 Prompt 关键词（LOCKED，从此处原文复制）：**

- **neon**: `as glowing neon sign lettering in [color] neon tubes mounted on dark brick wall, realistic neon tube glow effect with light bleeding onto the wall`
- **ice**: `rendered as realistic translucent ice sculpture lettering with frost crystals and water droplets on the surface, prismatic light refractions`
- **wood-carve**: `as hand-carved wooden letterpress type with visible wood grain texture and chisel marks, warm honey-colored wood material`
- **ink-wash**: `in flowing watercolor ink wash calligraphy with splashes of gold and crimson pigment bleeding at the edges, rice paper texture background`
- **glass-morph**: `in frosted glass morphism lettering with translucent blurred background showing through, subtle rainbow light refraction at edges, soft white glow outline and depth shadow`
- **floral**: `composed of and filled with real flowers - roses, peonies, cherry blossoms growing in the shape of each character, botanical typography with leaves and petals forming the strokes`
- **gold-foil**: `in luxurious gold foil 3D lettering with metallic reflection, embossed with depth, catches warm ambient light`
- **brush-gold**: `in bold brush calligraphy style with dynamic brush strokes, gold and black ink with gold splashes and ink splatters`

**副标题对比风格建议（自动选取与主标题材质形成对比）：**
- neon 主标题 → 副标题用 `smaller cool [对比色] neon`
- ice → `smaller frosted glass text`
- wood-carve → `smaller burnt wood pyrography style`
- ink-wash → `elegant thin brush strokes`
- glass-morph → `thin transparent acrylic text`
- floral → `delicate gold thin serif`
- gold-foil → `refined thin white serif`
- brush-gold → `smaller elegant regular weight text`

**ImageGen 尺寸映射（LOCKED）：**
- 16:9 → `1792x1024`
- 3:4 → `1024x1536`
- 1:1 → `1024x1024`
- 9:16 → `1024x1792`

**3.1 并行生成 2-3 张变体**（同材质，变场景/构图/光影方向）。

**3.2 用 present_files 展示给用户，用 AskUserQuestion 让用户选择**（或要求全部重来/换材质）。

### Phase 4: 文字校验（二次校验，必须执行）

用户选定后，agent 必须**逐字核对**标题和副标题：

1. 读取选定图片（用 Read tool 查看）
2. 将图中文字与用户原始文案**逐字比对**
3. 判定结果：
   - **全部正确** → 进入 Phase 5
   - **有错字/缺字/多字/笔画异常** → 用相同 prompt 重新生成（重试），最多重试 **2 次**
   - **重试 2 次仍有误** → 告知用户具体哪个字有问题，提供选项：(a) 接受瑕疵 (b) 换一个材质重试 (c) 缩短标题重试

**常见错误类型（校验重点）：**
- 多一笔/少一笔（如"品"变三个口但位置歪）
- 整字替换（如"萃"变"翠"）
- 镜像/旋转（笔画方向不对）
- 模糊不可辨（材质遮挡了笔画）

### Phase 5: 交付

`present_files` 交付选定的完成品 PNG。

---

## Pitfalls

- 标题 **≤ 8 字** 效果最好；> 10 字出错率显著上升，应建议用户缩短
- 数字混排（如"5折""199元"）比纯中文出错率高——校验时重点关注
- 每种材质有"最佳搭配场景"（如 ice+冷饮, neon+暗夜），不要跨调性硬配
- 副标题字数建议 ≤ 12 字，太长会被模型忽略或变形
- AI 文字有**随机性**——同一 prompt 每次生成结果不同，通常重试即可修正错字
- 如用户需要**多尺寸输出**，每个尺寸需独立生成（AI直出无法复用）
- neon 材质在横图(16:9)下效果最佳，竖图(9:16)容易构图失衡
- 构图指令中加 `subject positioned in [位置]` 可引导文字/场景分布

## 材质-场景自动匹配速查

| 主题关键词 | 推荐材质 |
|-----------|---------|
| 夏日/冰/凉/冷饮 | ice |
| 咖啡/手作/木/茶 | wood-carve |
| 中秋/春节/国风/茶 | ink-wash 或 brush-gold |
| 科技/AI/发布/SaaS | glass-morph |
| 花/春/美妆/母亲节 | floral |
| 周年/庆典/高端/奢品 | gold-foil |
| 夜/酒/潮/电音 | neon |
| 白酒/国潮/书法 | brush-gold |

