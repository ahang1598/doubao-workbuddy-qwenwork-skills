# editorial_atelier · Design Tokens

从 4 张标杆 SVG 逆向提取的所有 magic number。**新 skin 必须以这些数字为地基。**

参照标杆：
1. `mindmap_ml_4layer.svg` — 4-layer knowledge tree · hub + ribbon + block + card + chip
2. `mindmap_taxonomy_6layer.svg` — 6-column lineage · hero + sibling chip + milestone + timeline
3. `mindmap_system_design.svg` — 1 hub + 6 branch × 3 sub-cards · fan-out
4. `p53_interactome.svg` — hub + upstream/downstream + feedback + ribbon + phospho marker

---

## 1. Canvas

| Token | 值 |
|---|---|
| `HERO_CANVAS.w` | **1400** |
| `HERO_CANVAS.h` | **820** |
| `HERO_CANVAS.margin_x` | 55 (左) · 55 (右) |
| body 可用宽 | 1400 - 55 × 2 = **1290** |
| viewBox | `0 0 1400 820` |

## 2. 底色 · Ink · 主题色 (cross-figure)

| Slot | Token | Value | 用途 |
|---|---|---|---|
| bg | `BONE` | `#F1E9DA` | 纸面 · cream · 报纸米 |
| ink | `INK` | `#1C1914` | 主文字 · 深墨 |
| gray | `GRAY_72` | `rgba(94,80,62,0.72)` | 副文字 · 说明文 · 引言 |
| gray-dim | `GRAY_60` | `rgba(94,80,62,0.6)` | column header / 编号 |
| gray-body | `INK_82` | `rgba(28,25,20,0.82)` | READ 段正文 |
| gray-mute | `INK_75` | `rgba(28,25,20,0.75)` | card sub-text |
| hair | `HAIR` | `#1C1914` @ opacity 0.22 | title 下 hairline |
| hair-dim | `HAIR_16` | `rgba(28,25,20,0.16)` | 底部 divider |
| **primary** | `RUST` | **`#A35832`** | hub · 强调 · lineage 高亮 |

## 3. Categorical Hues (最多 6 色 · 每图挑 4-6 色)

按标杆 1/2/3/4 交叉使用的 hue：

| Token | Value | 出现在 |
|---|---|---|
| `RUST`     | `#A35832` | 全部 4 张 · 主色 |
| `ORANGE`   | `#C87F3D` | ML L2 Supervised · sysdesign step1 · p53 apoptosis kinase |
| `MAGENTA`  | `#A63C6E` | ML L2 Unsup · sysdesign step2 · p53 apoptosis group |
| `BLUE`     | `#3F6892` | ML L2 RL · sysdesign step4 · p53 metabolism |
| `GREEN`    | `#558045` | ML L2 DL · sysdesign step3 · p53 DNA repair |
| `OLIVE`    | `#7A6A3A` | sysdesign step5 · taxonomy L5 |
| `CINNAMON` | `#8B5A3C` | sysdesign step6 · taxonomy L6 |
| `GOLD_P`   | `#D9A448` | p53 phospho marker 填充 |

**tint 规则**：category rect fill 用 `rgba(<hue>, 0.12~0.14)` · card fill 用 `rgba(<hue>, 0.06~0.07)` · chip fill 用 `rgba(<hue>, 0.12)` · hub fill 用 `rgba(RUST, 0.22~0.24)` · highlighted lineage 用 `rgba(RUST, 0.24)`

## 4. Filter defs (共 3 个 · 全 SVG 共享)

```svg
<filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
  <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
  <feOffset dx="0" dy="1.5"/>
  <feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer>
  <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="hub-shadow" x="-30%" y="-30%" width="160%" height="160%">
  <feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/>  <!-- 3.0 in taxonomy -->
  <feOffset dx="0" dy="2.5"/>                             <!-- 2.0 in taxonomy -->
  <feComponentTransfer><feFuncA type="linear" slope="0.35"/></feComponentTransfer> <!-- 0.32 in taxonomy -->
  <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="hub-halo" x="-60%" y="-60%" width="220%" height="220%">
  <feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/>  <!-- 4.0 in taxonomy; 5.0 in p53 -->
</filter>
```

统一取值（skin 里落库）：`soft-shadow.blur=2 dy=1.5 slope=0.28` · `hub-shadow.blur=3.5 dy=2.5 slope=0.35` · `hub-halo.blur=5.5`

## 5. Gradient defs (ribbon 用)

