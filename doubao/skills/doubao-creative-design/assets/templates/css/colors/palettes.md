# 配色｜参数与实现

[返回使用说明](../README.md)。本文件保存该分类的真实参数、默认值与代码；无需从 catalog 查找参数值。CSS 代码块是维护源，生成正式 HTML 时按现有协议展开为行内声明。

<a id="palette-directory"></a>

## 全部配色目录

所有新增配色都在本目录下按颜色特征分文件；本页的共用参数不等于全部配色。风格标签为通用不表示配色被删除。

| 配色 | 参数所在文件 |
|---|---|
| [青色青柠](palettes.md#palette.aqua-lime) | palettes.md |
| [奶油粉](palettes.md#palette.cream-pink) | palettes.md |
| [暖纸棕](palettes.md#palette.warm-paper) | palettes.md |
| [糕点暖金](rich-and-retro.md#palette.pastry-gold) | rich-and-retro.md |
| [酒红奶油](rich-and-retro.md#palette.burgundy-cream) | rich-and-retro.md |
| [净白青蓝](calm-and-rational.md#palette.clinical-cyan) | calm-and-rational.md |
| [炭黑玫粉](high-contrast-pop.md#palette.charcoal-rose) | high-contrast-pop.md |
| [竹林深绿](fresh-and-natural.md#palette.bamboo-olive) | fresh-and-natural.md |
| [苔绿信笺](fresh-and-natural.md#palette.moss-letter) | fresh-and-natural.md |
| [桂香奶金](soft-and-muted.md#palette.osmanthus-cream) | soft-and-muted.md |
| [红黄蓝纸本撞色](bright-and-playful.md#palette.primary-pop) | bright-and-playful.md |
| [晴空蓝青柠](bright-and-playful.md#palette.sky-lime) | bright-and-playful.md |
| [钴蓝荧绿](high-contrast-pop.md#palette.cobalt-acid) | high-contrast-pop.md |
| [黑底电光青](high-contrast-pop.md#palette.neon-cyan) | high-contrast-pop.md |
| [科研蓝白橙](calm-and-rational.md#palette.science-blue-orange) | calm-and-rational.md |
| [植萃绿金](fresh-and-natural.md#palette.botanical-green-gold) | fresh-and-natural.md |
| [炭黑银灰荧黄](high-contrast-pop.md#palette.industrial-silver-lime) | high-contrast-pop.md |
| [古纸赭黄墨棕](rich-and-retro.md#palette.antique-ochre) | rich-and-retro.md |
| [灰纸靛蓝砖红](soft-and-muted.md#palette.oxide-blue-paper) | soft-and-muted.md |
| [珊瑚朱红纸白墨黑](bright-and-playful.md#palette.coral-paper-ink) | bright-and-playful.md |

<a id="colors.parameters"></a>

## 参数表

风格标签：通用（共用实现或组合规则，非独立风格预设）。

| 参数 | 实现默认值 | 类型／调整范围 | 作用与限制 |
|---|---|---|---|
| `--vl-hue` | `184` | number | 色相，通常 0–360 |
| `--vl-tint` | `hsl(var(--vl-hue) 87% 91%)` | color | 表面底色 |
| `--vl-ink` | `hsl(var(--vl-hue) 70% 19%)` | color | 正文颜色 |
| `--vl-accent` | `#ffdf53` | color | 主强调色；文件夹背页读取此色 |
| `--vl-accent-2` | `var(--vl-accent)` | color | 第二强调色；仅显式绑定的色块／装饰使用 |
| `--vl-accent-3` | `var(--vl-accent)` | color | 第三强调色；不自动添加色块 |
| `--vl-surface-end` | `hsl(var(--vl-hue) 82% 91%)` | color | 塑料/玻璃表面渐变末端；纸张仅用 tint |
| `--vl-muted-ink` | `var(--vl-ink)` | color | 次级正文色，与 body-opacity 共同决定结果 |
| `--vl-edge-color` | `#fff` | color | 亮边主色；文件夹渐变末端沿用色相 |
| `--vl-light-color` | `#fff` | color | 主高光颜色 |
| `--vl-shadow-color` | `hsl(var(--vl-hue) 80% 25%)` | color | 底部环境投影色；不替代材质内部阴影 |
| `--vl-label-bg` | `hsl(var(--vl-hue) 66% 48% / .82)` | color | 标签底色 |
| `--vl-label-ink` | `#fff` | color | 标签文字色 |

默认值是组件内部的缺省颜色，不是整页背景或风格推荐。先根据用户参考、品牌、主体与主题选择实际色板，再以缺省值补齐未指定的组件角色；不能把奶油／暖纸色自动推广为“高级、自然、留白”的全页底色。背景的空间、色场或纹理另由视觉设定决定。材质预设的纸色在本文件维护，纹理与滤镜在 surfaces 维护。

<a id="colors.defaults"></a>

## 通用与纸张缺省颜色

风格标签：通用（共用实现或组合规则，非独立风格预设）。

```css
.vl-folder {
  --vl-surface-end: hsl(var(--vl-hue) 82% 91%);
  --vl-muted-ink: var(--vl-ink);
  --vl-edge-color: #fff;
  --vl-light-color: #fff;
  --vl-shadow-color: hsl(var(--vl-hue) 80% 25%);
  --vl-label-bg: hsl(var(--vl-hue) 66% 48% / .82);
  --vl-label-ink: #fff;
  --vl-hue: 184;
  --vl-accent: #ffdf53;
  --vl-accent-2: var(--vl-accent);
  --vl-accent-3: var(--vl-accent);
  --vl-ink: hsl(var(--vl-hue) 70% 19%);
  --vl-tint: hsl(var(--vl-hue) 87% 91%);
  color: var(--vl-ink);
}

.vl-folder__back {
  background: linear-gradient(100deg, #fff8ac, var(--vl-accent));
}

.vl-paper {
  --vl-hue: 35;
  --vl-accent: #dd9671;
  --vl-tint: #f1e6cc;
  --vl-ink: #53432e;
}

.vl-tag {
  background: var(--vl-label-bg);
  color: var(--vl-label-ink);
}

.vl-copy {
  color: var(--vl-muted-ink);
}
```

<a id="palette.aqua-lime"></a>

## 青色青柠

风格标签：通用。

- 只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。
- --vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。

直接把以下 overrides 写到 article 的行内 style。

```json
{
  "id": "palette.aqua-lime",
  "kind": "palette",
  "label": "青色青柠",
  "tags": [
    "配色",
    "青色青柠",
    "aqua-lime"
  ],
  "applies_to": [
    "recipe.folder-plastic",
    "recipe.folder-glass",
    "recipe.folder-paper",
    "recipe.rounded-plastic",
    "recipe.rounded-glass",
    "recipe.rounded-paper"
  ],
  "overrides": {
    "--vl-hue": "184",
    "--vl-tint": "#d4f9f7",
    "--vl-surface-end": "#d5f8fa",
    "--vl-ink": "#164d4c",
    "--vl-muted-ink": "#356664",
    "--vl-accent": "#e2ef70",
    "--vl-label-bg": "#208888",
    "--vl-label-ink": "#fff",
    "--vl-edge-color": "#fff",
    "--vl-light-color": "#fff",
    "--vl-shadow-color": "#164d4c"
  },
  "notes": [
    "只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。",
    "--vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。"
  ],
  "status": "implemented"
}
```

<a id="palette.cream-pink"></a>

## 奶油粉

风格标签：通用。

- 只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。
- --vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。

直接把以下 overrides 写到 article 的行内 style。

```json
{
  "id": "palette.cream-pink",
  "kind": "palette",
  "label": "奶油粉",
  "tags": [
    "配色",
    "奶油粉",
    "cream-pink"
  ],
  "applies_to": [
    "recipe.folder-plastic",
    "recipe.folder-glass",
    "recipe.folder-paper",
    "recipe.rounded-plastic",
    "recipe.rounded-glass",
    "recipe.rounded-paper"
  ],
  "overrides": {
    "--vl-hue": "345",
    "--vl-tint": "#fff0e3",
    "--vl-surface-end": "#f9dce8",
    "--vl-ink": "#653848",
    "--vl-muted-ink": "#785766",
    "--vl-accent": "#f4cc72",
    "--vl-label-bg": "#99566f",
    "--vl-label-ink": "#fff",
    "--vl-edge-color": "#fff",
    "--vl-light-color": "#fff",
    "--vl-shadow-color": "#653848"
  },
  "notes": [
    "只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。",
    "--vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。"
  ],
  "status": "implemented"
}
```

<a id="palette.warm-paper"></a>

## 暖纸棕

风格标签：通用。

- 只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。
- --vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。

直接把以下 overrides 写到 article 的行内 style。

```json
{
  "id": "palette.warm-paper",
  "kind": "palette",
  "label": "暖纸棕",
  "tags": [
    "配色",
    "暖纸棕",
    "warm-paper"
  ],
  "applies_to": [
    "recipe.folder-plastic",
    "recipe.folder-glass",
    "recipe.folder-paper",
    "recipe.rounded-plastic",
    "recipe.rounded-glass",
    "recipe.rounded-paper"
  ],
  "overrides": {
    "--vl-hue": "35",
    "--vl-tint": "#f1e6cc",
    "--vl-surface-end": "#eadabe",
    "--vl-ink": "#53432e",
    "--vl-muted-ink": "#75644c",
    "--vl-accent": "#dd9671",
    "--vl-label-bg": "#806044",
    "--vl-label-ink": "#fff",
    "--vl-edge-color": "#fff",
    "--vl-light-color": "#fff",
    "--vl-shadow-color": "#53432e"
  },
  "notes": [
    "只覆盖颜色；透明材质叠加后的实际对比度按目标背景检查。",
    "--vl-surface-end 仅用于塑料/玻璃，纸张使用 --vl-tint。"
  ],
  "status": "implemented"
}
```

## 配色边界

全页背景与颜色面积比例由版式决定。纸张只消费 tint，塑料／玻璃还消费 surface-end；次级文字与正文 opacity 叠加后再判断对比度。三个配色不是自动深浅主题，使用深底时重新检查文字与亮边。

<a id="color.gradient"></a>

## 通用渐变与逐色标透明度

风格标签：通用。

覆盖已有蓝青活动背景、金色章节、透明玻璃高光和透明退场的渐变需求。三个类型共用 stops；表面几何、纹理、文字裁切由各自原子负责。

| 参数 | 默认值 | 作用与限制 |
|---|---|---|
| `--vl-gradient-stops` | `var(--vl-tint,#fff) 0%, var(--vl-accent,#0bb) 100%` | 任意数量、至少两个 CSS 色标；每个色标可有独立透明度 |
| `--vl-gradient-angle` | `135deg` | 线性渐变方向；0deg 向上，90deg 向右 |
| `--vl-gradient-x` | `50%` | 径向／圆锥中心横坐标 |
| `--vl-gradient-y` | `50%` | 径向／圆锥中心纵坐标 |
| `--vl-gradient-rx` | `70%` | 径向椭圆水平半径 |
| `--vl-gradient-ry` | `70%` | 径向椭圆垂直半径 |
| `--vl-gradient-turn` | `0deg` | 圆锥渐变起始角度 |
| `--vl-paint` | `由所选类型计算` | 实现输出，供背景或文字填充消费，不再独立维护第二套渐变 |

```css
.vl-gradient--linear { --vl-paint:linear-gradient(var(--vl-gradient-angle,135deg),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--radial { --vl-paint:radial-gradient(ellipse var(--vl-gradient-rx,70%) var(--vl-gradient-ry,70%) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-gradient--conic { --vl-paint:conic-gradient(from var(--vl-gradient-turn,0deg) at var(--vl-gradient-x,50%) var(--vl-gradient-y,50%),var(--vl-gradient-stops,var(--vl-tint,#fff) 0%,var(--vl-accent,#0bb) 100%)); }
.vl-paint-fill { background-image:var(--vl-paint,none); }
```

```html
<section class="vl-gradient--linear vl-paint-fill" style="--vl-gradient-angle:90deg;--vl-gradient-stops:#f5ce68 0%,#ee718d 45%,#315fce 100%">多色背景</section>
<span class="vl-gradient--radial vl-paint-fill" style="--vl-gradient-stops:color-mix(in srgb,#dffbff 80%,transparent) 0%,color-mix(in srgb,#2a8ecf 25%,transparent) 50%,transparent 100%">独立装饰层</span>
```

类型选择 linear / radial / conic 之一，不同时添加多个类型类。HTML 实现 可逐项记录 `{color, opacity, offset}`，组装时将每项转成 `color-mix(in srgb, 颜色 透明度百分比, transparent) 位置`，以逗号连接写入 stops；数组本身不能直接作为 CSS 声明。offset 按非递减顺序排列，同位置可形成硬切；改变透明度只作用于该色标，不对正文父层设 opacity。需要淡出已有照片时使用图片自身 mask，渐变覆盖层不是图片透明蒙版。圆锥渐变是通用类型补齐，本批参考未据此增加圆锥主题预设。

<!-- css-extraction-palettes -->
## 脚本维护的配色目录

| 配色 | 参数入口 |
|---|---|
| 青色青柠 | [参数](palettes.md#palette.aqua-lime) |
| 奶油粉 | [参数](palettes.md#palette.cream-pink) |
| 暖纸棕 | [参数](palettes.md#palette.warm-paper) |
| 糕点暖金 | [参数](rich-and-retro.md#palette.pastry-gold) |
| 酒红奶油 | [参数](rich-and-retro.md#palette.burgundy-cream) |
| 净白青蓝 | [参数](calm-and-rational.md#palette.clinical-cyan) |
| 炭黑玫粉 | [参数](high-contrast-pop.md#palette.charcoal-rose) |
| 竹林深绿 | [参数](fresh-and-natural.md#palette.bamboo-olive) |
| 苔绿信笺 | [参数](fresh-and-natural.md#palette.moss-letter) |
| 桂香奶金 | [参数](soft-and-muted.md#palette.osmanthus-cream) |
| 红黄蓝纸本撞色 | [参数](bright-and-playful.md#palette.primary-pop) |
| 晴空蓝青柠 | [参数](bright-and-playful.md#palette.sky-lime) |
| 钴蓝荧绿 | [参数](high-contrast-pop.md#palette.cobalt-acid) |
| 黑底电光青 | [参数](high-contrast-pop.md#palette.neon-cyan) |
| 科研蓝白橙 | [参数](calm-and-rational.md#palette.science-blue-orange) |
| 植萃绿金 | [参数](fresh-and-natural.md#palette.botanical-green-gold) |
| 炭黑银灰荧黄 | [参数](high-contrast-pop.md#palette.industrial-silver-lime) |
| 古纸赭黄墨棕 | [参数](rich-and-retro.md#palette.antique-ochre) |
| 灰纸靛蓝砖红 | [参数](soft-and-muted.md#palette.oxide-blue-paper) |
| 珊瑚朱红纸白墨黑 | [参数](bright-and-playful.md#palette.coral-paper-ink) |
| 冷银墨黑青蓝 | [参数](calm-and-rational.md#palette.silver-cyan-mono) |
| 酒馆红棕赭纸亮橙 | [参数](rich-and-retro.md#palette.tavern-umber-orange) |
<!-- /css-extraction-palettes -->
