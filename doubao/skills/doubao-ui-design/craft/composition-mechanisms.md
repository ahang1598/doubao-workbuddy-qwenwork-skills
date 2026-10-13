# 构图机制库（由内容关系触发的可复用语法）

`queryContract` 决定沟通任务，`designIntent` 决定内容拓扑、视觉主角和注意力路径，
本文件提供把这些关系变成画面的机制。材质与色来自主体、品牌、参考和可量测 token，
不是由 family 一步选出。

> **合同**：多章节交付至少声明 1 个服务内容关系的结构机制，并在 HTML 中真实实现；
> 单屏、工具型或极克制任务可只有一个机制。数量不是质量指标，严禁为凑数强塞巨字、玻璃、
> 出框或动效。

选择原则：

- 先写清 `purpose / when / derivedFrom`，再选择机制；
- 机制之间有主次：一个承担设计签名，其余只解决必要关系；
- 结构相近的章节不得因机制相同而复用同一 DOM 内壳；
- 传统 M01–M10 是可选高表现力机制，不是默认套餐。

---

## 通用结构机制（优先按语义选择）

| id | 适用证据 | 可观察结果 |
|---|---|---|
| `subject-stage` | object/people 是 heroic 主角 | 主体承担最大视觉面积，文案与主体形成空间关系 |
| `evidence-grid` | data/evidence 拓扑 | 指标可横向比较并回指来源，不做装饰数字 |
| `type-led-axis` | type/观点是主角 | 文字尺度与阅读轴组织页面，不依赖卡片 |
| `content-rail` | 克制叙事或工具型长页 | 稳定阅读轨道串联章节，低装饰也有秩序 |
| `relationship-map` | 系统/生态/架构 | 节点与连接构成真实拓扑 |
| `asymmetric-pairing` | 比较/案例差异 | 两侧不等权，差异通过尺度与证据职责显现 |
| `chapter-pacing` | sequence/长叙事 | 长短、疏密与图文比交替 |
| `reveal-mask` | query 需要动态揭示 | 只在关键章节触发，并有 reduced-motion |
| `local-light-source` | 主体材质支持暗场 | 可指出光从何处来；不等于统一黑底霓虹 |

以下 M01–M10 保留为表现力更强的可选机制。只有 evidence 支持时才使用。

## 高表现力结构类（可选）

### M01 巨字锚定 `giant-type-anchor`

**做什么**：品牌词/主题词以 `12–18vw` 渲染，被主体或面板**部分遮挡**，
或被画布裁切（左右出血）。字是**构图结构**，不是标题。

```css
.ghost{position:absolute; z-index:1; font-size:clamp(6rem,15vw,15rem);
  line-height:.82; letter-spacing:-.03em;      /* 纯拉丁巨字才可负字距 */
  color:rgba(255,255,255,.14);                  /* 或 --world 的 8–18% */
  white-space:nowrap; left:-2vw; pointer-events:none}
.hero-subject{position:relative; z-index:3}     /* 主体压在字上 */
```

**合格信号**：缩略到 200px 时，巨字仍是可读的形状块，且**被压住**。
**失败信号**：巨字居中、完整可见、不与任何元素相交 —— 那只是一个大标题。
**变体**：竖排旋转巨字贴左右边缘（`writing-mode:vertical-rl`）；页首页尾同词呼应形成书挡。

### M02 异形咬合转场 `shaped-section-cut`

**做什么**：两个色域之间的边界**不是直线**。用波浪、凹口、拱门、圆弧咬入。

```css
/* 凹口：下一段用负 margin 咬进上一段，并带圆角 */
.next{margin-top:-72px; border-radius:48px 48px 0 0; position:relative; z-index:2}

/* 波浪/斑块边界：clip-path 或 border-radius 变形 */
.blob-cut{clip-path:ellipse(120% 100% at 50% 0%)}

/* 圆形咬口：让一个球体/产品正好嵌在缺口里 */
.notch{clip-path:path("...")}  /* 或用 radial-gradient 遮罩模拟 */
```

**合格信号**：滚动过边界时能感到"进入了另一个空间"。
**失败信号**：`section` 之间只有 `padding` 变化。
**注意**：一页 ≤2 种异形语言；咬合处必须有影，否则读作错位。

### M03 主体出框 `subject-breakout`

**做什么**：主资产/卡片**超出**它所在容器 8–20%，形成 z 轴纵深。

```css
.panel{position:relative; overflow:visible}      /* 关键：不能 hidden */
.subject{position:absolute; top:-14%; right:6%; width:52%;
  filter:drop-shadow(0 24px 48px rgba(20,16,12,.34))}   /* 去背主体用 drop-shadow */
```

**合格信号**：至少一处元素跨越了另一个元素的边界线。
**失败信号**：所有内容都规矩地待在自己的圆角矩形里。

### M04 信息浮层 `floating-info-layer`

**做什么**：信息卡/玻璃面板**浮在**满版影像之上，而不是与影像左右并排。

```css
.stage{position:relative; min-height:820px}
.stage>img{position:absolute; inset:0; width:100%; height:100%; object-fit:cover}
.glass{position:relative; z-index:2; margin:auto; max-width:min(1100px,88vw);
  backdrop-filter:blur(18px) saturate(1.4);
  background:linear-gradient(160deg,rgba(255,255,255,.16),rgba(255,255,255,.06));
  border:1px solid rgba(255,255,255,.22); border-radius:28px}
```

