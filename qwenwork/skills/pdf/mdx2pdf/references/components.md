# Built-in MDX component palette

All components are imported automatically — just use them inline.

## Layout / structure

### `<Cover>` — full-page report cover

```mdx
<Cover
  eyebrow="Quarterly Report"
  title="The Future of Knowledge Work"
  subtitle="optional subtitle"
  author="QwenWork Research"
  date="June 2026"
/>
```

Centered vertically, forces a page break after itself. Always the first
element of a multi-page document.

### `<TOC depth={3} />` — table of contents

Populates **client-side** by scanning headings of depth 2 through `depth`.
Default `depth={3}` (h2 + h3). Place it after `<Cover>` and any introductory
paragraph.

### `<PageBreak />` — force a page break

Use sparingly, e.g. before an Appendix:

```mdx
<PageBreak />

## Appendix A
```

### `<Landscape caption="...">` — sideways page for wide content

```mdx
<Landscape caption="A wide flowchart">
  <Mermaid>{`flowchart LR; A --> B --> C --> ...`}</Mermaid>
</Landscape>
```

Auto-promotion: tables with ≥8 columns and Mermaid diagrams with intrinsic
SVG width > 1.2× the portrait column are already wrapped automatically; only
use `<Landscape>` when you need explicit control or a caption.

### `<Two>` / `<Col>` — two-column grid

```mdx
<Two gap="2rem">
  <Col>
    Left column content.
  </Col>
  <Col>
    Right column content.
  </Col>
</Two>
```

### `<Aside>` — right-floated callout

```mdx
<Aside>
  Tangential context that hangs off the main flow.
</Aside>
```

## Emphasis / annotation

### `<Callout type="...">` — boxed annotation

```mdx
<Callout type="note" title="Heads up">…</Callout>
<Callout type="tip">…</Callout>
<Callout type="warning">…</Callout>
<Callout type="danger" title="Stop">…</Callout>
```

Types: `note` (blue icon), `tip` (green), `warning` (amber), `danger` (red).
Title falls back to a sensible default per type.

### `<Cite id="...">` and `<Bibliography entries={…}>`

```mdx
A finding<Cite id="smith2024" /> grounded in data.

<Bibliography entries={{
  "smith2024": <>Smith, J. <em>Title</em>, Journal, 2024.</>,
  "lee2025":   <>Lee, A. <em>Other Title</em>, J. Org., 2025.</>,
}} />
```

`<Cite>` renders an in-text superscript bracket like `[1]`.
`<Bibliography>` renders an ordered list at the bottom, using ids registered
by every `<Cite>`. Always render `<Bibliography>` somewhere (typically the
last element before any footer).

## Media

### `<Figure src caption credit width>`

```mdx
<Figure
  src="./assets/diagram.svg"
  alt="Three circles in the QwenWork palette"
  caption="Optional caption shown below the image"
  credit="QwenWork Design"
  width="60%"
/>
```

Relative `src` is resolved against the input file's directory and embedded
as a data URI in the PDF (so the PDF stays self-contained).

### `<Mermaid>{`...source...`}</Mermaid>`

```mdx
<Mermaid caption="Optional caption">{`
flowchart LR
  A --> B --> C
`}</Mermaid>
```

Mermaid renders in the browser before PDF capture. Wrap in `<Landscape>`
if the diagram is wide (≥6 nodes in a row).

## ASCII / box-drawing 框图（已知限制）

