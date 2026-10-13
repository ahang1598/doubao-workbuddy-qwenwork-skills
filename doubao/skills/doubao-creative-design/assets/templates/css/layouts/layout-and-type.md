# 组件布局与字体｜密度、文字与局部位移

[返回使用说明](../README.md)。本文件保存该分类的真实参数、默认值与代码；无需从 catalog 查找参数值。CSS 代码块是维护源，生成正式 HTML 时按现有协议展开为行内声明。

## 当前覆盖范围

本文件目前只提供组件内部留白、字体、旋转与错位参数，以及 `layout.compact`、`layout.airy` 两种密度预设；它们不是页面布局。

页面级实现分别见 [规整网格](grid-and-alignment.md)、[疏朗阅读栏](airy-and-spacious.md)、[错位标题](asymmetric-balance.md)、[主图场景](hero-focus.md)、[连续章节](continuous-flow.md)。新增 [叠层拼贴](overlap-and-collage.md)；导览线与横向卡片分别在连续、规整分类中。自由复杂叠压仍需按真实内容编排，末尾构图说明不计作已实现预设。

<a id="layouts.parameters"></a>

## 参数表

风格标签：通用（共用实现或组合规则，非独立风格预设）。

| 参数 | 实现默认值 | 类型／调整范围 | 作用与限制 |
|---|---|---|---|
| `--vl-padding` | `clamp(20px, 5cqi, 34px)` | length | 内容留白，非负 px 或原有 clamp 表达式 |
| `--vl-content-offset` | `26px` | length | 文件夹正文在页签下的安全距离；仅 folder |
| `--vl-font-family` | `"Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif` | font-family | 组件字体；实际作品按字体协议选择云端可用字体 |
| `--vl-title-size` | `clamp(24px, 7cqi, 40px)` | length | 标题字号 |
| `--vl-title-weight` | `700` | number | 标题字重 |
| `--vl-title-leading` | `1.2` | line-height | 标题行高，数字或长度 |
| `--vl-title-tracking` | `-.05em` | length | 标题字距 |
| `--vl-body-size` | `clamp(13px, 2.8cqi, 15px)` | length | 正文字号 |
| `--vl-body-leading` | `1.85` | line-height | 正文行高，数字或长度 |
| `--vl-body-opacity` | `.82` | number | 次级文字不透明度，通常优先用 muted-ink 调色 |
| `--vl-title-gap-before` | `17px` | length | 标题上方间距 |
| `--vl-title-gap-after` | `12px` | length | 标题下方间距 |
| `--vl-rotate` | `0deg` | angle | 整个组件旋转；旋转后检查相邻布局 |
| `--vl-shift-x` | `0px` | length | 组件横向视觉错位，不改变正常布局占位 |
| `--vl-shift-y` | `0px` | length | 组件纵向视觉错位，不改变正常布局占位 |

表中为 CSS 源默认值；六个示例在组合配方中显式使用 30px 标题／42px 标题行高、14px 正文／26px 正文行高及 26px 留白。新任务可覆盖，不应把示例值当成固定风格。

## 调整示例

将 `--vl-padding:32px; --vl-body-leading:1.9; --vl-title-tracking:-.02em` 写到组件根节点即可改变内部密度与文字节奏。字体按 [字体协议](../../../../references/rendering/font-family-library.md) 选择真实可用字体。

`--vl-content-offset` 只用于文件夹，普通圆角容器只用 padding。旋转与错位不改变布局占位，需检查变换后的轮廓和邻居。全页列数、主图比例、跨段动线写到目标布局或 HTML 实现，不由这些组件参数自动决定。

<a id="layouts.implementation"></a>

## 布局与字体实现

风格标签：通用（共用实现或组合规则，非独立风格预设）。

