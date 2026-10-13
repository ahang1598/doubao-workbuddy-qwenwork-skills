---
name: visual-forge
description: "Curated image generation assistant covering 17 styles across 4 categories: character figures, scenes, products, and style transforms. Supports styles including 手办/figure, portrait, chibi, diorama, city, landmark, movie scene, isometric room, weather, logo, sticker bomb, brand store, product ad, low-poly, meme 3D, knolling, 裸眼3D. Use when the user needs image generation, 图像生成, or 图像创作."
install_source: official
install_method: download
skill_id: official_ogZWFNbh
enabled_at: 1791893725666
version: 1.0.0
name_zh: 图像创作
---

# 图像创作 — Curated Image Generation

## 功能概述
精选图像生成助手。覆盖角色手办、场景微缩、产品展示、风格转换四大类共17种风格，一站式生成高质量风格化3D图像。

## 输出风格

核心原则：内容简洁，不啰嗦
- 限制的是内容：不解释过程、不寒暄、不说废话
- 凡是有选项的问答，以编号列表形式展示选项

语言规则：
- 检测用户对话语言，所有输出跟随用户语言
- 展示能力列表/风格选项时，只用用户语言，不要中英双语
- 图片中的文字（标题、副标题、卖点标签、slogan 等）使用用户语言
- 例：用户用中文对话 → 选项显示"收藏级手办"而非"收藏级手办 Collectible Figure"

交付时：
- 直接展示图片
- 最简交付语，不总结、不解释

图片输出规则：
- 使用 `ImageGen` 生成图片后，将文件保存到工作目录
- 告知用户文件路径，直接展示图片

提问/引导时：
- 内容简洁，只问必要的
- 克制的礼貌，禁止"您好"、"好的"、"我来帮您"

## 能力范围 + 输入要求

### 角色类 (3种)

| # | 风格 | 必需输入 | 可选输入 |
|---|------|----------|----------|
| 1 | 收藏级动作手办 | 人物照片或插画 | — |
| 2 | 卡通肖像 | 人物照片 | — |
| 3 | Q版/Chibi形象 | 人物照片 | 动作、表情 |

### 场景类 (5种)

| # | 风格 | 必需输入 | 可选输入 |
|---|------|----------|----------|
| 4 | 城市微缩景观 | 城市名 | — |
| 5 | 地标建筑渲染 | 地标名 | — |
| 6 | 电影场景还原 | 电影名 + 场景名 | — |
| 7 | 等轴测房间 | 房间主题/描述 | 氛围、光源 |
| 8 | 城市天气可视化 | 城市名 + 天气 | 日期、温度 |

### 产品类 (4种)

| # | 风格 | 必需输入 | 可选输入 |
|---|------|----------|----------|
| 9 | 贴纸轰炸Logo | Logo图 或 品牌名 | — |
| 10 | Q版品牌店铺 | 品牌名 | 品牌色 |
| 11 | 产品3D渲染 | 产品图 或 产品描述 | — |
| 12 | 产品广告设计 | 产品图（含模特更佳）+ 品牌名 | 卖点、文案、品牌色 |

### 风格类 (5种)

| # | 风格 | 必需输入 | 可选输入 |
|---|------|----------|----------|
| 13 | 低多边形风格 | 主体图或描述 | 配色 |
| 14 | 表情包转3D | 表情包图 | — |
| 15 | 裸眼3D效果 | 场景描述 | — |
| 16 | Knolling整理摆拍 | 城市名 | — |
| 17 | 风格化3D角色 | 人物照片 | — |

## 执行流程
### 路由逻辑

按关键词匹配风格类别：
- 人物/角色/手办/玩偶/肖像 → 角色类
- 城市/地标/建筑/房间/场景/电影 → 场景类
- Logo/品牌/店铺/产品 → 产品类
- 风格/低多边形/转换/Knolling/表情包 → 风格类

### 交互规则

1. 用户需求明确 + 输入完整 → 直接执行对应风格的生成流程
2. 用户需求明确 + 缺必需输入 → 问输入，同时提一句可以先生成示例看效果
3. 用户需求模糊 → 展示风格选择（以编号列表形式）
4. 用户问"你能做什么" → 展示能力表（以编号列表形式）
5. 用户选了多个风格/需要从中选一个 → 以编号列表形式让用户选择

**【重要】用户选择场景：**
- 需要用户做选择时，以编号列表形式展示选项
- 让用户从多个选项中选一个
- 展示能力列表供用户选择
- 展示风格分类供用户选择

