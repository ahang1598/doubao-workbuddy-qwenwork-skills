---
name: seedance-real-selling-video
description: Seedance 2.5 真人感出海 AI 带货视频技能，整合「去 AI 感」与「去广告感」双向优化。四大真实感支柱（混合光源、生活杂物、毛孔纹理、手机拍摄）+ 六条核心补丁语句 + 负面轰炸 + 三段锁定 + 结尾质量指令区块 + 15–25 秒带货四段式脚本。当用户需要：(1)做 AI 真人带货 / UGC 口播 / 种草视频，(2)让 AI 视频更真实更像手机实拍、降低 AI 味和广告感，(3)排查塑料皮肤、崩手多指、眼神闪烁、口型不同步、跨镜头崩脸漂移、画面冒乱码文字与 logo、假光照，(4)写或优化 Seedance 提示词，(5)让角色在多镜头间保持一致，(6)设计带货口播脚本钩子与节奏时使用。
---

# Seedance 2.5 真人感出海带货视频

**核心矛盾**：AI 带货视频有两个死穴——「一眼 AI」（塑料皮肤、崩手、假光）和「一眼广告」（棚拍打光、干净台面、完美构图）。两者要同时躲开。

**解法是反向优化**：不追求精致，主动制造真实世界的不完美。欠指定的提示词，模型一定拿通用默认值填——那就是 AI 味的来源。

**能力基线**：Seedance 2.5 单次 30 秒（可延长至 90 秒）、最多 50 个参考素材、原生 4K、单次生成内可处理场景切换。带货建议单段 15–25 秒直出，**不拆段**——拼接处的色调跳变本身就是 AI 味来源。

**实测基线**：乱码文字规避 100%（N=12）、眼神稳定性 95、角色跨镜头一致性 92、手部解剖正确性 89。

---

## 一、核心补丁语句库（默认全部加上）

**不要等出问题才加。** 预打补丁不增加提示词复杂度，但显著降低重抽率。

| AI 痕迹 | 直接粘贴这句 |
|---|---|
| 塑料 / 过度磨皮 | `Skin shows natural texture with pores and subtle imperfections, not over-smoothed plastic.` |
| AI-art 玻璃质感 | `Documentary realism throughout, NOT AI-art aesthetic, NOT 3D render, NOT illustration.` |
| 崩手 / 多指 / 手黏连 | `Hands have natural anatomy with five fingers and correct proportions.` |
| 眼神闪烁 / 抖动 | `Eyes remain stable and focused without flickering or jitter.` |
| 中文口型漂移 | `Mouth movement strictly synchronized to dialogue per shot — closed and still otherwise. Lip-sync precise to each Mandarin syllable.` |
| 品牌名读错 | `Word pronunciation: "[品牌]" pronounced as "[音标]".` |
| 分段间背景漂移 | `Same room as Segment A.` |

中文版（写中文提示词时用）：

```
皮肤有自然纹理、可见毛孔和细微瑕疵，不是光滑塑料感，不要过度磨皮。
纪实写实风格贯穿全片，不要 AI 绘画质感，不要 3D 渲染感，不要插画感。
手部解剖自然，五指完整、比例正确。
眼神稳定聚焦，无闪烁无抖动。
口型严格对应每句台词，不说话时闭合静止；对准每个中文音节。
```

---

## 二、四大真实感支柱

### 支柱 1 · 光线：混合光源

**通用灯光是最大的 AI 味来源。** 均匀受光不存在于现实世界，现实一定有明暗。

必须指定三件事：色温（`warm 3000K key light`）、方向（`side light from camera-left`）、质感（`soft, diffused` 或 `hard, contrasty`）。

```
❌ professional lighting / studio lighting / 三点布光 / 柔光箱

✅ Mix lighting: cool daylight from a window on camera-left combined with
   a warm overhead household lamp. Color temperatures clash naturally,
   creating uneven shadows across the face. Natural falloff, no fill light.
```

**进阶（更真实）**：指定单一可信光源，比三点布光真实得多：