```svg
<linearGradient id="r-{hue}" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{hue}" stop-opacity="0.75"/>
  <stop offset="1" stop-color="{hue}" stop-opacity="0.35"/>
</linearGradient>
```

**variant**：p53 用 `0.5 → 0.78` 反向流；sysdesign 用不同 `x1/y1/x2/y2` 方向组合（对角、正 y、反 x）。

按需为每个 hue 生成一个 `r-{name}` gradient（rust · orange · magenta · blue · green · olive · cinnamon）。

## 6. Marker defs (箭头 / T-bar / 磷酸化圆)

```svg
<!-- 箭头 · 每 hue 一个 -->
<marker id="arr-{hue}" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="7" markerHeight="7" orient="auto">
  <path d="M 0 0 L 9 5 L 0 10 Z" fill="{hue}"/>
</marker>

<!-- T-bar 表示抑制/降解 -->
<marker id="tbar-gray" viewBox="0 0 10 10" refX="7" refY="5"
        markerWidth="8" markerHeight="8" orient="auto">
  <line x1="7" y1="0" x2="7" y2="10" stroke="rgba(94,80,62,0.85)" stroke-width="2.6"/>
</marker>
```

**注意**：SKILL.md 的 rule G-5 禁 `<marker>` in slide XML —— 但只是 lark-slides embed 场景的限制。**hero canvas 独立 SVG 里允许用 marker**。

## 7. Typography Scale

| Slot | size | family | weight | letter-spacing | italic | 出处 |
|---|---|---|---|---|---|---|
| title | 26 | Georgia serif | 700 | .01em | no | title 主标 |
| subtitle | 13 | Inter sans | 500 | .04em | no | title 下副标 |
| section-kicker | 10 | Inter sans | 700 | .18em ~ .28em | no | § / STEP / 大分组标签 |
| column-header | 10 | Inter sans | 700 | .26em ~ .28em | no | L1 · KINGDOM |
| hub-name | 18-19 | Georgia serif | 800 | 0 | no | 中心 hub 名 (ML=19, sysdesign/taxonomy=18) |
| hub-name-hero | 26 | Georgia serif | 800 | 0 | no | p53 "TP53" 巨号 |
| block-title | 16-18 | Georgia serif | 700-800 | 0 | no | Paradigm/Kingdom 块 title |
| card-title | 13-14.5 | Inter sans | 800 | 0 | no | 三级 card 标题 (14.5 = kinase chip) |
| chip-label | 11 | Inter sans | 700 | 0 | no | pill chip 主 label |
| body-desc | 9.5-10 | Inter sans | 500-600 | 0 | italic 有时 | card 描述文字 |
| micro-numeric | 9-9.5 | Georgia serif | 500-700 | 0 | italic OK | 数字/例句 |
| footer-read | 12-12.5 | Inter sans | 500 | 0 | no | READ 段正文 |
| footer-italic | 11 | Inter sans | 500 | 0 | yes | READ 段脚注 |
| kicker-mini | 8.5 | Inter sans | 600-800 | .14em ~ .22em | no | 卡内 "1 OF 5 KINGDOMS" |
| source-tag | 10 | Inter sans | 700 | .22em | no | "READ" / "SOURCE" 标签 |

**Family alias**：
- `head_family` (Georgia): `"Georgia, serif"`
- `body_family` (Inter): `"Inter, sans-serif"`
- 全部 letter-spacing 用 em 单位

## 8. Chrome (6 层) 位置

Hero canvas 1400×820 · x_margin = 55

| # | 层 | y | 内容 | 字号 |
|---|---|---|---|---|
| 1 | title | 46 | 主标题 | serif 26 bold |
| 2 | subtitle | 70 | 副标 + 数据 | sans 13 medium |
| 3 | title-hair | 92 | 全宽 hairline (x=55→1345) | 0.6px opacity 0.22 |
| 4 | section-headers | 115 | column header / step counter | sans 10 bold letter=.26em |
| 5 | body | 128 → 700ish | pattern 主视觉 | (由 preset 定义) |
| 6a | body-hair | 722 (ML) / 704 (taxonomy) / 638-732 (p53) | 底部 divider | 0.5-0.6px opacity 0.12-0.22 |
| 6b | READ-kicker | 744 (ML) / 726 (taxonomy) / 756 (p53) | "READ" tag | sans 10 bold letter=.22em gray |
| 6c | READ-body | 763~803 (ML 3 lines) / 746~805 (taxonomy 4 lines) / 778~798 (p53 2 lines) | 完整解读段 | sans 12-12.5 medium ink @ 0.82 |
| 6d | source | 右下角 或 底部 | Source · ... | sans/mono 10-11 |

