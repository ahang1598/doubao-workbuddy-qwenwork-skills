# 连续流动

状态：已实现。

参考：图 1 的连续章节、图 4 的酒红色块接续、图 5 / 7 的照片与文字章交替。统一垂直节奏，不固定业务章节数。

<a id="layout.chapter-flow"></a>

## 连续流动原子

风格标签：通用。

| 参数 | 默认值 | 调整与作用 |
|---|---|---|
| `--vl-flow-gap` | `0px` | 连续照片设 0；独立章节可设 12–48px |
| `--vl-section-space` | `48px` | 非满幅章节上下留白 |
| `--vl-section-inset` | `7%` | 非满幅章节左右留白 |

```css
.vl-flow { display:grid; gap:var(--vl-flow-gap,0px); }
.vl-flow > section { min-width:0; }
.vl-flow__section { padding:var(--vl-section-space,48px) var(--vl-section-inset,7%); }
.vl-flow__bleed { padding:0; }
.vl-flow__bleed > img { display:block; width:100%; height:auto; }
```

```html
<main class="vl-flow"><section class="vl-flow__bleed">满幅主图</section><section class="vl-flow__section">文字与证据</section><section class="vl-flow__bleed">下一章主图</section></main>
```

照片章和内容章可按需重复；局部网格放在章节内部。相邻同色区使用同一颜色变量，可连续接底；切换深浅底时同时显式切换 ink。跨段浮动物体需要专门的叠层实现，本原子不包含破框动效。

实现值为视觉近似和可调起点，不是原设计源文件的精确数值。CSS 为生成阶段实现源；正式交付按现有协议展开为行内样式。

<a id="layout.route-flow"></a>

## S 形导览线

风格标签：通用。

参考创作小镇的道路动线。在已有章节流后方增加可重复的 S 形虚线；街屋、招牌与舞台仍为素材。

| 参数 | 默认值 | 作用与调整 |
|---|---|---|
| `--vl-route-step` | `640px` | 一个完整 S 的高度，按章节节奏设定 |
| `--vl-route-color` | `#a5edff` | 导览线颜色 |
| `--vl-route-opacity` | `.7` | 只影响导览线 |
| `--vl-route-phase` | `0px` | 纵向重复起点 |

```css
.vl-route { position:relative; isolation:isolate; }
.vl-route__line { position:absolute; inset:0; z-index:-1; pointer-events:none; background:var(--vl-route-color,#a5edff); opacity:var(--vl-route-opacity,.7); mask-image:url("asset:svg/route-s.svg"); mask-size:100% var(--vl-route-step,640px); mask-position:0 var(--vl-route-phase,0px); mask-repeat:repeat-y; }
```

```html
<main class="vl-flow vl-route"><span class="vl-route__line" aria-hidden="true"></span><section class="vl-flow__section">第一站</section><section class="vl-flow__section">第二站</section></main>
```

