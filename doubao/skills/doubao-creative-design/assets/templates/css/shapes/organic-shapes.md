# 拱顶与星芒轮廓

状态：近似实现。数值为可调起点，不是参考图原始源参数。

<a id="shape.arch-panel"></a>

## 拱顶章节面板

风格标签：通用。

补齐糕点详情页章节之间的宽拱形边界。它是背景分区轮廓，和用于裁照片的 arch-window 分开。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-panel-rise` | `60px` | 顶端椭圆圆角纵向半径 |
| `--vl-panel-safe` | `24px` | 拱顶下方额外内容留白 |

```css
.vl-arch-panel { border-radius:50% 50% 0 0 / var(--vl-panel-rise,60px) var(--vl-panel-rise,60px) 0 0; padding:calc(var(--vl-panel-rise,60px) + var(--vl-panel-safe,24px)) var(--vl-padding,24px) var(--vl-padding,24px); background:var(--vl-tint,#ffe7bf); color:var(--vl-ink,#5b301c); }
```

```html
<section class="vl-arch-panel"><h2>传统美味</h2><p>章节内容</p></section>
```

适用于横向较宽的章节。高度很小时浏览器会缩小圆角，正文区需保留足够高度；此参数不是照片拱窗的裁切比例。

<a id="shape.sparkle"></a>

## 四角星芒

风格标签：通用。

对应圆形徽章旁的细星光、演唱会标题旁的亮色星芒。使用真实装饰节点，不占用其他材质的伪元素。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-star-size` | `24px` | 星芒宽高 |
| `--vl-star-inset` | `42%` | 腰部内收位置；建议 35%–48%，越大越纤细 |

```css
.vl-sparkle { display:inline-block; flex:none; width:var(--vl-star-size,24px); aspect-ratio:1; background:var(--vl-paint,var(--vl-accent,#edff79)); clip-path:polygon(50% 0,var(--vl-star-inset,42%) var(--vl-star-inset,42%),0 50%,var(--vl-star-inset,42%) calc(100% - var(--vl-star-inset,42%)),50% 100%,calc(100% - var(--vl-star-inset,42%)) calc(100% - var(--vl-star-inset,42%)),100% 50%,calc(100% - var(--vl-star-inset,42%)) var(--vl-star-inset,42%)); transform:rotate(var(--vl-rotate,0deg)); }
```

```html
<span class="vl-sparkle" aria-hidden="true" style="--vl-star-size:20px;--vl-star-inset:45%;--vl-accent:#b7eeff"></span>
```

可复用 color.gradient 的 `--vl-paint` 填充和 `--vl-rotate` 旋转。需要外发光时放在单独的 filter:drop-shadow 容器中，避免星芒自身的 clip-path 裁去外光。此形状为四角星，不等同于随机手绘星或多射线爆炸标。

<a id="shape.sweeping-band"></a>

## 非对称宽幅曲带

风格标签：通用。

形状原子，作用于背景分区。现有arch-panel只有对称拱顶，不能表达两条非平行连续曲边。

band-height默认420px，band-paint控制颜色，mask随目标盒拉伸；建议宽高比1.4–3.0，超出应调整曲线。它不承载文字节点；布局另设文字安全区，不能把矩形盒全域当曲带内可读区域。相同轮廓可叠第二层作淡色背带，位移保存在组合内。

```css
.vl-sweeping-band { width:100%; height:var(--vl-band-height,420px); background:var(--vl-band-paint,#fff); mask-image:url("asset:svg/invite-wave-mask.svg"); mask-size:100% 100%; mask-repeat:no-repeat; pointer-events:none; }
```

```html
<div class="vl-sweeping-band" aria-hidden="true"></div>
```

<a id="shape.ceremony-edge"></a>

## 多弧礼仪压边

风格标签：通用。

形状原子，属于标题色面压住下方纸面的边界。多个浅圆弧与中央下探共同构成，不等于普通圆角卡或拱形图窗。

cap-height默认200px；edge-width默认5px，通过两个同形mask的纵向偏移显示金边，不是等距法线描边。中央徽章由组合另放，不能把顶部整个矩形区域算作纸面正文区。mask比例建议2.3–4.2，极端比例需重新核对圆弧。

```css
.vl-ceremony-edge { position:relative; width:100%; height:var(--vl-cap-height,200px); }
.vl-ceremony-edge__rim,.vl-ceremony-edge__face { position:absolute; inset:0; mask:url("asset:svg/invite-ceremony-mask.svg") 0 0/100% 100% no-repeat; }
.vl-ceremony-edge__rim { background:var(--vl-cap-rim,#e6c77d); transform:translateY(var(--vl-cap-edge,5px)); }
.vl-ceremony-edge__face { background:var(--vl-cap-color,#a30e15); }
```

```html
<div class="vl-ceremony-edge" aria-hidden="true"><span class="vl-ceremony-edge__rim"></span><span class="vl-ceremony-edge__face"></span></div>
```

<a id="shape.u-turn-band"></a>

## 可参数化U/J形回转粗带

风格标签：通用。

SVG开放路径由两段竖线、两个四分之一圆弧与底部水平段构成，stroke生成粗带。R控制拐弯半径，O控制两竖段中心线间距；缩短右竖段得到J形，不使用横向扫带。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-band-width` | {"default": "44px", "unit": "SVG user unit", "range": "20–64"} |
| `--cv-band-color` | {"default": "#8d9e55", "unit": "color", "range": "任意装饰色"} |
| `R` | {"default": 90, "unit": "SVG user unit", "range": "60–130；须满足2R≤O且R>带宽/2"} |
| `O` | {"default": 552, "unit": "SVG user unit", "range": "360–552；内净开口=O-带宽"} |
| `X` | {"default": 64, "unit": "SVG user unit", "range": "至少带宽/2+10"} |
| `B` | {"default": 310, "unit": "SVG user unit", "range": "280–330；B+带宽/2≤370"} |
| `T_left` | {"default": 30, "unit": "SVG user unit", "range": "至少带宽/2"} |
| `T_right` | {"default": 30, "unit": "SVG user unit", "range": "U形同T_left；J形可设B-R"} |
| `--cv-band-cap` | {"default": "butt", "unit": "enum", "range": ["butt", "round"]} |

```css
.cv-u-band,.cv-u-band *{box-sizing:border-box}.cv-u-band{--cv-band-width:44px;--cv-band-color:#8d9e55;--cv-band-cap:butt;display:block;width:min(100%,680px);margin:0;aspect-ratio:680/380}.cv-u-band .cv-u-band-svg{display:block;width:100%;height:100%;overflow:hidden}.cv-u-band .cv-u-band-path{fill:none;stroke:var(--cv-band-color);stroke-width:var(--cv-band-width);stroke-linecap:var(--cv-band-cap);stroke-linejoin:round}.cv-u-demo,.cv-u-demo *{box-sizing:border-box}.cv-u-demo{width:min(100%,680px);background:#faf9f3;color:#2d3e30;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-u-demo .cv-u-demo-copy{padding:24px 28px}.cv-u-demo h2{font-size:22px;margin:0 0 10px}.cv-u-demo p{margin:0}
```

```html
<section class="cv-u-demo"><header class="cv-u-demo-copy"><h2>回转造型</h2><p>Alex Chen · Product Designer<br>Selected experience, 2021–2025</p></header><figure class="cv-u-band" aria-label="U形回转装饰"><svg class="cv-u-band-svg" viewBox="0 0 680 380" role="img" aria-label="U-shaped band"><path class="cv-u-band-path" d="M64 30V220A90 90 0 0 0 154 310H526A90 90 0 0 0 616 220V30"/></svg></figure></section>
```

适配与边界：
- 构建时用真实公式生成d：M X T_left V(B-R) A R R 0 0 0 (X+R) B H(X+O-R) A R R 0 0 0 (X+O) (B-R) V T_right；R/O/X/B/T不是CSS变量，不会仅改内联style就自动改变路径。
- 默认可直接使用；J形示例只需把末尾V30改为V220。所有几何变量调整后应重新写入d属性。
- 圆头额外向端点外延半个带宽；外侧至少留10单位，内侧文字距描边边缘建议24单位。
- SVG按比例缩放，stroke随坐标缩放；此原子不定位人像、不承担正文背景。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="shape.radial-sticker"></a>

## 三预设放射贴纸

风格标签：通用。

单一原子提供8臂星号、8圆瓣、12尖角三套真实SVG轮廓；星号用四条穿心粗线形成八个端臂，圆瓣用中心圆和八个重叠圆联合，尖角用24顶点交替半径多边形。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `data-preset` | {"default": "asterisk", "unit": "enum", "range": ["asterisk", "petal", "spike"]} |
| `--cv-sticker-size` | {"default": "128px", "unit": "px", "range": "64–180"} |
| `--cv-sticker-color` | {"default": "#bd573a", "unit": "color", "range": "任意装饰色"} |
| `--cv-sticker-rotate` | {"default": "0deg", "unit": "deg", "range": "-180–180"} |
| `--cv-arm-width` | {"default": "14px", "unit": "SVG user unit", "range": "10–18"} |

```css
.cv-radial,.cv-radial *{box-sizing:border-box}.cv-radial{--cv-sticker-size:128px;--cv-sticker-color:#bd573a;--cv-sticker-rotate:0deg;--cv-arm-width:14px;display:block;width:var(--cv-sticker-size);max-width:100%;aspect-ratio:1;color:var(--cv-sticker-color);transform:rotate(var(--cv-sticker-rotate));overflow:visible}.cv-radial .cv-radial-asterisk,.cv-radial .cv-radial-petal,.cv-radial .cv-radial-spike{display:none}.cv-radial[data-preset=asterisk] .cv-radial-asterisk{display:block;fill:none;stroke:currentColor;stroke-width:var(--cv-arm-width);stroke-linecap:butt}.cv-radial[data-preset=petal] .cv-radial-petal{display:block;fill:currentColor}.cv-radial[data-preset=spike] .cv-radial-spike{display:block;fill:currentColor}.cv-radial-demo,.cv-radial-demo *{box-sizing:border-box}.cv-radial-demo{width:min(100%,680px);padding:28px;background:#f7f2e7;color:#343b30;font:14px/1.6 Arial,'PingFang SC',sans-serif}.cv-radial-demo h2{margin:0 0 10px;font-size:22px}.cv-radial-demo p{margin:0 0 22px}.cv-radial-demo .cv-radial-list{display:flex;flex-wrap:wrap;gap:28px;padding:16px}.cv-radial-demo figure{margin:0}.cv-radial-demo figcaption{text-align:center;margin-top:14px}
```

```html
<section class="cv-radial-demo"><h2>放射造型</h2><p>Alex Chen · Visual Designer<br>Editorial experiments, 2021–2025</p><div class="cv-radial-list"><figure><svg class="cv-radial" data-preset="asterisk" viewBox="0 0 100 100" role="img" aria-label="八臂星号"><g class="cv-radial-asterisk"><path d="M50 6V94M6 50H94M19 19L81 81M19 81L81 19"/></g><g class="cv-radial-petal"><circle cx="50" cy="50" r="29"/><circle cx="50" cy="20" r="17"/><circle cx="71.2" cy="28.8" r="17"/><circle cx="80" cy="50" r="17"/><circle cx="71.2" cy="71.2" r="17"/><circle cx="50" cy="80" r="17"/><circle cx="28.8" cy="71.2" r="17"/><circle cx="20" cy="50" r="17"/><circle cx="28.8" cy="28.8" r="17"/></g><polygon class="cv-radial-spike" points="50,3 57.8,21 73.5,9.3 71.2,28.8 90.7,26.5 79,42.2 97,50 79,57.8 90.7,73.5 71.2,71.2 73.5,90.7 57.8,79 50,97 42.2,79 26.5,90.7 28.8,71.2 9.3,73.5 21,57.8 3,50 21,42.2 9.3,26.5 28.8,28.8 26.5,9.3 42.2,21"/></svg><figcaption>八臂星号</figcaption></figure><figure><svg class="cv-radial" data-preset="petal" viewBox="0 0 100 100" role="img" aria-label="八圆瓣"><g class="cv-radial-petal"><circle cx="50" cy="50" r="29"/><circle cx="50" cy="20" r="17"/><circle cx="71.2" cy="28.8" r="17"/><circle cx="80" cy="50" r="17"/><circle cx="71.2" cy="71.2" r="17"/><circle cx="50" cy="80" r="17"/><circle cx="28.8" cy="71.2" r="17"/><circle cx="20" cy="50" r="17"/><circle cx="28.8" cy="28.8" r="17"/></g></svg><figcaption>圆瓣</figcaption></figure><figure><svg class="cv-radial" data-preset="spike" viewBox="0 0 100 100" role="img" aria-label="十二尖角"><polygon class="cv-radial-spike" points="50,3 57.8,21 73.5,9.3 71.2,28.8 90.7,26.5 79,42.2 97,50 79,57.8 90.7,73.5 71.2,71.2 73.5,90.7 57.8,79 50,97 42.2,79 26.5,90.7 28.8,71.2 9.3,73.5 21,57.8 3,50 21,42.2 9.3,26.5 28.8,28.8 26.5,9.3 42.2,21"/></svg><figcaption>尖角</figcaption></figure></div></section>
```

适配与边界：
- 首个SVG包含三种轮廓，可直接切换data-preset；后两个为精简预设实例，切换前需补齐对应几何组。
- 八臂星号由八个粗矩形端臂构成，不是四角星；圆瓣和尖角的轮廓算法不同。
- 装饰默认不压正文；若叠字，只在中央半径18单位内放极短标签，并重新检验对比度。
- 旋转后外接框可能扩大，周围预留至少16px；贴纸不应遮盖人物面部或主要标题。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。
