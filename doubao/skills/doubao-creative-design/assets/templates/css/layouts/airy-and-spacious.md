# 疏朗留白

状态：已实现。

参考：图 6 的香调说明、图 7 的信件正文。共享居中窄内容栏；信笺分支只调整阅读宽度和段距。

<a id="layout.reading-column"></a>

## 疏朗留白原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-reading-width` | `34rem` | 文本最大宽度；信笺可设 26rem |
| `--vl-reading-inset` | `8%` | 两侧留白，建议 6%–18% |
| `--vl-reading-space` | `64px` | 上下留白，建议 32–120px |
| `--vl-paragraph-gap` | `1.5em` | 段距，建议 1–2em |

```css
.vl-reading { box-sizing:border-box; padding:var(--vl-reading-space,64px) var(--vl-reading-inset,8%); }
.vl-reading__body { max-width:var(--vl-reading-width,34rem); margin-inline:auto; overflow-wrap:anywhere; }
.vl-reading__body > * { margin-block:0; }
.vl-reading__body > * + * { margin-block-start:var(--vl-paragraph-gap,1.5em); }
```

```html
<section class="vl-reading"><div class="vl-reading__body"><h2>章节标题</h2><p>正文段落</p><p>下一段</p></div></section>
```

字体仍读取 [字体与文字参数](layout-and-type.md#layouts.parameters)，在正文节点应用 font-family、font-size、line-height。信笺正文左对齐；居中的署名、章节标题在各节点单独设置，避免整页居中降低阅读效率。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。
