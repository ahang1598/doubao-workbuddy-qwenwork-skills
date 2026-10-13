# 影像桥接（UI 方案用图）

HTML 方案里的质感高度依赖图片。本文件把 `doubao-visual-creative` 的**影像世界 + 门 A**收束为 UI 场景可执行规范。  
正式生图前建议 Read：`doubao-visual-creative/references/image-direction.md`（八项与六项自检原文）。

## 何时生图

- 默认 `proposal-doc`：写 widgets **之前**  
- `revise`：升级主视觉时  
- Web：assets 阶段只生成视频 poster，真实 mp4 留到完整 Doc 宿主验收后的 media 阶段

**禁止：** 先用 emoji/CSS 圆球占位交差，再声称「以后补图」。

## 影像世界八项（每个方案冻结一次）

```yaml
image_world:
  subject_topology: "主角结构与数量"
  repeated_motif: "跨屏重复母题"
  materials: ["...", "..."]
  light: "方向 + 软硬 + 色温"
  camera: "焦段 + 机位 + 景别"
  color_grade: "与家族色脚本一致"
  post_process: "颗粒/柔焦；勿糊 UI 字"
  negative_space: "为标题预留左/右/下哪一侧"
unified_suffix: "60-90字，追加到本方案每条 prompt 末尾"
audience_mod: "15-30字受众修饰"
```

## UI 常用资产表（按本轮 query 与 contentRole 裁剪）

下表是可选职责库，不是每个项目必须凑齐的购物清单。`assetPlan` 只为
`contentPlan` 中真正依赖影像的角色建槽；`check_assets.py` 按该计划逐项验收，
不得再用“landing page 固定至少 N 张”强迫无关封面、icon-kit 或横幅进入方案。

| 资产 | 用途 | 画幅建议 | 门槛 |
|---|---|---|---|
| hero-main | 首屏主角 | 透明底或预留负空间的 1:1/4:5 | 短边 ≥1200 |
| hero-support | 次设备/副角色 | 可切边 | 短边 ≥800 |
| scene | 中段叙事 | 16:9 或 3:2，宽 ≥1800 | 光色与 suffix 一致 |
| ui-content | 手机/桌面屏内内容 | 按设备比例 | 文字锐利；或 HTML 真 DOM 代替 |
| motif | 雕塑/符号特写 | 1:1 透明底 | 可跨章复用 |
| texture | L0 底纹（可选） | 16:9 低对比 | 无主体 |
| **icon-kit** | 仅「主角图标」（≤3 枚，如订单状态主图） | 1:1，**逐枚单独生成** | 同材质同视角同光向；短边 ≥800；必须去背验 alpha |
| **product-shot** | 商品 / SKU / 内容图 | 1:1 或 4:5 | **统一机位、统一背景、统一光向、统一裁切**；**一图只服务一个 SKU** |
| **doc-cover** | 文档封面 | 16:9–21:9 | 禁止方图冒充；禁止正文图复用 |
| **doc-banner** | 章节横幅 | **3:1–4:1** | 巨号章节号 + 章名；比 21:9 更扁 |
| **doc-board** | 色板/字体/组件/关键屏证据板 | 16:9–21:9 | 文档与 PDF 的主证据 |

**功能图标分流（写 SVG 前先判定）：**

| 界面类型 | 图标来源 |
|---|---|
| **功能图标（Tab / 导航 / 工具位 / 状态）——不分家族** | **一律 Phosphor inline** → `phosphor_icon.py inject`，用 `fill`/`duotone` 字重 + token 上色 + 圆底板撑表现力 |
| 主角图标（≤3 枚，如订单状态主图） | 生图，但**逐枚单独出**、去背、`check_assets` 验 alpha |
| 任意 | **禁止**手写 Feather/Lucide 默认描边（`0 0 24 24` + `stroke-width:2`）；**禁止**雪碧图切片 |

**为什么表现型 Tab 也改走 Phosphor**（这条已被产物证伪，勿回退）：
旧规则要求「一条 prompt 出一整组 icon-kit」，与 `img-reused-across-slots`（一图一位）互斥。
两条同时生效时唯一的解是把拼贴大图用 `background-position` 切成 N 份——
而文生图产出的拼贴**没有对齐网格、没有 alpha**，切出来每块都是糊掉的照片碎片。
失败条件：一份点单小程序的 tab 图标、分类图标、商品图**全部错位**，
`.tab-icon{background-size:500% auto;background-position:0% center}` 这类写法现在由
`check_layout_contract.py` 的 `sprite-slicing` 直接拦下。

表现力不靠"生成的图标"，靠**图标之外的东西**：`fill`/`duotone` 字重、token 上色、
圆底板（半径同 `--r-control`）、选中态实心/描边切换、底板色域随分区变化。

