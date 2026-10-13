# 可编辑套图内容页布局

本文件提供独立单页的结构起点：介绍、参与、话题、奖励、地图。按内容职责选结构，再继承确认封面的字体、配色、边缘与材质。案例中的引文面、操作纸片、照片说明、奖品陈列与地图优先关系可借用；这里是通用实现，不声明三套参考图的精确复刻。

每个条目的 `get --dependencies --templates` 返回本页 CSS、HTML 骨架与共用层；`--templates` 用于显式读取 HTML 示例。示例文案与素材槽由实际内容替换；正式输出沿公共契约把样式展开到真实节点。每页单独组装与导出，CSS 来源在实现注释中记录 ID 和消费者。

<a id="carousel.frame"></a>

## 共用固定画布与自然流

参考尺寸 516×696；根宽高由目标平台确定。字号、边距和图窗须按最终画幅及字体试排调整，不用整体 transform 缩放正文。默认上下安全区为 56／84px，左右 31px；实际平台规则优先。准确主体、照片、奖品与地图使用任务资产；示例槽只表示职责。底图由确认封面的同源纹理、渐变或图片补充，纯透明底是结构默认值。

参数：`--cc-width/height` 画布；`--cc-safe-top/bottom/side` 安全区；`--cc-gap` 模块距离；`--cc-title/body/leading` 字级与行高；`--cc-font` 实际已验证字体。页面正文保持自然换行与真实占位，溢出交给验收发现。容量适配沿套图 Spec 的扩容、减留白、调整图文、密集变体或拆页顺序；本文件不预先宣称任何高密度版本已通过。

```css
.cc-page{box-sizing:border-box;position:relative;isolation:isolate;width:var(--cc-width,516px);height:var(--cc-height,696px);padding:var(--cc-safe-top,56px) var(--cc-safe-side,31px) var(--cc-safe-bottom,84px);display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:var(--cc-gap,16px);font:var(--cc-body,16px)/var(--cc-leading,1.45) var(--cc-font,sans-serif);color:var(--cc-ink,inherit);background:var(--cc-base,transparent)}
.cc-page *{box-sizing:border-box}
.cc-page :where(h1,h2,h3,p,figure,blockquote,dl,dd,ol,ul){margin:0}
.cc-page :where(h1,h2,h3,p,li,dd,figcaption){overflow-wrap:anywhere}
.cc-page h1{font-size:var(--cc-title,36px);line-height:1.12}
.cc-page h2{font-size:var(--cc-subtitle,21px);line-height:1.25}
.cc-page h3{font-size:var(--cc-item-title,18px);line-height:1.3}
.cc-head,.cc-body,.cc-foot,.cc-copy{min-width:0}
.cc-head,.cc-copy{display:grid;gap:8px;align-content:start}
.cc-body{min-height:0}
.cc-foot{font-size:var(--cc-meta,11px);line-height:1.4}
.cc-media{position:relative;min-width:0;min-height:0;display:grid;place-items:center}
.cc-media>img{display:block;width:100%;height:100%;object-fit:var(--cc-fit,contain)}
.cc-media>span{font-size:12px;text-align:center}
.cc-eyebrow{font-size:var(--cc-meta,11px)}
```

<a id="layout.carousel-statement"></a>

## 引文主场与下方议题区

布局：上方品牌／标题，中部单一引文阅读面，下方议题或下一步提示，页脚保留来源。适用理念、活动介绍、价值说明。保留一条阅读轴；引文可用切角纸面、半透明承托或开放排字，纸面属于视觉层。

```json
{"common":"carousel.frame"}
```

```css
.cc-statement .cc-body{display:grid;grid-template-rows:minmax(min-content,1fr) auto;gap:var(--cc-gap,16px)}
.cc-statement .cc-quote{align-self:center;display:grid;gap:16px;padding:var(--cc-quote-inset,18px);text-align:var(--cc-quote-align,left)}
.cc-statement .cc-topics-note{display:grid;gap:8px;border-top:1px solid currentColor;padding-top:12px}
```

