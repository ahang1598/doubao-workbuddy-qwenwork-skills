# 聚焦主场

状态：已实现。

参考：图 4 / 5 的整幅摄影与图 6 的产品主场。共用主图与可调文字区；遮光层仅在图片叠字确有对比不足时按需添加，商品抠图可以改用 contain。

<a id="layout.image-stage"></a>

## 聚焦主场原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-stage-ratio` | `5 / 9` | 容器宽／高；作为正式 Hero 时按统一优先级落实高度，完整命名配方或用户要求须显式传入；参考图自身比例不构成覆盖依据 |
| `--vl-stage-height` | `auto` | 可选最小高度；固定画布时可填 HTML 实现 段高，不以统一像素值代替比例 |
| `--vl-stage-fit` | `cover` | cover / contain |
| `--vl-stage-position` | `50% 50%` | 图片焦点位置 |
| `--vl-stage-align` | `end` | 文字区纵向 start / center / end |
| `--vl-stage-padding` | `32px` | 文字安全距离 |
| `--vl-stage-scrim` | `0` | 默认关闭；启用时按文字区域对比决定强度，0–.65 |
| `--vl-stage-scrim-paint` | `none` | 按背景与文字明确渐变方向、逐色标颜色与透明度，不默认黑色 |
| `--vl-stage-scrim-inset` | `auto` | 启用时明确 top/right/bottom/left，使遮光只覆盖需要的区域 |

```css
.vl-stage { position:relative; isolation:isolate; display:grid; width:100%; box-sizing:border-box; aspect-ratio:var(--vl-stage-ratio,5 / 9); min-height:var(--vl-stage-height,auto); background:var(--vl-tint,transparent); }
.vl-stage__image { position:absolute; inset:0; width:100%; height:100%; object-fit:var(--vl-stage-fit,cover); object-position:var(--vl-stage-position,50% 50%); z-index:-2; }
.vl-stage__scrim { position:absolute; inset:var(--vl-stage-scrim-inset,auto); background:var(--vl-stage-scrim-paint,none); opacity:var(--vl-stage-scrim,0); z-index:-1; pointer-events:none; }
.vl-stage__content { align-self:var(--vl-stage-align,end); padding:var(--vl-stage-padding,32px); min-width:0; overflow-wrap:anywhere; }
```

```html
<section class="vl-stage">
  <img class="vl-stage__image" src="主图素材" alt="商品或场景说明">
  <div class="vl-stage__content"><h2>主场标题</h2><p>说明文字</p></div>
</section>
```

主图容器不预设底色：未传 --vl-tint 时保持透明，显示已规划的父层背景。需要独立底色的主场必须在 HTML 实现 绑定实际背景色及配套文字色；透明不代表背景已完成，素材缺失时也不以默认颜色兜底。