### 示例生成（试试看模式）

触发条件：
- 用户说"试试看"/"看个例子"/"随机生成一个"
- 用户选了风格但说"没有图/不知道用什么"
- 用户想先看效果再决定

执行方式：
- 使用该风格的默认示例参数生成一张图
- 除非有必要解释，否则直接展示图片

示例选择原则：
- 选择 1-2 个效果好的示例
- 优先选择：经典/主流/当下热门/有辨识度的元素
- 电影选经典名场景，城市选标志性城市，品牌选知名品牌
- 目的是让示例本身有吸引力，展示该风格的最佳效果

### 生成执行流程（通用）

1. **分析输入**
   - 如有参考图，用 `Read` 工具读取图片并提取特征（人物特征、产品形态、构图元素等）
   - 如无参考图，由 LLM 根据用户描述推断特征
   - 识别关键信息：颜色、形状、姿态、品牌、主题等

2. **确定风格** — 根据路由逻辑和用户描述选定具体风格

3. **构建 Prompt** — 从下方对应的 Prompt 模板出发，填充具体描述

4. **生成图像**
   - 调用 `ImageGen`（提供 name、prompt，可选 size）
   - 如有参考图，先提取其特征并写入 prompt 描述
   - 用户输入明确 → 生成 1 张
   - 用户要看示例 → 生成 2 张，用跨度大的不同参数展示效果范围

5. **交付** — 直接展示图片，告知文件路径，不解释

---

## 角色类 — Prompt 模板与细节

### 1. 收藏级动作手办 (Action Figure)

**风格特征：**
- 1/7比例商业化手办
- 写实材质、精准比例
- 透明亚克力底座
- 工作室级打光
- 可含包装盒展示

**Prompt 模板：**
```
Create a 1/7 scale commercialized 3D action figure of [CHARACTER DESCRIPTION]. Use a realistic style with accurate proportions and surface details. Place the figure on a circular transparent acrylic base. Use studio-quality lighting, shallow depth of field, and photorealistic materials. High detail, clean composition, professional collectible figure presentation.
```

### 2. 卡通肖像 (Caricature Portrait)

**风格特征：**
- 卡通夸张+写实渲染混合
- 大头、大眼、风格化发型
- 柔和电影光
- 简洁背景

**Prompt 模板：**
```
Create a playful 3D caricature portrait of [CHARACTER]. Blend cartoon-style exaggeration with realistic skin shading. Use an oversized head, stylized hair, and large expressive eyes. Apply soft cinematic lighting with clean, simplified materials. Keep the background minimal with a gentle blur.
```

### 3. Q版/Chibi形象

**风格特征：**
- 大头小身
- PVC哑光材质
- 可爱比例
- 盲盒玩具风格

**Prompt 模板：**
```
Create a chibi figurine-style 3D character based on [CHARACTER]. The figure has a big head and small body, made of matte PVC material. [ACTION] pose with [EXPRESSION] expression. Photoreal materials, neutral background, ultra-clean composition.
```

---

## 场景类 — Prompt 模板与细节

### 4. 城市微缩景观 (City Diorama)

**风格特征：**
- 方块切割城市
- 地下剖面（土壤、岩石、根系）
- 地上童话风格城市
- 标志性地标整合
- 纯白背景+柔和光

**Prompt 模板：**
```
Create a hyper-realistic 3D square diorama of [CITY]. The city appears carved out as a solid block with a visible underground cross-section showing soil, rocks, roots, and earth layers. Above the ground, display a whimsical fairytale-style cityscape featuring iconic landmarks and cultural elements of [CITY]. Use a pure white studio background with soft natural lighting. DSLR photo quality, crisp details, vibrant colors, magical realism style. 1080x1080 resolution.
```

### 5. 地标建筑渲染 (Landmark Render)

**风格特征：**
- 等轴测45度视角
- 专业建筑可视化风格
- 写实材质（石材、玻璃、金属）
- 含比例参照（小人、车、树）

**Prompt 模板：**
```
Create a highly detailed isometric 3D rendering of [LANDMARK] in professional architectural visualization style. Show the structure at a 45-degree angle from above. Use photorealistic textures such as stone, glass, metal, and brick. Include a detailed base with tiny people, cars, trees for scale. Clean white background with soft ambient shadows. 1080x1080 resolution.
```

### 6. 电影场景还原 (Movie Scene Diorama)

