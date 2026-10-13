# `TEXT`

文本 Item。内容分支为 `<inline>`。

## 字段

```xml
<item item_id="563" type="TEXT" path="/deliverables/poster" title="窗字标题" brief="主视觉「窗」字标题">
  <size width="380" height="280" />
  <inline>
    <contents>
      <content bold="true">窗</content>
    </contents>
    <style font_size="200" font_family="寒蝉锦书宋Pro" font_weight="700" color="#FFFFFF" align="center" vertical_align="center" />
  </inline>
</item>
```

### `<inline>`

| 字段 | 必填 | 说明 |
|---|---:|---|
| `contents / content` | 是 | `<contents>` 容器内放 `<content>` 片段，按顺序拼成完整文本 |
| `style` | 是 | 整块文本共用的排版样式 |
| `auto_width` | 否 | 是否按内容自适应宽度，缺省 `false` |
| `auto_height` | 否 | 是否按内容自适应高度，缺省 `false` |
| `stroke` | 否 | 文字描边颜色 |
| `stroke_width` | 否 | 文字描边宽度 |

### `<content>`

每个 `<content>` 是一个文本片段：

| 字段 | 必填 | 说明 |
|---|---:|---|
| 元素文本 | 是 | 片段文字直接写在 `<content>` 内，不使用 `<text>` 子节点 |
| `line_break` | 否 | 该片段之后是否换行，`true` / `false`；省略时按 `false` 连续拼接 |
| `bold` | 否 | 加粗 |
| `italic` | 否 | 斜体 |
| `underline` | 否 | 下划线 |
| `color` | 否 | 片段级颜色，覆盖 `style.color` |

### `<style>`

| 字段 | 必填 | 说明 |
|---|---:|---|
| `font_size` | 是 | 整数字号，如 `48`，不写 `48.0` 或科学计数法 |
| `font_family` | 是 | 使用[字体白名单](fonts.md)中的精确名称 |
| `font_weight` | 是 | 整数字重，使用[字体白名单](fonts.md)中对应字体的字重 |
| `color` | 是 | `#RRGGBB` |
| `align` | 是 | 水平对齐：`left` / `center` / `right` |
| `vertical_align` | 否 | 垂直对齐：`top` / `center` / `bottom`，缺省 `top` |
| `bg_color` | 否 | 背景色 |
| `border_color` | 否 | 边框色 |
| `line_height` | 否 | 数值像素行高，不带 px 后缀；字号 48 的 1.2 倍行高写 `57.6` |
| `letter_spacing` | 否 | 字间距，单位百分比 |

## 多行

样式统一的多行文字放在**同一个 Item** 里，用多个 `<content>`，除最后一段外 `line_break` 为 `true`：

```xml
<inline stroke="#7C2D12" stroke_width="1">
  <contents>
    <content bold="true" line_break="true">雨夜便利店</content>
    <content color="#FCA5A5">第三话</content>
  </contents>
  <style font_size="48" font_family="寒蝉锦书宋Pro" font_weight="700" color="#FFFFFF" align="center" line_height="57.6" vertical_align="center"/>
</inline>
```

最后一个片段的 `line_break` 必须是 `false`，否则末尾多出一个空行。

## 片段级样式

同一块文本里个别词要加粗或变色时，用片段级字段，不必拆成多个 Item：

```xml
<inline auto_width="false">
  <contents>
    <content line_break="false">限时</content>
    <content bold="true" color="#C5542D" line_break="false">五折</content>
    <content line_break="false">起</content>
  </contents>
  <style font_size="48" font_family="Source Han Sans SC VF" font_weight="400" color="#172B4D" align="left"/>
</inline>
```

字号、字体不同则必须拆成多个 Item——`<style>` 是整块共用的。

## 文本框高度

`transform.height` 要容得下实际渲染结果，否则文字被裁切。粗算下限：

```text
height ≥ ceil(font_size × 1.32 × 行数)
```

`line_height` 显式给出时以它为准。字体实测更高时以实测为准。

扩大已有文本框时保持垂直中心不变：

```text
new_y = old_y - (new_height - old_height) / 2
```

不要靠 `vertical_align` 掩盖高度不足——它只改变文本块在框内的位置，不解决裁切。

## 注意

- 文字对比按[共同构图策略](../style/shared/composition-principles.md#文字与背景的对比处理)选择。字色、字重与位置优先满足实际阅读；风格需要描边时使用已有 `<inline stroke="…" stroke_width="…">`，不自造外描边对齐属性，回读渲染后检查是否侵蚀字腔。协议没有文字模糊阴影字段：轻微硬投影可用下层同文案、同字体的偏移 TEXT，并与主字同步编辑、在 `render_text` 中只登记一次语义；需要柔化或复杂材质的生成标题在图像内完成，不把普通正文栅格化。承托的准入与用途以共同构图策略为准；协议支持某种图层不代表可以添加文字底板。
- `SHAPE` 不承载文字。带文字的卡片、按钮、标签一律拆成背景 `SHAPE` + 上层 `TEXT`。
- 准确文字（价格、日期、参数）保持为真实 `TEXT`，不要烘焙进图片——那样不可编辑、不可搜索。