主角图标（≤3 枚）确实要生图时，**逐枚单独出**，例：

```text
a single app icon: a matte ceramic coffee cup, 3/4 angle, soft top light,
centered with ample margin on all four sides, solid flat #FF00E5 background,
no text no labels, no frame, no border. {unified_suffix}
```

**商品图统一性**：同一组 SKU 的每条独立 prompt 必须逐字共享同一机位、同一背景 hex、
同一光向、同一裁切比例和 `unified_suffix`。每个 SKU 单独生成、单独绑定；禁止拼贴切片。

柔光/角色家族：优先透明底。电影/建筑家族：优先全幅摄影负空间构图。

## Prompt 门 A（缺一不发送）

每条 prompt 必须包含：

1. 主体 + ≥2 个材质反应  
2. 构图空间词 + 主体占比 + 留白侧  
3. 镜头  
4. 光线  
5. 色彩世界  
6. 逐字 `unified_suffix` + `audience_mod`  
7. 禁止项：无随机文字、无 Logo、无水印、无他人商标角色  

出品级 prompt 通常 120–220 字；&lt;80 字几乎必缺项。

发送前逐条自查（**包里没有校验脚本**，这一条靠你自己过一遍；
门 A 的八项在 `reference/image-direction.md`）。
把这一批 prompt 按下面的形状写下来，缺项一眼就看得出来：

```json
{
  "unified_suffix": "……60-90 字，全项目逐字一致……",
  "audience_mod": "……15-30 字受众修饰……",
  "prompts": [
    {"id": "hero-main", "role": "hero",  "text": "……"},
    {"id": "scene-01",  "role": "scene", "text": "……"}
  ]
}
```

`role` 决定额外约束：`hero`/`motif` 要求透明底或干净背板；`hero`/`scene` 要求声明留白侧。

## 透明底资产的唯一合法生产路径

> **文生图不产 alpha。** 在 prompt 里写 `transparent background` / 「纯净透明背景」
> 只会得到**白底或灰白棋盘纹理**。把它压在彩色背景上 = 一块白框。
> 这是已发生过的线上事故，不是理论风险。

需要透明底主体时按序执行，**不允许在第 1 步就写"透明背景"**：

```text
1  生成：背景指定为「单一纯色平背」，且与页面 --world 明确不同
     写法：solid flat #FF00E5 magenta background, no gradient, no shadow on background,
           no reflection, subject fully inside frame with 8% margin
     （选品红/正绿这类画面里不会出现的色，去背时不会误吃主体）
2  去背：image_edit「移除背景，输出主体去背 PNG，保留主体底部接触影」
3  验证：把去背结果读进上下文看一眼，并确认 alpha 通道不是全 255：
     python3 -c "from PIL import Image;a=Image.open('assets/x.png').convert('RGBA').split[3];print(a.getextrema)" 
4  兜底：第 2 步拿不到 alpha 时**不要硬上**，改走「干净背板 + CSS 融合」：
     · 资产背景色与页面该处底色取同一个 hex（不是相近，是同一个）
     · 或 mask-image / mix-blend-mode 收边，配 drop-shadow 落地
     · 并在 art-direction.json 置 "alphaRequired": false
```

**判据**：`alphaRequired: true` 却拿不到真 alpha —— 走第 4 步是合格交付，
硬贴上去是交付失败。两者的区别在最终画面上一眼可见。

**拿参考对象当风格锚点会被拦截**（`in the style of X`、`XX 风格`、`对标 XX`）——
必须把它拆成镜头、光线、材质、色板等可见规则，这既是质量要求也是版权安全要求。

### 家族提示骨架（示例，须替换具体主体）

**柔光 3D / 粉彩：**

```text
single soft 3D subject, three-quarter view, full body readable silhouette,
matte silicone and translucent acrylic, soft lavender-cyan rim light,
large clean shape, subtle contact shadow,
solid flat #FF00E5 magenta background, no gradient, no reflection,
negative space on the left for typography, no text no logo no extra props,
70mm look, high detail. {unified_suffix} {audience_mod}
（→ 随后必须走「透明底资产的唯一合法生产路径」第 2–3 步去背并验证）
```

**电影氛围板：**

```text
wide cinematic environment plate, dominant negative space on the left for headline,
subject on lower-right third, deep navy and muted amber grade,
atmospheric depth, realistic light scatter, no typography, 21:9. {unified_suffix} {audience_mod}
```

**品牌雕塑：**

```text
hero brand sculpture centered, premium studio softbox, subtle reflection floor,
isolated on a clean backdrop whose color equals the page --world hex,
no text no logo glyphs, 85mm. {unified_suffix} {audience_mod}
```

## 把生成结果落到本地（每次都要做）