```css
.vl-folder {
  --vl-content-offset: 26px;
  --vl-font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
  --vl-title-size: clamp(24px, 7cqi, 40px);
  --vl-title-weight: 700;
  --vl-title-leading: 1.2;
  --vl-title-tracking: -.05em;
  --vl-body-size: clamp(13px, 2.8cqi, 15px);
  --vl-body-leading: 1.85;
  --vl-body-opacity: .82;
  --vl-title-gap-before: 17px;
  --vl-title-gap-after: 12px;
  --vl-rotate: 0deg;
  --vl-shift-x: 0px;
  --vl-shift-y: 0px;
  --vl-padding: clamp(20px, 5cqi, 34px);
  transform: translate(var(--vl-shift-x), var(--vl-shift-y)) rotate(var(--vl-rotate));
  font-family: var(--vl-font-family);
  text-align: left;
}

.vl-folder__tab {
  font-size: clamp(12px, 3cqi, 17px);
  line-height: 1.4;
  font-weight: 650;
  letter-spacing: .01em;
}

.vl-folder__content {
  position: relative;
  z-index: 3;
  padding: calc(var(--vl-tab-height) + var(--vl-content-offset)) var(--vl-padding) var(--vl-padding);
}

.vl-tag {
  display: inline-block;
  padding: 5px 11px;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.4;
}

.vl-heading {
  margin: var(--vl-title-gap-before) 0 var(--vl-title-gap-after);
  font-size: var(--vl-title-size);
  line-height: var(--vl-title-leading);
  font-weight: var(--vl-title-weight);
  letter-spacing: var(--vl-title-tracking);
}

.vl-copy {
  margin: 0;
  font-size: var(--vl-body-size);
  line-height: var(--vl-body-leading);
  opacity: var(--vl-body-opacity);
}

.vl-copy + .vl-copy {
  margin-top: 15px;
}

.vl-rounded .vl-folder__content {
  padding: var(--vl-padding);
}
```

<a id="layout.compact"></a>

## 紧凑内容

风格标签：通用。

- 仅影响组件内部，content-offset 仅文件夹生效；重新测量卡片高度，不改变根画布尺寸。

```json
{
  "id": "layout.compact",
  "kind": "layout",
  "label": "紧凑内容",
  "tags": [
    "布局",
    "密度",
    "紧凑内容",
    "compact"
  ],
  "applies_to": [
    "recipe.folder-plastic",
    "recipe.folder-glass",
    "recipe.folder-paper",
    "recipe.rounded-plastic",
    "recipe.rounded-glass",
    "recipe.rounded-paper"
  ],
  "overrides": {
    "--vl-padding": "20px",
    "--vl-content-offset": "20px",
    "--vl-title-gap-before": "10px",
    "--vl-title-gap-after": "6px"
  },
  "notes": [
    "仅影响组件内部，content-offset 仅文件夹生效；重新测量卡片高度，不改变根画布尺寸。"
  ],
  "status": "implemented"
}
```

<a id="layout.airy"></a>

## 宽松内容

风格标签：通用。

- 仅影响组件内部，content-offset 仅文件夹生效；重新测量卡片高度，不改变根画布尺寸。

```json
{
  "id": "layout.airy",
  "kind": "layout",
  "label": "宽松内容",
  "tags": [
    "布局",
    "密度",
    "宽松内容",
    "airy"
  ],
  "applies_to": [
    "recipe.folder-plastic",
    "recipe.folder-glass",
    "recipe.folder-paper",
    "recipe.rounded-plastic",
    "recipe.rounded-glass",
    "recipe.rounded-paper"
  ],
  "overrides": {
    "--vl-padding": "32px",
    "--vl-content-offset": "32px",
    "--vl-title-gap-before": "20px",
    "--vl-title-gap-after": "12px"
  },
  "notes": [
    "仅影响组件内部，content-offset 仅文件夹生效；重新测量卡片高度，不改变根画布尺寸。"
  ],
  "status": "implemented"
}
```

## 页面布局的参考说明（尚未封装）

网格与分栏需表达内容的并列或主从；叠压需有明确层序与安全区；连续长页需有主轴和章节承接。细节沿用 [Coding 构图规则](../../../../references/style/coding/composition-layout.md)，这里不增加新的风格家族路由。

<a id="text.paint"></a>

## 渐变与纹理填字

风格标签：通用。

