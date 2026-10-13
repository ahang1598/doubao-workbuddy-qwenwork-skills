# 展开图文关系

用途：可复用的展开布局；风格：通用。适用于三折页、画册及横向展开，不定义折法。下列 CSS 与 HTML 是配套实现源，正式交付展开为行内样式。样本 900×570；宽高、视觉分区、字级与安全距按实际内容覆盖。物理面序、折线、出血沿用品类 Spec，不把视觉网格当刀版。

规划按策略名称、采用区域与图文关系选择，再读取该节 CSS 和节点骨架；无需填写布局编号。各节可独立使用，无必需外部 CSS。图片路径为待绑定槽位，必须替换就绪资产；布局不生成摄影、插画或材质。固定印刷尺寸内先用实际文案试排，不增高纸面或隐藏正文溢出；跨面文字按完整字词排布，折线避开字形及关键事实。裁切只作用于指定图窗，背景、文字不继承其 clip-path。

## 独立视觉分区与跨区内容

风格标签：通用。适用：需要深浅分区、图文穿插或跨区题注；视觉分界与文字归属不重合。来自[植物四区展开](../combinations/recipes.md#combination.four-zone-imagery)的关系提炼；不同于普通 grid，本条把背景色区与内容网格分层，内容可跨背景边界。

布局：背景区是共同展开层的绝对定位子节点；正文／图窗通过列跨度占据真实网格位置，题注另占一行，不靠越界塞入相邻面。`--vl-zones-columns` 默认四视觉区；`--vl-zones-start/span` 控制内容范围；各背景节点显式给出覆盖矩形。改成三折时可保留四视觉区，再独立避让三片物理折面，不机械变成三列。

```css
.vl-spread-zones { position:relative; isolation:isolate; display:grid; grid-template-columns:var(--vl-zones-columns,repeat(4,minmax(0,1fr))); grid-template-rows:auto minmax(0,1fr); width:100%; height:var(--vl-zones-height,570px); background:var(--vl-zones-base,#fff); box-sizing:border-box; }
.vl-spread-zones__paint { position:absolute; z-index:0; pointer-events:none; background:var(--vl-zone-paint,#20372d); }
.vl-spread-zones__content { position:relative; z-index:1; grid-column:var(--vl-zones-start,1)/span var(--vl-zones-span,1); grid-row:var(--vl-zones-row,2); min-width:0; padding:var(--vl-zones-inset,24px); box-sizing:border-box; overflow-wrap:anywhere; }
.vl-spread-zones__content img { display:block; width:100%; height:var(--vl-zones-image-height,260px); object-fit:cover; object-position:var(--vl-zones-focus,50% 50%); }
```

```html
<section class="vl-spread-zones">
  <div class="vl-spread-zones__paint" style="inset:0 0 0 75%"></div>
  <div class="vl-spread-zones__paint" style="inset:55% 0 0 50%"></div>
  <header class="vl-spread-zones__content" style="--vl-zones-row:1;--vl-zones-start:1;--vl-zones-span:3"><h2 style="margin:0">共享题注横跨视觉区</h2></header>
  <article class="vl-spread-zones__content" style="--vl-zones-start:1;--vl-zones-span:2"><img src="assets/scene.jpg" alt="主场景"><p>图窗跨两个视觉区，说明随图归组。</p></article>
  <article class="vl-spread-zones__content" style="--vl-zones-start:3"><p>短说明留在浅底区域；下部背景独立延续。</p></article>
  <article class="vl-spread-zones__content" style="--vl-zones-start:4;color:#fff"><p>深底索引</p></article>
</section>
```

验收：调整背景分界不应带动题注或图窗重新分栏；共享深底不能被内容节点的不透明底遮断。文字跨深浅区时分别绑定墨色或移动文字，不给全图统一加暗罩。

## 跨分界错层图窗

风格标签：通用。适用：图窗跨越深浅背景的水平分界、下接独立标题与正文。提炼自[室内切角图窗](../combinations/recipes.md#combination.offset-cut-window)；不继承室内题材、色板或照片。

布局：共同背景分界独立于三列内容。图窗跨上下两带的连接由 `--vl-window-cross` 控制，图下正文通过等量净距真实避让，不用负间距。`--vl-window-split` 为上带高度，`--vl-window-columns` 为视觉列宽；切角是图窗边缘的可选覆盖，不是正文裁切。需要不切角时设置 `--vl-window-clip:none`。

```css
.vl-spread-window { position:relative; isolation:isolate; display:grid; grid-template-columns:var(--vl-window-columns,1fr 1.15fr 1fr); grid-template-rows:var(--vl-window-split,250px) minmax(0,1fr); width:100%; height:var(--vl-window-height,570px); --vl-window-cross:40px; background:var(--vl-window-base,#fff); box-sizing:border-box; }
.vl-spread-window__band { position:absolute; inset:0 0 auto; height:var(--vl-window-split,250px); background:var(--vl-window-paint,#233c35); z-index:0; pointer-events:none; }
.vl-spread-window__side { position:relative; z-index:1; grid-row:1/3; min-width:0; padding:24px; box-sizing:border-box; overflow-wrap:anywhere; }
.vl-spread-window__media { position:relative; z-index:2; grid-column:2; grid-row:1; align-self:end; height:calc(100% - 36px); margin:0 20px; transform:translateY(var(--vl-window-cross)); }
.vl-spread-window__media img { display:block; width:100%; height:100%; object-fit:cover; object-position:var(--vl-window-focus,50% 50%); clip-path:var(--vl-window-clip,polygon(0 0,100% 0,100% 86%,86% 100%,0 100%)); }
.vl-spread-window__copy { position:relative; z-index:1; grid-column:2; grid-row:2; min-width:0; padding:calc(var(--vl-window-cross) + 20px) 20px 24px; box-sizing:border-box; overflow-wrap:anywhere; }
```

```html
<section class="vl-spread-window">
  <div class="vl-spread-window__band" aria-hidden="true"></div>
  <aside class="vl-spread-window__side" style="grid-column:1"><h2 style="color:#fff;margin:0">场景导语</h2></aside>
  <figure class="vl-spread-window__media"><img src="assets/detail.jpg" alt="跨分界的局部图窗"></figure>
  <article class="vl-spread-window__copy"><h3 style="margin:0 0 12px">图片下方的说明</h3><p style="margin:0">正文与照片独立，留出跨界深度和图文净距。</p></article>
  <aside class="vl-spread-window__side" style="grid-column:3"><p style="color:#fff;margin:0">辅助信息</p></aside>
</section>
```

验收：图窗下沿超过色带分界且距正文至少 20px；改变 cross 后正文同步避让。split、cross、正文容量须共同适配固定高度；跨折图窗另查主体安全，必要时移动或缩窄图窗而非取消整个错层关系。

## 跨列标题与独立信息行

风格标签：通用。适用：标题建立展开视觉轴，事实回到各自阅读列。提炼自[会议跨列标题](../combinations/recipes.md#combination.spanning-display-title)，不绑定红色或会议题材。

布局：标题占真实网格行，后续信息进入下一行，不以大字溢出邻栏模拟跨列。`--vl-title-columns` 控制列宽，`--vl-title-start/span` 控制标题跨度；自然标题高度决定下行起点，固定纸面剩余高度仍须容纳正文。字号是实例参数，正文不继承大字级。

```css
.vl-spread-title { display:grid; grid-template-columns:var(--vl-title-columns,repeat(3,minmax(0,1fr))); grid-template-rows:auto minmax(0,1fr); width:100%; height:var(--vl-title-height,570px); isolation:isolate; box-sizing:border-box; }
.vl-spread-title__lead { grid-column:1; grid-row:1; padding:26px; min-width:0; box-sizing:border-box; }
.vl-spread-title__heading { grid-column:var(--vl-title-start,2)/span var(--vl-title-span,2); grid-row:1; margin:0; padding:26px; min-width:0; box-sizing:border-box; font-size:var(--vl-title-size,64px); line-height:1.08; overflow-wrap:anywhere; }
.vl-spread-title__column { grid-row:2; min-width:0; padding:26px; box-sizing:border-box; overflow-wrap:anywhere; }
```

```html
<section class="vl-spread-title">
  <aside class="vl-spread-title__lead">主题简介</aside>
  <h2 class="vl-spread-title__heading">跨列主题标题</h2>
  <article class="vl-spread-title__column" style="grid-column:1">左列事实</article>
  <article class="vl-spread-title__column" style="grid-column:2">中列信息</article>
  <article class="vl-spread-title__column" style="grid-column:3">右列行动</article>
</section>
```

验收：长标题换行后，下排整体下移且无重叠。三折页中按实际折线对完整词组分段定位；grid 跨列本身不保证字形避折。标题改为跨全宽时，移动或移除 lead 的同格占位，不能将其压在标题下。

## 连续场景与局部阅读区

风格标签：通用。适用：共享插画／摄影跨面延展，其上布置独立阅读区与局部证据图窗。提炼自[植物展开](../combinations/recipes.md#combination.four-zone-imagery)与[暗花编辑展开](../combinations/recipes.md#combination.dark-editorial)。区别于单图 hero：场景只在展开共同层取景一次，各阅读区独立定位，不逐面重设背景。

布局：`--vl-scene-columns` 决定阅读区网格；场景作为一个全幅图片层。阅读面默认透明，`--vl-scene-reading-paint` 仅在选定区域覆盖为不透明或半透明色，不让文字跟随透明。素材必须提供叠字净空，或在必要区域承托；场景未就绪时不能用 CSS 图标宣称插画完成。

```css
.vl-spread-scene { position:relative; isolation:isolate; display:grid; grid-template-columns:var(--vl-scene-columns,repeat(3,minmax(0,1fr))); width:100%; height:var(--vl-scene-height,570px); box-sizing:border-box; }
.vl-spread-scene__image { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; object-position:var(--vl-scene-focus,50% 50%); z-index:0; }
.vl-spread-scene__reading { position:relative; z-index:1; grid-column:var(--vl-scene-start,1)/span var(--vl-scene-span,1); grid-row:1; min-width:0; margin:var(--vl-scene-margin,24px); padding:var(--vl-scene-inset,20px); background:var(--vl-scene-reading-paint,transparent); box-sizing:border-box; overflow-wrap:anywhere; }
.vl-spread-scene__window { display:block; width:100%; height:var(--vl-scene-window-height,150px); object-fit:cover; object-position:var(--vl-scene-window-focus,50% 50%); margin:16px 0; }
```

```html
<section class="vl-spread-scene">
  <img class="vl-spread-scene__image" src="assets/panorama.jpg" alt="连续展开场景">
  <article class="vl-spread-scene__reading" style="--vl-scene-start:1"><h2>场景净空中的标题</h2><p>本区依赖实际图片的文字净空。</p></article>
  <article class="vl-spread-scene__reading" style="--vl-scene-start:2;--vl-scene-reading-paint:#fff"><h3>独立阅读区</h3><p>承托只覆盖必要正文范围。</p></article>
  <article class="vl-spread-scene__reading" style="--vl-scene-start:3"><img class="vl-spread-scene__window" src="assets/evidence.jpg" alt="独立证据图窗"><p>局部图窗有自己的取景与图注。</p></article>
</section>
```

验收：改变面宽后仍只有一次全景取景；图窗裁切不改变背景，阅读区不自动变为三张同款卡片。插画人物、医生照片、解剖图等素材职责不可互换；若需跨两面图窗，可组合跨区网格，不用拉伸原图。
