# 叠层拼贴

状态：已填充。参数为参考图的视觉近似与可调起点，正式输出按既有协议展开节点、样式行内化和 SVG 内嵌。

<a id="layout.collage"></a>

## 叠层拼贴

风格标签：通用。

参考演我大赛、蓝色活动、秋日商业活动和演唱会战报。纸张／照片共享网格占位，旋转、位移与层级只由实例覆盖；不复制四套拼贴实现。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-collage-columns` | `12` | 正整数；页内使用统一列数 |
| `--vl-collage-gap` | `12px` | 网格间距，建议 0–32px |
| `--vl-collage-inset` | `24px` | 为旋转与外伸预留空间 |
| `--vl-col-start` | `auto` | 实例起始列 |
| `--vl-col-span` | `6` | 实例列跨度，不能大于总列数 |
| `--vl-row-start` | `auto` | 实例起始行；同一行允许叠放 |
| `--vl-row-span` | `1` | 实例行跨度 |
| `--vl-stack-order` | `0` | 实例层级，数值更大则靠前 |

```css
.vl-collage { display:grid; grid-template-columns:repeat(var(--vl-collage-columns,12),minmax(0,1fr)); gap:var(--vl-collage-gap,12px); padding:var(--vl-collage-inset,24px); isolation:isolate; }
.vl-collage__item { position:relative; min-width:0; grid-column:var(--vl-col-start,auto)/span var(--vl-col-span,6); grid-row:var(--vl-row-start,auto)/span var(--vl-row-span,1); z-index:var(--vl-stack-order,0); transform:translate(var(--vl-shift-x,0px),var(--vl-shift-y,0px)) rotate(var(--vl-rotate,0deg)); transform-origin:center; overflow-wrap:anywhere; }
:where(.vl-collage__item img) { display:block; max-width:100%; height:auto; }
```

```html
<section class="vl-collage">
  <figure class="vl-collage__item" style="margin:0;--vl-col-start:1;--vl-col-span:8;--vl-row-start:1;--vl-rotate:-3deg">主照片</figure>
  <aside class="vl-collage__item" style="--vl-col-start:8;--vl-col-span:5;--vl-row-start:1;--vl-stack-order:1;--vl-rotate:4deg;--vl-shift-y:30px">短便签</aside>
