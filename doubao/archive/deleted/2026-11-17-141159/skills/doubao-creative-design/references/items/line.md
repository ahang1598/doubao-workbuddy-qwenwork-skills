# `LINE`

线段 Item。内容分支为 `<line>`。用于分隔线、连接线和指向关系。

## 字段

```xml
<item item_id="700" type="LINE" path="/deliverables" title="引导曲线" brief="从人物指向标题的引导曲线">
  <size width="520" height="160" />
  <line line_kind="bezier">
    <points>
      <point x="0" y="0.8" control_out_x="0.22" control_out_y="0.05" />
      <point x="1" y="0.2" control_in_x="0.72" control_in_y="0.95" />
    </points>
    <stroke width="5" style="dash-dot" line_cap="round">
      <paint color="#6366F1" opacity="1" />
    </stroke>
    <start_arrow kind="circle" width_scale="1" length_scale="1" />
    <end_arrow kind="arrow" width_scale="1.2" length_scale="1.2" />
  </line>
</item>
```

### `<line>`

| 字段 | 必填 | 说明 |
|---|---:|---|
| `line_kind` | 是 | `straight` / `bezier` |
| `points` | 是 | 端点与控制点 |
| `stroke` | 是 | 描边 |
| `start_arrow` | 否 | 起点箭头 |
| `end_arrow` | 否 | 终点箭头 |

### `<stroke>`

| 字段 | 说明 |
|---|---|
| `width` | `1..20` |
| `style` | `solid` / `dash` / `dot` / `dash-dot` / `short-dash` / `long-dash` / `dash-dot-dot` |
| `line_cap` | `butt` / `round` / `square`，缺省 `butt` |
| `line_join` | `miter` / `round` / `bevel`，缺省 `round` |
| `miter_limit` | 大于 0，建议 `1.32`，缺省 `4` |
| `paint` | 颜色与透明度 |

本模块使用上述已列明的 7 个 LINE 描边样式；不要由 SHAPE 的 14 个样式或 `0..64` 范围推断 LINE 同样支持。LINE 暂沿用 `1..20` 的生成范围，扩展值须验证目标 Renderer。

### 箭头

| 字段 | 说明 |
|---|---|
| `kind` | `none` / `arrow` / `triangle` / `diamond` / `circle` / `square` / `stealth` |
| `width_scale` | `0.4..4`，缺省 `1` |
| `length_scale` | `0.4..4`，缺省 `1` |

未写箭头节点时没有装饰；新建修改版本要清除已有箭头时，显式写 `kind="none"`，不要依赖省略节点清除旧值。

`bar` 与 `open-arrow` 在历史表格和示例中的口径不一致，当前不列入默认生成集合。确需使用时，先验证目标 Renderer 并记录其版本与结果；不能仅凭旧本地渲染器或本文历史示例认定支持。上表为设计侧生成集合，非已取得 SDK／前端注册表验证的完整枚举。

## 坐标：`<point>` 是归一化的

**`point` 的 `x` / `y` 是相对 `transform` 紧包围盒的 `0..1` 归一化坐标，不是像素值。**

这是 `LINE` 最容易写错的地方。Frame 内坐标按下式还原：

```text
frame_x = transform.x + point.x × transform.width
frame_y = transform.y + point.y × transform.height
```

从两个 Frame 内坐标端点 `A(ax, ay)`、`B(bx, by)` 反算：

```text
box_x      = min(ax, bx)
box_y      = min(ay, by)
box_width  = max(abs(bx - ax), 1)
box_height = max(abs(by - ay), 1)

point_a.x = (ax - box_x) / box_width
point_a.y = (ay - box_y) / box_height
point_b.x = (bx - box_x) / box_width
point_b.y = (by - box_y) / box_height
```

Frame 成员的 `transform` 就是这个紧包围盒；顶层 LINE 用 `<size width height>` 表达其宽高，不写位置；水平或垂直方向的最小尺寸取 `1`。

成员的 `transform.rotation` 固定为 `0` —— 旋转已经体现在点位里。

### 算例

`1080 × 1440` 画布上，从 `(10%, 50%)` 到 `(90%, 50%)` 的水平线：

```text
世界端点   (108, 720) → (972, 720)
紧包围盒   x=108  y=720  width=864  height=1
相对点位   (0, 0) → (1, 0)
```

```xml
<line line_kind="straight">
  <points>
    <point x="0" y="0"/>
    <point x="1" y="0"/>
  </points>
  <stroke width="2">
    <paint color="#334155" opacity="1"/>
  </stroke>
</line>
```

对应 `<transform>` 为 `x=108 y=720 width=864 height=1`。

## 带箭头的指向线

从左上指向右下，终点带实心箭头：

```xml
<item item_id="701" type="LINE" path="/script" title="场景流程箭头" brief="从场景 A 指向场景 B 的流程箭头">
  <size width="600" height="40" />
  <line line_kind="straight">
    <points>
      <point x="0" y="0" />
      <point x="1" y="1" />
    </points>
    <stroke width="3" style="solid" line_cap="round">
      <paint color="#334155" opacity="1" />
    </stroke>
    <end_arrow kind="arrow" width_scale="1" length_scale="1" />
  </line>
</item>
```

## 贝塞尔

`line_kind` 为 `bezier` 时，`point` 可带控制点：

| 字段 | 说明 |
|---|---|
| `control_in_x` / `control_in_y` | 入控制点 |
| `control_out_x` / `control_out_y` | 出控制点 |

控制点同样是 `0..1` 归一化坐标。紧包围盒必须**同时纳入全部锚点和控制点**，不能只按起止点算——否则控制点会落到 `0..1` 之外。

```xml
<line line_kind="bezier">
  <points>
    <point x="0" y="0.8" control_out_x="0.22" control_out_y="0.05"/>
    <point x="1" y="0.2" control_in_x="0.72" control_in_y="0.95"/>
  </points>
  <stroke width="2">
    <paint color="#334155" opacity="1"/>
  </stroke>
</line>
```

## 注意

- **不要用超薄 `rect` 模拟线条**。分隔线、连接线、指向关系一律用 `LINE`。
- 所有归一化结果必须落在 `0..1`。算出界说明包围盒取错了，回去重算，不要 clamp。
- 水平线的 `transform.height` 取 `1`，垂直线的 `width` 取 `1`——不能为 `0`。
