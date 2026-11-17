# 球面玻璃近似

状态：近似实现。数值为可调起点，不是参考图原始源参数。

<a id="material.sphere-glass"></a>

## 球面玻璃近似

风格标签：通用。

对应蓝色二次元活动中的圆形徽章。圆形轮廓复用 shape.badge，新增中心透色、暗部厚度、边缘亮线与弧形高光；它们与普通磨砂平面不是同一材质预设。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-sphere-tint` | `#1679c4` | 球体透色色调 |
| `--vl-sphere-alpha` | `.5` | 球体底色透明度，建议 .2–.75；不影响字面 |
| `--vl-sphere-dark` | `#052b65` | 边缘厚度与背光暗部 |
| `--vl-sphere-rim` | `#cefaff` | 轮廓与高光色 |
| `--vl-sphere-rim-width` | `1px` | 边缘细线宽度 |
| `--vl-sphere-shine` | `.85` | 顶部高光强度 |
| `--vl-sphere-shine-x` | `30%` | 顶部高光横向位置 |
| `--vl-sphere-shine-y` | `8%` | 顶部高光纵向位置 |
| `--vl-sphere-blur` | `1px` | 透底背景模糊，设 0 保持清晰 |
| `--vl-sphere-content-inset` | `12%` | 文字距圆边的安全区 |

```css
.vl-badge.vl-sphere { position:relative; isolation:isolate; padding:0; border:0; background:transparent; }
.vl-sphere__shell { position:absolute; inset:0; z-index:0; border-radius:inherit; pointer-events:none; border:var(--vl-sphere-rim-width,1px) solid color-mix(in srgb,var(--vl-sphere-rim,#cefaff) 75%,transparent); backdrop-filter:blur(var(--vl-sphere-blur,1px)); background:radial-gradient(ellipse 85% 60% at var(--vl-sphere-shine-x,30%) var(--vl-sphere-shine-y,8%),color-mix(in srgb,var(--vl-sphere-rim,#cefaff) calc(var(--vl-sphere-shine,.85) * 100%),transparent) 0%,transparent 62%),radial-gradient(ellipse 80% 65% at 70% 95%,color-mix(in srgb,var(--vl-sphere-tint,#1679c4) 72%,transparent) 0%,transparent 72%),radial-gradient(circle at 40% 35%,color-mix(in srgb,var(--vl-sphere-tint,#1679c4) calc(var(--vl-sphere-alpha,.5) * 100%),transparent) 0%,color-mix(in srgb,var(--vl-sphere-dark,#052b65) calc(var(--vl-sphere-alpha,.5) * 100%),transparent) 85%); box-shadow:inset -5px -7px 14px color-mix(in srgb,var(--vl-sphere-dark,#052b65) 60%,transparent),inset 3px 4px 7px color-mix(in srgb,var(--vl-sphere-rim,#cefaff) 35%,transparent),0 0 5px color-mix(in srgb,var(--vl-sphere-tint,#1679c4) 45%,transparent); }
.vl-sphere__shine { position:absolute; z-index:1; inset:5% 13% 57% 13%; border-radius:50%; border-top:calc(var(--vl-sphere-rim-width,1px) * 1.5) solid var(--vl-sphere-rim,#cefaff); opacity:var(--vl-sphere-shine,.85); pointer-events:none; }
.vl-sphere__content { position:relative; z-index:2; margin:var(--vl-sphere-content-inset,12%); text-align:center; }
```

```html
<div class="vl-badge vl-badge--circle vl-sphere" style="--vl-badge-size:128px;--vl-label-ink:#8bdeff"><span class="vl-sphere__shell" aria-hidden="true"></span><span class="vl-sphere__shine" aria-hidden="true"></span><div class="vl-sphere__content">圆形<br>主题</div></div>
```