**body 区**：肉眼可用高约 **~600px**（比 embed 900×336 的 body 高 ~3 倍）。

## 9. Component Primitive Geometry

### 9.1 hub_double (中心 hub 双 rect + halo)

```
外 halo rect · none fill · stroke=RUST 2.0-2.4 opacity=0.5-0.55 · filter=hub-halo
   → 尺寸：hub 宽高各 +20-30，rx=12-14

内 cream rect · fill=BONE · filter=hub-shadow
   → hub 基础尺寸 · rx=10

覆盖 tint rect · fill=rgba(RUST, 0.22-0.24) · stroke=RUST 2.2-2.6
   → 与 cream rect 完全对齐 · rx=10
```

**参考尺寸**：ML mindmap 140×180 · sysdesign 210×110 · taxonomy 207×115 · p53 200×110

### 9.2 card_double (三级 card)

```
底 cream rect · fill=BONE (画白避免 tint 叠加) · rx=7
tint rect · fill=rgba(<hue>, 0.12-0.14) · stroke=<hue> 1.2-1.3 · rx=7
```

**参考尺寸**：ML 220×48（chip 上一级）· sysdesign 126×90 · taxonomy 207×115（hero）+ 207×36（sibling） · p53 155×52 · 110×44

### 9.3 chip_pill (最小 pill)

```
rect · rx=14 (=height/2) · fill=rgba(<hue>, 0.12) · stroke=<hue> 1.1
text · anchor=middle · size=11 · bold · ink
```

**参考尺寸**：ML `118×28` · 5 列间距 9px · rx=14

### 9.4 ribbon_gradient (梯形连接)

```
<path d="M {hub_top} C {mid} {mid} {block_top} L {block_bot} C {mid} {mid} {hub_bot} Z"
      fill="url(#r-{hue})"/>
```

关键点：
- 两条 cubic bezier 从 hub 侧到 block 侧
- 中控点在 x 方向 ~30% 处
- 顶边 y 与 hub/block 顶部对齐
- 底边 y 与 hub/block 底部对齐（"梯形宽度" = hub 侧 30-40px · block 侧 20-140px）
- fill 用对应 hue gradient

### 9.5 connector_dashed (虚线 hairline)

```
<line stroke="<hue>" stroke-width="1.2" opacity="0.55" stroke-dasharray="3 2"/>
```

用途：L3→L4 · task family → chip 的连接。

### 9.6 halo_wrap (高亮 lineage 外 halo)

```
<rect fill="none" stroke=RUST 2-2.4 opacity=0.5-0.55 filter=hub-halo/>
```

包在 highlighted node 外层，形成"光晕"感（taxonomy 里 6 chip 有此层）。

## 10. Line / Divider Styles

| 用途 | stroke | width | dash | opacity |
|---|---|---|---|---|
| title-hair | INK | 0.6 | none | 0.22 |
| bottom-divider | INK | 0.6 | none | 0.16 |
| card-in-line | <hue> | 0.6-0.7 | none | 0.4-0.5 |
| L3→L4 connector | <hue> | 1.2 | "3 2" | 0.55 |
| container dashed | <hue> | 1.1-1.2 | "4 3" ~ "6 4" | 0.3-0.85 |
| phospho-line | <hue> | 1.9 | none | 0.82 |
| feedback-arc | RUST | 1.9 | none | 0.88 |
| tbar-line | GRAY | 1.9 | "5 3" | 0.9 |
| lineage-backbone | RUST_14 rect | (rect fill) | - | fill rgba(RUST, 0.14) |

## 11. p53 独有：Phospho Disc + Feedback Arc

- 磷酸化圆：`<circle r=9 fill=GOLD_P stroke=BONE stroke-width=1.4/>` + `<text "P" serif 12 bold ink/>`
- feedback 双弧：`M {a} C ... {b}` cubic bezier · 一条 solid RUST → arr-rust marker · 一条 dashed GRAY → tbar-gray marker
- feedback pill：`rect 112×18 rx=9 fill=rgba(RUST, 0.14) stroke=rgba(RUST, 0.55) sw=0.9` + `text "FEEDBACK LOOP" 9 bold RUST letter=.2em`

## 12. 高亮 tspan (READ 段的 inline color emphasis)