```html
<article class="cc-page cc-statement">
  <header class="cc-head"><p class="cc-eyebrow">主题识别</p><h1>活动介绍</h1></header>
  <main class="cc-body"><blockquote class="cc-quote"><p>本页核心主张，以已确认的准确文案替换。</p><p>补充背景、价值或必要条件，保持正文的阅读顺序。</p></blockquote><aside class="cc-topics-note"><h2>继续探索</h2><p>关联议题或下一页引导。</p></aside></main>
  <footer class="cc-foot">来源与页次</footer>
</article>
```

容量：短文靠阅读面位置与段间关系建立重心，长文先减少非语义留白；正文与下方议题区保持独立占位。

<a id="layout.carousel-steps"></a>

## 编号操作与参与条件

布局：标题与导语、按序编号的操作组、底部参与条件或收益，统一页脚。适用参与方式、投稿流程、教程；序号明确先后，每步文字保持完整。

```json
{"common":"carousel.frame"}
```

```css
.cc-steps .cc-body{display:grid;grid-template-rows:auto minmax(min-content,1fr) auto;gap:var(--cc-gap,16px)}
.cc-steps-list{list-style:none;padding:0;display:grid;gap:var(--cc-step-gap,18px);align-content:center}
.cc-steps-list>li{display:grid;grid-template-columns:2em minmax(0,1fr);gap:12px;align-items:start}
.cc-step-number{font-size:24px;line-height:1.2;font-weight:700}
.cc-step-note{padding-top:12px;border-top:1px solid currentColor}
```

```html
<article class="cc-page cc-steps">
  <header class="cc-head"><p class="cc-eyebrow">参与指南</p><h1>发笔记领周边</h1></header>
  <main class="cc-body"><p>参与日期与范围由活动真实资料提供。</p><ol class="cc-steps-list"><li><span class="cc-step-number">01</span><div class="cc-copy"><h2>发布相关笔记</h2><p>写明操作与必要话题。</p></div></li><li><span class="cc-step-number">02</span><div class="cc-copy"><h2>完成参与条件</h2><p>写明判定方式与条件。</p></div></li></ol><aside class="cc-step-note"><p>奖励、限制或下一步行动。</p></aside></main>
  <footer class="cc-foot">活动来源与页次</footer>
</article>
```

容量：2–3 步为试排起点，条件归属到对应步骤；真实活动只有一个动作时，改用主动作加条件结构，保持事实而非补造步骤。

<a id="layout.carousel-topics"></a>

## 分类标题与错列图文组

布局：统一页题，下方 2–3 个有独立小标题的主题组；可按内容加入侧图，交替照片位置。适用话题方向、灵感、分类说明与清单。并列组保持可比较，组间差异来自内容权重与图片职责。

```json
{"common":"carousel.frame"}
```

```css
.cc-topics .cc-body{display:grid;grid-auto-rows:minmax(min-content,1fr);gap:var(--cc-topic-gap,14px)}
.cc-topic{min-width:0;display:grid;align-content:center;gap:8px;padding:var(--cc-topic-inset,12px) 0;border-top:1px solid currentColor}
.cc-topic:first-child{border-top:0}
.cc-topic.has-media{grid-template-columns:minmax(0,1fr) var(--cc-thumb-width,108px);column-gap:14px}
.cc-topic.has-media>.cc-media{grid-column:2;grid-row:1/3;min-height:90px}
.cc-topic.has-media:nth-child(even){grid-template-columns:var(--cc-thumb-width,108px) minmax(0,1fr)}
.cc-topic.has-media:nth-child(even)>.cc-media{grid-column:1}
.cc-topic.has-media:nth-child(even)>:not(.cc-media){grid-column:2}
```

```html
<article class="cc-page cc-topics">
  <header class="cc-head"><p class="cc-eyebrow">主题灵感</p><h1>话题方向</h1></header>
  <main class="cc-body"><section class="cc-topic"><h2>话题一</h2><p>本组核心问题与具体表达方向。</p></section><section class="cc-topic"><h2>话题二</h2><p>与第一组不同的内容入口。</p></section><section class="cc-topic"><h2>话题三</h2><p>第三类说明与示例。</p></section></main>
  <footer class="cc-foot">参与入口与页次</footer>
</article>
```

