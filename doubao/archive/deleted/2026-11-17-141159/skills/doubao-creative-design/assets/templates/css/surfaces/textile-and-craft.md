# 织物手作

状态：已实现。

参考：图 1 棕色背景的经纬纹理。细线经纬是可复用 CSS 近似；粗糙纤维、结头与真实布面起伏需要纹理素材。

<a id="surface.woven-grid"></a>

## 织物手作原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-weave-step` | `5px` | 经纬间隔，建议 3–9px |
| `--vl-weave-line` | `.65px` | 线宽，建议 .4–1px 且小于 step |
| `--vl-weave-opacity` | `.12` | 0–.3；轻纹理 .06–.12 |
| `--vl-weave-light` | `#f2d4a0` | 亮线颜色 |
| `--vl-weave-dark` | `#4c281b` | 暗线颜色 |

```css
.vl-weave { position:relative; isolation:isolate; }
.vl-weave__texture { position:absolute; inset:0; z-index:-1; pointer-events:none; border-radius:inherit; opacity:var(--vl-weave-opacity,.12); background-image:repeating-linear-gradient(0deg,var(--vl-weave-light,#f2d4a0) 0 var(--vl-weave-line,.65px),transparent var(--vl-weave-line,.65px) var(--vl-weave-step,5px)),repeating-linear-gradient(90deg,var(--vl-weave-dark,#4c281b) 0 var(--vl-weave-line,.65px),transparent var(--vl-weave-line,.65px) var(--vl-weave-step,5px)); }
```

```html
<section class="vl-weave" style="background:var(--vl-tint)"><span class="vl-weave__texture" aria-hidden="true"></span><h2>织纹章节</h2></section>
```

为避免所有材质都变成重噪点，织纹强度独立于现有 grain。经纬纹理与纸粒可分别选择，只有参考确实同时存在时才叠加。检查最终导出尺寸，过密细线缩图可能产生摩尔纹。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="surface.twisted-cord"></a>

## 双色绳近似

风格标签：通用。

补齐蓝白扭绳与秋日活动绳线。圆柱明暗叠加双色斜条纹，适用于直线或整体倾斜的装饰绳。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-cord-thickness` | `8px` | 绳子直径 |
| `--vl-cord-step` | `12px` | 一组双色条纹的周期 |
| `--vl-cord-a` | `#f9f4df` | 第一股颜色 |
| `--vl-cord-b` | `#46b9dc` | 第二股颜色 |
| `--vl-cord-slant` | `125deg` | 双色条纹方向 |

```css
.vl-cord { display:block; height:var(--vl-cord-thickness,8px); border-radius:999px; background:linear-gradient(0deg,#0005 0%,transparent 40%,#fff9 65%,transparent 100%),repeating-linear-gradient(var(--vl-cord-slant,125deg),var(--vl-cord-a,#f9f4df) 0 calc(var(--vl-cord-step,12px) / 2),var(--vl-cord-b,#46b9dc) calc(var(--vl-cord-step,12px) / 2) var(--vl-cord-step,12px)); transform:rotate(var(--vl-rotate,0deg)); }
```

```html
<span class="vl-cord" style="width:100%;--vl-rotate:-2deg" aria-hidden="true"></span>
```

只保留视觉上的扭纹和厚度近似，不模拟真正编织拓扑。弯曲、打结、垂坠路径或有明显毛纤维的绳索需要 SVG 路径／素材；不能靠旋转一条直线假装复杂绳结。