比例参数控制整个 section，图片随容器填充；它不是 `object-fit` 参数。1080px 宽在通用默认下得到 1944px 高；正式 Hero 按[纵向空间规则](../../../../references/style/coding/composition-layout.md#正式-hero-的纵向空间)落实用户要求、完整命名配方或通用默认，内页摄影段单独定高，不能把所有段变成同样高。生成正式固定画布 HTML 时将选定比例换算为实际段高；移动端预览整体等比缩放。

作为正式 Hero 时，先按统一优先级锁定高度，再在该槽位内调整文字位置、层级、断行与素材净空；内容无法安全容纳时说明冲突，不让容器自动增高、缩字或裁切正文。仅用于非 Hero 的弹性内容模块时，才允许随内容自然增高并同步后续段。图片叠字仍不足以保证对比时，才添加 vl-stage__scrim 节点并在 HTML 实现中绑定区域、方向、色标和强度；一体化 Hero 已有图内标题时不自动追加 DOM 标题或遮光。遮光只服务文字对比，不作为跨屏接缝、卡片投影或统一氛围效果。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="layout.dual-anchor-scene"></a>

## 双端文案场景布局

ID：`layout.dual-anchor-scene`。所属文档：`layouts.hero-focus`。分类／风格标签：通用。

`layout.image-stage`的显式双端变体：顶部、底部均正常流，中间弹性空场保留可调最小高度。复用基础场景的定位、隔离、宽度、比例及覆盖图片，不复制基础原子代码；不是摄影或配色预设。

```json
{"dependencies":["layout.image-stage"],"optional_features":[{"class":"vl-stage__scrim","optional":true,"status":"最小示例未启用"}],"asset_slots":[{"id":"scene-background","optional":false,"role":"场景覆盖背景；通过background_url绑定经核验的图像，按fit与position适配，不参与正常流段高"}]}
```

### 参数

| 参数 | 默认值 | 作用 |
|---|---|---|
| --vl-dual-safe | 120px | 中央空场min-height；非负长度，不使用百分比 |
| --vl-dual-padding | 24px | 根容器四边安全距离；可用四值简写，非负 |
| --vl-stage-ratio | 5 / 9 | 继承基础原子的宽／高默认值；作为正式 Hero 时按统一优先级显式落实所选高度 |
| --vl-stage-height | auto | 继承基础原子的最小高度，不是固定height |
| --vl-stage-fit | cover | 继承图片适配，可改contain |
| --vl-stage-position | 50% 50% | 继承图片焦点 |

### 完整变体CSS

先加载`layout.image-stage`，再加载以下全部增量；单独这一段不包含基础原子的图片覆盖实现。

```css
.vl-stage.vl-dual-scene{display:flex;flex-direction:column;height:auto;max-height:none;min-width:0;padding:var(--vl-dual-padding,24px);overflow:visible;overflow-wrap:anywhere}
.vl-dual-scene>.vl-dual-scene__top,.vl-dual-scene>.vl-dual-scene__bottom{position:relative;display:flow-root;flex:0 0 auto;min-width:0;margin:0}
.vl-dual-scene>.vl-dual-scene__space{flex:1 0 auto;min-height:var(--vl-dual-safe,120px);margin:0;padding:0;pointer-events:none}
```

### 最小HTML

`{{background_url}}`替换为经核验的背景图像URL。下列比例只演示局部布局，不是正式 Hero 的高度依据；用于正式 Hero 时须替换为按统一优先级选定的比例。背景作为装饰时保持空alt；有信息含义的素材须另提供可访问文本。

```html
<section class="vl-stage vl-dual-scene" style="--vl-stage-ratio:364 / 602;--vl-dual-safe:120px" aria-label="双端布局测试">
  <img class="vl-stage__image" src="{{background_url}}" alt="">
  <header class="vl-dual-scene__top"><h2>顶部正常流文案</h2><p>文字变长时自然换行。</p></header>
  <div class="vl-dual-scene__space" aria-hidden="true"></div>
  <footer class="vl-dual-scene__bottom"><p>底部正常流文案，内容增长不得被裁切。</p></footer>
</section>
```

### 已验证范围

独立加载基础CSS与变体CSS，在280/320/364px宽度、safe为96/160px、普通及长文本压力两种状态下完成12组本地浏览器测试，报告均无错误。普通文本中带约314.30—475.63px；长文本中带保持所设96/160px，容器自然增高，未报告水平溢出。普通文本截图显示上下文案与中央空场分离。120px是默认值及示例值，不属于上述12组参数矩阵。

未加载变体的对照在同一新合同下有8组不通过，仅说明基础布局不提供双端安全带与相应长文本保护，不能解释为基础原子原有合同失效。

reference使用中性图像，仅验证双端正常流、最小净空和流式增长机制，不验证整图、摄影主体、纹理或配色。集成验收应检查无水平溢出、top.bottom≤space.top、space.height≥safe、space.bottom≤bottom.top、容器包住底部文字，以及覆盖背景随容器增长。

### 使用边界

- 作为非 Hero 弹性模块时，不设固定 height/max-height，不对根或文案 clip，长文可让容器增长；作为正式 Hero 时显式落实已选高度，超量内容返回构图或尺寸冲突处理，不自动增高、裁切或缩字。
- 安全带只保证两个文案块之间的几何距离，不保证摄影主体始终位于该带；不得通过增大安全带替代素材焦点验证。
- 顶部、空场、底部须为根容器的直接子节点。顶部和底部只挂对应包装类，不再挂带padding的`vl-stage__content`；内部标题、段落间距及排版由调用者提供。
- 素材、色彩、字体、纹理、徽章和拼贴不属于本原子。需要圆角裁图时仅处理背景层，不得裁掉正文。
- 已有组合只有在实际加载CSS、迁移节点并移除冲突布局后，才构成对此原子的调用；结构相似不等于已采用。
