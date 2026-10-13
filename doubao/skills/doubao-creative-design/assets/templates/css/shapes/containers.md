# 容器形状｜参数与实现

[返回使用说明](../README.md)。本文件保存该分类的真实参数、默认值与代码；无需从 catalog 查找参数值。CSS 代码块是维护源，生成正式 HTML 时按现有协议展开为行内声明。

<a id="shapes.parameters"></a>

## 参数表

风格标签：通用（共用实现或组合规则，非独立风格预设）。

| 参数 | 实现默认值 | 类型／调整范围 | 作用与限制 |
|---|---|---|---|
| `--vl-radius` | `20px` | length | 圆角半径；圆角容器建议不小于 2px；文件夹须保持遮罩尺寸为正 |
| `--vl-tab-width` | `44cqi` | length；['cqi', 'px'] | 页签宽度；不用 %，1cqi 为卡片宽度的 1% |
| `--vl-tab-height` | `36px` | length | 页签高度 px；随轮廓检查遮罩 |
| `--vl-slope` | `40px` | length | 页签斜坡宽度 px |
| `--vl-back-display` | `block` | enum；['block', 'none'] | 文件夹背页开关 |
| `--vl-border-width` | `1.5px` | length | 圆角及显式引用该值的轮廓边框；文件夹 mask 不读取此值 |

默认轮廓是文件夹，`.vl-rounded` 修饰类改为原生圆角。两者共用 `.vl-folder` 根容器与内容结构，材质另外选择。几何参数变化时须保留内外轮廓、表面遮罩与正文避让的关系。

文件夹、页签与背页实现见[文件夹形状](tabs-and-folders.md#shape.folder)。

<a id="shape.rounded"></a>

## 圆角容器：明确的几何覆盖

风格标签：通用。

先读取[文件夹基础结构](tabs-and-folders.md#shape.folder)，再使用根类 `.vl-folder vl-rounded vl-glass`（材质类可换）。不放 back 与 tab，内部保留 edge、surface、content。`--vl-border-width` 只在这个形状中生效。

```css
.vl-rounded .vl-folder__edge {
  clip-path: none;
  background: none;
  border-radius: var(--vl-radius);
  border: var(--vl-border-width) solid color-mix(in srgb, var(--vl-edge-color) calc(var(--vl-edge) * 100%), transparent);
}
.vl-rounded .vl-folder__surface {
  clip-path: none;
  mask-image: none;
  inset: calc(var(--vl-border-width) + .5px) var(--vl-border-width) calc(var(--vl-border-width) + 1px);
  border-radius: calc(var(--vl-radius) - var(--vl-border-width));
}
```