</section>
```

rotate、shift-x/y 复用 [局部位移参数](layout-and-type.md#layouts.parameters)。默认网格占位不会为 transform 外伸自动增加空间；在 HTML 实现 明确遮挡对象、允许区域、正文保护区和外边界。上例重叠一列，只适合右侧有空白的主图；不要遮挡人脸、关键商品或正文。窄画布改为单列时同时设置实例 --vl-col-start:auto、col-span=1、row-start=auto 并取消重叠位移。

<a id="layout.letter-in-envelope"></a>

## 信纸插入信封的叠层布局

风格标签：通用。

粒度：组件布局。已有collage是通用网格与实例位移，未提供信封底部遮挡带和随内容增高的安全区契约；本条将其明确为独立结构。

[信封折片](../shapes/notes-and-paper.md#shape.envelope-flaps)只负责形状；本条负责信纸在后、折片在前、封印跨界及内容避让。paper padding-bottom=折片深度+安全距，保证最后一行位于整个折片包围盒上方；长文案增长时信纸和外容器一起增高，前封片保持贴底。封印固定在折片交界，不随正文段落定位。

默认值以约540px组件宽度试排；envelope-depth建议120–200px，letter-safe建议32–56px；可覆盖，必须为正且适配组件宽度。窄组件先减左右内距，不压缩字形。信纸只让背景paint半透明，不对含文字article设置opacity。文字内容和所有前景装饰均需独立检查。

```css
.vl-letter-envelope { position:relative; isolation:isolate; width:100%; box-sizing:border-box; --vl-envelope-depth:180px; --vl-letter-safe:42px; }
.vl-letter-envelope__paper { position:relative; z-index:1; margin:0 var(--vl-paper-inset,8px); padding:var(--vl-paper-top,60px) var(--vl-paper-side,48px) calc(var(--vl-envelope-depth) + var(--vl-letter-safe)); box-sizing:border-box; border-radius:var(--vl-paper-radius,44px) var(--vl-paper-radius,44px) 0 0; background:var(--vl-paper-paint,#fffdf1); }
.vl-letter-envelope__content { display:flex; flex-direction:column; gap:var(--vl-letter-gap,38px); min-width:0; }
.vl-letter-envelope__front { position:absolute; inset:auto 0 0; height:var(--vl-envelope-depth); z-index:3; pointer-events:none; }
.vl-letter-envelope__seal { position:absolute; left:50%; bottom:calc(var(--vl-envelope-depth)*.52); transform:translate(-50%,50%); width:var(--vl-seal-size,72px); height:var(--vl-seal-size,72px); z-index:4; pointer-events:none; }
```

```html
<section class="vl-letter-envelope">
 <article class="vl-letter-envelope__paper"><div class="vl-letter-envelope__content"><h2>活动主题</h2><p>邀请正文</p><div>时间与地点</div></div></article>
 <div class="vl-letter-envelope__front"><!-- 放置shape.envelope-flaps的完整节点 --></div>
 <div class="vl-letter-envelope__seal"><!-- 可选shape.wax-seal；不在此重复维护封印材质 --></div>
</section>
```

<a id="layout.cross-zone-sections"></a>

## 背景分区与跨界内容

风格标签：通用。

整页渐变生成独立连续背景分区；首行精确落在背景边界，下一行的人物占位和正文栏目分别以负外距跨界。内容保持正常文档流并自然推高后续行。

适用产物：简历／个人履历／作品集介绍页；粒度：局部模块。此原子不代替整页组合。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-boundary` | {"default": "190px", "unit": "px", "range": "160–260"} |
| `--cv-cross` | {"default": "36px", "unit": "px", "range": "16–56"} |
| `--cv-person-width` | {"default": "170px", "unit": "px", "range": "130–200"} |
| `--cv-zone-top` | {"default": "#d9e7e3", "unit": "color", "range": "浅色"} |
| `--cv-zone-bottom` | {"default": "#f4f1e8", "unit": "color", "range": "浅色"} |
| `--cv-safe` | {"default": "24px", "unit": "px", "range": "16–36"} |

```css
.cv-zones,.cv-zones *{box-sizing:border-box}.cv-zones{--cv-boundary:190px;--cv-cross:36px;--cv-person-width:170px;--cv-zone-top:#d9e7e3;--cv-zone-bottom:#f4f1e8;--cv-safe:24px;width:min(100%,680px);display:grid;grid-template-columns:var(--cv-safe) var(--cv-person-width) var(--cv-safe) minmax(0,1fr) var(--cv-safe);grid-template-rows:minmax(var(--cv-boundary),auto) auto auto;isolation:isolate;background:var(--cv-zone-bottom);color:#233a34;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-zones .cv-zones-head{grid-column:2/5;grid-row:1;padding-top:var(--cv-safe);padding-bottom:calc(var(--cv-cross) + 16px);min-height:0}.cv-zones h1{font-size:32px;line-height:1.2;margin:0 0 8px}.cv-zones p{margin:0 0 12px;overflow-wrap:anywhere}.cv-zones .cv-zones-person{grid-column:2;grid-row:2;margin:calc(-1 * var(--cv-cross)) 0 0;align-self:start;z-index:1;aspect-ratio:3/4;background:#839e94;overflow:hidden}.cv-zones .cv-zones-person svg{display:block;width:100%;height:100%}.cv-zones .cv-zones-section{grid-column:4;grid-row:2;z-index:2;margin-top:calc(-1 * var(--cv-cross));padding:var(--cv-safe);background:#fff;min-width:0}.cv-zones h2{font-size:18px;margin:0 0 12px}.cv-zones .cv-zones-footer{grid-column:2/5;grid-row:3;padding:var(--cv-safe) 0}@media(max-width:500px){.cv-zones{--cv-person-width:110px;--cv-safe:16px}.cv-zones .cv-zones-section{padding:16px}.cv-zones h1{font-size:26px}}
.cv-zones::before{content:"";grid-column:1/-1;grid-row:1;background:var(--cv-zone-top);z-index:-1}
```

```html
<article class="cv-zones" aria-label="作品集介绍页"><header class="cv-zones-head"><h1>个人简介</h1><p>Alex Chen · Independent Designer</p></header><figure class="cv-zones-person" aria-label="跨背景人物占位"><svg viewBox="0 0 150 200" role="img" aria-label="Portrait placeholder"><circle cx="75" cy="65" r="32" fill="#e5e8dc"/><path d="M12 200v-28a63 63 0 0 1 126 0v28" fill="#e5e8dc"/></svg></figure><section class="cv-zones-section"><h2>精选经历</h2><p><strong>North Studio · 2021–2025</strong></p><p>Led visual systems and product design for civic services. Partnered with researchers and developers from discovery through delivery.</p></section><section class="cv-zones-footer"><h2>设计方向</h2><p>Editorial systems · Accessible interfaces · Service design</p></section></article>
```

适配与边界：
- 背景层0、人物层1、栏目层2；仅跨界栏目使用白色承载面，不统一套卡。
- 页面安全区由--cv-safe控制；人物安全区限制在独立网格列；文字安全区为白色栏目内距，三者不互相侵占。
- 头部为minmax最小高；长文自然增高，同网格背景边界同步移动；不使用正文滚动区域。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="layout.curve-portrait-junction"></a>

## 回转带与人像交界布局

风格标签：通用。

共享U形带原子的坐标系，把圆形人物锚定在左侧竖段进入弯折的位置；标题放在开口内，详细经历放在图形下方。本项CSS仅负责层级、锚点与安全区，不重画U形。

适用产物：简历／个人履历／作品集介绍页；粒度：局部模块。此原子不代替整页组合。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-stage-height` | {"default": "380px", "unit": "px", "range": "360–460；变化时需同步SVG坐标系"} |
| `--cv-portrait-size` | {"default": "108px", "unit": "px", "range": "80–112"} |
| `--cv-portrait-x` | {"default": "64px", "unit": "px", "range": "默认与依赖带左侧中心线一致"} |
| `--cv-portrait-y` | {"default": "220px", "unit": "px", "range": "默认与依赖带左弯起点一致"} |
| `--cv-inner-left` | {"default": "142px", "unit": "px", "range": "不少于左带外缘加28px"} |
| `--cv-inner-right` | {"default": "142px", "unit": "px", "range": "不少于右带外缘加28px"} |

依赖：[回转色带](../shapes/organic-shapes.md#shape.u-turn-band)。

```json
{"dependencies":["shape.u-turn-band"]}
```

```css
.cv-junction,.cv-junction *{box-sizing:border-box}.cv-junction{--cv-stage-height:380px;--cv-portrait-size:108px;--cv-portrait-x:64px;--cv-portrait-y:220px;--cv-inner-left:142px;--cv-inner-right:142px;width:680px;max-width:none;overflow:visible;background:#fff;color:#23372f;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-junction .cv-junction-stage{position:relative;isolation:isolate;width:680px;height:var(--cv-stage-height)}.cv-junction .cv-junction-band{position:absolute;inset:0;z-index:0;width:680px;height:var(--cv-stage-height);margin:0}.cv-junction .cv-junction-inner{position:absolute;z-index:2;top:28px;left:var(--cv-inner-left);right:var(--cv-inner-right);min-height:0;padding:8px}.cv-junction h1{font-size:32px;line-height:1.15;margin:0 0 14px}.cv-junction p{margin:0 0 12px;overflow-wrap:anywhere}.cv-junction .cv-junction-portrait{position:absolute;z-index:3;left:var(--cv-portrait-x);top:var(--cv-portrait-y);transform:translate(-50%,-50%);width:var(--cv-portrait-size);height:var(--cv-portrait-size);margin:0;border:6px solid #fff;border-radius:50%;overflow:hidden;background:#a6b7a1}.cv-junction .cv-junction-portrait svg{width:100%;height:100%;display:block}.cv-junction .cv-junction-outer{padding:12px 28px 28px;min-width:0}.cv-junction h2{font-size:18px;margin:0 0 10px}
```

```html
<article class="cv-junction" aria-label="个人履历"><div class="cv-junction-stage"><figure class="cv-u-band cv-junction-band" aria-hidden="true"><svg class="cv-u-band-svg" viewBox="0 0 680 380"><path class="cv-u-band-path" d="M64 30V220A90 90 0 0 0 154 310H526A90 90 0 0 0 616 220V30"/></svg></figure><header class="cv-junction-inner"><h1>个人履历</h1><p><strong>Alex Chen</strong><br>Product &amp; Editorial Designer</p><p>Building clear, accessible experiences with multidisciplinary teams.</p></header><figure class="cv-junction-portrait" aria-label="弯折交界人物占位"><svg viewBox="0 0 100 100" role="img" aria-label="Portrait placeholder"><circle cx="50" cy="36" r="20" fill="#f2f0df"/><path d="M10 100v-12a40 40 0 0 1 80 0v12" fill="#f2f0df"/></svg></figure></div><section class="cv-junction-outer"><h2>工作经历</h2><p>North Studio · Senior Designer · 2021–2025</p><p>Led interface systems and editorial direction for public-facing services.</p></section></article>
```

适配与边界：
- 必须同时加载shape.u-turn-band的CSS；示例不需要该原子的展示页CSS。
- 默认带内缘x=86/594，正文x=142–538；底带上缘y=288，内文到y=254，保留34px文字安全距离。
- 人像直径108px时左缘10px，保留画布安全区；脸部不得进入自身圆形裁切边缘。带形参数改变后须同步锚点和内外安全区。
- 这是固定680艺术坐标的局部布局，缩略展示整体等比缩放；长文超过带内净空时必须联动增大stage-height、SVG路径和人像锚点后重新渲染，不能隐藏或滚动正文。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。