- 仅靠窗边自然光，光从画面左侧进入，右半边脸自然沉入阴影，无补光
- 只有头顶一盏暖色吸顶灯，脸部上方受光、下颌有自然投影
- 傍晚窗户余光 + 手机屏幕冷光反射在脸上

按真实感排序的灯光方案：**自然天光**（纪实感最强）>**实景光源**（画面里能看见灯具/屏幕）>**蓝调时刻 / 阴天**（冷调漫射，中性）>**三点布光**（影棚感，偏「制作过」）。

避免：无来源的均匀亮光、说不出方向的柔光、饱和过头的彩色光。

### 支柱 2 · 场景：主动塞杂物

`clean background` 是死刑。关键是「用过的痕迹」而非「摆好的道具」：

| 假（摆拍感） | 真（生活感） |
|---|---|
| 整齐叠放的毛巾 | 揉皱随手放的纸巾 |
| 未开封的包装盒 | 拆开一半、胶带翘起的快递袋 |
| 空咖啡杯 | 喝了一半、杯壁有水痕的咖啡杯 |
| 摆正的手机 | 屏幕朝下扣着 + 缠着的充电线 |
| 空白墙面 | 贴了便利贴、有插座和电线的墙 |

```
Lived-in cluttered background: a half-finished coffee mug with visible
stains, an opened express delivery bag with tape peeling off, a crumpled
tissue tossed nearby, a tangled charging cable, a few receipts.
NOT a styled set, NOT a clean background.
```

### 支柱 3 · 皮肤：主动要毛孔

观众第一眼察觉「不对」的地方。

```
Skin has visible texture and pores, natural uneven skin tone with slight
redness on cheeks and nose, faint under-eye shadows, a few small blemishes.
Real human skin, NOT smoothed, NOT retouched, NOT plastic, NOT CGI.
```

### 支柱 4 · 镜头：指定手机拍摄

打破「精致广告片」惯性最快的一招，**开头就写**。四要素缺一不可：

```
Shot on iPhone, handheld with subtle natural shake, slight motion blur,
composition slightly off-center, casual framing, vertical 9:16.
Amateur home-video feel.
```

可叠加：`slight lens smudge`（镜头脏污）、`auto-exposure hunting`（自动曝光调整）、`slight rolling shutter wobble`（果冻效应）。

**完美无瑕的画面本身就是 AI 特征**——轻微的镜头脏、光晕、呼吸感都能显著提升真实度。

---

## 三、负面轰炸（治画面幻觉出文字/logo + 广告感）

单条 `NO text` 会被软性理解，堆叠 5 条以上才会被当作硬约束。带货场景要把「去广告感」和「去 AI 感」两组词一起堆：

```
professional photography, studio lighting, softbox, three-point lighting,
perfect skin, flawless, retouched, symmetrical, centered composition,
clean background, minimalist set, 3D render, CGI, oversaturated,
hyperreal, AI-art aesthetic, illustration, plastic skin, over-smoothed,
NO text, NO Chinese characters, NO English text, NO numbers, NO logos,
NO UI elements, NO recognizable symbols, NO punctuation
```

前半段砍广告感，后半段砍 AI 感。

**实测数据**：1 条否定 → 47% 出现乱码文字；3 条 → 18%；6 条以上 → 0%（N=12）。

**放置位置**：既要写在对应镜头块内，也要在提示词**结尾**重复一遍。模型生成每帧前会重读最后一段，近因效应下结尾规则的激活强度约为埋在中段的 3 倍。

### 配套：正向替代（关键）

只说「不要」会留下真空，模型会用变体填回来。每条重要的 NO 都要配一句「要什么」：

```
❌ 浮动卡片。卡片上不要有文字。

✅ 柔和抽象的发光矩形悬浮在右侧边缘（紫/粉/蓝渐变色调，
   无可识别图案或文字），卡片呈失重半透明状，暗示全息数据。
   NO text, NO characters, NO numbers, NO logos, NO UI elements.
```

对文字、logo、品牌标记、皮肤、光线、背景这些真正致命的项，**否定和正向描述都要留**。

### 真需要屏幕文字时

