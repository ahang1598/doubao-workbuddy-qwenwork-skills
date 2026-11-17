# 弥散光晕

状态：已实现。

参考：图 3 的玫粉光晕与图 6 的暖金柔光。共享径向光场，仅改变颜色、位置、范围和强度。

<a id="surface.diffuse-field"></a>

## 弥散光晕原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-glow-color` | `var(--vl-accent,#e7a4bd)` | 光色；通常读取强调色 |
| `--vl-glow-opacity` | `.22` | 0–.5；推荐先从 .12–.22 开始 |
| `--vl-glow-x` | `25%` | 光心横坐标 |
| `--vl-glow-y` | `20%` | 光心纵坐标 |
| `--vl-glow-width` | `75%` | 径向椭圆横向半径，40%–120% |
| `--vl-glow-height` | `55%` | 径向椭圆纵向半径 |
| `--vl-glow-core` | `0%` | 中心实色范围，0%–20% |

```css
.vl-light-field { position:relative; isolation:isolate; }
.vl-light-field__glow { position:absolute; inset:0; z-index:-1; pointer-events:none; border-radius:inherit; opacity:var(--vl-glow-opacity,.22); background:radial-gradient(ellipse var(--vl-glow-width,75%) var(--vl-glow-height,55%) at var(--vl-glow-x,25%) var(--vl-glow-y,20%),var(--vl-glow-color,var(--vl-accent,#e7a4bd)) var(--vl-glow-core,0%),transparent 100%); }
```

```html
<section class="vl-light-field" style="background:var(--vl-tint)"><span class="vl-light-field__glow" aria-hidden="true"></span><h2>内容保持清晰</h2></section>
```

玫粉：color=#e7a4bd、opacity=.32、x=20%、y=24%。暖金：color=#d8a344、opacity=.18、x=65%、y=35%、width=90%。这两个覆盖共用本段代码，不登记为两个独立材质。光场不模糊正文；图 6 的花影和真实景深仍由图片提供。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="surface.neon-edge"></a>

## 霓虹亮边与文字发光

风格标签：通用。

