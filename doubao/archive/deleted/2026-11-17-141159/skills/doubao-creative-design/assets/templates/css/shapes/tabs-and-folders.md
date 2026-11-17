# 页签与文件夹｜形状实现

文件夹轮廓、页签斜坡与背页在本文件维护；[共用参数](containers.md#shapes.parameters)仍在容器参数表。材质与组合分别读取对应条目。

<a id="shape.folder"></a>

## 文件夹：结构与完整轮廓

风格标签：通用。

五个固定 SVG 遮罩片段共用 [assets/svg](../../../svg) 下的 folder-*.svg 文件；半径、页签宽高与斜坡仍由下方 CSS 控制。复制代码时保留 asset: 短引用，组装脚本读取真实 SVG 后再内嵌，无需把遮罩源码带入上下文。

- 保留 --vl-contour/--vl-shape/--vl-outline 和 surface 的完整遮罩；只复制 clip-path 会遗漏背景模糊边界。
- 改变材质时保留这些几何声明。

依赖 [布局与字体](../layouts/layout-and-type.md)、所选 [材质](../surfaces/materials.md) 和 [配色默认值](../colors/palettes.md)。下面只提供轮廓，未固定某种材质。

```html
<article class="vl-folder vl-glass">
  <span class="vl-folder__back" aria-hidden="true"></span>
  <span class="vl-folder__edge" aria-hidden="true"></span>
  <span class="vl-folder__surface" aria-hidden="true"></span>
  <header class="vl-folder__tab">文件夹标题</header>
  <div class="vl-folder__content">
    <span class="vl-tag">标签</span>
    <h2 class="vl-heading">真实标题</h2>
    <p class="vl-copy">真实正文</p>
  </div>
</article>
```

此骨架用于生成阶段组装。正式输出需将 shadow／texture／light 伪元素展开为实际节点，不能把这里的 class-only 骨架当作最终交付；带短引用的行内实例见 [组合源模板](../combinations/material-recipes.html)，预览与正式交付前执行 [资源内嵌](../README.md#svg-assets)。

```css
.vl-folder {
  --vl-border-width: 1.5px;
  --vl-tab-width: 44cqi;
  --vl-tab-height: 36px;
  --vl-slope: 40px;
  --vl-radius: 20px;
  --vl-back-display: block;
  --vl-contour: from var(--vl-radius) 0,
    line to calc(var(--vl-tab-width) - 12px) 0,
    curve to calc(var(--vl-tab-width) + 8px) 8px with var(--vl-tab-width) 0 / calc(var(--vl-tab-width) + 2px) 2px,
    line to calc(var(--vl-tab-width) + var(--vl-slope) - 8px) calc(var(--vl-tab-height) - 8px),
    curve to calc(var(--vl-tab-width) + var(--vl-slope) + 12px) var(--vl-tab-height) with calc(var(--vl-tab-width) + var(--vl-slope) - 2px) calc(var(--vl-tab-height) - 2px) / calc(var(--vl-tab-width) + var(--vl-slope) + 2px) var(--vl-tab-height),
    line to calc(100% - var(--vl-radius)) var(--vl-tab-height),
    curve to 100% calc(var(--vl-tab-height) + var(--vl-radius)) with 100% var(--vl-tab-height),
    line to 100% calc(100% - var(--vl-radius)),
    curve to calc(100% - var(--vl-radius)) 100% with 100% 100%,
    line to var(--vl-radius) 100%,
    curve to 0 calc(100% - var(--vl-radius)) with 0 100%,
    line to 0 var(--vl-radius),
    curve to var(--vl-radius) 0 with 0 0,
    close;
  --vl-shape: shape(var(--vl-contour));
  --vl-outline: shape(evenodd var(--vl-contour),
    move to var(--vl-radius) 2px,
    line to calc(var(--vl-tab-width) - 12px) 2px,
    curve to calc(var(--vl-tab-width) + 8px) 10px with var(--vl-tab-width) 2px / calc(var(--vl-tab-width) + 2px) 4px,
    line to calc(var(--vl-tab-width) + var(--vl-slope) - 8px) calc(var(--vl-tab-height) - 6px),
    curve to calc(var(--vl-tab-width) + var(--vl-slope) + 12px) calc(var(--vl-tab-height) + 2px) with calc(var(--vl-tab-width) + var(--vl-slope) - 2px) var(--vl-tab-height) / calc(var(--vl-tab-width) + var(--vl-slope) + 2px) calc(var(--vl-tab-height) + 2px),
    line to calc(100% - var(--vl-radius)) calc(var(--vl-tab-height) + 2px),
    curve to calc(100% - 1.5px) calc(var(--vl-tab-height) + var(--vl-radius)) with calc(100% - 1.5px) calc(var(--vl-tab-height) + 2px),
    line to calc(100% - 1.5px) calc(100% - var(--vl-radius)),
    curve to calc(100% - var(--vl-radius)) calc(100% - 2.5px) with calc(100% - 1.5px) calc(100% - 2.5px),
    line to var(--vl-radius) calc(100% - 2.5px),
    curve to 1.5px calc(100% - var(--vl-radius)) with 1.5px calc(100% - 2.5px),
    line to 1.5px var(--vl-radius),
    curve to var(--vl-radius) 2px with 1.5px 2px,
    close);
  position: relative;
  container-type: inline-size;
  min-width: 0;
  overflow-wrap: anywhere;
}

.vl-folder::after {
  content: "";
  position: absolute;
  z-index: 0;
  inset: auto 6px 1px;
  height: 36px;
  border-radius: 0 0 var(--vl-radius) var(--vl-radius);
  pointer-events: none;
}

.vl-folder__back {
  position: absolute;
  display: var(--vl-back-display);
  z-index: 0;
  left: calc(var(--vl-tab-width) - 12px);
  right: 9px;
  top: 12px;
  height: calc(var(--vl-tab-height) + 35px);
  border-radius: 13px 13px 0 0;
  pointer-events: none;
}

.vl-folder__edge, .vl-folder__surface {
  position: absolute;
  inset: 0;
  clip-path: var(--vl-shape);
  pointer-events: none;
}

.vl-folder__edge {
  z-index: 1;
  clip-path: var(--vl-outline);
}

.vl-folder__surface {
  z-index: 2;
  inset: 2px 1.5px 2.5px;
  mask-image: url("asset:svg/folder-top-left.svg"),
    linear-gradient(#000,#000),
    url("asset:svg/folder-slope.svg"),
    linear-gradient(#000,#000),
    linear-gradient(#000,#000),
    url("asset:svg/folder-top-right.svg"),
    linear-gradient(#000,#000),
    url("asset:svg/folder-bottom-left.svg"),
    url("asset:svg/folder-bottom-right.svg");
  mask-size: var(--vl-radius) var(--vl-radius),
    calc(var(--vl-tab-width) - var(--vl-radius) - 12px) var(--vl-tab-height),
    calc(var(--vl-slope) + 24px) var(--vl-tab-height),
    var(--vl-radius) calc(100% - var(--vl-radius) * 2),
    calc(100% - var(--vl-radius) * 2) calc(100% - var(--vl-tab-height)),
    var(--vl-radius) var(--vl-radius),
    var(--vl-radius) calc(100% - var(--vl-tab-height) - var(--vl-radius) * 2),
    var(--vl-radius) var(--vl-radius),
    var(--vl-radius) var(--vl-radius);
  mask-position: left 0 top 0,
    left var(--vl-radius) top 0,
    left calc(var(--vl-tab-width) - 12px) top 0,
    left 0 top var(--vl-radius),
    left var(--vl-radius) top var(--vl-tab-height),
    right 0 top var(--vl-tab-height),
    right 0 top calc(var(--vl-tab-height) + var(--vl-radius)),
    left 0 bottom 0,
    right 0 bottom 0;
  mask-repeat: no-repeat;
}

.vl-folder__tab {
  position: absolute;
  z-index: 3;
  top: 12px;
  left: 22px;
  max-width: calc(var(--vl-tab-width) - 28px);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.vl-tag {
  border-radius: 5px;
}
```

<a id="decoration.back-sheet"></a>

## 文件夹背页

风格标签：通用。

背页 `.vl-folder__back` 的完整几何已包含在上面的文件夹代码中，依赖 `shape.folder`。颜色通过 `--vl-accent` 控制，`--vl-back-display:none` 可关闭；不要单独复制到圆角容器。

边缘高光的强度和阴影控制位于 [材质与光照](../surfaces/materials.md)。其他纸张辅件按其独立条目选用。