**合格信号**：影像是"世界"，面板是"窗口"。
**失败信号**：`左文右图` 两张皮 —— 这是本库要消灭的头号构图。
**注意**：玻璃靠**边缘高光 + 饱和度提升**成立，不靠单纯降低白色透明度。

---

## 节奏类（决定长页不无聊）

### M05 编号序列 `numbered-sequence`

**做什么**：`01 / 02 / 03` 以**大字号弱色**参与构图，串起服务、步骤、章节。

```css
.step-num{font-family:var(--font-display); font-size:clamp(2.5rem,5vw,4.5rem);
  color:color-mix(in srgb, var(--ink) 16%, transparent); line-height:1}
```

**合格信号**：编号本身是视觉元素，不是列表符号。跨章复现形成秩序感。

### M06 尺度突变 `scale-jump`

**做什么**：相邻两段的主元素尺寸差 **≥3×**。满版大图接一段紧凑列表；
巨字接小字表格。这是"高级感"最廉价也最有效的来源。

**合格信号**：缩略图上能看到明显的疏密交替。
**失败信号**：全页所有区块高度接近、密度接近。

### M07 数据即展示字 `data-as-display`

**做什么**：关键数字用 display 字体 + `2.5–4rem`，而不是正文字号平铺。

```css
.stat b{font-family:var(--font-display); font-size:clamp(2.2rem,4vw,3.6rem);
  font-variant-numeric:tabular-nums; line-height:1}
.stat small{font-size:.72rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--ink-soft)}
```

**合格信号**：数字是画面焦点之一，不是句子里的一部分。

---

## 资产类（决定图片不廉价）

### M08 异形照片蒙版 `shaped-image-mask`

**做什么**：照片不是清一色圆角矩形。菱形、拱门、药丸、椭圆、贴纸白边，任选 **1–2 种**。

```css
.arch{border-radius:50% 50% 12px 12px / 38% 38% 12px 12px}   /* 拱门 */
.pill{border-radius:999px}                                     /* 药丸 */
.diamond{transform:rotate(45deg); overflow:hidden}             /* 菱形：内层反向旋转 */
.sticker{border:6px solid #fff; border-radius:18px;
  filter:drop-shadow(0 8px 18px rgba(0,0,0,.22))}              /* 贴纸白边 */
```

**合格信号**：同一页形状语言 ≤2 套，且与家族气质一致。
**失败信号**：整页 `border-radius:12px` 的图片网格。

### M09 角色多姿态世界 `character-multi-pose`

**做什么**：角色以 **≥3 个姿态/视角**跨屏复现，光色材质锁定同一套，并与道具、场景同材质。

**合格信号**：角色像"住在这个产品里"，而不是贴了一张吉祥物图。
**失败信号**：同一张角色图裁切三次冒充三个姿态（`check_assets` 会判 FAIL）。
**配套**：角色必须与巨字（M01）或场景发生**遮挡关系**，否则只是浮贴。

### M10 暗场局部光 `dark-with-light-source`

**做什么**：暗底页面必须有**可指认的光源**与大气纵深，而不是纯黑填充。

```css
.stage{background:
  radial-gradient(120% 80% at 68% 18%, rgba(255,214,170,.22), transparent 60%),
  radial-gradient(90% 70% at 20% 90%, rgba(90,140,190,.16), transparent 62%),
  var(--canvas)}                                  /* --canvas 是带色相的暗色，不是 #000 */
```

**合格信号**：能说出"光从哪来"。暗部有色相，不是灰阶。
**失败信号**：`background:#000` + 白字 + 亮色卡片。

---

## 组合示例（同机制、不同证据 → 完全不同的画面）

| 需求 | 证据焦点 | 机制组合 | 得到的画面 |
|---|---|---|---|
| 摄影师作品集 | 原片比例、作者署名、作品序列 | type-led-axis + M08 | 阅读轴和不等画幅让作品承担主角 |
| 儿童机器人课 | 角色与动手步骤 | subject-stage + chapter-pacing | 角色跨章节但步骤仍清楚 |
| 金融数据产品 | 指标关系与决策路径 | evidence-grid + M07 | 数字是证据，不是装饰 |
| 点单小程序 | 商品主体与价格决策 | subject-stage + asymmetric-pairing | 商品、规格与价格形成清晰决策顺序 |
| 建筑事务所 | 项目摄影与尺度信息 | content-rail + M06 | 满版图与紧凑事实交替 |

同一机制在不同主体、内容关系、品牌材料与参考证据下会产生不同画面；这不是模板轮换，
而是同一语法对不同事实的响应。

---

## 反模式（本库要消灭的四种画面）

1. **左文右图两张皮**：Hero 左半文字、右半一张图，互不相交 → 用 M01/M03/M04 破。
2. **等宽三卡阵列复读**：连续多段"标题 + 三张等宽卡" → 用 M02/M06 破。
3. **全页同一 z 平面**：背景 + 一层卡片，无任何叠压 → 用 M01/M03 破。
4. **纯黑底 + 亮色卡片**：以为暗色就等于高级 → 用 M10 破。
