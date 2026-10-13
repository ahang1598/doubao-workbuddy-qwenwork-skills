# `SHAPE`

基础图形 Item。内容分支为 `<shape>`。

## 字段

```xml
<item item_id="561" type="SHAPE" path="/deliverables/poster" title="蓝色外框" brief="「窗」字主视觉的蓝色外框">
  <size width="960" height="520" />
  <shape shape_kind="round-rect" corner_radius="24">
    <fill color="#1B4D8F" opacity="1" />
    <stroke width="3" style="solid" line_cap="round" line_join="round" miter_limit="4">
      <paint color="#0F2E56" opacity="1" />
    </stroke>
  </shape>
</item>
```

### `<shape>`

| 字段 | 必填 | 说明 |
|---|---:|---|
| `shape_kind` | 是 | 图形类型，见下表 |
| `fill` | 否 | 填充 |
| `stroke` | 否 | 描边 |
| `corner_radius` | 否 | 圆角半径，画布世界单位；只对 `rect` / `round-rect` 有效 |
| `adjustments` | 否 | 几何调节参数，见下方 `<adjustments>` 一节 |

`corner_radius` 取值 `0..min(width,height)/2`，**只对 `rect` / `round-rect` 生效** ——
不要给 `ellipse` / `star5` / 箭头等图形写这一格。

### `<adjustments>`

几何调节参数，值都是**相对比例**。只给支持该 key 的 `shape_kind` 设置；不写用默认值，
越界值会被前端限制到支持范围。不要给不支持 adjustments 的图形写任意 key。

```xml
<shape shape_kind="star5">
  <fill color="#FDE68A" opacity="1"/>
  <adjustments>
    <adjustment key="inner_radius_ratio" value="0.45"/>
  </adjustments>
</shape>
```

| key | 适用 `shape_kind` | 控制什么 | 范围 / 默认 |
|---|---|---|---|
| `cap_ratio` | `can` | 上下椭圆端面的高度；越大端面越高、直边区越短 | 0.08–0.32 / 0.17 |
| `notch_ratio` | `chevron` | 左侧 V 形凹口的切入深度；越大越尖锐 | 0.15–0.55 / 0.35 |
| `tip_ratio` | `home-plate` | 右侧尖头占总宽的比例；越大尖头越长 | 0.15–0.65 / 0.33 |
| `slant_ratio` | `parallelogram` | 上下边错开的比例；越大侧边越斜 | 0–0.45 / 0.23 |
| `inset_ratio` | `trapezoid` | 顶部两角向内收缩的比例；越大顶边越短 | 0–0.45 / 0.23 |
| `apex_ratio` | `triangle` | 顶点的水平位置；0 最左、0.5 居中、1 最右 | 0–1 / 0.5 |
| `inner_radius_ratio` | `star5` | 内侧凹点相对外半径的距离；越小尖角越细越深 | 0.15–0.8 / 0.45 |
| `cut_ratio` | `hexagon` | 左右斜边的切入比例；越大斜边越长 | 0.08–0.42 / 0.23 |
| `cut_ratio` | `octagon` | 四角被切掉的比例 | 0.08–0.42 / 0.278 |
| `shaft_ratio` | `left/right/up/down-arrow` | 箭身粗细比例；不改变箭头长度 | 0.15–0.85 / 0.45 |
| `head_ratio` | `left/right/up/down-arrow` | 箭头尖部占总长的比例；越大箭身越短 | 0.18–0.7 / 0.37 |
| `arm_ratio` | `cross` | 横臂与竖臂的统一宽度 | 0.15–0.75 / 0.33 |

### `<fill>` 与 `<stroke><paint>`

| 字段 | 说明 |
|---|---|
| `color` | `#RRGGBB` |
| `opacity` | `0..1` |
| `gradient` | 渐变，有值时优先于 `color` |

### `<stroke>`

| 字段 | 说明 |
|---|---|
| `width` | `0..64`；`0` 表示不显示描边 |
| `style` | 见下表；优先用不带 `sys-` 前缀的规范值 |
| `paint` | 描边颜色 |
| `line_cap` | `butt` / `round` / `square` —— 线端或每个 dash 的端帽 |
| `line_join` | `miter` / `round` / `bevel` —— 折角连接方式 |
| `miter_limit` | `1..32`，默认 `4`；仅 `miter` 生效，限制尖角延伸 |

本模块统一采用 `0..64` 的设计侧描边范围；`0` 隐藏描边。该范围与下表样式是本 Skill 的生成约定，不是 SDK／目标 Renderer 已验证范围的证明；目标端能力不符时以其实际支持范围为准。

`style` 的 14 个规范值：

