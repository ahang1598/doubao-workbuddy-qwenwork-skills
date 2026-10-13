# 卡片与面板

状态：已实现。

普通矩形和圆角面板沿用 [shape.rounded](containers.md#shape.rounded)。参考图 1 的肩角描边另做阶梯轮廓分支；这是规则几何近似，不包含原图花形装饰。

<a id="shape.stepped-frame"></a>

## 卡片与面板原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-frame-step` | `10px` | 肩角尺寸，建议 6–18px |
| `--vl-frame-border` | `2px` | 外框厚度，建议 1–4px |
| `--vl-frame-inset` | `24px` | 内容安全距离，应大于 step |

```css
.vl-stepped { --vl-stepped-path:polygon(0 var(--vl-frame-step,10px),var(--vl-frame-step,10px) var(--vl-frame-step,10px),var(--vl-frame-step,10px) 0,calc(100% - var(--vl-frame-step,10px)) 0,calc(100% - var(--vl-frame-step,10px)) var(--vl-frame-step,10px),100% var(--vl-frame-step,10px),100% calc(100% - var(--vl-frame-step,10px)),calc(100% - var(--vl-frame-step,10px)) calc(100% - var(--vl-frame-step,10px)),calc(100% - var(--vl-frame-step,10px)) 100%,var(--vl-frame-step,10px) 100%,var(--vl-frame-step,10px) calc(100% - var(--vl-frame-step,10px)),0 calc(100% - var(--vl-frame-step,10px))); padding:var(--vl-frame-border,2px); background:var(--vl-edge-color,#c79a53); clip-path:var(--vl-stepped-path); }
.vl-stepped__body { box-sizing:border-box; padding:var(--vl-frame-inset,24px); background:var(--vl-tint,#ffe7bf); color:var(--vl-ink,#5b301c); clip-path:var(--vl-stepped-path); overflow-wrap:anywhere; }
```

```html
<section class="vl-stepped"><div class="vl-stepped__body"><h2>产品信息</h2><p>真实规格内容</p></div></section>
```

此轮廓使用内外两层同形缩放构成阶梯描边；角部是装饰肩角，不是严格等距工程描边。需要外部投影时加独立外包装，避免 clip-path 裁掉投影。

普通卡片的复用覆盖：图 2 的方角信息区 `--vl-radius:0px;--vl-border-width:0px`；图 3 的面板 `--vl-radius:14px;--vl-border-width:1px`。这两项只改现有 rounded 的参数，不新增 shape ID，也不强制添加玻璃质感。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="shape.speech-panel"></a>

## 侧尾对话框

风格标签：通用。

参考数码奇妙夜的人物引语。尾部与正文是两个真实节点，使用同一填色与边色。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-tail-size` | `16px` | 尾部方形基元边长，建议 10–24px |
| `--vl-tail-y` | `32px` | 尾部距顶端距离，应避开圆角 |

```css
.vl-speech { position:relative; border:var(--vl-border-width,2px) solid var(--vl-edge-color,#b58e45); border-radius:var(--vl-radius,20px); padding:var(--vl-padding,20px); background:var(--vl-tint,#fff8e8); color:var(--vl-ink,#302a20); }
.vl-speech__tail { position:absolute; left:calc(var(--vl-tail-size,16px) / -2 - var(--vl-border-width,2px) / 2); top:var(--vl-tail-y,32px); width:var(--vl-tail-size,16px); aspect-ratio:1; background:var(--vl-tint,#fff8e8); border-top:var(--vl-border-width,2px) solid var(--vl-edge-color,#b58e45); border-left:var(--vl-border-width,2px) solid var(--vl-edge-color,#b58e45); transform:rotate(-45deg); pointer-events:none; }
.vl-speech__content { position:relative; overflow-wrap:anywhere; }
```

```html
<aside class="vl-speech"><span class="vl-speech__tail" aria-hidden="true"></span><div class="vl-speech__content">人物引语</div></aside>
```

radius、border-width、padding、tint、ink 沿用已有参数。本分支未指定覆盖时 radius=20px、border-width=2px、padding=20px；尾部超出容器的空间由父布局预留。此分支为左侧尾部，若改方向需同时调整位置、旋转和边线，不能只翻转正文。

<a id="shape.arch-window"></a>

## 拱形图片窗

风格标签：通用。

参考数码奇妙夜的拱形人物窗。只封装图片裁切轮廓，阳台、窗框细节仍为素材。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-window-ratio` | `3 / 4` | 窗口宽高比 |
| `--vl-arch-radius` | `50% 50% 0 0 / 35% 35% 0 0` | 上部椭圆圆角 |
| `--vl-window-focus` | `50% 50%` | 图像焦点位置 |

```css
.vl-arch-window { aspect-ratio:var(--vl-window-ratio,3 / 4); border-radius:var(--vl-arch-radius,50% 50% 0 0 / 35% 35% 0 0); overflow:hidden; background:var(--vl-tint,#efe4cc); }
.vl-arch-window > img { display:block; width:100%; height:100%; object-fit:cover; object-position:var(--vl-window-focus,50% 50%); }
```

```html
<figure style="margin:0"><div class="vl-arch-window"><img src="人物素材" alt="人物说明"></div><figcaption>窗外说明</figcaption></figure>
```

标题和注释放在窗口外，避免圆弧裁切文字；焦点位置以实际人脸为依据。矩形和普通圆角图片不新增此分支。

<a id="shape.chinese-petal-window"></a>

## 中式花瓣窗框

风格标签：通用。

六瓣柔弧轮廓的可复用容器，适合中式花窗、植物图窗、局部摄影与短题。轮廓由内嵌SVG几何提供，CSS负责尺寸、裁切和槽位；不是玻璃摆件素材，也不依赖窗内内容生成形状。

结构：pw-window外层→pw-clip裁切层→可替换pw-image或pw-content；表面pw-surface与轮廓内缘pw-relief独立；外边线pw-edge不参与内容。边缘效果默认关闭、背景透明，不能强制把所有实例染成绿色。

参数：size默认330px，等宽高，建议180–600px；fit=cover、position=50% 50%，换照片需检查主体裁切。line默认.004为归一化SVG描边，建议0–.012；edge默认透明，base透明，surface=none，relief=0，softness=3px。surface只接受表面色场，不包含文字；relief为0–1的局部轮廓内缘强度，不声称真实折射。准确文字置中央inset22%安全框，长文案改外置图注或增大窗口，不缩字、不要让内容塞进花瓣尖端。

每个实例必须替换pw-example为页面内唯一ID，并同步--pw-clip引用；图像与文字无须修改SVG路径。多个实例不能共用重复DOM ID。轮廓是六瓣近似，不是通用任意瓣数参数；调整轮廓需同步clip与两个描边path。多素材支持的是替换槽位，不是把背景切成花瓣块。

```css
.pw-window{position:relative;isolation:isolate;width:var(--pw-size,330px);max-width:100%;aspect-ratio:1;margin:0}.pw-defs{position:absolute;width:0;height:0;overflow:hidden}.pw-clip{position:absolute;inset:0;clip-path:var(--pw-clip);background:var(--pw-base,transparent)}.pw-image{display:block;width:100%;height:100%;object-fit:var(--pw-fit,cover);object-position:var(--pw-position,50% 50%)}.pw-content{position:absolute;inset:22%;display:grid;align-content:center;text-align:center;overflow-wrap:anywhere;z-index:2}.pw-content>*{margin:0}.pw-surface{position:absolute;inset:0;pointer-events:none;background:var(--pw-surface,none);z-index:1}.pw-edge{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:3;overflow:visible}.pw-edge path{fill:none;stroke:var(--pw-edge,transparent);stroke-width:var(--pw-line,.004)}.pw-relief{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:var(--pw-relief,0);filter:blur(var(--pw-softness,3px));z-index:1}.pw-relief path{fill:none;stroke:var(--pw-shade,#738b60);stroke-width:.035}
```

```html
<figure class="pw-window" style="--pw-clip:url(#pw-example)"><svg class="pw-defs" aria-hidden="true"><defs><clipPath id="pw-example" clipPathUnits="objectBoundingBox"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></clipPath></defs></svg><div class="pw-clip"><img class="pw-image" src="SLOT:content" alt="窗内素材"><svg class="pw-relief" viewBox="0 0 1 1" aria-hidden="true"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></svg><span class="pw-surface" aria-hidden="true"></span></div><svg class="pw-edge" viewBox="0 0 1 1" aria-hidden="true"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></svg></figure>
```

纯文字实例将pw-image换成`<div class="pw-content"><h2>窗中短题</h2><p>简短说明</p></div>`。竹韵实例在组合中绑定淡绿底色、描边、轻内缘，不在原子中固化竹叶或质感。已验证三个独立实例：竹叶、摄影、coding文字；唯一ID、角部裁切、180/420px等比例缩放。真实照片焦点和长文本仍须逐例核对。

<a id="shape.editor-selection"></a>

## 编辑器选框与控制柄

风格标签：通用。

内容盒自身边框构成选框，四角方形控制点随盒高增长；可选SVG贝塞尔曲线、切线与端点锚定在内容盒上方的保留区。背景在底层、文字在内容层、控制装饰在前层但不进入文字安全区，全部装饰忽略指针且不参与辅助技术阅读。

参数基准：示例宽680px；原子颜色用于机制演示，由整页组合覆盖，不绑定某种风格。

| 参数 | 默认值、单位与范围 |
|---|---|
| `--cv-demo-width` | {"default": "680px", "unit": "px", "range": "示例固定680px；窄屏最大100%"} |
| `--cv-selection-color` | {"default": "#245ce5", "unit": "color", "range": "合法CSS颜色，须与背景有足够对比"} |
| `--cv-selection-stroke` | {"default": "1px", "unit": "px", "range": "1–2px"} |
| `--cv-handle-size` | {"default": "8px", "unit": "px", "range": "6–12px"} |
| `--cv-content-pad` | {"default": "22px", "unit": "px", "range": "16–40px，不小于控制点尺寸"} |
| `--cv-edge-safe` | {"default": "28px", "unit": "px", "range": "20–48px"} |
| `--cv-handle-reserve` | {"default": "104px", "unit": "px", "range": "88–140px，不小于贝塞尔装饰高度"} |
| `--cv-bezier-width` | {"default": "280px", "unit": "px", "range": "180–420px，另受容器宽度限制"} |
| `--cv-bezier-height` | {"default": "80px", "unit": "px", "range": "60–88px"} |
| `data-cv-handles` | {"default": "on", "unit": "enum", "range": ["on", "off"]} |

```css
.cv-selection-demo{--cv-demo-width:680px;--cv-selection-color:#245ce5;--cv-selection-stroke:1px;--cv-handle-size:8px;--cv-content-pad:22px;--cv-edge-safe:28px;--cv-handle-reserve:104px;--cv-bezier-width:280px;--cv-bezier-height:80px;box-sizing:border-box;width:var(--cv-demo-width);max-width:100%;padding:var(--cv-edge-safe);background:#f5f2e9;color:#202027;font-family:Arial,'PingFang SC',sans-serif;isolation:isolate}.cv-selection-demo *{box-sizing:border-box}.cv-selection-demo .cv-selection-heading{margin:0 0 12px;font-size:22px;line-height:1.4;overflow-wrap:anywhere}.cv-selection-demo .cv-selection-stage{padding:14px calc(var(--cv-handle-size)/2 + 2px)}.cv-selection-demo .cv-selection-stage[data-cv-handles='on']{padding-top:var(--cv-handle-reserve)}.cv-selection-demo .cv-selection-box{position:relative;min-width:0;border:var(--cv-selection-stroke) solid var(--cv-selection-color);padding:var(--cv-content-pad);background:#fffdf7}.cv-selection-demo .cv-selection-copy{position:relative;z-index:1;min-width:0;overflow-wrap:anywhere}.cv-selection-demo .cv-selection-copy h3{margin:0 0 10px;font-size:28px;line-height:1.15}.cv-selection-demo .cv-selection-copy p{margin:0;font-size:15px;line-height:1.65}.cv-selection-demo .cv-selection-corner{position:absolute;z-index:2;width:var(--cv-handle-size);height:var(--cv-handle-size);border:var(--cv-selection-stroke) solid var(--cv-selection-color);background:#fff;pointer-events:none}.cv-selection-demo .cv-selection-tl{top:0;left:0;transform:translate(-50%,-50%)}.cv-selection-demo .cv-selection-tr{top:0;right:0;transform:translate(50%,-50%)}.cv-selection-demo .cv-selection-bl{bottom:0;left:0;transform:translate(-50%,50%)}.cv-selection-demo .cv-selection-br{bottom:0;right:0;transform:translate(50%,50%)}.cv-selection-demo .cv-selection-bezier{display:none;position:absolute;z-index:2;bottom:calc(100% + 10px);left:50%;transform:translateX(-50%);width:min(var(--cv-bezier-width),calc(100% - 24px));height:var(--cv-bezier-height);color:var(--cv-selection-color);overflow:visible;pointer-events:none}.cv-selection-demo [data-cv-handles='on'] .cv-selection-bezier{display:block}.cv-selection-demo .cv-selection-bezier path,.cv-selection-demo .cv-selection-bezier line,.cv-selection-demo .cv-selection-bezier circle,.cv-selection-demo .cv-selection-bezier rect{stroke:currentColor;stroke-width:var(--cv-selection-stroke);vector-effect:non-scaling-stroke}.cv-selection-demo .cv-selection-bezier path{fill:none}.cv-selection-demo .cv-selection-bezier line{stroke-dasharray:3 3;opacity:.7}.cv-selection-demo .cv-selection-bezier circle,.cv-selection-demo .cv-selection-bezier rect{fill:#fff}
```

```html
<section class="cv-selection-demo" aria-label="编辑器选框示例"><h2 class="cv-selection-heading">编辑选框 · 个人简介</h2><div class="cv-selection-stage" data-cv-handles="on"><article class="cv-selection-box"><svg class="cv-selection-bezier" viewBox="0 0 280 80" preserveAspectRatio="none" aria-hidden="true" focusable="false"><line x1="12" y1="64" x2="88" y2="12"/><line x1="268" y1="64" x2="192" y2="12"/><path d="M12 64 C88 12 192 12 268 64"/><circle cx="88" cy="12" r="4"/><circle cx="192" cy="12" r="4"/><rect x="8" y="60" width="8" height="8"/><rect x="264" y="60" width="8" height="8"/></svg><span class="cv-selection-corner cv-selection-tl" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-tr" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-bl" aria-hidden="true"></span><span class="cv-selection-corner cv-selection-br" aria-hidden="true"></span><div class="cv-selection-copy" lang="en"><h3>Alex Morgan — Editorial Designer</h3><p>Independent designer working across visual identities, publications and digital experiences. Selected projects combine clear typography with thoughtful art direction.</p></div></article></div></section>
```

适配与边界：
- 通用局部机制，不限制产物类型；这是静态编辑器视觉装饰，不提供拖拽或真实选中行为。
- 三类安全区：外缘由--cv-edge-safe及stage横向padding保护；文字由--cv-content-pad保护；贝塞尔装饰由--cv-handle-reserve独占上方空间。关闭控制柄用data-cv-handles="off"，四角仍保留。
- 正文不设固定高度，长标题和长单词可换行；选框随内容增长。祖先容器不应裁切控制点，避免overflow:hidden。
- 示例不含图片；插入图片时应放入内容盒内、设置max-width:100%，保留文字底色，不把控制柄压在人像或正文上。
- SVG是静态三次贝塞尔预设；修改路径时必须同步切线、控制点与端点坐标。

示例中的头像轮廓仅验证几何占位，不是可交付人物素材；正式注入人像需另验主体裁切。SVG复用时须按实例重命名ID及引用。

<a id="shape.chamfered-notched-panel"></a>

## 切角凹口双轨面板

风格标签：通用。

作用于章节容器，不附带字体、底色或默认光。角--ct-panel-corner默认22px，建议18–24px；凹深--ct-panel-notch默认7px，建议5–8px；上退宽180px、侧凹长度72px、底槽宽112px均可配置。线宽--ct-panel-line默认1px，建议1–2px；轨距6px，建议4–9px；外净空22px，内净空30px。角与凹深全部使用固定px，内容增高不拉伸切角。外壳填色默认透明。边轨用CSS evenodd空心多边形沿完整轮廓绘制，双轨非严格工程等距；仅装饰被clip，正文不裁。支持现代CSS polygon(evenodd)，无降级或兼容分支。建议容器宽至少280px，窄框减小顶槽/底槽宽；角和凹口维持px尺寸，随文案增高不拉伸。

```css
.ct-panel{position:relative;isolation:isolate;box-sizing:border-box;min-width:0;min-height:calc(var(--ct-panel-corner,22px)*2 + var(--ct-panel-notch-width,72px));padding:var(--ct-panel-outer-space,22px);--ct-panel-path:polygon(0 var(--ct-panel-corner,22px),var(--ct-panel-corner,22px) 0,calc(50% - var(--ct-panel-top-width,180px)/2 - var(--ct-panel-notch,7px)) 0,calc(50% - var(--ct-panel-top-width,180px)/2) var(--ct-panel-notch,7px),calc(50% + var(--ct-panel-top-width,180px)/2) var(--ct-panel-notch,7px),calc(50% + var(--ct-panel-top-width,180px)/2 + var(--ct-panel-notch,7px)) 0,calc(100% - var(--ct-panel-corner,22px)) 0,100% var(--ct-panel-corner,22px),100% calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)),calc(100% - var(--ct-panel-notch,7px)) calc(50% - var(--ct-panel-notch-width,72px)/2),calc(100% - var(--ct-panel-notch,7px)) calc(50% + var(--ct-panel-notch-width,72px)/2),100% calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),100% calc(100% - var(--ct-panel-corner,22px)),calc(100% - var(--ct-panel-corner,22px)) 100%,calc(50% + var(--ct-panel-bottom-width,112px)/2 + var(--ct-panel-notch,7px)) 100%,calc(50% + var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px)),calc(50% - var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px)),calc(50% - var(--ct-panel-bottom-width,112px)/2 - var(--ct-panel-notch,7px)) 100%,var(--ct-panel-corner,22px) 100%,0 calc(100% - var(--ct-panel-corner,22px)),0 calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),var(--ct-panel-notch,7px) calc(50% + var(--ct-panel-notch-width,72px)/2),var(--ct-panel-notch,7px) calc(50% - var(--ct-panel-notch-width,72px)/2),0 calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)));}.ct-panel__shell,.ct-panel__rail{position:absolute;pointer-events:none;user-select:none;}.ct-panel__shell{clip-path:var(--ct-panel-path);inset:0;z-index:0;background:var(--ct-panel-shell,transparent);}.ct-panel__rail--inner{inset:var(--ct-panel-rail-gap,6px);background:var(--ct-panel-inner-line-color,#526f79);}.ct-panel__body{position:relative;z-index:2;box-sizing:border-box;min-width:0;padding:var(--ct-panel-inner-space,30px);overflow-wrap:anywhere;}.ct-panel__body>:first-child{margin-top:0;}.ct-panel__body>:last-child{margin-bottom:0;}
.ct-panel__rail{inset:0;z-index:1;background:var(--ct-panel-line-color,#7eabb6);clip-path:polygon(evenodd,0 var(--ct-panel-corner,22px),var(--ct-panel-corner,22px) 0,calc(50% - var(--ct-panel-top-width,180px)/2 - var(--ct-panel-notch,7px)) 0,calc(50% - var(--ct-panel-top-width,180px)/2) var(--ct-panel-notch,7px),calc(50% + var(--ct-panel-top-width,180px)/2) var(--ct-panel-notch,7px),calc(50% + var(--ct-panel-top-width,180px)/2 + var(--ct-panel-notch,7px)) 0,calc(100% - var(--ct-panel-corner,22px)) 0,100% var(--ct-panel-corner,22px),100% calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)),calc(100% - var(--ct-panel-notch,7px)) calc(50% - var(--ct-panel-notch-width,72px)/2),calc(100% - var(--ct-panel-notch,7px)) calc(50% + var(--ct-panel-notch-width,72px)/2),100% calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),100% calc(100% - var(--ct-panel-corner,22px)),calc(100% - var(--ct-panel-corner,22px)) 100%,calc(50% + var(--ct-panel-bottom-width,112px)/2 + var(--ct-panel-notch,7px)) 100%,calc(50% + var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px)),calc(50% - var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px)),calc(50% - var(--ct-panel-bottom-width,112px)/2 - var(--ct-panel-notch,7px)) 100%,var(--ct-panel-corner,22px) 100%,0 calc(100% - var(--ct-panel-corner,22px)),0 calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),var(--ct-panel-notch,7px) calc(50% + var(--ct-panel-notch-width,72px)/2),var(--ct-panel-notch,7px) calc(50% - var(--ct-panel-notch-width,72px)/2),0 calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)),0 var(--ct-panel-corner,22px),var(--ct-panel-line,1px) calc(var(--ct-panel-corner,22px) + var(--ct-panel-line,1px) * .42),calc(var(--ct-panel-corner,22px) + var(--ct-panel-line,1px) * .42) var(--ct-panel-line,1px),calc(50% - var(--ct-panel-top-width,180px)/2 - var(--ct-panel-notch,7px)) var(--ct-panel-line,1px),calc(50% - var(--ct-panel-top-width,180px)/2) calc(var(--ct-panel-notch,7px) + var(--ct-panel-line,1px)),calc(50% + var(--ct-panel-top-width,180px)/2) calc(var(--ct-panel-notch,7px) + var(--ct-panel-line,1px)),calc(50% + var(--ct-panel-top-width,180px)/2 + var(--ct-panel-notch,7px)) var(--ct-panel-line,1px),calc(100% - var(--ct-panel-corner,22px) - var(--ct-panel-line,1px) * .42) var(--ct-panel-line,1px),calc(100% - var(--ct-panel-line,1px)) calc(var(--ct-panel-corner,22px) + var(--ct-panel-line,1px) * .42),calc(100% - var(--ct-panel-line,1px)) calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)),calc(100% - var(--ct-panel-notch,7px) - var(--ct-panel-line,1px)) calc(50% - var(--ct-panel-notch-width,72px)/2),calc(100% - var(--ct-panel-notch,7px) - var(--ct-panel-line,1px)) calc(50% + var(--ct-panel-notch-width,72px)/2),calc(100% - var(--ct-panel-line,1px)) calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),calc(100% - var(--ct-panel-line,1px)) calc(100% - var(--ct-panel-corner,22px) - var(--ct-panel-line,1px) * .42),calc(100% - var(--ct-panel-corner,22px) - var(--ct-panel-line,1px) * .42) calc(100% - var(--ct-panel-line,1px)),calc(50% + var(--ct-panel-bottom-width,112px)/2 + var(--ct-panel-notch,7px)) calc(100% - var(--ct-panel-line,1px)),calc(50% + var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px) - var(--ct-panel-line,1px)),calc(50% - var(--ct-panel-bottom-width,112px)/2) calc(100% - var(--ct-panel-notch,7px) - var(--ct-panel-line,1px)),calc(50% - var(--ct-panel-bottom-width,112px)/2 - var(--ct-panel-notch,7px)) calc(100% - var(--ct-panel-line,1px)),calc(var(--ct-panel-corner,22px) + var(--ct-panel-line,1px) * .42) calc(100% - var(--ct-panel-line,1px)),var(--ct-panel-line,1px) calc(100% - var(--ct-panel-corner,22px) - var(--ct-panel-line,1px) * .42),var(--ct-panel-line,1px) calc(50% + var(--ct-panel-notch-width,72px)/2 + var(--ct-panel-notch,7px)),calc(var(--ct-panel-notch,7px) + var(--ct-panel-line,1px)) calc(50% + var(--ct-panel-notch-width,72px)/2),calc(var(--ct-panel-notch,7px) + var(--ct-panel-line,1px)) calc(50% - var(--ct-panel-notch-width,72px)/2),var(--ct-panel-line,1px) calc(50% - var(--ct-panel-notch-width,72px)/2 - var(--ct-panel-notch,7px)),var(--ct-panel-line,1px) calc(var(--ct-panel-corner,22px) + var(--ct-panel-line,1px) * .42),0 var(--ct-panel-corner,22px));}.ct-panel__rail--inner{inset:var(--ct-panel-rail-gap,6px);background:var(--ct-panel-inner-line-color,#526f79);}
```

```html
<div class="ct-panel" style="width:min(100%,440px);--ct-panel-top-width:120px;--ct-panel-shell:rgba(90,125,140,.07)"><span class="ct-panel__shell" aria-hidden="true"></span><span class="ct-panel__rail" aria-hidden="true"></span><span class="ct-panel__rail ct-panel__rail--inner" aria-hidden="true"></span><div class="ct-panel__body"><p>切角凹口面板</p><p>双轨外壳独立，内容自然撑高。</p><button type="button">可点击内容</button></div></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。

<a id="shape.open-chamfer-brackets"></a>

## 开放切角四角括框

风格标签：通用。

臂长--ct-brackets-arm默认48px，建议35–52px；切角--ct-brackets-cut默认15px，建议12–18px；线宽默认2px，建议1–2px；颜色取--ct-brackets-color。正文净空--ct-brackets-space默认40px，CSS强制不小于35px。四角位于正文下层，无实心卡底、无默认发光。宽高应大于两倍臂长，推荐宽度至少200px；高度随正文增长，无固定175px限制。

```css
.ct-brackets{position:relative;isolation:isolate;box-sizing:border-box;min-width:0;}.ct-brackets__body{position:relative;z-index:1;box-sizing:border-box;padding:max(35px,var(--ct-brackets-space,40px));overflow-wrap:anywhere;}.ct-brackets__corner{position:absolute;z-index:0;left:0;top:0;width:var(--ct-brackets-arm,48px);height:var(--ct-brackets-arm,48px);background:var(--ct-brackets-color,#85b6c5);pointer-events:none;user-select:none;clip-path:polygon(0 var(--ct-brackets-cut,15px),var(--ct-brackets-cut,15px) 0,100% 0,100% var(--ct-brackets-line,2px),calc(var(--ct-brackets-cut,15px) + var(--ct-brackets-line,2px)*.42) var(--ct-brackets-line,2px),var(--ct-brackets-line,2px) calc(var(--ct-brackets-cut,15px) + var(--ct-brackets-line,2px)*.42),var(--ct-brackets-line,2px) 100%,0 100%);}.ct-brackets__corner--tr{left:auto;right:0;transform:scaleX(-1);}.ct-brackets__corner--bl{top:auto;bottom:0;transform:scaleY(-1);}.ct-brackets__corner--br{left:auto;right:0;top:auto;bottom:0;transform:scale(-1);}.ct-brackets__body>:first-child{margin-top:0;}.ct-brackets__body>:last-child{margin-bottom:0;}
```

```html
<div class="ct-brackets" style="width:min(100%,470px)"><span class="ct-brackets__corner" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--tr" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--bl" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--br" aria-hidden="true"></span><div class="ct-brackets__body"><p>开放括框</p><p>四角折线，中部留空，正文独立。</p></div></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。

<a id="shape.slanted-strip"></a>

## 文字独立斜切题带

风格标签：通用。

只裁切底板及可选端片，真实文字不做transform、不裁切。切角--ct-strip-cut默认22px，建议18–26px；最小高度50px而非锁定高度；横净空28px，纵净空8px，可随换行增高。底板、端片和文字分别使用fill、end-color、text-color变量；--ct-strip-end-opacity:0关闭端片。端片宽默认8px，建议4–12px。外部可设width:min(100%,350px)，极窄空间需减小切角。

```css
.ct-strip{position:relative;isolation:isolate;display:inline-grid;box-sizing:border-box;max-width:100%;min-width:calc(var(--ct-strip-cut,22px)*2 + 24px);min-height:var(--ct-strip-height,50px);padding:var(--ct-strip-pad-y,8px) max(var(--ct-strip-pad-x,28px),calc(var(--ct-strip-cut,22px) + 6px));align-items:center;text-align:center;vertical-align:middle;}.ct-strip::before{content:'';position:absolute;inset:0;z-index:0;pointer-events:none;background:var(--ct-strip-fill,#2c475a);clip-path:polygon(var(--ct-strip-cut,22px) 0,100% 0,calc(100% - var(--ct-strip-cut,22px)) 100%,0 100%);}.ct-strip::after{content:'';position:absolute;inset:0;z-index:0;pointer-events:none;opacity:var(--ct-strip-end-opacity,1);background:var(--ct-strip-end-color,#85b6c5);clip-path:polygon(calc(100% - var(--ct-strip-end-width,8px)) 0,100% 0,calc(100% - var(--ct-strip-cut,22px)) 100%,calc(100% - var(--ct-strip-cut,22px) - var(--ct-strip-end-width,8px)) 100%);}.ct-strip__text{position:relative;z-index:1;min-width:0;color:var(--ct-strip-text-color,inherit);overflow-wrap:anywhere;}
```

```html
<div class="ct-strip" style="--ct-strip-text-color:#fff"><span class="ct-strip__text">玩法说明 · 演示</span></div>
```

边界：示例底色和字体不是原子依赖。仅装饰可裁切，正文自然撑高；效果关闭时不得影响真实内容。已作本地参考机制及尺寸验证，不代表整页复刻。

<a id="shape.beveled-metal-frame"></a>

## 金属包边框

风格标签：通用。

默认外斜面带9px，建议5–12px；frame-light、frame-mid、frame-dark和frame-slot为颜色接口，其中frame-mid供组合统一银面基色时绑定。不可变结构为外反光斜面→内凹暗沟→真实内容槽三个层次，不能删为普通灰border。伪元素仅画窄高光，z为自然层；内容槽独立裁切，不使用整卡截图。默认宽度上限300px，图像1:1且contain，照片不能拉伸；文字槽自然增长。正文RetroSource 400，英文示例Georgia斜体不是艺术Logo复原。反射为CSS近似，不模拟复杂铬面物体的环境倒影。

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
.vl-r8-metal{--frame-light:#f5faf9;--frame-mid:#aab7be;--frame-dark:#485158;--frame-slot:#e2e9e8;--frame-band:9px;box-sizing:border-box;width:100%;max-width:300px;margin:0;padding:var(--frame-band);position:relative;background:linear-gradient(135deg,var(--frame-light) 0%,#a6aeb1 8%,#edf4f7 17%,var(--frame-dark) 27%,var(--frame-mid) 42%,#f8fbfa 49%,#89939b 63%,#dee7e9 80%,#535b61 94%,var(--frame-light) 100%);clip-path:polygon(2px 0,calc(100% - 2px) 0,100% 2px,100% calc(100% - 2px),calc(100% - 2px) 100%,2px 100%,0 calc(100% - 2px),0 2px);box-shadow:inset 1px 1px 0 #fff,inset -1px -1px 0 #343b3f,inset 3px 3px 0 #cad4da,inset -3px -3px 0 #f4f7f7;color:#080909;font-family:RetroSource,sans-serif;font-weight:400}.vl-r8-metal:before{content:'';position:absolute;inset:3px;pointer-events:none;border-top:1px solid #fff;border-left:1px solid #f5fafc;border-bottom:1px solid #59636b;border-right:1px solid #69737b}.vl-r8-metal__recess{position:relative;padding:4px;background:linear-gradient(135deg,#303b46,#7f94aa 38%,#f5faf9 72%,#a5b4bc);box-shadow:inset 2px 2px 3px #111a,inset -1px -1px 0 #fff;border-radius:2px}.vl-r8-metal__slot{position:relative;overflow:hidden;background:var(--frame-slot);box-shadow:0 0 0 1px #edf1e9,inset 0 2px 5px #0004}.vl-r8-metal__image{display:block;width:100%;height:auto;aspect-ratio:1;object-fit:contain}.vl-r8-metal__sample{box-sizing:border-box;min-height:190px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;text-align:center;gap:14px;background:linear-gradient(130deg,#c0cbce,#e3e8e4 52%,#acb8bd)}.vl-r8-metal__sample strong{font:italic 36px Georgia,serif}.vl-r8-metal__sample p{margin:0;font-size:15px;line-height:1.7}
```

```html
<figure class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><div class="vl-r8-metal__sample"><strong>Starlight</strong><p>银色收藏展示框<br>可替换为商品图或编辑内容</p></div></div></div></figure>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：shape.beveled-metal-frame。验收限本条声明机制，不代表整页或原始字体精确复刻。

<a id="shape.shelf-profile"></a>

## 搁板顶面与前沿

风格标签：通用。

截面形状与主题配色分离；默认厚度24px，建议16–28px，通过--vl-shelf-depth调节。内容层z2、截面z1、顶面接触阴影z0；内容底边与顶面承重线相接关系不变。宽度100%，示例最大658px；可承接单列或多列自然高度内容。RetroSource正文400、示例标题650。CSS仅复原顶面透视、亮前沿及厚侧面，不声称渐变是真实木纹。

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
.vl-r9-shelf{--vl-shelf-depth:24px;--vl-shelf-light:#a95a22;--vl-shelf-mid:#78300d;--vl-shelf-dark:#3c1004;position:relative;box-sizing:border-box;width:100%;padding:24px 5% var(--vl-shelf-depth);isolation:isolate}.vl-r9-shelf::before{content:'';position:absolute;z-index:1;pointer-events:none;left:0;right:0;bottom:0;height:var(--vl-shelf-depth);background:linear-gradient(to bottom,transparent 0 10%,var(--vl-shelf-light) 11% 16%,var(--vl-shelf-mid) 17% 49%,var(--vl-shelf-light) 50% 53%,var(--vl-shelf-dark) 55% 100%);box-shadow:0 10px 13px -7px #170500cc}.vl-r9-shelf::after{content:'';position:absolute;z-index:0;pointer-events:none;left:0;right:0;bottom:calc(var(--vl-shelf-depth) - 5px);height:17px;background:linear-gradient(to bottom,#21070000,#210700b3 60%,var(--vl-shelf-mid));transform:perspective(140px) rotateX(22deg);transform-origin:bottom;box-shadow:0 -8px 14px #24070045}.vl-r9-shelf-content{position:relative;z-index:2}.vl-r9-shelf-demo{max-width:658px;background:#461303;color:#f0d7b5;font-family:RetroSource,sans-serif;font-weight:400}.vl-r9-shelf-demo-object{max-width:270px;margin:24px auto 0;padding:28px 20px;background:#a87548;box-shadow:5px 5px 10px #18060080}.vl-r9-shelf-demo-object h3{margin:0 0 12px;font-size:24px;font-weight:650}.vl-r9-shelf-demo-object p{margin:0;line-height:1.8}
```

```html
<div class="vl-r9-shelf-demo"><section class="vl-r9-shelf"><div class="vl-r9-shelf-content"><article class="vl-r9-shelf-demo-object"><h3>今晚，沿街走走</h3><p>一张街区导览落在搁板上。薄亮前沿承接纸面，厚暗侧面形成柜体的连续横线。</p></article></div></section></div>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：shape.shelf-profile。验收限本条声明机制，不代表整页或原始字体精确复刻。

<a id="shape.recessed-paper-slot"></a>

## 内凹出纸槽

风格标签：通用。

默认机身112px、槽口35px、长纸宽86%；建议纸宽84%–90%、正文安全距22–40px。槽口必须横向贯通，纸从槽后延伸；机身z0、内凹槽z1、纸z2、遮住纸顶的前唇z3、便笺z4不可互换。纸张自然撑高，无固定高度裁文；460px以下便笺解除负边距。单一长纸可承接任意规则段落，不拆卡。字体RetroSource正文400、小题650。底部轻毛边是近似轮廓，超长内容时建议分为多个独立纸章节而非继续拉长毛边；未模拟真实纸纤维或完整金属设备。

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
.vl-r9-slot{--vl-slot-housing:#604737;--vl-slot-bevel:#9b8069;--vl-slot-shadow:#20140e;--vl-slot-paper:#a87548;--vl-slot-ink:#f0d7b5;position:relative;box-sizing:border-box;width:100%;padding-top:34px;isolation:isolate}.vl-r9-slot-machine{position:absolute;z-index:0;top:0;left:0;right:0;height:112px;background:linear-gradient(180deg,var(--vl-slot-bevel) 0 2px,var(--vl-slot-housing) 3px 95%,#38281e);box-shadow:0 3px 0 #b2906b55}.vl-r9-slot-mouth{position:absolute;z-index:1;top:28px;left:4.2%;right:4.2%;height:35px;border-radius:24px;background:linear-gradient(#080605,#25170e 56%,#5b3e29);box-shadow:0 -2px 2px #b3957466,0 3px 0 #ad8a6a55,inset 0 6px 8px #000,inset 2px 0 3px #000,inset -2px 0 3px #000}.vl-r9-slot-paper{position:relative;z-index:2;box-sizing:border-box;width:86%;margin:0 auto;padding:48px clamp(22px,6%,40px) 40px;color:var(--vl-slot-ink);background:linear-gradient(180deg,#1d100acc,transparent 48px),linear-gradient(105deg,#ffffff08,transparent 44%,#2d140c12),var(--vl-slot-paper);box-shadow:inset 1px 0 #e9be8255,inset -1px 0 #44200b66,0 7px 12px #19070055;clip-path:polygon(0 0,100% 0,100% 99.5%,98% 99.8%,96% 99.5%,94% 100%,92% 99.6%,89% 99.9%,86% 99.6%,83% 100%,80% 99.7%,76% 100%,72% 99.7%,68% 100%,64% 99.6%,60% 99.9%,56% 99.7%,52% 100%,48% 99.7%,44% 100%,40% 99.6%,36% 100%,32% 99.7%,28% 100%,24% 99.7%,20% 100%,16% 99.6%,12% 100%,8% 99.6%,4% 100%,0 99.6%)}.vl-r9-slot-lip{position:absolute;z-index:3;pointer-events:none;top:27px;left:5.5%;right:5.5%;height:13px;border-radius:10px 10px 3px 3px;background:linear-gradient(#170e09,#39271b 55%,#8a6548 63%,#503421);box-shadow:0 7px 9px #180a0980}.vl-r9-slot-note{position:relative;z-index:4;box-sizing:border-box;width:82%;margin:-30px 2% 0 auto;padding:24px;color:#4a1708;background:#d0c4b0;clip-path:polygon(5% 0,98% 0,100% 100%,0 100%);box-shadow:0 4px 8px #20090080}.vl-r9-slot-demo{max-width:658px;padding:30px 0;background:#421103;font-family:RetroSource,sans-serif;font-weight:400}.vl-r9-slot-demo h3{margin:0 0 18px;font-size:24px;font-weight:650}.vl-r9-slot-demo p{margin:0 0 18px;font-size:18px;line-height:1.9}.vl-r9-slot-demo small{font-size:14px}.vl-r9-slot-demo .vl-r9-slot-note p{margin:0}@media(max-width:460px){.vl-r9-slot-note{width:90%;margin:16px auto 0;padding:22px}.vl-r9-slot-paper{width:88%;padding-left:24px;padding-right:24px}}
```

```html
<div class="vl-r9-slot-demo"><section class="vl-r9-slot"><div class="vl-r9-slot-machine" aria-hidden="true"></div><div class="vl-r9-slot-mouth" aria-hidden="true"></div><article class="vl-r9-slot-paper"><h3>街头热红酒领取说明</h3><p>在活动期间选择一家喜欢的小店，购买活动产品后，到店出示实时订单完成验券。</p><p>第一次验券领取纸质地图；沿街收集不同店铺的印章，慢慢拼出你的冬日散步路线。</p><p>纸面是一条独立的长内容流，可以继续增加规则、地址和提示，不限制正文高度。</p><small>未成年人禁止饮酒。</small></article><div class="vl-r9-slot-lip" aria-hidden="true"></div><aside class="vl-r9-slot-note"><p><strong>兑换提醒</strong><br>请以现场开放时间与实际库存为准，并携带可核验的实时订单。</p></aside></section></div>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：shape.recessed-paper-slot。验收限本条声明机制，不代表整页或原始字体精确复刻。


<a id="shape.sloped-deck"></a>

## 斜台面与独立前沿

风格标签：通用。

只含台面轮廓与独立前沿；前沿高度独立于内容与投影。颜色、颗粒、按钮与内部网格由组合绑定。

```css
.cs-deck{position:relative;isolation:isolate;--cs-front-height:40px;--cs-inset:4.3%;--cs-top:#d4d6d9;--cs-front:#9fa4ac}
.cs-deck__top{position:relative;isolation:isolate;padding:20px 7%;min-width:0}
.cs-deck__top::before{content:"";position:absolute;inset:0;z-index:-1;background:var(--cs-top);clip-path:polygon(var(--cs-inset) 0,calc(100% - var(--cs-inset)) 0,100% 100%,0 100%)}
.cs-deck__front{position:relative;box-sizing:border-box;height:var(--cs-front-height);background:var(--cs-front);border-radius:0 0 9px 9px}
```

```html
<div class="cs-deck"><div class="cs-deck__top">操作区内容自然撑高</div><div class="cs-deck__front" aria-hidden="true"></div></div>
```


<a id="shape.thin-sided-key"></a>

## 薄侧边立体按键

风格标签：通用。

键面、薄侧边与承托分离；主体可换圆滑SVG轮廓。原图组合保留已校准的圆滑路径作为覆盖。不是带行为的按钮组件。

```css
.cs-key{position:relative;isolation:isolate;box-sizing:border-box;border:0;background:none;color:inherit;font:inherit;padding:14px 24px 20px;min-height:56px;white-space:normal;overflow-wrap:anywhere;--cs-key-side-height:7px;--cs-key-face:#ddd;--cs-key-side:#999;--cs-key-support:#333}
.cs-key::before,.cs-key::after{content:"";position:absolute;pointer-events:none;clip-path:polygon(6% 0,94% 0,100% 87%,98% 100%,2% 100%,0 87%);border-radius:5px}
.cs-key::before{inset:5px -6px -8px;z-index:-2;background:var(--cs-key-support)}
.cs-key::after{inset:0;z-index:-1;background:linear-gradient(to bottom,var(--cs-key-face) 0,var(--cs-key-face) calc(100% - var(--cs-key-side-height)),var(--cs-key-side) calc(100% - var(--cs-key-side-height)))}
.cs-key:focus-visible{outline:2px solid currentColor;outline-offset:10px}
```

```html
<button type="button" class="cs-key">行动按钮</button>
```