生图工具与 `web.fetch` 返回的是 **302 短链**（`aka.doubaocdn.com/s/…` 一类）。不跟随重定向就只会
拿到几十字节的重定向体，而 `curl -s` 不报错——文件"下载成功"，实际是坏图。这一个缺失的
参数让三张竞品图全部无法解码，执行者转而用无关图片冒充证据。

```bash
curl -L -sS --fail -o assets/A/hero-main.jpg "<返回的 URL>"
```

- `-L` 跟随重定向（**最关键**）；`-sS` 静默但保留错误；`--fail` 让 HTTP 错误变成非零退出码
- 落盘后立刻核对体积：**<8KB 一律视为下载失败**，重下或换 URL
- **扩展名必须与真实内容一致**：文生图常返回 JPEG，存成 `.png` 会让飞书整层丢弃原生图片
  （`degrade_code=2101`，回读表现为"正文里一张图都没有"）。`check_assets.py` 会拦，但在这里就写对更省事
- 多张图合并成一条命令，减少宿主授权往返

## 绑定进 HTML

**写 widget 源码时**用相对路径（便于本地调试与二次修改）：

```html
<img src="../assets/hero-main.webp" alt="林间定制住宅外观" width="1600" height="1200" decoding="async">
```

**进飞书的画布必须自包含**，否则相对路径 404、预览碎图：图一律 base64 内嵌。
出图与内嵌由 `scripts/pack_img.py` 做（`ui.py doc` 会替你调），
它的宽度和质量各有下限，会自己协商并把退让原因打出来；长图自动切段。
preflight 会拦下任何不是 `data:` URI 的 `<img>`。

- 主视觉用有意义的 `alt`（纯装饰可空 alt，但要在方案资产表里说明）  
- 禁止把整张含文案的「假 UI 海报」当作可交互页背景  
- 生图不承担 Logo、按钮文字、卡号、长文案 —— 这些由 HTML 原生排版叠加  

## 与交付合同的关系

进入本 Skill 的 UI 设计任务不能用图片替代完整 Doc。用户只要海报/单图时应在启动前分流视觉
创意 Skill；移动端关键屏图片是 Doc 的内容资产，Web poster 是视频生成与 reduced-motion 的
内容资产，都不是最终交付物本身。

## 版权

不生成可识别的第三方 IP 角色/商标。对标竞品只学构图与材质逻辑。

## 整屏关键屏：prompt 就是设计本身

App 的关键屏由 `image_gen` / `image_edit` 出整屏稿，HTML 画布只做画框。所以**图好不好看，
等于 prompt 好不好**。`make_prompts.py` 已经把下面三条编译进产物，执行者原样送图即可。

### 一、元数据绝不进 prompt

尺寸、像素、字号、hex 一律不写。扩散模型不理解它们，只会把字符**画进画面**。三条实测证据
（其中两条来自被认可为"效果还可以"的产物）：

| prompt 里写了 | 图里出现了 |
|---|---|
| `full 390x844 screen layout` | 占了半屏的「390×844」 |
| `anchored on #FF6B35` | 按钮下方印着「生书汁#FF6B35」 |
| `#FF67F5` / `#12B33` | 好友卡片里印着这两串字符 |

颜色只用词（`color_words` 把 hex 翻成 `vivid golden yellow` 这类说法），画幅由 `size`
字段控制。`check_image_prompt.py` 在送图前拦 `prompt-hex-leak` / `prompt-dimension-leak` /
`prompt-unit-leak` 三类泄漏。

同源问题：让扩散模型渲染精确长文案会得到「薄页」「人霖台美式复i」这类幻觉字形。
prompt 只写 `short realistic Chinese UI text, concise labels`，长文案由原生层承担。

### 二、逐张换重心，不是换文案

十屏用同一个构图只换标题，读者第三屏就走了。`SCREEN_BEATS` 按屏序轮换画面重心：

巨字主导 → 主角登台 → 密集列表 → 满版横带 → 双栏对比 → 径向环绕 → 满版影像叠内容层
→ 时间轴 → 可分享卡 → 磁贴网格

同一套设计语言（后缀恒定）下，每屏都是新的一眼。这条借自
`doubao-visual-creative/references/image-direction.md §2` 的变量矩阵。

### 三、正面要求内容被填满

后缀里写死 `every card and list row filled with real plausible content, no empty panels`。
「一个图标 + 一大片空白」「空药丸条」是这条链最刺眼的失败形态，负向词挡不住它，
必须**正面要求**（gate-design §1 问 4：全是 `no-*` 等于没有要求任何事发生）。

### 执行者唯一要填的空

`<主体：…>` —— 写这一屏**画什么**。不要复述参考图已有的版式（那是 `restoration` 才做的事），
也不要把它改写成中文分区清单：手写路径实测稳定产出空卡片与错位。
