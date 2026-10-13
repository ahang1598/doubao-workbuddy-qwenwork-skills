# Phosphor 图标包（本 Skill 内置）

官方 [Phosphor Icons](https://phosphoricons.com/) 的 **SVG Flat** 全集（MIT），供功能图标、导航、Tab、工具栏直接取用。

```text
assets/phosphor/
├── phosphor-svgs-flat.zip   # 6 字重 × 1512 枚
├── catalog.json             # 全部规范名索引
└── LICENSE                  # MIT，再分发须保留
```

格式：`viewBox="0 0 256 256"` · `fill="currentColor"` —— **不是** Feather/Lucide 的 `0 0 24 24` + `stroke-width:2` 默认描边，可过 `check_ui_quality` 的通用描边检测。

## 何时用 / 何时不用

| 场景 | 做法 |
|---|---|
| F14 后台 / 工具 / 高密数据；克制型 B2B 功能位 | **直接用 Phosphor**；HTML 顶写 `<!-- design-intent: system-icons -->` |
| 落地页次要功能条、页脚社交、表单控件旁 glyph | Phosphor + `currentColor` 吃 `--ink` / `--accent` |
| F19 / F03 等**表现型** Tab / 主功能卡 | **同样走 Phosphor**（`fill`/`duotone` 字重 + token 上色 + 圆底板）。旧规则"必须生图 icon-kit"已被产物证伪并废除，见 image-bridge.md |
| 主视觉 / Hero 主角 | **禁止**用图标冒充；必须真实影像资产 |

**一句话**：功能图标一律 Phosphor。文生图做不出对齐、可切分、带 alpha 的图标组——
强行要求只会逼出雪碧图切片（`check_layout_contract` 的 `sprite-slicing` 会拦）。
只有「主角图标」（≤3 枚）才走生图，且必须逐枚单独出。

## 取用（写 HTML 前的绑定动作）

先查名，再注入或拷贝。未找到 = 换名或改走生图，禁止手写临摹 Feather。

图标库是 `assets/phosphor/phosphor-svgs-flat.zip`（9,000 个 SVG，
路径形如 `SVGs Flat/<weight>/<name>.svg`）。用标准库直接取，不需要专门的脚本：

```bash
# 模糊查名
python3 -c "import zipfile;print([n for n in zipfile.ZipFile('assets/phosphor/phosphor-svgs-flat.zip').namelist if 'wifi' in n][:8])"

# 取出一个，得到可直接内联的 SVG
python3 -c "import zipfile;print(zipfile.ZipFile('assets/phosphor/phosphor-svgs-flat.zip').read('SVGs Flat/regular/house.svg').decode)"
```

内联进 HTML 之后把 `fill`/`stroke` 换成 `currentColor`，尺寸用 `width/height`
或外层字号控制 —— 这样图标才会跟着文字的颜色与字阶走。

字重：`thin` · `light` · `regular`（默认）· `bold` · `fill` · `duotone`。

- UI 默认：`regular` 或 `bold`
- 选中 / 实心态：`fill`
- 双色层次：`duotone`（可用 CSS 控透明度；颜色仍跟 token）

## 嵌入约定（必须遵守）

1. **颜色只走 `currentColor`**，由父级 `color: var(--ink)` 或 `var(--accent)` 控制；禁止写死 `#000` / Tailwind 蓝。
2. **尺寸用 width/height 或 CSS**，保持方形；触控热区 ≥44px，图标本体常 20–28px。
3. **同屏字重一致**：Tab 一组不要混 regular + thin。
4. **与圆角同源**：图标落在圆底板时，底板半径用 `--r-control`，不要另起一套 pill。
5. **无障碍**：装饰性加 `aria-hidden="true"`；独担语义的按钮用 `aria-label`。
6. 打包进飞书 html5-block 时：优先 **inline SVG**（`inject`），避免相对路径丢图。

## 与质量门的关系

- 基线 §7b：Phosphor 属于合法路径 **② 设计决定的矢量** / **③ 系统图标声明**。
- 门只拦 Feather 式通用描边；用本包注入的 SVG 不受影响。
- `check_layout_contract.py` 的 `sprite-slicing` 会拦下"一张图切成多份当图标用"；用本包 inject 的 inline SVG 不受影响。

## 许可

MIT © Phosphor Icons。再分发或交付给客户时，保留 `assets/phosphor/LICENSE` 或等价声明。
