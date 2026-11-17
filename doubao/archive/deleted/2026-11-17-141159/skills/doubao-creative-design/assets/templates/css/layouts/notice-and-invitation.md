# 通知与邀请的单屏布局

只维护几何、阅读顺序、叠放和安全区；颜色、字体、纸纹、插画风格留在组合。尺寸变量是起点，内容增长必须重新校验，不靠裁切隐藏。

**检索契约**：产物类型是语义，不是发布平台。整版布局适用于通知/公告/邀请函/喜报；社媒单张通知仍属于通知。跨产物借用必须先选择“局部模块”，显式说明适用性，不能套用整版。`--artifact`启用严格产物白名单筛选，未标注适用产物的旧条目也不自动放行；不带筛选仅为词法召回，不能保证产物适配。

<a id="layout.title-letter-stack"></a>

## 宣告区—信纸—页脚单屏布局

产物标签：通知、公告、邀请函、喜报。布局范围：整张单屏。风格：通用。

标题/主视觉、独立信纸、页脚依次占区；主体纸面是全文唯一承托，背景跨全页。信纸正文先排容量，页脚不得被绝对定位挤入。

```css
.vl-notice-stack{position:relative;isolation:isolate;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:var(--notice-section-gap,24px);padding:var(--notice-page-inset,40px);min-height:var(--notice-page-height,1000px)}.vl-notice-stack__backdrop{position:absolute;inset:0;z-index:-1}.vl-notice-stack__paper{min-width:0;padding:var(--notice-paper-inset,32px)}.vl-notice-stack__footer{min-width:0}
```

```html
<article class="vl-notice-stack"><div class="vl-notice-stack__backdrop"></div><header>标题与主视觉</header><section class="vl-notice-stack__paper">正文与落款</section><footer class="vl-notice-stack__footer">页脚信息</footer></article>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。

<a id="layout.split-masthead"></a>

## 标题与标识分列

产物标签：通知、公告、邀请函、喜报。布局范围：局部模块。风格：通用。

标题在主列，品牌/编号在辅列；两者有独立净空。副题跟随标题列，不被品牌挤出。

```css
.vl-notice-masthead{display:grid;grid-template-columns:minmax(0,1fr) var(--notice-mark-width,100px);column-gap:var(--notice-mark-gap,24px);align-items:start}.vl-notice-masthead__title{min-width:0;margin:0;overflow-wrap:break-word}.vl-notice-masthead__mark{width:100%;max-height:var(--notice-mark-height,140px);object-fit:contain}
```

```html
<header class="vl-notice-masthead"><div class="vl-notice-masthead__title">主标题与副题</div><img class="vl-notice-masthead__mark" src="{{brand_mark}}" alt="品牌标识"></header>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。

<a id="layout.bound-paper-stack"></a>

## 标题与装订纸的叠放

产物标签：通知、公告、邀请函、喜报。布局范围：整张单屏。风格：通用。

上方标题/插画，下方单张信纸；装订带跨纸上沿，前景仅进入预留装饰区。适用于2/4/7的不同装订样式，环形/直条是shape职责，不随布局固定。

```css
.vl-notice-bound{--notice-bind-safe:52px;display:grid;gap:var(--notice-hero-gap,32px);padding:var(--notice-page-inset,32px)}.vl-notice-bound__hero{position:relative;min-height:var(--notice-hero-height,280px)}.vl-notice-bound__paper{position:relative;isolation:isolate;padding:var(--notice-bind-safe) var(--notice-paper-inset,32px) var(--notice-paper-bottom,32px)}.vl-notice-bound__binding{position:absolute;top:0;left:var(--notice-paper-inset,32px);right:var(--notice-paper-inset,32px);transform:translateY(-50%);height:var(--notice-bind-height,42px);pointer-events:none}.vl-notice-bound__body{position:relative;min-width:0}.vl-notice-bound__foreground{position:absolute;right:0;top:0;transform:translateY(-70%);max-width:var(--notice-art-width,30%);max-height:var(--notice-art-height,130px);object-fit:contain}
```