不要指望模型写对。在 AI 外部生成再合成：
- HTML 做版 → 无头浏览器截图 → 当首帧图喂进去
- 用真实拍摄的招牌照片
- 后期用剪辑软件叠加

---

## 四、三段锁定（治跨镜头崩脸漂移）

把角色/场景/声音提到镜头脚本**之前**的独立区块。模型会把置顶区块当作 schema（全局恒真事实）而非叙事细节。

**实测**：三段锁定置顶 → 7 个镜头角色一致性 92 分；同样细节内联写在每个镜头里 → 掉到 68 分。

```
[Character Lock — 名字]
6–8 行具体外观：体型 / 年龄 / 发型 / 眼镜 / 服装 / 配饰。
所有 N 个镜头保持同一套服装与外观。
皮肤有自然纹理和可见毛孔，不是光滑塑料感。

[Setting Lock]
环境 + 光源方向 + 色温 + 道具 + 空间构图。
所有镜头同一场景。

[Voice Lock]
语言 / 口音 / 年龄段 / 音色 + 音频行为规则（口型同步、停顿模式）。
```

做系列带货内容时，把这三块存成可复用的头部。第二条视频用完全相同的 Character Lock 和 Setting Lock，人设一致性自动延续。

---

## 五、带货脚本结构（15–25 秒四段式）

| 段落 | 时长 | 写法要点 |
|---|---|---|
| 钩子 | 前 2 秒 | 具体数字 / 反常识 / 直接喊人群 / 从动作中段切入 |
| 痛点 | 3–8 秒 | 说场景不说形容词——「每次挤地铁妆就花」胜过「持妆不好」 |
| 展示 | 8–18 秒 | 手真实拿起产品、可见效果变化 |
| 行动 | 最后 3 秒 | 一句话说清怎么买 |

**口播真实感**：句子 4–12 字（长句必然拉低口型准确率）、允许口语碎词（「就是」「其实」「你懂吧」）、不要排比押韵（那是广告腔）、语速指定偏慢。

**手部规避**：手是已知弱项。用「握住」「放桌上推近」这类简单动作，避免转动、翻面、多指精细操作——非必要不写手部动作。

**运镜要给量**：
- 说时长：`slow push-in over 3 seconds`，不要只说 `push-in`
- 说幅度：`subtle 1.05x zoom`，不要只说 `zoom`
- 说时机：`push-in starts at 1s, ends at shot end`

---

## 六、结尾质量指令区块（骨架）

```
[Quality directives]
[角色名]的面部特征在全部 N 个镜头中保持一致——同一张脸、同样的发型角度、
同样的眼镜、同样的服装与配饰。

Hands have natural anatomy with five fingers and correct proportions.
Skin shows natural texture with pores and subtle imperfections, not
over-smoothed plastic.
Eyes remain stable and focused without flickering or jitter.
Mouth movement strictly synchronized to dialogue per shot — closed and
still otherwise. Lip-sync precise to each Mandarin syllable.

光照全程与[光源]一致。

NO text, NO Chinese characters, NO English text, NO numbers,
NO logos, NO UI elements, NO recognizable symbols.

Documentary realism throughout, NOT AI-art aesthetic, NOT 3D render,
NOT illustration. NOT professional advertising footage.
```

实测：带结尾质量指令的生成，AI 玻璃皮肤痕迹降低 12%，手部解剖改善 8%，负面指令遵守率 100%（不带时 78%）。

---

## 七、提示词组装顺序

1. **三段锁定**（Character / Setting / Voice Lock，独立置顶区块）
2. **镜头声明**（支柱 4，开头就写）
3. **光线**（支柱 1）
4. **场景杂物**（支柱 2）
5. **皮肤纹理 + 核心补丁语句**（支柱 3 + 第一章）
6. **动作与口播台词**（四段式，逐段带时间轴与运镜量）
7. **结尾质量指令区块 + 负面轰炸**（第六章，重申一遍）

---

## 八、症状 → 修复对照表