```
<text ...>
  Read left → right for depth:
  <tspan font-weight="700" fill="#A35832">L1</tspan> answers "what is ML?" ·
  <tspan font-weight="700" fill="#A35832">L2</tspan> ...
</text>
```

每个 READ 段用 `<tspan>` 高亮 hue 或 primary 色的关键词，字重 700。

## 13. 数据密度门槛 (最低)

| 图 | 元素数 |
|---|---|
| ML 4-layer | 1 hub + 4 block + 9 card + 45 chip + 6 chrome layer + 3 READ 行 = ~68 element |
| taxonomy 6-layer | 6 hero + 18 sibling + 6 milestone + 6 timeline dot + 6 header + 4 READ 行 = ~46 element |
| sysdesign | 1 hub + 6 branch header + 18 sub-card + 6 step counter + 4 READ = ~35 element |
| p53 | 4 kinase + 1 MDM2 + 1 hub + 4 group × 2-3 chip + 4 phospho + 4 ribbon + 4 legend + 2 READ = ~35 element |

**hero preset 数据 dataclass 必须支撑到这个密度**——不能 5 个元素就交差。

## 14. Palette 落库结构 (给 editorial_atelier skin 使用)

复用现有 `Palette` dataclass · 落一个新常量：

```python
BONE_RUST = Palette(
    name="Bone Rust · Editorial Atelier",
    bg="#F1E9DA",
    bg_alt="#EFE4CE",       # 稍深卡片背景
    bg_dim="#E4D7BA",
    ink="#1C1914",
    gray="rgba(94,80,62,0.72)",   # 保留 rgba string
    hair="#1C1914",         # 加 opacity 0.22 by usage
    primary="#A35832",      # RUST
    primary_dim="#C87F3D",  # ORANGE
    accent="#D9A448",       # GOLD_P
    accent_dim="#A63C6E",   # MAGENTA
    positive="#558045",
    negative="#A63C6E",
    head_family="Georgia, serif",
    body_family="Inter, sans-serif",
    mono_family="Inter, sans-serif",   # 用 Inter mono variant · 无外部字体依赖
    kicker_letter_spacing=2.8,          # 大约 .28em @ 10pt = 2.8
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="FIGURE",
    signature_note="EDITORIAL ATELIER · BONE RUST",
)
```

## 15. Skin 需要暴露的 primitives (对应 aesthetics.py Round 3 已抽)

新 `editorial_atelier.py` 内部私有 helper：

```python
def svg_defs(hues: list[str]) -> str: ...           # 3 filter + N gradient + N marker
def hub_double(x,y,w,h, name, role, tagline, stat, palette): ...
def card_double(x,y,w,h, title, sub, tint_hue, palette): ...
def chip_pill(x,y,w,h, label, tint_hue, palette): ...
def ribbon_gradient(hub_top, hub_bot, blk_top, blk_bot, hue_id): ...
def connector_dashed(x1,y1,x2,y2, hue): ...
def halo_wrap(x,y,w,h, palette): ...
def phospho_disc(cx,cy, palette): ...               # p53-specific
def feedback_arc(a, b, palette, kind="transactivate"|"degrade"): ...
def hero_chrome(kicker, title, subtitle, encoding_note, palette, ...): ...
def hero_footer(caption, source, read_body, read_highlights, palette): ...
```

**strict-mode 契约**：hero preset 只能通过这 11 个 helper 画图，不允许自己写 rect/line/circle。

## 16. Chrome (hero) 组装 (预留 canvas 参数)

```python
hero_chrome(
    kicker="§ TAXONOMY · TREE OF LIFE",
    title="The 6-Layer Tree of Life · How Humans Are Classified",
    subtitle="From Kingdom (1.5M species) down to Species — canonical...",
    encoding_note=None,                      # optional 右上角
    column_headers=[("L1 · KINGDOM", 158), ...],  # 每列的 (label, x_center)
    palette=BONE_RUST,
    canvas=HERO_CANVAS,
)
```

## 17. READ 段的强制字段

hero preset data 必须提供：
- `read_lines: list[str]` (2-4 句 · 每句 ≥ 40 字符)
- `read_highlights: list[tuple[str, str]]` (关键词 → 颜色) — 用于 tspan 高亮

否则 render 直接 raise。

---

**Handoff done · v0 draft**

下一步：Task #2 起草 `editorial_atelier.py` 骨架，实现 §14 palette + §15 primitives + §16 chrome。
