# 胶囊与徽章

状态：已实现。

参考：图 1 的圆形标题字章、图 2 的圆形版本标、图 3 的 VS 标记。共享内容居中容器，圆形为胶囊的等宽高分支。

<a id="shape.badge"></a>

## 胶囊与徽章原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-badge-radius` | `999px` | 胶囊圆角；圆形也使用此值 |
| `--vl-badge-size` | `44px` | 圆形宽度，建议 24–80px |
| `--vl-badge-pad-x` | `14px` | 胶囊水平内边距 |
| `--vl-badge-pad-y` | `5px` | 胶囊垂直内边距 |
| `--vl-badge-border` | `1px` | 描边宽度 |

```css
.vl-badge { display:inline-grid; place-items:center; box-sizing:border-box; padding:var(--vl-badge-pad-y,5px) var(--vl-badge-pad-x,14px); border:var(--vl-badge-border,1px) solid var(--vl-edge-color,currentColor); border-radius:var(--vl-badge-radius,999px); background:var(--vl-label-bg,#c79a53); color:var(--vl-label-ink,#fff); line-height:1.2; }
.vl-badge--circle { width:var(--vl-badge-size,44px); aspect-ratio:1; padding:0; flex:none; text-align:center; }
```

```html
<span class="vl-badge">章节标签</span><span class="vl-badge vl-badge--circle">VS</span>
```

圆章仅放短字或图标；长文字使用胶囊并允许换行。中央 VS 的叠放位置由比较区布局负责，shape 只负责轮廓。字距、字号复用文字参数，不把圆章中的汉字拆成不可编辑图片。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="shape.warning-chevron-band"></a>

## 连续实心箭头警戒带

风格标签：通用。

形状由SVG实心多边形重复构成，配色独立由语义变量ground、warning、ink、paper和muted提供，不是细线之字纹。默认带高52px、倾角-9deg；推荐高度42–65px、倾角-8至-12deg。图案周期94px且纵向52px，改变带高时建议同步修改pattern的height和viewBox以保持箭头比例。单条满宽，不分列；容器负责裁掉旋转溢出。SVG为底层，组合掉墨层在其上，正文不放在带内。字体仅用于独立示例标签，正文400。参考黄黑节奏接近，具体污损不由此形状原子负责。

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
.vl-r3-band-demo{--vl-r3-ground:#242420;--vl-r3-warning:#d7dd16;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;--vl-r3-muted:#999781;max-width:658px;padding:42px 0;background:var(--vl-r3-ground);overflow:hidden;font-family:RetroSource,sans-serif}.vl-r3-band{--vl-r3-band-height:52px;--vl-r3-band-angle:-9deg;position:relative;width:110%;height:var(--vl-r3-band-height);margin-left:-5%;transform:rotate(var(--vl-r3-band-angle));background:var(--vl-r3-warning,#d7dd16);overflow:hidden;color:var(--vl-r3-ink,#292a21)}.vl-r3-band__arrows{display:block;width:100%;height:100%;fill:currentColor}.vl-r3-band-demo__label{display:block;margin:32px 24px 0;color:var(--vl-r3-paper);font-size:13px;letter-spacing:.12em}
```

```html
<div class="vl-r3-band-demo"><div class="vl-r3-band" role="img" aria-label="黄黑连续实心箭头警戒带"><svg class="vl-r3-band__arrows" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><pattern id="vl-r3-chevron-atom" width="94" height="52" patternUnits="userSpaceOnUse" viewBox="0 0 94 52"><path d="M-24 0H23L53 26 23 52H-24L6 26ZM70 0H117L147 26 117 52H70L100 26Z"/></pattern></defs><rect width="100%" height="100%" fill="url(#vl-r3-chevron-atom)"/></svg></div><span class="vl-r3-band-demo__label">ARCHIVE BOUNDARY / 档案现场边界</span></div>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：shape.warning-chevron-band。验收限本条声明机制，不代表整页或原始字体精确复刻。


<a id="shape.capsule-indicator"></a>

## 双层胶囊指示器

风格标签：通用。

外壳和内芯各自居中，border-box使内芯边框计入高度；外层相对标题条居中由组合负责。本原子为装饰指示器，不宣称开关交互或实时状态。

```css
.cs-capsule{position:relative;display:inline-block;box-sizing:border-box;flex:none;width:var(--cs-capsule-width,59px);height:var(--cs-capsule-height,14px);border-radius:999px;background:var(--cs-capsule-fill,#a7eed8);color:var(--cs-capsule-ink,#348f86);font:5px/1 Arial,sans-serif;letter-spacing:1px;padding:0 8px;text-shadow:none;vertical-align:middle}
.cs-capsule__label{position:absolute;left:8px;top:50%;transform:translateY(-50%)}
.cs-capsule::after{content:"";position:absolute;box-sizing:border-box;right:var(--cs-capsule-gap,3px);top:50%;transform:translateY(-50%);width:var(--cs-capsule-thumb-width,26px);height:calc(100% - 4px);border:1px solid var(--cs-capsule-thumb-edge,#7a8792);border-radius:999px;background:var(--cs-capsule-thumb,#26313c)}
```

```html
<span class="cs-capsule" aria-hidden="true"><span class="cs-capsule__label">ON</span></span>
```