对应金色标题、蓝色活动标题与印刷字面；复用通用 paint 或纹理短引用，保留真实文字节点。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-text-fill` | `var(--vl-paint,none)` | 渐变、纹理 URL 或 CSS 多层背景列表；使用前必须提供有效 paint 或 fill |
| `--vl-text-fill-size` | `100% 100%` | 渐变通常 100% 100%；纸纹可设 192px 192px |
| `--vl-text-fill-position` | `50% 50%` | 填充图案位置 |

```css
.vl-text-paint { color:transparent; background-image:var(--vl-text-fill,var(--vl-paint,none)); background-size:var(--vl-text-fill-size,100% 100%); background-position:var(--vl-text-fill-position,50% 50%); background-clip:text; }
```

```html
<h2 class="vl-gradient--linear vl-text-paint" style="--vl-gradient-stops:#e0faff 0%,#4dc9ff 45%,#176bbe 100%">蓝色渐变标题</h2>
```

依赖 [通用渐变](../colors/palettes.md#color.gradient)，或者显式提供短引用作为 text-fill。纸纹图片有透明区域时可在同一 fill 列表后叠加纯色渐变底层，防止文字主体变稀。SVG 内部纹理强度需要改资源，单个背景图层没有独立 CSS opacity；需要动态独立强度时使用两层同字节点并只调装饰层。不要直接把整块玻璃卡片样式加到文字上。

<a id="text.outline"></a>

## 文字描边

风格标签：通用。

补齐活动粗字、球面徽章字面与彩色标题轮廓。描边、填字和挤出分别启用。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-text-stroke-width` | `1px` | 字形轮廓宽度，建议 .5–2px |
| `--vl-text-stroke-color` | `#c4f5ff` | 轮廓颜色 |

```css
.vl-text-outline { -webkit-text-stroke:var(--vl-text-stroke-width,1px) var(--vl-text-stroke-color,#c4f5ff); paint-order:stroke fill; }
```

```html
<h2 class="vl-text-outline" style="color:#1678c0;--vl-text-stroke-width:1px">轮廓清晰</h2>
```

薄描边保持字腔，小字号需要减小宽度。图中定制字形、弯曲变形不由描边自动产生；字体仍通过原字体规则选取。此实现使用目标浏览器的 text-stroke，不添加兼容分支。

<a id="text.arc"></a>

## 弧形路径排字

风格标签：通用。

最早粉色手作参考里的弧形 Magic room 属于路径排字；它与“字面凸起”是两个效果。源码存于 [text-arc.svg](../../../svg/text-arc.svg)，由 [弧形标题生成器](../../../../scripts/runtime/make-text-arc.py) 按当前文字生成任务内 SVG。

| 生成参数 | 默认值 | 作用 |
|---|---|---|
| text | 必填 | 真实文字，生成器进行 XML 转义 |
| width / height | 320 / 140 | SVG 画布；默认图形宽高比不强加给所有标题 |
| rise | 40 | 弧线中点比两端抬高的距离；不是 CSS 外层参数 |
| baseline | 100 | 弧线两端 y 坐标 |
| inset | 24 | 两侧路径起止留白 |
| font-size | 28 | 字号；需要在实际字体就绪后检查是否沿路径放得下 |
| letter-spacing | 0 | 字距 |
| font-family | 继承 | 可指定已就绪字体；SVG 以 DOM 插入后可继承页面字体与颜色 |

从 Skill 根目录执行，下例把任务资产副本放在 task/assets；副本中保留本次其他原子需要的资源：

```bash
python3 scripts/runtime/make-text-arc.py --text "MAGIC ROOM" --rise 40 --font-size 28 --output task/assets/svg/title.svg
python3 scripts/runtime/inline-svg-assets.py --input task/draft.html --output task/final.html --asset-root task/assets
```

草稿中使用下面的 DOM 插入标记，正文不粘贴 SVG 源码：

```html
<div style="color:#6b1729;font-family:serif">
  <!-- svg-inline:svg/title.svg -->
</div>
```

生成器保留真实 textPath 文字，组装器按实例重命名路径 ID，重复插入不会串用路径。rise 只改变圆弧近似路径，不使字形本体产生透视或球面变形。生成器检查几何边界，不自动测字／缩字；长标题需扩大画布或减小字号再渲染核验。光晕可在 SVG 外包装用 drop-shadow，不能为每个字预烘焙发光而丢失文字。


<a id="layout.section-masthead"></a>

## 章节眉线

风格标签：通用。

风格不绑定行业。将参考里的重复英文眉题、细线与章节标记抽成通用结构；品牌字形和认证图标不作默认装饰。默认值以 1080px 固定画布试排，其他宽度按设计比例换算。

| 参数 | 默认值 | 作用 |
|---|---|---|
| `--vl-masthead-size` | `20px` | 眉题字号 |
| `--vl-masthead-gap` | `22px` | 眉题与底线间距 |
| `--vl-masthead-after` | `42px` | 底线到标题间距 |
| `--vl-rule-width` | `1px` | 线宽 |

