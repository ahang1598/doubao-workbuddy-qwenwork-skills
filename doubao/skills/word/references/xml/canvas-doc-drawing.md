# 本地 Word XML：Drawing、Shape、TextBox 与文字效果

用于 DrawingML Shape、TextBox、WordArt、轮廓和 run-level 文字效果。公共 XML 与更新规则先读 [`canvas-doc-xml.md`](canvas-doc-xml.md) 和 [`../cli/canvas-doc-update.md`](../cli/canvas-doc-update.md)；布局属性同时加读 [`canvas-doc-media.md`](canvas-doc-media.md)，正文属性加读 [`canvas-doc-text.md`](canvas-doc-text.md)。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

这些对象使用既有 block 命令，通过 DocxXML `--content` 提交，不另设专用请求。

- **修改前**：必须用 `+local-fetch --detail full` 确认目标返回本文定义的可写标签。
- **新建前**：读取 carrier 和相邻格式，按本文语法及[预设值表](canvas-doc-drawing-presets.md)构造；不要求文档已有 Drawing。
- **能力不足**：仅有只读投影时向入口返回 `local_unverifiable`；Update 结构化返回不支持时，由 recovery 返回 `local_unsupported_runtime`。本页不直接切换路由。

## 结构

```xml
<drawing id="drawing-1" layout="floating" width="320pt" height="180pt"
  wrap="square" wrap-text="both-sides"
  position-h-relative-from="page" position-h-align="right"
  position-v-relative-from="page" position-v-align="bottom">
  <shape id="shape-1" preset="roundRect"
    fill="solid" fill-color="rgb(68,114,196)"
    outline="solid" outline-width="1pt"
    outline-color="rgb(32,56,100)" outline-style="solid">
    <textbox id="textbox-1"
      inset-top="3.6pt" inset-right="7.2pt"
      inset-bottom="3.6pt" inset-left="7.2pt"
      wrap="square" vertical-align="center" auto-fit="none">
      <p id="textbox-p-1">文本框内容</p>
    </textbox>
  </shape>
</drawing>
```

- `<drawing>` 只能作为文本流中的行内对象，必须恰好包含一个 `<shape>`。
- `<shape>` 最多包含一个 `<textbox>`；TextBox 内 block 属于独立 story。
- 修改已有对象必须沿用 Fetch 返回的 `drawing`、`shape`、`textbox` 和内部 block ID；新建对象省略对应 `id`。
- 修改时保留 Fetch 的可回放属性和对象 ID，让宿主合并保留未暴露的高级属性；不要把内部 sidecar 字段自行添加为 XML 属性。

## Drawing 布局

`<drawing>` 与 `<img>` 共享下列属性的值域和布局语义，但 Drawing 使用严格属性校验：未知属性或非法值使整次请求失败，不能套用图片的 warning/drop 规则。

```text
layout width height wrap wrap-text
position-h-relative-from position-h-offset position-h-pct-offset position-h-align
position-v-relative-from position-v-offset position-v-pct-offset position-v-align
simple-pos-x simple-pos-y simple-pos-enabled
behind-doc relative-height wrap-polygon
wrap-distance-top wrap-distance-right wrap-distance-bottom wrap-distance-left
float-effect-extent-top float-effect-extent-right
float-effect-extent-bottom float-effect-extent-left
allow-overlap locked layout-in-cell
```

- `layout` 只取 `inline|floating`；新建必填正 `width` / `height`，更新时省略尺寸则保留原值。
- `wrap` 只取 `none|square|tight|through|top-bottom`，`wrap-text` 只取 `both-sides|left|right|largest`。
- 浮动属性出现但 `layout` 缺席时会规范化为 `layout="floating"`。
- `<textbox wrap>` 表示框内文字换行，与 `<drawing wrap>` 的对象外部正文环绕不是同一属性。

## Shape 几何、填充与轮廓