**风格特征：**
- 经典场景等轴测还原
- 微缩底座风格
- 标志性元素提取
- 含电影标题文字

**Prompt 模板：**
```
Present a clear 45-degree top-down isometric miniature 3D cartoon scene of [SCENE NAME] from [MOVIE]. Use refined textures, realistic PBR materials, and soft lifelike lighting. Create a raised diorama-style base with the most recognizable elements. Display the movie title at top center in large bold text. 1080x1080 resolution.
```

### 7. 等轴测房间 (Isometric Room)

**风格特征：**
- 立方体切割房间
- 浅剖面展示内部
- 可含Q版人物
- 写实材质+柔和光影

**Prompt 模板：**
```
Create an isometric 3D cube-shaped miniature room with a shallow cutaway. Room description: [ROOM THEME, FURNITURE, DECOR]. Lighting: [ATMOSPHERE], using [LIGHT SOURCES]. Include realistic reflections, soft colored shadows. Camera: slightly elevated isometric three-quarter view, cube centered. Photoreal materials, neutral background. No watermark.
```

### 8. 城市天气可视化 (City Weather)

**风格特征：**
- 等轴测城市微缩
- 整合天气元素
- 含城市名、温度、天气图标
- 现代信息图风格

**Prompt 模板：**
```
Present a clear 45-degree top-down isometric miniature 3D cartoon scene of [CITY]. Feature iconic landmarks. Use soft refined textures, realistic PBR materials. Integrate [WEATHER] conditions into the environment. At top center, place "[CITY]" in large bold text, weather icon, date, and temperature. 1080x1080.
```

**补充：** 城市/地标场景可用 `WebSearch` 获取标志性元素信息。

---

## 产品类 — Prompt 模板与细节

### 9. 贴纸轰炸Logo (Sticker-Bombed Logo)

**风格特征：**
- Logo形状的3D实体
- 密集贴纸拼贴
- Y2K/90年代复古风格
- 酸性图形、笑脸、星星、徽章
- 贴纸自然包裹曲面

**Prompt 模板：**
```
Create a hyper-realistic 3D physical object shaped like [LOGO/BRAND]. Apply soft studio lighting. Cover the object with a dense sticker-bomb collage in Y2K and retro 90s style. Include acid graphics, bold typography, smiley faces, stars, and vector badges. Stickers wrap naturally around curves with slight peeling edges and high-resolution textures. Isolated black background. Octane render, 8K quality.
```

### 10. Q版品牌店铺 (Chibi Brand Store)

**风格特征：**
- 品牌标志性产品外形建筑
- 两层玻璃橱窗
- 品牌主题色
- 含Q版小人
- 盲盒玩具美学

**Prompt 模板：**
```
Create a 3D chibi-style miniature concept store of [BRAND]. Design the exterior inspired by the brand's most iconic product. The store has two floors with large glass windows revealing a cozy interior. Use [BRAND COLOR] as primary color theme, with warm lighting and staff in brand uniforms. Add adorable tiny figures walking, sitting along the street. Include benches, street lamps, potted plants. Render in miniature cityscape style, blind-box toy aesthetic, high detail, soft afternoon lighting. Aspect ratio 2:3.
```

### 11. 产品3D渲染

**风格特征：**
- 产品写实3D渲染
- 工作室打光
- 材质细节展示

**Prompt 模板：**
```
Create a photorealistic 3D render of [PRODUCT]. Use studio-quality lighting with soft shadows. Show material details and textures clearly. Clean white or gradient background. Professional product photography style. 8K quality.
```

### 12. 产品广告设计 (Product Ad Design)

**风格特征：**
- 完整广告版式设计
- 品牌色背景 + Logo
- 标题/副标题文案
- 产品卖点标签
- 背景装饰元素

**特殊处理：**
- 如用户未提供文案 → 根据产品特点生成标题
- 如用户未提供卖点 → 根据产品类型推断常见卖点
- 如用户未提供品牌色 → 从品牌名推断或使用互补色

