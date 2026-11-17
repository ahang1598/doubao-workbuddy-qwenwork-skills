# 文字挤出与浮雕近似

状态：近似实现。数值为可调起点，不是参考图原始源参数。

<a id="surface.type-relief"></a>

## 文字挤出与浮雕近似

风格标签：通用。

对应球面徽章上的厚字和金色标题。四层硬阴影近似挤出深度，字面与侧面分层，避免透明渐变字面被阴影覆盖。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-text-depth-x` | `3px` | 最远侧面横向位移，可负值 |
| `--vl-text-depth-y` | `4px` | 最远侧面纵向位移，可负值 |
| `--vl-text-side-color` | `#063870` | 挤出侧面色 |
| `--vl-text-contact-color` | `#001a40` | 最后一层接触阴影色 |
| `--vl-text-contact-blur` | `1px` | 接触层柔化；硬边挤出保持其余层 blur=0 |

```css
.vl-type-relief { display:inline-grid; isolation:isolate; }
.vl-type-relief__depth,.vl-type-relief__face { grid-area:1/1; font:inherit; letter-spacing:inherit; line-height:inherit; text-align:inherit; }
.vl-type-relief__depth { z-index:0; color:var(--vl-text-side-color,#063870); text-shadow:calc(var(--vl-text-depth-x,3px) * .25) calc(var(--vl-text-depth-y,4px) * .25) 0 var(--vl-text-side-color,#063870),calc(var(--vl-text-depth-x,3px) * .5) calc(var(--vl-text-depth-y,4px) * .5) 0 var(--vl-text-side-color,#063870),calc(var(--vl-text-depth-x,3px) * .75) calc(var(--vl-text-depth-y,4px) * .75) 0 var(--vl-text-side-color,#063870),var(--vl-text-depth-x,3px) var(--vl-text-depth-y,4px) var(--vl-text-contact-blur,1px) var(--vl-text-contact-color,#001a40); }
.vl-type-relief__face { z-index:1; }
```

```html
<h2 class="vl-type-relief"><span class="vl-type-relief__depth" aria-hidden="true">立体字面</span><span class="vl-type-relief__face vl-gradient--linear vl-text-paint" style="--vl-gradient-stops:#d8faff 0%,#46c3f7 45%,#237dc1 100%">立体字面</span></h2>
```

两层文字必须同源、同字体、同换行；装饰侧面设 aria-hidden，不能独立手工修改成另一段文案。建议大字使用，depth 超过约 6px 时四层近似可能出现台阶，需要增加阴影采样或改为专门的立体素材。此实现没有真实照明、透视挤压或字体轮廓重建。

<a id="surface.metal-bands"></a>

## 金属反光带近似

风格标签：通用。

金色标题使用窄亮带与深浅反差近似金属反光，复用 [通用渐变](../colors/palettes.md#color.gradient)；应用于文字时再加 [填字](../layouts/layout-and-type.md#text.paint)，应用于框面时用 paint-fill。

```json
{
  "id": "surface.metal-bands",
  "base": "color.gradient",
  "selector": "vl-gradient--linear",
  "overrides": {
    "--vl-gradient-angle": "105deg",
    "--vl-gradient-stops": "#704018 0%,#bf8538 22%,#fff4bd 35%,#d5a74d 44%,#8a5420 58%,#ffe9a0 76%,#b57529 100%"
  }
}
```

调整亮带的位置、宽度与方向即可改变反光。透明度在各色标中配置。真实丝绸、鱼油液滴、复杂金属倒影仍是素材，不把该渐变称为物理材质复现。