参考演唱会战报的青色框线与女性电影的粉色标题。背景弥散光继续复用 surface.diffuse-field；轮廓发光是独立分支。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-neon-color` | `var(--vl-accent,#00d8df)` | 发光颜色 |
| `--vl-neon-alpha` | `.65` | 发光强度，不影响正文整体透明度 |
| `--vl-neon-blur` | `16px` | 外部光晕半径 |
| `--vl-neon-width` | `1px` | 框线宽度 |
| `--vl-neon-inset` | `4px` | 框内光晕半径；设 0 关闭内光扩散 |

```css
.vl-neon-edge { outline:var(--vl-neon-width,1px) solid var(--vl-neon-color,var(--vl-accent,#00d8df)); outline-offset:0; box-shadow:0 0 var(--vl-neon-blur,16px) color-mix(in srgb,var(--vl-neon-color,var(--vl-accent,#00d8df)) calc(var(--vl-neon-alpha,.65) * 100%),transparent),inset 0 0 var(--vl-neon-inset,4px) color-mix(in srgb,var(--vl-neon-color,var(--vl-accent,#00d8df)) calc(var(--vl-neon-alpha,.65) * 100%),transparent); }
.vl-neon-type { text-shadow:0 0 var(--vl-neon-blur,16px) color-mix(in srgb,var(--vl-neon-color,var(--vl-accent,#00d8df)) calc(var(--vl-neon-alpha,.65) * 100%),transparent); }
```

```html
<section class="vl-neon-edge" style="border-radius:18px;padding:24px"><h2 class="vl-neon-type">舞台标题</h2><p>正文不默认发光</p></section>
```

轮廓由所选形状提供；outline 和 box-shadow 不适合直接加在会裁剪自身的 mask 节点，应放到外包装。边框、背景光与标题发光按对象单独启用；不是选了霓虹配色就给所有节点加光。

## 共用光场的新增覆盖

演唱会背景复用 [弥散光场](#surface.diffuse-field)：`--vl-glow-color:#04d3dc;--vl-glow-opacity:.34;--vl-glow-x:15%;--vl-glow-y:20%`。需要另一团蓝光时添加第二个光层节点并局部覆盖 color=#317bbc、x=85%、y=75%，不要复制光场 CSS。

金色猫粮场景使用同一光场的暖金覆盖。真实油滴、丝绸反射、立体营养金字塔与成分结构保留为图像；玻璃说明卡沿用原玻璃材质，不能把所有金色摄影归为金属 CSS。


<a id="surface.image-fade"></a>

## 图片边缘透明衔接

风格标签：通用。

图片确有可退场的安全空场时，才用 Alpha 显露下方背景；与 color.gradient 的覆盖色场分开。默认保留整图，蒙版只放图片节点，不放包含文字的 section。无安全空场时调整素材或保留明确边界。

| 参数 | 默认值 | 作用 |
|---|---|---|
| `--vl-fade-angle` | `180deg` | 180deg 向下淡出；0deg 向上；90deg 向右 |
| `--vl-fade-stops` | `#000 0%,#000 100%` | 默认全程不透明；根据最终裁切后的安全空场显式设置色标，位置非递减 |

```css
.vl-image-fade { mask-image:linear-gradient(var(--vl-fade-angle,180deg),var(--vl-fade-stops,#000 0%,#000 100%)); mask-mode:alpha; mask-repeat:no-repeat; mask-size:100% 100%; }
```

以下仅演示已核验底部 20% 为低细节安全空场、且下方存在可衔接背景的局部退场；主体、接触点、材质证据和图内文字均在退场区之外。不满足条件时不配置退场色标，保留全不透明默认或明确图窗边界。

```html
<figure style="margin:0;background:var(--vl-tint)">
 <img class="vl-image-fade" src="场景素材" alt="场景说明" style="display:block;width:100%;height:auto;--vl-fade-angle:180deg;--vl-fade-stops:#000 0%,#000 80%,rgb(0 0 0 / .65) 91%,transparent 100%">
</figure>
```

三种渐变分别绑定：章节色场用 color.gradient；局部亮区用 surface.diffuse-field；图片退场用本蒙版。例：底部 20% 柔退，stops=`#000 0%,#000 80%,rgb(0 0 0 / .65) 91%,transparent 100%`。两端退场可设 `transparent 0%,#000 16%,#000 80%,transparent 100%`，仅在两端均有安全空场时使用。

淡出区域避开产品包装、脸、图内文字、食品主体和图表。先检查最终裁切图，再决定起止与缓变距离；示例百分比不是默认裁切范围，也不能为套用示例而擦掉主体。容器衔接底色按 [双侧取色与合成](../../../../references/workflow/html-assembly.md#素材就绪后的合成与几何复核) 确定，覆盖上下实际边缘的 A→B 色场，不用统一 tint 代替两侧取色；同色硬切是有效选项，不为每个接缝强加渐变。复杂林地不能仅靠平均绿色拼接，需延续真实场景或明确换章。蒙版占用图片自身 mask 槽位；已做撕边等轮廓遮罩时分层包装，不覆盖原 mask。正文保持 opacity=1，文字不随图片淡出。

<a id="surface.soft-focus-mist"></a>

## 局部柔焦与薄雾

风格标签：通用。

复用 [弥散光晕](diffuse-light.md#surface.diffuse-field) 和 [图片透明衔接](diffuse-light.md#surface.image-fade)，本段只补独立图层失焦与薄雾遮罩。柔焦不是风格名称，也不是把全页 blur；必须明确被模糊的对象、清晰主体和文字保护区。适合花枝前景、无关远景与空气感装饰，真实镜头景深、高光溢出和运动拖影仍由素材承担。

| 参数 | 起点／范围（1080px画幅） | 作用 |
|---|---|---|
| `--vl-soft-blur` | 默认0px；选中装饰层后先试8–20px，前景可试20–36px | 仅对该图像层执行blur，主体／正文默认不模糊 |
| `--vl-soft-opacity` | 1；装饰可试.55–.85 | 只控制装饰层，不施加到section |
| `--vl-soft-inset` | 默认0；全幅背景可外扩-24px至-72px | 预留模糊采样边缘，约为blur的2–3倍；需要按主体和实际裁切确认 |
| `--vl-mist-opacity` | 默认0；选中雾层时.08–.22 | 雾层独立强度，不与文字绑定 |
| `--vl-mist-paint` | 默认none | 明确雾色、方向和逐色标透明度；不自带黑色遮光 |
| `--vl-mist-inset` | 默认0 | 雾层区域；避开产品标识和关键细节 |

```css
.vl-soft-scene { position:relative; isolation:isolate; overflow:hidden; }
.vl-soft-scene__decor { position:absolute; inset:var(--vl-soft-inset,0); z-index:0; pointer-events:none; opacity:var(--vl-soft-opacity,1); filter:blur(var(--vl-soft-blur,0px)); }
.vl-soft-scene__decor > img { display:block; width:100%; height:100%; object-fit:cover; }
.vl-soft-scene__mist { position:absolute; inset:var(--vl-mist-inset,0); z-index:1; pointer-events:none; opacity:var(--vl-mist-opacity,0); background:var(--vl-mist-paint,none); }
.vl-soft-scene__subject { position:relative; z-index:2; }
.vl-soft-scene__content { position:relative; z-index:3; }
```

```html
<section class="vl-soft-scene" style="background:#f2eddb;--vl-soft-blur:12px;--vl-soft-inset:-36px;--vl-mist-opacity:.16;--vl-mist-paint:linear-gradient(90deg,rgb(249 245 228 / .85) 0%,rgb(249 245 228 / .3) 45%,rgb(249 245 228 / 0) 75%)">
 <div class="vl-soft-scene__decor"><img src="独立花影素材" alt=""></div>
 <div class="vl-soft-scene__mist" aria-hidden="true"></div>
 <div class="vl-soft-scene__subject">独立清晰产品或主体图</div>
 <div class="vl-soft-scene__content">保持清晰的标题与正文</div>
</section>
```

主体与content是正常文档流，决定容器高度；正式组装按 Brief 的可见关系在 HTML 确定实际尺寸及位置，不能把样例占位文字直接交付。背景／装饰→雾层→清晰主体→文字为默认顺序；只有确有参考依据才在主体上叠低强度前景雾，并避开标识。图像本身已有柔焦时优先关闭CSS blur，避免二次糊化。图片遮罩放在独立包装层，避免覆盖既有轮廓mask。

色标alpha与雾层opacity相乘，如 .85×.16≈.136，不把两者误当同一强度；参数需按最终尺寸等比调整。检查边缘透明漏底、主体误模糊、文字对比和前后景是否分明。均匀高斯blur不等于横向拖影；不使用复制叠影伪装精确摄影效果。

<a id="surface.fine-grain-mist"></a>

## 细颗粒柔雾色场

风格标签：通用。

基底：[弥散色场](diffuse-light.md#surface.diffuse-field)，同时复用 [屏幕颗粒分层原则](paper-and-print.md#surface.screen-grain)。这是可直接套用的灰度细颗粒参数变体，不是新的玻璃材质。色场模糊、微颗粒和正文三个独立层。

色场起点为薄荷／青／奶白大色带，不能仅铺单一线性渐变。--mist-softness 建议16–48px；装饰层向外扩8%防模糊黑边。--mist-grain建议.15–.4，频率.8建议.6–1.2；没有尖锐凸凹高光。只适用于卡片／背景，字体质感另选text.paint且保护细字。每个实例使用唯一的mist-grain-a。

```css
.vl-grain-mist {position:relative;isolation:isolate;overflow:hidden;background:#edf1e8;}
.vl-grain-mist__field {position:absolute;inset:-8%;background:var(--mist-field,radial-gradient(ellipse at 78% 8%,#86b9bc 0%,transparent 45%),radial-gradient(ellipse at 14% 85%,#b1d6c6 0%,transparent 56%),linear-gradient(160deg,#e7eade 10%,#a9c9c7 38%,#f2f1e4 52%,#9dc7d4 67%,#d9e7d9 90%));filter:blur(var(--mist-softness,24px));}
.vl-grain-mist__grain {position:absolute;inset:0;width:100%;height:100%;mix-blend-mode:soft-light;opacity:var(--mist-grain,.3);pointer-events:none;}
.vl-grain-mist__copy {position:relative;z-index:1;padding:32px;color:#274747;}
```

```html
<div class="vl-grain-mist" style="min-height:300px">
 <div class="vl-grain-mist__field" aria-hidden="true"></div>
 <svg class="vl-grain-mist__grain" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><defs><filter id="mist-grain-a" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="1" seed="41"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncR type="linear" slope="2.5" intercept="-.75"/><feFuncG type="linear" slope="2.5" intercept="-.75"/><feFuncB type="linear" slope="2.5" intercept="-.75"/></feComponentTransfer></filter></defs><rect width="100%" height="100%" filter="url(#mist-grain-a)"/></svg>
 <div class="vl-grain-mist__copy">柔雾色场上的清晰内容</div>
</div>
```
参考的非规则云带这里只作可编辑近似；按版面改色标、径向中心和blur，不调根节点opacity。将同一机制用于背景和卡片只记录两个适用对象。

灰度通道经2.5倍对比扩展后由外层opacity压低，避免细颗粒在浅底完全消失；只作用于纹理，不改变正文颜色。

<a id="surface.type-channel-offset"></a>

## 真实字形轻通道错位

风格标签：通用。

主文本是唯一可访问和可选择的语义文本，两份复制必须与主文本完全一致且aria-hidden=true。复制层绝对定位、不参与尺寸，真实字形保留在上层，不用text-shadow伪造笔画。--ct-offset-x默认1px，y默认0px，两轴硬限制±2px，推荐仅水平1px；cyan、violet独立调色。--ct-offset-enabled:0关闭两份复制，主文本不受影响。适用于短标题，不推荐整段正文；长题时主副本共享字体、宽度与换行规则，外部字体加载后需重新检查同文换行。无动画、无裁断笔画。

分类说明：真实字形的平移彩边，不改变主字骨。

```css
.ct-offset{position:relative;isolation:isolate;display:inline-grid;max-width:100%;vertical-align:baseline;overflow-wrap:anywhere;}.ct-offset__main{position:relative;grid-area:1/1;z-index:1;min-width:0;color:var(--ct-offset-main-color,inherit);}.ct-offset__copy{position:absolute;inset:0;z-index:0;pointer-events:none;user-select:none;font:inherit;letter-spacing:inherit;line-height:inherit;text-align:inherit;white-space:inherit;overflow-wrap:inherit;word-break:inherit;opacity:var(--ct-offset-enabled,1);color:var(--ct-offset-cyan,rgba(92,213,244,.65));transform:translate(clamp(-2px,var(--ct-offset-x,1px),2px),clamp(-2px,var(--ct-offset-y,0px),2px));}.ct-offset__copy--violet{color:var(--ct-offset-violet,rgba(197,115,221,.5));transform:translate(calc(0px - clamp(-2px,var(--ct-offset-x,1px),2px)),calc(0px - clamp(-2px,var(--ct-offset-y,0px),2px)));}
```

```html
<div style="padding:16px;background:#18232c;color:#fff;font-size:30px;font-weight:700"><span class="ct-offset"><span class="ct-offset__main">终端标题</span><span class="ct-offset__copy" aria-hidden="true">终端标题</span><span class="ct-offset__copy ct-offset__copy--violet" aria-hidden="true">终端标题</span></span></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。