依赖 [徽章轮廓](../shapes/capsules-and-badges.md#shape.badge)。建议短字徽章直径 96–160px；尺寸调节使用原 badge-size，不复制一套球体尺寸参数。顶端弧形高光、普通文字发光和弧形路径排字是三个不同效果。壳体和高光独立于内容；复杂的背景折射、非均匀鼓包仍需图像或专门变形实现。普通玻璃继续读取 [material.glass](materials.md#material.glass)。

<a id="surface.pebbled-glass"></a>

## 压纹玻璃｜粉彩与冰蓝

风格标签：通用。

表面凸凹亮沟模拟，区别于 [玻璃透明面](materials.md#material.glass) 和 [柔焦](diffuse-light.md#surface.soft-focus-mist)。一份实现，两套色场；不要按卡片／背景或粉彩／冰蓝重复建文件。适用于卡片和背景，暂不作为字体填充。

宏观柔和色团在底层，微小凸凹光照在中层，正文独立上层。此实现没有真实背景折射；原图强折射细节需要专用纹理或渲染素材。没有透后景需求时不添加 backdrop-filter。

| 参数 | 起点／调整 |
|---|---|
| baseFrequency | .16 .20；.08–.25，越大越细 |
| surfaceScale | 2.5 / 3；1–4，控制浮雕深浅 |
| specularExponent | 12；6–24，控制亮边锐度 |
| --pebble-relief | .58，冰蓝 .7；.25–.8 |
| 色场 | 粉青白径向色团；ice 类切换蓝白斜带 |

每个实例使用唯一滤镜ID pebble-a，不给正文父节点加 filter/opacity。SVG无viewBox，频率按CSS像素处理；最终输出尺寸应核对纹理尺度。大背景避免多个重叠滤镜。

```css
.vl-pebble { position:relative;isolation:isolate;overflow:hidden;background:var(--pebble-base,#f4f5ef); }
.vl-pebble__color { position:absolute;inset:0;background:var(--pebble-field,radial-gradient(ellipse at 78% 24%,#efb4d1 0%,transparent 43%),radial-gradient(ellipse at 16% 65%,#acd0cc 0%,transparent 50%),linear-gradient(135deg,#faf7ec,#c6ddea)); }
.vl-pebble__relief { position:absolute;inset:0;width:100%;height:100%;opacity:var(--pebble-relief,.58);mix-blend-mode:soft-light;pointer-events:none; }
.vl-pebble__copy { position:relative;z-index:1;padding:32px;color:#24353b; }
.vl-pebble--ice { --pebble-field:radial-gradient(ellipse at 8% 74%,#f2f2e8 0%,transparent 43%),linear-gradient(126deg,#d9e4e7 0%,#92bcdc 36%,#b8d2e5 55%,#efeee7 84%);--pebble-relief:.7; }
```

```html
<div class="vl-pebble" style="min-height:300px">
 <div class="vl-pebble__color" aria-hidden="true"></div>
 <svg class="vl-pebble__relief" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
  <defs><filter id="pebble-a" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
   <feTurbulence type="fractalNoise" baseFrequency=".16 .20" numOctaves="2" seed="23" result="height"/>
   <feDiffuseLighting in="height" surfaceScale="2.5" diffuseConstant="1" lighting-color="white" result="diff"><feDistantLight azimuth="225" elevation="42"/></feDiffuseLighting>
   <feSpecularLighting in="height" surfaceScale="3" specularConstant=".65" specularExponent="12" lighting-color="white" result="shine"><feDistantLight azimuth="225" elevation="55"/></feSpecularLighting>
   <feBlend in="diff" in2="shine" mode="screen"/>
  </filter></defs>
  <rect width="100%" height="100%" fill="white" filter="url(#pebble-a)"/>
 </svg>
 <div class="vl-pebble__copy">独立的清晰文字</div>
</div>
```
冰蓝预设：同一节点增加 `vl-pebble--ice`。字体可使用独立纯色面板保障阅读；不能将密集凸凹直接罩在细字上。
