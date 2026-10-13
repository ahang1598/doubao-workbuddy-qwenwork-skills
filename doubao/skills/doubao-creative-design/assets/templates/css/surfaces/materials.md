# 材质与光照｜参数与实现

[返回使用说明](../README.md)。本文件保存该分类的真实参数、默认值与代码；无需从 catalog 查找参数值。CSS 代码块是维护源，生成正式 HTML 时按现有协议展开为行内声明。

<a id="surfaces.parameters"></a>

## 参数表

风格标签：通用（共用实现或组合规则，非独立风格预设）。

| 参数 | 实现默认值 | 类型／调整范围 | 作用与限制 |
|---|---|---|---|
| `--vl-grain` | `.14` | number；[0, 0.85] | 纹理强度；0 关闭纹理 |
| `--vl-texture-size` | `192px` | length；['96px', '384px'] | 平铺尺寸，越大颗粒越粗 |
| `--vl-alpha` | `.72` | number；[0, 1] | 表面不透明度，不作用于正文 |
| `--vl-blur` | `8px` | length | 背景模糊半径，非负 px |
| `--vl-highlight` | `.5` | number；[0, 1] | 材质光照强度 |
| `--vl-edge` | `.88` | number；[0, 1] | 亮边强度 |
| `--vl-shadow` | `0` | number；[0, 1] | 外投影强度；默认关闭，按接触／悬浮关系启用 |
| `--vl-texture-blend` | `soft-light` | enum；['soft-light', 'multiply'] | 随材质成组复制，非通用换肤开关 |
| `--vl-texture-size-x` | `var(--vl-texture-size)` | length | 横向平铺尺寸；默认跟随统一尺寸 |
| `--vl-texture-size-y` | `var(--vl-texture-size)` | length | 纵向平铺尺寸；可拉长纤维外观，不能改变纤维数量 |
| `--vl-texture-x` | `0px` | length | 纹理平铺横向偏移 |
| `--vl-texture-y` | `0px` | length | 纹理平铺纵向偏移 |
| `--vl-light-angle` | `112deg` | angle | 塑料/玻璃主高光方向；纸张使用径向光源位置 |
| `--vl-light-width` | `36%` | percentage | 塑料/玻璃主高光宽度，建议 12%–70% |
| `--vl-light-softness` | `0px` | length | 光层模糊半径，不模糊文字 |
| `--vl-light-x` | `20%` | percentage | 纸张径向光源横向位置 |
| `--vl-light-y` | `10%` | percentage | 纸张径向光源纵向位置 |
| `--vl-shadow-x` | `0px` | length | 外投影横向偏移 |
| `--vl-shadow-y` | `2px` | length | 外投影纵向偏移 |
| `--vl-shadow-blur` | `5px` | length | 外投影模糊半径，非负 |
| `--vl-shadow-spread` | `0px` | length | 外投影扩散，可为负；与偏移、模糊共同控制同一层投影 |

这些值只作用于表面，不降低或模糊正文。形状与材质均不自动启用外投影，纸张、塑料和玻璃默认关闭。纸纤维、印刷颗粒不代表纸片悬浮；只有真实叠纸接触或实体悬浮时，才按光向、对象尺度、接触距离与背景设置投影；不使用大面积黑色渐变作通用底影。内高光／内阴影用于材质厚度，与外投影分别控制。已有烘焙阴影的图像不重复启用外投影。

| 材质 | alpha | blur | grain（轻／强） | texture-size | highlight | edge | shadow |
|---|---|---|---|---|---|---|---|
| 塑料 | .72 | 8px | .14／.36 | 192px | .60 | .96 | 0 |
| 玻璃 | .24 | 18px | .18／.48 | 176px | .40 | .95 | 0 |
| 纸张 | .97 | 0px | .36／.70 | 256px | .16 | .45 | 0 |

## 快速调整

玻璃较轻：根节点使用 `--vl-grain:.12; --vl-blur:12px`。细纹拉长：使用 `--vl-texture-size-x:160px; --vl-texture-size-y:280px`。这些参数调的是叠加强度与平铺尺度，不是 SVG 里的纤维数量。

<a id="surfaces.base"></a>

## 共用表面、纹理叠层与光照实现

风格标签：通用（共用实现或组合规则，非独立风格预设）。