| 分组 | 取值 |
|---|---|
| 实线 | `solid` |
| 虚线 | `short-dash` / `dash` / `long-dash` |
| 点线 | `dot` / `round-dot` |
| 点划线 | `dash-dot` / `long-dash-dot` / `dash-dot-dot` / `long-dash-dot-dot` |
| 系统变体 | `sys-dot` / `sys-dash` / `sys-dash-dot` / `sys-dash-dot-dot` |

未知 `style` 当前按 `solid` 兜底，但不要依赖这个行为。`dashed` / `dotted` 是旧别名，不要写。

即使不需要描边也建议保留合法的 `paint` 颜色，`width` 给 `0`。

## `shape_kind` 取值

| `shape_kind` | 视觉语义 | 尺寸建议 |
|---|---|---|
| `rect` | 矩形 | 任意比例；可用 `corner_radius` |
| `round-rect` | 圆角矩形 | 任意比例；圆角用 `corner_radius` |
| `circle` | 圆形 | `width = height` |
| `ellipse` | 椭圆 | 任意比例 |
| `diamond` | 菱形 | 接近 1:1 |
| `triangle` | 三角形 | 接近 1:1 |
| `rt-triangle` | 直角三角形 | 接近 1:1 |
| `pentagon` | 五边形 | 接近 1:1 |
| `hexagon` | 六边形 | 接近 1:1 |
| `octagon` | 八边形 | 接近 1:1 |
| `star5` | 五角星 | `width = height` |
| `heart` | 心形 | 接近 1:1 |
| `cross` | 十字形 | 接近 1:1 |
| `cloud` | 云朵 | 横向 |
| `can` | 圆柱形 | 竖向或接近 1:1 |
| `chevron` | 右向 V 形 | 横向 |
| `home-plate` | 本垒板形 | 横向 |
| `parallelogram` | 平行四边形 | 横向 |
| `trapezoid` | 梯形 | 横向 |
| `left-arrow` | 左箭头 | `width > height` |
| `right-arrow` | 右箭头 | `width > height` |
| `up-arrow` | 上箭头 | `height > width` |
| `down-arrow` | 下箭头 | `height > width` |
| `wedge-ellipse-callout` | 椭圆气泡 | 任意比例 |
| `wedge-round-rect-callout` | 圆角矩形气泡 | 任意比例 |

比例敏感的图形要按建议给尺寸：`circle` 宽高不等会渲染成椭圆，`star5` 同理；箭头方向要与宽高关系一致。

这份取值来自设计侧已验证的实践集合，尚未经前端注册表正式确认。用表外值前先确认渲染支持。

## 渐变

`fill` 与 `stroke.paint` 都支持：

```xml
<shape shape_kind="star5">
  <fill color="#FDE68A" opacity="1">
    <gradient kind="radial" center_x="0.35" center_y="0.3" radius="0.8">
      <stops>
        <stop offset="0" color="#FFF7AE" opacity="1"/>
        <stop offset="1" color="#F472B6" opacity="1"/>
      </stops>
    </gradient>
  </fill>
  <adjustments>
    <adjustment key="inner_radius_ratio" value="0.45"/>
  </adjustments>
</shape>
```

| 字段 | 说明 |
|---|---|
| `kind` | `linear` / `radial` |
| `stops` / `stop` | 色标，`offset` 取值 `0..1` |
| `angle` | 线性渐变角度，单位度 |
| `center_x` / `center_y` | 径向渐变中心比例，缺省 `0.5` |
| `radius` | 径向渐变半径比例，缺省 `0.5` |

径向渐变：

```xml
<fill color="#FFFFFF" opacity="1">
  <gradient kind="radial" center_x="0.5" center_y="0.35" radius="0.6">
    <stops>
      <stop offset="0" color="#FFFFFF" opacity="1"/>
      <stop offset="1" color="#93C5FD" opacity="0.9"/>
    </stops>
  </gradient>
</fill>
```

## 最小示例

纯色矩形，无描边：

```xml
<item item_id="560" type="SHAPE" path="/deliverables/poster" title="海报底色" brief="海报的深蓝底色">
  <size width="1920" height="1080" />
  <shape shape_kind="rect">
    <fill color="#0F172A" opacity="1" />
  </shape>
</item>
```

## 注意

- **`SHAPE` 不承载文字**。标题、按钮文案、数字、标签、Emoji 都要建独立 [`TEXT`](text.md)，坐标覆盖在上方且 `z_index` 更高。
- **分隔线、连接线不要用超薄 `rect` 模拟**，用 [`LINE`](line.md)。
- 阴影没有专门字段。用主图形下方 1–3 个低透明、错位的 `SHAPE` 近似，统一光源方向。
- 大背景先建（`z_index` 小），小装饰与文字后建（`z_index` 大）。
- 复杂异形、非对称圆角、撕边这类形态超出 `shape_kind` 表达能力，用抠好的透明 PNG 作 [`IMAGE`](image.md)。
