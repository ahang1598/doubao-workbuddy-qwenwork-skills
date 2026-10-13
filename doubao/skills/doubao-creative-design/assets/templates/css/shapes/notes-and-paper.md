# 照片衬纸与胶带

状态：已填充。参数为参考图的视觉近似与可调起点，正式输出按既有协议展开节点、样式行内化和 SVG 内嵌。

<a id="shape.paper-mount"></a>

## 照片衬纸与胶带

风格标签：通用。

参考蓝色活动中的照片纸、秋日活动中的照片拼贴和胶带。基础轮廓是矩形，底部衬纸与独立胶带为此组合提供差异。邮票边另选 [齿孔](tickets-and-notches.md#shape.perforated-paper)。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-paper-pad` | `8px` | 衬纸边距 |
| `--vl-paper-footer` | `28px` | 底部留白；说明文字另按正常文流占位 |
| `--vl-tape-width` | `64px` | 胶带宽度 |
| `--vl-tape-height` | `20px` | 胶带高度 |
| `--vl-tape-x` | `50%` | 胶带中心横坐标 |
| `--vl-tape-y` | `0px` | 胶带中心纵坐标 |
| `--vl-tape-angle` | `-8deg` | 胶带自身角度 |
| `--vl-tape-alpha` | `.72` | 只作用于胶带 |
| `--vl-tape-color` | `#e6d2a4` | 胶带颜色 |

```css
.vl-paper-mount { position:relative; margin:0; padding:var(--vl-paper-pad,8px) var(--vl-paper-pad,8px) var(--vl-paper-footer,28px); background:var(--vl-tint,transparent); color:var(--vl-ink,#342c23); }
.vl-paper-mount > img { display:block; width:100%; height:auto; }
.vl-paper-mount__tape { position:absolute; z-index:2; left:var(--vl-tape-x,50%); top:var(--vl-tape-y,0px); width:var(--vl-tape-width,64px); height:var(--vl-tape-height,20px); background:var(--vl-tape-color,#e6d2a4); opacity:var(--vl-tape-alpha,.72); transform:translate(-50%,-50%) rotate(var(--vl-tape-angle,-8deg)); pointer-events:none; }
```

```html
<figure class="vl-paper-mount"><span class="vl-paper-mount__tape" aria-hidden="true"></span><img src="照片素材" alt="照片说明"><figcaption>简短注释</figcaption></figure>
```

衬纸底色由当前 HTML 实现 的表面色显式传入 --vl-tint，并配套文字色；未传时保持透明，不回退米色。需要可见衬纸时须验证其颜色与下层有足够区别，不能因节点存在就判定纸面已呈现。照片、纸边和胶带分别继承各自颜色职责。

不用胶带时删除装饰 span，不新建另一份卡片实现。整体倾斜与层级交给 [拼贴布局](../layouts/overlap-and-collage.md#layout.collage)；图像自带纸边时不重复添加衬纸。本衬纸原子不含夹具；简化夹子与直绳分别见本文件 shape.binder-clip 和织物分类 surface.twisted-cord，真实三维夹具仍使用素材。

<a id="shape.scroll-sheet"></a>

## 卷纸与垂挂公告面

风格标签：通用。

用平面 DOM 表达卷边、主纸面和底部折页，适合规则、公告、菜单说明和长段正文。卷边是结构部件，不是普通卡片顶部加一条胶囊。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-scroll-roll` | `32px` | 顶部卷边高度，建议 22–48px |
| `--vl-scroll-inset` | `28px` | 正文到纸边的安全距离 |
| `--vl-scroll-shadow` | `.2` | 卷边与纸面的接触阴影强度 |
| `--vl-scroll-skew` | `8px` | 底边轻微错位量，不用于正文层 |

```html
<article class="vl-scroll-sheet">
  <span class="vl-scroll-sheet__sheet" aria-hidden="true"></span>
  <span class="vl-scroll-sheet__roll" aria-hidden="true"></span>
  <span class="vl-scroll-sheet__foot" aria-hidden="true"></span>
  <div class="vl-scroll-sheet__content"><h2>公告标题</h2><p>真实正文</p></div>
</article>
```

```css
.vl-scroll-sheet { position:relative; box-sizing:border-box; padding:calc(var(--vl-scroll-roll,32px) + var(--vl-scroll-inset,28px)) var(--vl-scroll-inset,28px) calc(var(--vl-scroll-inset,28px) + 12px); color:var(--vl-ink,#402617); filter:drop-shadow(0 10px 12px color-mix(in srgb,#2b1408 calc(var(--vl-scroll-shadow,.2) * 100%),transparent)); }
.vl-scroll-sheet__sheet { position:absolute; z-index:0; inset:calc(var(--vl-scroll-roll,32px) / 2) 0 0; background:var(--vl-tint,#c9915d); clip-path:polygon(1% 0,99% 0,100% 96%,calc(100% - var(--vl-scroll-skew,8px)) 100%,var(--vl-scroll-skew,8px) 98%,0 100%); }
.vl-scroll-sheet__roll { position:absolute; z-index:2; top:0; left:-2%; width:104%; height:var(--vl-scroll-roll,32px); border-radius:999px; background:linear-gradient(180deg,color-mix(in srgb,var(--vl-tint,#c9915d) 72%,#2b1408) 0%,var(--vl-tint,#c9915d) 38%,color-mix(in srgb,var(--vl-tint,#c9915d) 76%,#fff) 57%,color-mix(in srgb,var(--vl-tint,#c9915d) 70%,#2b1408) 100%); box-shadow:0 5px 7px color-mix(in srgb,#2b1408 calc(var(--vl-scroll-shadow,.2) * 100%),transparent); }
.vl-scroll-sheet__foot { position:absolute; z-index:1; left:8%; right:5%; bottom:-8px; height:18px; background:color-mix(in srgb,var(--vl-tint,#c9915d) 82%,#fff); clip-path:polygon(0 0,100% 20%,98% 100%,4% 78%); opacity:.72; }
.vl-scroll-sheet__content { position:relative; z-index:3; overflow-wrap:anywhere; }
```

卷边和纸面共享同一色系，明暗只解释卷曲厚度。正文保持在独立内容层，不能烘焙进纸面图片；纸纹另选 surface.light-paper。外部投影由根包装承担，避免被纸面 clip-path 裁掉。卷边不得遮住首行，底部折页不得压住末行。

<a id="shape.archival-sheet"></a>

## 不规则档案纸与报纸面

风格标签：通用。

用轻微不规则切角、背页、折痕和分栏线表达报纸、档案页或旧书页；正文仍在平整内容区。它不是把普通圆角卡改成米色。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-archive-inset` | `30px` | 内容安全距离，需避开不规则边 |
| `--vl-archive-fold` | `42%` | 竖向折痕位置 |
| `--vl-archive-rotate` | `-0.8deg` | 整张纸轻微偏转，长正文可设为 0 |
| `--vl-archive-shadow` | `.16` | 背页与纸面的接触阴影强度 |

```html
<article class="vl-archive-sheet">
  <span class="vl-archive-sheet__back" aria-hidden="true"></span>
  <span class="vl-archive-sheet__surface" aria-hidden="true"></span>
  <span class="vl-archive-sheet__fold" aria-hidden="true"></span>
  <div class="vl-archive-sheet__content"><header>档案页眉</header><div>真实分栏正文</div></div>
</article>
```

```css
.vl-archive-sheet { position:relative; box-sizing:border-box; padding:var(--vl-archive-inset,30px); color:var(--vl-ink,#39352c); transform:rotate(var(--vl-archive-rotate,-.8deg)); filter:drop-shadow(0 9px 11px color-mix(in srgb,#2c281f calc(var(--vl-archive-shadow,.16) * 100%),transparent)); }
.vl-archive-sheet__back { position:absolute; z-index:0; inset:9px -7px -8px 8px; background:color-mix(in srgb,var(--vl-tint,#e6e0c8) 78%,#8d8269); clip-path:polygon(1% 2%,98% 0,100% 96%,96% 100%,2% 98%,0 6%); }
.vl-archive-sheet__surface { position:absolute; z-index:1; inset:0; background:var(--vl-tint,#e6e0c8); clip-path:polygon(0 3%,4% 1%,29% 0,61% 1%,96% 0,100% 5%,99% 43%,100% 78%,97% 100%,67% 99%,38% 100%,2% 98%,0 72%,1% 35%); }
.vl-archive-sheet__fold { position:absolute; z-index:2; top:2%; bottom:3%; left:var(--vl-archive-fold,42%); width:16px; transform:translateX(-50%); background:linear-gradient(90deg,transparent 0%,color-mix(in srgb,#6f6754 12%,transparent) 38%,color-mix(in srgb,#fff 22%,transparent) 58%,transparent 100%); pointer-events:none; }
.vl-archive-sheet__content { position:relative; z-index:3; overflow-wrap:anywhere; }
```

需要报纸分栏时由内容层使用真实 Grid／Flex 和分隔线，折痕只作为低对比表面层，不改变文本顺序。纸边的不规则幅度保持克制；大量锯齿、烧焦边、破洞和污渍需要独立素材，不在此原子中伪造。打印或 ATS 场景可关闭旋转、折痕和投影，但保留内容结构。

<a id="shape.stitched-panel"></a>

## 规则缝线边

风格标签：通用。

补齐最早粉色手作图中的布边针脚。采用可调的规则针脚近似，不复制已有经纬纹理。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-stitch-inset` | `8px` | 针脚中心带距外边距离 |
| `--vl-stitch-length` | `10px` | 针脚带宽度 |
| `--vl-stitch-step` | `12px` | 针脚周期 |
| `--vl-stitch-width` | `1.2px` | 线宽，小于 step |
| `--vl-stitch-tilt` | `8deg` | 针脚倾斜 |
| `--vl-stitch-color` | `#977d62` | 线色 |

```css
.vl-stitched { position:relative; padding:calc(var(--vl-stitch-inset,8px) + var(--vl-stitch-length,10px) + 12px); background:var(--vl-tint,#edb9d0); color:var(--vl-ink,#631934); }
.vl-stitch { position:absolute; pointer-events:none; z-index:1; }
.vl-stitch--top,.vl-stitch--bottom { left:var(--vl-stitch-inset,8px); right:var(--vl-stitch-inset,8px); height:var(--vl-stitch-length,10px); background:repeating-linear-gradient(calc(90deg - var(--vl-stitch-tilt,8deg)),transparent 0 calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)),var(--vl-stitch-color,#977d62) calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)) var(--vl-stitch-step,12px)); }
.vl-stitch--top { top:var(--vl-stitch-inset,8px); }.vl-stitch--bottom { bottom:var(--vl-stitch-inset,8px); }
.vl-stitch--left,.vl-stitch--right { top:var(--vl-stitch-inset,8px); bottom:var(--vl-stitch-inset,8px); width:var(--vl-stitch-length,10px); background:repeating-linear-gradient(var(--vl-stitch-tilt,8deg),transparent 0 calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)),var(--vl-stitch-color,#977d62) calc(var(--vl-stitch-step,12px) - var(--vl-stitch-width,1.2px)) var(--vl-stitch-step,12px)); }
.vl-stitch--left { left:var(--vl-stitch-inset,8px); }.vl-stitch--right { right:var(--vl-stitch-inset,8px); }
```

```html
<section class="vl-stitched"><span class="vl-stitch vl-stitch--top" aria-hidden="true"></span><span class="vl-stitch vl-stitch--bottom" aria-hidden="true"></span><span class="vl-stitch vl-stitch--left" aria-hidden="true"></span><span class="vl-stitch vl-stitch--right" aria-hidden="true"></span><p>布面内容</p></section>
```

经纬布纹另读 surface.woven-grid，纸纤维另读 surface.light-paper；缝线只负责边缘。针脚的真实随机长短和毛边不由此规则图案产生，若继承要求强调不规则手缝，应修改专用 SVG 或保留纹理素材。

<a id="shape.binder-clip"></a>

## 简化夹子

风格标签：通用。

补齐蓝色活动图里夹在纸片上的象牙白／粉色夹子。用一份带孔 SVG 轮廓与可变渐变填面做二维近似。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-clip-width` | `48px` | 夹子宽度，高度按 SVG 的 72:80 比例 |
| `--vl-clip-shadow` | `.18` | 投影强度；只是接触提示 |

```css
.vl-binder-clip { display:inline-block; position:relative; width:var(--vl-clip-width,48px); aspect-ratio:72 / 80; transform:rotate(var(--vl-rotate,0deg)); filter:drop-shadow(0 2px 2px color-mix(in srgb,#243345 calc(var(--vl-clip-shadow,.18) * 100%),transparent)); }
.vl-binder-clip__body { position:absolute; inset:0; background-image:var(--vl-paint,linear-gradient(110deg,#fffdf1 0%,#e4e0ce 45%,#cacbbf 70%,#fff9df 100%)); mask-image:url("asset:svg/binder-clip.svg"); mask-size:100% 100%; mask-repeat:no-repeat; }
```

```html
<span class="vl-binder-clip vl-gradient--linear" style="--vl-gradient-stops:#ffe1ed 0%,#e88ab8 50%,#ffbcdb 100%" aria-hidden="true"><span class="vl-binder-clip__body"></span></span>
```

填面复用 [通用渐变](../colors/palettes.md#color.gradient)，位置由纸片／拼贴实例决定。需要改孔径和肩部轮廓时按需改 binder-clip.svg；这些不属于外层 CSS 参数。此近似没有真实弹簧、夹口结构与摄影反射，要求严格同款时继续使用素材。

<a id="shape.envelope-flaps"></a>

## 信封左右折片与前封片

风格标签：通用。

形状原子：三块独立几何面，左右折片在后，三角前封片在前。它不规定信纸高度与正文位置；组合调用[信纸插入布局](../layouts/overlap-and-collage.md#layout.letter-in-envelope)。

四个fold/front颜色变量控制各面明暗，不默认纸纹或外投影。容器宽高比建议2.5–4.0；尖点与交界以百分比定义。此为参考的简化几何，不是可印刷信封展开刀模，不含背面、胶舌或真实折纸厚度。

```css
.vl-envelope-flaps { position:relative; width:100%; height:100%; min-height:80px; }
.vl-envelope-flaps__left,.vl-envelope-flaps__right,.vl-envelope-flaps__front { position:absolute; inset:0; }
.vl-envelope-flaps__left { clip-path:polygon(0 0,61% 70%,0 100%); background:linear-gradient(135deg,var(--vl-fold-light,#98bd78),var(--vl-fold-dark,#507f3e)); }
.vl-envelope-flaps__right { clip-path:polygon(100% 0,39% 70%,100% 100%); background:linear-gradient(225deg,var(--vl-fold-light,#98bd78),var(--vl-fold-dark,#507f3e)); }
.vl-envelope-flaps__front { clip-path:polygon(0 100%,50% 35%,100% 100%); background:linear-gradient(180deg,var(--vl-front-light,#91b96d),var(--vl-front-dark,#6b9849)); }
```

```html
<div class="vl-envelope-flaps" aria-hidden="true"><span class="vl-envelope-flaps__left"></span><span class="vl-envelope-flaps__right"></span><span class="vl-envelope-flaps__front"></span></div>
```