SVG 源码分别保存为 [塑料纹理](../../../svg/plastic-grain.svg)、[磨砂纹理](../../../svg/frosted-grain.svg)、[纸纤维](../../../svg/paper-fiber.svg)。下面只引用资源；常规调参不读取 SVG。交付时按 [内嵌步骤](../README.md#svg-assets) 处理。

```css
.vl-folder {
  --vl-texture-size-x: var(--vl-texture-size);
  --vl-texture-size-y: var(--vl-texture-size);
  --vl-texture-x: 0px;
  --vl-texture-y: 0px;
  --vl-light-angle: 112deg;
  --vl-light-width: 36%;
  --vl-light-softness: 0px;
  --vl-light-x: 20%;
  --vl-light-y: 10%;
  --vl-shadow-x: 0px;
  --vl-shadow-y: 2px;
  --vl-shadow-blur: 5px;
  --vl-shadow-spread: 0px;
  --vl-alpha: .72;
  --vl-blur: 8px;
  --vl-grain: .14;
  --vl-texture-size: 192px;
  --vl-texture-blend: soft-light;
  --vl-texture: url("asset:svg/plastic-grain.svg");
  --vl-edge: .88;
  --vl-shadow: 0;
  --vl-highlight: .5;
}

.vl-folder, .vl-folder *, .vl-folder *::before, .vl-folder *::after {
  box-sizing: border-box;
}

.vl-folder::after {
  box-shadow: var(--vl-shadow-x) var(--vl-shadow-y) var(--vl-shadow-blur) var(--vl-shadow-spread) color-mix(in srgb, var(--vl-shadow-color) calc(var(--vl-shadow) * 100%), transparent);
}

.vl-folder__edge {
  background: linear-gradient(155deg, color-mix(in srgb, var(--vl-edge-color) calc(var(--vl-edge) * 100%), transparent), color-mix(in srgb, var(--vl-edge-color) calc(var(--vl-edge) * 35%), transparent) 65%, hsl(var(--vl-hue) 95% 65% / var(--vl-edge)));
}

.vl-folder__surface {
  background: linear-gradient(150deg, color-mix(in srgb, var(--vl-tint) calc(var(--vl-alpha) * 100%), transparent), color-mix(in srgb, var(--vl-surface-end) calc(var(--vl-alpha) * 100%), transparent));
  backdrop-filter: blur(var(--vl-blur)) saturate(1.25);
  box-shadow: inset 0 -3px 0 hsl(var(--vl-hue) 90% 55% / .14);
}

.vl-folder__surface::before, .vl-folder__surface::after {
  content: "";
  position: absolute;
  inset: 0;
}

.vl-folder__surface::before {
  z-index: 1;
  opacity: var(--vl-grain);
  background-image: var(--vl-texture);
  background-size: var(--vl-texture-size-x) var(--vl-texture-size-y);
  background-position: var(--vl-texture-x) var(--vl-texture-y);
  background-repeat: repeat;
  mix-blend-mode: var(--vl-texture-blend);
}

.vl-folder__surface::after {
  opacity: var(--vl-highlight);
  filter: blur(var(--vl-light-softness));
  background: linear-gradient(var(--vl-light-angle), transparent 6%, color-mix(in srgb, var(--vl-light-color) 60%, transparent) calc(6% + var(--vl-light-width) * 13 / 36), color-mix(in srgb, var(--vl-light-color) 6.666667%, transparent) calc(6% + var(--vl-light-width) * 24 / 36), transparent calc(6% + var(--vl-light-width))),
    linear-gradient(160deg, #fffa, transparent 29%, transparent 70%, #fff6),
    linear-gradient(0deg, #fff7, transparent 7%);
  box-shadow: inset 0 2px 1px #fffc, inset 0 -5px 8px hsl(var(--vl-hue) 70% 32% / .18);
}
```

半透明塑料覆盖见[塑料材质](plastic-and-gel.md#material.plastic)，与本文件共用层一起使用。

<a id="material.glass"></a>

## 磨砂玻璃

风格标签：通用。

- 材质替换同时复制 root 材质变量、surface 表面声明及 texture/light 两个子层；保留目标形状的几何声明。
- 仅调 grain/alpha/blur 不会把一种纹理变成另一种材质。
- 毛玻璃与透明效果依赖背景；背后有图像或色块时再判断模糊强度。

共用层与下面的材质层一起使用；纹理以 asset:svg 引用本地资源，正式 HTML 按内嵌步骤展开。

```css
.vl-glass {
  --vl-shadow: 0;
  --vl-alpha: .24;
  --vl-blur: 18px;
  --vl-grain: .18;
  --vl-edge: .95;
  --vl-highlight: .40;
  --vl-texture-size: 176px;
  --vl-texture: url("asset:svg/frosted-grain.svg");
}
```

<a id="material.paper"></a>

## 纤维纸张

风格标签：通用。

- 材质替换同时复制 root 材质变量、surface 表面声明及 texture/light 两个子层；保留目标形状的几何声明。
- 仅调 grain/alpha/blur 不会把一种纹理变成另一种材质。
- 纸张颜色同时调整 tint 与 ink；使用 multiply 纹理与漫反射 light。

共用层与下面的材质层一起使用；纹理以 asset:svg 引用本地资源，正式 HTML 按内嵌步骤展开。

```css
.vl-paper {
  --vl-alpha: .97;
  --vl-blur: 0px;
  --vl-grain: .36;
  --vl-edge: .45;
  --vl-highlight: .16;
  --vl-shadow: 0;
  --vl-texture-size: 256px;
  --vl-texture-blend: multiply;
  --vl-texture: url("asset:svg/paper-fiber.svg");
}

.vl-paper .vl-folder__surface::after {
  background: radial-gradient(ellipse at var(--vl-light-x) var(--vl-light-y), color-mix(in srgb, var(--vl-light-color) 53.333333%, transparent), transparent 65%), linear-gradient(0deg, #92774b44, transparent 8%);
  box-shadow: inset 0 1px 1px #fff9, inset 0 -3px 3px #80674722;
}

.vl-paper .vl-folder__surface {
  background: color-mix(in srgb, var(--vl-tint) calc(var(--vl-alpha) * 100%), transparent);
}
```

<a id="decoration.edge"></a>

## 亮边

风格标签：通用。

参数 `--vl-edge` 与 `--vl-edge-color`；文件夹亮边背景在共用 `.vl-folder__edge` 规则中，轮廓来自 shapes。圆角亮边由 shapes 中的原生 border 实现。强度设为 0 可关闭，不改形状遮罩。

<a id="decoration.shadow"></a>

## 底部投影

风格标签：通用。

根伪元素 `.vl-folder::after` 的 box-shadow 位于共用代码。`--vl-shadow` 控制强度，x／y／blur／spread／color 控制环境投影；接触阴影和材质内阴影保持各自职责。默认强度为 0；启用须说明哪个实体向哪个承接面投影，不因选择纸张、胶囊或卡片形状而开启。

<a id="surfaces.svg-generation"></a>

## SVG 生成阶段参数

风格标签：通用（共用实现或组合规则，非独立风格预设）。

| 参数 | 类型 | 修改目标 | 作用 |
|---|---|---|---|
| `noise_frequency` | number-pair | `feTurbulence@baseFrequency` | 噪声空间频率，非 CSS 平铺尺寸；两轴可不同 |
| `noise_seed` | integer | `feTurbulence@seed` | 固定噪声随机种子，重复生成保留该值 |
| `noise_octaves` | integer | `feTurbulence@numOctaves` | 噪声细节层数，通常 1–3，增加时检查渲染开销 |
| `fiber_density` | number | `paper SVG 纤维图形数量/平铺面积` | 重新生成矢量纤维分布，不靠 opacity 代替密度 |
| `fiber_length_width` | length-pair | `paper SVG 纤维图形几何与笔画` | 修改纤维长宽，不同时缩放整张纹理 |
| `fiber_direction` | angle | `paper SVG 纤维图形坐标/旋转` | 控制纤维方向；修改后保持可平铺边界 |
| `geometry_seed` | integer | `生成阶段的伪随机几何算法` | 记录到现有 HTML 实现，用于复现纤维位置；与 feTurbulence seed 分开 |

1. 只有改变滤镜或纤维几何时，读取选中资源的 SVG 源文件；只改 grain、平铺尺寸、颜色时不需要读取。
2. 没有匹配节点时先检查真实 SVG 结构，不能虚构参数已应用。记录生成参数与随机种子到现有 HTML 实现。
3. 保留 SVG 命名空间、滤镜 ID 引用与平铺设置，保存为 SVG；编码交给内嵌脚本，不在模型上下文中手工编码。
4. 项目独有纹理修改使用任务 assets 副本与脚本的 --asset-root；维护共用库时更新对应 SVG，保留现有短引用即可。资源重命名时同步正文与模板引用。
5. 不把 SVG 内部控制写为外层 CSS 自定义属性；生成后检查平铺接缝和目标渲染器。最终 HTML 自包含，不依赖构建时资源路径或网络。

<a id="surfaces.texture-field"></a>

## 独立背景的共用纹理层

风格标签：通用（共用实现或组合规则，非独立风格预设）。

用于没有文件夹或卡片骨架的页面／纸片背景。纸纤维与屏幕颗粒共用本层，只覆盖纹理资源；grain、texture-size、texture-blend 仍由本文件参数表定义。

```css
.vl-texture-field { position:relative; isolation:isolate; background:var(--vl-tint,transparent); color:var(--vl-ink,#302a20); }
.vl-texture-field__texture { position:absolute; inset:0; z-index:-1; pointer-events:none; border-radius:inherit; background-image:var(--vl-texture,none); background-size:var(--vl-texture-size-x,var(--vl-texture-size,256px)) var(--vl-texture-size-y,var(--vl-texture-size,256px)); background-position:var(--vl-texture-x,0px) var(--vl-texture-y,0px); opacity:var(--vl-grain,.12); mix-blend-mode:var(--vl-texture-blend,multiply); }
```

```html
<section class="vl-texture-field" style="--vl-texture:url('asset:svg/paper-fiber.svg');--vl-grain:.12"><span class="vl-texture-field__texture" aria-hidden="true"></span><h2>正文保持清晰</h2></section>
```

纹理与底色分开选择：本层未传 --vl-tint 时保持透明，纹理覆盖在已规划的下层表面；需要不透明纸面时显式传入表面色及配套文字色。纸纤维、颗粒与纸张名称都不自动指定米色。

纹理 span 和内容必须分层。CSS 光场同时使用时保留另一个光层节点，由 HTML 实现 指定两层顺序；照片自带纹理时不重复覆盖。资源交付仍经过 SVG 内嵌脚本。
