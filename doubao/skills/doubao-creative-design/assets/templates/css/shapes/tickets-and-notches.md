# 票券与缺口

状态：已实现。

参考：图 7 的小邮票。重复圆孔切边是新轮廓机制；普通照片白边继续用矩形容器加 padding。

<a id="shape.perforated-paper"></a>

## 票券与缺口原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-perf-step` | `14px` | 孔距，建议 10–20px |
| `--vl-perf-radius` | `3px` | 孔半径，应小于 step/2 |
| `--vl-perf-inset` | `14px` | 正文离边距离，应大于 radius + 4px |

```css
.vl-perforated { box-sizing:border-box; padding:var(--vl-perf-inset,14px); background:var(--vl-tint,#f0f1df); color:var(--vl-ink,#405332); mask:radial-gradient(circle at 50% 0,transparent var(--vl-perf-radius,3px),#000 calc(var(--vl-perf-radius,3px) + .5px)) 0 0 / var(--vl-perf-step,14px) 100% repeat-x,radial-gradient(circle at 50% 100%,transparent var(--vl-perf-radius,3px),#000 calc(var(--vl-perf-radius,3px) + .5px)) 0 0 / var(--vl-perf-step,14px) 100% repeat-x,radial-gradient(circle at 0 50%,transparent var(--vl-perf-radius,3px),#000 calc(var(--vl-perf-radius,3px) + .5px)) 0 0 / 100% var(--vl-perf-step,14px) repeat-y,radial-gradient(circle at 100% 50%,transparent var(--vl-perf-radius,3px),#000 calc(var(--vl-perf-radius,3px) + .5px)) 0 0 / 100% var(--vl-perf-step,14px) repeat-y; mask-composite:intersect; }
```

```html
<figure class="vl-perforated"><img src="邮票内图素材" alt="邮票图案" style="display:block;width:100%;height:auto"><figcaption>短标题</figcaption></figure>
```

轻微旋转可用已有 rotate 参数在外包装应用 transform，不再新增倾斜原子。此分支是规则邮票齿孔，不等于随机撕纸边；元素高度变化时末端孔距可能不对称。mask 会裁切本层投影和轮廓，投影或交互焦点放在外包装。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="shape.torn-paper"></a>

## 不规则撕纸边

风格标签：通用。