| 症状 | 根因 | 修复 |
|---|---|---|
| 一眼就是广告片 | 棚拍光 + 干净台面 + 完美构图 | 换混合光/单一光源 + 塞生活杂物 + 构图偏心 + 声明手机拍摄 |
| 皮肤像塑料 / 玻璃 / CGI | 模型默认审美偏「美颜」 | 正向描述纹理毛孔 + 拒绝 AI-art 风格，两句都要 |
| 光线假、脸上没阴影 | 均匀受光无来源 | 混合光源色温冲撞，或单一光源 + `no fill light` |
| 背景太空像影棚 | 欠指定，模型给默认干净场 | 逐件列出带使用痕迹的杂物 + 负向词加 `clean background` |
| 画面过于锐利完美 | 缺镜头污染 | 加 `slight motion blur` + `handheld shake` + `lens smudge` |
| 镜头间人脸变了 | 锁定不足，细节内联埋在镜头里 | Character Lock 提到置顶独立区块 + 结尾重申 + 首尾帧锚定 |
| 眼神一直在抖 | 模型默认给「有趣」的眼部动画 | 加眼神稳定语句 |
| 手指数量不对 | 已知弱项，动态中尤甚 | 加手部解剖语句 + 改用简单手势 |
| 口型对不上（中文尤其） | 模型默认按英文音素 | 精确指定语言口音（如 `Mandarin, Taiwan accent`）+ 音节级同步 + 放慢语速 + 缩短句子 |
| 画面冒出乱码文字/logo | 模型倾向「填充」细节 | 负面轰炸 6 条以上，镜头块与结尾各写一遍 |
| 分段拼接处画面跳 | 段间背景漂移 | 加 `Same room as Segment A.` + 转场时长从 0.4s 加到 0.6–0.8s |
| 多段色调不统一 | 各段独立生成 | 后期统一 LUT |
| 真需要屏幕文字 | 模型能力外 | 后期叠加，或 HTML 截图当首帧图 |

**后期统一调色（最后一道关）**：多段生成的素材色调必然有差异。用同一套 LUT 压过去——轻微去饱和 + 阴影偏蓝品红 + 一点胶片颗粒——让所有片段看起来像同一台机器拍的。这一步能救回很多素材。

---

## 九、重抽 3 次还不行怎么办

问题可能不在提示词，而在模型：
1. **换生成档位** —— 不同推理路径表现有差异
2. **换分辨率** —— 有时低分辨率反而更稳
3. **换参考图** —— 首帧图可能在跟提示词打架
4. **换模型** —— 不同模型的舒适区不同

---

## 十、能力上限（生成前就说清楚）

| 维度 | 快速档上限 |
|---|---|
| 自然度 / 去 AI 感 | 70–80 |
| 中文口型同步 | 70–85% |
| 超过 5 次剪辑的多镜头 | 65–80% 精度 |
| 跨镜头角色一致性 | 80–90% |

不要事后解释，生成前就把预期对齐。

---

## 十一、提交前自查

- [ ] 五条补丁语句是否全加（皮肤 / 手 / 眼 / 口型 / 纪实风格）
- [ ] 负面否定是否堆到 6 条以上，且镜头块与结尾各写一遍
- [ ] 去广告感负向词是否加了（studio lighting / clean background / perfect skin / centered composition）
- [ ] 三段锁定是否置顶成独立区块，而非内联在镜头里
- [ ] 结尾是否有 `[Quality directives]` 区块重申关键规则
- [ ] 灯光是否指定了色温 + 方向 + 质感，且为混合光或单一可信光源
- [ ] 背景是否逐件列出了带使用痕迹的杂物
- [ ] 是否声明了手机拍摄四要素（手持晃动 / 动态模糊 / 构图偏心 / 竖屏）
- [ ] 运镜是否给了时长和幅度
- [ ] 是否避开了复杂手部动作
- [ ] 口播句子是否控制在 4–12 字、语速偏慢
- [ ] 钩子是否在前 2 秒落地

任何一项没勾，提示词就是欠指定的，模型会拿通用默认值填——那就是 AI 味的来源。

---

去 AI 感方法论部分出自 github.com/roy6732856/seedance-ip-pipeline（MIT）。