```css
.vl-masthead { display:flex; align-items:end; justify-content:space-between; gap:24px; padding-bottom:var(--vl-masthead-gap,22px); margin-bottom:var(--vl-masthead-after,42px); border-bottom:var(--vl-rule-width,1px) solid var(--vl-edge-color,#bcc3c9); font-size:var(--vl-masthead-size,20px); line-height:1.25; color:var(--vl-muted-ink,#4d5967); }
.vl-masthead > * { min-width:0; overflow-wrap:anywhere; }
```

```html
<div class="vl-masthead"><span>章节主题</span><span>01</span></div>
```


<a id="text.metric-unit"></a>

## 数字与单位层级

风格标签：通用。

数字、单位和说明各用独立真实文字。这里只规定排版，不预填百分比、功效或认证结果。

| 参数 | 默认值 | 作用 |
|---|---|---|
| `--vl-metric-size` | `144px` | 数字字号；可从 96–180px 试排 |
| `--vl-unit-size` | `64px` | 单位字号，与数字分开调 |
| `--vl-metric-weight` | `300` | 数字字重；须使用可用字体字重 |
| `--vl-metric-gap` | `6px` | 数字与单位间距 |
| `--vl-caption-size` | `32px` | 说明字号 |

```css
.vl-metric { display:flex; flex-wrap:wrap; align-items:baseline; gap:var(--vl-metric-gap,6px); color:var(--vl-accent,currentColor); }
.vl-metric__value { font-size:var(--vl-metric-size,144px); font-weight:var(--vl-metric-weight,300); line-height:1.05; font-variant-numeric:lining-nums tabular-nums; }
.vl-metric__unit { font-size:var(--vl-unit-size,64px); line-height:1; }
.vl-metric__caption { flex-basis:100%; margin:12px 0 0; color:var(--vl-ink); font-size:var(--vl-caption-size,32px); line-height:1.35; }
```

```html
<div class="vl-metric"><span class="vl-metric__value">数值</span><span class="vl-metric__unit">单位</span><p class="vl-metric__caption">指标说明与条件</p></div>
```

并列指标复用 evidence-grid；长数字按真实字数试排，不能缩小整组让说明无法阅读。用于浅绿底时单独设深色 metric accent，金色主要用于稳定暗底。

<a id="layout.bilingual-section-title"></a>

## 圆标双语章节标题

风格标签：通用。