参考秋日商业活动的优惠纸张与拼贴纸面。撕边和已有规则邮票齿孔是两种轮廓机制。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-tear-inset` | `20px` | 内容安全距离；建议 16–32px，按实际缩放检查 |

```css
.vl-torn-paper { padding:var(--vl-tear-inset,20px); background:var(--vl-tint,transparent); color:var(--vl-ink,#382b20); mask-image:url("asset:svg/paper-torn.svg"); mask-size:100% 100%; mask-repeat:no-repeat; overflow-wrap:anywhere; }
```

```html
<section class="vl-torn-paper"><h2>纸片标题</h2><p>纸片正文</p></section>
```

撕边只规定轮廓，不指定纸色。当前 HTML 实现 显式传入 --vl-tint 与配套文字色；未传时保持透明。需要可见纸片边界时必须落实有区别的表面色或纹理，透明不算纸片效果已完成，也不以默认米色补齐。

纸纹另选 [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)，不把形状与纹理烘焙成一张图。此 SVG 按 3:4 近似轮廓制作；极宽或极长容器会拉伸撕边，需要按最终比例调整 SVG，边缘起伏不伪装成外层 CSS 参数。阴影放到外包装，避免被 mask 裁掉。

<a id="shape.paired-waist-ticket"></a>

## 双侧单腰缺口票面

风格标签：通用。

形状与配色分离，通过ticket-paper、ticket-ink、ticket-accent接收色板；本例提供独立默认色。默认宽度上限180px、缺口半径9px，建议7–10px；腰线默认55%，建议52%–58%。两张径向遮罩取交集，严格每侧一个半圆孔，孔内真实透出父背景，不以底色圆覆盖。表面层z=-1、内容正常层，颗粒只覆盖券脚且不改变内容透明度。金额Arial 800是运动数字的近似，正文RetroSource 400、券脚700；未复原原图方块字形。门槛建议1–2行，长文增加票高时需联调腰线，不能将缺口变成重复齿孔。原子不负责列数。

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
.vl-r8-ticket{--ticket-paper:#fff;--ticket-ink:#080909;--ticket-accent:#24afd2;--ticket-notch:9px;--ticket-waist:55%;position:relative;isolation:isolate;width:100%;max-width:180px;min-height:148px;color:var(--ticket-ink);font-family:RetroSource,sans-serif;font-weight:400;filter:drop-shadow(0 -3px 5px #0003)}.vl-r8-ticket__surface{position:absolute;inset:0;z-index:-1;border-radius:16px 16px 9px 9px;background:linear-gradient(to bottom,var(--ticket-paper) 0 76%,var(--ticket-accent) 76% 100%);-webkit-mask-image:radial-gradient(circle var(--ticket-notch) at 0 var(--ticket-waist),transparent 98%,#000 100%),radial-gradient(circle var(--ticket-notch) at 100% var(--ticket-waist),transparent 98%,#000 100%);-webkit-mask-composite:source-in;mask-image:radial-gradient(circle var(--ticket-notch) at 0 var(--ticket-waist),transparent 98%,#000 100%),radial-gradient(circle var(--ticket-notch) at 100% var(--ticket-waist),transparent 98%,#000 100%);mask-composite:intersect}.vl-r8-ticket__amount{box-sizing:border-box;min-height:83px;display:flex;align-items:center;justify-content:center;gap:5px;padding:12px 12px 6px;font-family:Arial,sans-serif;font-size:48px;font-weight:800;line-height:1;letter-spacing:-3px}.vl-r8-ticket__currency{align-self:flex-start;margin-top:10px;font-size:14px;font-weight:700;letter-spacing:0}.vl-r8-ticket__condition{margin:0 14px;padding:5px 0 6px;border-top:1px dashed #8888;text-align:center;font-size:15px;line-height:1.4;overflow-wrap:anywhere}.vl-r8-ticket__foot{position:relative;overflow:hidden;min-height:29px;display:grid;place-items:center;padding:2px 8px;color:var(--ticket-paper);font-size:14px;line-height:1.5;font-weight:700;text-align:center}.vl-r8-ticket__foot:after{content:'';position:absolute;inset:0;pointer-events:none;background:url('asset:svg/screen-grain.svg') repeat;opacity:.07}
```

```html
<article class="vl-r8-ticket" aria-label="满100元减10元优惠券"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>10</div><p class="vl-r8-ticket__condition">满100可用</p><div class="vl-r8-ticket__foot">优惠券</div></article>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：shape.paired-waist-ticket。验收限本条声明机制，不代表整页或原始字体精确复刻。


<a id="shape.arc-notched-stub"></a>

## 连续圆弧缺口票根

风格标签：通用。

使用同一闭合路径绘制底色与描边，底边8个圆弧缺口。此预设随viewBox缩放，不宣称孔径与数量可直接通过CSS独立改变；需要不同孔数时重新构造路径并验证。无名单、条码或上部票面语义。

```css
.cs-stub{position:relative;isolation:isolate;padding:18px 24px 32px;--cs-stub-fill:#e2e6ef;--cs-stub-stroke:#72809a}
.cs-stub__skin{position:absolute;inset:0;width:100%;height:100%;z-index:-1;pointer-events:none;overflow:visible}
.cs-stub__outline{fill:var(--cs-stub-fill);stroke:var(--cs-stub-stroke);stroke-width:1;vector-effect:non-scaling-stroke}
```

```html
<div class="cs-stub"><svg class="cs-stub__skin" viewBox="0 0 552 120" preserveAspectRatio="none" aria-hidden="true"><path class="cs-stub__outline" d="M20 .7H532Q551.3 .7 551.3 20V100Q551.3 119.3 532 119.3H496A12 12 0 0 0 472 119.3H437A12 12 0 0 0 413 119.3H378A12 12 0 0 0 354 119.3H319A12 12 0 0 0 295 119.3H260A12 12 0 0 0 236 119.3H201A12 12 0 0 0 177 119.3H142A12 12 0 0 0 118 119.3H83A12 12 0 0 0 59 119.3H20Q.7 119.3 .7 100V20Q.7 .7 20 .7Z"/></svg><p>票根附注与说明</p></div>
```