```html
<article class="vl-notice-bound"><header class="vl-notice-bound__hero">标题与主视觉</header><section class="vl-notice-bound__paper"><div class="vl-notice-bound__binding" aria-hidden="true">装订装饰槽</div><img class="vl-notice-bound__foreground" src="{{edge_art}}" alt=""><div class="vl-notice-bound__body">正文</div></section><footer>落款</footer></article>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。

<a id="layout.sectioned-ticket"></a>

## 悬挂票据的标题与分段正文

产物标签：通知、公告、邀请函、喜报。布局范围：整张单屏。风格：通用。

悬挂横杆在纸后，标题区与事实区用一条分隔界面连接；内凹口和锯齿是边缘装饰，不将每段拆卡。二维码联络区在票据之外。

```css
.vl-notice-ticket{padding:var(--notice-page-inset,40px);display:grid;gap:var(--notice-footer-gap,32px)}.vl-notice-ticket__paper{position:relative;isolation:isolate}.vl-notice-ticket__rail{position:absolute;z-index:-1;left:-24px;right:-24px;top:-5px;height:var(--notice-rail-height,20px)}.vl-notice-ticket__header{padding:var(--notice-header-inset,32px);text-align:center}.vl-notice-ticket__separator{position:relative;height:var(--notice-tear-gap,28px)}.vl-notice-ticket__body{padding:var(--notice-body-inset,32px);display:grid;gap:var(--notice-fact-gap,28px)}.vl-notice-ticket__footer{min-width:0}
```

```html
<article class="vl-notice-ticket"><section class="vl-notice-ticket__paper"><div class="vl-notice-ticket__rail"></div><header class="vl-notice-ticket__header">品牌与公告标题</header><div class="vl-notice-ticket__separator" aria-hidden="true">分隔边缘槽</div><div class="vl-notice-ticket__body">分组事实</div></section><footer class="vl-notice-ticket__footer">二维码联络信息</footer></article>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。

<a id="layout.contact-footer"></a>

## 二维码与落款联络区

产物标签：通知、公告、邀请函、喜报。布局范围：局部模块。风格：通用。

二维码固定辅列，机构/日期/联系方式在弹性主列；分隔线可选，文字不进入二维码静区。文字增长撑高行，不把码压小。

```css
.vl-notice-contact{display:grid;grid-template-columns:calc(var(--notice-qr-size,96px) + 2 * var(--notice-qr-quiet,8px)) minmax(0,1fr);gap:var(--notice-contact-gap,24px);align-items:center;padding:var(--notice-contact-inset,16px)}.vl-notice-contact__qr{box-sizing:content-box;width:var(--notice-qr-size,96px);height:var(--notice-qr-size,96px);object-fit:contain;padding:var(--notice-qr-quiet,8px);background:white}.vl-notice-contact__text{min-width:0;overflow-wrap:break-word;text-align:var(--notice-contact-align,right)}
```

```html
<footer class="vl-notice-contact"><img class="vl-notice-contact__qr" src="{{confirmed_qr}}" alt="二维码"><div class="vl-notice-contact__text">确认的机构、日期或联络信息</div></footer>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。

<a id="layout.labeled-facts"></a>

## 标签与事实说明分组

产物标签：通知、公告、邀请函、喜报。布局范围：局部模块。风格：通用。

每组标签与一段事实共用阅读轴；标签可左对齐印章式，也可居中胶囊式。段落之间留白，不压到下一组。

```css
.vl-notice-facts{display:grid;gap:var(--notice-fact-gap,28px)}.vl-notice-facts__group{display:grid;gap:var(--notice-label-gap,14px);min-width:0}.vl-notice-facts__label{justify-self:var(--notice-label-align,start);margin:0;max-width:100%}.vl-notice-facts__copy{margin:0;line-height:var(--notice-copy-leading,1.6);overflow-wrap:break-word}
```

```html
<section class="vl-notice-facts"><section class="vl-notice-facts__group"><h2 class="vl-notice-facts__label">事项标签</h2><p class="vl-notice-facts__copy">确认的事实说明</p></section><section class="vl-notice-facts__group"><h2 class="vl-notice-facts__label">下一事项</h2><p class="vl-notice-facts__copy">确认的说明</p></section></section>
```

安全区：以实际文字与素材边界验收；品牌、二维码、装订和插画各有独立净空。QR列的最小宽度需含两侧静区，绑定时将列宽设为码尺寸加两倍静区；图形自身已带静区时不要重复计算。固定画布溢出时先调整容量和分组，不隐藏正文。