照片变体：需要照片的主题组增加 `has-media` 与带任务素材的 `figure.cc-media`，保持标题和说明关联。长文优先增加该组容量，窄图文区可回到纯文字分类；图窗比例与图片裁切按素材验证。

<a id="layout.carousel-rewards"></a>

## 权益说明与奖品展陈

布局：页题、权益及成立条件、奖品／作品陈列带和页脚。适用奖励、权益、实物展示与画廊。正文说明“如何获得”，陈列区说明“是什么”，标签紧随所属对象。

```json
{"common":"carousel.frame"}
```

```css
.cc-rewards .cc-body{display:grid;grid-template-rows:auto minmax(min-content,1fr);gap:var(--cc-gap,16px)}
.cc-benefits{display:grid;gap:14px}
.cc-display{display:grid;grid-template-columns:repeat(var(--cc-display-columns,3),minmax(0,1fr));gap:12px;align-content:center}
.cc-display>figure{display:grid;grid-template-rows:minmax(80px,1fr) auto;gap:8px;min-width:0}
.cc-display figcaption{font-size:14px;text-align:center}
```

```html
<article class="cc-page cc-rewards">
  <header class="cc-head"><p class="cc-eyebrow">活动权益</p><h1>奖励与周边</h1></header>
  <main class="cc-body"><div class="cc-benefits"><section class="cc-copy"><h2>主要权益</h2><p>已确认的奖励数值与获得条件。</p></section><section class="cc-copy"><h2>补充权益</h2><p>适用范围与名额说明。</p></section></div><div class="cc-display"><figure><div class="cc-media" data-asset-slot="reward-1"><span>奖品素材待绑定</span></div><figcaption>奖品名称</figcaption></figure><figure><div class="cc-media" data-asset-slot="reward-2"><span>奖品素材待绑定</span></div><figcaption>奖品名称</figcaption></figure><figure><div class="cc-media" data-asset-slot="reward-3"><span>奖品素材待绑定</span></div><figcaption>奖品名称</figcaption></figure></div></main>
  <footer class="cc-foot">规则来源与页次</footer>
</article>
```

容量：陈列 3 件为起点，4–6 件可两行重排并复查主体可见尺度；纯权益页以文字关系为主，按内容移除素材槽。数量与价值由事实决定。

<a id="layout.carousel-map"></a>

## 活动信息与地图主场

布局：标题、简短介绍、时间地点、独立地图大区与图例／页脚。适用活动场地、路线和空间导览。保留地图的空间关系与足够可见面积；真实地图来自获准资产或核实坐标，概念示意标明性质。

```json
{"common":"carousel.frame"}
```

```css
.cc-map .cc-body{display:grid;grid-template-rows:auto auto minmax(140px,1fr) auto;gap:12px}
.cc-facts{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 12px}
.cc-map .cc-media{align-self:stretch}
.cc-map-legend{display:flex;flex-wrap:wrap;gap:6px 16px;list-style:none;padding:0;font-size:14px}
```

```html
<article class="cc-page cc-map">
  <header class="cc-head"><p class="cc-eyebrow">到场指南</p><h1>活动场地</h1></header>
  <main class="cc-body"><p>简短活动介绍，承接封面主题。</p><dl class="cc-facts"><dt>时间</dt><dd>已确认时间</dd><dt>地点</dt><dd>已确认地点</dd></dl><figure class="cc-media" data-asset-slot="verified-map"><span>地图／空间示意素材待绑定</span></figure><ul class="cc-map-legend"><li>入口与交通</li><li>活动区域</li></ul></main>
  <footer class="cc-foot">地图来源与页次</footer>
</article>
```

准确标注可独立用原生文字或 SVG 实现，基于核实位置定位；图例顺序对应地图内容。长导语先按 Spec 调整分配，保持地图与标注可读。地图素材本身与布局骨架分别验收。