| 属性 | 取值与规则 |
|---|---|
| `preset` | [Shape 预设值表](canvas-doc-drawing-presets.md#shape-preset)中的原值；不可清除，不自行转 kebab-case |
| `rotation` | 有限十进制度数；`clear` 清除 |
| `flip-horizontal` / `flip-vertical` | boolean；`false` 是显式值 |
| `fill` | `none\|solid`；`none` 与 `fill-color` 互斥 |
| `fill-color` | 统一颜色文法；接受 `auto`，实际颜色须不透明 |
| `outline` | `none\|solid`；`none` 与其他 outline 参数互斥 |
| `outline-width` | 非负裸数值（按 pt）、`pt` 或 `px`；归一化为 pt |
| `outline-color` | 统一颜色文法；接受 `auto`，实际颜色须不透明 |
| `outline-style` | `solid\|dot\|dash\|lgDash\|dashDot\|lgDashDot\|lgDashDotDot\|sysDash\|sysDot\|sysDashDot\|sysDashDotDot` |
| `outline-cap` | `flat\|round\|square` |
| `outline-join` | `round\|bevel\|miter` |

线端属性为：

- `outline-head-type` / `outline-tail-type`：`none|triangle|stealth|diamond|oval|arrow`；
- `outline-head-width` / `outline-tail-width`：`sm|med|lg`；
- `outline-head-length` / `outline-tail-length`：`sm|med|lg`；
- `type=none` 时不得同时写 width/length。

gradient、pattern、blip、theme ref、custom geometry、geometry adjustment、group/canvas、custom dash 和复杂 effects 均不开放写入。

## 非视觉属性与 TextBox

Shape 的 `name`、`alt-description`、`alt-title`、`remove-alt-description`、`remove-alt-title` 与图片同义；`remove-*="true"` 与对应 value 属性互斥。

`<textbox>` 支持：

| 属性 | 取值与规则 |
|---|---|
| `inset-top/right/bottom/left` | 非负裸数值（按 pt）、`pt` 或 `px`；缺席保留 |
| `wrap` | `none\|square` |
| `vertical-align` | `top\|center\|bottom\|justify\|distributed` |
| `auto-fit` | 写入只支持 `none\|shape`；Fetch 的 `normal` 是 preserve-only |

修改 `auto-fit="normal"` 的相邻属性时保留原 ID 和 auto-fit，由宿主保留未暴露的缩放参数，不把这些内部参数写成 XML 属性。已有 `normal` 不能改成 `none` 或 `shape`，也不能为新 TextBox 设置 `normal`；需要这种模式转换时向入口输出 `local_unsupported`。

## WordArt 与文字效果

DrawingML WordArt 是 Shape discriminator，不新增 `<word-art>`：

```xml
<drawing id="drawing-2" layout="inline" width="240pt" height="72pt">
  <shape id="shape-2" preset="rect" fill="none" outline="none"
    word-art="true" word-art-warp="textArchUp">
    <textbox id="textbox-2">
      <p id="word-art-p-1" align="center">
        <span text-fill="solid" text-fill-color="rgb(255,255,255)"
          text-outline="solid" text-outline-width="1pt"
          text-outline-color="rgb(0,0,0)"
          text-shadow="outer-bottom-right">WordArt</span>
      </p>
    </textbox>
  </shape>
</drawing>
```

- `word-art="true"` 是断言或新建 discriminator；新建 WordArt 必须恰好包含一个 `<textbox>`，新建时指定 `word-art-warp` 也必须声明 `word-art="true"`。普通 Shape 与 WordArt 不支持类型转换。
- 新建或更换 `word-art-warp`、`text-shadow`、`text-reflection`、`text-glow` 时读取[预设值表](canvas-doc-drawing-presets.md)；已有值未修改时沿用 Fetch，无需加载整表。阴影、映像、发光使用 `none` 清除，不使用 UI 标识 `shadow-none` / `reflection-none` / `glow-none`。
- 文字效果只作用于 `<span>`；仅空 `<p>` 可表达 paragraph-mark run properties，非空 `<p>` 不接受效果属性。
- 同一效果的属性是原子组；修改某一组时携带该组需保留的全部属性，保留其他效果和非目标文字格式。不能用省略颜色、宽度等组内属性表示局部 patch。

| effect 属性 | 取值与约束 |
|---|---|
| `text-fill`、`text-outline` | `none` 或 `solid` |
| `text-fill-color`、`text-outline-color` | 不透明统一颜色；分别须同时提供 `text-fill`、`text-outline`，且不得为 `none` |
| `text-outline-width` | 非负 `<n>pt`；不套用 Shape 轮廓的裸数或 px 文法 |
| `text-outline-style` | 与上文 `outline-style` 相同的 11 个线型值 |
| `text-shadow`、`text-reflection`、`text-glow` | [各自预设值](canvas-doc-drawing-presets.md)或 `none` |
| `text-shadow-color`、`text-glow-color` | 统一颜色，支持真实 alpha；分别须同时提供非 `none` 的 `text-shadow`、`text-glow` |

清除填充或轮廓时仅保留该组的 `text-fill="none"` 或 `text-outline="none"`，移除组内颜色等参数；清除阴影或发光时也移除对应颜色。不要把未发布的效果参数或 JSON sidecar 写进 XML。

VML TextPath 仅以 `source="vml"`、`word-art="true"`、`text-path="..."` 只读投影；不能修改或用于新建。

## 更新与验收

- Drawing 是行内对象，但 `block_replace`、`block_delete` 和 `block_insert_after` 对它有专用路径。更新时以最新 Fetch 返回的 drawing ID 作为 `--block-id`，`--content` 传同 ID 的单根 `<drawing>`；删除时直接以 drawing ID 执行 `block_delete`，无需替换宿主 carrier。
- 在已有 Drawing 后复制或新建 Drawing 时，以锚点 drawing ID 执行 `block_insert_after`，并传单根 `<drawing>`；省略 Drawing、Shape、TextBox 及内部 block 的 record ID，由宿主重新分配。内嵌对象按各自专项处理。
- shape/textbox ID 不能作为 Drawing 命令目标。修改 TextBox 正文时使用该 story 内最新 Fetch 返回的 block ID；跨 story 或已失效的 identity 会被拒绝。
- 新建对象只使用本页白名单与 canonical constructor default；`preset` 可省略，普通无 TextBox Shape 默认 `rect`，含 TextBox 或 `word-art="true"` 时使用各自构造器默认；显式指定时必须来自[预设值表](canvas-doc-drawing-presets.md)。新建必填正尺寸；后插还需真实锚点，文末追加则可用 `append` 写入含 Drawing 的完整段落。
- 写后回读完整 `<drawing>` 和必要的 TextBox story，核对对象 identity、布局、非目标 sidecar 和 run 级效果。保存重开保真须有实际保存重开证据，未完成时披露未验证，不得把 XML 回读当作该证明，也不得为验收自动关闭用户文件。

## 明确不支持

- 文档 theme 定义与 Shape 的 theme ref 写入；文本引用现有主题字体的四个 `font-family-*-theme` 属性仍可用，见[文本规范](canvas-doc-text.md#富文本)；
- Shape hyperlink sidecar、超链接创建或修改；
- custom geometry、geometry/warp adjustment、group/canvas；
- Shape locks、`outline-compound`、miter limit、line align、sketch、custom dash；
- gradient/pattern/blip fill、TextBox vertical flow/columns/linked story、完整 `normal` AutoFit 参数；
- VML TextPath 创建或修改、非 registry shadow/reflection/glow 参数。

===== 全文完 =====