依赖 [章节流](#layout.chapter-flow) 和 [随包资源内嵌](../README.md#svg-assets)。重复线提供装饰动线，不保证自动经过每个站点；需要精确连接各站时，根据最终位置调整 route-s.svg 的路径。线宽与虚线长度属于 SVG 源参数，不冒充 CSS 可调项。

<a id="layout.subject-band-bridge"></a>

## 跨段主体与窄幅图带衔接

风格标签：通用。

粒度：上下两段与中间图带的布局。12列：上下正文列1–7、列8留空、主体列9–12跨三行。上/下段最小高300/180px，图带112px，列距12px，内距36px；正值按素材比例与文案调整。正文自然增长，不固定总高。图带z=1、前景z=2、正文z=3，列间避让不能只靠层级替代。独立素材模式：band照片+subject透明素材；完整场景模式：仅scene整幅无字场景，同时移除band和subject，背景不可按文字段拆分。场景图片cover需检查裁切，文字增长后重新适配素材或将增量移出场景，不拉伸主体。原子无默认渐变，文字不继承场景opacity/filter/mask。示例竖排文字仅验证槽位几何，不能充当已复刻木雕。

已核对 [章节流](#layout.chapter-flow) 不含跨段主体，[主场](hero-focus.md#layout.image-stage) 是单场域，[拼贴](overlap-and-collage.md#layout.collage) 未绑定三段与保护列。本实现无运行依赖。

```css
.sbx-bridge{box-sizing:border-box;position:relative;isolation:isolate;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-template-rows:minmax(var(--sbx-top-min,300px),auto) var(--sbx-band-height,112px) minmax(var(--sbx-bottom-min,180px),auto);column-gap:12px;padding-inline:var(--sbx-inset,36px)}.sbx-top,.sbx-bottom{position:relative;z-index:3;grid-column:1/8;min-width:0;overflow-wrap:anywhere;align-self:center;padding-block:28px}.sbx-top{grid-row:1}.sbx-bottom{grid-row:3}.sbx-band{grid-column:1/-1;grid-row:2;min-width:0;min-height:0;margin-inline:calc(-1 * var(--sbx-inset,36px));z-index:1}.sbx-subject{grid-column:9/-1;grid-row:1/4;position:relative;z-index:2;min-width:0;min-height:0;align-self:stretch;pointer-events:none}.sbx-scene{grid-column:1/-1;grid-row:1/4;position:relative;z-index:0;min-width:0;min-height:0;margin-inline:calc(-1 * var(--sbx-inset,36px));pointer-events:none}.sbx-demo{width:600px;max-width:100%;margin:0 auto;color:#29251f;background:#f6f2e9;font-family:'PingFang SC',Arial,sans-serif}.sbx-demo h2{margin:0 0 14px;font:400 30px/1.4 'Songti SC',serif}.sbx-demo p{margin:0;font-size:15px;line-height:1.9}.sbx-demo-strip{height:100%;display:flex;align-items:center;padding-inline:36px;box-sizing:border-box;background:#ded5c6;color:#342d25;font-size:14px;letter-spacing:3px}.sbx-demo-axis{height:100%;display:flex;align-items:flex-end;justify-content:center;padding-bottom:54px;box-sizing:border-box}.sbx-demo-axis span{writing-mode:vertical-rl;font:400 26px/1.8 'Songti SC',serif;letter-spacing:5px}.sbx-subject>img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;object-position:center bottom}.sbx-scene>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.sbx-band>img{display:block;width:100%;height:100%;object-fit:cover}
```

```html
<article class="sbx-demo"><section class="sbx-bridge"><header class="sbx-top"><h2>循木纹而行</h2><p>先观察材料的走向，再寻找可以保留的轮廓。每一道转折，都从木头本来的形态出发。</p></header><div class="sbx-band"><div class="sbx-demo-strip">取材 · 修整 · 成形</div></div><aside class="sbx-subject"><div class="sbx-demo-axis"><span>在时间里成器</span></div></aside><section class="sbx-bottom"><h2>细处见手艺</h2><p>放慢落刀的速度，留意边缘与掌心相遇的地方。让坚实的材料，呈现轻盈的线条。</p></section></section></article>
```

示例字体和底色属于演示，不是布局必需；组合另绑定素材、配色、字形和局部渐变。已验证600/420px及四倍正文的几何关系；不代表参考图素材、质感或完整组合效果验证通过。正式输出按目标协议展开样式。

<a id="layout.product-performance-longpage"></a>

## 性能递进长页

风格标签：通用。产物：详情页长图；粒度：完整长页。

整页分区：一体主视觉 → 抓地场景 → 标题山景与齿纹／交叉鞋体 → 支撑场景 → 右对齐说明＋左贴边材质图窗 → 轻量说明＋悬浮主体 → 左右错位细节组 → 产品资料面板 → 尺码与测量槽 → 多视角／颜色序列。

全页骨架保留出画主体与章节顺序，不等同于通用垂直堆叠。细节组可先用合成资产；有干净单图和特征坐标时，按需使用[图片标注](grid-and-alignment.md#layout.annotated-figure)；文字过长时改为独立正文区并保留安全间距。

| 布局参数 | 参考值／调节 |
|---|---|
| `--vl-page-width` | 658px，max-width:100% |
| `--vl-copy-block/inset` | 67px /38px；普通独立说明上下／左右留白 |
| `--vl-detail-window-width` | 88.15%；材质图左贴边，右侧保留背景 |
| 特殊说明 | mesh、weight 的 padding 独立保留，换文案正常增高 |
| 尺码／测量 | 整页保留该位置；表格内部实现属于组合，不作为新原子 |
| 配色展示 | 单侧面→俯视→后跟/外底双图→其他侧面；按真实SKU增减 |

适用：功能证据逐层递进且有大场景、局部特写和规格资料的详情页。不能把一张任意商品照拉长填满，也不因风格相近套到通知或简历。

纯布局只保存页面顺序、图窗宽高关系、对齐和留白，字体／配色／表面在组合皮肤层。单独选布局时加载 layout 样式与 main 骨架，不加载 recipe 样式；另选配色、字体和素材。组合与布局共用该 main，不复制第二套排版。图片 width/height 是参考比例而非固定显示高度，所有正文正常流增高。

素材契约：`{{pageN_asset_XX}}` 为真实素材槽，逐图的 alt 和 data-asset-ratio 说明角色及比例。完整合成场景包含标题或引线时保留一体素材，禁止 HTML 重复叠字；若需换产品／改图内文案，应重新制作该场景或获得可分离源素材。图窗边界不等于允许任意裁切，换图先核对主体净空。摄影、飞石、山雾、织物、特殊标题字形均不由布局 CSS 生成，参考图和私人本地路径不进入库模板。

安全底线：禁止给正文模块设固定高度或隐藏溢出；新字体按实际 face 检查字宽、字级和行框。先增加文案区高度，再调整栏宽／图文方向；不靠缩字和裁切过关。以画布容器宽度而非浏览器宽度触发480px窄版重排：性能页资料/用途改单列、测量改图文行；摄影页APP改单列、渠道改双列、缩减门店与页尾内距。背景换色须同步素材边缘与所在章节，不能仅改根变量就宣称整图换色完成。420px 与658px是已测画幅；更窄或更长内容须再次试排。

实现：读取登记模板的 main 和 layout 样式。局部尺寸为658px参考基准，不是固定页高。

**short 组装约束：** 此处样式与模板用于读取结构。按实际固定画布选择布局分支，将变量、选择器与继承展开到真实元素行内 style，伪元素转为真实装饰节点；最终 HTML 不保留 style 节点、媒体／容器查询或响应式缩放脚本。658／420 仅为历史测试宽度，不锁定新作品尺寸。参考中含字影像不自动授权新任务烘焙章节文字：按 Brief 保留准确文字 DOM，仅获准图内文字随图使用且不重复覆字。

<a id="layout.editorial-lookbook-longpage"></a>

## 摄影分章长页

风格标签：通用。产物：详情页长图、社媒长图、品牌专题；粒度：完整长页。

整页分区：一体主视觉 → `look-cycle`循环（完整摄影主场＋左窄右宽双窗＋偏右大图＋开放底单品图文）→ 发售／四个门店条目 → 街拍与互动说明 → 推荐横列 → 六个渠道 → 双APP入口 → 搜索 → 账号信息与收尾。

每个 look-cycle 是同一穿搭章节，不可打散为等宽卡片；单品图文左右交替，图片和图注属于开放的连续底面。尾段按产物可删：社媒长图删无意义的商店控件，品牌专题保留真实有效入口；不把这些控件误写成详情页必填。

| 布局参数 | 参考值／调节 |
|---|---|
| `--vl-page-width` | 658px，max-width:100% |
| `--vl-pair-ratio` | 253fr 360fr，保留左窄右宽 |
| `--vl-window-gap` | 19px；双窗间净空 |
| `--vl-chapter-gap` | 43px；主场后间距 |
| 单品图文 | 正向253:367、反向365:267，独立槽位避免压图 |
| 门店行 | 图标32px＋minmax(0,1fr)文字＋100px建筑图；行高由文字撑开 |
| 推荐横列 | 首卡flex-basis:min(465px,100%)，窄版首卡标题完整；后续预告卡可以局部露出 |

适用：以多组人物／单品摄影讲述系列穿搭的详情长图或品牌专题。布局亲和杂志摄影，不绑定奶油色、鞋类或品牌。

纯布局只保存页面顺序、图窗宽高关系、对齐和留白，字体／配色／表面在组合皮肤层。单独选布局时加载 layout 样式与 main 骨架，不加载 recipe 样式；另选配色、字体和素材。组合与布局共用该 main，不复制第二套排版。图片 width/height 是参考比例而非固定显示高度，所有正文正常流增高。

素材契约：`{{pageN_asset_XX}}` 为真实素材槽，逐图的 alt 和 data-asset-ratio 说明角色及比例。完整合成场景包含标题或引线时保留一体素材，禁止 HTML 重复叠字；若需换产品／改图内文案，应重新制作该场景或获得可分离源素材。图窗边界不等于允许任意裁切，换图先核对主体净空。摄影、飞石、山雾、织物、特殊标题字形均不由布局 CSS 生成，参考图和私人本地路径不进入库模板。

安全底线：禁止给正文模块设固定高度或隐藏溢出；新字体按实际 face 检查字宽、字级和行框。先增加文案区高度，再调整栏宽／图文方向；不靠缩字和裁切过关。以画布容器宽度而非浏览器宽度触发480px窄版重排：性能页资料/用途改单列、测量改图文行；摄影页APP改单列、渠道改双列、缩减门店与页尾内距。背景换色须同步素材边缘与所在章节，不能仅改根变量就宣称整图换色完成。420px 与658px是已测画幅；更窄或更长内容须再次试排。

实现：读取登记模板的 main 和 layout 样式。局部尺寸为658px参考基准，不是固定页高。

**short 组装约束：** 此处样式与模板用于读取结构。按实际固定画布选择布局分支，将变量、选择器与继承展开到真实元素行内 style，伪元素转为真实装饰节点；最终 HTML 不保留 style 节点、媒体／容器查询或响应式缩放脚本。658／420 仅为历史测试宽度，不锁定新作品尺寸。参考中含字影像不自动授权新任务烘焙章节文字：按 Brief 保留准确文字 DOM，仅获准图内文字随图使用且不重复覆字。

<a id="layout.numbered-media-longpage"></a>

## 编号分章 · 图文递进

风格标签：通用。范围：完整长页；适用产物：详情页长图、品牌专题。

保留“整幅主场 → 三项概览 → 编号图文章 → 主图与双细节 → 大图章 → 双场景媒体卡 → 三项包装说明 → 键值资料”的阅读关系。章节可以按真实信息增减，编号同步；不是按固定屏数堆叠等高卡片。图窗归各章，场景卡标题归自己的照片，资料区在末尾正常流收束。

完整几何与节点见登记模板的 `data-food-variant="1"` 和 `data-food-layout="1"`；只选布局不读取 food-skin。模板以596px为已验起排宽度，整页高度由真实内容决定，不保存曲奇主题、配色、字体族或阴影。需要其他固定宽度时重新排版和测高，不整体截图缩放。

| 参数／区域 | 起排值与调整 |
|---|---|
| 页侧净空 | 24px，标题额外内缩16px；新宽度不小于4% |
| 章节标题／编号 | 68px / 49px；主标题允许换行，编号独立不压缩 |
| 章间距离 | 52–56px，随上一章内容自然后移 |
| 胶囊副题 | 33px / 43px行高；取消 nowrap，长文案换行增高，不减字或遮挡 |
| 双细节／三列说明 | 各自独立图窗；资料与图注正常流，网格最小宽度为0 |
| 图像 | 等比显示，以最终素材真实尺寸更新；包装窄窗必要时 contain，不裁识别面 |
| 收尾 | 最后一个正常流安全区≥32px；用户另有更大值则从其要求 |

图片保留完整主体与语义净空；原料引线坐标必须随新图重配，不能照搬像素点。图内字不可单独编辑，换内容需用干净素材加原生文字，或沿当前品类授权整体编辑；已有集成标题不能再覆字。干净Hero可增加原生标题区，先核对图片实际净空；具体标题样式由组合选择。

验证边界：原图参考允许标题字体同类近似；纯布局已用森林绿香氛主题、宋体章节与长文案交叉测试。保留同一编号／图组结构，颜色与图像内容不构成布局依赖。

short最终组装：模板是结构输入，不是交付HTML。按确定画幅把选择器、变量、继承展开到元素行内style，伪元素变真实装饰节点；测自然高度后固定画布并复测。不得把模板style节点、媒体查询或参考位图直接当作最终可编辑成品。

<a id="layout.sensory-macro-longpage"></a>

## 微距叙事长图

风格标签：通用。范围：完整单长页；适用产物：社媒长图、详情页长图。

一张画布、一个main，顺序为叶影主视觉与标题 → 系列介绍 → 果肉微距与引言 → 双材质对照 → 流体融合 → 原料静物与收尾。只有双材质是局部两列，不生成左右独立成品，也不将两张海报截图上下粘接。完整销售详情仍按Spec补真实商品资料。

几何与节点读取 food-sensory-templates.html 的 `main[data-food-variant="3"]` 和 `style[data-food-layout="3"]`；单用布局时不读取皮肤。默认宽364px为验证起排值，高度随内容自然增长，尾部净空32px。换固定宽度须重新排版测高，不能直接放大截图。

Hero起排728px、流体场景486px，图片作为局部背景，文字容器参与正常流。Hero标题约24px、正文12–14px、英文≥10px。标题安全区约312×150px，流体题约230×66px；超量内容移到相邻正常流 `.long-copy`，不缩字、不裁切、不继续覆盖主体。若图片未留这块净空，重构素材或将标题移至正常流，不能照抄坐标。

双材质为2个最小宽度0的图窗；各自图注正常流增高。静物左右内缩24px，完整主体不得因裁切丢失。章节不得设置整页总高或overflow:hidden压住超量文案。模板是组装输入；正式产物沿short展开行内样式、测量后固定画布并复测。

布局不依赖水果、配色或字体族。背景衔接、字体与配色属于皮肤；虚焦果影、透光籽粒、液体扩散属于素材，不声称由CSS生成。
