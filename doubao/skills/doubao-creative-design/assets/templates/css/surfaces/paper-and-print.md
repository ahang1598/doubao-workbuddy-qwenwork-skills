# 纸张印刷

状态：已填充复用预设。

参考：图 7 的浅绿信笺；图 1 的纸色信息区可选择同一轻纸纹。复用现有 [纸纤维实现](materials.md#material.paper) 和共用表面结构，不再新增一份噪点 SVG。颜色读取所选 palette。

<a id="surface.light-paper"></a>

## 轻纸纹覆盖

风格标签：通用。

```json
{
  "id": "surface.light-paper",
  "base": "material.paper",
  "overrides": {
    "--vl-grain": ".12",
    "--vl-texture-size": "256px",
    "--vl-texture-blend": "multiply",
    "--vl-alpha": "1",
    "--vl-highlight": ".08",
    "--vl-shadow": "0"
  }
}
```

grain 建议 .06–.2；texture-size 建议 192–384px；照片不额外覆盖纸纹。以上为视觉近似起点，不代表图片原始参数。

用于既有 rounded-paper 时直接应用覆盖；用于整页纸底时使用 [共用纹理层](materials.md#surfaces.texture-field)，设置 `--vl-texture:url("asset:svg/paper-fiber.svg")`；无需文件夹 mask、页签、背页和阴影。保持 texture 绝对定位且不拦截交互，正文在其上；不要整页加 opacity。图中的旧印章、字体和照片颗粒不是该纸纹自动产生的效果。

<a id="surface.screen-grain"></a>

## 彩色屏幕颗粒

风格标签：通用。

参考演唱会战报的蓝青杂色颗粒。它保留噪声 RGB 通道，与纸纤维不同；复用 [共用纹理层](materials.md#surfaces.texture-field)，只切换资源与参数。

```json
{
  "id": "surface.screen-grain",
  "implementation": "surfaces.texture-field",
  "overrides": {
    "--vl-texture": "url('asset:svg/screen-grain.svg')",
    "--vl-grain": ".16",
    "--vl-texture-size": "192px",
    "--vl-texture-blend": "soft-light"
  }
}
```

grain 推荐 .06–.22；深浅底效果不同，按最终尺度验证。频率 .72、seed=29、octaves=1 保存在 screen-grain.svg；只有改变颗粒生成方式时才读取修改。霓虹光圈另选光晕原子，不能用增加噪点替代发光。

<a id="surface.dot-pattern"></a>

## 网点与点阵字

风格标签：通用。

参考演唱会战报的大字点阵。相同径向点阵可应用于装饰色块或文字裁切；字形仍由真实字体决定。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-dot-step` | `5px` | 点阵间距，建议 3–8px |
| `--vl-dot-radius` | `1.4px` | 点半径，应小于 step/2 |
| `--vl-dot-color` | `#e5ffff` | 点色 |
| `--vl-dot-alpha` | `1` | 点色透明度；背景印刷通常 .08–.25，点阵字通常 1 |

```css
.vl-dot-pattern { background-image:radial-gradient(circle,color-mix(in srgb,var(--vl-dot-color,#e5ffff) calc(var(--vl-dot-alpha,1) * 100%),transparent) var(--vl-dot-radius,1.4px),transparent calc(var(--vl-dot-radius,1.4px) + .3px)); background-size:var(--vl-dot-step,5px) var(--vl-dot-step,5px); }
.vl-dot-pattern--text { color:transparent; background-clip:text; }
```

```html
<h2 class="vl-dot-pattern vl-dot-pattern--text" style="font-size:96px;font-weight:900;--vl-dot-step:4px;--vl-dot-radius:1.4px">演出</h2>
```

点阵字只用于大字，正文不使用；最终字号小于约 48px 时优先保留完整字形。实体字的光晕由独立文字发光层或素材提供，不用阴影把点阵孔隙填平。背景网点放独立装饰层以免影响正文清晰度。

<a id="surface.riso-overprint"></a>

## 套色网印与错版颗粒

风格标签：通用。

基底：[规则网点](paper-and-print.md#surface.dot-pattern)。增加双角度网点、独立墨色与轻微错版，区别于均匀噪点。适用卡片、背景；字体不会自动继承，点阵大字单独引用基底。纸张照片与原图 RISO 字样不作为纹理。

| 参数 | 起点／范围 |
|---|---|
| 墨层 opacity | .78；.3–.85，正文密集处取低值 |
| SVG 网点间距 | 6 / 6.5 视图单位；约4–9 |
| 两版角度 | 23° / -17°，有意形成套色交叠 |
| 错版／粗糙位移 | 2,-1 / 2.2 视图单位；0–3 |
| 墨色 | 黄蓝；红蓝变体将 yellow 改为 #d65b45 |

SVG 使用600×400自然尺度等比裁切，跨大背景应按实际画布调整 viewBox 和点距；不要把整幅无限拉伸。每个实例把 riso-a 前缀替换为唯一ID，所有 url 引用同步。单色版删除一层，不通过整组透明度降低正文。

```css
.vl-riso { position:relative;isolation:isolate;overflow:hidden;background:var(--riso-paper,#f5efdf);color:#292d27; }
.vl-riso__ink { position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:var(--riso-opacity,.78);mix-blend-mode:multiply; }
.vl-riso__copy { position:relative;z-index:1;padding:32px; }
.vl-riso__yellow { fill:var(--riso-yellow,#ced12c); }
.vl-riso__blue { fill:var(--riso-blue,#4282aa); }
.vl-riso__red { fill:var(--riso-red,#d65b45); }
```

```html
<div class="vl-riso" style="min-height:300px">
 <svg class="vl-riso__ink" viewBox="0 0 600 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs>
   <filter id="riso-a-rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".45" numOctaves="2" seed="18" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" xChannelSelector="R" yChannelSelector="G"/></filter>
   <pattern id="riso-a-y" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(23)"><ellipse class="vl-riso__yellow" cx="3" cy="3" rx="2.2" ry="1.6"/></pattern>
   <pattern id="riso-a-b" width="6.5" height="6.5" patternUnits="userSpaceOnUse" patternTransform="rotate(-17)"><ellipse class="vl-riso__blue" cx="3" cy="3" rx="1.6" ry="1.25"/></pattern>
  </defs>
  <g filter="url(#riso-a-rough)"><path d="M0 0H380Q220 150 360 400H0Z" fill="url(#riso-a-y)"/><path d="M310 0H600V400H120Q420 180 310 0" fill="url(#riso-a-b)" style="mix-blend-mode:multiply" transform="translate(2 -1)"/></g>
 </svg>
 <div class="vl-riso__copy">独立排版的内容</div>
</div>
```
小尺寸易摩尔纹：在最终尺寸检查点间距，缩略卡优先减弱墨层或移除第二角度；这只是印刷近似，不等同真实 RISO 油墨渗透。

三色印刷参数：复制一组pattern和独立色块路径，使用唯一后缀r，圆点填充class=vl-riso__red；第三版角度建议55°、间距6.2、位移(-1,2)。沿用同一rough滤镜，不复制滤镜机制。黄灰预设将blue设为#60615a；红黄蓝预设恢复blue=#6e8ca6，yellow=#ecb844，red=#dc7669。色版叠印由不重叠到重叠调节，不用平滑渐变替代。

<a id="surface.modulated-stipple"></a>

## 空间调制的灰度颗粒

风格标签：通用。

基底：[彩色屏幕颗粒](paper-and-print.md#surface.screen-grain)。此变体改为灰色阈值颗粒，并用低频密度 mask 留出弯曲稀疏带。区别于铺满均匀噪点；不是织物经纬或纸纤维。

| 参数 | 起点／调整 |
|---|---|
| baseFrequency | .48；.25–.8（细度） |
| alpha计算 | 红通道×8−4.5；偏置−4.0更密，−4.8更稀 |
| --stipple-alpha | .7；.15–.75，只影响纹理 |
| 低频分布 | ellipse中心 .61,.57；尺寸 .48,.66；旋转24° |

alpha来自噪声红通道，不能取恒定的SourceAlpha。模板提供中心疏、边部密的一种分布；参考图多条褶皱需增加独立密度场，不能宣称本示例完全复现。用于卡片／背景；正文独立上层。每个实例的 stipple-a 前缀需唯一。

```css
.vl-stipple {position:relative;isolation:isolate;overflow:hidden;background:var(--stipple-paper,#f3f3f1);}
.vl-stipple__grain {position:absolute;inset:0;width:100%;height:100%;opacity:var(--stipple-alpha,.7);pointer-events:none;}
.vl-stipple__copy {position:relative;z-index:1;padding:32px;}
```

```html
<div class="vl-stipple" style="min-height:300px">
 <svg class="vl-stipple__grain" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
   <filter id="stipple-a-dots" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency=".48" numOctaves="1" seed="37"/>
    <feColorMatrix type="matrix" values="0 0 0 0 .35  0 0 0 0 .38  0 0 0 0 .39  8 0 0 0 -4.5"/>
   </filter>
   <radialGradient id="stipple-a-gap"><stop stop-color="black" offset="0"/><stop stop-color="#555" offset=".4"/><stop stop-color="white" offset="1"/></radialGradient>
   <mask id="stipple-a-mask" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/><ellipse cx=".61" cy=".57" rx=".48" ry=".66" fill="url(#stipple-a-gap)" transform="rotate(24 .61 .57)"/></mask>
  </defs>
  <rect width="100%" height="100%" filter="url(#stipple-a-dots)" mask="url(#stipple-a-mask)"/>
 </svg>
 <div class="vl-stipple__copy">保留中心阅读区</div>
</div>
```
缩图检查颗粒是否变成灰雾；若如此减小密度而非提高对比。照片已有颗粒时不再叠加。

<a id="surface.scanline"></a>

## 正文后置薄扫描线

风格标签：通用。

使用独立span而非占用宿主伪元素，正文必须放ct-scan__content，确保z-index在扫描层之上；宿主背景在扫描层之下。周期--ct-scan-period默认3px，CSS限制2–4px；线宽默认1px，限制0.5–1px；默认颜色alpha .08，建议.04–.12。--ct-scan-enabled:0关闭，仅改变装饰层透明度，不改变容器、文字或图片透明度。内容和图片是不透明时自然遮住后方扫描，适合阅读面而非盖住截图。无动画、无固定高度。

分类说明：由硬色标渐变构成的规则扫描或稀疏条带；不是随机纸纹，也不声称真实屏幕成像。

```css
.ct-scan{position:relative;isolation:isolate;}.ct-scan__layer{position:absolute;inset:0;z-index:0;pointer-events:none;user-select:none;border-radius:inherit;opacity:var(--ct-scan-enabled,1);background:repeating-linear-gradient(to bottom,var(--ct-scan-color,rgba(196,232,246,.08)) 0,var(--ct-scan-color,rgba(196,232,246,.08)) clamp(.5px,var(--ct-scan-line,1px),1px),transparent clamp(.5px,var(--ct-scan-line,1px),1px),transparent clamp(2px,var(--ct-scan-period,3px),4px));}.ct-scan__content{position:relative;z-index:1;min-width:0;}
```

```html
<div class="ct-scan" style="padding:24px;background:#24313d;color:#fff"><span class="ct-scan__layer" aria-hidden="true"></span><div class="ct-scan__content">薄扫描线在正文后面。</div></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。

<a id="surface.sparse-glitch-bars"></a>

## 确定性稀疏背景故障条

风格标签：通用。

六组固定多层渐变，每层只绘一次，不重复、不随机、不动画；高度变化只改变相对锚点，不增加条数。--ct-glitch-p1至p6配置每组位置；w1至w6建议8–110px；h1至h6建议1–4px。两种颜色由cyan、violet变量设置，默认低透明度。--ct-glitch-enabled:0关闭背景层。真实内容放ct-glitch__content；默认位置偏边缘，阅读区应降低色彩alpha或重新设置锚点。只作用指定组件背景，不挂到body做全页高频纹理。

分类说明：由硬色标渐变构成的规则扫描或稀疏条带；不是随机纸纹，也不声称真实屏幕成像。

```css
.ct-glitch{position:relative;isolation:isolate;}.ct-glitch__layer{position:absolute;inset:0;z-index:0;pointer-events:none;user-select:none;overflow:hidden;opacity:var(--ct-glitch-enabled,1);background-image:linear-gradient(90deg,transparent 0 8%,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 8% 46%,transparent 46% 57%,var(--ct-glitch-violet,rgba(163,118,185,.2)) 57% 78%,transparent 78%),linear-gradient(90deg,var(--ct-glitch-violet,rgba(163,118,185,.2)) 0 18%,transparent 18% 31%,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 31% 91%,transparent 91%),linear-gradient(90deg,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 0 23%,transparent 23% 30%,var(--ct-glitch-violet,rgba(163,118,185,.2)) 30% 64%,transparent 64%),linear-gradient(90deg,transparent 0 10%,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 10% 66%,transparent 66% 73%,var(--ct-glitch-violet,rgba(163,118,185,.2)) 73%),linear-gradient(90deg,var(--ct-glitch-violet,rgba(163,118,185,.2)) 0 26%,transparent 26% 42%,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 42% 80%,transparent 80%),linear-gradient(90deg,var(--ct-glitch-cyan,rgba(99,198,219,.28)) 0 38%,transparent 38% 53%,var(--ct-glitch-violet,rgba(163,118,185,.2)) 53% 88%,transparent 88%);background-repeat:no-repeat;background-size:var(--ct-glitch-w1,92px) var(--ct-glitch-h1,2px),var(--ct-glitch-w2,58px) var(--ct-glitch-h2,1px),var(--ct-glitch-w3,108px) var(--ct-glitch-h3,3px),var(--ct-glitch-w4,76px) var(--ct-glitch-h4,2px),var(--ct-glitch-w5,44px) var(--ct-glitch-h5,1px),var(--ct-glitch-w6,88px) var(--ct-glitch-h6,2px);background-position:var(--ct-glitch-p1,4% 8%),var(--ct-glitch-p2,96% 18%),var(--ct-glitch-p3,0% 41%),var(--ct-glitch-p4,100% 57%),var(--ct-glitch-p5,7% 79%),var(--ct-glitch-p6,93% 94%);}.ct-glitch__content{position:relative;z-index:1;min-width:0;}
```

```html
<div class="ct-glitch" style="width:min(100%,420px);background:#18232c;color:#fff"><span class="ct-glitch__layer" aria-hidden="true"></span><div class="ct-glitch__content" style="padding:50px 30px">稀疏背景短条<br>固定位置，不重复铺满。</div></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。

<a id="surface.worn-ink"></a>

## 局部掉墨与擦损

风格标签：通用。

默认掉墨强度0.23，推荐0.08–0.35；wear-color指定露底色，与内容颜色分离。固定五处斑点和两组断续划痕，确定性可复现，不对内容设置透明度，不宣称还原真实纸纤维。容器底面z0、marks装饰z1、content文字z2，三者关系不可互换。任意宽度与文案量均可自然增高，不限制列数；长容器不会用密集重复噪声覆盖文字。独立示例标题700、正文RetroSource 400。参考仅近似局部擦损的分布逻辑，不能替代摄影中的真实磨蚀。 实渲染修正：用确定性不规则小缺墨和断裂擦痕遮罩替代贯穿长直线，默认强度.6、推荐.35–.8、平铺320×210px；露底色必须与真实承载底色绑定。这是墨面磨损覆盖近似，不支持字形、不宣称真实纸纤维。

```json
{
  "dependencies": [],
  "asset_slots": [],
  "font_binding": {
    "family": "RetroSource",
    "catalog_id": "chinese-0010-font-4f8d31775b64",
    "file": "SourceHanSansSC-VF.otf",
    "range": "250–900",
    "status": "示例阅读黑体；原图艺术Logo作为独立素材，不声称字体精确复原",
    "additional_candidates": {
      "RetroDisplay": {
        "catalog_id": "chinese-0045-font-c817c7883480",
        "file": "DouyinSansBold.ttf",
        "weight": 400,
        "face": "Bold"
      },
      "RetroNarrow": {
        "catalog_id": "chinese-0194-font-3a657740be7a",
        "file": "ChillGSans.otf",
        "weight": 500,
        "face": "Medium",
        "source": "https://github.com/Warren2060/ChillGSans"
      }
    }
  }
}
```

```css
.vl-r3-wear-demo{--vl-r3-ground:#242420;--vl-r3-warning:#d7dd16;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;--vl-r3-muted:#999781;max-width:658px;padding:24px;background:var(--vl-r3-paper);font-family:RetroSource,sans-serif;box-sizing:border-box}.vl-r3-wear{--vl-r3-wear-strength:.23;--vl-r3-wear-color:var(--vl-r3-paper,#c6c2aa);position:relative;isolation:isolate}.vl-r3-wear__marks{position:absolute;inset:0;z-index:1;pointer-events:none;overflow:hidden;opacity:var(--vl-r3-wear-strength);background:radial-gradient(ellipse 22px 3px at 8% 17%,var(--vl-r3-wear-color) 0 68%,transparent 74%),radial-gradient(ellipse 3px 11px at 17% 87%,var(--vl-r3-wear-color) 0 66%,transparent 74%),radial-gradient(ellipse 37px 2px at 58% 9%,var(--vl-r3-wear-color) 0 65%,transparent 75%),radial-gradient(ellipse 11px 4px at 87% 71%,var(--vl-r3-wear-color) 0 65%,transparent 76%),radial-gradient(ellipse 31px 2px at 73% 93%,var(--vl-r3-wear-color) 0 65%,transparent 75%)}.vl-r3-wear__marks:before{content:'';position:absolute;inset:0;background:linear-gradient(116deg,transparent 0 12%,var(--vl-r3-wear-color) 12.1% 12.3%,transparent 12.4% 66%,var(--vl-r3-wear-color) 66.1% 66.25%,transparent 66.4%),linear-gradient(7deg,transparent 0 83%,var(--vl-r3-wear-color) 83.1% 83.35%,transparent 83.5%);clip-path:polygon(0 0,100% 0,100% 23%,75% 18%,72% 78%,100% 80%,100% 100%,0 100%,0 69%,22% 72%,24% 27%,0 25%)}.vl-r3-wear__content{position:relative;z-index:2}.vl-r3-wear-demo__panel{padding:26px;background:var(--vl-r3-ink);color:var(--vl-r3-paper)}.vl-r3-wear-demo__title{margin:0 0 12px;font-size:clamp(22px,5vw,34px);font-weight:700}.vl-r3-wear-demo__copy{margin:0;font-size:15px;line-height:1.8;font-weight:400}
.vl-r3-wear__marks{background:var(--vl-r3-wear-color);mask-image:url(asset:svg/retro-worn-ink.svg);mask-size:320px 210px;mask-repeat:repeat;opacity:var(--vl-r3-wear-strength,.6)}.vl-r3-wear__marks:before{display:none}.vl-r3-wear{--vl-r3-wear-strength:.6}
```

```html
<div class="vl-r3-wear-demo"><section class="vl-r3-wear vl-r3-wear-demo__panel"><span class="vl-r3-wear__marks" aria-hidden="true"></span><div class="vl-r3-wear__content"><h2 class="vl-r3-wear-demo__title">已归档 / FILED</h2><p class="vl-r3-wear-demo__copy">墨面边缘留下细小擦痕，档案正文仍保持完整、清晰。此装饰层可用于深墨事实栏，也可叠在警戒带上。</p></div></section></div>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：修正后实际658/420截图与正文加倍验证通过。掉墨采用内联SVG资源解析，真实内容独立不透明；出纸说明保留槽后垂纸、前唇、低对比横纹及前便笺层级。验收针对本条机制，非整页精确复刻。