**前置条件：框图必须放进代码块（fenced code block，三反引号 ```）。** 直接
贴进正文会走比例字体 + 折叠换行，框线必乱。代码块可以**带语言标签**
（推荐 ` ```text `）也可以是**裸 ` ``` `** —— 两者都会拿到等宽字体
Maple Mono CN + 灰卡背景（裸 fence 的卡片样式由 `pre:not(.shiki)` 兜底，
见 0.4.4）。带语言标签还额外获得 Shiki 语法高亮。

用 `┌─┐│└┘├┤┬┴┼` 拼的 ASCII 框图能否对齐，取决于**源文本的列宽假设**
是否与渲染字体一致。Maple Mono CN 锁定 CJK = 2 列、ASCII / box-drawing = 1 列；
只要源文本按同一规则拼写，竖线就会精确对齐。

常见错位原因：作者在某个编辑器里按不同的 CJK 宽度凑的图 —— 每个 CJK 字符
实际渲染 2 列，但源文本里多占 / 少占了空格。**这在任何等宽渲染器（VS Code、
终端、本工具）里都会偏**，不是渲染端能可靠推断的：

```text
┌─────────────┐      ← 边框 13 列
│ 悟空 Agent  │      ← 若作者按 CJK=2 凑，这里也是 13 列 → 对齐
│ 悟空 Agent   │     ← 若多补 1 空格 → 14 列 → 右边框右移，错位
└─────────────┘
```

- ✅ **推荐**：架构图 / 流程图用 **`<Mermaid>`**（矢量渲染，永不错位，更美观）。
- ⚠️ **若必须用 ASCII 框图**：① 放进代码块；② 确保每个 CJK 字符按
  **2 个半角列**对齐。本工具**刻意不**自动「猜测」重排 box-drawing —— 因为对
  嵌套框、并排框、内部列分隔表格、以及代码块里把 `│` 当逻辑或运算符的情况，
  自动重排只会制造更隐蔽的损坏。源文本对齐了，输出就对齐。

## Charts

Server-side rendered as inline SVG (`d3-scale` + `d3-shape`). No JS at
PDF time, qwenwork palette by default (orange → purple → green → blue →
amber → gray, cycled per series).

### `<BarChart>`

```mdx
<BarChart
  data={[
    { name: 'Engineering', value: 412 },
    { name: 'Design',      value: 186 },
  ]}
  caption="Survey respondents by domain"
/>

{/* Multi-series, grouped: auto-detects series from data keys ≠ xKey */}
<BarChart
  data={[
    { quarter: 'Q1', sales: 120, refunds: 18 },
    { quarter: 'Q2', sales: 145, refunds: 22 },
  ]}
  xKey="quarter"
  caption="Sales vs refunds (USD ‘000)"
/>

{/* Stacked */}
<BarChart data={...} xKey="region" stacked caption="..." />

{/* Horizontal */}
<BarChart data={...} horizontal caption="..." />
```

Props: `data`, `caption?`, `xKey="name"`, `series?` (override),
`width=720`, `height=320`, `horizontal=false`, `stacked=false`.

### `<PieChart>` / donut

```mdx
<PieChart
  data={[
    { name: 'Subscriptions', value: 64 },
    { name: 'Services',      value: 22 },
    { name: 'Marketplace',   value: 10 },
    { name: 'Other',         value: 4 },
  ]}
  caption="Revenue mix"
/>

<PieChart data={...} donut caption="Subscribers by plan tier" />
```

Props: `data: { name, value }[]`, `donut=false`, `showLabels=true`,
`showLegend=true`, `width=520`, `height=320`.

### `<LineChart>`

```mdx
<LineChart
  data={[
    { month: 'Jan', revenue: 32, costs: 28 },
    { month: 'Feb', revenue: 45, costs: 31 },
  ]}
  xKey="month"
  smooth
  caption="H1 2026 (USD ‘000)"
/>
```

Props: `data`, `xKey="x"`, `series?`, `smooth=false`, plus the standard
size props.

### `<AreaChart>`

```mdx
<AreaChart
  data={[…]}
  xKey="week"
  stacked
  caption="Active users by platform (millions)"
/>
```

Props: same as LineChart plus `stacked=false`. Filled at 25 % opacity.

## What about plain Markdown features?

Everything works as expected — all CommonMark is valid MDX:

- **Headings** `# … ######`
- **GFM tables** `| a | b |\n|---|---|\n| 1 | 2 |`
- **Code fences** with language tag (Shiki highlights it)
- **Math** `$inline$`, `$$display$$` (KaTeX SSR)
- **Task lists** `- [ ]`, `- [x]`
- **Definition lists** `Term\n:   Definition`
- **Footnotes** `text[^1]\n\n[^1]: note`
- **Frontmatter** YAML at the top — `title:` becomes the PDF metadata title

You can freely mix CommonMark and MDX components in the same file.