空心圆、可增长英文标题、右对齐中文组成三列；整组底边框随最高标题行下移，保持双语对齐且不裁字。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-en-size` | {"default": "32px", "unit": "px", "range": "24–44"} |
| `--cv-mark-size` | {"default": "15px", "unit": "px", "range": "10–20"} |
| `--cv-title-gap` | {"default": "14px", "unit": "px", "range": "8–22"} |
| `--cv-line-color` | {"default": "#294537", "unit": "color", "range": "可辨识线色"} |

```css
.cv-bilingual,.cv-bilingual *{box-sizing:border-box}.cv-bilingual{--cv-en-size:32px;--cv-mark-size:15px;--cv-title-gap:14px;--cv-line-color:#294537;width:min(100%,680px);padding:28px;color:#294537;background:#fff;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-bilingual .cv-bilingual-title{display:grid;grid-template-columns:var(--cv-mark-size) minmax(0,1fr) minmax(4em,28%);gap:var(--cv-title-gap);align-items:baseline;border-bottom:1px solid var(--cv-line-color);padding-bottom:12px;margin:0 0 20px}.cv-bilingual .cv-bilingual-mark{width:var(--cv-mark-size);height:var(--cv-mark-size);border:2px solid currentColor;border-radius:50%;align-self:start;margin-top:.45em}.cv-bilingual .cv-bilingual-en{font-size:var(--cv-en-size);line-height:1.15;font-weight:700;overflow-wrap:anywhere}.cv-bilingual .cv-bilingual-zh{text-align:right;font-size:16px;line-height:1.5;overflow-wrap:anywhere}.cv-bilingual p{margin:0;overflow-wrap:anywhere}@media(max-width:440px){.cv-bilingual .cv-bilingual-title{grid-template-columns:var(--cv-mark-size) minmax(0,1fr)}.cv-bilingual .cv-bilingual-zh{grid-column:2;justify-self:end}}
```

```html
<section class="cv-bilingual"><h2 class="cv-bilingual-title"><span class="cv-bilingual-mark" aria-hidden="true"></span><span class="cv-bilingual-en" lang="en">Professional Experience</span><span class="cv-bilingual-zh" lang="zh-CN">工作经历</span></h2><p>North Studio · Senior Designer · 2021–2025<br>Led design systems and accessible product experiences.</p></section>
```

适配与边界：
- 英文不设置nowrap或固定高度，长英文与中文都能换行；中文仍在自己的列内右对齐。
- 空心圆为装饰并隐藏于辅助技术；底线属于标题整体，不会穿过增长后的文字。
- 局部机制适用于任意双语章节，不限制为简历。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.icon-section-band"></a>

## 矢量图标通栏标题色带

风格标签：通用。

色带占满容器宽度，内部用图标固定列加自适应标题列；内联SVG提供真实几何图标，不依赖emoji或图标字体。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-band-bg` | {"default": "#294b40", "unit": "color", "range": "与前景至少4.5:1"} |
| `--cv-band-fg` | {"default": "#ffffff", "unit": "color", "range": "高对比前景"} |
| `--cv-icon-size` | {"default": "24px", "unit": "px", "range": "18–32"} |
| `--cv-band-pad` | {"default": "28px", "unit": "px", "range": "16–36"} |

```css
.cv-iconband,.cv-iconband *{box-sizing:border-box}.cv-iconband{--cv-band-bg:#294b40;--cv-band-fg:#fff;--cv-icon-size:24px;--cv-band-pad:28px;width:min(100%,680px);background:#fff;color:#253a31;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-iconband .cv-iconband-title{display:grid;grid-template-columns:var(--cv-icon-size) minmax(0,1fr);align-items:start;gap:14px;padding:16px var(--cv-band-pad);margin:0;background:var(--cv-band-bg);color:var(--cv-band-fg);font-size:20px;line-height:1.4}.cv-iconband .cv-iconband-icon{width:var(--cv-icon-size);height:var(--cv-icon-size);margin-top:2px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linejoin:round;stroke-linecap:round}.cv-iconband .cv-iconband-label{overflow-wrap:anywhere}.cv-iconband .cv-iconband-body{padding:22px var(--cv-band-pad)}.cv-iconband p{margin:0 0 10px;overflow-wrap:anywhere}
```

```html
<section class="cv-iconband"><h2 class="cv-iconband-title"><svg class="cv-iconband-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="7" width="18" height="14" rx="1"/><path d="M8 7V3h8v4M3 12h18M10 12v3h4v-3"/></svg><span class="cv-iconband-label">工作经历 / Experience</span></h2><div class="cv-iconband-body"><p><strong>North Studio · Senior Designer</strong><br>2021–2025</p><p>Built consistent interfaces and reusable editorial components.</p></div></section>
```

适配与边界：
- 通栏色带不是包围正文的圆角卡；正文与色带共用水平内距实现同轴。
- 标题换行时色带自然增高，SVG固定首行锚点且不遮文字。
- 图标作为装饰隐藏；若图标承担独立信息，应另外提供可访问名称。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.display-script-overlap"></a>

## 展示字与书写字叠层

风格标签：通用。

同一标题中的展示字占正常流，书写字绝对锚定于标题盒底部；通过预留底部空间把重叠限制在展示字下沿，白色细描边保护字腔并区分两层，而非两行缩进。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-display-size` | {"default": "86px", "unit": "px", "range": "56–100"} |
| `--cv-script-size` | {"default": "54px", "unit": "px", "range": "36–66"} |
| `--cv-script-x` | {"default": "26%", "unit": "%", "range": "10–35"} |
| `--cv-script-y` | {"default": "30px", "unit": "px", "range": "24–34；对应默认字号"} |
| `--cv-script-angle` | {"default": "-8deg", "unit": "deg", "range": "-12–0"} |
| `--cv-title-bg` | {"default": "#f6f3ea", "unit": "color", "range": "必须与描边背景相同"} |

```css
.cv-script,.cv-script *{box-sizing:border-box}.cv-script{--cv-display-size:86px;--cv-script-size:54px;--cv-script-x:26%;--cv-script-y:30px;--cv-script-angle:-8deg;--cv-title-bg:#f6f3ea;width:min(100%,680px);padding:32px 28px;background:var(--cv-title-bg);color:#243b31;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-script .cv-script-kicker{margin:0 0 18px;font-size:18px}.cv-script .cv-script-title{position:relative;isolation:isolate;margin:0 0 22px;padding-bottom:70px;font-weight:400;line-height:1}.cv-script .cv-script-display{position:relative;z-index:0;display:block;font:900 var(--cv-display-size)/1 Arial,sans-serif;letter-spacing:-.055em;overflow-wrap:anywhere}.cv-script .cv-script-hand{position:absolute;z-index:1;left:var(--cv-script-x);bottom:var(--cv-script-y);max-width:calc(100% - var(--cv-script-x) - 16px);transform:rotate(var(--cv-script-angle));transform-origin:left center;font:400 var(--cv-script-size)/1.15 'Snell Roundhand',cursive;color:#b14832;-webkit-text-stroke:2px var(--cv-title-bg);paint-order:stroke fill;white-space:nowrap}.cv-script .cv-script-copy{margin:0;overflow-wrap:anywhere}@media(max-width:520px){.cv-script{--cv-display-size:56px;--cv-script-size:38px;--cv-script-x:18%;--cv-script-y:34px}}
```

```html
<article class="cv-script"><h2 class="cv-script-kicker">个人履历</h2><h1 class="cv-script-title" aria-label="Alex Chen — Selected work"><span class="cv-script-display" aria-hidden="true">ALEX CHEN</span><span class="cv-script-hand" aria-hidden="true">Selected work</span></h1><p class="cv-script-copy">Product &amp; Editorial Designer<br>North Studio · 2021–2025<br>Creating thoughtful systems for digital and printed experiences.</p></article>
```

适配与边界：
- 展示字实际指定Arial，书写字实际指定Snell Roundhand；未安装Snell Roundhand的设备会回退，需合法字体授权后用@font-face部署才能保证一致。
- 默认锚点将书写字限制在大字下缘而不横穿主要字腔；自定义字体度量后需目视复核，不把整块不透明底色盖到大字上。
- 展示标题可以换行；书写短语建议不超过18个拉丁字符，长短语应减小字号或改短文案，不能无限叠压。
- 页面28px内距、标题底部70px预留、描边分层分别承担外沿、文字和叠层安全区。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.external-terminal-title"></a>

## 框外避字终端章节标题

风格标签：通用。

该原子只负责框外标题布局；标题与下方面板必须是正常文档流中的前后兄弟，不用负margin或绝对定位把标题压入框。字号--ct-title-size默认36px，建议34–39px；字距线间隔gap默认12px，建议10–18px；标题最大宽470px，relative-max默认76vw，在嵌套组合中应覆盖为适合其容器的上限。左右相等弹性列保证标题居中，线不穿字。行高1.3，panel-gap默认10px。真实标题用h2或h3；装饰span均aria-hidden。长标题自然换行，极窄容器允许装饰线缩到零；不限制标题行数。字体由使用方绑定。

```css
.ct-title{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,auto) minmax(0,1fr);align-items:center;column-gap:var(--ct-title-gap,12px);width:100%;min-width:0;margin:0 0 var(--ct-title-panel-gap,10px);box-sizing:border-box;}.ct-title__text{display:block;min-width:0;max-width:min(var(--ct-title-max,470px),var(--ct-title-relative-max,76vw));margin:0;color:var(--ct-title-color,inherit);font-size:var(--ct-title-size,36px);font-weight:var(--ct-title-weight,700);line-height:var(--ct-title-leading,1.3);text-align:center;overflow-wrap:anywhere;word-break:normal;}.ct-title__line{position:relative;display:block;height:var(--ct-title-mark-height,15px);min-width:0;pointer-events:none;background:linear-gradient(var(--ct-title-line-color,#8bb1bc),var(--ct-title-line-color,#8bb1bc)) center/100% var(--ct-title-line,1px) no-repeat;}.ct-title__line::after{content:'';position:absolute;right:0;top:0;width:var(--ct-title-mark-width,8px);height:6px;border-top:var(--ct-title-line,1px) solid var(--ct-title-line-color,#8bb1bc);border-left:var(--ct-title-line,1px) solid var(--ct-title-line-color,#8bb1bc);}.ct-title__line--right{transform:rotate(180deg);}
```

```html
<section style="width:min(100%,602px)"><div class="ct-title"><span class="ct-title__line" aria-hidden="true"></span><h2 class="ct-title__text">框外章节标题</h2><span class="ct-title__line ct-title__line--right" aria-hidden="true"></span></div><div style="border:1px solid #85a8b4;padding:30px">下方面板随标题换行下移。</div></section>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。
