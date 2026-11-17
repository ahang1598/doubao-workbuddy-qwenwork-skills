# 沉稳理性

状态：已填充。

共用 [语义颜色参数](palettes.md#colors.parameters)，不新增色彩实现。将 overrides 写到目标节点；已有组件会定义自己的默认变量，所以只设在页面祖先上不能覆盖组件默认值。纯页面使用 `background:var(--vl-tint);color:var(--vl-ink)`，不要求套用材质卡片。

<a id="palette.clinical-cyan"></a>

## 净白青蓝

风格标签：通用。

参考：本批图 2 的背景、文字与章节色块；颜色是视觉估计值，面积比例是排版建议。

白底约 85%，黑灰文字约 10%，青蓝强调约 5%；参考图的亮青可用于装饰，正文强调采用较深青色。

```json
{
  "id": "palette.clinical-cyan",
  "kind": "palette",
  "overrides": {
    "--vl-tint": "#f7f8f6",
    "--vl-surface-end": "#e9f1ee",
    "--vl-ink": "#171a1a",
    "--vl-muted-ink": "#596365",
    "--vl-accent": "#087f89",
    "--vl-edge-color": "#c7d8d7",
    "--vl-light-color": "#ffffff",
    "--vl-hue": "184",
    "--vl-shadow-color": "#171a1a",
    "--vl-label-bg": "#087f89",
    "--vl-label-ink": "#fffaf0"
  }
}
```


<a id="palette.science-blue-orange"></a>

## 科研蓝白橙

风格标签：通用。

参考蓝白成长营养详情页。以下为视觉估计与可调起点，不是源设计精确色值。与净白青蓝的区别在深蓝主场、灰白信息区和橙色点强调；共用 [颜色角色](palettes.md#colors.parameters) 与 [渐变](palettes.md#color.gradient)。

```css
.vl-science-light {
 --vl-tint:#f3f4f2; --vl-ink:#124f9d; --vl-muted-ink:#505b68;
 --vl-accent:#ff650e; --vl-accent-2:#1a62bc; --vl-accent-3:#092d8a;
 --vl-label-bg:#1455a9; --vl-label-ink:#fff; --vl-edge-color:#c8cdd2;
 --vl-surface-end:#e5eaf0; --vl-shadow-color:#153b62; --vl-light-color:#fff;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#fafaf8 0%,#f3f4f2 64%,#e5eaf0 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
.vl-science-dark {
 --vl-tint:#09278f; --vl-ink:#fff; --vl-muted-ink:#e0ecff;
 --vl-accent:#ff650e; --vl-accent-2:#60a0e1; --vl-accent-3:#d8eafa;
 --vl-label-bg:#f5f7fa; --vl-label-ink:#124f9d; --vl-edge-color:#86add8;
 --vl-surface-end:#397acd; --vl-shadow-color:#06184e; --vl-light-color:#fff;
 --vl-gradient-angle:180deg; --vl-gradient-stops:#081b87 0%,#1045ae 46%,#619cda 100%;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

light / dark 二选一应用到章节节点；渐变需要该节点同时使用 `vl-gradient--linear vl-paint-fill` 才消费 stops。暗色标题用白色，橙色只作箭头／短标记，细小橙色正文不直接叠亮蓝底。两种状态同时定义所有上述颜色角色，避免换底不换字。白色比较区正文使用 muted-ink，产品强调列用蓝底白字。轻微灰白变化不能代替产品照片中的真实照明。

<a id="palette.silver-cyan-mono"></a>

## 冷银墨黑青蓝

风格标签：通用。

本原子仅定义语义颜色、字体基线和独立可见色板示例，不定义票形。冷银默认#bdc8c8、青蓝#24afd2，环境粉绿建议透明度10%–35%，黄色只用于标题短划。颗粒默认5.5%，建议4%–8%，由组合独立伪层实现，不能称为纸纤维。正文RetroSource 400，标题700，数字可用Arial或Georgia。色板四列仅为示例；组合可以改券阵和商品列数，语义变量名不随列数变化。无图片槽位，背景层在文字后。

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
.vl-r8-palette{--vl-silver:#bdc8c8;--vl-silver-light:#e3e9e8;--vl-silver-deep:#899b9e;--vl-ink:#050707;--vl-paper:#fff;--vl-cyan:#24afd2;--vl-metal-light:#f4f8f8;--vl-metal-mid:#aab7be;--vl-metal-dark:#485158;--vl-ambient-green:#c1d29f;--vl-ambient-pink:#d7c2ce;--vl-spark:#e8c75e;--vl-grain-opacity:.055;color:var(--vl-ink);background-color:var(--vl-silver);font-family:RetroSource,sans-serif;font-weight:400}.vl-r8-palette__demo{box-sizing:border-box;max-width:658px;padding:clamp(20px,5%,36px);background:radial-gradient(ellipse at 100% 0,#c1d29f66,transparent 42%),linear-gradient(120deg,var(--vl-silver-light),var(--vl-silver) 56%,var(--vl-silver-deep))}.vl-r8-palette__demo h2{margin:0 0 12px;font-size:26px;font-weight:700}.vl-r8-palette__demo p{margin:0;font-size:15px;line-height:1.8}.vl-r8-palette__swatches{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:22px}.vl-r8-palette__swatch{padding:22px 3px 10px;text-align:center;font:12px Arial,sans-serif;background:var(--swatch);color:var(--swatch-text,var(--vl-ink));box-shadow:inset 0 0 0 1px #0002}.vl-r8-palette__swatch--silver{--swatch:var(--vl-silver)}.vl-r8-palette__swatch--ink{--swatch:var(--vl-ink);--swatch-text:var(--vl-paper)}.vl-r8-palette__swatch--paper{--swatch:var(--vl-paper)}.vl-r8-palette__swatch--cyan{--swatch:var(--vl-cyan)}
```

```html
<section class="vl-r8-palette vl-r8-palette__demo"><h2>冷银 · 星光</h2><p>连续冷银底承载墨黑正文，纸白负责反白层级，青蓝只用于优惠券等小面积重点。</p><div class="vl-r8-palette__swatches"><span class="vl-r8-palette__swatch vl-r8-palette__swatch--silver">SILVER</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--ink">INK</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--paper">WHITE</span><span class="vl-r8-palette__swatch vl-r8-palette__swatch--cyan">CYAN</span></div></section>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：palette.silver-cyan-mono。验收限本条声明机制，不代表整页或原始字体精确复刻。
