# 浓郁复古

状态：已填充。

共用 [语义颜色参数](palettes.md#colors.parameters)，不新增色彩实现。将 overrides 写到目标节点；已有组件会定义自己的默认变量，所以只设在页面祖先上不能覆盖组件默认值。纯页面使用 `background:var(--vl-tint);color:var(--vl-ink)`，不要求套用材质卡片。

<a id="palette.pastry-gold"></a>

## 糕点暖金

风格标签：通用。

参考：本批图 1 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

奶油纸底约 60%，棕色章节约 30%，金边和强调约 10%；不同章节交换底色与文字色。

```json
{
  "id": "palette.pastry-gold",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#ffe7bf",
    "--vl-surface-end": "#f3d2a0",
    "--vl-ink": "#5b301c",
    "--vl-muted-ink": "#815535",
    "--vl-accent": "#9b5328",
    "--vl-edge-color": "#c79a53",
    "--vl-light-color": "#fff5d9",
    "--vl-hue": "33",
    "--vl-shadow-color": "#5b301c",
    "--vl-label-bg": "#9b5328",
    "--vl-label-ink": "#fffaf0"
  }
}
```

<a id="palette.burgundy-cream"></a>

## 酒红奶油

风格标签：通用。

参考：本批图 4 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

酒红与奶油分段铺底，约 55:40；小面积橙红由照片提供。酒红区用 label-bg / label-ink 成对切换。

```json
{
  "id": "palette.burgundy-cream",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#efeada",
    "--vl-surface-end": "#e4dcc7",
    "--vl-ink": "#792125",
    "--vl-muted-ink": "#885348",
    "--vl-accent": "#921e26",
    "--vl-edge-color": "#b78b70",
    "--vl-light-color": "#fff4df",
    "--vl-hue": "356",
    "--vl-shadow-color": "#792125",
    "--vl-label-bg": "#921e26",
    "--vl-label-ink": "#fffaf0"
  }
}
```

## 已有配色的局部变体

秋日商业活动复用 [暖纸棕](palettes.md#palette.warm-paper)，草木和照片的真实秋色属于素材，不再登记近似的棕色方案。

金色猫粮参考复用 [糕点暖金](#palette.pastry-gold)。深色章节覆盖如下，浅色说明区继续使用原配方；金属光影与鱼油晶体仍由图像提供。

```json
{
  "base": "palette.pastry-gold",
  "overrides": {
    "--vl-tint": "#3a1d0c",
    "--vl-surface-end": "#9b6028",
    "--vl-ink": "#ffedbc",
    "--vl-muted-ink": "#e5c69a",
    "--vl-accent": "#edb54d",
    "--vl-edge-color": "#f8d99c",
    "--vl-label-bg": "#edb54d",
    "--vl-label-ink": "#3a1d0c"
  }
}
```


<a id="palette.antique-ochre"></a>

## 古纸赭黄墨棕

风格标签：通用。

视觉近似色值；只描述颜色角色，不单独推断整体风格。渐变使用 [通用渐变](palettes.md#color.gradient)，采用 `vl-antique-ochre vl-gradient--linear vl-paint-fill` 才消费渐变色标。

```css
.vl-antique-ochre {
 --vl-tint:#b5aa88; --vl-ink:#302b1b; --vl-muted-ink:#4e4935;
 --vl-accent:#8d481f; --vl-accent-2:#ddbe79; --vl-accent-3:#d4c9aa;
 --vl-label-bg:#302b1b; --vl-label-ink:#b5aa88; --vl-edge-color:#ddbe79;
 --vl-surface-end:#d4c9aa; --vl-light-color:#fff; --vl-shadow-color:#302b1b;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#b5aa88 0%,#b5aa88 65%,#d4c9aa 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

主底色、文字与标签成对应用；浅底纸面默认用纯色，渐变不是必选。强色章节需单独切换文字，不能只替换背景。真纸纹、缺墨字形和照片光影从其他原子／素材取得。

<a id="palette.tavern-umber-orange"></a>

## 酒馆红棕赭纸亮橙

风格标签：通用。

主题类限定变量作用域，不写全局样式；默认柜底#430f02、纸#A87548、奶油字#E5CDA9、亮橙#FF861D。可调整明度约±10%，保持柜底最暗、纸居中、正文与行动高亮的关系。向搁板及纸槽提供同名语义变量，组合须实际使用。色板四列，460px以下两列，文案可换行；无图像槽、无叠层要求。RetroSource正文400、标题650。照片不经过滤色，此色板不能替代真实木纹和纸纤维。

```json
{
  "dependencies": [],
  "asset_slots": [],
  "font_binding": {
    "family": "RetroSource",
    "catalog_id": "chinese-0010-font-4f8d31775b64",
    "file": "SourceHanSansSC-VF.otf",
    "range": "250–900",
    "status": "示例阅读黑体；原图艺术Logo作为独立素材，不声称字体精确复原",
    "additional_candidates": {
      "RetroDisplay": {
        "catalog_id": "chinese-0045-font-c817c7883480",
        "file": "DouyinSansBold.ttf",
        "weight": 400,
        "face": "Bold"
      },
      "RetroNarrow": {
        "catalog_id": "chinese-0194-font-3a657740be7a",
        "file": "ChillGSans.otf",
        "weight": 500,
        "face": "Medium",
        "source": "https://github.com/Warren2060/ChillGSans"
      }
    }
  }
}
```

```css
.vl-r9-palette{--vl-cabinet:#430f02;--vl-cabinet-deep:#2c0902;--vl-paper:#a87548;--vl-paper-deep:#8a5634;--vl-cream:#e5cda9;--vl-orange:#ff861d;--vl-orange-deep:#ef6810;--vl-ink:#431b0b;--vl-road:#414140;--vl-metal:#86766a;--vl-note:#c9c0ae;--vl-shelf-light:#aa531b;--vl-shelf-mid:#7f310a;--vl-shelf-dark:#3c1004;--vl-slot-housing:#604737;--vl-slot-bevel:#9b8069;--vl-slot-shadow:#20140e;--vl-slot-paper:var(--vl-paper);--vl-slot-ink:var(--vl-cream);color:var(--vl-cream);background-color:var(--vl-cabinet);font-family:RetroSource,sans-serif;font-weight:400}.vl-r9-palette-demo{box-sizing:border-box;max-width:658px;padding:clamp(20px,5%,34px)}.vl-r9-palette-demo h3{margin:0 0 20px;font-size:25px;font-weight:650}.vl-r9-palette-swatches{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.vl-r9-palette-swatch{padding:35px 8px 12px;min-width:0;font-size:13px;line-height:1.6;border-bottom:2px solid currentColor}.vl-r9-palette-swatch:nth-child(1){background:var(--vl-cabinet-deep);color:var(--vl-cream)}.vl-r9-palette-swatch:nth-child(2){background:var(--vl-paper);color:var(--vl-ink)}.vl-r9-palette-swatch:nth-child(3){background:var(--vl-cream);color:var(--vl-ink)}.vl-r9-palette-swatch:nth-child(4){background:var(--vl-orange);color:var(--vl-ink)}.vl-r9-palette-demo p{line-height:1.8;margin:22px 0 0}.vl-r9-palette-demo a{color:var(--vl-orange)}@media(max-width:460px){.vl-r9-palette-swatches{grid-template-columns:repeat(2,minmax(0,1fr))}}
```

```html
<section class="vl-r9-palette vl-r9-palette-demo"><h3>街区酒馆 · 语义色板</h3><div class="vl-r9-palette-swatches"><div class="vl-r9-palette-swatch">柜体深底<br>#430F02</div><div class="vl-r9-palette-swatch">赭色纸面<br>#A87548</div><div class="vl-r9-palette-swatch">奶油正文<br>#E5CDA9</div><div class="vl-r9-palette-swatch">行动亮橙<br>#FF861D</div></div><p>深红棕连接整页，赭纸承载规则，亮橙只强调路牌与行动。<a href="#vl-r9-palette-end">查看活动说明</a></p><p id="vl-r9-palette-end">照片保留青蓝霓虹、紫红灯光和植物绿色，不叠加统一褐色滤镜。</p></section>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：palette.tavern-umber-orange。验收限本条声明机制，不代表整页或原始字体精确复刻。