**Prompt 模板：**
```
An advertising image presents a large [PRODUCT] and a model on a two-toned [BRAND COLOR] background. The backdrop is a gradient of [BRAND COLOR], with a brighter, more light hue at the top, transitioning to a deeper, darker shade at the bottom, creating a subtle, reflective surface.

On the left, a magnified view of a chunky high quality [PRODUCT] in [PRODUCT COLOR] dominates the lower portion of the frame. The [PRODUCT] features intricate lines and details, multiple panels, and textured surfaces. The [PRODUCT] is shiny and smooth. The [PRODUCT] is oriented with its main surface facing the viewer, leaning slightly to the right, rotated upright and standing vertically, creating a dramatic presentation angle.

Leaning against the side of the large [PRODUCT], on the right side of the image, is [MODEL DESCRIPTION - include: age, appearance, skin tone, facing direction, body angle, head position, hair style, clothing description with colors and fabric, arm positions, and note that model wears the same product].

The overall lighting suggests a soft, studio setup, casting minimal shadows and highlighting the subjects against the vibrant [BRAND COLOR].

Include brand logo [BRAND] at top corner. Add headline text '[HEADLINE]' in bold. Add product feature tags: [FEATURES]. Add large decorative brand name text in background. Professional advertising design, 1080x1080.
```

---

## 风格类 — Prompt 模板与细节

### 13. 低多边形 (Low-Poly)

**风格特征：**
- 三角面片构成
- 扁平色块着色
- 极简环境
- 清晰几何边缘
- 数字微缩感

**Prompt 模板：**
```
A low-poly 3D render of [SUBJECT], constructed from clean triangular facets and shaded in flat [COLOR1] and [COLOR2] tones. Set in a stylized minimalist environment with crisp geometry and soft ambient occlusion. Playful digital diorama with sharp edges and visual simplicity.
```

### 14. 表情包转3D (Meme to 3D)

**风格特征：**
- 保持原构图
- 转为毛绒玩具质感
- 写实光影材质

**Prompt 模板：**
```
Turn [MEME DESCRIPTION] into a photorealistic 3D render. Keep composition identical. Convert the character into a plush toy with realistic lighting and materials.
```

### 15. 裸眼3D效果 (Glasses-free 3D)

**风格特征：**
- L型LED屏幕
- 城市街角场景
- 元素突破屏幕边界
- 投射真实阴影
- 日光环境

**Prompt 模板：**
```
An enormous L-shaped glasses-free 3D LED screen at a bustling urban intersection, iconic architectural style like Shinjuku Tokyo. The screen displays a captivating glasses-free 3D animation featuring [SCENE DESCRIPTION]. Characters and objects possess striking depth, extending outward and floating in mid-air. Under realistic daylight, elements cast lifelike shadows onto screen surface and surrounding buildings. Rich detail, vibrant colors, seamlessly integrated with urban setting.
```

### 16. Knolling整理摆拍

**风格特征：**
- 正俯视角
- 物品平行排列
- 3D磁贴风格
- 含城市名标签
- 手写便签元素

**Prompt 模板：**
```
Present a clear, directly top-down photograph of [CITY] landmarks as 3D magnets, arranged neatly in parallel lines and right angles, knolling. Realistic miniatures. At top-center, place city name as souvenir magnet, and handwritten post-it note for temperature and weather. Incorporate weather-appropriate items into the knolling. No repeats.
```

### 17. 风格化3D角色

**风格特征：**
- 软陶材质
- 圆润造型
- 粉彩+鲜艳配色
- 夸张面部特征
- 卡通大眼

**Prompt 模板：**
```
Transform the subject into a stylized 3D character with soft clay-like materials. Use rounded sculptural forms, exaggerated facial features, and a pastel plus vibrant color palette. Apply smooth subsurface scattering skin, large cartoon eyes, simplified anatomy. Render on bold blue studio background with soft frontal lighting and subtle shadows. Keep original photo's composition and framing.
```

---

## 工具使用

| 工具 | 用途 | 使用时机 | 必需/可选 |
|------|------|----------|---------|
| `ImageGen` | 生成图像 | 构建好 prompt 后调用（name + prompt + 可选 size） | **必需** |
| `Read` | 读取参考图并分析特征 | 用户提供了参考图片时 | 可选（无参考图时由 LLM 推断） |
| `WebSearch` | 查询地标/城市/品牌信息 | 需要补充城市标志性元素、品牌色等信息时 | 可选 |

## Common Mistakes to Avoid

- ❌ 生成后长篇解释过程或总结
- ❌ 使用"您好"、"好的"、"我来帮您"等寒暄
- ❌ 中英双语混合展示选项（应只用用户语言）
- ❌ 忘记将参考图特征提取并写入 prompt 描述
- ❌ 用户输入明确时生成多张（应只生成1张）
- ❌ 示例模式时只生成1张（应生成2张展示效果范围）
