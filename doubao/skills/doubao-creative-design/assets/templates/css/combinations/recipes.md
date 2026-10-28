# 组合配方｜引用、覆盖与可复制模板

[返回使用说明](../README.md)。本文件保存组合组成、参数覆盖、结构约束与具体用法；无需从 catalog 读取任何参数。组件配方提供现成节点；章节组合引用页面布局与原子，风格归属保留本文件标签；可搭配分支及筛选条件集中见 catalog 的 candidate_contexts，不按风格复制原子或另建目录。

<a id="combinations.assembly"></a>

## 两种使用方式

风格标签：通用（共用实现或组合规则，非独立风格预设）。

**快速复用**：先核对已选图文关系确实需要该载体，再按 recipe 的 `template` 和 `selector` 提取完整 article，按真实内容重排并应用已锁定参数；需要开放排字时只取相关原子。不能先复制卡片再把内容拆成相同数量的格子。原子代码用于理解或修改实现，不必每次重编译。

组合提供参考关系和实现，不替代品类决策。逐项区分继承的布局、配色、材质与影像：只借拼贴布局或纸纹时，不连带继承米黄底、照片数量、卡片、阴影或装饰字。整页背景遵守本次锁定配色，局部衬纸保留局部范围；固定列数、尺寸和角度只适用于原示例的内容量。用户明确复刻时保留锁定特征，仍检查真实文字是否容得下。

**原子组装**：读取 shapes 的结构、layouts 的内容样式、surfaces 共用层与选中材质、colors 的颜色。代码合并建议顺序为 layouts → shapes → colors → surfaces；同一节点的几何声明和表面声明分别保留。需要载体时分别选择形状与材质，圆角按已选边缘语言增加 `.vl-rounded`，不默认启用。选中的局部或预设覆盖最后应用。

根节点保持 position:relative、container-type:inline-size；有职责的 shadow/back 在底层，edge 在其上，surface 再上，正文和页签在最上；未启用投影时不补画影层。材质透明度不作用于根节点或正文。装饰不拦截交互；复制实例后重新分配 data-layer-id。

渐变按作用对象分别组装：章节色场使用逐色标颜色与透明度，局部光场单独绑定位置和强度，图片退场使用图片自身 Alpha 蒙版；文字与图表保持清晰独立。仅对已选的安全空场做图片渐隐，不用于遮盖不相容场景的结构接缝。图像型章节组合仍依赖实际摄影／渲染素材，不等于完整页面复刻模板。

正式 HTML 需要把伪元素展开为实际节点并将样式行内化，再按 [SVG 随包内嵌步骤](../README.md#svg-assets) 将 asset: 短引用替换为内嵌资源。模板属于组装源，不能跳过资源步骤直接交付；最终不在运行时引入 Markdown、CSS、catalog 或 assets 文件。参数优先级沿用 [HTML 组装协议](../../../../references/workflow/html-assembly.md)。

<a id="recipe.common"></a>

## 六个示例共用的局部覆盖

风格标签：通用（共用实现或组合规则，非独立风格预设）。

这些值用于保留当前示例的尺度，不是全局锁定值。其他视觉参数来自各原子文件。

```json
{
  "root_style": {
    "width": "100%",
    "min-height": "236px"
  },
  "overrides": {
    "--vl-tab-height": "30px",
    "--vl-slope": "32px",
    "--vl-radius": "18px",
    "--vl-padding": "26px",
    "--vl-title-size": "30px",
    "--vl-title-leading": "42px",
    "--vl-title-gap-before": "14px",
    "--vl-title-gap-after": "8px",
    "--vl-body-size": "14px",
    "--vl-body-leading": "26px"
  },
  "slot_styles": {
    "body": {
      "white-space": "pre-line"
    }
  }
}
```

<a id="recipe.folder-plastic"></a>

## 文件夹 · 半透明塑料

风格标签：通用。

```json
{
  "id": "recipe.folder-plastic",
  "kind": "recipe",
  "label": "文件夹 · 半透明塑料",
  "tags": [
    "folder",
    "plastic",
    "文件夹",
    "塑料"
  ],
  "components": [
    "shape.folder",
    "material.plastic",
    "decoration.edge",
    "decoration.shadow",
    "decoration.back-sheet"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".14"
    },
    "strong": {
      "--vl-grain": ".36"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"folder-plastic\"]",
  "common": "recipe.common"
}
```

<a id="recipe.folder-glass"></a>

## 文件夹 · 磨砂玻璃

风格标签：通用。

```json
{
  "id": "recipe.folder-glass",
  "kind": "recipe",
  "label": "文件夹 · 磨砂玻璃",
  "tags": [
    "folder",
    "glass",
    "文件夹",
    "毛玻璃"
  ],
  "components": [
    "shape.folder",
    "material.glass",
    "decoration.edge",
    "decoration.shadow",
    "decoration.back-sheet"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".18"
    },
    "strong": {
      "--vl-grain": ".48"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"folder-glass\"]",
  "common": "recipe.common"
}
```

<a id="recipe.folder-paper"></a>

## 文件夹 · 纤维纸张

风格标签：通用。

```json
{
  "id": "recipe.folder-paper",
  "kind": "recipe",
  "label": "文件夹 · 纤维纸张",
  "tags": [
    "folder",
    "paper",
    "文件夹",
    "手作纸张"
  ],
  "components": [
    "shape.folder",
    "material.paper",
    "decoration.edge",
    "decoration.shadow",
    "decoration.back-sheet"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".36"
    },
    "strong": {
      "--vl-grain": ".70"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"folder-paper\"]",
  "common": "recipe.common"
}
```

<a id="recipe.rounded-plastic"></a>

## 圆角容器 · 半透明塑料

风格标签：通用。

```json
{
  "id": "recipe.rounded-plastic",
  "kind": "recipe",
  "label": "圆角容器 · 半透明塑料",
  "tags": [
    "rounded",
    "plastic",
    "圆角",
    "塑料"
  ],
  "components": [
    "shape.rounded",
    "material.plastic",
    "decoration.edge",
    "decoration.shadow"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".14"
    },
    "strong": {
      "--vl-grain": ".36"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"rounded-plastic\"]",
  "common": "recipe.common"
}
```

<a id="recipe.rounded-glass"></a>

## 圆角容器 · 磨砂玻璃

风格标签：通用。

```json
{
  "id": "recipe.rounded-glass",
  "kind": "recipe",
  "label": "圆角容器 · 磨砂玻璃",
  "tags": [
    "rounded",
    "glass",
    "圆角",
    "毛玻璃"
  ],
  "components": [
    "shape.rounded",
    "material.glass",
    "decoration.edge",
    "decoration.shadow"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".18"
    },
    "strong": {
      "--vl-grain": ".48"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"rounded-glass\"]",
  "common": "recipe.common"
}
```

<a id="recipe.rounded-paper"></a>

## 圆角容器 · 纤维纸张

风格标签：通用。

```json
{
  "id": "recipe.rounded-paper",
  "kind": "recipe",
  "label": "圆角容器 · 纤维纸张",
  "tags": [
    "rounded",
    "paper",
    "圆角",
    "手作纸张"
  ],
  "components": [
    "shape.rounded",
    "material.paper",
    "decoration.edge",
    "decoration.shadow"
  ],
  "default_variant": "light",
  "parameter_variants": {
    "light": {
      "--vl-grain": ".36"
    },
    "strong": {
      "--vl-grain": ".70"
    }
  },
  "status": "implemented",
  "template": "material-recipes.html",
  "selector": "article[data-recipe=\"rounded-paper\"]",
  "common": "recipe.common"
}
```

<a id="combination-font-binding"></a>

## 组合字体与关系的读取约定

每条组合的“关系与字体复核”与原有参数表一起读取。配方只描述字体角色、视觉重量、对比、姿态与搭配关系，不能判定资源可用性，也不能证明整张参考图已完成字体提取；通用组件只提供角色起点，不能反推原图。需要具体候选时从 [字体推荐入口](../../../../references/rendering/font-recommendation-list.md) 保留本次参考图的可见字形约束，并用目标文案试排；精选清单不是封闭白名单，查询结果只表示候选、缺口和诊断。组合数不是原图数，原“复用落点／覆盖边界”表中的引用仍不代表每张来源已经完整提取。以下是配方级关系复核，不是所有历史成品的逐像素或渲染验收。

本次字体候选依据 2026-09-12 本地真实文件的 family、OS/2 weight 和代表性字样检查。它们不是对参考原字体的鉴定；“本地存在可试排”不等于许可已通过、全部目标文字已覆盖或远端 `artifact-preview` 已装载。配方用于正式 HTML 时，视觉候选确定后仍须执行 [字体资源与执行契约](../../../../references/rendering/font-family-library.md)，用目标环境真实 family／face／weight 回读并核验许可、目标字形覆盖与 Web 加载，不允许浏览器静默回退；用户锁定精确字体而门禁失败时必须请求确认。配方用于 pure-image 时只借用角色、重量、对比与搭配建议，不进入 HTML 资源门禁，也不承诺精确 family。以下本地路径是核验位置，不是远程 URL，也不将系统字体复制入包。

| 精确 family | 本次核验字重／样式 | 本地文件定位与边界 |
|---|---|---|
| Source Han Sans | 100、300、350、400、500、700、900，直立 | `~/Library/Fonts/SourceHanSans-*.otf`；已查到 ExtraLight／Light／Normal／Regular／Medium／Bold／Heavy，各是实际文件；不要混写成缺少Heavy的Source Han Sans SC |
| Source Han Sans SC | 300 Light，直立；本例已实渲染 | `~/Library/Fonts/SourceHanSansSC-Light.OTF`；真实face为SourceHanSansSC-Light，与Source Han Sans分开绑定，不由这一字面推断其他字重 |
| Alibaba PuHuiTi 2.0 | 250、300、400、500、600、700、800、900，直立 | `~/Library/Fonts/AlibabaPuHuiTi-2-*.ttf`；以2.0文件为准，文件名75 SemiBold对应CSS600；105 Heavy字形覆盖少于其他字重，逐字检查。目录ID chinese-0026-2-0-3-0的非标许可按当前用途核验 |
| Songti SC | 300、400、700、900，直立 | 系统 `Supplemental/Songti.ttc` 中SC字面；900的字符覆盖少于400/700，缺字时明确改用700并复排，不能伪粗 |
| Baskerville | 400、600、700及对应真实Italic | 系统 `Supplemental/Baskerville.ttc`；只承担拉丁和数字，不用作中文回退 |
| Bodoni 72 | 400 Book、400 Book Italic、700 Bold | 系统 `Supplemental/Bodoni 72.ttc`；视觉细不表示存在300字重 |
| DIN Condensed | 700，直立 | 系统 `Supplemental/DIN Condensed Bold.ttf`；短英文／数字，不能凭英文窄字把中文压扁 |
| Impact | 400，直立粗窄字 | 系统 `Supplemental/Impact.ttf`；视觉粗不改写成700 |
| Arial | 400、700；400 Italic及700 Bold Italic真字形已核验 | 系统 `Supplemental/Arial.ttf`、`Arial Bold.ttf`、`Arial Italic.ttf`、`Arial Bold Italic.ttf`；作为准确拉丁小字与数字，局部粗斜体短签名绑定Arial-BoldItalicMT，不合成斜体 |
| Kodchasan | 300、400、500、600、700及真实Italic | `~/Library/Fonts/Kodchasan.ttc`；玩具感短英文，不能承载中文 |
| Chalkboard SE | 400 Regular、700 Bold | 系统 `Supplemental/ChalkboardSE.ttc`；400另有Light字面，本表仅指定Regular；手写英文，不承担中文 |
| JiangChengLvDongHei | 700，直立但字面起伏 | `~/Library/Fonts/江城律动黑.ttf`；已看代表字样，当前缺许可证据，作为近形候选而非已准出字体 |
| yuweij | 500，Medium | `~/Library/Fonts/禹卫书法行书简体.ttf`；本地笔势候选，许可待核；不假定原图书法就是此字体 |
| Feibo Zheng Dots | 400，Regular | `~/Library/Fonts/飞波正点体V2.1版本.ttf`；本地毛笔候选，许可待核，定制字组仍有差异 |
| Smiley Sans | 400，Oblique | `~/Library/Fonts/SmileySans-Oblique-2.ttf`；同机另有OTF，实际选择只绑定一个版本。不声明700/900；倾斜窄字只在参考匹配时采用 |

上述系统路径前缀为 `/System/Library/Fonts/`，用户路径 `~` 为当前用户目录。文件定位仅供复查；生产时记录所选文件的真实绝对路径和版本。实际方案通常最多两个家族，表中跨语言、书法与章节候选是按需取舍，不要求全部加载。正文没有理由就不叠纹理／描边；标题字形的斜、窄、圆、粗必须有本条依据。

每条先锁定字形和角色，再核验字体。建议字号、行高仍读取本条原参数，以其声明的1080px或375px基准换算；不混用两个尺度。本节具体字重优先于原表“粗体／细体”等视觉描述；示例CSS的Arial／PingFang及通用font-weight是骨架值，不是字体绑定完成。将所选精确family、真实weight、style、字距、行高写入对应文字元素后，重测行宽与换行。若最贴近候选受限，记录替代及损失的字形特征，不能静默换得意黑或把“字体存在”写成“还原完成”。

<a id="combination.clear-light"></a>

## 清透光感面板

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 光感底与半透明面板分层；本条是局部容器，不推断整页背景。 |
| 图片／装饰素材 | 图标／缩图在内容区独立占位；反射层只装饰壳体。 |
| 文字归属与阅读顺序 | 标题、说明、动作在面板内按阅读流排列，不继承壳体透明度。 |
| 页面／容器／素材安全区 | 页面遵守所属章节边距；面板扣除边缘高光；图标不侵入字行。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 600 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 500 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Arial 400／700，数字与单位同组 |

匹配依据与边界：中性清透面板没有唯一原图字体；依据内容选平直、开放字腔，不自动用斜体。


风格标签：通用。

先取 recipe，再依次应用 presets，最后叠加用户要求的局部参数。

```json
{
  "id": "combination.clear-light",
  "kind": "combination",
  "label": "清透光感面板",
  "tags": [
    "清透光感面板",
    "组合"
  ],
  "recipe": "recipe.rounded-glass",
  "presets": [
    "palette.aqua-lime",
    "layout.airy"
  ]
}
```

<a id="combination.paper-editorial"></a>

## 暖纸编辑面板

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 暖纸底与独立纸面保留层差，细纤维只绑定纸面。 |
| 图片／装饰素材 | 图片可用矩形图窗，图注在图下；不把纸纹覆盖摄影。 |
| 文字归属与阅读顺序 | 编辑标题与正文共用内对齐轴，眉题和引用形成层级。 |
| 页面／容器／素材安全区 | 页面留白与纸面内边距分开；图注不贴裁切边；长文增高纸面。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 700 |
| 章节／卖点题 | Songti SC 400 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 400／400 italic |

匹配依据与边界：偏纸本出版的建议搭配；不因米色就强加书法。


风格标签：通用。

先取 recipe，再依次应用 presets，最后叠加用户要求的局部参数。

```json
{
  "id": "combination.paper-editorial",
  "kind": "combination",
  "label": "暖纸编辑面板",
  "tags": [
    "暖纸编辑面板",
    "组合"
  ],
  "recipe": "recipe.rounded-paper",
  "presets": [
    "palette.warm-paper",
    "layout.compact"
  ]
}
```

<a id="combination.soft-paper-folder"></a>

## 柔色纸本文件夹

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 柔色母底→文件夹背面→内纸页；页签是外壳局部。 |
| 图片／装饰素材 | 图片／图标在内页；夹子、贴纸独立挂边，不占正文位。 |
| 文字归属与阅读顺序 | 页签短标签与内页标题分开；正文沿纸页内容框。 |
| 页面／容器／素材安全区 | 页面边距不等于文件夹内距；避开页签斜坡、夹口和前景贴纸。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 700 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 600 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Kodchasan 500／700，限短英文；数字用中文家族 |

匹配依据与边界：柔色不代表必须圆体或得意黑，当前候选为温和的端正黑体。


风格标签：通用。

先取 recipe，再依次应用 presets，最后叠加用户要求的局部参数。

```json
{
  "id": "combination.soft-paper-folder",
  "kind": "combination",
  "label": "柔色纸本文件夹",
  "tags": [
    "柔色纸本文件夹",
    "组合"
  ],
  "recipe": "recipe.folder-paper",
  "presets": [
    "palette.cream-pink",
    "layout.airy"
  ]
}
```

## 配色、密度与原子来源

- 配色覆盖值直接读 [配色](../colors/palettes.md)；内部密度覆盖值直接读 [布局与字体](../layouts/layout-and-type.md)。
- 形状结构直接读 [容器形状](../shapes/containers.md)；材质参数和纹理直接读 [材质与光照](../surfaces/materials.md)。
- 保留 shape 与 material 的共同 surface 声明，不能整段覆盖后丢失 mask。新增组合需检查窄容器、长文案、字体变化和实际背景。

<a id="combinations.scene-examples"></a>

## 可选场景与内容装饰代码

风格标签：通用（共用实现或组合规则，非独立风格预设）。

以下为旧示例保留的场景、图块与分隔线实现，不是组件必选项。按实际需要取用，不加入默认组合。

```css
.vl-tiles {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 12px;
  margin-top: 24px;
}

.vl-tile {
  min-width: 0;
}

.vl-tile__art {
  height: clamp(65px,18cqi,92px);
  display: grid;
  place-items: center;
  background: linear-gradient(140deg,#fff8,#fff2);
  border: 1px solid #fff7;
  border-radius: 10px;
  color: hsl(var(--vl-hue) 60% 38%);
}

.vl-tile__art svg {
  width: 90%;
  height: 85%;
}

.vl-tile__label {
  display: block;
  margin-top: 9px;
  font-size: clamp(9px,2.2cqi,11px);
  opacity: .7;
  text-align: center;
}

.vl-rule {
  border: 0;
  height: 1px;
  background: currentColor;
  opacity: .12;
  margin: 22px 0;
}

.vl-scene {
  position: relative;
  overflow: hidden;
}

.vl-scene--aqua {
  background: radial-gradient(ellipse at 0 5%,#f2ffff 0,transparent 62%),linear-gradient(120deg,#c7f9f8,#79e8ee);
}

.vl-scene--ink {
  background: radial-gradient(ellipse at 20% 20%,#358888,transparent 62%),#173d40;
}

.vl-scene--paper {
  background: radial-gradient(ellipse at 0 0%,#fffdf6,transparent 70%),#e9e1d2;
}

.vl-scene--ink .vl-folder {
  --vl-ink: hsl(var(--vl-hue) 60% clamp(19%, calc(110% - var(--vl-alpha) * 135%), 96%));
}

.vl-scene__orb, .vl-scene__ribbon {
  position: absolute;
  pointer-events: none;
}

.vl-scene__orb {
  width: 150px;
  height: 150px;
  left: 17%;
  top: 32%;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 25%,#fff2b3,#e9e750 55%,#aaca52);
  box-shadow: inset -8px -12px 20px #4c7f4c22,0 20px 40px #26989f22;
}

.vl-scene__ribbon {
  width: 90px;
  height: 280px;
  right: 24%;
  top: 10%;
  transform: rotate(33deg);
  border-radius: 30px;
  background: repeating-linear-gradient(90deg,#eefdfd 0 8px,#72cecb 8px 15px);
  box-shadow: 8px 14px 26px #217e6c22;
}
```

## 页面章节的组合参考

下列风格描述对应参考画面的整体关系，不向单个原子传播；场景参考不等于新增专属风格配方。下列是可选组合，不固定商品品类、文案或章节数。按引用找到正文实现，把形状、材质与布局放到相应节点；不要把所有类机械地加在同一个根节点。所有颜色和尺寸均可局部覆盖。

| 参考 | 组合引用 | 节点关系与保留的素材  风格标签（候选） |
|---|---|---|---|
| 图 1 糕点 | [暖金](../colors/rich-and-retro.md#palette.pastry-gold) + [章节流](../layouts/continuous-flow.md#layout.chapter-flow) + [网格](../layouts/grid-and-alignment.md#layout.evidence-grid) + [织纹](../surfaces/textile-and-craft.md#surface.woven-grid) + [阶梯框](../shapes/cards-and-panels.md#shape.stepped-frame) | 织纹放章节背景；阶梯框只包信息；食品与木桌为图片  新中式风 / 当代东方 |
| 图 2 洁面 | [净白青蓝](../colors/calm-and-rational.md#palette.clinical-cyan) + [错位标题](../layouts/asymmetric-balance.md#layout.staggered-title) + [网格](../layouts/grid-and-alignment.md#layout.evidence-grid) | 标题和证据网格是兄弟区块；泡沫、瓶身与凝胶为图片  理性信息风 / 极简理性 |
| 图 3 猫砂 | [炭黑玫粉](../colors/high-contrast-pop.md#palette.charcoal-rose) + [弥散光](../surfaces/diffuse-light.md#surface.diffuse-field) + [网格](../layouts/grid-and-alignment.md#layout.evidence-grid) + [圆角](../shapes/containers.md#shape.rounded) | 章节底层光晕；对比区内部用两栏；岩石、猫和立体环为图片  奢雅精致风（一级） |
| 图 4 童装 | [酒红奶油](../colors/rich-and-retro.md#palette.burgundy-cream) + [主场](../layouts/hero-focus.md#layout.image-stage) + [章节流](../layouts/continuous-flow.md#layout.chapter-flow) | 主图与纯色文案区接续，不默认加卡片  杂志编辑风 / 时尚杂志 |
| 图 5 竹香 | [竹林深绿](../colors/fresh-and-natural.md#palette.bamboo-olive) + [主场](../layouts/hero-focus.md#layout.image-stage) + [网格](../layouts/grid-and-alignment.md#layout.evidence-grid) | 场景图后接规格行和四格图片；竹纹与晶体为图片  新中式风 / 当代东方；自然质朴风 / 田园森系 |
| 图 6 桂香 | [桂香奶金](../colors/soft-and-muted.md#palette.osmanthus-cream) + [窄内容栏](../layouts/airy-and-spacious.md#layout.reading-column) + [弥散光](../surfaces/diffuse-light.md#surface.diffuse-field) | 文字栏置于光层上；保留摄影中的真实花影  诗性浪漫风 / 柔光花艺；感官生活风 / 居家仪式 |
| 图 7 春日信件 | [苔绿信笺](../colors/fresh-and-natural.md#palette.moss-letter) + [窄内容栏](../layouts/airy-and-spacious.md#layout.reading-column) + [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) + [邮票齿孔](../shapes/tickets-and-notches.md#shape.perforated-paper) | 纸纹在背景层；邮票是独立小组件；整幅照片不覆纸纹  诗性浪漫风 / 书信叙事 |

新页面原子使用各自的 HTML 骨架，与早期 `.vl-folder` 组件独立。同一层同时需要光晕与织纹时，保留两个装饰 span；颜色来自目标节点 palette，强度来自各自材质参数。字体沿用字体协议，不通过复刻图片品牌字样创建新的字体预设。

### 本组参考图标识

以下保留源图文件名用于区分参考，不作为运行时路径；素材不随 CSS 库复制。

| 编号 | 参考内容 | 源图文件名 |
|---|---|---|
| 图 1 | 中式糕点 | `codex-clipboard-5d94ec6e-0c0c-43e3-9b8b-83b9af45ac4b.png` |
| 图 2 | 青蓝洁面 | `codex-clipboard-d1d2868a-e01a-4b5a-8473-a3bcc7629b3b.png` |
| 图 3 | 黑粉猫砂 | `codex-clipboard-2055a4d6-2cfa-442d-aed3-fbe89f08a1e6.png` |
| 图 4 | 酒红童装 | `codex-clipboard-1f758395-4e1a-4f9a-b87e-14635cb5c20a.png` |
| 图 5 | 竹林香氛 | `codex-clipboard-1e57d4e2-84bb-43e4-aada-baac1f471fe3.png` |
| 图 6 | 桂香洗护 | `codex-clipboard-aab3df2d-31b8-446e-8f0b-3b7342511fe8.png` |
| 图 7 | 春日信件 | `codex-clipboard-d4cf9ed5-0f79-4cac-bd2c-f08d8065e99c.png` |

<a id="combination.retro-pop-collage"></a>

## 复古高饱和拼贴：按节点组合

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 浅纸整底承接红黄蓝局部色块，网点仅指定纸面。 |
| 图片／装饰素材 | 照片衬纸交叠，主照片优先；奖杯、拍板等作为独立素材锚点。 |
| 文字归属与阅读顺序 | 标题与贴纸短注可错位；正文属于自身纸片，人物图注紧随照片。 |
| 页面／容器／素材安全区 | 纸边可叠压空白边；文字避开折角／胶带，人脸保持完整，页面不可裁掉必要信息。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | JiangChengLvDongHei 700（许可待核；端正替代 Source Han Sans 900） |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Kodchasan 700；编号 Arial 400 italic |

匹配依据与边界：江城候选更接近手作跳动字面；不把这种起伏套给所有章节，未核许可时保留替代差异。


风格标签：二级：波普撞色风 / 波普拼贴。

归属依据：本组合共同规定红黄蓝色块、纸本照片叠放、错位与纸面处理，形成波普拼贴关系；各组成原子仍为通用，不继承组合标签。

适合 Brief 指向红黄蓝色块、纸本照片拼贴与少量印刷质感的情况。这里的“复古”不必是低饱和棕色；若参考实际偏胶片、港风或旧报纸，应重新选色、字体和纸面处理，不把本组合当万能匹配。

| 作用对象 | 读取的原子 | 本组合的起始覆盖 |
|---|---|---|
| 全局色彩 | [红黄蓝纸本撞色](../colors/bright-and-playful.md#palette.primary-pop) | 浅底约 60%，红／黄／蓝色块合计约 35%，深色文字约 5%；比例是设计起点 |
| 照片与短便签组 | [叠层拼贴](../layouts/overlap-and-collage.md#layout.collage) | 12 列、gap=12px、外围留白 28px；只允许纸边覆盖主图空白区 |
| 照片纸片 | [照片衬纸](../shapes/notes-and-paper.md#shape.paper-mount) | pad=8px、footer=28px；主片 -3°，副片 +4°；角度记录到实例 |
| 页面纸底 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)与[共用纹理层](../surfaces/materials.md#surfaces.texture-field) | grain=.10；texture=paper-fiber.svg；不覆盖照片 |

需要可见撕边时，局部选择 [撕纸轮廓](../shapes/tickets-and-notches.md#shape.torn-paper)；需要网印装饰时，局部选择 [网点](../surfaces/paper-and-print.md#surface.dot-pattern)。这两项是可选项，不和玻璃、霓虹一起默认叠加。正文与人脸保护区、字体、照片素材和固定画布仍按已选品类与 Brief 决定。

```json
{
  "id": "combination.retro-pop-collage",
  "kind": "combination",
  "components": ["palette.primary-pop", "layout.collage", "shape.paper-mount", "surface.light-paper"],
  "bindings": [
    {"element_role": "photo-group", "ref": "layout.collage", "overrides": {"--vl-collage-columns": "12", "--vl-collage-gap": "12px", "--vl-collage-inset": "28px"}},
    {"element_role": "paper-background", "ref": "surface.light-paper", "overrides": {"--vl-texture": "url('asset:svg/paper-fiber.svg')", "--vl-grain": ".10"}},
    {"element_role": "photo-main", "ref": "shape.paper-mount", "overrides": {"--vl-paper-pad": "8px", "--vl-paper-footer": "28px", "--vl-rotate": "-3deg"}},
    {"element_role": "note-secondary", "ref": "shape.paper-mount", "overrides": {"--vl-rotate": "4deg"}}
  ]
}
```

bindings 是配方的角色说明，使用时映射到最终 HTML 的真实 DOM id，不另建参数规划文件或固定 schema；rotate 由实例拼贴类消费，paper-mount 自身不负责整体旋转。

## 第二组参考的复用落点

| 参考 | 主要采用 | 保留为素材／复用边界  风格标签（候选） |
|---|---|---|---|
| 演我大赛 | 红黄蓝配色、拼贴、徽章、照片衬纸 | 奖杯、拍板、手作立体人像为图片  波普撞色风 / 波普拼贴 |
| 创作小镇 | 晴空蓝青柠、章节流、S 形导览线 | 街屋和舞台整体为素材；导览线是可编辑装饰  趣味创意风 / 趣味拟物 |
| 假期追剧 | 钴蓝配色、网格、倾斜条幅、弥散光 | 条幅倾斜复用局部 rotate；播放图标与媒体内容按素材／图标职责处理  趣味创意风 / 清新轻艺术 |
| 蓝色生活／出行／二次元活动 | 晴空蓝或钴蓝覆盖、横向卡片、衬纸、拼贴 | 三条展示长页不当成实际页面三列；星空插画为素材  趣味创意风（一级，三页分别判断分支） |
| 数码／音乐／女性电影 | 深色配色局部覆盖、拱窗、对话框、横向卡片、霓虹标题 | 建筑、岩石、唱片与人物仍为素材；不同内容不强制同一色系  都市潮流风（一级，分别匹配音乐现场／字体潮流等） |
| 秋日商业活动 | 暖纸棕、纸纤维、衬纸、拼贴、邮票齿孔或撕边 | 绳索、夹子、树林与食物是素材；纸纹只作用在指定纸面  手账拼贴风 / 旅行手账 |
| 金色猫粮 | 暖金深棕覆盖、主场、玻璃说明卡、对比网格 | 油滴、丝绸、立体金字塔与食材为图像；不编造产品数值  奢雅精致风 / 古典雅奢 |
| 演唱会战报 | 黑底电光青、霓虹亮边、彩色颗粒、点阵字、原文件夹与拼贴 | 人物、签名字形等按素材与字体规则处理；数据来自真实 Brief  都市潮流风 / 音乐现场 |

以上引用均可按 catalog 定位到具体参数；色彩为视觉估计，未将原图品牌、文案或数据做成模板默认内容。

<a id="combination.luminous-sphere"></a>

## 球面玻璃与立体字组合

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 背景与球壳分别承担色场、反光；不是通用满页玻璃。 |
| 图片／装饰素材 | shell、shine及星光分别定位，真实曲面折射仍属素材。 |
| 文字归属与阅读顺序 | 标题居球面前的可读区域，挤出字与正面字同源；小字不做挤出。 |
| 页面／容器／素材安全区 | 页面按所属布局；圆形内部安全区扣除弧缘与高光；星光不压字腔。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 900 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 700 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Kodchasan 700，数字沿标题家族 |

匹配依据与边界：较宽厚的展示笔画接近体积字起点，不能冒充原图球面变形字。


风格标签：通用。

对应蓝色圆形主题徽章。轮廓、壳体、弧形高光和字面分开读取：

```json
{
  "id": "combination.luminous-sphere",
  "kind": "combination",
  "components": [
    "shape.badge",
    "material.sphere-glass",
    "surface.type-relief",
    "color.gradient",
    "text.paint"
  ],
  "bindings": [
    {
      "element_role": "badge",
      "ref": "shape.badge",
      "overrides": {
        "--vl-badge-size": "128px"
      }
    },
    {
      "element_role": "shell",
      "ref": "material.sphere-glass",
      "overrides": {
        "--vl-sphere-tint": "#1679c4",
        "--vl-sphere-alpha": ".50",
        "--vl-sphere-shine": ".85"
      }
    },
    {
      "element_role": "title",
      "ref": "surface.type-relief",
      "overrides": {
        "--vl-text-depth-x": "2px",
        "--vl-text-depth-y": "3px",
        "--vl-text-side-color": "#084779"
      }
    },
    {
      "element_role": "title-face",
      "ref": "text.paint",
      "overrides": {
        "--vl-gradient-stops": "#baf1ff 0%,#43bbee 48%,#1573bb 100%"
      }
    }
  ]
}
```

标题用真实文字，两层必须同源。徽章壳体用独立 shell / shine span，字面填充用 linear + text-paint，侧面用 type-relief。不要把 sphere 的透明度应用到整组文字。默认只做视觉近似；原参考的定制字形、球面变形和不均匀折射仍未复现。

## 补查后的覆盖边界

| 已提供参考中的特征 | 对应实现 | 当前边界 |
|---|---|---|
| 粉色手作布面、缝线、弧形店名 | 经纬织纹 + 规则缝线 + text.arc | 手绘动物、真实纤维毛边为素材；字形按真实字体决定 |
| 青绿文件夹与活动面板 | 原文件夹／圆角 + 玻璃／塑料 + 通用渐变 | 立体图标为素材 |
| Aha 纸本长页与春日信件 | 轻纸纹、章节流、网格、邮票／撕边 | 插画、照片和特殊品牌字形不转成通用 CSS |
| 糕点章节的拱顶、暖金纸面 | 拱顶面板 + 暖金配色／渐变 | 食品、礼盒、木桌为素材 |
| 蓝色圆形主题徽章 | 球面玻璃 + 文字挤出／填色 | 近似球面高光，不是真实折射或变形字形 |
| 夹着纸片的蓝白绳与粉色夹子 | 衬纸／拼贴 + 双色绳 + 简化夹子 | 近似直绳与二维夹具；鱼袋、绳结、真实夹口仍为素材 |
| 金色标题、渐变透明说明区 | 通用逐色标渐变 + 填字／反光带 | 油滴、丝绸、金属倒影和三维金字塔仍为图像 |
| 黑蓝／黑粉战报、发光点阵标题 | 原霓虹、彩色颗粒、网点 + 描边／挤出 | 发光、填色、厚度分开选择，不默认全部叠加 |

覆盖以实际代码和参数为准。“近似”保留了可编辑的视觉机制，不表示参考的所有细节都已经封装。SVG 的内部几何参数与 CSS 外层参数分别记录，不能仅凭改名或颜色宣称新增材质能力。

球面徽章旁的细小星光可按需读取 [四角星芒](../shapes/organic-shapes.md#shape.sparkle)，尺寸和腰部内收独立调整，不合并进玻璃材质。


<a id="combination.science-blue-white"></a>

## 蓝白科研信息组合

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 白信息章与蓝主场交替；网格退后，图表面保持干净。 |
| 图片／装饰素材 | 产品与上升动线共享主场；分子／骨骼图在机理章，比较栏使用独立真实资产。 |
| 文字归属与阅读顺序 | 眉线统一章节轴；主副标题左对齐；标注邻接机理节点，双栏按同一指标行对齐。 |
| 页面／容器／素材安全区 | 沿已有84px文字边距试排；比较卡扣内距；轨迹不穿字，保护产品标签、结构端点及数字。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 700 |
| 章节／卖点题 | Source Han Sans 500 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Source Han Sans 300用于轻大数字；参数400，强调700 |

匹配依据与边界：端正中粗黑体与参考信息秩序接近；不用得意黑的斜向字面。


风格标签：一级：理性信息风。

参数以 1080px 成品宽度试排，全部为视觉近似。展示板底色、外框投影、并排陈列不进入页面预设；最终成品是单条连续长页。下表用于规划 HTML 实现，不规定固定章节数，准确文案、数据和认证来自本次任务资料。

归属依据：蓝白交替、重复章节眉线、清晰比较栏和信息标注共同形成理性信息秩序；橙色与分子图本身不单独决定风格。

| 作用对象 | 复用实现 | 本组合起始参数 |
|---|---|---|
| 全页颜色 | [科研蓝白橙](../colors/calm-and-rational.md#palette.science-blue-orange) | light / dark 按章节切换；两种状态不叠加 |
| Hero | [主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.65–1.9，先试 1.75；1080 宽对应 1890 高；产品与上升动线共享舞台 |
| 标题与眉线 | [章节眉线](../layouts/layout-and-type.md#layout.section-masthead) | 两侧 84px；标题 80px/1.15，副标题 64px/1.2；眉线后 42px |
| 双栏比较 | [网格](../layouts/grid-and-alignment.md#layout.evidence-grid) | ratio=`1.25fr 1fr`；gap=30px；每项以同一行网格对齐，不独立堆两个失配列表 |
| 参数数字 | [数字单位](../layouts/layout-and-type.md#text.metric-unit) | size=112px；unit=48px；说明=30px；数值准确，不能照抄参考 |
| 成分机理段 | [图像标注](../layouts/grid-and-alignment.md#layout.annotated-figure) | 中图保持完整；标注 28px，线 36px；图中物件、箭头端点按实际资产校准 |
| 深蓝场景底 | [渐变](../colors/palettes.md#color.gradient) | angle=180deg；stops 使用 dark 配色；不要叠透明黑遮罩压暗全图 |
| 辅助光场 | [弥散](../surfaces/diffuse-light.md#surface.diffuse-field) | color=#b6dcff，opacity=.16，x=70%，y=72%，width=75%，height=45% |
| 场景出口 | [图片淡出](../surfaces/diffuse-light.md#surface.image-fade) | 仅安全空场使用；信息白区可以直接换章，不强求全部软接 |

可选背景细网格是两层正交线性渐变，共用一份声明，不新增纹理 SVG：

```css
.vl-science-guide { position:absolute; inset:0; pointer-events:none; opacity:var(--vl-guide-alpha,.07); background-image:linear-gradient(to right,var(--vl-guide-color,#fff) 1px,transparent 1px),linear-gradient(to bottom,var(--vl-guide-color,#fff) 1px,transparent 1px); background-size:var(--vl-guide-step,64px) var(--vl-guide-step,64px); }
```

guide 放章节背景之上、主体和文字之下；浅底时 line-color=#164d96、alpha=.045。参数表和真实图表优先保持纯净底色。比较面板复用普通圆角，主列蓝底白字，次列灰白底深字，颜色差异作用于面板而非降低整列透明度。顶端商品可破框，但为商品与首行文案预留净距。

原案例素材包括产品及包装、成长剪影、分子／骨骼机理图和立体绕行箭头，仅用于说明来源，不是本组合必需资产。当前素材由 Brief 的内容与证据决定，不因采用蓝白布局而新增医学结构或箭头。CSS 负责布局和信息，不重建真实三维折射或医学结构；图表应以真实数据生成，参考图中的证书和数值不做默认内容。


<a id="combination.botanical-green-gold"></a>

## 植萃绿金感官组合

**产物适用标签**：粒度：组件或章节组合；适配产物：社媒长图；适配产物：详情页单屏。组合不是完整长页；只在确需此组件的屏段使用。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 奶白、草绿、深绿按章形成场景底；光场与白色证据板独立。 |
| 图片／装饰素材 | 食材／产品／猫等占感官主场，液滴与机理图承担局部说明，不套满页玻璃。 |
| 文字归属与阅读顺序 | 大标题在图上方净空，双指标并列；科研标注靠近对象，证据板正文独立。 |
| 页面／容器／素材安全区 | 标题沿72px边距起排；白板扣内距；保护主体识别面、食材边缘与图表数字，渐隐只过空场。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 700 |
| 章节／卖点题 | Source Han Sans 500 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Source Han Sans 300用于轻指标，400用于单位 |

匹配依据与边界：字面宽松端正，标题靠字重和尺度建立力度；金色细数字不能用浓重斜体代替。


风格标签：通用。

参数以 1080px 成品宽度试排，全部为视觉近似。展示板底色、外框投影、并排陈列不进入页面预设；最终成品是单条连续长页。下表用于规划 HTML 实现，不规定固定章节数，准确文案、数据和认证来自本次任务资料。

本组结合自然场景、感官特写与科研图像，没有稳定单一风格归属，保持通用；按具体画面选择整体风格，不新增混合风格大类。

| 作用对象 | 复用实现 | 本组合起始参数 |
|---|---|---|
| 章节颜色 | [植萃绿金](../colors/fresh-and-natural.md#palette.botanical-green-gold) | 奶白、草绿、墨绿按内容切换；金色为次级强调 |
| Hero 与感官特写 | [主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.7–2.0，先试 1.8；1080 宽对应 1944 高；主体和环境共同占位 |
| 标题区 | [宽松文字](../layouts/layout-and-type.md#layout.airy) | 主标题 108px/1.12，副标题 62px/1.2；两侧 72px；标题不压主体识别面 |
| 并列大数字 | [网格](../layouts/grid-and-alignment.md#layout.evidence-grid)＋[数字单位](../layouts/layout-and-type.md#text.metric-unit) | 两栏 gap=48px；数字 150px/300，单位 66px，说明 36px；暗底采用浅金 |
| 科研图标注 | [图像标注](../layouts/grid-and-alignment.md#layout.annotated-figure) | 图像占据中央可见主场，正文 30px；复杂弧线／光轨由图像或任务路径承载 |
| 深绿底亮区 | [弥散](../surfaces/diffuse-light.md#surface.diffuse-field) | color=#b7ce66，opacity=.20，x=45%，y=42%，width=90%，height=65%；深色底仍保留 |
| 奶白向草绿 | [渐变](../colors/palettes.md#color.gradient) | 180deg；复用 light stops；白／浅绿段长度随主体和文案区调整 |
| 图片向下退场 | [图片淡出](../surfaces/diffuse-light.md#surface.image-fade) | 默认 80% 前不透明，91% 透明度 .65，100% 全透明；底色匹配下一段 |
| 指标白面板 | [圆角](../shapes/containers.md#shape.rounded) | radius=24px；纯白或近白表面、深色字；图表区不强加磨砂 |

图层顺序为章节颜色 → 可选光场 → 主体／环境图片 → 独立标注与文字。图片若已含光晕或浓烈高光，就取消同区域 CSS 光层；透明退场只能穿过空场，不能把肉类、包装或数据擦掉。若图片要从奶白过渡至深绿，可将落底色直接设为下一段深绿，并重新试排尾部白字；不要在同一文字组中跨越反差不足区。

原案例素材包括猫、食材、流心奶酪、苔藓草地、菌体、透明液滴和立体光轨，不是跨主题使用清单。当前素材由 Brief 决定；仅借绿金配色、特写与信息关系时，不附带生成原案例对象。真实材质起伏、微距高光与复杂折射由摄影／渲染提供；CSS 渐变不替代这部分质感。需要弧形小字时复用 [路径排字](../layouts/layout-and-type.md#text.arc)，不另存一套 SVG。

### 清透微距感官长图（清透果茶变体，同组合）

用途：需要微距、虚实对比与连续色场的感官叙事；果茶、水果为参考题材，换品类按视觉关系判断；交付为一整个连续长图。风格候选：自然质朴风／清雅自然；强调食材感官时可搭配感官生活风／滋养疗愈，不以粉色、绿色或水果名称单独决定风格。

布局采用 [微距叙事长图](../layouts/continuous-flow.md#layout.sensory-macro-longpage)。读取 food-sensory-templates.html 的 food-variant=3、food-layout=3、food-skin=3。仅一个main，以局部放大、虚实对比、连续色场与疏密变化组织长图。参考中的叶影、系列介绍、果肉、双材质、流体及原料静物是可替换槽位内容；没有双材质或流体需求时可改为其他有职责的细节或场景，并删改相应局部结构，不因缺少这些对象否定组合适配。需要局部对读时可用两列，不代表整页双栏。用户明确要求连续长图，旧参考并排展示方式不作为输出结构。

皮肤用 `--page / --ink / --on-photo / --font-family / --field-top / --field-middle / --field-bottom / --muted-ink` 分别控制底色、正文、图上文字、字体族和连续色场；全部可替换。绿色、石榴红只是主题实例，不进入纯布局。标题清晰无衬线，正文轻量；不复制原品牌、宣称或参考字体身份。

背景与素材：标题与主摄影共享场景背景，不加独立标题色块。局部材质及静物保留图窗，连续背景不等于全页只能一张图片。相邻场景先按实际边缘取色；`--hero-edge-mask`、`--flesh-edge-mask`未设置时均为none。仅在已确认无主体、无文字的留白边缘，按实际留白范围显式设置所需方向的淡出；换素材先取消旧值重新判断，不沿用演示百分比。禁止统一白蒙层擦除果肉，禁止用图注白色托底掩盖素材净空不足。图注优先正常流；局部叠字须匹配新素材净空。

素材槽位按视觉职责选择：虚实交叠的主场、局部出框的细节、具有节奏差异的局部对读、可连续展开的材质或场景、轻量收束。叶影、果肉、水珠、双材质和流体仅为参考表现，按商品与主题替换，不强制生成。摄影要求包含主体占比、裁切方向、清晰与虚焦区域和文字净空；不只写题材关键词。换主题全部使用无字新素材，原照片中的图注不可当作可编辑文本。

验证分两项：实现检查单画布、正常流、无溢出与真实槽位；视觉检查背景连续性、图窗与铺底区别、主体尺度、虚实、透明度和文字净空。结构正确不等于还原通过。石榴测试已修复主要接缝及蒙层问题，果影重量和流体细丝仍与原参考不同；不把这类差异写成CSS能力或宣称完整复刻。

完整销售页按Spec另补商品资料，不为凑章节编造功效。模板只分发参数与素材槽位，参考照片、石榴实例和测试记录保留在任务目录；最终按short行内HTML协议组装。

<a id="combination.urban-pink-cinema"></a>

## 黑粉巨字电影专题

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 黑底承接粉色光与颗粒；粉栏目板、灰海报壳是不同表面。 |
| 图片／装饰素材 | 海报为直立图窗，人物专题卡独立；拱形章节不裁首屏巨字。 |
| 文字归属与阅读顺序 | 巨字分行居主场；影片名、日期、动作随海报；小栏目双语清晰分层。 |
| 页面／容器／素材安全区 | 面板沿原32px内距；拱顶及光晕避开字组；保护海报必要信息和人物脸，静态不靠横滑隐藏内容。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 900 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Arial 700；局部窄数字 DIN Condensed 700 |

匹配依据与边界：参考为端正厚重巨字；字腔、宽度优先，辉光不应用斜窄得意黑替代。


风格标签：二级：都市潮流风 / 字体潮流。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：巨字与重复文字、黑粉高反差、发光标题和电影栏目共同构成字体主导的都市专题。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 全局 | [炭黑玫粉](../colors/high-contrast-pop.md#palette.charcoal-rose) | 底色 #080808，文字 #fff5fa，accent=#e63c8b；玫粉栏目底 #b83272 |
| 开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.25–1.5；主标题 150–200px、行高 .95–1.05，明确分行，不把整段正文放大 |
| 标题光 | [霓虹亮边与文字发光](../surfaces/diffuse-light.md#surface.neon-edge) | neon-color=#ffb4da，blur=12–20px；仅主标题字形发光，不给全文加光 |
| 背景颗粒 | [彩色屏幕颗粒](../surfaces/paper-and-print.md#surface.screen-grain) | grain=.08–.14，texture-size=192px；独立背景层，不盖电影海报 |
| 章节入口 | [拱顶章节面板](../shapes/organic-shapes.md#shape.arch-panel) | 拱顶开启新章节；图片与标题分别放到独立节点，拱顶不裁主标题 |
| 电影内容 | [横向卡片列](../layouts/grid-and-alignment.md#layout.card-rail) | card-width=82%，gap=30px；静态导出需要完整内容时改网格 |
| 栏目面板 | [圆角容器](../shapes/containers.md#shape.rounded) | radius=24px，内容安全边距 32px，灰底海报壳与粉色栏目分层 |

素材与边界：主标题可用 text.paint / text.outline，但高度失真的定制字形需字体或艺术字素材。电影海报与人物照片使用真实资产；横向露出仅供可滚动场景，静态不得隐藏必要影片信息。暗粉光场退到底黑时，使用独立径向光层；不把整张主标题透明化。


<a id="combination.urban-blue-concert"></a>

## 蓝银演出与磁带专题

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 黑蓝共底与蓝银光场相接；颗粒只在屏幕／壳体。 |
| 图片／装饰素材 | 现场照纵向主导，磁带、票根倾斜叠放；地图与奖品为后续独立信息。 |
| 文字归属与阅读顺序 | 窄长标题与银色英文分层；说明随票根净空，侧边规则字沿独立轴。 |
| 页面／容器／素材安全区 | 斜票根内容一起变换，扣除边框和重叠；保护现场人物、磁带窗口与票据关键字。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 500 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | DIN Condensed 700短英文／年份；Baskerville 400 italic仅签写副题，二选一 |

匹配依据与边界：参考定制窄字和签名字无法精确识别；不横向压缩中文，不默认全篇斜体。


风格标签：二级：都市潮流风 / 音乐现场。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：现场摄影、磁带票根与蓝银字形共同构成音乐现场视觉，而非仅凭蓝色归类。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 局部换色 | [钴蓝荧绿](../colors/high-contrast-pop.md#palette.cobalt-acid) | 复用钴蓝结构；tint=#07090f，ink=#eef2ff，muted-ink=#b4bfda，accent=#819bf3，label-bg=#314da7，label-ink=#fff；取消荧绿 |
| 开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.4–1.75；标题 120–158px，演出现场占开场纵向主体 |
| 磁带与票根 | [叠层拼贴](../layouts/overlap-and-collage.md#layout.collage) | 12列；主物件跨10列，旋转 -5°；文字说明另层，不能压住关键字 |
| 数码颗粒 | [彩色屏幕颗粒](../surfaces/paper-and-print.md#surface.screen-grain) | grain=.06–.12，仅背景和指定壳体 |
| 蓝银光场 | [弥散光晕](../surfaces/diffuse-light.md#surface.diffuse-field) | color=#7b93d3，opacity=.20，x=65%，y=45%，width=85%，height=65% |
| 现场退场 | [图片边缘透明衔接](../surfaces/diffuse-light.md#surface.image-fade) | 主体以下安全区域从75%开始淡出，到100%露出 #07090f |
| 票根信息容器 | [文件夹轮廓](../shapes/tabs-and-folders.md#shape.folder) | 复用轮廓；边色 #9aa8d0，表面 #213568；不强加玻璃 |

素材与边界：磁带、唱片、舞台、城市地图和真实条码为素材；装饰条码不能当成可扫描凭证。侧边规则入口绑定实际文本节点，不默认变成页面悬浮按钮。银色反光只在需要的边缘用 metal-bands，照片自带高光不叠一遍。


<a id="combination.industrial-silver-panel"></a>

## 银灰工业科技面板

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 墨黑工程底→细网格→暗灰工业板；银色反光局部。 |
| 图片／装饰素材 | 悬浮拼图为独立主资产，螺钉在板角，方向小物件支持分类。 |
| 文字归属与阅读顺序 | 标题居主场顶部，正文落在板内；任务双列各自题文动作，编号轴统一。 |
| 页面／容器／素材安全区 | 原40px板内距扣除螺钉；保护拼图轮廓与行动文本；页边编号不出画。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 900 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | DIN Condensed 700用于短标题／数字，说明沿正文 |

匹配依据与边界：直立硬边粗黑更接近工业面板；银色填充不代表需要运动斜字。


风格标签：二级：未来科技风 / 工业科技。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：硬边信息板、工程秩序、银色立体主体与荧黄标记共同形成工业科技表达。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 全局 | [炭黑银灰荧黄](../colors/high-contrast-pop.md#palette.industrial-silver-lime) | 墨黑底、银灰字、荧黄小标记；暗面板 #242727，正文 #eef0e8 |
| 开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.2–1.5；产品或拼图主体宽为本段55%–72%，标题 115–145px |
| 信息秩序 | [章节眉线](../layouts/layout-and-type.md#layout.section-masthead) | rule-width=1px，masthead-size=22px；编号与标签保持同一轴线 |
| 工业信息板 | [圆角容器](../shapes/containers.md#shape.rounded) | radius=12px，border-width=1px，edge-color=#666c68，padding=40px；避免大圆角软萌感 |
| 并列任务 | [规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid) | 两列，gap=30px；说明与动作入口分别对齐 |
| 局部银色 | [金属反光带近似](../surfaces/metal-and-relief.md#surface.metal-bands) | stops=#777f83 0%,#e9eeee 35%,#929a9e 52%,#f3f6f4 58%,#677075 100%；只用于装饰边或大字 |
| 编号与指标 | [数字与单位层级](../layouts/layout-and-type.md#text.metric-unit) | metric-size=112px，unit-size=44px；荧黄只强调短数字／箭头 |

素材与边界：悬浮拼图、复杂折射及金属曲面保留为图像。螺钉可用独立圆形 span 与短槽线近似：直径18px、银灰渐变、槽线10×2px，放在角内20px，不作按钮；需要真实螺纹则用素材。工程网格复用科研组合的细网格声明，step=72px、alpha=.05，不复制纹理实现。

细网格来源：[蓝白科研组合](#combination.science-blue-white)，使用其 `vl-science-guide` 声明并局部覆盖参数。


<a id="combination.ivory-portrait-report"></a>

## 象牙白人物雅致战报

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 象牙白连续底，暖金细边与浅白数据面板分开。 |
| 图片／装饰素材 | 人物大图渐融纸底，榜单截图与商品独立，照片不加统一纸纹。 |
| 文字归属与阅读顺序 | 细宋标题在头顶净空，红棕衬线大指标居面板；图榜按行对应。 |
| 页面／容器／素材安全区 | 保护人物脸和肩线；原框内距另算，指标单位同行；长金额先扩列宽，不截尾。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400 |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Bodoni 72 400 italic用于GMV大数字；小英文400 |

匹配依据与边界：高反差细衬线更贴近；本地Bodoni Book是400，替代原文视觉weight300，不伪造300字重。


风格标签：二级：奢雅精致风 / 极简精品。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：人物留白、细衬线标题、少量暖金与红棕巨数、精细边框共同形成极简精品表达。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 颜色覆盖 | [桂香奶金](../colors/soft-and-muted.md#palette.osmanthus-cream) | tint=#f6f1e6，ink=#5f543c，muted-ink=#716858，accent=#a43d2e；暖金只作次级装饰 |
| 人物开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.65–1.95；人物宽65%–85%，标题在头部安全区，避免遮脸 |
| 人像下缘 | [图片边缘透明衔接](../surfaces/diffuse-light.md#surface.image-fade) | 下部衣服外的背景安全区78%→100%淡入 #f6f1e6；不淡出脸与标题 |
| 主指标 | [数字与单位层级](../layouts/layout-and-type.md#text.metric-unit) | 数字190px、unit90px、weight300；字体沿衬线角色，红棕强调 |
| 数据面板 | [圆角容器](../shapes/containers.md#shape.rounded) | radius=22px，边框1px，底色 #fffdf8，无粗阴影 |
| 榜单与商品 | [规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid) | 不等宽网格 1fr 1.2fr，gap=32px；商品照片与名次保持关联 |

素材与边界：人物与服装身份保留；签名式标题由合适字体或透明艺术字资产负责，不能复制示例姓名。白色背景淡出需匹配就绪图片色温；不能用半透明白膜覆盖脸。所有榜单、GMV、排名与金额只来自用户资料。


<a id="combination.kraft-editorial-report"></a>

## 牛皮纸时尚编辑战报

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 深浅牛皮纸硬切，细纤维不跨到摄影。 |
| 图片／装饰素材 | 大人物跨版心，标题框在上，斜纸条压空场；商品列表与证据截图平直。 |
| 文字归属与阅读顺序 | 超大窄数字主导战报，下部每行商品左、金额右；纸条短题与长文分别排。 |
| 页面／容器／素材安全区 | 斜条扣折角净空；保护头脸、品牌包款及截图文字；数字描边需留字腔和行距。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 900 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Impact 400用于巨大紧凑金额；Arial 400用于小英文 |

匹配依据与边界：Impact本身是粗窄字，文件weight400，不写700；中文不拉窄模仿品牌定制字。


风格标签：二级：杂志编辑风 / 时尚杂志。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：编辑边线、时尚人像、纸色错层与商品排行共同形成时尚杂志式信息编排。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 深浅纸色 | [暖纸棕](../colors/palettes.md#palette.warm-paper) | tint=#eee5d4，ink=#382b1f，muted-ink=#625643，accent=#7a654b；深纸区 #82735f 配 #fff4df |
| 人物与标题 | [叠层拼贴](../layouts/overlap-and-collage.md#layout.collage) | 人物跨9–11列，标题框置于人物上方；斜条 -3°，文字净距32px |
| 编辑标识 | [章节眉线](../layouts/layout-and-type.md#layout.section-masthead) | 小眉题22px、边线1px、段间留白40px |
| 巨型指标 | [文字描边](../layouts/layout-and-type.md#text.outline) | 大字170px；描边色 #fff0d2，宽度3px；准确数值在真实文字层 |
| 纸面 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | grain=.12–.20，size=256px；深纸区适度减弱，不给人像加纸纹 |
| 商品排行 | [规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid) | 逐行 1fr 1.65fr，gap=28px；同一行容纳商品、名称与金额，行高随内容 |
| 证据截图 | [照片衬纸与胶带](../shapes/notes-and-paper.md#shape.paper-mount) | 衬纸 pad=12px、footer=16px；对证据保持平直，不用大旋转 |

素材与边界：品牌包款、Logo、人物和平台榜单截图均为真实资产。标题框与巨大数字是排版，不把品牌字体当默认字库。深浅纸面硬切配合斜条即可，无须每段加渐变。


<a id="combination.torn-paper-report"></a>

## 撕纸票签人物战报

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 纸白／棕票纸为主体，织纹只在指定底面。 |
| 图片／装饰素材 | 人物场景为首屏，撕纸包裹指标，凭据截图和商品行独立。 |
| 文字归属与阅读顺序 | 书写主题在人物上方净空；侧签竖题；大衬线金额与票纸对齐。 |
| 页面／容器／素材安全区 | 原32px撕边内距按可见轮廓算；保护脸、扇子、截图文字；长条mask随比例重查。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | yuweij 500（许可待核；结构替代 Songti SC 700） |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Bodoni 72 400 italic用于金额；小英文400 |

匹配依据与边界：本地行书只是笔势候选，非原签名字；无许可／原字形时保留缺口，不宣称字体还原。


风格标签：二级：手账拼贴风 / 票据档案。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：撕边纸条、侧挂票签、截图衬纸与凭据排行共同构成档案式拼贴，不因人物服饰而归新中式。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 纸色覆盖 | [暖纸棕](../colors/palettes.md#palette.warm-paper) | tint=#f1e6cc，ink=#442c16，muted-ink=#705d41，accent=#95481f；标签底 #c8bb8f |
| 人物开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.4–1.8；留出顶部书写标题和侧边姓名标签 |
| 指标纸条 | [不规则撕纸边](../shapes/tickets-and-notches.md#shape.torn-paper) | 撕边框只包指标；内容安全距离32px；长条按最终比例调整 mask，不能直接拉伸3:4原版 |
| 指标 | [数字与单位层级](../layouts/layout-and-type.md#text.metric-unit) | metric-size=170px，unit-size=82px；衬线／斜体沿字体协议，浅纸深字 |
| 凭据卡片 | [照片衬纸与胶带](../shapes/notes-and-paper.md#shape.paper-mount) | pad=16px，footer=14px；截图独立，真实文字不叠到截图上 |
| 底面织纹 | [织物手作](../surfaces/textile-and-craft.md#surface.woven-grid) | step=6px，line=.5px，opacity=.06；与纸纹分层，只在参考需要时同用 |
| 商品数据条 | [规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid) | 两列 1fr 1.6fr；gap=24px，商品、指标与来源同一行 |

素材与边界：人物环境、扇子、服装、叶片等保留为图片；手写标题用真实字体或资产。纸条长度变化较大时使用原子声明的边界策略；未调整轮廓前不得把窄长撕边当成已验证。


<a id="combination.antique-illustrated-story"></a>

## 古典插画人文长页

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 古纸赭黄或灰蓝整底二选一，纸纹与版画插图分层。 |
| 图片／装饰素材 | 长船／帆面或拱门／立柱组织连续阅读，不新加圆角卡。 |
| 文字归属与阅读顺序 | 标题围绕插画留白，正文居中窄栏；日期属于拱门内部，不能用外框代替内面。 |
| 页面／容器／素材安全区 | 沿72–80%正文栏起排；帆面文字避桅杆和缆绳；人物轮廓与印章不遮字。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 900 |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 700用于古典英文，日期400 |

匹配依据与边界：宋体仅接近书卷骨架；原图做旧雕刻／手写的缺口保留为字形／资产需求，不把噪点覆字当完成。


风格标签：二级：杂志编辑风 / 人文出版。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：插画、章题、居中阅读栏与纸本编排共同形成图文人文出版方向；赭黄／灰蓝是组合内配色分支。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 赭黄分支 | [古纸赭黄墨棕](../colors/rich-and-retro.md#palette.antique-ochre) | 古纸底、棕黑线稿、赭黄插画；长船形叙事背景依靠图像 |
| 灰蓝分支 | [灰纸靛蓝砖红](../colors/soft-and-muted.md#palette.oxide-blue-paper) | 灰青纸、靛蓝插画、砖红短标题；两套配色二选一 |
| 叙事开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.5–1.9；人物／船／建筑插画占主导，图上标题遵守安全区 |
| 正文 | [疏朗留白](../layouts/airy-and-spacious.md#layout.reading-column) | 内容宽72%–80%；正文32px/1.65，章节标题72px，段间留白64–96px |
| 印刷底 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | grain=.14–.24，size=256–384px；只处理纸底 |
| 灰蓝拱门段 | [拱形图片窗](../shapes/cards-and-panels.md#shape.arch-window) | ratio=3/4，图片窗与日期文字分层；立柱和门饰为插画 |
| 连续关系 | [连续流动](../layouts/continuous-flow.md#layout.chapter-flow) | 船帆或建筑分区承担叙事，内容高度随真实文案，不把每段改成卡片 |

素材与边界：古典人物、船、陶器、建筑、纹章与复杂印刷字形必须由相应插画和字体承载；CSS 纸纹不等于版画／古希腊艺术复现。赭黄长船的每段文字对齐实际帆面安全区，不能把通用网格当船帆轮廓。时间与活动信息全部替换为本次真实内容。


<a id="combination.minnan-folk-editorial"></a>

## 朱红民艺图文长页

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 纸白开场切朱红底，长文由白纸片承托；红底不统一模糊。 |
| 图片／装饰素材 | 建筑、民俗人物和船是插画层，局部越纸边；纹样在低干扰区域。 |
| 文字归属与阅读顺序 | 大宋体标题在建筑上方；纸片正文分组，章节小题与编号关联。 |
| 页面／容器／素材安全区 | 长文纸片正向，装饰避开内距；保护屋顶识别线及字组；页面朱红侧题不可裁断。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 900 |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Baskerville 400／700，日期沿正文 |

匹配依据与边界：端正高反差宋体较接近传统标题；未经参考依据不添书法或得意黑。


风格标签：二级：国潮装饰风 / 传统纹样。

下列尺寸按 1080px 成品宽度试排，色值与比例为参考估计；用户参考及真实内容优先。展示板的并排列、黑／蓝外底、设计师签名、水印和外框投影不计入成品。使用主场、章节流与准确文字组合；本配方不是完整成品 HTML，身份照片、插画与品牌素材另行就绪。

归属依据：民俗纹样、建筑线描、传统字形与朱红纸白的装饰编排共同支持国潮装饰方向。

| 对象 | 实现引用 | 起始参数与绑定 |
|---|---|---|
| 全局 | [珊瑚朱红纸白墨黑](../colors/bright-and-playful.md#palette.coral-paper-ink) | 纸白开场＋珊瑚朱红正文段；红色段的正文放白纸块上，装饰字可用近白 |
| 建筑开场 | [聚焦主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.3–1.65；大标题110px，建筑与民俗插画跨主场，正文不挤进插画细节 |
| 正文纸片 | [照片衬纸与胶带](../shapes/notes-and-paper.md#shape.paper-mount) | pad=24px、footer=0；部分纸片旋转 -1.5°，对长正文保持正向 |
| 章节拼贴 | [叠层拼贴](../layouts/overlap-and-collage.md#layout.collage) | 12列，gap=20px；主纸片跨10列，插画局部破框但不遮正文 |
| 纸面 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | grain=.10–.16，size=256px；红底可低强度 .06，文字清晰 |
| 编号与小标题 | [章节眉线](../layouts/layout-and-type.md#layout.section-masthead) | masthead-size=22px，rule-width=1px；标题另用衬线／书写角色 |
| 阅读动线 | [连续流动](../layouts/continuous-flow.md#layout.chapter-flow) | 纸白开场切红底信息段，再由独立纸片承接；保持段尾颜色和下一段一致 |

素材与边界：屋顶、人物、船、剪纸纹样和手绘波浪边保留为插画。波浪边不是已有四角星或撕纸 mask 的别名；无现成几何时用插画边缘或明确硬切。禁止按照片题材替换成任意传统符号。


<a id="combination.oriental-garden-scroll"></a>

## 古画游园长卷

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 沿下文浅纸／深橄榄共同底，不导入黑展示底。 |
| 图片／装饰素材 | 园林环绕中央净空，只有特写配画框；人物和花枝独立越框。 |
| 文字归属与阅读顺序 | 中央窄短文、侧边竖题签与产品图各有归属，保持长卷交替节奏。 |
| 页面／容器／素材安全区 | 三类安全区详见本条原表；保护亭台人物、坛口、标签和酒液，长文增加段高。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400 |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 400用于英文主题，数字400 |

匹配依据与边界：细宋配古典英文适合长卷；短书写装饰可另核字体，不能让行书承载长正文。


风格标签：一级：新中式风。

古画人物、园林长卷与现代商品摄影共同组织节令叙事；不硬归宋韵或水墨。以用户黄酒长页参考为依据，展示板外底、并排展示方式不计入页面。以下均为视觉近似起点，按 1080px 成品宽度缩放。

| 对象 | 复用入口 | 局部参数／组装 |
|---|---|---|
| 色彩 | [暖纸棕](../colors/palettes.md#palette.warm-paper) | tint=#e5d5ab，ink=#514a32，muted-ink=#6b6047，accent=#97462d；深章底 #766843、字 #f2e7c6，标签底 #c8af77、字 #4a3b25；替换成对文字颜色 |
| 主场 | [图像主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.65–2.0，园林人物为大面积底图，标题与引言独立；场景之间保留可阅读空场 |
| 长卷节奏 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow)、[疏朗正文](../layouts/airy-and-spacious.md#layout.reading-column) | 交替远景、短文、题签和产品特写；正文宽度约画幅 55–65%，段间距 90–160px |
| 纸面 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | grain=.08–.14，texture-size=256–384px，multiply；使用 paper-fiber.svg 短引用；仅纸底，不覆盖摄影或文字 |
| 淡接 | [图片透明衔接](../surfaces/diffuse-light.md#surface.image-fade) | 检查最终裁切后，仅在确有安全空场时设渐隐；78%–100% 是原例试排值，亭台、人物与包装不得被擦除 |
| 题签与画框 | [阶梯边框](../shapes/cards-and-panels.md#shape.stepped-frame)、[图片衬纸](../shapes/notes-and-paper.md#shape.paper-mount) | 细框 1–2px、金棕色；竖题签可用 writing-mode:vertical-rl，正文保持横排；复杂古典花边需独立素材 |

纸纤维只补轻微底纹；古画中的斑驳、山水晕染和笔触由图像承担，不能叠一层噪点声称复原。需要从深章切回浅章时可直接分章，不强行给每段加渐变。产品、节令人物及园林需摄影／插画素材，参考中的品牌和宣传文案不作为默认内容。

### 背景、图框、文字与安全区

| 层／对象 | 布局关系 | 保护范围与调整 |
|---|---|---|
| 章背景 | 浅纸章与深橄榄章分别为共同底；外层黑展示底不属于画面 | 纸纤维局限底层；粗古画斑驳与笔触在插画素材内，不罩在全文上 |
| 园林插画 | 可出血至长卷两侧，环绕中央文字净空；不是每段独立矩形卡 | 标题／引言不能占人物头部、亭台轮廓和高反差山线；净空随素材重新标注 |
| 短文 | 中央窄栏是背景／插画的兄弟节点；长文横排，不统一装进卡片 | 沿用正文宽55–65%，以段落实际占用高度留出上下间隔；文案增长先增加段高，不能缩字压进人物区 |
| 竖题签 | 局部金棕面板承载竖题，插画人物在题签外侧相邻 | 题签内文字框与外部小人物不能重叠；可见转角／缺口以内再留内边距，不能只算外接矩形 |
| 产品画框 | 只有指定特写使用独立画框；框、图像与文字各自可替换 | 包装标签、坛口、倾倒酒液与碗沿为保护主体；装饰人物可以局部越框，但不覆盖这些区域 |
| 前景装饰 | 花枝／人物可高于画框，正文层在其保护净空内单独定位 | “文字z-index更高”不等于允许装饰贴在字后；必要时移动装饰，而不是遮一块白底 |

安全区参数不是截图测量值：以画幅W为基准，页面必要文字先留约6–8%W横向边距；图框／题签的内容距可见轮廓约4–6%容器宽。保持原文中央栏比例；这些只是试排起点，源图缩略细字不能支持精确像素反推。将文字、人物／包装保护区域分别绑定到实际图层，不设覆盖全图的单一安全矩形。

图层关系：章底色→纸纤维→园林／产品图→局部框与题签表面→独立文字；出框装饰为同级单独层，按不遮挡主体及文字调整。图片mask只对空场末端生效。浅深分章是否硬切按参考判断，不把全部画框、文字和背景一起淡出。

纹理实现状态：轻纸纤维已复用 `paper-fiber.svg`；古画云斑、山水笔触及画框古典花边保留素材需求，未声明为已生成的通用纹理。当前回查补的是关系与边界说明，尚未对整张古画长页做完整素材渲染验收。

<a id="combination.oriental-vermilion-scent"></a>

## 朱砂墨底东方香叙

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 沿下文红黑连续底；细纤维、大片云斑、植物暗纹分别承担。 |
| 图片／装饰素材 | 左右错落香调插画／产品，黑底静物大图；只局部方图用矩形。 |
| 文字归属与阅读顺序 | 书法大字为独立字组，香调编号与短说明邻近图片净空，曲线避开字。 |
| 页面／容器／素材安全区 | 三类安全区详见本条原表；保护瓶盖高光、果实与金字，暗纹不吞笔画。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Feibo Zheng Dots 400（许可待核；书法还原未完成） |
| 章节／卖点题 | Songti SC 400 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 400／400 italic，香调编号优先细衬线 |

匹配依据与边界：飞波正点体仅作待重新验证的本地近似候选；宋体可暂排结构但不能替代已锁定书法结论。


风格标签：二级：新中式风 / 当代东方。

依据石榴香氛参考：书法构成、朱砂墨色、植物插画和现代静物摄影共同定义风格。尺寸按 1080px 宽度试排，不提取展示板外层的棕色纹理。

| 对象 | 复用入口 | 局部参数／组装 |
|---|---|---|
| 配色 | [酒红奶油](../colors/rich-and-retro.md#palette.burgundy-cream) | tint=#762b1e，ink=#eee0a5，muted-ink=#dcc8a2，accent=#c8a15d；黑段 tint=#090706，ink=#f0e6bf；label-bg=#e4ce91、label-ink=#4a2017 |
| 主场与字 | [主场](../layouts/hero-focus.md#layout.image-stage)、[错落标题](../layouts/asymmetric-balance.md#layout.staggered-title) | H/W=1.7–2.0；书法标题占主要视觉，短句与小英文错落排布；定制书法需字体或艺术字，不能用普通宋体拉伸替代 |
| 红黑色场 | [通用渐变](../colors/palettes.md#color.gradient) | angle=180deg；stops=#762b1e 0%, #612319 60%, #090706 100%；独立底层，不对正文整体设 opacity |
| 纸墨底纹 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | paper-fiber.svg；grain=.12–.20，texture-size=256–384px，multiply。仅近似纤维，不等同原图大尺度斑驳 |
| 纹理退场 | [图像渐隐](../surfaces/diffuse-light.md#surface.image-fade) | 仅在红场转黑场的实际换场区渐退纹理；起止按最终素材与阅读区确定，不在每章重置淡出；底色渐变与图片 Alpha 分别控制 |
| 香调章节 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow)、[图像标注](../layouts/grid-and-alignment.md#layout.annotated-figure) | 初段／中段／尾段错落，细引导线 1–2px；插画、说明、产品各自独立，实际文案决定章数 |
| 产品暖光 | [局部光场](../surfaces/diffuse-light.md#surface.diffuse-field) | 摄影未自带光场时才补红橙局部光，透明度 .15–.25；产品照片已有光影则关闭重复叠光 |

粗细两种尺度不能混成重噪点：细纸纹复用已有 SVG；明显红褐云斑、印染起伏需单独纹理图，透明度从 .12 起按图调整，不能由 screen-grain 冒充。植物暗纹是插画图层，建议透明度 .06–.12，不是随机噪点。摄影与纹理分层，纹理不污染香水瓶高光及可读文案。

### 背景、局部图块、文字与安全区

| 层／对象 | 布局关系 | 保护范围与调整 |
|---|---|---|
| 红黑章底 | 连续朱砂→黑色色场，细纤维、大斑驳是两个尺度的独立层 | 大尺度斑驳尚需真实纹理素材；不能用提高细噪点强度代替；外侧棕色展示底没有作为页面纹理入库 |
| 书法主标题 | 大小字错落构成独立字组，短引言在其下方净空 | 保留字间负空间；定制书法须真实字形，不能任意拉伸宋体；黑色退场不能吞掉细金字 |
| 香调图文 | 插画／产品在左右不同位置，章节号与短说明沿邻近净空安排 | 不是等宽两列卡片；引导曲线位于文字之外，不能横穿字行、瓶标或花果主体 |
| 局部方图 | 末段小型产品／材质比较可保留矩形图窗；香调主体融底须采用透明主体或与共同红黑场同源的场景素材，不将独立矩形实景靠渐变强融 | 不给每个香调段添加卡片底、边框或统一阴影；小图留自身安全边距，不强拉成通栏 |
| 黑底静物 | 大幅石榴／香水静物可独立占据章节上部，文字置下部或侧边黑场 | 产品轮廓、瓶盖高光、花瓣与果实关键轮廓是保护区；若实际照片缺少净空，先编辑扩展同源场景或在同组阅读区重排；不自动追加通栏说明条 |
| 植物暗纹 | 插画装饰层位于底色上、正文下，原记录opacity .06–.12仅为试排范围 | 字后暗纹仍须可读性检查；减少／移开暗纹优先于增加文字描边，暗纹不是随机噪点 |

以画幅W试排，必要文案横向边距约6–8%W；文字与主体可见轮廓、引导曲线之间先保留约3–5%W净空。局部图块安全区基于自身轮廓计算，不沿用全页边距。上述为布局起点，不是已从低清图精确量得的值。每个段落分别记录文字框、产品保护区和纹理允许区域；文案增长时增段高、移动插画，不能靠减字距或将文字淡化避让。

层级：章底色→细纸纹／独立云斑→低对比植物暗纹→主插画与产品→引导线和文字（线仍在文字保护区外）。纹理与背景可共同渐退至黑，产品和文字不继承此mask。安全区不仅检查越界，还检查文字与高频斑驳、明亮摄影和装饰线的空间冲突。

纹理实现状态：细纸纹及红黑色场已有代码／依赖；大尺度红褐云斑、真实印染起伏与石榴植物暗纹仅记录了素材职责和参数，尚未形成独立可调用纹理资产。本次不得将这部分标为“完整提取”。外侧展示底若单独作为纹理参考处理，应另登记来源和用途。

### 连续图文的素材交接

先将香调叙事组织为同一红黑场内的阅读组，再分配果实、花卉、木质与短说明；初／中／尾调不是三个必须切底的独立海报。主图与短文案联合确定高度，索引不以大段空白撑满一屏。主体位置、景别和疏密推动阅读，红黑渐变与纹理坐标在组内连续。

每张图在原 asset_slots 声明透明主体、同源场景或独立图窗，并给出邻接区域和保护范围。同源场景共享背景与光向；透明花果保留真实轮廓；木质若是独立材质证据图，保留有意取景边界，不以模糊黑边冒充空间连续。先预合成一组香调图文检查接缝与阅读密度，再扩展其余段落。收束商品图有新的总结／行动职责才保留，避免重播首屏。

<a id="combination.oriental-family-album"></a>

## 东方家族影像册

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 暖白纸是成品底；外侧粗糙灰米展示底不进入长页，布纹属于照片。 |
| 图片／装饰素材 | 大人像、花窗照片、卷轴照片各自独立；花窗mask与边框同路径。 |
| 文字归属与阅读顺序 | 中英短题放图间纸面，照片内短题只占真实净空；卷轴图注在图外。 |
| 页面／容器／素材安全区 | 沿64–90px页边距起排；扣花窗收口和卷轴端头；头顶、手部、边缘人物都需保护。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400 |
| 章节／卖点题 | Songti SC 700 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Bodoni 72 400用于ORIENTAL式英文，短数字400 |

匹配依据与边界：中英高反差衬线构成雅致编辑感；书法小签不是整页字体。


风格标签：二级：新中式风 / 当代东方。

依据新增家族摄影长页：中式服装与陈设、花窗式取景、卷轴、暖纸和现代中英编辑排版形成组合。不能仅凭米色或拱窗把其他页面归为新中式。展示板外侧的粗糙灰米底、英文制作说明及外投影不是长页背景。

| 对象 | 复用入口 | 局部参数／组装 |
|---|---|---|
| 色彩 | [暖纸棕](../colors/palettes.md#palette.warm-paper) | tint=#f1eadc，ink=#211c17，muted-ink=#6a5e4b，accent=#a08b57，edge-color=#c8b47c；label-bg=#e4d7bc、label-ink=#352b20。朱红 #80382c 仅作小印记；不把照片服装颜色强行铺满纸底 |
| 开场 | [图像主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.4–1.8；人物照片占主要空间，标题可在照片安全空场或下方纸面，人物脸部不可遮挡 |
| 图文节奏 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow)、[疏朗正文](../layouts/airy-and-spacious.md#layout.reading-column) | 大幅照片→中英短题→花窗照片→卷轴照片；横向边距约 64–90px，图间距 100–160px，短说明与照片独立 |
| 普通拱窗 | [拱形图片窗](../shapes/cards-and-panels.md#shape.arch-window) | 只用于单拱图窗；金色描边约 1–2px。复杂多瓣花窗不能直接用单拱代替；定制 mask 与边框使用同一路径，先核对人物裁切 |
| 纸底细纹 | [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper) | texture=asset:svg/paper-fiber.svg，grain=.06–.12，texture-size=256–384px，multiply；放在纸色上、照片与文字下，不加全页阴影 |
| 稀疏纸屑 | [共用纹理层](../surfaces/materials.md#surfaces.texture-field) | 与密集纤维分开：少量不规则棕灰颗粒，静态节点尺寸约 1–3px、opacity=.12–.22，每 1080×1080 区域先试 12–24 个；固定坐标，可按内容避让。不是彩色屏幕噪点，也不是规则波点 |
| 织物 | [织纹近似](../surfaces/textile-and-craft.md#surface.woven-grid) | 默认不叠加：背景织物已存在于照片。仅当另做独立布面装饰时可试 step=5px、line=.5px、opacity=.06；实际布面起伏由素材提供 |

纹理分工：暖白纸面的零散颗粒属于可编排表面；人物服装、背后布面和地毯属于摄影，保留原图。外底看似压纹／粗纤维的起伏无法仅凭截图确认材质，也不并入纸纹默认值。长页本身不需要强渐变；优先保持干净暖纸与照片清晰切换。

卷轴端头、织锦滚轴及装饰花窗属于形状／素材依赖，并非已有 CSS 原子已完整覆盖。使用授权素材或任务专用 SVG；新增可复用 SVG 随 skill 保存，以 asset:svg/... 短引用交由现有脚本内嵌；不编造云端短链、不在 Markdown 展开 SVG。复杂花窗必须检查头顶、手部和边缘人物是否被裁；卷轴照片保持为独立可替换节点。

三组纹理复核：以最终输出宽度和缩小到手机宽度各看一次，检查纤维是否消失、织纹是否产生摩尔纹、纸屑是否像污点、渐隐是否留下接缝。上述值为可调起点，不宣称是原图精确参数；通用纸纹、织纹和渐变不新增风格标签。

<a id="combination.doodle-learning-guide"></a>

## 手绘涂鸦知识长页

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 奶油连底，大色块用于章节与书封；木桌只在开场局部。 |
| 图片／装饰素材 | 抱书人、文具、翻角为插画，书页／便签是容器，边框抖动不传给字行。 |
| 文字归属与阅读顺序 | 标题在人物上方；封面引言、页内知识、对话框各自对应；进度条是章间装饰。 |
| 页面／容器／素材安全区 | 沿原64–90px页边距；扣书脊、翻角、夹板夹口；人物手和水果不能盖正文。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | JiangChengLvDongHei 700（许可待核；替代 Alibaba PuHuiTi 2.0 900） |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 700 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Chalkboard SE 700用于手写英文，数字沿正文 |

匹配依据与边界：江城起伏字面较接近趣味手写，仍不等于原手绘字；描边只在大标题且不堵字。


风格标签：二级：趣味创意风 / 涂鸦手作。

归属依据：粗黑抖动轮廓、文具插画、书本／便签式信息容器、明亮分章色和中英混排共同形成手绘知识指南。与 [复古高饱和拼贴](recipes.md#combination.retro-pop-collage) 共享颜色和少量形状，但本组合以讲解顺序和手绘线条为主，不默认照片拼贴、复古网点或纸纹。用户开学指南图为视觉依据；文字事实与示例品牌不进入模板默认文案。以下按 1080px 输出宽度换算为试排起点，不宣称原图精确参数。

### 配色与文字配搭

复用 [红黄蓝纸本撞色](../colors/bright-and-playful.md#palette.primary-pop) 的颜色角色，局部覆盖为奶油、天蓝、糖粉、黄绿、柠黄，不另建同机制 palette：

```css
.vl-doodle-guide {
 --vl-tint:#fcf7e5; --vl-ink:#171714; --vl-muted-ink:#48483d;
 --vl-accent:#149dd1; --vl-accent-2:#e984b6; --vl-accent-3:#a9d84c;
 --vl-edge-color:#171714; --vl-label-bg:#149dd1; --vl-label-ink:#ffffff;
 --guide-yellow:#f4e744;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

| 对象 | 字体／字号关系 | 色彩与排版 |
|---|---|---|
| 首屏主标题 | 粗黑体或经确认的手绘展示字，约 120–160px，行高 1.05–1.15；最多 2–3 行 | 蓝／粉逐行区分，黑边约 2–4px，仅大字使用；复用 [文字描边](../layouts/layout-and-type.md#text.outline)，保持字腔清晰；偏斜定制字形另需字体或艺术字 |
| 章节导航 | 中文粗黑体 56–72px＋窄体／手写感拉丁章节序号 48–60px | 黑色承载标题主句，括号中的主题蓝、粉、绿按章固定；英文仅短标签，拼写按真实内容校对，不复制参考中的拼写问题 |
| 副标题 | 粗黑体 44–54px，行高 1.25–1.4 | 黑字搭小段同色下划线／重点色块，不整行加描边 |
| 正文 | 清晰常规黑体 32–40px，行高 1.45–1.65 | 深色为主；关键词可用章色，但浅粉／黄绿文字在奶油底不够清晰时改深色字＋色块，不能以原色强行套用 |
| 书封／色签 | 中粗字 42–56px | 大字可白字配较深粉／蓝，长文用深色字；随实际色值检查对比度 |
| 英文手写补笔 | 24–32px | 小面积辅助，不能承担正文；中文正文不跟随变成难读的手写体 |

页面视觉面积起点：奶油／白约 65%，明亮色块约 25%，黑字和描边约 10%；这些是布局估计而非像素采样。章色各有职责，黄色主要用于人物、进度提示和小装饰，不能把五种亮色平均撒到每个模块。主展示中文＋短英文辅助＋清晰中文正文构成搭配，不识别或虚构原字体名称。

### 布局、图文与线条

| 对象 | 原子／实现 | 参数与限制 |
|---|---|---|
| 开场 | [主场](../layouts/hero-focus.md#layout.image-stage) | H/W约1.35–1.6；上部主标题，下部人物抱书，书封承载短引言；插画与可编辑标题分层 |
| 知识分章 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow) | 横向安全边距约64–90px、章间距100–150px；疑问概览→连续知识章→结语，数量由内容决定 |
| 对话解释 | [对话框](../shapes/cards-and-panels.md#shape.speech-panel) | 复用文本、尾部独立结构；粗边3–5px、内边距36–48px。手绘不规则边不是该规则圆角自动生成的，必要时用任务SVG路径 |
| 便笺／夹板 | [衬纸](../shapes/notes-and-paper.md#shape.paper-mount)、[简化夹子](../shapes/notes-and-paper.md#shape.binder-clip) | 夹子作为独立节点，外框绿、夹子蓝；文字另层；翻角、活页孔、书脊等定制形状需素材或路径，不用撕纸mask冒充 |
| 书本内容 | 书本插画／定制边框＋独立正文区 | 先给文字留净空和中缝安全区，再配书页轮廓；页内行距不随边框抖动 |
| 装饰 | 文具、水果、问号、音符等图标或插画 | 优先出现在节点边角与章节起点；不遮字、不让每个段落都增加装饰 |

装饰进度条只提示阅读节奏，非真实加载状态。规则几何可用以下局部近似，外边轻微手绘感需独立路径；fill 取0%–100%，多章可递增，不能据此声称任务完成率：

```css
.vl-guide-progress { position:relative; height:26px; border:3px solid #171714; border-radius:16px; overflow:hidden; background:#fffbed; }
.vl-guide-progress__fill { position:absolute; inset:0 auto 0 0; width:var(--guide-progress,33%); background:#f4e744; }
.vl-guide-progress__stripes { position:absolute; inset:0; background:repeating-linear-gradient(110deg,transparent 0 30px,#171714 30px 33px); }
```

使用三个实际节点容器／fill／stripes，纹理层在fill之上、文字之外。默认没有表面噪点、强光或渐变。手绘质感来自轮廓和笔画的轻微不规则，而非全页加 grain 或扭曲文本；原图桌面木纹属于局部插画／图片，不铺满全文。

素材需求：抱书人物、打开的书本、复杂翻角和有特征的手绘轮廓。已有CSS承担布局、色彩、文字和规则进度条；未提供素材时明确缺口。导出前检查大标题描边是否堵字、粉绿关键词是否可读、书页正文是否碰边、装饰是否遮住阅读顺序。

<a id="combination.playful-product-editorial"></a>

## 潮玩拟物产品长页

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 白／浅灰功能板，黑色章节条明确换章，不满页加纸纹。 |
| 图片／装饰素材 | 主产品、多色款、细节、拆解图按各章事实选镜头；挂件为配角，不靠旋转复用一个视角。 |
| 文字归属与阅读顺序 | 上方／侧方粗标题与图像净空配对，英文在中文下方成组，箭头指向实际部件。 |
| 页面／容器／素材安全区 | 原40–64px内容距；保护吸管、杯口、挂件和结构端点，长标题先重排图文。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 900 |
| 章节／卖点题 | Source Han Sans 900 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | DIN Condensed 700短英文，规格数字沿正文500 |

匹配依据与边界：参考是紧凑但端正的编辑粗黑，不能因玩具题材换成细窄斜得意黑。


风格标签：二级：趣味创意风 / 趣味拟物。

归属依据：玩具感产品比例、爱心／花朵挂件、趣味标签与粗黑编辑排版共同构成商品展示，不能仅凭黑白红归类。用户杯子长图已分段检查；记录构图和素材用途，不将参考品牌、结构参数、材质与功能宣称用作其他产品的真实事实。以下为1080px宽的近似试排参数。

### 配色与文字布局

沿用 [红黄蓝纸本撞色](../colors/bright-and-playful.md#palette.primary-pop) 的变量机制，局部换为白／浅灰／黑／深红；黄、蓝、粉主要来自真实产品色款，不让参考产品色成为所有商品的固定配色。

```css
.vl-playful-product {
 --vl-tint:#ffffff; --vl-ink:#080d0c; --vl-muted-ink:#414442;
 --vl-accent:#a22736; --vl-accent-2:#e7e7e5; --vl-accent-3:#ead9ca;
 --vl-label-bg:#080d0c; --vl-label-ink:#ffffff; --vl-edge-color:#080d0c;
 background-color:var(--vl-tint); color:var(--vl-ink);
}
```

| 文字角色 | 参数起点 | 空间关系 |
|---|---|---|
| 首屏主标题 | 极粗黑体约140–185px、行高.98–1.08，2行主句 | 左上主导，短红色椭圆签在剩余空白；大字不压过商品身份关键部件 |
| 功能章节标题 | 粗黑体约100–140px、行高1.05–1.15 | 常用左上两行／右上两行；复用 [错位标题](../layouts/asymmetric-balance.md#layout.staggered-title)，按图片净空选择，不把每段随机倾斜 |
| 英文对应词 | 紧凑粗体约34–52px、全大写短语、行高1.05–1.15 | 在中文下方成组，或另一侧作较小平衡块；不承担必要信息，不复制装饰小字或品牌英文 |
| 章间黑条 | 黑底白字24–36px，条高约80–120px | 承接章节，短栏目名／品牌和信息分左右；图文板块以浅灰间隙分隔 |
| 功能短注 | 粗黑体36–48px、行高1.2–1.4 | 紧靠指向对象的净空，椭圆圈或箭头作为辅助；长解释移到图下 |
| 章末总结 | 粗字40–54px | 主图下方单句收束，与页首主标题形成层级，不新增一套大标题竞争 |
| 真实规格 | 常规／中粗字32–42px、行高1.4–1.6 | [规整网格](../layouts/grid-and-alignment.md#layout.evidence-grid) 与分隔线，名称／值明确对应；不得以小装饰字代替规格 |

不要为塞长标题横向压扁字形；优先重新分行、调整图像位置，再适度降字号。竖排英文仅作边缘装饰，不强制每段添加。色签、括号和星芒只是强调手段，避免同一句同时套满。

### 图文关系：根据功能选择版式

复用 [主场](../layouts/hero-focus.md#layout.image-stage)、[章节流](../layouts/continuous-flow.md#layout.chapter-flow) 和 [图像标注](../layouts/grid-and-alignment.md#layout.annotated-figure)。开场H/W约1.7–2.1，单个功能章约1.25–1.7；短细节横条单独降低，不统一锁定全部段高。白色图文板圆角约32–44px，浅灰章间隙约8–16px，内容安全边距40–64px。

| 关系 | 实际编排 | 约束 |
|---|---|---|
| 顶部标题＋主物件 | 顶部约20–28%用于标题，产品占主体区，下方短收束 | 大产品约占章节视觉面积55–70%，图片可以出画，但吸管、开口等当前卖点不可裁掉 |
| 对角多色款 | 产品沿对角线错落，标签跟随色款，文字留在剩余角落 | 每个色款是独立真实资产；不靠CSS滤镜改色冒充商品SKU |
| 近景材质 | 标题在上，杯口／表面大特写在下并可局部出画 | 图像重点和标题卖点一致，只有该材质被真实确认才配对应说明 |
| 结构分解 | 主体在右或中间，编号／标签位于左侧或图下 | 图层顺序依照真实结构，箭头端点跟随部件位置；不可把3列标注原子硬套全部拆解图 |
| 双模式对照 | 两个不同功能部位分居上下或对角，短标签各自贴近 | 保持阅读映射，不重复放同一角度图冒充两个模式 |
| 场景组合 | 桌面用品／饮品围绕主产品，色调统一，顶部留字 | 环境配角体量和对比弱于产品；不在视觉上混淆商品与赠品 |
| 横条细节 | 文字占左侧约35–42%，右侧为局部裁切大图 | 使用图片真正的空白区，不能直接用白色遮罩盖掉功能部件 |
| 收尾规格 | 产品家族合照在上，结构化数据在下 | 所有色款比例统一；规格必须来自用户资料，参考只是排版示范 |

### 产品配图清单与资产职责

| 配图类型 | 需要表现什么 | 素材准备要求 |
|---|---|---|
| Hero主视角 | 完整轮廓、造型趣味、识别性部件 | 3/4视角，产品与可选挂件分清；上方预留标题空间，输出尺寸按主场比例 |
| 色款组合 | 不同配色与统一系列关系 | 保持同一型号几何、比例、镜头与光向；各色款单独透明底或一致白底 |
| 材质特写 | 内胆、表面、边缘、接合等真实材质 | 宏观纹理与高光来自摄影／渲染，CSS不替代；不能随意给所有部件同一塑料质感 |
| 结构／拆洗图 | 部件、连接顺序、操作方向 | 有产品结构资料再制作；保持结构准确，分解件与标注文案对应 |
| 使用场景 | 饮品、办公、携带等用途 | 选真实适用场景；搭配道具仅作情境，不自动列为包装内物品 |
| 功能演示 | 倒置、切换方式等视觉演示 | 功能已获真实资料支持后才制作；摔落／防漏图片不能独立构成性能证据 |
| 多角度／细节 | 顶部、侧面、底部和关键部位 | 围绕各章问题选角度，避免以同一主图任意旋转代替真实视角 |
| 系列与规格合照 | 一致尺度下的产品比较 | 保持相机、光照、投影一致，品牌及标识遵守真实素材 |

配图需求在同一素材清单中记录角色、所需角度、画幅、文字净空和事实依据；每张图与相应章节绑定，不只写“生成一张产品图”。主要产品、文字、圈签、箭头为独立可编辑层，照片原有标签不要重复叠加。

纹理与渐变：页面白／灰背景大体纯色，黑条为实色；产品本身有亮漆、磨砂、陶瓷般反光以及挂件的粗绒感，分别由对应素材提供，不全页铺噪点。阴影沿素材光向，避免重复CSS投影；仅在照片白底与版面白色存在细微接缝时调整素材或安全空场，不对产品边缘强行渐隐。真实材质名称以产品资料为准，截图只说明视觉感受。

调用前检查产品是否具有趣味造型或配件，普通严肃设备不因粗黑标题就强制玩具化。导出时核对长标题、产品部件裁切、颜色真实性、箭头对位、灰白接缝与规格可读性。

<a id="combination.osmanthus-poetic-light"></a>

## 桂花柔光香叙

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 共用奶金柔光底，不给每件产品添加不透明矩形卡。 |
| 图片／装饰素材 | 瓶偏右、罐偏左且错落于连续场景；花影／丝带在独立气氛层，具体顺序沿本条单品区。 |
| 文字归属与阅读顺序 | 标题随产品邻近净空定位，卖点另沿左侧清晰区域；不是机械镜像两列。 |
| 页面／容器／素材安全区 | 沿单品区实际坐标试排，保护瓶标及罐沿；花影不占卖点行，柔焦不传给文字。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400 |
| 章节／卖点题 | Songti SC 400 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 400 italic用于香调英文；小数字400 |

匹配依据与边界：较细宋体与古典斜英文接近原图轻盈感；字体自身不用blur，细笔画靠足够对比保护。


风格标签：二级：诗性浪漫风 / 情绪影像。

归属依据：暖金人物与静物摄影、虚实花影、诗句留白和香调叙事共同构成情绪影像。香氛题材本身不是判断条件，也不只凭奶油金配色归类。以用户桂花洗护参考为依据，三列展示不变成成品三列布局。下列按1080px宽试排，非原稿精确值。

| 对象 | 原子引用 | 覆盖与图文关系 |
|---|---|---|
| 配色 | [桂香奶金](../colors/soft-and-muted.md#palette.osmanthus-cream) | 奶油约60–70%、暖金摄影约25–35%、棕色文字少量；照片颜色不强制服从精确比例。浅章tint=#f2eddb、ink=#514733；深暖章字=#fff6df，保证成对切换 |
| Hero | [主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.7–2.1；人物、屏风光影和产品礼盒构成场景，标题放上方净空，短引言放主体以下；图内已有艺术字时不重复叠标题 |
| 字体搭配 | [疏朗阅读栏](../layouts/airy-and-spacious.md#layout.reading-column) | 中文细宋／衬线＋细衬线英文，书写字只用于主题短题；标题64–90px、正文30–38px、英文辅题24–30px，正文行高1.6–1.85。细字不可淡到不可读，不虚构原字体名 |
| 短诗与香调 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow) | 短诗2–4行可居中，长正文左对齐；香调标签与内容成行对齐，英文词与中文名不散落成装饰；上下留白100–180px按文字量调整 |
| 产品介绍 | [图像标注](../layouts/grid-and-alignment.md#layout.annotated-figure) | 同一连续长图中产品右→左→右错落，标题和卖点沿各段实际净空分布；首个瓶身偏右、第二个罐体偏左。不是两个等宽栏，也不是图上文下或矩形照片与文字卡交替；见下方连续产品区实现 |
| 柔焦 | [局部柔焦与薄雾](../surfaces/diffuse-light.md#surface.soft-focus-mist) | 背景花枝或独立前景blur=12–24px、opacity=.6–.85；人脸、产品标识和正文保持清晰。原片有失焦先不加filter |
| 薄雾 | [局部柔焦与薄雾](../surfaces/diffuse-light.md#surface.soft-focus-mist) | 奶白雾层opacity=.10–.18，方向朝实际净空；色标可从rgb(249 245 228 / .85)到同色alpha0，范围不超过需要区域 |
| 暖光 | [弥散光晕](../surfaces/diffuse-light.md#surface.diffuse-field) | color=#d8a344、opacity=.12–.18、x=65%、y=35%、width=90%；只补素材没有的光层，不重复模拟原片光照 |
| 图片淡接 | [图片渐隐](../surfaces/diffuse-light.md#surface.image-fade) | 以最终裁切后的安全空场决定色标；原例80%／91% alpha.65／100%透明不作默认，落底色等于下章首缘；场景不相容则明确换章，不靠雾遮接缝 |

### 配图与质感职责

人物场景负责情绪开场；礼盒静物负责商品识别；桂花／茶杯负责香气联想；树皮或原料近景负责质感停顿；单品瓶罐负责功能说明。配图应共享暖光方向与奶油金环境，但不把每张照片全部蒙黄。通过视距变化形成长页节奏，不能同一产品图反复放大填充。

背景虚化的花枝、轻纱般光感、液体与包装高光来自摄影／渲染；CSS薄雾只做辅助。纸粒默认关闭，不能用噪点冒充空气感。柔焦记录到具体图层及保护区域，不只写“朦胧风”。实际洗护功效、香调和原料须来自用户资料，参考中的数字与文案不默认继承。

复核：细宋体与白字在金色亮区的对比，朦胧图是否丢失产品识别，薄雾是否遮标，照片与章节是否自然衔接。主体可以具有原生摄影柔感，但不因组合要求对全部主体强制滤镜。

### 单品区：连续画布中的左右产品与文字

本段专门约束参考右侧的产品介绍长图，不改变前面的暖金人物开场、诗句或礼盒静物章节。

- **第一段：瓶身偏右**，标题在左上；第一组卖点在左侧，后续卖点向左下延伸。产品与轻纱／花影可以越过想象中的中线，文字避开瓶标与浓重图像。
- **第二段：罐体偏左**，标题在右上；罐体周围保留大面积柔雾空场，说明落在下方偏左的净空。不是把第一段机械镜像成“左图右文”。
- **后续段：产品继续左右错落**，标题与注释按素材净空安排，顺着长图从上到下阅读。第三段完整下部在当前裁切中不可见，示例位置仅为可调整骨架，不当作精确还原。
- 页面共享奶油雾色底，产品图透明底或用同色环境自然淡接。**不得使用带完整窗台、桌沿与矩形边界的照片卡来替代漂浮产品场景**。复杂纱幔和局部失焦用素材处理，不给整张产品统一高斯模糊。
- 标题、产品、卖点和环境层彼此独立。可以用不可见网格辅助定位，但成品不能出现等宽双栏分割、卡片边框、统一编号列或逐段硬切背景。

以下CSS只负责位置和层级。cqw按连续画布宽度缩放；文本超过约定长度时，应增加段高并下移后续内容，不能压缩字距或裁字。每个figure需插入真实img（尺寸与alt由素材决定），素材应自带合适透明边缘，空槽仅用于排版测试。

```css
.vl-osm-stream {container-type:inline-size;position:relative;isolation:isolate;overflow:hidden;background:#eeeadd;color:#615c47;font-family:"Songti SC","Noto Serif CJK SC",serif;}
.vl-osm-scene {position:relative;min-height:160cqw;isolation:isolate;}
.vl-osm-scene::before {content:"";position:absolute;inset:-8cqw -12cqw;z-index:-1;pointer-events:none;background:radial-gradient(ellipse at 75% 44%,#d9c18a33,transparent 64%);}
.vl-osm-heading {position:absolute;top:7cqw;left:7%;width:85%;z-index:3;margin:0;font-size:6cqw;font-weight:400;line-height:1.35;}
.vl-osm-heading small {display:block;font-size:3.6cqw;font-style:italic;line-height:1.5;margin-bottom:1cqw;}
.vl-osm-product {position:absolute;top:32cqw;left:39%;width:70%;height:85cqw;margin:0;z-index:1;display:grid;place-items:center;}
.vl-osm-product img {display:block;width:100%;height:100%;object-fit:contain;}
.vl-osm-benefits {position:absolute;left:7%;top:40cqw;width:34%;z-index:3;font-size:3.7cqw;line-height:1.6;}
.vl-osm-benefits p {margin:0 0 5cqw;}.vl-osm-benefits strong {display:block;font-size:4cqw;font-weight:500;}
.vl-osm-benefits--lower {top:108cqw;width:48%;}
.vl-osm-scene--left {min-height:164cqw;}
.vl-osm-scene--left .vl-osm-heading {left:auto;right:7%;text-align:right;}
.vl-osm-scene--left .vl-osm-product {left:-9%;top:32cqw;width:78%;height:80cqw;}
.vl-osm-scene--left .vl-osm-benefits {top:111cqw;left:7%;width:60%;}
.vl-osm-atmosphere {position:absolute;inset:0;z-index:2;pointer-events:none;}
.vl-osm-atmosphere::after {content:"";position:absolute;inset:60% -10% -8cqw;background:linear-gradient(180deg,#eeeadd00 0%,#eeeadd00 45%,#eeeadd80 80%,#eeeadd 100%);}
.vl-osm-scene--left::before {background:radial-gradient(ellipse at 24% 50%,#d8ba7830,transparent 64%);}
```

```html
<div class="vl-osm-stream">
 <section class="vl-osm-scene vl-osm-scene--right">
  <h3 class="vl-osm-heading"><small>Product / 01</small>洗发水 · 产品名称</h3>
  <figure class="vl-osm-product" data-slot="transparent-product-right" role="img" aria-label="右侧漂浮瓶身素材槽"></figure>
  <div class="vl-osm-benefits"><p><strong>卖点一</strong>左侧净空内的短说明。</p></div>
  <div class="vl-osm-benefits vl-osm-benefits--lower"><p><strong>卖点二</strong>沿产品下侧留白继续说明。</p><p><strong>卖点三</strong>保持文字独立清晰。</p></div>
  <div class="vl-osm-atmosphere" aria-hidden="true"></div>
 </section>
 <section class="vl-osm-scene vl-osm-scene--left">
  <h3 class="vl-osm-heading"><small>Product / 02</small>发膜 · 产品名称</h3>
  <figure class="vl-osm-product" data-slot="transparent-product-left" role="img" aria-label="左侧漂浮罐体素材槽"></figure>
  <div class="vl-osm-benefits"><p><strong>卖点一</strong>罐体下方的说明文字。</p><p><strong>卖点二</strong>长句按文字量增加段高。</p></div>
  <div class="vl-osm-atmosphere" aria-hidden="true"></div>
 </section>
 <section class="vl-osm-scene vl-osm-scene--right">
  <h3 class="vl-osm-heading"><small>Product / 03</small>护发精华 · 产品名称</h3>
  <figure class="vl-osm-product" data-slot="transparent-product-right" role="img" aria-label="右侧精华素材槽"></figure>
  <div class="vl-osm-benefits"><p><strong>卖点一</strong>沿侧边净空排布。</p></div>
  <div class="vl-osm-atmosphere" aria-hidden="true"></div>
 </section>
</div>
```

环境渐隐只是装饰层，不能覆盖标题与卖点；若侵入产品识别区，应调整渐隐起点而非降低整组opacity。产品的漂浮角度优先由素材决定，不统一旋转不同包装。花枝仅在边角或两段之间作连接，照片自带纹理不重复叠加纸粒。

<a id="combination.woody-scent-editorial"></a>

## 木质香氛编辑长页

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 浅灰米编辑底与黑花影章交替；真实木纹仅是一段近景，不平铺全文。 |
| 图片／装饰素材 | 大产品静物保持矩形，小图左右错落但不旋转；花影拖影来自图像。 |
| 文字归属与阅读顺序 | 上中英短题、长文左对齐，小图对应邻近段落；淡英文只作次级层。 |
| 页面／容器／素材安全区 | 原26–38%小图宽按阅读检验；保护瓶标，字不压高频木裂纹；图窗扣图注净距。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400 |
| 章节／卖点题 | Songti SC 400 |
| 正文／注释 | Songti SC 400 |
| 英文／数字 | Baskerville 400／400 italic；数字沿对应字体 |

匹配依据与边界：细衬线及留白接近编辑原图；资料说明很密时可单独选 Source Han Sans 400，不整页默认粗黑。


风格标签：二级：自然质朴风 / 侘寂质朴。

归属依据：粗粝木皮与克制瓶身、黑白花影、低饱和色场和疏朗图文共同体现自然材质的静谧对比；编辑版式是组织方式，不仅凭衬线字体判风格。用户木质香氛参考首屏到末尾已分段查看；低分辨率背景细纹不作精确材质判断。按1080px画幅给出近似参数。

| 对象 | 原子引用 | 覆盖与图文关系 |
|---|---|---|
| 色彩 | [暖纸棕](../colors/palettes.md#palette.warm-paper) | 局部tint=#e6e5d9、ink=#33342b、muted-ink=#5e5d51、accent=#80634b、label-bg=#33342b、label-ink=#f0eee2。暗章底=#0c0e09、字=#eeeade；棕色主要来自木料而非全页滤色 |
| Hero | [主场](../layouts/hero-focus.md#layout.image-stage) | H/W=1.8–2.2；上部中英标题，中下部横向朦胧花影；超大淡英文仅作次级背景，不能遮住必要中文 |
| 字体 | [阅读栏](../layouts/airy-and-spacious.md#layout.reading-column) | 细衬线英文标题66–96px，中文标题58–80px，正文30–38px／行高1.65–1.9；不把参考中极小的装饰字当信息承载；留白比阴影与边框更重要 |
| 编辑节奏 | [章节流](../layouts/continuous-flow.md#layout.chapter-flow) | 黑色花影→浅灰短文→黑白图组→产品静物→木纹满幅横章→品牌服务说明→产品收尾；由实际内容取舍，不复制固定营销章节 |
| 小图错落 | [叠层拼贴](../layouts/overlap-and-collage.md#layout.collage) | 复用网格但rotate=0，不默认胶带纸边；图宽约26–38%，左右错位留出正文，不随机重叠 |
| 主产品静物 | [主场](../layouts/hero-focus.md#layout.image-stage) | 独立矩形大图，瓶身与木块对比明确；构图预留标题和瓶标；主图保持高于小图组的视觉权重 |
| 木纹章节 | 真实近景素材＋[章节流](../layouts/continuous-flow.md#layout.chapter-flow) | 用木截面／木皮宏观纹理作为一段转场；不可把少量木纹拉伸铺满长页，文字放实际暗部净空 |
| 局部失焦 | [局部柔焦与薄雾](../surfaces/diffuse-light.md#surface.soft-focus-mist) | 默认blur=0；选用自带横向拖影的花影素材。普通背景柔化可试8–16px，但不能声称复原首屏方向性拖影；雾层默认关闭 |
| 边缘过渡 | [图片渐隐](../surfaces/diffuse-light.md#surface.image-fade) | 只有首屏图像安全空场需融入黑底时才加；其他编辑图片保持矩形边界，避免每张图都被模糊成光团 |

### 材质、配图和清晰层级

- 黑白花影：传达气味与空间的情绪，允许局部失焦和原生拖影；正文不可用同一滤镜。花瓣轮廓仍需有辨识度。
- 木块与瓶身：粗木裂纹／边缘与清洁瓶面产生材质对比。金属或玻璃具体材质以产品资料为准，截图只用于视觉参考；不能对二者统一叠纸纹。
- 木纹横图：提供章节停顿和微距尺度；摄影已有方向性模糊时不额外加全局blur。
- 产品小图组：不同规格或使用形态的真实照片，保持光向、比例与留白一致；错位图组由网格组织，不靠随机旋转冒充编辑感。

浅灰米底可先用实色；只有更清晰参考确认纤维后才复用 [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)，grain=.04–.08作为轻量试排值，不能将截图缩放纹理直接判断为纸面。木纹、花影、瓶身均保留为实际素材，不新造“木纹噪点”SVG。

长文左对齐，短引言可居中；中英文各有层级，细分隔线约1px、间距80–150px。核对浅字对比、瓶身标签、木纹是否重复平铺、小图错位是否打乱阅读顺序。参考品牌服务、产品用途与广告陈述不自动纳入其他产品的事实。

<a id="combination.camera-ui-explainer"></a>

## 相机界面与蓝白说明长页

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 天空蓝相机主场转浅灰信息底；白色窗是正文容器。 |
| 图片／装饰素材 | 雪山置取景框内、快门置下方；对比照片位于信息窗，状态角标独立。 |
| 文字归属与阅读顺序 | 中文衬线主句与黑体关键词混排；窗内先正文后对照，图注对应照片。 |
| 页面／容器／素材安全区 | 扣信息窗顶栏与内距；取景角线不穿字；状态标记不盖对比重点，渐隐不擦山体。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Songti SC 400；关键词 Source Han Sans 700 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Arial 400用于技术英文／数字 |

匹配依据与边界：混排按字组绑定，不能让根节点一种Arial回退吞掉衬线主句。


风格标签：二级：未来科技风 / 产品科技。

归属依据是相机取景框、快门控件、桌面信息窗与对比图共同构成产品技术说明，而不是单凭蓝色。首屏图像主导，下部转为清晰说明；与科研分子结构不同。

复用 [证据网格](../layouts/grid-and-alignment.md#layout.evidence-grid)、[图片渐隐](../surfaces/diffuse-light.md#surface.image-fade)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 白灰#f0f0ef约60%，天空蓝#079de2/#0064b8约30%，文字#222及局部蓝#468edf；绿黄仅标记关键词 |
| 文字 | 主标题可用中文衬线与黑体关键词混排；说明题24px/700，正文13px/1.7；不识别为某个精确字库 |
| 主视觉 | 雪山天空素材约首屏55%；取景角线为绝对定位装饰，快门置底；正文不能嵌进截图 |
| 卡片／纹理 | 白色信息窗在浅灰底，顶部三色窗点，圆角12px；页面本身不加颗粒 |
| 渐变 | 天空底#0265be→#16b2df；下缘白雾独立层 alpha0→1；不模糊标题 |
| 图文关系 | 窗内先短文后2×2对比图；状态标记放图角，说明为独立图注 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-camera {background:#efefee;color:#222;font-family:Arial,"PingFang SC",sans-serif;padding:0 18px 28px;}
.vl-camera__hero {position:relative;isolation:isolate;min-height:360px;padding:26px 18px 50px;margin:0 -18px 26px;background:linear-gradient(160deg,#0564b9,#13abe1);color:white;border-radius:0 0 28px 28px;overflow:hidden;}
.vl-camera__hero:after {content:"";position:absolute;inset:75% 0 0;background:linear-gradient(transparent,#efefee);z-index:-1;}
.vl-camera h2 {font-size:30px;line-height:1.2;font-weight:400;margin:0 0 24px;}.vl-camera h2 b{font-weight:800;}
.vl-camera__view {height:155px;border:1px solid #a8e7ee;border-radius:18px;display:grid;place-items:center;object-fit:cover;width:100%;}
.vl-camera__shutter {width:44px;height:44px;border:6px solid #d4f4fa;border-radius:50%;margin:18px auto;background:#fff8;}
.vl-camera__window {background:#fff;border-radius:12px;overflow:hidden;margin:20px 0;padding:0 14px 16px;font-size:13px;line-height:1.7;}
.vl-camera__bar {background:#e2e3e3;height:22px;margin:0 -14px 12px;padding-left:12px;letter-spacing:3px;color:#4195d3;}
.vl-camera__compare {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}.vl-camera__compare>*{min-height:82px;background:#e3edf1;border-radius:6px;padding:8px;}
.vl-camera h3 {font-size:23px;color:#468edf;margin:26px 0 10px;}
```

```html
<article class="vl-camera"><header class="vl-camera__hero"><h2>图像技术<br><b>所见与所得</b></h2><div class="vl-camera__view" data-slot="hero">雪山天空素材</div><div class="vl-camera__shutter" aria-hidden="true"></div></header><h3>清晰呈现每个细节</h3><section class="vl-camera__window"><div class="vl-camera__bar" aria-hidden="true">●●●</div><p>先解释技术解决的问题，再呈现同条件的对比。</p><div class="vl-camera__compare"><div data-slot="before">对比图 A</div><div data-slot="after">对比图 B</div></div></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.ocean-orbit-campaign"></a>

## 海洋星球与地点卡活动

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 深海蓝转钴蓝，白胶囊与彩色地点板独立；星空颗粒仅局部。 |
| 图片／装饰素材 | 星球轨道占首屏下半，作者图卡横排，地点信息纵排。 |
| 文字归属与阅读顺序 | 顶部厚白字；地点、日期、地址按行对应，局部衬线关键词有独立角色。 |
| 页面／容器／素材安全区 | 轨道绕过标题，地点板扣圆角及标签；人物卡保护脸，静态版完整呈现必要地点。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 900 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 700；局部关键词 Songti SC 700 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Kodchasan 700短英文；日期沿正文500 |

匹配依据与边界：厚字比得意黑窄斜字更贴近；需要宋体关键词时算明确混排，不强制增加家族。


风格标签：二级：趣味创意风 / 趣味拟物。

星球、轨道与海洋被拟物成活动空间；明快地点卡形成信息节奏。与未来科技设备说明分开。

复用 [横向卡列](../layouts/grid-and-alignment.md#layout.card-rail)、[弥散光](../surfaces/diffuse-light.md#surface.diffuse-field)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 钴蓝#0759cc主底约65%，白/青#c8f7ff说明面；黄#e8fa56、紫#bba3f1、绿#4beaac作为地点分类 |
| 文字 | 主标题34px/900、紧行距1.05，白字轻光晕；章节标题蓝色28px，中文衬线关键词可局部穿插 |
| 图文 | 星球轨道素材占首屏下半，不能穿过主标题；作者图卡横向展示；地点卡纵向堆叠，每卡左地点右日期/地址 |
| 卡片 | 白胶囊边框与青色短标签，地点卡圆角18px；卡片颜色分类须同时带文字标签 |
| 渐变／纹理 | 顶部深海蓝→钴蓝；星球光圈来自素材，标题阴影局部；细颗粒仅在星空/行星，不默认满页 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-ocean{background:linear-gradient(#032a58 0,#0759cc 330px);color:#fff;padding:24px 18px;font-family:Arial,"PingFang SC",sans-serif;}
.vl-ocean h2{font-size:34px;line-height:1.08;margin:0;text-shadow:0 0 7px #8ce8ff;font-weight:900;}
.vl-ocean__planet{min-height:175px;display:grid;place-items:center;color:#b2efff;object-fit:contain;width:100%;}
.vl-ocean__panel{background:#fff;color:#26a4d9;border:4px solid #a6edff;border-radius:25px;padding:16px;margin:18px 0;box-shadow:0 0 18px #19c7ff66;font-size:25px;font-weight:800;}
.vl-ocean__rail{display:flex;gap:10px;overflow:auto;padding:8px 0 22px;}.vl-ocean__rail>*{flex:0 0 44%;min-height:125px;background:#198fd2;border-radius:8px;padding:8px;font-size:12px;}
.vl-ocean__place{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:18px;background:#e8fa56;color:#141719;border-radius:18px;margin-top:6px;font-size:14px;}.vl-ocean__place:nth-of-type(2){background:#bba3f1;}.vl-ocean__place:nth-of-type(3){background:#4beaac;}.vl-ocean__place strong{font-size:22px;}
```

```html
<article class="vl-ocean"><h2>一起探索<br>海洋影像</h2><div class="vl-ocean__planet" data-slot="orbit">星球与轨道素材</div><section class="vl-ocean__panel">创作者与影像相遇</section><div class="vl-ocean__rail"><div data-slot="creator-photo">作者图卡 A</div><div data-slot="creator-photo">作者图卡 B</div></div><section><div class="vl-ocean__place"><strong>地点 A</strong><span>日期<br>活动地址</span></div><div class="vl-ocean__place"><strong>地点 B</strong><span>日期<br>活动地址</span></div><div class="vl-ocean__place"><strong>地点 C</strong><span>日期<br>活动地址</span></div></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.theatre-collage-guide"></a>

## 舞台剪贴与图解导览

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 浅灰编辑底，蓝帷幕仅开场上沿，黄色信息板是局部。 |
| 图片／装饰素材 | 剧场人物剪影与帷幕构成主场；海报卡和操作截图各自绑定图注。 |
| 文字归属与阅读顺序 | 蓝色巨字居主场，黄色英文底条附属；导览步骤标题与路径线成组。 |
| 页面／容器／素材安全区 | 避开帷幕褶皱与人物头部；黄板扣内距；箭头沿截图之间净空走，不穿说明。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 900 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Arial 700用于黄色底条，步骤数字400 |

匹配依据与边界：蓝色粗黑是字形主体；涂鸦线属于装饰，不要求中文整体手写。


风格标签：二级：趣味创意风 / 清新轻艺术。

剧场帷幕、报纸舞台、手绘标题标记与截图导览组合成轻艺术活动页；纸纹只在舞台/衬纸，不全页继承。

复用 [导览流](../layouts/continuous-flow.md#layout.route-flow)、[照片衬纸](../shapes/notes-and-paper.md#shape.paper-mount)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 暖灰#dededb约55%、蓝#4088ed约20%、淡黄#fafb9f约20%，正文近黑 |
| 字体 | 主标题蓝色粗黑体42px，英文黄色底条16px；章节题24px/700，操作说明13px |
| 首屏 | 帷幕压顶部，报纸质感舞台做背景，人物剪影贴舞台底部；标题独立前景 |
| 图文关系 | 精选剧目横卡左海报右文字；步骤卡内截图成对，箭头连接动作与结果，不横穿说明 |
| 卡片与渐变 | 浅黄圆角卡薄橄榄边；背景基本纯色，舞台边缘按真实场景或载体轮廓收束，不默认叠灰白渐隐；蓝色手绘线为局部装饰 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-theatre{background:#dededb;color:#222;font-family:Arial,"PingFang SC",sans-serif;padding:20px 16px;}
.vl-theatre__stage{min-height:300px;position:relative;padding:50px 14px 20px;background:#eaeae7;isolation:isolate;}
.vl-theatre__curtain{position:absolute;inset:0 0 auto;height:60px;background:#244879;color:white;display:grid;place-items:center;z-index:-1;}
.vl-theatre h2{font-size:42px;line-height:1.08;color:#4088ed;margin:0;}.vl-theatre mark{background:#fafb9f;color:#3279d3;font-size:16px;}
.vl-theatre__audience{min-height:80px;display:grid;place-items:center;margin-top:30px;background:linear-gradient(transparent,#dededb);}
.vl-theatre h3{text-align:center;color:#4088ed;font-size:25px;}
.vl-theatre__card{border:1px solid #c5c761;border-radius:10px;padding:14px;background:#fafb9f;margin:12px 0;font-size:13px;line-height:1.6;}
.vl-theatre__shots{display:grid;grid-template-columns:1fr 24px 1fr;align-items:center;gap:4px;}.vl-theatre__shots div{min-height:92px;background:#fff;border:1px solid #76a4cb;border-radius:8px;padding:6px;}.vl-theatre__shots span{color:#4088ed;text-align:center;font-size:22px;}
```

```html
<article class="vl-theatre"><header class="vl-theatre__stage"><div class="vl-theatre__curtain" data-slot="curtain">帷幕素材</div><h2>好戏<br>就在这里</h2><mark>Theater Guide</mark><div class="vl-theatre__audience" data-slot="stage-audience">报纸舞台与观众素材</div></header><h3>看懂参与步骤</h3><section class="vl-theatre__card"><b>路径一 · 找到入口</b><p>先说明动作，再展示操作前后的界面。</p><div class="vl-theatre__shots"><div data-slot="screenshot-before">入口截图</div><span aria-hidden="true">→</span><div data-slot="screenshot-after">结果截图</div></div></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.clay-craft-office"></a>

## 手作事务所与活页说明卡

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 奶油连底、天空首屏、浅黄活页，绿地弧线是场景边界。 |
| 图片／装饰素材 | 黏土工具商店为首屏素材，铅笔／手作角色只在卡边穿插。 |
| 文字归属与阅读顺序 | 吊牌大题→场景→居中邀请文；活页正文清晰分组，动作在自己的纸面区。 |
| 页面／容器／素材安全区 | 吊牌避绳孔，活页扣线圈；道具可出纸边不可盖规则，页尾按钮保留完整。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 900 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 700 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Kodchasan 700／500，短英文约中文视觉高度1/3 |

匹配依据与边界：本地普惠体是较温和厚字替代，未精确覆盖参考圆润定制字；不以700加描边伪装黏土字。


风格标签：二级：趣味创意风 / 趣味拟物。

玩具化工具与手作场景组成首屏，纸本活页承担长文；体积感属于素材，卡片布局可复用。

复用 [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)、[活页／纸卡](../shapes/notes-and-paper.md#shape.paper-mount)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 奶油#faf6e7、浅黄#f4dfa0为底；草绿#88ba78、天空#d7edf2；棕#795c3c文字 |
| 字体 | 短粗圆标题30px/900；说明18px/700；正文13px/1.7；中英比例约3:1 |
| 图文关系 | 首屏吊牌标题→工具商店场景→草地弧底；说明卡文字居中，道具只越出卡片外缘 |
| 卡片 | 浅黄活页卡，左边孔/线圈，胶带色条；纸卡不能伪装成厚玻璃 |
| 纹理/渐变 | 纸底少量纤维可选；角色黏土质感保留图像；下部渐变仅小范围奶黄→纸白 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-craft{background:#faf6e7;color:#795c3c;font-family:Arial,"PingFang SC",sans-serif;padding:20px;}
.vl-craft__sign{border-radius:18px;background:#f4dfa0;text-align:center;padding:14px;font-size:30px;font-weight:900;box-shadow:0 3px 0 #d6bd80;}
.vl-craft__scene{min-height:210px;background:linear-gradient(#d7edf2 0 75%,#88ba78 75%);display:grid;place-items:center;margin:0 -20px 22px;width:calc(100% + 40px);object-fit:contain;}
.vl-craft__note{position:relative;border-radius:12px 22px 14px 12px;background:#f5e3a8;padding:24px 20px 24px 30px;font-size:13px;line-height:1.8;}
.vl-craft__note:before{content:"";position:absolute;left:8px;top:15px;bottom:15px;width:8px;background:radial-gradient(circle,#b08a59 3px,transparent 3.5px) 0 0/8px 24px;}
.vl-craft h3{background:#88ba78;color:#fff;padding:6px 12px;display:table;font-size:20px;transform:rotate(-2deg);margin:0 0 12px;}
.vl-craft__cta{display:table;margin:18px auto 0;border:0;border-radius:24px;padding:10px 22px;background:#efac77;color:#69492f;font-size:16px;}
```

```html
<article class="vl-craft"><header class="vl-craft__sign">手作事务所</header><div class="vl-craft__scene" data-slot="clay-workshop">工具与手作商店素材</div><section class="vl-craft__note"><h3>欢迎创作</h3><p>用清楚的短段落介绍活动。道具可以靠近纸边，但不覆盖说明文字。</p><p>参与条件和时间单独列出，保持阅读顺序。</p><button class="vl-craft__cta">查看参与方式</button></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.clay-parenting-collage"></a>

## 育儿玩具与照片拼贴活动

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 蓝色章带与白格底相接，网格归背景，照片内不加网格。 |
| 图片／装饰素材 | 大角色首屏，白边亲子照片成组，玩具出现在边角；不是所有段落都需卡壳。 |
| 文字归属与阅读顺序 | 蓝绿主标题及章节题，照片配邻近短图注，奖励区为独立文字层级。 |
| 页面／容器／素材安全区 | 照片白边内扣裁切安全区；人物脸／手与玩具保护；长图注改开放图文流，不能硬塞两列。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 900 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 700 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Kodchasan 700用于玩具感英文，日期500 |

匹配依据与边界：厚实端正字作可编辑近似；真正鼓胀圆体尚有差异，不给正文套字面浮雕。


风格标签：二级：趣味创意风 / 趣味拟物。

与手作事务所共享玩具素材语言，但白格底照片拼贴和蓝色章节分隔不同，独立保存组合。

复用 [拼贴布局](../layouts/overlap-and-collage.md#layout.collage)、[照片衬纸](../shapes/notes-and-paper.md#shape.paper-mount)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 蓝#4c91ff、白#fafbf8、绿#5dc479、奶黄#f7e0aa；约蓝白各40% |
| 文字 | 主标题蓝绿交替，圆体34px/900；章节蓝绿26px；正文蓝灰13px，避免多种装饰字体混排 |
| 图文关系 | 大角色首屏约40%；照片按实际比较关系与阅读尺寸排列；原例两列仅适合短图注，长说明用开放图文流；玩具只占边缘空白，奖励以文字层级归组 |
| 卡片 | 白底细浅灰网格28px，照片白边6px；确需照片载体时可用圆角16px与蓝边，默认无外投影；白格纹不要求额外卡片 |
| 渐变与质感 | 头尾明蓝线性渐变；角色材质为3D素材，不对照片加浮雕；网格只在白底 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-parenting{background:#fafbf8;color:#50728e;font-family:Arial,"PingFang SC",sans-serif;}
.vl-parenting__hero{padding:24px 20px;background:linear-gradient(#c6e3ff,#4c91ff);border-radius:0 0 45% 5%;}
.vl-parenting h2{font-size:34px;font-weight:900;line-height:1.12;margin:0;color:#428bdf;}.vl-parenting h2 em{font-style:normal;color:#5dc479;}
.vl-parenting__figure{min-height:210px;display:grid;place-items:center;object-fit:contain;width:100%;}
.vl-parenting__body{padding:24px 20px;background-image:linear-gradient(#dfe5e455 1px,transparent 1px),linear-gradient(90deg,#dfe5e455 1px,transparent 1px);background-size:28px 28px;}
.vl-parenting h3{font-size:26px;color:#4c91ff;text-align:center;}.vl-parenting__photos{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start;}
.vl-parenting__photos figure{margin:0;background:white;padding:6px;border-radius:9px;box-shadow:none;transform:rotate(-3deg);}.vl-parenting__photos figure:nth-child(even){transform:rotate(3deg);margin-top:18px;}.vl-parenting__photos [data-slot]{min-height:115px;background:#dfeaf0;display:grid;place-items:center;}.vl-parenting figcaption{font-size:12px;padding:8px 0;}
.vl-parenting__reward{margin-top:26px;padding:20px;background:#fff;border:3px solid #c6e3ff;border-radius:20px;font-size:14px;line-height:1.7;}
```

```html
<article class="vl-parenting"><header class="vl-parenting__hero"><h2>成长<em>好时光</em></h2><div class="vl-parenting__figure" data-slot="clay-family">育儿玩具人物素材</div></header><section class="vl-parenting__body"><h3>记录日常</h3><div class="vl-parenting__photos"><figure><div data-slot="photo-one">照片 A</div><figcaption>照片下的简短说明</figcaption></figure><figure><div data-slot="photo-two">照片 B</div><figcaption>独立图注避免覆盖主体</figcaption></figure></div><div class="vl-parenting__reward">活动奖励、参与条件与领取方式分段填写。</div></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.personified-fashion-stage"></a>

## 拟物时装舞台与身份标签

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 天空→舞台／跑道→白色标签区，草地属于局部素材条。 |
| 图片／装饰素材 | 拟人门、路锥、道具为一组透视场景；斜便签与身份小物件后续独立。 |
| 文字归属与阅读顺序 | 白色首题在天空净空；规则跟随便签平面；每个身份标签文字与物件缩图关联。 |
| 页面／容器／素材安全区 | 舞台字不盖核心道具；斜便签扣可用内面；图标让开身份名称与动作入口。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Alibaba PuHuiTi 2.0 700 |
| 章节／卖点题 | Alibaba PuHuiTi 2.0 600 |
| 正文／注释 | Alibaba PuHuiTi 2.0 400 |
| 英文／数字 | Baskerville 400 italic用于短时装副题；标签数字沿正文 |

匹配依据与边界：主场是清爽白色黑体，时装感英文只是辅助，不让它反向控制中文。


风格标签：二级：趣味创意风 / 趣味拟物。

拟人路锥、舞台门和草地候场区组成日常物件时装秀，下方身份标签采用规整可读的彩色网格。

复用 [拼贴](../layouts/overlap-and-collage.md#layout.collage)、[卡列](../layouts/grid-and-alignment.md#layout.card-rail)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 白与天空蓝#95d9f2为大底；红#e54738集中舞台；绿紫粉标签点缀，不全页堆叠高饱和 |
| 文字 | 首屏白色粗体32px；步骤标题蓝#238ab8/24px，粉色英文作为短注；正文13px |
| 主视觉 | 门/帷幕/路锥/跑道是一组透视素材；CSS文字只贴在独立安全区，不能逐字伪透视 |
| 图文关系 | 主场→倾斜规则便签→身份标签网格→内容卡；标签一块一身份并带物件缩图槽 |
| 卡片与纹理 | 横线纸作为局部笔记载体，默认无投影；约-3°倾斜仅用于已选拼贴关系，标签轮廓按内容，草地纹理仅素材 strip |
| 渐变 | 天空蓝→白；跑道阴影与舞台光由素材负责，白底标签区不发光 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-fashion{background:white;color:#1c1d1e;font-family:Arial,"PingFang SC",sans-serif;padding:0 18px 25px;}
.vl-fashion__hero{padding:25px 15px 0;margin:0 -18px;background:linear-gradient(#95d9f2,#ecf8f9);text-align:center;}.vl-fashion h2{font-size:32px;color:white;margin:0 0 16px;}
.vl-fashion__runway{min-height:250px;background:linear-gradient(100deg,#bfc1bf,#eeede9);display:grid;place-items:center;width:100%;object-fit:contain;}
.vl-fashion__note{margin:25px 8px;padding:22px 16px;font-size:14px;line-height:1.8;background:repeating-linear-gradient(#fff 0 25px,#dce2e2 25px 26px);box-shadow:none;transform:rotate(-3deg);}
.vl-fashion h3{font-size:24px;color:#238ab8;}.vl-fashion h3 small{color:#de87b1;font-size:16px;}
.vl-fashion__tags{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}.vl-fashion__tags>div{padding:16px 12px;min-height:65px;border-radius:18px 4px;background:#dfdfb7;font-size:16px;font-weight:700;}.vl-fashion__tags>div:nth-child(2){background:#067f63;color:white;}.vl-fashion__tags>div:nth-child(3){background:#b6ddf1;color:#254567;}.vl-fashion__tags>div:nth-child(4){background:#f2bad2;}
```

```html
<article class="vl-fashion"><header class="vl-fashion__hero"><h2>生活时装秀</h2><div class="vl-fashion__runway" data-slot="runway">拟人物件与透视舞台素材</div></header><section class="vl-fashion__note">先介绍入场方式，再展示身份选择。<br>纸卡上的正文独立清晰。</section><h3>选择你的身份 <small>Step 01</small></h3><div class="vl-fashion__tags"><div>日常观察家</div><div>自然同行者</div><div>城市漫游者</div><div>色彩收藏家</div></div></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.pop-campaign-ranking"></a>

## 波普活动排行与人像矩阵

**产物适用标签**：产物：社媒长图；适配产物：详情页单屏；粒度：长页组合。详情页单屏只借局部关系，不移植整条活动规则或长图流程。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 浅灰共同底，黄排行板与红边白规则板局部分组。 |
| 图片／装饰素材 | 首屏沿基底奖杯／拍板；人像卡三列，任务小物件在所属卡内。 |
| 文字归属与阅读顺序 | 蓝斜章节号与黑标题同行；左名次右奖励，姓名在头像下条，不遮脸。 |
| 页面／容器／素材安全区 | 名次列容纳Top 1／10／100完整语义；规则板扣红边；头像护脸，长姓名增高底条。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | JiangChengLvDongHei 700（首屏沿基底，许可待核） |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Arial 400 italic章节号；Top与数字Arial 400同组 |

匹配依据与边界：首屏手作展示字与正文黑体分开；得意黑不承担所有章节或排行标签。


风格标签：二级：波普撞色风 / 波普拼贴。

在现有红黄蓝拼贴基础上补充排行、章节号与人像矩阵的结构变体；不重复收录原奖杯拼贴首屏。

基底：[复古高饱和拼贴](recipes.md#combination.retro-pop-collage)。首屏仍引用基底；本变体只规定新的信息区。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 沿用红黄蓝纸本配色；浅灰#f0f0ee底，黄#ffe72c排行板、红#ff294d外围、蓝#287fda标题号 |
| 文字 | 章节号蓝色斜体30px，章节题黑粗体22px；手写主标题来自真实字形，正文12–14px |
| 排行 | 左窄列名次右宽列说明；Top数字可装饰，但正文奖励数字必须来自brief |
| 人像 | 3列头像卡，红黄蓝循环；裁切优先人脸，姓名和标签置独立底条，不遮脸 |
| 纹理/渐变 | 原纸底可轻纹，新增列表以纯色为主；不要自动加霓虹/玻璃 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-pop-rank{padding:24px 18px;background:#f0f0ee;color:#171717;font-family:Arial,"PingFang SC",sans-serif;}
.vl-pop-rank__tabs{display:flex;gap:4px;margin:12px 0;}.vl-pop-rank__tabs span{flex:1;padding:10px 4px;text-align:center;background:#ddd;border-radius:9px 9px 0 0;font-size:12px;}.vl-pop-rank__tabs span:first-child{background:#ff294d;color:white;}.vl-pop-rank__rules{border:7px solid #ff294d;background:white;padding:14px;font-size:13px;line-height:1.7;box-shadow:5px 5px 0 #ffe72c;}.vl-pop-rank__tasks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;background:#ffe72c;padding:12px;}.vl-pop-rank__tasks div{background:white;border-radius:8px;padding:15px 6px;font-size:12px;text-align:center;}
.vl-pop-rank h3{font-size:23px;line-height:1.2;display:flex;align-items:baseline;gap:8px;}.vl-pop-rank h3 i{font-size:32px;font-weight:400;color:#287fda;}
.vl-pop-rank__list{padding:14px;background:#ffe72c;transform:rotate(1deg);}.vl-pop-rank__row{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:12px;align-items:center;margin:8px 0;}.vl-pop-rank__row>b{color:#ff294d;font-size:24px;font-weight:500;white-space:nowrap;}.vl-pop-rank__row>p{background:white;border-radius:7px;padding:12px;margin:0;font-size:13px;}
.vl-pop-rank__people{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;}.vl-pop-rank__people>figure{margin:0;padding:6px;border-radius:9px;background:#287fda;color:#fff;}.vl-pop-rank__people>figure:nth-child(3n+2){background:#ff294d;}.vl-pop-rank__people>figure:nth-child(3n){background:#ffe72c;color:#171717;}.vl-pop-rank__photo{aspect-ratio:3/4;object-fit:cover;width:100%;border-radius:6px;background:#fff8;display:grid;place-items:center;font-size:12px;}.vl-pop-rank figcaption{padding:7px 0;font-size:12px;}
```

```html
<section class="vl-pop-rank"><h3><i>02</i>参与方式</h3><div class="vl-pop-rank__tabs"><span>开始阶段</span><span>展示阶段</span><span>结果阶段</span></div><div class="vl-pop-rank__rules">活动要求与内容方向分段填写。页签仅示范静态视觉，交互逻辑需要业务实现。</div><h3><i>03</i>活动激励</h3><div class="vl-pop-rank__list"><div class="vl-pop-rank__row"><b>Top 1</b><p>对应名次的真实奖励说明</p></div><div class="vl-pop-rank__row"><b>Top 2</b><p>对应名次的真实奖励说明</p></div></div><h3><i>04</i>创作者展示</h3><div class="vl-pop-rank__people"><figure><div class="vl-pop-rank__photo" data-slot="portrait">人像素材</div><figcaption>创作者 A</figcaption></figure><figure><div class="vl-pop-rank__photo" data-slot="portrait">人像素材</div><figcaption>创作者 B</figcaption></figure><figure><div class="vl-pop-rank__photo" data-slot="portrait">人像素材</div><figcaption>创作者 C</figcaption></figure></div><h3><i>05</i>互动任务</h3><div class="vl-pop-rank__tasks"><div>任务一<br>素材槽</div><div>任务二<br>素材槽</div><div>任务三<br>素材槽</div></div></section>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

补充规则阶段页签、红边白纸面板和三列任务卡。交互不是CSS提取的一部分，静态示例不可宣称报名或抽奖功能可用；首屏仍复用基底。

<a id="combination.clinical-cyan-evidence"></a>

## 净白青蓝功效说明

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 净白整底，浅青局部过渡；证据面保持白／灰，无通用纸纹。 |
| 图片／装饰素材 | 首瓶中右，凝胶与泡沫在机理段；皮肤前后对照并列，底部产品承接结语。 |
| 文字归属与阅读顺序 | 左右错落短句、青色关键词与轻大数字；图注靠证据，比例／单位语义完整。 |
| 页面／容器／素材安全区 | 保护瓶标、检测图局部与对照条件；图框扣图注空间；泡沫mask不覆盖字。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 500 |
| 章节／卖点题 | Source Han Sans 500 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Source Han Sans 300用于大比例；小英文／单位400 |

匹配依据与边界：轻中等无衬线接近原图，不能用900展示黑或运动斜字统一替换。


风格标签：二级：理性信息风 / 数据图解。

以白底错位标题、成分比例、过程图解和对比证据构成理性说明，不因商品用途称作商务。

复用 [净白青蓝](../colors/calm-and-rational.md#palette.clinical-cyan)、[错位标题](../layouts/asymmetric-balance.md#layout.staggered-title)、[证据网格](../layouts/grid-and-alignment.md#layout.evidence-grid)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 复用净白青蓝，白#f6f7f5约80%，青#20bbc5约12%，黑#171717与浅灰注释 |
| 字体 | 中文无衬线主标题30px/500，关键词青色；大数字36px/300，正文12px/1.65；小英文10px/灰 |
| 文字布局 | 左右错位短句分段，单段最多两处关键词强调；数字和单位分开但不拆散语义 |
| 图文 | 瓶身首屏居中偏右，说明靠左；成分比率图横向对齐；前后证据图2列有独立图注 |
| 材质 | 卡片白/浅灰，无通用纸纹；泡沫凝胶油滴与皮肤质感在图像素材中 |
| 渐变 | 局部浅青→白，漂浮产品底白雾作图片mask，文字不受mask影响；不要复制图中疗效与检测值 |

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-clinical{padding:24px 20px;background:#f6f7f5;color:#171717;font-family:Arial,"PingFang SC",sans-serif;}
.vl-clinical h2{font-size:30px;font-weight:500;line-height:1.15;letter-spacing:-1px;margin:12px 0;}.vl-clinical em{font-style:normal;color:#20bbc5;}
.vl-clinical__hero{position:relative;min-height:300px;background:radial-gradient(ellipse at 70% 65%,#ceeceb,transparent 65%);}.vl-clinical__product{width:75%;min-height:195px;margin-left:25%;object-fit:contain;display:grid;place-items:center;color:#398e96;}
.vl-clinical__section{padding:24px 0;border-top:1px solid #e1e4e2;}.vl-clinical__section:nth-of-type(even) h2{text-align:right;}
.vl-clinical__ratio{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:center;margin:18px 0;}.vl-clinical__ratio>div:first-child{height:75px;background:linear-gradient(135deg,#e1f1ee,#fff);border-radius:20px 6px;display:grid;place-items:center;}.vl-clinical__ratio strong{font-size:32px;font-weight:400;color:#20bbc5;}.vl-clinical p{font-size:12px;line-height:1.65;}
.vl-clinical__evidence{display:grid;grid-template-columns:1fr 1fr;gap:8px;}.vl-clinical__evidence figure{margin:0;background:white;}.vl-clinical__evidence [data-slot]{min-height:85px;background:#dde8e8;display:grid;place-items:center;font-size:12px;}.vl-clinical figcaption{padding:8px;font-size:12px;background:#171717;color:#fff;}
```

```html
<article class="vl-clinical"><header class="vl-clinical__hero"><h2>成分说明<br>从<em>清晰信息</em>开始</h2><div class="vl-clinical__product" data-slot="product">产品瓶身素材</div></header><section class="vl-clinical__section"><h2>配方结构<br><em>逐项解释</em></h2><div class="vl-clinical__ratio"><div data-slot="ingredient">成分图像</div><div><strong>比例</strong><p>填写经过核实的成分与单位。</p></div></div></section><section class="vl-clinical__section"><h2>对比条件<br><em>清楚标注</em></h2><div class="vl-clinical__evidence"><figure><div data-slot="evidence-before">证据图 A</div><figcaption>条件与时间</figcaption></figure><figure><div data-slot="evidence-after">证据图 B</div><figcaption>条件与时间</figcaption></figure></div></section></article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

<a id="combination.black-orange-product-stage"></a>

## 黑橙光场与产品功能矩阵

**产物适用标签**：产物：详情页长图；适配产物：详情页单屏；适配产物：社媒长图；粒度：长页组合。单屏只取完整语义段，另定画幅与安全区；社媒使用需重新组织阅读节奏。标签用于检索，不覆盖 Brief 已锁定的产物。

### 关系与字体复核

| 对象 | 本组合约定 |
|---|---|
| 背景／卡面 | 黑整底与低位橙色光场，黑灰功能卡另有轻微表面差。 |
| 图片／装饰素材 | 首屏为通栏完整场景，3/4产品偏中右是场景内部构图，不是独立右列图片。产品、地面、接触阴影和橙色光场保持同一坐标；卡内细节图与剖面铺到卡边，左剖面可跨行；网布质感属于素材。 |
| 文字归属与阅读顺序 | 标题、副题、价格和标识叠在首屏场景的真实留白区，文字边距只约束文字、不使场景内缩。功能题与完整说明在卡顶部，橙色参数分别对应续航和防护注释；不能删去单位、限定语和关键技术说明来简化样例。 |
| 页面／容器／素材安全区 | 扣功能卡内距；产品不得顶入标题，保护腔体及端口；光场不让正文对比消失。 |

字体按 [核验状态与绑定约定](#combination-font-binding) 使用，以下为最贴近的本地候选及已知差异：

| 角色 | 精确 family 与字重 |
|---|---|
| 主标题 | Source Han Sans 700 |
| 章节／卖点题 | Source Han Sans 700 |
| 正文／注释 | Source Han Sans 400 |
| 英文／数字 | Source Han Sans 500用于参数，400用于单位；拉丁沿同家族 |

匹配依据与边界：直立现代黑体贴近产品信息表达；不把橙色和科技题材自动映射到得意黑。


风格标签：二级：未来科技风 / 产品科技。

大幅真实产品渲染、受控橙色地平线光与规整功能矩阵共同表达产品科技；与银色工业面板不同。

复用 [主图聚焦](../layouts/hero-focus.md#layout.image-stage)、[证据网格](../layouts/grid-and-alignment.md#layout.evidence-grid)、[弥散光场](../surfaces/diffuse-light.md#surface.diffuse-field)。

| 对象 | 参数与图文规则 |
|---|---|
| 配色 | 近黑#050505/#151515约85%，橙#ff6500局部，标题#fff、正文#b7b7b7；不另建只换色的palette |
| 文字 | 主标题32px/700，功能题21px/700，说明13px/1.5；关键参数橙色36px，单位有独立基线 |
| 主场 | 通栏完整场景内的倾斜3/4产品置中右，左上为文字净空；场景不受文字padding影响，不拆成标题栏＋右侧矩形产品裁片。保留原场景比例、光向、地面与投影 |
| 矩阵 | 双列功能卡，左侧结构剖面可跨两行；卡内文字顶部、产品图底部，功能图不顶住正文 |
| 质感 | 网布/金属/腔体高光来自真实素材；卡片仅黑灰微渐变和1px边，不加统一噪点 |
| 光照渐变 | 首屏橙色低位椭圆光与细弧线分层；顶部保持黑；深色功能卡不重复大光晕 |


### 原图对照的关键约束

- 本参考首屏约为2160×1624的通栏场景（比例为本例观察值），图片铺满首屏；左右安全边距作用于标题、价格等文字层。只有参考明确为图文分栏时才拆列，不能由“产品偏右”推断两列。
- 下方卡片的文字有内边距，摄影可铺满卡宽并抵达底边；不能将二者套入同一padding。原例保留双列、左侧剖面跨行、右侧组合图／参数／连接信息的不同段高，不改成等高卡。
- 校对细节清单：主副题、价格及限定语、品牌／奖项标识、功能题及副说明、高低音单元说明、低音模式、调音标识、续航／防护各自图注和连接方式。仅在本次资料确实提供时沿用，不把参考参数当其他商品事实。
- 没有无字场景源时，内部测试可复用授权参考的摄影区域并明确保留的图内字；不能用整页截图代替组装，也不能把局部黑底遮挡原字后留下的矩形块当成融合完成。摄影边界、文字编辑边界分别记录。
- 验收除越界外，还要比较场景宽度／段高、产品视觉占比、文字安全区、功能图占卡比例与细节清单。任一核心场景关系丢失均判该段失败，不能以“几何无溢出”降为通过。

以下是可复制的结构骨架。标注“素材”的节点是图片槽，不是已经提取出的产品／人物；接入真实 img 时沿用同名 class，设置 width/height 与 object-fit，并提供准确 alt。尺寸以约375px阅读宽度为起点，扩画布应同时调整字级、间距和素材尺寸，不能只放大图片。示例文案均为中性占位。

```css
.vl-speaker{container-type:inline-size;background:#151515;color:white;font-family:"Source Han Sans",sans-serif;padding:0 0 20px;}
.vl-speaker__hero{position:relative;isolation:isolate;aspect-ratio:var(--vl-speaker-hero-ratio,2160/1624);padding:0;overflow:hidden;background:#030303;}
.vl-speaker__scene{position:absolute;inset:0;width:100%;height:100%;z-index:0;}
.vl-speaker__scene>img{display:block;width:100%;height:100%;object-fit:cover;object-position:center;}
.vl-speaker__hero-copy{position:absolute;left:6.1%;top:9%;right:12%;z-index:1;}
.vl-speaker__hero h2{font-size:8.5333cqw;font-weight:700;line-height:1.2;margin:0 0 1.5cqw;}
.vl-speaker p{font-size:3.4667cqw;font-weight:400;line-height:1.5;color:#b7b7b7;margin:0;}
.vl-speaker__price{position:relative;margin-top:1.5cqw;font-size:5cqw;font-weight:500;line-height:1.2;color:#ddb968;z-index:1;}
.vl-speaker__brand{position:absolute;right:4%;top:5%;width:8%;z-index:1;}
.vl-speaker__awards{position:absolute;left:8%;bottom:12%;max-width:22%;z-index:1;}
.vl-speaker__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.55cqw;margin:3.2cqw;}
.vl-speaker__card{background:linear-gradient(#030303,#111);border:1px solid #242424;border-radius:2cqw;padding:0;overflow:hidden;display:flex;flex-direction:column;min-width:0;}
.vl-speaker__copy{padding:3cqw 3cqw 2cqw;}
.vl-speaker h3{font-size:5.6cqw;font-weight:700;line-height:1.3;margin:0 0 1.5cqw;}
.vl-speaker__image{width:100%;margin-top:auto;aspect-ratio:var(--vl-speaker-image-ratio,1.5);}
.vl-speaker__image>img{display:block;width:100%;height:100%;object-fit:cover;}
.vl-speaker__card--tall{grid-row:span 3;}.vl-speaker__card--tall .vl-speaker__image{aspect-ratio:1.15;}
.vl-speaker__specs{display:grid;grid-template-columns:1fr 1fr;gap:1cqw;text-align:center;padding:3cqw 1cqw;}
.vl-speaker__spec{font-size:9.6cqw;font-weight:500;color:#ff7b28;display:block;}
.vl-speaker__connections{display:flex;justify-content:space-around;gap:1cqw;padding:2cqw 1cqw;color:#d58a43;font-size:1.8cqw;}
```

```html
<article class="vl-speaker">
  <header class="vl-speaker__hero">
    <div class="vl-speaker__scene" data-slot="full-bleed-hero-scene"><!-- 同比例的完整无字场景img：产品、光场、地面、投影共用同一资产；不是右侧产品裁片 --></div>
    <div class="vl-speaker__hero-copy"><h2>产品主标题</h2><p>准确副标题</p>
    <div class="vl-speaker__price" data-slot="verified-price">真实价格及限定语</div></div>
    <div class="vl-speaker__brand" data-slot="brand-mark"></div>
    <div class="vl-speaker__awards" data-slot="verified-awards"></div>
  </header>
  <section class="vl-speaker__grid">
    <div class="vl-speaker__card"><div class="vl-speaker__copy"><h3>外观设计</h3><p>完整功能说明</p></div><div class="vl-speaker__image" data-slot="detail"></div></div>
    <div class="vl-speaker__card"><div class="vl-speaker__copy"><h3>光效展示</h3><p>完整光效说明</p></div><div class="vl-speaker__image" data-slot="lighting"></div></div>
    <div class="vl-speaker__card vl-speaker__card--tall"><div class="vl-speaker__copy"><h3>音效与内部结构</h3><p>高低音单元、模式说明与调音标识按资料分别排版，不删成一句短注。</p></div><div class="vl-speaker__image" data-slot="cutaway"></div></div>
    <div class="vl-speaker__card"><div class="vl-speaker__copy"><h3>组合使用</h3><p>准确的组合与串联条件</p></div><div class="vl-speaker__image" data-slot="pair"></div></div>
    <div class="vl-speaker__card vl-speaker__specs"><div><span class="vl-speaker__spec">续航</span><p>真实数值及条件</p></div><div><span class="vl-speaker__spec">防护</span><p>真实等级及条件</p></div></div>
    <div class="vl-speaker__card vl-speaker__connections" data-slot="verified-connections">按实际接口逐项填充</div>
  </section>
</article>
```

正文不要继承装饰的 blur、opacity、mix-blend-mode。主视觉素材的轮廓、内部光照与纹理不由卡片CSS生成；素材未齐时必须显式记录缺项，不能把本骨架宣称为参考图完整复刻。

本骨架的首屏槽位必须绑定完整就绪场景，空槽不算渲染验证。图内已有品牌、奖项或文字时，先明确复用／拆分边界，避免在同一位置重复覆字。卡片图像比例及分区高度按本次实际资产和文案调整；上述跨行数对应本例右侧三组信息，不是所有产品的固定规则。

<a id="combination.menu-kraft-doodle"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 牛皮纸手绘菜品拼贴菜单

**产物适用**：菜单单页竖版。社媒长图／详情页单屏只能借用局部关系，必须重新分配信息密度，不自动串联菜单面。

### 背景、图文关系与安全区

**参考画幅**：710×948，仅为设计比例，不等于印刷毫米尺寸。

整张纸底上的六盘开放拼贴；图注位于各盘邻侧净空，盘圈与涂鸦单独描绘。左上吉祥物是独立纸贴纸，保留浅色异形边，不用通用矢量涂鸦替代；品牌字标另设素材槽。英文Otter靠右、中文大标题跨上部。没有价格证据，不加价格。

背景或异形色卡 → 独立菜品与装饰素材 → 标题、菜名、译名和价格为分层关系；所有文字绑定其所属菜品或分类。背景纹理不能影响正文透明度，照片内原有文字必须清除或排除，不再重复叠写。页面外围至少2%留白；图注与图片可见轮廓至少4–8px；图注和价格保留6px间隔；标签完全落在所属图片或卡片安全区。文字变化时重排邻接对象，不靠缩小字号或裁切掩盖溢出。

### 配方字体与质感

中文标题 Feibo Zheng Dots 400（飞波正点体V2.1，当前四字已整图核验）；品牌使用独立字标资产，禁止缺字回退混排；拉丁标题 Brush Script MT 400；中文图注 Source Han Sans SC 400，英文图注 Chalkboard 400（常规手写字款，不使用伪斜）；不使用得意黑。

以上为本地实际可用候选及字重，不声称识别出原作者字体。先按目标环境核实字体文件、真实字款、中文覆盖与使用许可；不以字体名称相同或400参数相同代替整图视觉验证。字体选择必须连同配色、描边、背景和图文关系一起渲染。纸纹使用独立低对比噪声/纤维层；复杂真实纸纤维与产品摄影属于素材能力，不把规则点阵或裁片背景当成等价实现。

### CSS 组合实现

下面为已实渲染关系的维护源。生产按目标HTML行内化协议处理；文案是参考排版样例，营业事实由Brief绑定，不能沿用演示价格。照片已替换为独立资产槽，不携带原图、局部截图或本机路径。每槽绑定对应菜品，保留素材原比例；参考裁片的临时遮罩不带入生产。正文内联坐标为相对所属画布百分比，cqw字号随画布缩放。缩到手机宽度不代表可读性通过。

```css
.vl-menu-kraft-doodle .panel{position:relative;container-type:inline-size;width:100%;overflow:hidden;font-synthesis:none}.vl-menu-kraft-doodle .n{position:absolute;box-sizing:border-box}.vl-menu-kraft-doodle .text{white-space:pre-wrap;line-height:1.16;overflow-wrap:normal;margin:0}.vl-menu-kraft-doodle .photo{overflow:hidden}.vl-menu-kraft-doodle .break{height:18px;background:#dfdbd2}
```

```html
<section class="vl-menu-kraft-doodle"><main class="panel" data-width="710" data-height="948" style="aspect-ratio:710/948;background:#E4C992"><svg class="n" width="100%" height="100%" style="opacity:0.15;pointer-events:none"><filter id="noise0"><feTurbulence type="fractalNoise" baseFrequency=".67 .19" numOctaves="3" seed="9"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#noise0)"/></svg><div class="n shape" data-node="0:0" style="left:2.112676056338028%;top:2.0042194092827006%;width:95.77464788732394%;height:95.78059071729957%;background:radial-gradient(ellipse at 37% 24%, #F0DDA755 0%, #E4C99200 68%, #BE975E16 100%);border-radius:0;border:none;"></div><div class="n photo" style="left:14.084507042253522%;top:2.109704641350211%;width:17.74647887323944%;height:13.0897583429229%;filter:drop-shadow(0 .15cqw .12cqw #74583b28);border-radius:0.0cqw;"><img data-asset-slot="mascot_sticker" src="{{mascot_sticker_url}}" alt="透明底异形纸贴纸；保留原浅色轮廓和蓝色线稿，不重画成涂鸦" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n shape" data-node="0:2" style="left:0.0%;top:0.0%;width:0.0%;height:0.0%;background:transparent;border-radius:0;border:none;"></div><div class="n photo" style="left:14.366197183098592%;top:15.928270042194093%;width:18.591549295774648%;height:4.606452840963167%;border-radius:0.0cqw;"><img data-asset-slot="brand_wordmark" src="{{brand_wordmark_url}}" alt="已核对品牌文字的独立字标，不能缺字回退混排" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-node="0:4" style="left:34.78873239436619%;top:2.6371308016877637%;width:51.40845070422535%;height:17.932489451476794%;font-family:&quot;Brush Script MT&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:19.577464788732392cqw;color:#593827;text-align:right;">Otter</div><div class="n text" data-node="0:5" style="left:11.830985915492958%;top:20.35864978902954%;width:71.83098591549296%;height:12.974683544303797%;font-family:&quot;Feibo Zheng Dots&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:13.802816901408452cqw;color:#593827;text-align:center;">咖喱满堂</div><div class="n path" data-node="0:6" style="left:74.22535211267606%;top:14.662447257383967%;width:9.43661971830986%;height:10.970464135021098%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M16 35 C6 35 8 29 14 28 C11 20 18 20 21 26 C27 20 34 26 27 32 C34 36 29 43 23 38 C24 47 17 48 16 39 Z M67 11 L74 1 L79 11 L91 12 L82 20 L83 32 L74 26 L63 31 L66 20 L57 16 Z M70 30 L64 42 M76 31 L70 45 M23 43 L20 58 M13 46 L16 57 M21 66 L29 87 L38 61 M33 91 L63 65 M28 91 L48 48 M18 85 L9 67" fill="none" stroke="#60422D" stroke-width="3" stroke-linecap="round"/></svg></div><div class="n photo" style="left:61.267605633802816%;top:32.80590717299578%;width:29.577464788732392%;height:16.350210970464136%;border-radius:0.0cqw;"><img data-asset-slot="dish_1" src="{{dish_1_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:8" style="left:60.4225352112676%;top:32.80590717299578%;width:31.12676056338028%;height:16.877637130801688%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M20 16 C-2 32 -1 60 13 79 C31 103 68 105 89 79 M9 31 C-4 58 8 87 37 96" fill="none" stroke="#658EA5" stroke-width="1.25" stroke-linecap="round"/></svg></div><div class="n shape" data-node="0:9" style="left:47.74647887323943%;top:36.075949367088604%;width:8.732394366197182%;height:7.383966244725738%;transform:rotate(9deg);background:#EEDBB0;border-radius:48% 38% 53% 39% / 39% 45% 35% 51%;border:none;"></div><div class="n path" data-node="0:10" style="left:48.732394366197184%;top:36.81434599156118%;width:6.338028169014084%;height:5.274261603375527%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M21 8 Q31 -1 43 9 Q56 -2 66 9 Q88 8 95 27 Q100 48 82 52 L61 45 Q46 44 40 58 Q61 54 62 70 Q59 84 42 75 Q41 100 26 94 Q28 79 15 75 Q-1 64 5 42 Q5 17 21 8 Z M73 24 L76 28 M35 66 Q22 54 16 64" fill="none" stroke="#658EA5" stroke-width="3" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:11" style="left:10.704225352112676%;top:38.81856540084388%;width:32.53521126760563%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.2535211267605635cqw;color:#5C89A3;text-align:left;">◦ 一道汤咖喱 &amp;BBQ慢烤鸡腿</div><div class="n text" data-node="0:12" style="left:13.521126760563378%;top:41.139240506329116%;width:26.056338028169012%;height:4.219409282700422%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">Asoup curry
BBQ Chicken Leg</div><div class="n photo" style="left:12.112676056338028%;top:45.9915611814346%;width:25.915492957746476%;height:14.873417721518987%;border-radius:0.0cqw;"><img data-asset-slot="dish_2" src="{{dish_2_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:14" style="left:11.126760563380282%;top:46.20253164556962%;width:27.74647887323944%;height:15.084388185654007%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M30 8 C8 13 -4 34 4 56 C15 89 65 107 87 89 C109 72 92 40 78 31 C70 25 61 20 50 18 M28 12 C6 19 1 42 11 63 C27 91 64 102 85 86" fill="none" stroke="#638DA5" stroke-width="1.3" stroke-linecap="round"/></svg></div><div class="n path" data-node="0:15" style="left:31.83098591549296%;top:44.303797468354425%;width:3.3802816901408446%;height:5.485232067510549%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M38 3 L9 0 L29 14 Q62 28 51 40 Q33 49 63 61 Q80 69 59 79 L92 99" fill="none" stroke="#654A31" stroke-width="5" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:16" style="left:43.239436619718305%;top:45.88607594936709%;width:17.183098591549296%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.2535211267605635cqw;color:#5C89A3;text-align:left;">◦ 葱油鲜虾拌面</div><div class="n text" data-node="0:17" style="left:44.929577464788736%;top:48.20675105485232%;width:28.450704225352112%;height:4.430379746835443%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">scallion oil
Shrimp mixed with noodles</div><div class="n photo" style="left:36.61971830985916%;top:55.379746835443036%;width:27.1830985915493%;height:14.767932489451477%;border-radius:0.0cqw;"><img data-asset-slot="dish_3" src="{{dish_3_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:19" style="left:35.774647887323944%;top:54.85232067510548%;width:28.87323943661972%;height:15.822784810126583%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M48 3 C75 -6 97 9 99 33 C104 61 83 87 55 96 C29 108 7 96 2 76 C-5 54 11 19 48 3 Z M10 45 C-3 75 17 98 43 96 C69 93 92 75 98 52" fill="none" stroke="#648EA6" stroke-width="1.2" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:20" style="left:67.88732394366197%;top:54.43037974683544%;width:25.915492957746476%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.2535211267605635cqw;color:#5C89A3;text-align:left;">◦ 一道汤咖喱&amp;炸猪排</div><div class="n text" data-node="0:21" style="left:69.57746478873239%;top:56.856540084388186%;width:16.19718309859155%;height:4.219409282700422%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">Asoup curry
Tonkatsu</div><div class="n path" data-node="0:22" style="left:85.35211267605634%;top:56.9620253164557%;width:6.901408450704226%;height:6.118143459915612%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M15 22 L0 0 L29 7 M5 6 C46 20 107 49 76 62 C62 68 9 37 24 42 C56 47 112 98 86 99 L45 92" fill="none" stroke="#61432C" stroke-width="4" stroke-linecap="round"/></svg></div><div class="n photo" style="left:62.95774647887325%;top:61.9198312236287%;width:27.042253521126757%;height:17.405063291139243%;border-radius:0.0cqw;"><img data-asset-slot="dish_4" src="{{dish_4_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:24" style="left:62.25352112676056%;top:61.60337552742617%;width:28.450704225352112%;height:18.354430379746837%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M45 8 L51 3 L57 5 L60 0 L71 4 C92 9 103 29 98 59 C96 84 76 100 52 98 C24 99 2 80 1 55 C-1 31 18 15 43 11 M39 12 C18 18 1 38 5 61 C10 86 33 96 56 95" fill="none" stroke="#638DA5" stroke-width="1.35" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:25" style="left:9.43661971830986%;top:66.03375527426161%;width:26.76056338028169%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.112676056338028cqw;color:#5C89A3;text-align:left;">◦ 印度咖喱黄油鸡(配薄饼)</div><div class="n text" data-node="0:26" style="left:10.985915492957748%;top:68.45991561181435%;width:25.774647887323944%;height:4.430379746835443%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">Butter Chicken Indian Curry
Paired with pancakes</div><div class="n path" data-node="0:27" style="left:7.323943661971831%;top:68.67088607594937%;width:4.647887323943662%;height:5.063291139240507%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M1 0 Q58 10 41 28 L33 40 L63 50 L56 67 L81 81 L67 92 L99 99" fill="none" stroke="#654A31" stroke-width="4" stroke-linecap="round"/></svg></div><div class="n photo" style="left:9.43661971830986%;top:74.47257383966245%;width:29.43661971830986%;height:14.978902953586498%;border-radius:0.0cqw;"><img data-asset-slot="dish_5" src="{{dish_5_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:29" style="left:8.591549295774648%;top:73.94514767932489%;width:30.985915492957744%;height:15.928270042194093%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M75 22 C55 4 31 -5 13 9 C-5 23 -2 51 14 73 C32 99 66 108 87 87 C96 79 99 67 98 59 C107 40 91 24 75 22 Z M9 20 C-3 43 10 72 35 87 C57 102 79 96 91 79" fill="none" stroke="#638DA5" stroke-width="1.2" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:30" style="left:37.605633802816904%;top:72.67932489451476%;width:23.098591549295776%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.2535211267605635cqw;color:#5C89A3;text-align:left;">◦ 川香辣奶油虾面</div><div class="n text" data-node="0:31" style="left:39.436619718309856%;top:75.10548523206751%;width:21.971830985915496%;height:4.430379746835443%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">Sichuan Spicy Cream
Shrimp Noodles</div><div class="n path" data-node="0:32" style="left:56.056338028169016%;top:68.88185654008439%;width:5.492957746478874%;height:5.590717299578059%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M0 24 L99 0 L9 48 L83 35 L25 76 L39 72 L20 97" fill="none" stroke="#654A31" stroke-width="4" stroke-linecap="round"/></svg></div><div class="n photo" style="left:37.605633802816904%;top:82.80590717299579%;width:29.718309859154928%;height:13.924050632911392%;border-radius:0.0cqw;"><img data-asset-slot="dish_6" src="{{dish_6_url}}" alt="本条菜品完整独立素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:34" style="left:36.76056338028169%;top:82.38396624472574%;width:30.985915492957744%;height:14.556962025316455%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M46 5 C69 -5 94 2 98 23 C107 49 88 78 65 91 C40 107 13 99 4 80 C-8 57 17 17 46 5 Z M8 49 C-4 78 20 98 42 96 C64 93 87 77 96 55" fill="none" stroke="#638DA5" stroke-width="1.3" stroke-linecap="round"/></svg></div><div class="n text" data-node="0:35" style="left:68.30985915492957%;top:83.43881856540084%;width:29.577464788732392%;height:2.4261603375527425%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.112676056338028cqw;color:#5C89A3;text-align:left;">◦ 一道汤咖喱 &amp;牛肉汉堡饼</div><div class="n text" data-node="0:36" style="left:69.57746478873239%;top:85.9704641350211%;width:25.492957746478872%;height:4.430379746835443%;font-family:&quot;Chalkboard&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.971830985915493cqw;color:#59452E;text-align:left;">Asoup curry
Beef Burger Cake</div><div class="n path" data-node="0:37" style="left:68.87323943661971%;top:90.71729957805907%;width:9.15492957746479%;height:4.219409282700422%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M1 99 C14 54 44 11 66 30 C92 50 25 112 42 65 C54 33 81 10 95 0 M77 1 L95 0 L89 23" fill="none" stroke="#654A31" stroke-width="2.5" stroke-linecap="round"/></svg></div></main></section>
```

### 验证与适配边界

验证覆盖完整组合的字体、配色、背景／卡片、图片／素材、文字归属及安全区，不能用骨架或字体样张单独代表通过。完整组合评审不等于像素级字标复刻，也不等于已完成印刷校样。参考照片分辨率、独立抠图、准确商标及复杂纸纤维仍依赖正式资产；正式交付需检查长菜名、价格宽度、实际物理尺寸下字号和安全区。

<a id="combination.menu-retro-diner"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 复古餐馆交错图注菜单

**产物适用**：菜单单页竖版。社媒长图／详情页单屏只能借用局部关系，必须重新分配信息密度，不自动串联菜单面。

### 背景、图文关系与安全区

**参考画幅**：658×944，仅为设计比例，不等于印刷毫米尺寸。

左品牌区与右双行标题分开。六图按三列错位，外列上图注、中列下图注，椭圆价签是独立DOM元素；不能把原照片旧价签留在裁图内再叠新价签。

背景或异形色卡 → 独立菜品与装饰素材 → 标题、菜名、译名和价格为分层关系；所有文字绑定其所属菜品或分类。背景纹理不能影响正文透明度，照片内原有文字必须清除或排除，不再重复叠写。页面外围至少2%留白；图注与图片可见轮廓至少4–8px；图注和价格保留6px间隔；标签完全落在所属图片或卡片安全区。文字变化时重排邻接对象，不靠缩小字号或裁切掩盖溢出。

### 配方字体与质感

品牌区 Bodoni 72 400 Italic（真实Book Italic字款），窄高几何处理并描边；标题及菜名 DIN Condensed 700；说明 Source Han Sans SC 400；椭圆价格 Arial Rounded MT Bold 700。

以上为本地实际可用候选及字重，不声称识别出原作者字体。先按目标环境核实字体文件、真实字款、中文覆盖与使用许可；不以字体名称相同或400参数相同代替整图视觉验证。字体选择必须连同配色、描边、背景和图文关系一起渲染。纸纹使用独立低对比噪声/纤维层；复杂真实纸纤维与产品摄影属于素材能力，不把规则点阵或裁片背景当成等价实现。

### CSS 组合实现

下面为已实渲染关系的维护源。生产按目标HTML行内化协议处理；文案是参考排版样例，营业事实由Brief绑定，不能沿用演示价格。照片已替换为独立资产槽，不携带原图、局部截图或本机路径。每槽绑定对应菜品，保留素材原比例；参考裁片的临时遮罩不带入生产。正文内联坐标为相对所属画布百分比，cqw字号随画布缩放。缩到手机宽度不代表可读性通过。

```css
.vl-menu-retro-diner .panel{position:relative;container-type:inline-size;width:100%;overflow:hidden;font-synthesis:none}.vl-menu-retro-diner .n{position:absolute;box-sizing:border-box}.vl-menu-retro-diner .text{white-space:pre-wrap;line-height:1.16;overflow-wrap:normal;margin:0}.vl-menu-retro-diner .photo{overflow:hidden}.vl-menu-retro-diner .break{height:18px;background:#dfdbd2}
```

```html
<section class="vl-menu-retro-diner"><main class="panel" data-width="658" data-height="944" style="aspect-ratio:658/944;background:#f5ecd8"><svg class="n" width="100%" height="100%" style="opacity:0.11;pointer-events:none"><filter id="noise0"><feTurbulence type="fractalNoise" baseFrequency=".67 .19" numOctaves="3" seed="9"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#noise0)"/></svg><div class="n text" data-bind="text-0:0" style="left:11.398176291793312%;top:2.5423728813559325%;width:30.091185410334347%;height:7.627118644067797%;font-family:&quot;Bodoni 72&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:9.270516717325227cqw;color:#f5edda;text-align:center;font-style:italic;transform:scaleX(0.76);transform-origin:top left;-webkit-text-stroke:.7px #173d48;text-shadow:1.5px 1px 0 #173d48;">Lake</div><div class="n text" data-bind="text-0:1" style="left:11.246200607902736%;top:9.216101694915254%;width:30.69908814589666%;height:6.1440677966101696%;font-family:&quot;Bodoni 72&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:7.446808510638298cqw;color:#f5edda;text-align:center;font-style:italic;transform:scaleX(0.76);transform-origin:top left;-webkit-text-stroke:.7px #173d48;text-shadow:1.5px 1px 0 #173d48;">House</div><div class="n shape" data-node="0:2" style="left:21.12462006079027%;top:15.995762711864407%;width:10.638297872340425%;height:2.9661016949152543%;transform:rotate(-5deg);background:#153c46;border-radius:50%;border:1px solid #ad8045;"></div><div class="n text" data-bind="text-0:3" style="left:22.036474164133736%;top:16.41949152542373%;width:8.814589665653495%;height:2.11864406779661%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.21580547112462cqw;color:#d5b97d;text-align:center;">BREWPUB
&amp; DINER</div><div class="n text" data-bind="text-0:4" style="left:36.32218844984803%;top:5.296610169491525%;width:30.3951367781155%;height:6.25%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:6.5349544072948325cqw;color:#153c46;text-align:left;">DINER MENU</div><div class="n text" data-bind="text-0:5" style="left:36.01823708206687%;top:11.016949152542372%;width:42.097264437689965%;height:7.733050847457627%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:9.270516717325227cqw;color:#a87538;text-align:left;">HOT SPECIAL</div><div class="n path" data-node="0:6" style="left:67.17325227963525%;top:4.025423728813559%;width:22.9483282674772%;height:6.779661016949152%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M1 82 L98 82 M7 77 L7 47 L13 47 L13 76 M10 47 L12 9 L15 47 M17 77 L17 40 L29 30 L43 40 L43 77 M15 41 L29 25 L47 40 M22 76 L22 51 L29 51 L29 76 M33 50 L39 50 L39 62 L33 62 Z M45 76 L45 48 L53 48 L53 76 M49 47 L50 2 L52 47 M55 75 L69 75 L69 63 L78 63 L78 77 M58 62 L58 55 M53 56 Q59 44 65 56 Z M81 78 L90 74 L90 62 M91 79 L94 78 L94 64 M2 87 Q28 84 45 88 T96 88 M18 94 L51 94 M60 94 L81 94" fill="none" stroke="#b1854f" stroke-width="0.8" stroke-linecap="round"/></svg></div><div class="n path" data-node="0:7" style="left:78.57142857142857%;top:11.334745762711865%;width:11.398176291793312%;height:7.309322033898305%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M7 4 L95 98 M2 12 L89 99 M91 2 L5 99 M97 9 L12 98 M50 5 C76 5 93 23 93 48 C93 75 75 94 50 94 C25 94 7 75 7 48 C7 22 24 5 50 5 Z M44 42 L50 35 L56 42 L64 45 L59 52 L58 60 L50 58 L42 61 L41 52 L35 46 Z M46 69 Q30 86 50 96 Q70 86 54 69 M40 77 L59 88 M59 77 L41 88" fill="none" stroke="#a87538" stroke-width="1.2" stroke-linecap="round"/></svg></div><div class="n text" data-bind="text-0:8" style="left:82.52279635258358%;top:11.546610169491526%;width:3.7993920972644375%;height:3.4957627118644066%;font-family:&quot;Songti SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.4954407294832825cqw;color:#a87538;text-align:center;">H</div><div class="n text" data-bind="text-0:9" style="left:79.0273556231003%;top:14.088983050847459%;width:3.4954407294832825%;height:2.6483050847457625%;font-family:&quot;Songti SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.343465045592705cqw;color:#a87538;text-align:center;">L</div><div class="n text" data-bind="text-0:10" style="left:85.86626139817629%;top:14.088983050847459%;width:3.64741641337386%;height:2.6483050847457625%;font-family:&quot;Songti SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.343465045592705cqw;color:#a87538;text-align:center;">B</div><div class="n shape" data-node="0:11" style="left:7.446808510638298%;top:19.597457627118644%;width:85.56231003039514%;height:0.1059322033898305%;background:#b18c57;border-radius:0;border:none;"></div><div class="n shape" data-node="0:12" style="left:9.270516717325227%;top:21.398305084745765%;width:24.012158054711247%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:13" style="left:9.878419452887538%;top:21.927966101694913%;width:22.796352583586625%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.43161094224924cqw;color:#153c46;text-align:center;">MACKEREL IN JOSPER</div><div class="n text" data-bind="text-0:14" style="left:8.206686930091186%;top:24.68220338983051%;width:26.443768996960486%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Macrou în josper cu cartofi
prăjiți și salată din varză
roșie</div><div class="n shape" data-node="0:15" style="left:14.74164133738602%;top:28.8135593220339%;width:13.37386018237082%;height:0.1059322033898305%;background:#bda579;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:16" style="left:10.030395136778116%;top:29.23728813559322%;width:22.796352583586625%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">200/120/100/40 g</div><div class="n shape" data-node="0:17" style="left:16.109422492401215%;top:30.93220338983051%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:18" style="left:16.565349544072948%;top:31.25%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:19" style="left:17.02127659574468%;top:31.46186440677966%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">100.</div><div class="n photo" style="left:7.598784194528875%;top:35.27542372881356%;width:27.659574468085108%;height:20.127118644067796%;border-radius:0.0cqw;"><img data-asset-slot="dish-1" src="{{dish_1_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n photo" style="left:36.474164133738604%;top:20.55084745762712%;width:27.659574468085108%;height:20.44491525423729%;border-radius:0.0cqw;"><img data-asset-slot="dish-2" src="{{dish_2_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n shape" data-node="0:22" style="left:45.13677811550152%;top:41.52542372881356%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:23" style="left:45.59270516717325%;top:41.84322033898305%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:24" style="left:46.048632218844986%;top:42.05508474576271%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">165.</div><div class="n shape" data-node="0:25" style="left:38.753799392097264%;top:46.08050847457627%;width:23.10030395136778%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:26" style="left:39.361702127659576%;top:46.61016949152542%;width:21.88449848024316%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.5835866261398177cqw;color:#153c46;text-align:center;">SALMON STAKE</div><div class="n text" data-bind="text-0:27" style="left:37.38601823708207%;top:49.36440677966102%;width:25.835866261398177%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Steak de somon cu sos de
frișcă și muștar, cartofi prăjiți
și salată din varză roșie</div><div class="n text" data-bind="text-0:28" style="left:39.361702127659576%;top:53.813559322033896%;width:21.88449848024316%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">150/120/100/40 g</div><div class="n shape" data-node="0:29" style="left:68.38905775075987%;top:21.398305084745765%;width:21.580547112462007%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:30" style="left:69.14893617021278%;top:21.927966101694913%;width:20.060790273556233%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.5835866261398177cqw;color:#153c46;text-align:center;">LULA KEBAB</div><div class="n text" data-bind="text-0:31" style="left:66.10942249240122%;top:24.68220338983051%;width:26.13981762917933%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Lula-Kebab din carne de
pui și vită, în sos picant de
frișcă</div><div class="n shape" data-node="0:32" style="left:72.49240121580547%;top:28.8135593220339%;width:13.37386018237082%;height:0.1059322033898305%;background:#bda579;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:33" style="left:68.84498480243161%;top:29.23728813559322%;width:20.66869300911854%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">320 g</div><div class="n shape" data-node="0:34" style="left:73.86018237082067%;top:30.93220338983051%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:35" style="left:74.3161094224924%;top:31.25%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:36" style="left:74.77203647416414%;top:31.46186440677966%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">105.</div><div class="n photo" style="left:65.34954407294833%;top:35.27542372881356%;width:27.659574468085108%;height:20.127118644067796%;border-radius:0.0cqw;"><img data-asset-slot="dish-3" src="{{dish_3_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:38" style="left:7.598784194528875%;top:56.355932203389834%;width:27.659574468085108%;height:1.8008474576271187%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#a87538;text-align:center;">LAKE HOUSE BREWPUB &amp; DINER</div><div class="n text" data-bind="text-0:39" style="left:36.474164133738604%;top:56.355932203389834%;width:27.659574468085108%;height:1.8008474576271187%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">LAKE HOUSE BREWPUB &amp; DINER</div><div class="n text" data-bind="text-0:40" style="left:65.34954407294833%;top:56.355932203389834%;width:27.659574468085108%;height:1.8008474576271187%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#a87538;text-align:center;">LAKE HOUSE BREWPUB &amp; DINER</div><div class="n shape" data-node="0:41" style="left:10.638297872340425%;top:60.063559322033896%;width:21.580547112462007%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:42" style="left:11.398176291793312%;top:60.59322033898306%;width:20.060790273556233%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.5835866261398177cqw;color:#153c46;text-align:center;">PORK KNUCKLE</div><div class="n text" data-bind="text-0:43" style="left:8.206686930091186%;top:63.347457627118644%;width:26.443768996960486%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Ciolan de porc cu cartofi
prăjiți, varză murată, sos chili
și ketchup</div><div class="n text" data-bind="text-0:44" style="left:9.878419452887538%;top:67.6906779661017%;width:23.10030395136778%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">540/150/125/50/50 g</div><div class="n shape" data-node="0:45" style="left:16.109422492401215%;top:69.49152542372882%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:46" style="left:16.565349544072948%;top:69.8093220338983%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:47" style="left:17.02127659574468%;top:70.02118644067797%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">220.</div><div class="n photo" style="left:7.598784194528875%;top:73.83474576271186%;width:27.659574468085108%;height:20.127118644067796%;border-radius:0.0cqw;"><img data-asset-slot="dish-4" src="{{dish_4_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n photo" style="left:36.474164133738604%;top:59.0042372881356%;width:27.659574468085108%;height:20.44491525423729%;border-radius:0.0cqw;"><img data-asset-slot="dish-5" src="{{dish_5_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n shape" data-node="0:50" style="left:45.13677811550152%;top:80.08474576271186%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:51" style="left:45.59270516717325%;top:80.40254237288136%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:52" style="left:46.048632218844986%;top:80.61440677966102%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">250.</div><div class="n shape" data-node="0:53" style="left:39.66565349544073%;top:84.53389830508475%;width:21.428571428571427%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:54" style="left:40.27355623100304%;top:85.0635593220339%;width:20.212765957446805%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.5835866261398177cqw;color:#153c46;text-align:center;">STEAK RIBEYE</div><div class="n text" data-bind="text-0:55" style="left:37.234042553191486%;top:87.8177966101695%;width:26.13981762917933%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Steak Ribeye cu legume la grătar
și cartofi prăjiți, sos chili și
ketchup</div><div class="n text" data-bind="text-0:56" style="left:39.361702127659576%;top:92.26694915254238%;width:21.88449848024316%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">450/150/50/50 g</div><div class="n shape" data-node="0:57" style="left:68.38905775075987%;top:60.063559322033896%;width:21.580547112462007%;height:2.754237288135593%;background:#f5ecd8;border-radius:0;border:1px solid #b18c57;"></div><div class="n text" data-bind="text-0:58" style="left:69.14893617021278%;top:60.59322033898306%;width:20.060790273556233%;height:2.11864406779661%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.5835866261398177cqw;color:#153c46;text-align:center;">PORK RIBS BBQ</div><div class="n text" data-bind="text-0:59" style="left:66.10942249240122%;top:63.347457627118644%;width:26.13981762917933%;height:3.8135593220338984%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">Costițe de porc glazurate
cu cartofi prăjiți, sos chili
și ketchup</div><div class="n text" data-bind="text-0:60" style="left:67.62917933130699%;top:67.6906779661017%;width:23.10030395136778%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.3677811550151975cqw;color:#153c46;text-align:center;">380/150/50/50 g</div><div class="n shape" data-node="0:61" style="left:73.86018237082067%;top:69.49152542372882%;width:10.638297872340425%;height:3.7076271186440675%;background:#153c46;border-radius:50%;border:1px solid #ac854e;"></div><div class="n shape" data-node="0:62" style="left:74.3161094224924%;top:69.8093220338983%;width:9.72644376899696%;height:3.0720338983050848%;background:#153c46;border-radius:50%;border:1px solid #e0cd9d;"></div><div class="n text" data-bind="text-0:63" style="left:74.77203647416414%;top:70.02118644067797%;width:8.814589665653495%;height:2.860169491525424%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.4954407294832825cqw;color:#f6eedb;text-align:center;">150.</div><div class="n photo" style="left:65.34954407294833%;top:73.83474576271186%;width:27.659574468085108%;height:20.127118644067796%;border-radius:0.0cqw;"><img data-asset-slot="dish-6" src="{{dish_6_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n shape" data-node="0:65" style="left:25.835866261398177%;top:95.65677966101694%;width:15.653495440729484%;height:0.1059322033898305%;background:#b18c57;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:66" style="left:42.24924012158054%;top:95.02118644067797%;width:15.19756838905775%;height:1.3771186440677965%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:0.911854103343465cqw;color:#9d783e;text-align:center;">LAKE HOUSE BREWPUB &amp; DINER</div><div class="n shape" data-node="0:67" style="left:58.20668693009119%;top:95.65677966101694%;width:15.653495440729484%;height:0.1059322033898305%;background:#b18c57;border-radius:0;border:none;"></div></main></section>
```

### 验证与适配边界

验证覆盖完整组合的字体、配色、背景／卡片、图片／素材、文字归属及安全区，不能用骨架或字体样张单独代表通过。完整组合评审不等于像素级字标复刻，也不等于已完成印刷校样。参考照片分辨率、独立抠图、准确商标及复杂纸纤维仍依赖正式资产；正式交付需检查长菜名、价格宽度、实际物理尺寸下字号和安全区。


修订约束（2026-09-13）：字标与椭圆标分离保护；加料区按卡片内实际文字边界验收，禁止内容底边越出卡片。887px参考画布中加料正文8.5–9px仅用于该信息密度，转印刷或手机时重新排版，不直接等比缩小。

<a id="combination.menu-orange-combo"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 橙色主推与套餐矩阵菜单

**产物适用**：菜单横版。社媒长图／详情页单屏只能借用局部关系，必须重新分配信息密度，不自动串联菜单面。

### 背景、图文关系与安全区

**参考画幅**：1460×982，仅为设计比例，不等于印刷毫米尺寸。

横版上品牌条、左两大主推、右五组套餐、下两行五列单品。价格与套餐图分属同一条目，主推照片完整，菜品不得重复充数，图组不能压住分类标题。

背景或异形色卡 → 独立菜品与装饰素材 → 标题、菜名、译名和价格为分层关系；所有文字绑定其所属菜品或分类。背景纹理不能影响正文透明度，照片内原有文字必须清除或排除，不再重复叠写。页面外围至少2%留白；图注与图片可见轮廓至少4–8px；图注和价格保留6px间隔；标签完全落在所属图片或卡片安全区。文字变化时重排邻接对象，不靠缩小字号或裁切掩盖溢出。

### 配方字体与质感

中文大标题 Feibo Zheng Dots 400；分类及菜名 FZZJ-DHTMBKSJF 400；价格 Arial 700 Italic（真实Bold Italic字款）；中文功能字 Source Han Sans SC 400。

以上为本地实际可用候选及字重，不声称识别出原作者字体。先按目标环境核实字体文件、真实字款、中文覆盖与使用许可；不以字体名称相同或400参数相同代替整图视觉验证。字体选择必须连同配色、描边、背景和图文关系一起渲染。纸纹使用独立低对比噪声/纤维层；复杂真实纸纤维与产品摄影属于素材能力，不把规则点阵或裁片背景当成等价实现。

### CSS 组合实现

下面为已实渲染关系的维护源。生产按目标HTML行内化协议处理；文案是参考排版样例，营业事实由Brief绑定，不能沿用演示价格。照片已替换为独立资产槽，不携带原图、局部截图或本机路径。每槽绑定对应菜品，保留素材原比例；参考裁片的临时遮罩不带入生产。正文内联坐标为相对所属画布百分比，cqw字号随画布缩放。缩到手机宽度不代表可读性通过。

```css
.vl-menu-orange-combo .panel{position:relative;container-type:inline-size;width:100%;overflow:hidden;font-synthesis:none}.vl-menu-orange-combo .n{position:absolute;box-sizing:border-box}.vl-menu-orange-combo .text{white-space:pre-wrap;line-height:1.16;overflow-wrap:normal;margin:0}.vl-menu-orange-combo .photo{overflow:hidden}.vl-menu-orange-combo .break{height:18px;background:#dfdbd2}
```

```html
<section class="vl-menu-orange-combo"><main class="panel" data-width="1460" data-height="982" style="aspect-ratio:1460/982;background:#F7EEDB"><svg class="n" width="100%" height="100%" style="opacity:0.05;pointer-events:none"><filter id="noise0"><feTurbulence type="fractalNoise" baseFrequency=".67 .19" numOctaves="3" seed="9"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#noise0)"/></svg><div class="n shape" data-node="0:0" style="left:0.0%;top:0.0%;width:100.0%;height:9.164969450101832%;background:#EB510B;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:1" style="left:1.9863013698630139%;top:1.2219959266802443%;width:15.0%;height:6.924643584521386%;font-family:&quot;Feibo Zheng Dots&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.9726027397260277cqw;color:#FFF7E7;text-align:left;">麻六记</div><div class="n text" data-bind="text-0:2" style="left:17.671232876712327%;top:1.7311608961303464%;width:10.684931506849315%;height:3.360488798370672%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.8493150684931507cqw;color:#FFF7E7;text-align:left;">酸 辣 粉</div><div class="n text" data-bind="text-0:3" style="left:17.73972602739726%;top:5.193482688391039%;width:10.753424657534246%;height:2.4439918533604885%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#FFF7E7;text-align:left;">川渝名小吃</div><div class="n text" data-bind="text-0:4" style="left:82.1917808219178%;top:1.6293279022403258%;width:15.753424657534246%;height:2.5458248472505094%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5753424657534247cqw;color:#FFF7E7;text-align:right;">MALIUJI</div><div class="n text" data-bind="text-0:5" style="left:79.45205479452055%;top:4.786150712830957%;width:18.493150684931507%;height:3.054989816700611%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.8493150684931507cqw;color:#FFF7E7;text-align:right;">400-0286-366</div><div class="n shape" data-node="0:6" style="left:1.9863013698630139%;top:10.692464358452138%;width:26.986301369863014%;height:86.25254582484725%;background:linear-gradient(180deg,#F8EEDB 4%,#F7D7B4 36%,#F27634 64%,#ED510D 100%);border-radius:0;border:none;"></div><div class="n photo" style="left:2.1232876712328768%;top:11.303462321792262%;width:17.602739726027398%;height:25.788088023446427%;border-radius:0.0cqw;"><img data-asset-slot="dish-1" src="{{dish_1_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n photo" style="left:2.4657534246575343%;top:34.317718940936864%;width:25.410958904109588%;height:19.85052987676482%;border-radius:0.0cqw;"><img data-asset-slot="dish-2" src="{{dish_2_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n path" data-node="0:9" style="left:19.17808219178082%;top:18.228105906313647%;width:7.602739726027398%;height:13.441955193482688%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M49 3 C79 0 98 23 96 51 C98 78 82 97 53 98 C23 100 3 79 4 49 C1 25 23 3 49 3 Z" fill="none" stroke="#BC511D" stroke-width="2.2" stroke-linecap="round"/></svg></div><div class="n text" data-bind="text-0:10" style="left:19.726027397260275%;top:19.45010183299389%;width:6.575342465753424%;height:11.09979633401222%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5068493150684932cqw;color:#AA4619;text-align:center;">地道
骨汤熬制
手工制粉
纯正</div><div class="n text" data-bind="text-0:11" style="left:3.287671232876712%;top:54.88798370672098%;width:16.986301369863014%;height:2.5458248472505094%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1643835616438356cqw;color:#FFF6DF;text-align:left;">推荐 ★★★★★</div><div class="n text" data-bind="text-0:12" style="left:3.287671232876712%;top:58.044806517311606%;width:16.43835616438356%;height:3.5641547861507124%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.7808219178082192cqw;color:#FFF8E8;text-align:left;">经典杂酱酸辣粉</div><div class="n text" data-bind="text-0:13" style="left:20.616438356164384%;top:56.72097759674134%;width:6.712328767123288%;height:5.091649694501019%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.945205479452055cqw;color:#FFF8E8;text-align:right;font-style:italic;">¥18</div><div class="n photo" style="left:2.3972602739726026%;top:62.83095723014257%;width:25.54794520547945%;height:24.09033748410995%;border-radius:0.0cqw;"><img data-asset-slot="dish-3" src="{{dish_3_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:15" style="left:3.287671232876712%;top:87.37270875763747%;width:16.78082191780822%;height:2.4439918533604885%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1643835616438356cqw;color:#FFF4DC;text-align:left;">推荐 ★★★★★</div><div class="n text" data-bind="text-0:16" style="left:3.287671232876712%;top:90.22403258655804%;width:16.71232876712329%;height:3.462321792260693%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.7808219178082192cqw;color:#FFF8E8;text-align:left;">超级豪华酸辣粉</div><div class="n text" data-bind="text-0:17" style="left:3.287671232876712%;top:93.9918533604888%;width:17.671232876712327%;height:2.3421588594704685%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1643835616438356cqw;color:#FFF8E8;text-align:left;">（肥肠+牛肉+三脆+牛杂）</div><div class="n text" data-bind="text-0:18" style="left:20.616438356164384%;top:90.020366598778%;width:6.712328767123288%;height:5.193482688391039%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.945205479452055cqw;color:#FFF8E8;text-align:right;font-style:italic;">¥38</div><div class="n text" data-bind="text-0:19" style="left:30.82191780821918%;top:11.710794297352342%;width:26.71232876712329%;height:11.507128309572302%;font-family:&quot;Feibo Zheng Dots&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:6.301369863013699cqw;color:#1E1B15;text-align:center;">超值会员</div><div class="n shape" data-node="0:20" style="left:31.506849315068493%;top:22.912423625254583%;width:24.863013698630137%;height:11.303462321792262%;transform:rotate(-3deg);clip-path:polygon(1% 12%,53% 4%,98% 0%,100% 33%,94% 36%,98% 79%,64% 86%,62% 96%,11% 100%,13% 85%,0% 84%,0% 62%,8% 58%);background:#EF5A14;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:21" style="left:32.602739726027394%;top:21.792260692464357%;width:18.424657534246574%;height:12.423625254582484%;font-family:&quot;Feibo Zheng Dots&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:7.260273972602739cqw;color:#1E1B15;text-align:center;">套餐</div><div class="n text" data-bind="text-0:22" style="left:48.6986301369863%;top:29.124236252545828%;width:5.136986301369863%;height:3.8696537678207736%;font-family:&quot;DIN Condensed&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:0.8904109589041096cqw;color:#261F16;text-align:center;">MALIUJI
酸辣粉</div><div class="n path" data-node="0:23" style="left:49.45205479452055%;top:24.338085539714868%;width:7.397260273972603%;height:7.841140529531568%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M3 30 C24 1 69 0 77 28 C88 63 61 84 53 56 C48 31 79 7 88 45 L93 77 M76 64 L94 80 L100 54" fill="none" stroke="#211B13" stroke-width="5" stroke-linecap="round"/></svg></div><div class="n text" data-bind="text-0:24" style="left:61.438356164383556%;top:12.118126272912424%;width:14.315068493150685%;height:3.2586558044806515%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.7808219178082192cqw;color:#B94D20;text-align:left;">必点单人套餐</div><div class="n text" data-bind="text-0:25" style="left:61.57534246575342%;top:15.376782077393075%;width:10.479452054794521%;height:5.39714867617108%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.808219178082192cqw;color:#C54912;text-align:left;font-style:italic;">¥24</div><div class="n photo" style="left:59.24657534246576%;top:20.061099796334013%;width:13.972602739726028%;height:10.386965376782078%;border-radius:0.0cqw;"><img data-asset-slot="dish-4" src="{{dish_4_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n photo" style="left:76.78082191780821%;top:12.830957230142568%;width:15.273972602739727%;height:11.35437881873727%;border-radius:0.0cqw;"><img data-asset-slot="dish-5" src="{{dish_5_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:28" style="left:77.19178082191782%;top:24.84725050916497%;width:16.36986301369863%;height:3.2586558044806515%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.7808219178082192cqw;color:#B94D20;text-align:left;">经典单人套餐</div><div class="n text" data-bind="text-0:29" style="left:77.32876712328766%;top:28.30957230142566%;width:11.301369863013697%;height:4.786150712830957%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.8767123287671232cqw;color:#C54912;text-align:left;font-style:italic;">¥20</div><div class="n text" data-bind="text-0:30" style="left:31.164383561643838%;top:36.96537678207739%;width:14.383561643835616%;height:3.1568228105906315%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.8493150684931507cqw;color:#B94D20;text-align:left;">经典双人餐</div><div class="n text" data-bind="text-0:31" style="left:31.232876712328768%;top:40.42769857433808%;width:9.520547945205479%;height:5.7026476578411405%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.0136986301369864cqw;color:#C54912;text-align:left;font-style:italic;">¥52</div><div class="n photo" style="left:36.36986301369863%;top:44.5010183299389%;width:13.013698630136986%;height:12.293098986170964%;border-radius:0.0cqw;"><img data-asset-slot="dish-6" src="{{dish_6_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:33" style="left:53.90410958904109%;top:34.92871690427698%;width:14.794520547945206%;height:3.2586558044806515%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.8493150684931507cqw;color:#B94D20;text-align:left;">经典双人餐</div><div class="n text" data-bind="text-0:34" style="left:54.041095890410965%;top:38.69653767820774%;width:9.794520547945206%;height:5.7026476578411405%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.0136986301369864cqw;color:#C54912;text-align:left;font-style:italic;">¥66</div><div class="n photo" style="left:58.83561643835616%;top:43.58452138492871%;width:13.013698630136986%;height:13.899618418896459%;border-radius:0.0cqw;"><img data-asset-slot="dish-7" src="{{dish_7_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:36" style="left:75.89041095890411%;top:36.252545824847246%;width:15.753424657534246%;height:3.360488798370672%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.8493150684931507cqw;color:#B94D20;text-align:left;">豪华双人套餐</div><div class="n text" data-bind="text-0:37" style="left:76.02739726027397%;top:40.020366598778004%;width:10.136986301369863%;height:5.7026476578411405%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.0136986301369864cqw;color:#C54912;text-align:left;font-style:italic;">¥80</div><div class="n photo" style="left:81.23287671232877%;top:43.58452138492871%;width:13.013698630136986%;height:12.431012103880207%;border-radius:0.0cqw;"><img data-asset-slot="dish-8" src="{{dish_8_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n shape" data-node="0:39" style="left:30.34246575342466%;top:62.52545824847251%;width:67.6027397260274%;height:34.419551934826885%;background:linear-gradient(180deg,#ED691E 0%,#F3B787 23%,#F7EBD7 54%,#F7EEDB 100%);border-radius:49px 61px 8px 8px / 43px 52px 8px 8px;border:none;"></div><div class="n text" data-bind="text-0:40" style="left:31.506849315068493%;top:57.5356415478615%;width:29.93150684931507%;height:5.6008146639511205%;font-family:&quot;Feibo Zheng Dots&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.8767123287671232cqw;color:#B84A19;text-align:left;">招牌酸辣粉系列</div><div class="n text" data-bind="text-0:41" style="left:80.95890410958904%;top:59.67413441955194%;width:16.095890410958905%;height:2.9531568228105907%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5068493150684932cqw;color:#B84A19;text-align:right;">精选红薯 手制鲜粉</div><div class="n shape" data-node="0:42" style="left:31.780821917808222%;top:80.44806517311609%;width:64.65753424657534%;height:0.10183299389002036%;background:#DFCCB3;border-radius:0;border:none;"></div><div class="n shape" data-node="0:43" style="left:71.5068493150685%;top:65.071283095723%;width:0.0684931506849315%;height:31.05906313645621%;background:#E4CDB3;border-radius:0;border:none;"></div><div class="n text" data-bind="text-0:44" style="left:31.438356164383563%;top:64.56211812627292%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">经典杂酱酸辣粉</div><div class="n photo" style="left:32.32876712328767%;top:67.92260692464357%;width:9.315068493150685%;height:8.024820602622912%;border-radius:0.0cqw;"><img data-asset-slot="dish-9" src="{{dish_9_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:46" style="left:33.21917808219178%;top:76.37474541751527%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥16</div><div class="n text" data-bind="text-0:47" style="left:44.86301369863014%;top:64.56211812627292%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">泡椒三脆酸辣粉</div><div class="n photo" style="left:45.75342465753425%;top:67.92260692464357%;width:9.315068493150685%;height:7.950516708154182%;border-radius:0.0cqw;"><img data-asset-slot="dish-10" src="{{dish_10_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:49" style="left:46.64383561643836%;top:76.37474541751527%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥22</div><div class="n text" data-bind="text-0:50" style="left:58.28767123287671%;top:64.56211812627292%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">红烧肉酸辣粉</div><div class="n photo" style="left:59.178082191780824%;top:67.92260692464357%;width:9.315068493150685%;height:8.024820602622912%;border-radius:0.0cqw;"><img data-asset-slot="dish-11" src="{{dish_11_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:52" style="left:60.06849315068493%;top:76.37474541751527%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥22</div><div class="n text" data-bind="text-0:53" style="left:72.80821917808218%;top:64.56211812627292%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">清汤杂酱粉</div><div class="n photo" style="left:73.6986301369863%;top:67.92260692464357%;width:9.315068493150685%;height:8.024820602622912%;border-radius:0.0cqw;"><img data-asset-slot="dish-12" src="{{dish_12_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:55" style="left:74.58904109589041%;top:76.37474541751527%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥18</div><div class="n text" data-bind="text-0:56" style="left:85.75342465753425%;top:64.56211812627292%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">番茄肉酱粉</div><div class="n photo" style="left:86.64383561643835%;top:67.92260692464357%;width:9.315068493150685%;height:8.024820602622912%;border-radius:0.0cqw;"><img data-asset-slot="dish-13" src="{{dish_13_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:58" style="left:87.53424657534246%;top:76.37474541751527%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥18</div><div class="n text" data-bind="text-0:59" style="left:31.438356164383563%;top:82.28105906313645%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">牛杂酸辣粉</div><div class="n photo" style="left:32.465753424657535%;top:85.64154786150712%;width:9.04109589041096%;height:7.907032466754524%;border-radius:0.0cqw;"><img data-asset-slot="dish-14" src="{{dish_14_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:61" style="left:33.21917808219178%;top:94.09368635437882%;width:7.602739726027398%;height:4.480651731160896%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥24</div><div class="n text" data-bind="text-0:62" style="left:44.86301369863014%;top:82.28105906313645%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">肥肠酸辣粉</div><div class="n photo" style="left:45.89041095890411%;top:85.64154786150712%;width:9.04109589041096%;height:8.03881634120043%;border-radius:0.0cqw;"><img data-asset-slot="dish-15" src="{{dish_15_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:64" style="left:46.64383561643836%;top:94.09368635437882%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥26</div><div class="n text" data-bind="text-0:65" style="left:58.28767123287671%;top:82.28105906313645%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">红烧牛肉酸辣粉</div><div class="n photo" style="left:59.31506849315068%;top:85.64154786150712%;width:9.04109589041096%;height:8.03881634120043%;border-radius:0.0cqw;"><img data-asset-slot="dish-16" src="{{dish_16_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:67" style="left:60.06849315068493%;top:94.09368635437882%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥26</div><div class="n text" data-bind="text-0:68" style="left:72.80821917808218%;top:82.28105906313645%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">红烧肉粉</div><div class="n photo" style="left:73.83561643835617%;top:85.64154786150712%;width:9.04109589041096%;height:8.03881634120043%;border-radius:0.0cqw;"><img data-asset-slot="dish-17" src="{{dish_17_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:70" style="left:74.58904109589041%;top:94.09368635437882%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥22</div><div class="n text" data-bind="text-0:71" style="left:85.75342465753425%;top:82.28105906313645%;width:11.164383561643836%;height:2.74949083503055%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.36986301369863cqw;color:#261D14;text-align:center;">冒节子肥肠粉</div><div class="n photo" style="left:86.78082191780821%;top:85.64154786150712%;width:9.04109589041096%;height:8.03881634120043%;border-radius:0.0cqw;"><img data-asset-slot="dish-18" src="{{dish_18_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:73" style="left:87.53424657534246%;top:94.09368635437882%;width:7.602739726027398%;height:3.6659877800407332%;font-family:&quot;Arial&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.1232876712328768cqw;color:#BF4915;text-align:center;font-style:italic;">¥26</div></main></section>
```

### 验证与适配边界

验证覆盖完整组合的字体、配色、背景／卡片、图片／素材、文字归属及安全区，不能用骨架或字体样张单独代表通过。完整组合评审不等于像素级字标复刻，也不等于已完成印刷校样。参考照片分辨率、独立抠图、准确商标及复杂纸纤维仍依赖正式资产；正式交付需检查长菜名、价格宽度、实际物理尺寸下字号和安全区。

<a id="combination.menu-pastel-dessert"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 柔色甜品异形卡片与双语价目菜单

**产物适用**：菜单多面横版。社媒长图／详情页单屏只能借用局部关系，必须重新分配信息密度，不自动串联菜单面。

### 背景、图文关系与安全区

**参考画幅**：887×625；887×632，仅为设计比例，不等于印刷毫米尺寸。

两个独立横版面。第一面粉色大异形冰品区、米白咖啡区、浅绿麻薯区；图片可以突破色卡但不能侵入图注净空。第二面左品牌竖条、两列品类价目与底部加料区，不把两个面拼成长菜单。

背景或异形色卡 → 独立菜品与装饰素材 → 标题、菜名、译名和价格为分层关系；所有文字绑定其所属菜品或分类。背景纹理不能影响正文透明度，照片内原有文字必须清除或排除，不再重复叠写。页面外围至少2%留白；图注与图片可见轮廓至少4–8px；图注和价格保留6px间隔；标签完全落在所属图片或卡片安全区。文字变化时重排邻接对象，不靠缩小字号或裁切掩盖溢出。

### 配方字体与质感

英文标题 Arial Rounded MT Bold 700；中文标题 FZZJ-DHTMBKSJF 400；下页正文及价格 Source Han Sans SC 400，正文约10.5–11.5px（887画布）；正文不用细小书法体。

以上为本地实际可用候选及字重，不声称识别出原作者字体。先按目标环境核实字体文件、真实字款、中文覆盖与使用许可；不以字体名称相同或400参数相同代替整图视觉验证。字体选择必须连同配色、描边、背景和图文关系一起渲染。纸纹使用独立低对比噪声/纤维层；复杂真实纸纤维与产品摄影属于素材能力，不把规则点阵或裁片背景当成等价实现。

### CSS 组合实现

下面为已实渲染关系的维护源。生产按目标HTML行内化协议处理；文案是参考排版样例，营业事实由Brief绑定，不能沿用演示价格。照片已替换为独立资产槽，不携带原图、局部截图或本机路径。每槽绑定对应菜品，保留素材原比例；参考裁片的临时遮罩不带入生产。正文内联坐标为相对所属画布百分比，cqw字号随画布缩放。缩到手机宽度不代表可读性通过。

```css
.vl-menu-pastel-dessert .panel{position:relative;container-type:inline-size;width:100%;overflow:hidden;font-synthesis:none}.vl-menu-pastel-dessert .n{position:absolute;box-sizing:border-box}.vl-menu-pastel-dessert .text{white-space:pre-wrap;line-height:1.16;overflow-wrap:normal;margin:0}.vl-menu-pastel-dessert .photo{overflow:hidden}.vl-menu-pastel-dessert .break{height:18px;background:#dfdbd2}
```

```html
<section class="vl-menu-pastel-dessert"><main class="panel" data-width="887" data-height="625" style="aspect-ratio:887/625;background:#c6e3c9"><svg class="n" width="100%" height="100%" style="opacity:0.05;pointer-events:none"><filter id="noise0"><feTurbulence type="fractalNoise" baseFrequency=".67 .19" numOctaves="3" seed="9"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#noise0)"/></svg><div class="n shape" data-node="0:0" style="left:3.9458850056369785%;top:18.08%;width:48.47801578354002%;height:78.4%;transform:rotate(-5deg);background:#efc1c8;border-radius:47% 58% 49% 38% / 41% 36% 61% 59%;border:none;"></div><div class="n shape" data-node="0:1" style="left:50.28184892897407%;top:4.8%;width:46.89966178128523%;height:55.2%;background:#faf8e6;border-radius:49% 33% 24% 31% / 28% 34% 37% 33%;border:none;"></div><div class="n shape" data-node="0:2" style="left:50.84554678692221%;top:62.56%;width:45.88500563697858%;height:33.76%;transform:rotate(-2deg);background:#e1efb3;border-radius:35% 47% 29% 43% / 39% 33% 50% 42%;border:none;"></div><div class="n shape" data-node="0:3" style="left:2.593010146561443%;top:3.6799999999999997%;width:10.259301014656144%;height:15.36%;transform:rotate(-6deg);background:#efc6cb;border-radius:48% 51% 42% 47% / 43% 48% 52% 49%;border:3px solid #fff7e9;"></div><div class="n path" data-node="0:4" style="left:4.735062006764374%;top:5.92%;width:5.975197294250282%;height:7.68%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M21 43 C5 31 16 12 34 22 C43 8 64 10 72 24 C92 17 100 37 83 46 L85 69 C78 87 28 89 19 68 Z M35 48 L36 53 M64 48 L65 53 M44 65 Q50 71 57 64" fill="#f4d5d3" stroke="#b48285" stroke-width="3" stroke-linecap="round"/></svg></div><div class="n text" data-bind="text-0:5" style="left:3.269447576099211%;top:13.76%;width:9.357384441939121%;height:4.0%;font-family:&quot;Brush Script MT&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.142051860202931cqw;color:#a77379;text-align:center;">Lucky Joy</div><div class="n text" data-bind="text-0:6" style="left:14.430665163472378%;top:3.52%;width:19.84216459977452%;height:15.040000000000001%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:4.3968432919954905cqw;color:#fffbee;text-align:left;">Shaved
Ice</div><div class="n text" data-bind="text-0:7" style="left:33.370913190529876%;top:4.16%;width:12.73957158962796%;height:8.16%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:4.8478015783540025cqw;color:#69a67e;text-align:left;">雪花</div><div class="n text" data-bind="text-0:8" style="left:30.665163472378804%;top:11.52%;width:16.1217587373168%;height:6.72%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.720405862457723cqw;color:#69a67e;text-align:center;">冰冰滋</div><div class="n photo" style="left:9.92108229988726%;top:18.08%;width:19.95490417136415%;height:27.242608695652176%;border-radius:0.0cqw;"><img data-asset-slot="dish-1" src="{{dish_1_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:10" style="left:30.101465614430666%;top:21.12%;width:19.729425028184895%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.4656144306651635cqw;color:#65564e;text-align:left;">Mango Pomelo Sago</div><div class="n text" data-bind="text-0:11" style="left:30.101465614430666%;top:24.16%;width:12.62683201803833%;height:5.4399999999999995%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#65564e;text-align:left;">何以解愁
杨枝甘露</div><div class="n text" data-bind="text-0:12" style="left:30.214205186020294%;top:29.759999999999998%;width:8.793686583990981%;height:3.52%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.029312288613303cqw;color:#76a781;text-align:left;">£9.5</div><div class="n photo" style="left:32.581736189402484%;top:30.080000000000002%;width:19.95490417136415%;height:26.105027932960894%;border-radius:0.0cqw;"><img data-asset-slot="dish-2" src="{{dish_2_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:14" style="left:24.01352874859076%;top:46.56%;width:9.244644870349493%;height:4.4799999999999995%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.2401352874859075cqw;color:#65564e;text-align:left;">Red bean
matcha</div><div class="n text" data-bind="text-0:15" style="left:24.01352874859076%;top:51.2%;width:9.244644870349493%;height:2.4%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#65564e;text-align:left;">红豆抹茶刨冰</div><div class="n text" data-bind="text-0:16" style="left:24.01352874859076%;top:54.08%;width:9.244644870349493%;height:3.36%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.6910935738444193cqw;color:#76a781;text-align:left;">£9.5</div><div class="n photo" style="left:2.593010146561443%;top:41.28%;width:21.08229988726043%;height:22.517113402061856%;border-radius:0.0cqw;"><img data-asset-slot="dish-3" src="{{dish_3_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:18" style="left:7.328072153325817%;top:64.8%;width:14.656144306651633%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#65564e;text-align:left;">Strawberry</div><div class="n text" data-bind="text-0:19" style="left:7.328072153325817%;top:67.84%;width:15.219842164599775%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.6910935738444193cqw;color:#65564e;text-align:left;">莓莓郁郁了</div><div class="n text" data-bind="text-0:20" style="left:7.440811724915446%;top:72.0%;width:8.568207440811724%;height:3.52%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.029312288613303cqw;color:#76a781;text-align:left;">£9.5</div><div class="n text" data-bind="text-0:21" style="left:24.577226606538897%;top:57.599999999999994%;width:13.303269447576099%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.4656144306651635cqw;color:#65564e;text-align:left;">Bubble Milk Tea</div><div class="n text" data-bind="text-0:22" style="left:24.577226606538897%;top:60.64000000000001%;width:12.063134160090192%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#65564e;text-align:left;">你珍的是嘛</div><div class="n text" data-bind="text-0:23" style="left:24.689966178128522%;top:64.64%;width:7.440811724915446%;height:3.52%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.029312288613303cqw;color:#76a781;text-align:left;">£9.2</div><div class="n photo" style="left:32.91995490417137%;top:60.0%;width:19.052987598647125%;height:22.65921787709497%;border-radius:0.0cqw;"><img data-asset-slot="dish-4" src="{{dish_4_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n photo" style="left:15.89627959413754%;top:68.8%;width:20.180383314543406%;height:29.73551912568306%;border-radius:0.0cqw;"><img data-asset-slot="dish-5" src="{{dish_5_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:26" style="left:9.357384441939121%;top:76.64%;width:9.92108229988726%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.4656144306651635cqw;color:#65564e;text-align:left;">Chocolate</div><div class="n text" data-bind="text-0:27" style="left:9.470124013528748%;top:79.84%;width:7.7790304396843295%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.6910935738444193cqw;color:#65564e;text-align:left;">巧克力</div><div class="n text" data-bind="text-0:28" style="left:9.582863585118377%;top:84.0%;width:7.215332581736189%;height:3.6799999999999997%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.029312288613303cqw;color:#76a781;text-align:left;">£9.2</div><div class="n text" data-bind="text-0:29" style="left:53.10033821871477%;top:4.32%;width:20.293122886133034%;height:15.040000000000001%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:4.3968432919954905cqw;color:#edafb7;text-align:left;">Lucky
Coffee</div><div class="n text" data-bind="text-0:30" style="left:71.47688838782412%;top:7.68%;width:13.416009019165728%;height:10.879999999999999%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.1567080045095826cqw;color:#79ad88;text-align:center;">牛马
口服液</div><div class="n photo" style="left:85.56933483652762%;top:3.84%;width:10.033821871476889%;height:16.77782178217822%;border-radius:0.0cqw;"><img data-asset-slot="dish-6" src="{{dish_6_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:32" style="left:55.58060879368658%;top:22.24%;width:17.925591882750847%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Orange C Americano</div><div class="n text" data-bind="text-0:33" style="left:55.58060879368658%;top:24.959999999999997%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">橙C美式</div><div class="n text" data-bind="text-0:34" style="left:68.5456595264938%;top:24.959999999999997%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:35" style="left:55.58060879368658%;top:28.16%;width:17.925591882750847%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Grape Americano</div><div class="n text" data-bind="text-0:36" style="left:55.58060879368658%;top:30.880000000000003%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">葡你没事</div><div class="n text" data-bind="text-0:37" style="left:68.5456595264938%;top:30.880000000000003%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:38" style="left:55.58060879368658%;top:34.08%;width:18.1510710259301%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.2965050732807215cqw;color:#625e50;text-align:left;">Green Grape Americano</div><div class="n text" data-bind="text-0:39" style="left:55.58060879368658%;top:36.8%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">人间青醒</div><div class="n text" data-bind="text-0:40" style="left:68.5456595264938%;top:36.8%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:41" style="left:55.58060879368658%;top:40.0%;width:18.26381059751973%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.33032694475761cqw;color:#625e50;text-align:left;">Strawberry Americano</div><div class="n text" data-bind="text-0:42" style="left:55.58060879368658%;top:42.72%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">莓有心事</div><div class="n text" data-bind="text-0:43" style="left:68.5456595264938%;top:42.72%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:44" style="left:55.58060879368658%;top:45.92%;width:17.925591882750847%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Lychee Americano</div><div class="n text" data-bind="text-0:45" style="left:55.58060879368658%;top:48.64%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">理智没事</div><div class="n text" data-bind="text-0:46" style="left:68.5456595264938%;top:48.64%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:47" style="left:55.58060879368658%;top:51.839999999999996%;width:18.038331454340472%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Pineapple Americano</div><div class="n text" data-bind="text-0:48" style="left:55.58060879368658%;top:54.559999999999995%;width:11.61217587373168%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">喂，凤梨</div><div class="n text" data-bind="text-0:49" style="left:68.5456595264938%;top:54.559999999999995%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:50" style="left:75.19729425028186%;top:22.24%;width:19.165727170236753%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.33032694475761cqw;color:#625e50;text-align:left;">Green Apple Americano</div><div class="n text" data-bind="text-0:51" style="left:75.19729425028186%;top:24.959999999999997%;width:12.62683201803833%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">青苹果美式</div><div class="n text" data-bind="text-0:52" style="left:89.62795941375423%;top:24.959999999999997%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:53" style="left:75.19729425028186%;top:28.16%;width:19.165727170236753%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Guava Americano</div><div class="n text" data-bind="text-0:54" style="left:75.19729425028186%;top:30.880000000000003%;width:12.62683201803833%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">芭乐美式</div><div class="n text" data-bind="text-0:55" style="left:89.62795941375423%;top:30.880000000000003%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£5.5</div><div class="n text" data-bind="text-0:56" style="left:75.19729425028186%;top:34.08%;width:19.165727170236753%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Latte  Iced/Hot</div><div class="n text" data-bind="text-0:57" style="left:75.19729425028186%;top:36.8%;width:12.62683201803833%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">拿捏</div><div class="n text" data-bind="text-0:58" style="left:89.62795941375423%;top:36.8%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£4.0</div><div class="n text" data-bind="text-0:59" style="left:75.19729425028186%;top:40.0%;width:19.165727170236753%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Americano  Iced/Hot</div><div class="n text" data-bind="text-0:60" style="left:75.19729425028186%;top:42.72%;width:12.62683201803833%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">没事</div><div class="n text" data-bind="text-0:61" style="left:89.62795941375423%;top:42.72%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£3.2</div><div class="n text" data-bind="text-0:62" style="left:75.19729425028186%;top:45.6%;width:19.39120631341601%;height:2.4%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.1837655016910935cqw;color:#625e50;text-align:left;">Ice Cream Coconut Latte</div><div class="n text" data-bind="text-0:63" style="left:75.19729425028186%;top:48.64%;width:13.641488162344984%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5219842164599773cqw;color:#625e50;text-align:left;">冰淇淋椰椰拿铁</div><div class="n text" data-bind="text-0:64" style="left:89.62795941375423%;top:48.64%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£6.0</div><div class="n text" data-bind="text-0:65" style="left:75.19729425028186%;top:51.839999999999996%;width:19.165727170236753%;height:2.7199999999999998%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.3528748590755355cqw;color:#625e50;text-align:left;">Tiramisu Latte</div><div class="n text" data-bind="text-0:66" style="left:75.19729425028186%;top:54.559999999999995%;width:13.528748590755354%;height:3.04%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#625e50;text-align:left;">提拉米苏拿铁</div><div class="n text" data-bind="text-0:67" style="left:89.62795941375423%;top:54.559999999999995%;width:4.3968432919954905%;height:3.04%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79ab87;text-align:right;">£6.0</div><div class="n text" data-bind="text-0:68" style="left:53.43855693348365%;top:64.0%;width:17.36189402480271%;height:5.4399999999999995%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.494926719278467cqw;color:#6aa56d;text-align:left;">Rice Ball</div><div class="n text" data-bind="text-0:69" style="left:69.67305524239008%;top:64.96%;width:7.666290868094701%;height:4.32%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.818489289740699cqw;color:#efb7bd;text-align:left;">With</div><div class="n text" data-bind="text-0:70" style="left:53.43855693348365%;top:69.12%;width:27.73393461104848%;height:5.76%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:3.3821871476888385cqw;color:#6aa56d;text-align:left;">Cheese Cream</div><div class="n text" data-bind="text-0:71" style="left:78.24126268320181%;top:63.04%;width:17.023675310033823%;height:7.199999999999999%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.9458850056369785cqw;color:#70a773;text-align:left;">奶怪丸子</div><div class="n photo" style="left:80.15783540022548%;top:70.88%;width:15.219842164599775%;height:23.935135135135134%;border-radius:0.0cqw;"><img data-asset-slot="dish-7" src="{{dish_7_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-0:73" style="left:55.01691093573844%;top:75.84%;width:9.582863585118377%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">Original</div><div class="n text" data-bind="text-0:74" style="left:55.01691093573844%;top:78.88%;width:5.975197294250282%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">原味</div><div class="n text" data-bind="text-0:75" style="left:62.119503945885%;top:78.88%;width:4.284103720405862%;height:3.2%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79a47a;text-align:right;">£4.8</div><div class="n text" data-bind="text-0:76" style="left:68.65839909808342%;top:75.84%;width:9.470124013528748%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">Matcha</div><div class="n text" data-bind="text-0:77" style="left:68.65839909808342%;top:78.88%;width:4.96054114994363%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">抹茶</div><div class="n text" data-bind="text-0:78" style="left:74.97181510710259%;top:78.88%;width:4.1713641488162345%;height:3.2%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79a47a;text-align:right;">£5.2</div><div class="n text" data-bind="text-0:79" style="left:55.01691093573844%;top:82.56%;width:11.837655016910936%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">Chocolate</div><div class="n text" data-bind="text-0:80" style="left:55.01691093573844%;top:85.6%;width:5.975197294250282%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">巧克力</div><div class="n text" data-bind="text-0:81" style="left:62.119503945885%;top:85.6%;width:4.284103720405862%;height:3.2%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79a47a;text-align:right;">£5.0</div><div class="n text" data-bind="text-0:82" style="left:68.65839909808342%;top:82.56%;width:9.470124013528748%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">Oreo</div><div class="n text" data-bind="text-0:83" style="left:68.65839909808342%;top:85.6%;width:5.2987598647125145%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">奥利奥</div><div class="n text" data-bind="text-0:84" style="left:74.97181510710259%;top:85.6%;width:4.1713641488162345%;height:3.2%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79a47a;text-align:right;">£5.2</div><div class="n text" data-bind="text-0:85" style="left:60.20293122886133%;top:89.28%;width:12.514092446448705%;height:2.88%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">Tiramisu</div><div class="n text" data-bind="text-0:86" style="left:60.20293122886133%;top:92.32000000000001%;width:8.117249154453212%;height:3.2%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.5783540022547913cqw;color:#627550;text-align:left;">提拉米苏</div><div class="n text" data-bind="text-0:87" style="left:69.56031567080045%;top:92.32000000000001%;width:4.3968432919954905%;height:3.2%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:1.5783540022547913cqw;color:#79a47a;text-align:right;">£5.0</div><div class="n path" data-node="0:88" style="left:4.96054114994363%;top:24.64%;width:3.494926719278467%;height:5.76%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M50 4 L50 96 M5 25 L95 75 M5 75 L95 25 M36 10 L50 23 L64 10 M36 90 L50 77 L64 90" fill="none" stroke="#fffbea" stroke-width="5" stroke-linecap="round"/></svg></div><div class="n path" data-node="0:89" style="left:39.120631341600905%;top:87.83999999999999%;width:9.019165727170236%;height:6.72%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M3 93 C24 25 80 3 69 56 C63 92 41 54 65 28 C76 15 90 13 98 17 M6 99 C29 43 69 12 58 55" fill="none" stroke="#fff7e6" stroke-width="3" stroke-linecap="round"/></svg></div><div class="n path" data-node="0:90" style="left:47.23788049605411%;top:53.92%;width:6.087936865839909%;height:5.92%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M9 65 C35 57 71 7 89 13 C106 22 67 45 35 54 C0 52 0 75 16 88 C30 99 45 75 35 54" fill="none" stroke="#e1edb4" stroke-width="4" stroke-linecap="round"/></svg></div></main><div class="break"></div><main class="panel" data-width="887" data-height="632" style="aspect-ratio:887/632;background:#fffbe7"><svg class="n" width="100%" height="100%" style="opacity:0.055;pointer-events:none"><filter id="noise1"><feTurbulence type="fractalNoise" baseFrequency=".67 .19" numOctaves="3" seed="9"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#noise1)"/></svg><div class="n shape" data-node="1:0" style="left:0.0%;top:0.0%;width:16.910935738444195%;height:100.0%;background:#efb8bd;border-radius:0;border:none;"></div><div class="n shape" data-node="1:1" style="left:18.714768883878243%;top:75.63291139240506%;width:80.04509582863585%;height:22.468354430379748%;background:repeating-linear-gradient(90deg,#dcebc9 0px,#dcebc9 15px,#cce2bd 15px,#cce2bd 29px);border-radius:0;border:none;"></div><div class="n text" data-bind="text-1:2" style="left:2.254791431792559%;top:4.430379746835443%;width:12.401352874859075%;height:5.8544303797468356%;font-family:&quot;Brush Script MT&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.3821871476888385cqw;color:#fffbe7;text-align:center;">Lucky</div><div class="n text" data-bind="text-1:3" style="left:2.705749718151071%;top:11.39240506329114%;width:11.499436302142051%;height:4.430379746835443%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.367531003382187cqw;color:#fffbe7;text-align:center;">喝碗糖水</div><div class="n text" data-bind="text-1:4" style="left:4.6223224351747465%;top:20.569620253164558%;width:7.891770011273957%;height:53.32278481012658%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:3.8331454340473505cqw;color:#fffbe7;text-align:center;">喝
碗
糖
水
顺
风
顺
水</div><div class="n text" data-bind="text-1:5" style="left:2.142051860202931%;top:82.75316455696202%;width:12.62683201803833%;height:11.708860759493671%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:center;">All Sweet Soup
With Brown Sugar
Coconut Milk
Fresh Milk
Milk tea</div><div class="n text" data-bind="text-1:6" style="left:20.180383314543406%;top:4.746835443037975%;width:20.9695603156708%;height:8.069620253164556%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.593010146561443cqw;color:#e6a5ad;text-align:left;">Tofu Pudding
Sweet Soup</div><div class="n text" data-bind="text-1:7" style="left:36.865839909808344%;top:4.588607594936709%;width:6.426155580608793%;height:9.018987341772151%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.818489289740699cqw;color:#80b78e;text-align:center;">富贵
豆花</div><div class="n photo" style="left:42.16459977452086%;top:7.9113924050632916%;width:16.459977452085685%;height:16.972358563678636%;border-radius:0.0cqw;"><img data-asset-slot="dish-8" src="{{dish_8_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-1:9" style="left:20.293122886133034%;top:13.924050632911392%;width:21.42051860202931%;height:4.588607594936709%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Pure Tofu Pudding
with Osmanthus Honey</div><div class="n text" data-bind="text-1:10" style="left:20.293122886133034%;top:18.670886075949365%;width:15.332581736189402%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">桂花蜂蜜豆花</div><div class="n text" data-bind="text-1:11" style="left:36.41488162344983%;top:18.670886075949365%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£5.88</div><div class="n text" data-bind="text-1:12" style="left:20.293122886133034%;top:21.518987341772153%;width:21.307779030439683%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Tofu Pudding, Red bean, Taro ball</div><div class="n text" data-bind="text-1:13" style="left:20.293122886133034%;top:24.050632911392405%;width:15.44532130777903%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">红豆芋圆豆花</div><div class="n text" data-bind="text-1:14" style="left:36.52762119503946%;top:24.050632911392405%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.99</div><div class="n text" data-bind="text-1:15" style="left:20.293122886133034%;top:27.056962025316455%;width:34.72378804960542%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Tofu Pudding, Rice Ball, Sweet Fermented Rice</div><div class="n text" data-bind="text-1:16" style="left:20.293122886133034%;top:29.746835443037973%;width:27.50845546786922%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">酒酿丸子豆花</div><div class="n text" data-bind="text-1:17" style="left:50.3945885005637%;top:29.746835443037973%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.99</div><div class="n text" data-bind="text-1:18" style="left:20.293122886133034%;top:32.75316455696203%;width:34.83652762119504%;height:4.430379746835443%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Tofu Pudding, Red bean, Egg Pudding,
Grass Jelly, White Tapioca</div><div class="n text" data-bind="text-1:19" style="left:20.293122886133034%;top:37.5%;width:27.62119503945885%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">豆花、红豆、布丁、仙草、白珍珠</div><div class="n text" data-bind="text-1:20" style="left:50.3945885005637%;top:37.5%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£8.99</div><div class="n text" data-bind="text-1:21" style="left:20.293122886133034%;top:40.50632911392405%;width:35.062006764374296%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Tofu Pudding, Rice ball, Pandan Jelly, Osmanthus Jelly</div><div class="n text" data-bind="text-1:22" style="left:20.293122886133034%;top:43.196202531645575%;width:27.62119503945885%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">豆花、丸子、斑斓冻、桂花冻</div><div class="n text" data-bind="text-1:23" style="left:50.3945885005637%;top:43.196202531645575%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£9.20</div><div class="n text" data-bind="text-1:24" style="left:20.293122886133034%;top:46.20253164556962%;width:35.062006764374296%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Tofu Pudding, Sago, Red bean, Mashed Taro, Taro ball</div><div class="n text" data-bind="text-1:25" style="left:20.293122886133034%;top:48.892405063291136%;width:27.62119503945885%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">豆花、西米、红豆、芋泥、芋圆</div><div class="n text" data-bind="text-1:26" style="left:50.3945885005637%;top:48.892405063291136%;width:4.735062006764374%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£9.50</div><div class="n text" data-bind="text-1:27" style="left:61.668545659526494%;top:5.2215189873417724%;width:14.092446448703495%;height:9.49367088607595%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.593010146561443cqw;color:#e6a5ad;text-align:left;">Grass
Jelly Soup</div><div class="n text" data-bind="text-1:28" style="left:75.87373167981961%;top:5.379746835443038%;width:9.92108229988726%;height:8.38607594936709%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.142051860202931cqw;color:#80b78e;text-align:center;">被迫营业
烧仙草</div><div class="n photo" style="left:84.32919954904172%;top:2.848101265822785%;width:13.641488162344984%;height:15.169182083739047%;border-radius:0.0cqw;"><img data-asset-slot="dish-9" src="{{dish_9_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-1:30" style="left:61.89402480270575%;top:16.930379746835442%;width:19.052987598647125%;height:4.272151898734177%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Egg Pudding, Tapioca,
Red Bean, Coconut Jelly</div><div class="n text" data-bind="text-1:31" style="left:61.89402480270575%;top:21.677215189873415%;width:19.165727170236753%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">布丁、珍珠、红豆、椰果</div><div class="n text" data-bind="text-1:32" style="left:61.89402480270575%;top:24.68354430379747%;width:7.328072153325817%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:left;">£8.99</div><div class="n text" data-bind="text-1:33" style="left:83.0890642615558%;top:16.930379746835442%;width:14.543404735062007%;height:4.272151898734177%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Red bean, Taro Ball,
Ice Cream, sago</div><div class="n text" data-bind="text-1:34" style="left:83.0890642615558%;top:21.677215189873415%;width:14.656144306651633%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">红豆、芋圆、雪糕、西米</div><div class="n text" data-bind="text-1:35" style="left:83.0890642615558%;top:24.68354430379747%;width:7.328072153325817%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:left;">£9.20</div><div class="n text" data-bind="text-1:36" style="left:61.89402480270575%;top:28.79746835443038%;width:19.616685456595263%;height:6.487341772151899%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Sweet Fermented Rice,
Rice Ball, Osmanthus Jelly,
Coconut Pudding</div><div class="n text" data-bind="text-1:37" style="left:61.89402480270575%;top:35.75949367088608%;width:19.616685456595263%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">酒酿、丸子、桂花冻、椰子冻</div><div class="n text" data-bind="text-1:38" style="left:61.89402480270575%;top:38.607594936708864%;width:7.328072153325817%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:left;">£9.50</div><div class="n text" data-bind="text-1:39" style="left:83.0890642615558%;top:28.79746835443038%;width:14.656144306651633%;height:6.487341772151899%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Pandan Jelly,
Red Bean, Rice Ball,
Ice Cream</div><div class="n text" data-bind="text-1:40" style="left:83.0890642615558%;top:35.75949367088608%;width:14.768883878241262%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">斑斓冻、红豆、丸子、雪糕</div><div class="n text" data-bind="text-1:41" style="left:83.0890642615558%;top:38.607594936708864%;width:7.328072153325817%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:left;">£9.50</div><div class="n text" data-bind="text-1:42" style="left:61.668545659526494%;top:42.405063291139236%;width:21.195039458850058%;height:9.81012658227848%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.818489289740699cqw;color:#e6a5ad;text-align:left;">Happy
Mochi Soup</div><div class="n text" data-bind="text-1:43" style="left:77.90304396843291%;top:42.721518987341774%;width:6.426155580608793%;height:9.968354430379748%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.705749718151071cqw;color:#80b78e;text-align:center;">开心
麻薯</div><div class="n photo" style="left:84.10372040586246%;top:42.24683544303797%;width:13.86696730552424%;height:15.569620253164556%;border-radius:0.0cqw;"><img data-asset-slot="dish-10" src="{{dish_10_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-1:45" style="left:61.668545659526494%;top:51.89873417721519%;width:21.645997745208568%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Mochi, Taro Ball, Sweet Soup</div><div class="n text" data-bind="text-1:46" style="left:61.668545659526494%;top:54.58860759493671%;width:14.768883878241262%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">麻薯、芋圆、糖水</div><div class="n text" data-bind="text-1:47" style="left:77.33934611048478%;top:54.58860759493671%;width:5.186020293122886%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.99</div><div class="n text" data-bind="text-1:48" style="left:61.668545659526494%;top:57.75316455696202%;width:35.963923337091316%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Mochi, Mango, Pomelo, Sago, Ice Cream</div><div class="n text" data-bind="text-1:49" style="left:61.668545659526494%;top:60.28481012658228%;width:28.52311161217587%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">麻薯、芒果、西柚、西米、雪糕</div><div class="n text" data-bind="text-1:50" style="left:92.10822998872604%;top:60.28481012658228%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£8.99</div><div class="n text" data-bind="text-1:51" style="left:61.668545659526494%;top:63.29113924050633%;width:35.963923337091316%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Mochi, Rice Ball, Sweet Fermented-Rice</div><div class="n text" data-bind="text-1:52" style="left:61.668545659526494%;top:65.82278481012658%;width:28.52311161217587%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">麻薯、丸子、酒酿</div><div class="n text" data-bind="text-1:53" style="left:92.10822998872604%;top:65.82278481012658%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.99</div><div class="n text" data-bind="text-1:54" style="left:61.668545659526494%;top:68.82911392405063%;width:35.963923337091316%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Oreo Family, Mochi, Ice Cream, Tapioca</div><div class="n text" data-bind="text-1:55" style="left:61.668545659526494%;top:71.36075949367088%;width:28.52311161217587%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">奥利奥、麻薯、雪糕、珍珠</div><div class="n text" data-bind="text-1:56" style="left:92.10822998872604%;top:71.36075949367088%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£8.88</div><div class="n text" data-bind="text-1:57" style="left:20.180383314543406%;top:52.37341772151899%;width:17.587373167981962%;height:9.49367088607595%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.593010146561443cqw;color:#e6a5ad;text-align:left;">Coconut
Sago Soup</div><div class="n text" data-bind="text-1:58" style="left:33.70913190529876%;top:52.37341772151899%;width:18.1510710259301%;height:4.588607594936709%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:2.818489289740699cqw;color:#80b78e;text-align:left;">椰汁西米露</div><div class="n shape" data-node="1:59" style="left:35.062006764374296%;top:57.27848101265823%;width:7.215332581736189%;height:2.689873417721519%;background:#92bd91;border-radius:45% 34% 43% 28% / 38% 50% 35% 45%;border:none;"></div><div class="n text" data-bind="text-1:60" style="left:35.400225479143174%;top:57.43670886075949%;width:6.538895152198422%;height:2.3734177215189876%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:center;">Iced/Hot</div><div class="n photo" style="left:43.291995490417136%;top:59.96835443037975%;width:15.332581736189402%;height:15.690928270042196%;border-radius:0.0cqw;"><img data-asset-slot="dish-11" src="{{dish_11_url}}" alt="绑定本条菜品的完整照片或透明底素材" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="n text" data-bind="text-1:62" style="left:20.293122886133034%;top:61.07594936708861%;width:22.435174746335964%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Red Bean, Coconut Sago Soup</div><div class="n text" data-bind="text-1:63" style="left:20.293122886133034%;top:63.60759493670886%;width:15.44532130777903%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">红豆椰汁西米露</div><div class="n text" data-bind="text-1:64" style="left:36.64036076662909%;top:63.60759493670886%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£6.88</div><div class="n text" data-bind="text-1:65" style="left:20.293122886133034%;top:66.45569620253164%;width:22.435174746335964%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">Red bean &amp; taro coconut sago</div><div class="n text" data-bind="text-1:66" style="left:20.293122886133034%;top:68.9873417721519%;width:15.44532130777903%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.1837655016910935cqw;color:#52644b;text-align:left;">红豆芋圆椰汁西米露</div><div class="n text" data-bind="text-1:67" style="left:36.64036076662909%;top:68.9873417721519%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.50</div><div class="n text" data-bind="text-1:68" style="left:20.293122886133034%;top:71.83544303797468%;width:16.234498308906424%;height:2.2151898734177213%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#52644b;text-align:left;">Mango coconut sago</div><div class="n text" data-bind="text-1:69" style="left:36.64036076662909%;top:71.83544303797468%;width:5.5242390078917705%;height:2.5316455696202533%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2965050732807215cqw;color:#427653;text-align:right;">£7.20</div><div class="n text" data-bind="text-1:70" style="left:20.293122886133034%;top:77.21518987341773%;width:13.641488162344984%;height:3.79746835443038%;font-family:&quot;Arial Rounded MT Bold&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:700;font-size:2.133032694475761cqw;color:#e6a5ad;text-align:left;">Toppings</div><div class="n text" data-bind="text-1:71" style="left:20.293122886133034%;top:81.64556962025317%;width:13.416009019165728%;height:7.120253164556963%;font-family:&quot;FZZJ-DHTMBKSJF&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.2604284103720407cqw;color:#80b78e;text-align:left;">缤纷小料区
（多加多快乐）</div><div class="n text" data-bind="text-1:72" style="left:20.40586245772266%;top:90.34810126582279%;width:13.19052987598647%;height:4.588607594936709%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.0180383314543404cqw;color:#52644b;text-align:left;">Fresh milk / Soya
换鲜奶/豆奶</div><div class="n text" data-bind="text-1:73" style="left:20.40586245772266%;top:94.9367088607595%;width:8.455467869222097%;height:2.689873417721519%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.4543404735062007cqw;color:#427653;text-align:left;">£0.5</div><div class="n text" data-bind="text-1:74" style="left:36.18940248027058%;top:77.05696202531645%;width:25.817361894024803%;height:3.322784810126582%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.745208568207441cqw;color:#427653;text-align:left;">£0.8</div><div class="n shape" data-node="1:75" style="left:36.076662908680944%;top:80.85443037974683%;width:26.268320180383313%;height:16.455696202531644%;background:#f1ccd0;border-radius:5% 8% 4% 7% / 10% 7% 12% 6%;border:none;"></div><div class="n text" data-bind="text-1:76" style="left:36.865839909808344%;top:81.9620253164557%;width:24.689966178128522%;height:5.379746835443038%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.0146561443066515cqw;color:#52644b;text-align:center;">Popping Pearl · 爆爆珠
Mango, Lychee, Strawberry,
Water Chestnut, Green Apple</div><div class="n text" data-bind="text-1:77" style="left:36.865839909808344%;top:88.4493670886076%;width:12.175873731679818%;height:7.753164556962025%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:0.9582863585118376cqw;color:#52644b;text-align:left;">White Tapioca 白珍珠
Tapioca 珍珠
Grass Jelly 仙草
Green Grape Jelly 葡萄冻</div><div class="n text" data-bind="text-1:78" style="left:49.71815107102593%;top:88.4493670886076%;width:12.063134160090192%;height:7.753164556962025%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:0.9582863585118376cqw;color:#52644b;text-align:left;">Oreo 奥利奥
Cheese Cream 奶盖
Egg Pudding 布丁
Sweet Red Bean 蜜红豆</div><div class="n text" data-bind="text-1:79" style="left:64.71251409244645%;top:77.05696202531645%;width:15.107102593010147%;height:3.322784810126582%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.745208568207441cqw;color:#427653;text-align:left;">£1.0</div><div class="n shape" data-node="1:80" style="left:64.4870349492672%;top:80.85443037974683%;width:15.670800450958286%;height:16.455696202531644%;background:#fffbe7;border-radius:8% 5% 9% 4% / 9% 13% 6% 11%;border:none;"></div><div class="n text" data-bind="text-1:81" style="left:65.2762119503946%;top:82.27848101265823%;width:14.205186020293123%;height:13.765822784810128%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.0146561443066515cqw;color:#52644b;text-align:center;">Tiramisu Cheese Cream
提拉米苏奶盖
Matcha Cheese Cream
抹茶奶盖
Mini Taro ball 小芋圆
Sago 西米 · Mochi 麻薯
Ice Cream 雪糕</div><div class="n text" data-bind="text-1:82" style="left:82.41262683201805%;top:77.05696202531645%;width:15.107102593010147%;height:3.322784810126582%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.745208568207441cqw;color:#427653;text-align:left;">£1.2</div><div class="n shape" data-node="1:83" style="left:82.2998872604284%;top:80.85443037974683%;width:15.219842164599775%;height:16.455696202531644%;background:#e8efbd;border-radius:8% 5% 7% 10% / 12% 7% 10% 6%;border:none;"></div><div class="n text" data-bind="text-1:84" style="left:83.0890642615558%;top:82.27848101265823%;width:13.641488162344984%;height:13.765822784810128%;font-family:&quot;Source Han Sans SC&quot;,&quot;Source Han Sans SC&quot;,sans-serif;font-weight:400;font-size:1.0146561443066515cqw;color:#52644b;text-align:center;">Osmanthus Jelly 桂花冻
Coconut Pudding 椰子冻
Pandan Jelly 斑斓冻
Tofu Pudding 豆花
Taro ball 大芋圆
Rice Ball 小丸子</div><div class="n path" data-node="1:85" style="left:40.58624577226607%;top:23.259493670886076%;width:2.705749718151071%;height:3.0063291139240507%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M5 85 Q42 77 41 48 Q40 25 69 21 L92 12 M72 8 L93 12 L87 35" fill="none" stroke="#5d6655" stroke-width="5" stroke-linecap="round"/></svg></div><div class="n path" data-node="1:86" style="left:81.28523111612176%;top:51.89873417721519%;width:2.705749718151071%;height:3.1645569620253164%;"><svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M8 90 Q29 40 90 28 M66 10 L91 28 L70 49" fill="none" stroke="#5d6655" stroke-width="5" stroke-linecap="round"/></svg></div></main></section>
```

### 验证与适配边界

验证覆盖完整组合的字体、配色、背景／卡片、图片／素材、文字归属及安全区，不能用骨架或字体样张单独代表通过。完整组合评审不等于像素级字标复刻，也不等于已完成印刷校样。参考照片分辨率、独立抠图、准确商标及复杂纸纤维仍依赖正式资产；正式交付需检查长菜名、价格宽度、实际物理尺寸下字号和安全区。


修订约束（2026-09-13）：字标与椭圆标分离保护；加料区按卡片内实际文字边界验收，禁止内容底边越出卡片。887px参考画布中加料正文8.5–9px仅用于该信息密度，转印刷或手机时重新排版，不直接等比缩小。

<a id="combination.menu-warm-korean"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 暖木招牌场景与分类陈列菜单

风格标签：一级：自然质朴风。

**产物／载体候选**：产物：菜单多页；载体：横版册页；用途：餐厅分类点单。这些为适用条件，不改变 Brief 已锁定的产物；社媒长图／详情页单屏只可借局部图文关系，必须重排，不自动把菜单单页串成详情页。

**范围与证据**：上下两块独立横向菜单：约y28–628、y655–1252；黑色展示底与间隔排除。比例与色值为从参考估计的实现起点。此组合为布局与配色结构实现；原品牌、艺术字、实拍材质不声明已复刻。

### 设计关系与安全区

- 背景／卡片：第一面左满栏牛肉场景＋右纸纹共底；上品牌横条有摄影材质，分类货架局部有木质承托。第二面纸纹满幅，分类分隔线贯穿。
- 图片／素材：第一面左主菜明显大于右条目；右四大必点为器皿陈列、六必吃为矩形摄影、汤锅为独立碗图。第二面上方开放器皿图鉴，下方小吃/拌饭独立图窗，两种图片边界不能合并。
- 文字归属：章节编号和宋体分类题引导；木质货架上小价格牌分别归菜；图窗底部窄色条为菜名价格，开放锅具旁为侧注。避免所有文本固定在图上方。
- 空间参数：第一面左约33%场景，右分类4/3/3列由不同菜组决定；第二面上方4列器皿、下方两分类各3列图窗。使用现有菜单规范 MN-S10 的实质关系。
- 安全区：页边2%–3%估计；锅柄、托盘和器皿完整保留；主视觉图像文字位于上方净空而非覆盖肉面；价格小牌有内边距，条目窄色条需容纳完整价格；长菜名加高标签区。
- 纹理／渐变：牛肉场景的暗化/木纹属于摄影；页底是纸纤维，不把照片的木纹扩展到全部列表底。

### 配色、字体与资产

纸白 #f6efdf；暖棕 #63442d；木色 #815333；推荐朱红只局部。

章节为中等衬线/宋体，候选 Songti SC 400/700；拉丁点缀 Baskerville 400 Italic；功能价名 Source Han Sans 400，价格 Arial 400/700。主标题与品牌字形须分别核验。

完整牛肉环境图、透明器皿图、独立小菜照片、真实木质货架和品牌资产；程序棕条只能示意承托而非真实木纹。

### 复用与内容适配

纸底按需引用 [轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)；纹理独立于准确内容层，示例稀疏点纹仅为位置检查，不算真实纸纤维验证。共用 [图像主场](../layouts/hero-focus.md#layout.image-stage)、[拼贴](../layouts/overlap-and-collage.md#layout.collage)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid) 的对应关系。品类内容与计价沿用 [菜单规范](../../../../references/style/coding/scenarios/menu-spec.md)，不得以模板演示文字生成营业事实。

参考的艺术标题、版式拓扑与功能字体分开核对；模板中的宋体／Arial是可读占位。照片自带价格、商标或说明时不得在其上再叠不同数字。本库只保留实现代码，不打包参考图。


### 本轮版式校正

**独立画布**：844×600；828×597（参考有效区域的像素比例，不是毫米印刷尺寸）。展示板的上下拼接不属于菜单内部。

第一面左主视觉、右4/3/3分类；第二面上方器皿在列间有高度错落，图注按图左/图右交替放置，下方左右各一分类照片矩阵。开放图鉴、独立照片和木质承托三种关系分别实现。

几何优先绑定节点坐标与父画布宽高；正文超出净空时应重新分配该条目、分类或页面，而不是让容器自动撑长改变横版比例。375px只是缩图检查，不能视为手机可读性通过。当前为原图关系约束下的固定画布骨架，参考中细小营业文案未转录。

### CSS 组合实现

下列按参考有效画布保留关键位置；资源路径为真实菜品/品牌/场景槽位，不含参考图片。源码中的left/top/width/height为父画布百分比。生产遵循原有HTML行内化和字体协议。

```css
.vl-menu-warm-korean *{box-sizing:border-box}.vl-menu-warm-korean{position:relative;container-type:inline-size;width:100%;overflow:hidden;background:var(--paper,#f7efdc);color:var(--ink,#67472c);font-synthesis:none}.vl-menu-warm-korean .node{position:absolute}.vl-menu-warm-korean .text{margin:0;line-height:1.17;overflow-wrap:normal}.vl-menu-warm-korean .photo{position:absolute;overflow:hidden}.vl-menu-warm-korean .title{font-family:"Songti SC";font-weight:700}.vl-menu-warm-korean .price{white-space:nowrap}.vl-menu-warm-korean .label{background:#f9efdc;border:1px solid #b5976c;text-align:center;padding:.35cqw}.vl-menu-warm-korean .panel-gap{padding:12px;font-size:13px;color:#555}.vl-menu-warm-korean .caption{font-size:1.7cqw}.vl-menu-warm-korean .shape{position:absolute;width:100%;height:100%;inset:0;z-index:0}.vl-menu-warm-korean .sheet-notice{padding:12px;font-size:13px}.vl-menu-warm-korean .cutout-fixture{clip-path:polygon(25% 0,65% 0,90% 20%,100% 50%,90% 85%,60% 100%,20% 90%,0 60%,5% 30%)}.vl-menu-warm-korean .section-rule{border-bottom:1px solid #a99571}.vl-menu-warm-korean .brand{font-family:Baskerville,serif}.vl-menu-warm-korean .compare-note{margin:14px;font-size:14px}
```

```html
<main class="vl-menu-warm-korean korean-a" data-width="844" data-height="600" style="aspect-ratio:844/600;--paper:#f6efdf;--ink:#63442d"><div class="node " style="left:0.0%;top:0.0%;width:33.41232227488152%;height:100.0%;background:#7c684a" ></div><div class="node photo source-hero" style="left:0.0%;top:0.0%;width:33.41232227488152%;height:99.66666666666667%;"><img src="dish-1.png" data-asset-slot="dish-1" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:34.59715639810427%;top:0.0%;width:64.0995260663507%;height:9.166666666666666%;border-radius:0 0 15px 15px;background:#65432e" ></div><div class="node text " style="left:36.25592417061612%;top:2.666666666666667%;width:61.25592417061612%;height:5.666666666666666%;font-size:3.080568720379147cqw;font-weight:400;text-align:left;color:#fff5dc;font-family:Songti SC;" >品味料理 · 分类菜单</div><div class="node text section-rule" style="left:35.18957345971564%;top:12.5%;width:62.44075829383886%;height:4.833333333333333%;font-size:2.843601895734597cqw;font-weight:400;text-align:left;font-family:Songti SC;" >01 四大必点</div><div class="node text section-rule" style="left:35.18957345971564%;top:39.33333333333333%;width:62.44075829383886%;height:4.833333333333333%;font-size:2.843601895734597cqw;font-weight:400;text-align:left;font-family:Songti SC;" >02 六个必吃</div><div class="node text section-rule" style="left:35.18957345971564%;top:78.66666666666666%;width:62.44075829383886%;height:4.833333333333333%;font-size:2.843601895734597cqw;font-weight:400;text-align:left;font-family:Songti SC;" >03 汤锅料理</div><div class="node " style="left:34.952606635071085%;top:31.333333333333336%;width:63.74407582938388%;height:4.333333333333334%;background:linear-gradient(#a5774a,#714624)" ></div><div class="node photo " style="left:36.018957345971565%;top:18.0%;width:14.099526066350712%;height:14.143442622950818%;"><img src="dish-2.png" data-asset-slot="dish-2" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:36.25592417061612%;top:31.166666666666664%;width:13.744075829383887%;height:3.0%;background:#f5e8ca" ></div><div class="node text " style="left:36.492890995260666%;top:31.666666666666664%;width:13.270142180094787%;height:2.5%;font-size:1.3033175355450237cqw;font-weight:400;text-align:center;" >对应菜名 —</div><div class="node photo " style="left:51.54028436018957%;top:18.0%;width:14.099526066350712%;height:13.608272506082725%;"><img src="dish-3.png" data-asset-slot="dish-3" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:51.77725118483413%;top:31.166666666666664%;width:13.744075829383887%;height:3.0%;background:#f5e8ca" ></div><div class="node text " style="left:52.014218009478675%;top:31.666666666666664%;width:13.270142180094787%;height:2.5%;font-size:1.3033175355450237cqw;font-weight:400;text-align:center;" >对应菜名 —</div><div class="node photo " style="left:67.06161137440758%;top:18.0%;width:14.099526066350712%;height:13.052706552706553%;"><img src="dish-4.png" data-asset-slot="dish-4" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:67.29857819905213%;top:31.166666666666664%;width:13.744075829383887%;height:3.0%;background:#f5e8ca" ></div><div class="node text " style="left:67.53554502369668%;top:31.666666666666664%;width:13.270142180094787%;height:2.5%;font-size:1.3033175355450237cqw;font-weight:400;text-align:center;" >对应菜名 —</div><div class="node photo " style="left:82.58293838862559%;top:18.0%;width:14.099526066350712%;height:13.718055555555555%;"><img src="dish-5.png" data-asset-slot="dish-5" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:82.81990521327015%;top:31.166666666666664%;width:13.744075829383887%;height:3.0%;background:#f5e8ca" ></div><div class="node text " style="left:83.0568720379147%;top:31.666666666666664%;width:13.270142180094787%;height:2.5%;font-size:1.3033175355450237cqw;font-weight:400;text-align:center;" >对应菜名 —</div><div class="node photo " style="left:35.18957345971564%;top:45.0%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-6.png" data-asset-slot="dish-6" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:35.18957345971564%;top:57.99999999999999%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:35.66350710900474%;top:58.5%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:56.39810426540285%;top:45.0%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-7.png" data-asset-slot="dish-7" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:56.39810426540285%;top:57.99999999999999%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:56.872037914691944%;top:58.5%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:77.60663507109004%;top:45.0%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-8.png" data-asset-slot="dish-8" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:77.60663507109004%;top:57.99999999999999%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:78.08056872037915%;top:58.5%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:35.18957345971564%;top:61.66666666666667%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-9.png" data-asset-slot="dish-9" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:35.18957345971564%;top:74.66666666666667%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:35.66350710900474%;top:75.16666666666667%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:56.39810426540285%;top:61.66666666666667%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-10.png" data-asset-slot="dish-10" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:56.39810426540285%;top:74.66666666666667%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:56.872037914691944%;top:75.16666666666667%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:77.60663507109004%;top:61.66666666666667%;width:20.14218009478673%;height:13.333333333333334%;"><img src="dish-11.png" data-asset-slot="dish-11" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:77.60663507109004%;top:74.66666666666667%;width:20.14218009478673%;height:3.3333333333333335%;background:#79573b" ></div><div class="node text " style="left:78.08056872037915%;top:75.16666666666667%;width:19.194312796208532%;height:3.0%;font-size:1.3033175355450237cqw;font-weight:400;text-align:left;color:#fff8eb;" >对应菜名      —</div><div class="node photo " style="left:36.37440758293839%;top:85.83333333333333%;width:13.38862559241706%;height:13.858490566037734%;"><img src="dish-12.png" data-asset-slot="dish-12" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:50.0%;top:87.83333333333333%;width:6.753554502369669%;height:7.5%;font-size:1.4218009478672986cqw;font-weight:400;text-align:left;" >汤锅<br>—</div><div class="node photo " style="left:57.58293838862559%;top:85.83333333333333%;width:13.38862559241706%;height:13.064564564564565%;"><img src="dish-13.png" data-asset-slot="dish-13" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:71.2085308056872%;top:87.83333333333333%;width:6.753554502369669%;height:7.5%;font-size:1.4218009478672986cqw;font-weight:400;text-align:left;" >汤锅<br>—</div><div class="node photo " style="left:78.7914691943128%;top:85.83333333333333%;width:13.38862559241706%;height:12.947916666666668%;"><img src="dish-14.png" data-asset-slot="dish-14" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:92.41706161137441%;top:87.83333333333333%;width:6.753554502369669%;height:7.5%;font-size:1.4218009478672986cqw;font-weight:400;text-align:left;" >汤锅<br>—</div></main><div class="panel-gap">独立菜单第2面</div><main class="vl-menu-warm-korean korean-b" data-width="828" data-height="597" style="aspect-ratio:828/597;--paper:#f6efdf;--ink:#63442d"><div class="node " style="left:0.0%;top:0.0%;width:100.0%;height:7.537688442211055%;background:#63442d" ></div><div class="node text " style="left:2.898550724637681%;top:1.675041876046901%;width:94.44444444444444%;height:4.522613065326634%;font-size:3.0193236714975846cqw;font-weight:400;text-align:left;color:#fff5dc;font-family:Songti SC;" >分类点单 · 韩式料理</div><div class="node text section-rule" style="left:0.966183574879227%;top:9.715242881072026%;width:97.82608695652173%;height:5.025125628140704%;font-size:2.898550724637681cqw;font-weight:400;text-align:left;font-family:Songti SC;" >04 传统韩料类</div><div class="node photo " style="left:1.2077294685990339%;top:16.750418760469014%;width:18.115942028985508%;height:17.664077965585502%;"><img src="dish-15.png" data-asset-slot="dish-15" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:19.806763285024154%;top:20.100502512562816%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:31.280193236714975%;top:18.76046901172529%;width:18.115942028985508%;height:17.89770771666552%;"><img src="dish-16.png" data-asset-slot="dish-16" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:26.207729468599034%;top:22.110552763819097%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:51.20772946859904%;top:16.750418760469014%;width:18.115942028985508%;height:17.08542713567839%;"><img src="dish-17.png" data-asset-slot="dish-17" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:69.80676328502415%;top:20.100502512562816%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:81.28019323671496%;top:18.76046901172529%;width:18.115942028985508%;height:17.899957302854137%;"><img src="dish-18.png" data-asset-slot="dish-18" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:76.20772946859904%;top:22.110552763819097%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:1.2077294685990339%;top:38.69346733668342%;width:18.115942028985508%;height:13.691210543736648%;"><img src="dish-19.png" data-asset-slot="dish-19" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:19.806763285024154%;top:42.04355108877722%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:31.280193236714975%;top:40.7035175879397%;width:18.115942028985508%;height:15.414495791842647%;"><img src="dish-20.png" data-asset-slot="dish-20" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:26.207729468599034%;top:44.0536013400335%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:51.20772946859904%;top:38.69346733668342%;width:18.115942028985508%;height:16.356952547974775%;"><img src="dish-21.png" data-asset-slot="dish-21" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:69.80676328502415%;top:42.04355108877722%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node photo " style="left:81.28019323671496%;top:40.7035175879397%;width:18.115942028985508%;height:15.389447236180903%;"><img src="dish-22.png" data-asset-slot="dish-22" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node text " style="left:76.20772946859904%;top:44.0536013400335%;width:5.434782608695652%;height:12.227805695142377%;font-size:1.4492753623188406cqw;font-weight:400;text-align:left;" >对应<br>料理<br>—</div><div class="node text section-rule" style="left:0.966183574879227%;top:57.6214405360134%;width:47.70531400966183%;height:5.025125628140704%;font-size:2.898550724637681cqw;font-weight:400;text-align:left;font-family:Songti SC;" >05 韩式小吃</div><div class="node text section-rule" style="left:50.84541062801933%;top:57.6214405360134%;width:47.70531400966183%;height:5.025125628140704%;font-size:2.898550724637681cqw;font-weight:400;text-align:left;font-family:Songti SC;" >06 经典拌饭</div><div class="node photo " style="left:0.966183574879227%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-23.png" data-asset-slot="dish-23" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:0.966183574879227%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:1.328502415458937%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:17.51207729468599%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-24.png" data-asset-slot="dish-24" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:17.51207729468599%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:17.874396135265698%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:34.05797101449276%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-25.png" data-asset-slot="dish-25" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:34.05797101449276%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:34.42028985507246%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:50.60386473429952%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-26.png" data-asset-slot="dish-26" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:50.60386473429952%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:50.96618357487923%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:67.14975845410628%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-27.png" data-asset-slot="dish-27" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:67.14975845410628%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:67.512077294686%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:83.69565217391305%;top:64.321608040201%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-28.png" data-asset-slot="dish-28" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:83.69565217391305%;top:77.72194304857621%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:84.05797101449275%;top:78.22445561139028%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:0.966183574879227%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-29.png" data-asset-slot="dish-29" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:0.966183574879227%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:1.328502415458937%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:17.51207729468599%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-30.png" data-asset-slot="dish-30" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:17.51207729468599%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:17.874396135265698%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:34.05797101449276%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-31.png" data-asset-slot="dish-31" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:34.05797101449276%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:34.42028985507246%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:50.60386473429952%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-32.png" data-asset-slot="dish-32" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:50.60386473429952%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:50.96618357487923%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:67.14975845410628%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-33.png" data-asset-slot="dish-33" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:67.14975845410628%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:67.512077294686%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div><div class="node photo " style="left:83.69565217391305%;top:81.90954773869346%;width:15.458937198067632%;height:13.721943048576216%;"><img src="dish-34.png" data-asset-slot="dish-34" alt="对应菜品或完整场景，须绑定真实资产" style="display:block;width:100%;height:100%;object-fit:contain"></div><div class="node " style="left:83.69565217391305%;top:95.30988274706867%;width:15.458937198067632%;height:3.350083752093802%;background:#75533c" ></div><div class="node text " style="left:84.05797101449275%;top:95.81239530988275%;width:14.734299516908212%;height:2.680067001675042%;font-size:1.328502415458937cqw;font-weight:400;text-align:left;color:#fff5dc;" >对应菜名  —</div></main>
```

### 验证边界

本轮检查独立画布比例、标题定位、异形轮廓、交错图注与照片等比。原品牌艺术字、精确手写字形、摄影透明边缘与纸/木纹仍属于素材依赖；原图裁片只在内部fixture使用，不能视为整图复刻通过。文字长度/字体改变后需重新测量内容安全区。


<a id="combination.four-zone-imagery"></a>

## 四区影像组合

风格标签：二级：杂志编辑风 / 时尚杂志。

**适用与状态**：粒度：展开组合；适配产物：折页展开视觉、品牌画册。两组展开关系作为一个组合的两种配置；不附折法。 已保存完整展开结构；来源版本记录其原参考关系验证通过，本次使用仍须复核；印刷折法与内外面序仍未确认。 完整组合关系验证通过，素材与精确字形边界见末段；不等于精确字形、素材授权或生产拼版通过。

归属与新增依据：大尺度影像、黑白分区、密疏文字与品牌大字共同形成商业编辑语法；四个视觉区的关系不同于既有纵向植萃长页。

### 提取内容与实现归属

| 提取内容 | CSS类型／处理 |
|---|---|
| 背景、图片、文字的组合内关系 | 布局几何统一引用[四区展开 · 图文穿插](../layouts/fold-full-page.md#layout.fold-four-zone-editorial)；不由通用图文骨架重新生成。 |
| 配色 | 组合内覆盖；视觉近似：白#FFFFFF、黑#080A07为结构底，深绿#34482B为影像基调，浅橄榄#A6BC72用于B末区约1/4；比例随配置变化，灰展示底不采纳。 |
| 字体 | 角色与字形选择见下表；沿用[字体绑定契约](#combination-font-binding)，不新增字体资源索引 |
| 质感／渐变 | 叶片、水面、岩土和柔焦保留在摄影中；不做CSS噪点、玻璃、金属或纸张阴影。 |
| 摄影／插画 | 图片素材槽位；满高环境远景、微距背景、叶片小图、带产品环境图、图表及地图式线图。叠字处留低细节区；产品外观、品牌、图表数据、地图和二维码均须替换授权内容，不复制事实。 |

### 背景、图窗与文字的关系

| 区域 | 归属与约束 |
|---|---|
| A展开 | 4等视觉区；左图文、白编号栏、白底小图接黑底产品区、全黑图文栏；第三和第四区下部同色连续。 |
| B展开 | 远景满高背景＋叠字／白色阅读栏／微距背景＋局部图窗／浅绿索引栏；满高图像不是卡片。 |
| 保护区 | 四栏样本900px宽、单栏225px；普通正文内距22–26px。背景叠字必须有可用净空；小图有自己的焦点与图注。 |

文字描述用于选型；精确几何和色值以本次已验证的布局源与主题源为准，900px展开宽是验证坐标，不是印刷规格。先分清全幅背景与局部图窗：背景可跨面共享，图窗只裁取景，无证据不附加底板、圆角或阴影。真实光照和绘画笔触留在素材内；新增CSS遮光须由实际叠字对比问题触发，不能把整张图片默认压暗。

### 字体与内容适配

保留粗细无衬线对比、细密编辑正文与大品牌字。来源版本的字体绑定见主题源 `--fold-font-*`；字号、行距、列宽见布局源，不沿用旧局部样例参数覆盖母版。字体替换后重查真实face、断行和溢出；原参考具体family未确认。

正文槽位按参考行密度设计；超量内容应明确调整信息分配并重验，不能隐藏、截字或全局缩成微字。窄屏展示按整体画布缩放；响应式重排与生产拼版另行确认。

### 组装起点

读取下方完整源，保留一次主结构；正式输出按目标协议行内化。普通正文组用纵向flow或flex，gap=16–18px、padding=26px仅作样本起点、min-width:0；共享背景与跨区元素归展开共同层，局部图窗保留自身取景边界，不将跨区关系套入单栏flow或面板裁切；背景层独立isolation，图片使用object-fit:cover和经主体核验的object-position，文字不继承图片滤镜。此骨架表达槽位而非来源素材下载地址，先落实槽位再输出成品。



上例只表达 A 的共同背景层：55% 为分界起点，按图文容量校准展开高度和分界；不能为各栏再铺不透明底遮断黑色连续区。B 另按下述关系绑定背景和图窗，不沿用 A 的黑底。基础划为约四个等宽视觉区。A：左区上图下文，第二白底编号说明，第三白底小图接下部产品图，末区全黑配图文；黑底延入第三底部。B：左区满高风景叠大字，第二白底说明与图表，第三微距背景接白色窄区并叠小图，第四浅绿底线图。背景、图窗、文字分别建层。

可变项：标题、正文量、图窗数量与实际资产；固定项为本组合主次、共享背景范围和图文归属。屏幕结构验证允许增高，固定印刷成品不能随文案任意增高或移动折线；超量时调整信息分配或增加页面。折面、出血与开合按[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)绑定，视觉分区不等于物理折面：按展开坐标适配共享背景、局部图窗与文字归属，不按折面机械重切视觉分区；局部复用须保留采用关系，未确认折法不等于布局不可用。

**局部验证与剩余边界**：两配置在900px展开宽渲染，原生文字、局部图片取景与背景层分开；检查基础/加长文案、文字边界、实际字体、背景连续性和无默认投影。源图裁片只用于本次验证，不加入库素材目录、不作为跨任务默认内容。图表、地图式线图与二维码的精确形态未提取；需清晰源图和本次真实数据。微距纹理仅作为摄影资产，不宣称CSS还原。 原参考的品牌、人物、联系方式、产品陈述均不继承；每次真实素材替换后重查主体和文字保护区。

### 完整实现与单面取用

布局：[ 四区展开 · 图文穿插 ](../layouts/fold-full-page.md#layout.fold-four-zone-editorial)。主题源只含 `style[data-fold-theme="botanical"]`，不能单独作为完整页面。先读取本组合和必需布局的模板节点，组合使用布局源的唯一主结构，不再从描述或旧局部骨架重建。

```json
{"dependencies":["layout.fold-four-zone-editorial"]}
```

只换配色／字体／质感时采用同一布局；单面取用按布局中的具名视区坐标及 `layout.fold-panel-view` 保留全局关系。跨栏标题、共享图窗所在面不得裁掉字词后冒充独立单页，需保留展开使用或明确重排。素材槽位保持独立实例；参考摄影、书法与图形资产不包含在主题源中。

<a id="combination.offset-cut-window"></a>

## 错层切角组合

风格标签：二级：奢雅精致风 / 极简精品。

粒度：两幅展开组合；适配折页展开视觉、品牌画册。深浅错层、轻重无衬线、切角实景与细密编辑内容共同定义本组。下列定位、字重和净距包含实测修正，不宣称原简略配方独立通过。原字体身份、原摄影及印刷面序仍未确认。

### 图文关系与依赖

复用[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)、[阅读栏](../layouts/airy-and-spacious.md#layout.reading-column)、[图片主场](../layouts/hero-focus.md#layout.image-stage)、[章节流](../layouts/continuous-flow.md#layout.chapter-flow)。完整几何由[三栏展开 · 错层图窗](../layouts/fold-full-page.md#layout.fold-cut-window)维护；上述通用原子只解释局部关系，不作为替换母版。三主区宽比285:330:285，不等同物理三折面；面序、折线、出血按[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)绑定。

每幅以900×570为验证坐标，来自参考约597×378；不是印刷规格。坐标x/y/w/h均相对所属展开，未指定高度的正文自然流。背景、局部图窗和文字分别建立归属，不把六区变成六张卡。

| 区域 | 背景、图片与文字约束 |
|---|---|
| A左 | 白底；主副题45/39/195，短文45/139/135；室内图50/228/185/225，左上切角。图边的局部深色签只承载短文案，不额外塞头像；小圆印记与正文分占水平空间。 |
| A中 | x=285,w=330，深底延至y=218后硬切白底；室内主图318/78/264/253跨分界，右下切角。栏目在图下约17px，正文接在其下，细线与联系组约从y=443开始；不把标题压进照片。 |
| A右 | 深底；Modern/Interior/Design题组664/114/201，最后一行到照片之间留24–36px净距；室内图669/271/231/299贴右下边，左上切角；竖向细字归独立窄区。 |
| A跨区题注 | 318/26/534，跨中右的细线与微字属于展开共同父层，不挂在中栏后以越界撑到右栏。 |
| B左 | 白底至y=391后硬切深底；新品牌小像33/58/82/123与短文并列；Opening/Soon题组约33/206/219；陈设图35/310/214/205跨分界，右下切角。 |
| B中 | 深底；工作近景339/31/228/193，左上切角；职业题组339/236/241放在照片下。两组头像简介约从y=315、399开始，头像约51×60；头像与简介局部成组，不另加底板。 |
| B右 | 白底；New/Season题组658/29/204；陈设图658/132/181/250，下接约3行说明和小图形说明。中右页脚基线约y=510，以共享对齐关系组织，不靠统一卡高。 |

坐标用于同尺度试排，真实文案替换后重算净距。圆箭头约47px，是与图边校准的独立方向标记，不是未实现的按钮；细线与标记不烘焙进图片。图片单角切入约15%–20%，只切最终取景空场，不能切椅子、沙发、双手或人脸；先核验object-fit与object-position再判断裁切通过。

### 配色、质感、渐变与透明

| 类型 | 本组绑定 |
|---|---|
| 配色 | 白#fff、近黑暖棕#1b150f为大色场，灰褐#a88d74用于轻标题、圆标和细线；照片保留自然暖灰、木色及绿植。参考外部格网纸与展示阴影不入库。 |
| 质感／资产 | 木纹、织物、墙面及窗光由高质量独立照片承担，不加纸纹或落地阴影。室内中远景、陈设、工作手部及人物头像分别绑定职责；不能用客厅替代工作或人物，也不把完整实景降成局部纹理。 |
| 渐变／光场 | 无额外柔化光场。A中和B左只是双色硬分区；可用同位置色标实现，例如linear-gradient(#1b150f 0 218px,#fff 218px)，不在两色之间插透明带。照片自身光照不重复叠黑渐变。 |
| 图片Alpha／表面透明 | 页面、图片和普通文字默认opacity:1，无图片渐隐或父层透明。若换图确有局部叠字对比需求，按通用承托规则重新判断，不让filter、mask或opacity作用于正文。 |

完整组含9个图像槽位：A三处室内图，B新品牌小像、陈设、工作近景、两头像及右陈设。相同室内图、陈设或头像允许有明确同资产复用意图，分别记录取景；不能凭素材现成而向局部色签新增图片。主体图建议不低于1024px短边；本次使用独立生成照片，原参考裁片不进入库素材或默认内容。

### 字体与内容密度

按[字体绑定契约](#combination-font-binding)核验真实face；不能按h1/h2标签给所有标题统一加粗。以下均为900px展开的校准字号，不是跨品类默认或印刷pt值。

| 文字角色 | 本轮字体／字级 |
|---|---|
| Brand、Opening、New等强调主词 | Source Han Sans 700，40–43px，直立粗体 |
| Sale、Soon、Season及Modern等轻副词 | Source Han Sans SC 300，32–40px，直立细体；不描边或投影 |
| Interior/Design空间主题 | Source Han Sans 400，约39px；不能沿用主词700，三行题组保持独立净空 |
| 栏目／职业小题 | 常规400约16px；职业分行强调约20px仍用400，字级形成主次，不靠全粗 |
| 正文／窄栏简介 | 一般11px／1.5；窄新品牌说明9px／1.45、头像简介9.5px／1.5；辅助8–9px。按栏宽与参考行数核验，不能只缩字适配超量文案 |
| 局部斜体签名 | Arial Bold Italic真字形约11px，仅短辅助语；不扩散为整页正文斜体 |

A保留活动短文、图下栏目、约3行主场说明、细线及联系细项；B保留新品牌图文、开场题、工作图、两组简介、季节题与环境说明。参考微字不可读时用同职责、接近行密度的完整演示文案，不写解释性占位。段距6–10px、普通图到短题12–18px、主题组距按内容约24–32px；有参考锚点时优先保护指定净距，不套全局统一gap。

长词、数字单位及末行孤字／单词须逐行检查；先重分语义、调整列宽或信息分配，不用隐藏溢出、强压字体或任意扩大固定印刷成品。窄屏展示固定画布时整体缩放，另有响应式要求才重排。品牌、人物、联系信息及优惠事实不从参考继承。

### 组装与验收

**完整实现入口**：[最终校准版 CSS／HTML](interior-cut-window-spread.html)。提取 `main[data-recipe="interior-cut-window-spread"]` 与 `style[data-recipe-css]`；样式限定在 `.vl-interior-spread`，不污染其他组合。`style[data-preview-only]` 仅展示底，不复制到成品。模板保留全部六区与真实密度演示文案；绑定 `data-asset-slot` 后再渲染，不能以空槽位声明效果通过。六个资产角色为 `interior-room`、`interior-lounge`、`interior-stilllife`、`interior-work`、`designer-a`、`designer-b`，共同服务9个图像节点；重复角色独立保留取景参数。正式输出仍按组装协议行内化样式并内嵌资源。

模板以成功版为准，保留空间主题400、主词700、轻副词300、共享题注直属展开层及修正后的正文断行；圆箭头字符使用实际Arial 400，局部圆印记为实色，摄影不继承透明或滤镜。配方约束与模板实现一起维护，不能只更新文字说明而留下旧尺寸或旧字重。

每幅创建relative/isolation的共同父层；大色场由三个区建立，跨区题注／线条直接归共同层，局部照片只裁自身图窗。文字内部用自然流，图边色签、箭头和竖题独立定位并校准；源图刻意贴边与切角不能推广为正文可越界。

整组实测保留六区与9个图片槽位，真实常规／粗体／细体加载；标题到右图约35px，正文末行单词与共享题注归属已修正，未检测到文字互相重叠或字形越界，无阴影／附加透明滤镜，只有两处硬色标分区。仍需对真实素材替换后的主体裁切、长文案及最终印刷阅读距离重新验证；该样本不是所有内容长度和字体环境的通过证明。

### 完整实现与单面取用

布局：[ 三栏展开 · 错层图窗 ](../layouts/fold-full-page.md#layout.fold-cut-window)。主题源只含 `style[data-fold-theme="interior"]`，不能单独作为完整页面。先读取本组合和必需布局的模板节点，组合使用布局源的唯一主结构，不再从描述或旧局部骨架重建。

```json
{"dependencies":["layout.fold-cut-window"]}
```

只换配色／字体／质感时采用同一布局；单面取用按布局中的具名视区坐标及 `layout.fold-panel-view` 保留全局关系。跨栏标题、共享图窗所在面不得裁掉字词后冒充独立单页，需保留展开使用或明确重排。素材槽位保持独立实例；参考摄影、书法与图形资产不包含在主题源中。

<a id="combination.vertical-title-whitespace"></a>

## 竖题留白组合

风格标签：二级：新中式风 / 当代东方。

**适用与状态**：粒度：展开组合；适配产物：折页展开视觉、品牌画册。六个独立竖面及其局部组合；不绑定实际折法 已保存完整展开结构；来源版本记录其原参考关系验证通过，本次使用仍须复核；印刷折法与内外面序仍未确认。 完整组合关系验证通过，素材与精确字形边界见末段；不等于精确字形、素材授权或生产拼版通过。

归属与新增依据：竖排书写主视觉、宋形栏目、淡绿留白与茶园影像共同构成当代东方；书写字资源尚未就绪，不能把宋体代排当完成。

### 提取内容与实现归属

| 提取内容 | CSS类型／处理 |
|---|---|
| 背景、图片、文字的组合内关系 | 布局几何统一引用[六面分工 · 竖题图文](../layouts/fold-full-page.md#layout.fold-tea-six-panels)；不由通用图文骨架重新生成。 |
| 配色 | 组合内覆盖；近似米白#F5F3E7占全组约六成；浅绿#97B79B至#D9E5D6服务单面背景；深绿#355D43用于标题，照片绿色保留。苔绿信笺仅作近邻配色复用。 |
| 字体 | 角色与字形选择见下表；沿用[字体绑定契约](#combination-font-binding)，不新增字体资源索引 |
| 质感／渐变 | 仅保留有证据的淡斑点及竹叶线描，不添加纤维或纸张投影。摄影光照随资产保留；渐变可CSS实现，四瓣裁切可SVG遮罩实现。 |
| 摄影／插画 | 图片素材槽位；茶园纵景需在左缘留标题保护区；采茶近景适配曲线窗，流程用横幅动作图；茶具横景及包装透明图独立提供。标识、工艺说明和产品事实必须替换为授权内容。 |

### 背景、图窗与文字的关系

| 区域 | 归属与约束 |
|---|---|
| 六面关系 | 分别保留流程、曲线窗、竖题主视觉、下图叙事、通栏图文、产品信息六个逻辑面，面序未定。 |
| 背景与容器 | 米白面开放排字；渐变只作用于品牌面。流程照片为图窗；产品信息的浅绿底确有载体边界，产品轮廓独立越出上缘。 |
| 保护区 | 900px三栏样本、单面300px；内距26px；主视觉图约55%面宽，竖题占左25%，不遮茶园主体；产品越界预留34px以上。 |

文字描述用于选型；精确几何和色值以本次已验证的布局源与主题源为准，900px展开宽是验证坐标，不是印刷规格。先分清全幅背景与局部图窗：背景可跨面共享，图窗只裁取景，无证据不附加底板、圆角或阴影。真实光照和绘画笔触留在素材内；新增CSS遮光须由实际叠字对比问题触发，不能把整张图片默认压暗。

### 字体与内容适配

保留竖向书写主视觉、宋形栏目与细正文。来源版本的字体绑定见主题源 `--fold-font-*`；字号、行距、列宽见布局源，不沿用旧局部样例参数覆盖母版。字体替换后重查真实face、断行和溢出；原参考具体family未确认。茶叶书法使用独立字形素材槽，不能用宋体代排后宣称完成。

正文槽位按参考行密度设计；超量内容应明确调整信息分配并重验，不能隐藏、截字或全局缩成微字。窄屏展示按整体画布缩放；响应式重排与生产拼版另行确认。

### 组装起点

读取下方完整源，保留一次主结构；正式输出按目标协议行内化。普通面板内容用纵向flow或flex，gap=16–18px、padding=26px、min-width:0；背景层独立isolation，图片使用object-fit:cover和经主体核验的object-position，文字不继承图片滤镜。此骨架表达槽位而非来源素材下载地址，先落实槽位再输出成品。



以约170:360竖面为基准，普通内边距约9%。主视觉图占右侧约60%宽、约70%高，大字在左上；渐变面曲线窗置上部中央。内容面采用标题—正文—通栏照片，产品面两块信息底纵排，产品独立叠在上沿。

可变项：标题、正文量、图窗数量与实际资产；固定项为本组合主次、共享背景范围和图文归属。屏幕结构验证允许增高，固定印刷成品不能随文案任意增高或移动折线；超量时调整信息分配或增加页面。折面、出血与开合按[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)绑定，图1这类四区展开不得强转三等面。

**局部验证与剩余边界**：两配置在900px展开宽渲染，原生文字、局部图片取景与背景层分开；检查基础/加长文案、文字边界、实际字体、背景连续性和无默认投影。源图裁片只用于本次验证，不加入库素材目录、不作为跨任务默认内容。主视觉书写字、细斑纹与竹叶线描待授权资源；四瓣窗只验证近似曲线，不宣称精确轮廓；产品越界以几何槽位检查，未完成真实商品边缘验证。 原参考的品牌、人物、联系方式、产品陈述均不继承；每次真实素材替换后重查主体和文字保护区。

### 完整实现与单面取用

布局：[ 六面分工 · 竖题图文 ](../layouts/fold-full-page.md#layout.fold-tea-six-panels)。主题源只含 `style[data-fold-theme="tea"]`，不能单独作为完整页面。先读取本组合和必需布局的模板节点，组合使用布局源的唯一主结构，不再从描述或旧局部骨架重建。

```json
{"dependencies":["layout.fold-tea-six-panels"]}
```

只换配色／字体／质感时采用同一布局；单面取用按布局中的具名视区坐标及 `layout.fold-panel-view` 保留全局关系。跨栏标题、共享图窗所在面不得裁掉字词后冒充独立单页，需保留展开使用或明确重排。素材槽位保持独立实例；参考摄影、书法与图形资产不包含在主题源中。

<a id="combination.dark-editorial"></a>

## 暗调编辑组合

风格标签：二级：奢雅精致风 / 古典雅奢。

粒度：两幅展开组合；适配折页／品牌画册。暗花绘画、高反差衬线品牌字与浅色密排栏共同定义本组。已做参考校准的完整效果验证并回写以下参数；原字体身份、原画精确复原及印刷面序不据此确认。普通文字与框由HTML/CSS实现，绘画为独立可替换素材。

### 图文关系与依赖

复用[网格](../layouts/grid-and-alignment.md#layout.evidence-grid)、[阅读栏](../layouts/airy-and-spacious.md#layout.reading-column)、[图片主场](../layouts/hero-focus.md#layout.image-stage)、[章节流](../layouts/continuous-flow.md#layout.chapter-flow)。完整几何统一由[三栏展开 · 暗花编辑](../layouts/fold-full-page.md#layout.fold-floral-editorial)维护；保留连续场域和独立图窗，不由通用骨架重建。面序、折线和出血由[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)约束。

两幅各以900×665、三面各300px为验证坐标；这只是参考比例起点，不是印刷规格。下表坐标均在所属展开内，x/y/w/h单位px；未列高度的正文按指定字级与完整文案自然流动，固定成品超量须重新分配内容。

| 对象 | 背景／图片／文字归属与几何 |
|---|---|
| A左编辑栏 | x=0,w=300，纸底；局部瓶花图35/33/232/294；文字组35/369/232，含英文栏目、中文小题、3组正文和小英文页脚 |
| A中右共享场域 | 300/0/600/665；一个连续暗花背景作为两面的共同父层，两个文字区为兄弟节点，不各自复制底图或加背景卡 |
| A圆标与短句 | 圆标350/222/126/126；MOFAY类短标与中文同行且整组测量；下方居中3行短句，x=348,y=361,w=150 |
| A联系区 | x=324,y=535,w=238；74×62独立小图窗，下接必要联系标签；它不是满版背景的一部分 |
| A右框题 | 638/194/231/274，纵向暖灰标签、双细线，无投影；品牌、英文辅助、中文主题及底部短句分四个字级／位置组；顶部与框下另有细字 |
| B左侧题与图文 | x=0,w=80橄榄题带；整行英文旋转−90°，不是斜体字形；瓶花图80/29/198/330；文字组128/425/150 |
| B中服务栏 | 334/45/234；英文栏目＋中文小题，下接4组服务短题与完整正文；横向细节图331/575/240/72，不给每组套卡 |
| B右主场 | 600/0/300/665独立全高花画；中央椭圆629/289/242/90，主标和小英文居中，文字不继承背景色阶处理 |

### 配色、质感、渐变与透明

| 类型 | 本组绑定 |
|---|---|
| 配色 | 纸底#c8c5af、墨字#24251f、暗底#1e1e1e、橄榄题带#6a6c55、局部标签#d1cdca；色值来自参考采样，花画色阶随最终图核验 |
| 质感 | 暗花轮廓与细笔触来自连续绘画，瓶花是更明亮、完整的独立画作；不得把瓶花小裁片放大成所有背景，也不靠随机噪点替代笔触 |
| 色彩渐变／光场 | 本组无独立CSS渐变或光晕需求；绘画自身明暗由素材承担，纸底与暗底为有意硬分区 |
| 图片Alpha／表面透明 | 默认不透明，无自动渐隐；花画过亮时按目标色阶修订素材并复核文字净空，不固定叠黑罩；任何按需透明层必须独立于正文和品牌文字 |

暗花资产覆盖A中右与B右两个槽位，可有明确同资产复用意图；分别绑定object-position并验证裁切。建议成图至少1024×1536，A横向覆盖会裁去部分上下区域，须保留花型、净空与暗调；不拉伸。局部瓶花需完整主体，适配竖画及小横窗；同资产不同取景仍独立记录。素材就绪后才能判定主体保护区通过，不以文件存在代替视觉检查。

### 字体、密度与内容

按[字体绑定契约](#combination-font-binding)核验实际face。以下为900px展开上的校准值，不向其他配方传播为默认字号；品牌角色与编辑角色分开测量。

| 角色 | 字体／字级与节奏 |
|---|---|
| 框题／椭圆品牌主标 | Bodoni 72 400，42px，line-height:1；不用合成粗体 |
| 英文栏目 | Bodoni 72 400，25px／1.12；旋转侧题40px／1.1 |
| 中文小题／服务短题 | Songti SC 400，15px／1.4；服务短题11.5px／1.5 |
| 正文 | Songti SC 400，10.5px／1.6；段距7px，服务组距18px；A左约3组、每组3行，B中4组，每组约3–5行 |
| 辅助英文／联系／圆标 | 辅助9–11px；圆标英文18px、中文12px，短标整体不换行并核对圆内净距 |

原图极小字无法可靠读出时，以同职责、接近行数的完整演示文案验证，不写“此处说明／保留留白”等解释句。正文偏大应先比对同尺度字级与栏宽，不能只扩大面板或删正文；过小同样要检查阅读距离。圆标、框内短句和数字单位不得掉成孤字；正文变化后重验相邻组与末行净距。

### 组装与验收

为每幅建立relative/isolation的共同坐标层；纸底与暗花场域先分父层，再按几何表绑定img、真实DOM文字和独立框形。连续背景使用覆盖共同父层的单一图片节点，局部图窗另建img。文字组内部采用自然流，品牌框的分级文字使用各自内容区；形状不承担整段透明度。

局部绘画、共同场域、圆标、纵框、细字、侧题和四组服务正文均属于完整效果的必需项；缺少其中关键角色只能标局部布局已验。实际小字号版已渲染并确认Bodoni 72 Book与Songti SC Regular加载、图片完整加载、无横向溢出；精确原画／原字体、文案替换后的断行和固定印刷尺寸仍需各自核验。参考品牌与业务示例不作为其他项目默认事实。

### 完整实现与单面取用

布局：[三栏展开 · 暗花编辑](../layouts/fold-full-page.md#layout.fold-floral-editorial)。组合模板仅提供`style[data-fold-theme="floral"]`；配套读取布局CSS及唯一`main[data-fold-layout="floral"]`，不要重新生成三栏。

```json
{"dependencies":["layout.fold-floral-editorial"]}
```

按布局正文的具名视区使用`layout.fold-panel-view`取面；跨面背景和完整展开结构仍保留。主题覆盖配色与字体，图窗、曲线、文本位置在布局层维护。仅换视觉时也需检查对比度及素材背景融合。

<a id="combination.spanning-display-title"></a>

## 跨列大字组合

风格标签：二级：理性信息风 / 企业宣讲。

**适用与状态**：粒度：展开组合；适配产物：折页展开视觉、品牌画册。两组展开视觉的配套组合，不定义折法与面序。 已保存完整展开结构；来源版本记录其原参考关系验证通过，本次使用仍须复核；印刷折法与内外面序仍未确认。 完整组合关系验证通过，素材与精确字形边界见末段；不等于精确字形、素材授权或生产拼版通过。

归属与新增依据：红黑白对比、跨列活动标题、人物序列与议程对齐形成企业活动宣讲；没有新增“活动导览”风格分支。

### 提取内容与实现归属

| 提取内容 | CSS类型／处理 |
|---|---|
| 背景、图片、文字的组合内关系 | 布局几何统一引用[三栏展开 · 跨栏大字](../layouts/fold-full-page.md#layout.fold-title-agenda)；不由通用图文骨架重新生成。 |
| 配色 | 组合内覆盖；近似#D2222A红占20%–30%，#F5F4F1白占主体，#151515用于标题与图标；灰阶主要来自照片和次级文字。排除外灰底及样机暗部。 |
| 字体 | 角色与字形选择见下表；沿用[字体绑定契约](#combination-font-binding)，不新增字体资源索引 |
| 质感／渐变 | 平面色块无需材质CSS；照片承担真实光照。局部圆角可用CSS，大弧裁图可用SVG遮罩；不加纸纤维、卡片阴影或样机折影。 |
| 摄影／插画 | 图片素材槽位；会议中景1处、人物肖像3处、主题近景1处；保护脸部与主动作。品牌、日期、姓名、联系方式及议程均由真实内容替换，禁止复制示例身份事实。 |

### 背景、图窗与文字的关系

| 区域 | 归属与约束 |
|---|---|
| A展开 | 三列对齐；左会议图和简介，中部红底与大标题，右侧次行标题和日期场；主标题可跨第二、三列，须占真实预留行。 |
| B展开 | 左人物序列、中引语与议程、右大弧图窗接说明；红色是分区底和强调，不是每条信息外壳。 |
| 保护区 | 900px样本内距26px；主标题测试430px宽、82px字级；邻栏其他标题下移，不使用负间距；名单和时间单位保持语义整体。 |

文字描述用于选型；精确几何和色值以本次已验证的布局源与主题源为准，900px展开宽是验证坐标，不是印刷规格。先分清全幅背景与局部图窗：背景可跨面共享，图窗只裁取景，无证据不附加底板、圆角或阴影。真实光照和绘画笔触留在素材内；新增CSS遮光须由实际叠字对比问题触发，不能把整张图片默认压暗。

### 字体与内容适配

保留粗重无衬线跨栏标题、轻数字日期与常规正文。来源版本的字体绑定见主题源 `--fold-font-*`；字号、行距、列宽见布局源，不沿用旧局部样例参数覆盖母版。字体替换后重查真实face、断行和溢出；原参考具体family未确认。

正文槽位按参考行密度设计；超量内容应明确调整信息分配并重验，不能隐藏、截字或全局缩成微字。窄屏展示按整体画布缩放；响应式重排与生产拼版另行确认。

### 组装起点

读取下方完整源，保留一次主结构；正式输出按目标协议行内化。普通正文组用纵向flow或flex，gap=16–18px、padding=26px仅作样本起点、min-width:0；共享背景与跨区元素归展开共同层，局部图窗保留自身取景边界，不将跨区关系套入单栏flow或面板裁切；背景层独立isolation，图片使用object-fit:cover和经主体核验的object-position，文字不继承图片滤镜。此骨架表达槽位而非来源素材下载地址，先落实槽位再输出成品。



每组以约三等列建立对齐。上组左列上半为会议图窗、下半为简介；中列顶部红底与右列标题相接，下置联系信息；右列下部红底日期区。下组左列纵排三个人像，中列上引语下议程，右列上大弧裁图下说明。标题、红底和图窗分别归属文字层、背景层、资产层。

可变项：标题、正文量、图窗数量与实际资产；固定项为本组合主次、共享背景范围和图文归属。屏幕结构验证允许增高，固定印刷成品不能随文案任意增高或移动折线；超量时调整信息分配或增加页面。折面、出血与开合按[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)绑定，视觉分区不等于物理折面：按展开坐标适配共享背景、局部图窗与文字归属，不按折面机械重切视觉分区；局部复用须保留采用关系，未确认折法不等于布局不可用。

**局部验证与剩余边界**：两配置在900px展开宽渲染，原生文字、局部图片取景与背景层分开；检查基础/加长文案、文字边界、实际字体、背景连续性和无默认投影。源图裁片只用于本次验证，不加入库素材目录、不作为跨任务默认内容。样机透视与阴影明确排除；原人物姓名、日期及折线位置未知，不作为默认内容；跨列字体候选已试排，原字体名未确定。 原参考的品牌、人物、联系方式、产品陈述均不继承；每次真实素材替换后重查主体和文字保护区。

### 完整实现与单面取用

布局：[ 三栏展开 · 跨栏大字 ](../layouts/fold-full-page.md#layout.fold-title-agenda)。主题源只含 `style[data-fold-theme="conference"]`，不能单独作为完整页面。先读取本组合和必需布局的模板节点，组合使用布局源的唯一主结构，不再从描述或旧局部骨架重建。

```json
{"dependencies":["layout.fold-title-agenda"]}
```

只换配色／字体／质感时采用同一布局；单面取用按布局中的具名视区坐标及 `layout.fold-panel-view` 保留全局关系。跨栏标题、共享图窗所在面不得裁掉字词后冒充独立单页，需保留展开使用或明确重排。素材槽位保持独立实例；参考摄影、书法与图形资产不包含在主题源中。

<a id="combination.ribbon-image-group"></a>

## 曲带图组组合

风格标签：二级：理性信息风 / 企业宣讲。

**适用与状态**：粒度：展开组合；适配产物：折页展开视觉、品牌画册。同一展开组合的A、B两种视觉变体，不推断正反面。 两套完整展开已通过API原参考对照；实际布局源与主题源均已登记。印刷折法、真实素材及精确字形仍按本次任务确认。

归属与新增依据：服务分类、真实活动照片与亲和插画共同服务机构宣讲；亲和是表现特征，不新增“亲和服务”二级风格。

### 提取内容与实现归属

| 提取内容 | CSS类型／处理 |
|---|---|
| 背景、图片、文字的组合内关系 | 统一读取[三栏展开 · 波浪串联](../layouts/fold-full-page.md#layout.fold-care-waves)的完整结构；通用原子仅解释局部关系。 |
| 配色 | 组合内覆盖；近似#FFFFFF与#4C8BBD为主场，A蓝约40%、B蓝约15%–20%；#153958用于标题，#F4C59C、#F8E9CE及#C8A25D作小面积柔化与勾边。比例排除照片及灰底。 |
| 字体 | 角色与字形选择见下表；沿用[字体绑定契约](#combination-font-binding)，不新增字体资源索引 |
| 质感／渐变 | 摄影保留原光照；平涂插画、植物、波浪和飘带优先用授权SVG或透明图。金色仅作色带，不默认金属反射；无需纸纹、浮雕或投影CSS。 |
| 摄影／插画 | 图片素材槽位；A含园艺主图、交流活动小图及人物插画；B含两张圆形人物图、三张环境图及底部插画。保护脸部、手部活动与空间主体；人物身份、机构名和服务资质不得自动复制。 |

### 背景、图窗与文字的关系

| 区域 | 归属与约束 |
|---|---|
| A变体 | 左服务阅读栏独立白底；中右共享蓝色场域，主活动图和局部照片在其上，人物插画是前景资产。 |
| B变体 | 白底居多；中栏圆图叠放、短标签与飘带串联，右栏环境图窗和说明配对；不自动沿用A大蓝底面积。 |
| 保护区 | 900px样本内距26px；圆图重叠只穿过非人脸区域；正文与插画分开留空；标题按完整短语断行，背景曲线不能切割文字。 |

以上比例与色值是参考目测起点，900px展开宽仅为局部验证尺度。先分清全幅背景与局部图窗：背景可跨面共享，图窗只裁取景，无证据不附加底板、圆角或阴影。真实光照和绘画笔触留在素材内；新增CSS遮光须由实际叠字对比问题触发，不能把整张图片默认压暗。

### 字体与内容适配

保持方整无衬线标题、常规正文和圆形短标签的层级。真实family通过组合主题的`--fold-font-*`绑定；字号、行距及图文槽位以已验证布局源为准，不能用旧局部样例的28px标题和通用gap覆盖母版。长文案、不同字体或图片换入后检查短语断行、人脸与正文净空。

### 组装与素材边界

共享蓝色背景、波浪与飘带由布局内曲线路径实现；照片与人物插画分别绑定独立素材槽位。正式插画应使用有透明背景的授权资产，不能把蓝色矩形裁片覆盖到连续场域上。原参考裁片仅用于本次对照验证，不随库分发；验证用局部羽化与轮廓遮罩不能替代正式资产的边缘检查。

固定画布换文案需复查容量，不能隐藏正文或任意扩大印刷成品。A/B是两种展开配置，不自动等同正反面；折线、面序、出血遵循[三折页Spec](../../../../references/style/coding/scenarios/tri-fold-spec.md)。

### 完整实现与单面取用

布局：[三栏展开 · 波浪串联](../layouts/fold-full-page.md#layout.fold-care-waves)。组合模板仅提供`style[data-fold-theme="care"]`；配套读取布局CSS及唯一`main[data-fold-layout="care"]`，不要重新生成三栏。

```json
{"dependencies":["layout.fold-care-waves"]}
```

按布局正文的具名视区使用`layout.fold-panel-view`取面；跨面背景和完整展开结构仍保留。主题覆盖配色与字体，图窗、曲线、文本位置在布局层维护。仅换视觉时也需检查对比度及素材背景融合。

<a id="combination.menu-paper-hot-cold"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 米色纤维纸三分类咖啡菜单

**产物适用**：产物：菜单单页；载体：竖版印刷；冷热双列；纯文字价目；纸纤维。社媒／详情页仅借用局部关系，重新确定密度，不直接等比缩放。

### 提取与组合规则

```json
{
  "artifact_tags": [
    "图2",
    "单页纸质菜单",
    "三组分类",
    "HOT/COLD双价格列",
    "米色纸感",
    "无产品照片"
  ],
  "dimensions": "近读试排示例宽794px，内容自然撑高；左分类150px，品项区与两列64px价格共同排布。示例用于内容试排，按目标载体重算宽度、列数与分页；试排后测量并锁定最终画布。锁定纸张放不下时调整分区或分页，不缩小整版，也不无限加长纸张。",
  "relationships": [
    {
      "type": "背景/容器",
      "description": "menu-2本身为唯一纸张容器；低对比米色渐变和细噪点作为纸张背景，正文不做透明度衰减。三组共用左侧竖向细线，组间靠留白区分。"
    },
    {
      "type": "图片素材",
      "description": "无产品照，不设置img或照片资产槽。三个器具图形采用小型内联SVG线描近似，不使用emoji，也不使用整张参考图。"
    },
    {
      "type": "文字所属",
      "description": "左上宋体字属于品牌文字近似；左列为三个中英分类；右列每行品名及英文属于同一品项，HOT/COLD固定网格列对应价格。手冲附烘焙度和风味说明；底部注释独立属于整页。"
    }
  ],
  "safe_areas": [
    {
      "type": "页面",
      "description": "四周36px留白；正文自然排版，页脚在内容之后，不以固定高度裁掉条目。"
    },
    {
      "type": "分类与品项",
      "description": "分类与品项间距24px，分类组间28px；长菜名、英译和风味说明换行撑高，HOT/COLD表头与两列价格对齐。"
    },
    {
      "type": "图片",
      "description": "无产品照片；分类SVG只作分类提示，不侵入品名价格。"
    }
  ],
  "fonts": [
    {
      "family": "Source Han Sans SC",
      "weight": 400,
      "role": "品名与价格20px，中文分类24px，说明16px，英译、英文分类及页脚14px；是近读试排字级，不替代目标载体可读性验收。"
    },
    {
      "family": "Songti SC",
      "weight": 700,
      "role": "品牌近似，系统 Songti SC 真正700字款；禁用合成粗体，不宣称原字标。"
    }
  ],
  "texture": "暖米色纸底，低对比多向渐变模拟轻微色差，SVG turbulence细噪点模拟纤维颗粒；不覆盖整页照片，不对正文叠加透明遮罩。",
  "limits": [
    "参考左上品牌字疑似“岚”，仅以可编辑宋体字近似，不复刻或冒充真实标志。",
    "手冲第一项风味末段清晰度不足，当前转录“太阳城茶”存在识别不确定性，正式制作应核对原稿。",
    "底部常见过敏原及中间短句清晰度有限，当前转录需核对；未补造联系方式或地址。",
    "各品项双列价格按参考保留，包括拿铁HOT ¥26、COLD ¥24这一不常见价格顺序；无供应价格使用原图双短横线。",
    "纸张明显褶皱与真实纤维无法直接分离，使用低对比程序纹理近似；器具线描为简化重绘。",
    "较长菜名、英译与风味说明在品名列内自然换行并撑高行；价格列独立，不借用相邻品项空白。示例用于内容试排，按目标载体重算宽度、列数与分页；试排后测量并锁定最终画布。锁定纸张放不下时调整分区或分页，不缩小整版，也不无限加长纸张。"
  ]
}
```

### CSS组合

```css
.menu-2{width:794px;padding:36px;box-sizing:border-box;color:#303126;background-color:#e9e7cb;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.72' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' opacity='.115' filter='url(%23n)'/%3E%3C/svg%3E"),linear-gradient(117deg,transparent 24%,rgba(128,127,83,.045) 24.5%,transparent 25.4%,transparent 64%,rgba(255,255,244,.2) 65%,transparent 67%),linear-gradient(27deg,#e9e6ca,#eeecd5 48%,#e4e3c7);font-family:'Source Han Sans SC',sans-serif;font-weight:400;font-size:18px;line-height:1.5;font-synthesis:none;-webkit-font-smoothing:antialiased}
.menu-2 *{box-sizing:border-box}
.menu-2 .brand{margin:0 0 20px;font-family:'Songti SC',serif;font-weight:700;font-size:48px;line-height:1.2}
.menu-2 .price-head{margin-left:174px;display:grid;grid-template-columns:minmax(0,1fr) 64px 64px;gap:8px;font-size:16px;margin-bottom:12px}
.menu-2 .price-head span{text-align:center}
.menu-2 .menu-body{display:grid;grid-template-columns:150px minmax(0,1fr);row-gap:28px}
.menu-2 .category{border-right:1px solid rgba(104,105,69,.5);display:flex;flex-direction:column;justify-content:center;gap:8px;padding-right:20px;min-width:0}
.menu-2 .category-cn{font-size:24px;line-height:1.4}
.menu-2 .category-en{font-size:14px;line-height:1.4;color:#424535;overflow-wrap:anywhere}
.menu-2 .line-art{width:72px;height:48px;fill:none;stroke:#74775b;stroke-width:.75;stroke-linecap:round;stroke-linejoin:round}
.menu-2 .items{padding-left:24px;min-width:0}
.menu-2 .item{display:grid;grid-template-columns:minmax(0,1fr) 64px 64px;column-gap:8px;align-items:start;min-height:58px;padding:10px 0;break-inside:avoid}
.menu-2 .item-copy,.menu-2 .item-name{min-width:0}
.menu-2 .item-name{margin:0;font-size:20px;line-height:1.5;font-weight:400;overflow-wrap:anywhere}
.menu-2 .english{display:block;color:#55583e;font-size:14px;line-height:1.5}
.menu-2 .detail{margin:4px 0 0;font-size:16px;line-height:1.5;overflow-wrap:anywhere}
.menu-2 .price{font-size:20px;line-height:1.5;text-align:center;white-space:nowrap;font-variant-numeric:tabular-nums}
.menu-2 .footer{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px 20px;margin-top:32px;color:#55583e;font-size:14px;line-height:1.5}
```

```html
<main class="menu-2" aria-label="咖啡与茶饮菜单"><h1 class="brand" aria-label="岚">岚</h1><div class="price-head"><span></span><span>HOT</span><span>COLD</span></div><div class="menu-body"><section class="category category-hand" aria-label="手冲咖啡分类"><svg class="line-art hand-art" viewBox="0 0 55 36" aria-hidden="true"><path d="M20 11h17l-1 21H22zM23 8h12M27 6h5M37 15c10-4 12 12 0 12M20 15l-7-6-10 1 10 3 7 9M42 30h7M47 28l-2-7"/></svg><div class="category-cn">手冲咖啡</div><div class="category-en">HAND BREWED COFFEE</div></section><section class="items hand-items" aria-label="手冲咖啡品项"><div class="item"><div class="item-copy"><p class="item-name">巴拿马瑰夏<span class="english">Panama Geisha</span></p><p class="detail">烘焙度：中度烘焙</p><p class="detail">风味：奶油巧克力、柑橘、太阳城茶</p></div><div class="price">¥98</div><div class="price">--</div></div><div class="item"><div class="item-copy"><p class="item-name">哥伦比亚月夜<span class="english">Flower Moonlit Night</span></p><p class="detail">烘焙度：中度烘焙</p><p class="detail">风味：荔枝、芒果、玫瑰花茶</p></div><div class="price">¥98</div><div class="price">--</div></div><div class="item"><div class="item-copy"><p class="item-name">牙买加蓝山<span class="english">Jamaica Blue Mountain</span></p><p class="detail">烘焙度：中度烘焙</p><p class="detail">风味：枫糖、陈皮、小青柑茶</p></div><div class="price">¥98</div><div class="price">--</div></div></section><section class="category category-espresso" aria-label="意式咖啡分类"><svg class="line-art espresso-art" viewBox="0 0 53 35" aria-hidden="true"><ellipse cx="21" cy="12" rx="14" ry="4"/><path d="M7 12c1 12 5 15 14 15s12-5 14-15M35 14c12-3 9 9-3 8M8 29c7 4 22 4 28-1M43 27c4-6 9-3 6 1s-8 3-6-1M44 29l5-4"/></svg><div class="category-cn">意式咖啡</div><div class="category-en">ESPRESSO COFFEE</div></section><section class="items espresso-items" aria-label="意式咖啡品项"><div class="item"><p class="item-name">美式咖啡<span class="english">Americano</span></p><div class="price">¥22</div><div class="price">¥24</div></div><div class="item"><p class="item-name">意式浓缩<span class="english">Italian concentration</span></p><div class="price">¥22</div><div class="price">¥24</div></div><div class="item"><p class="item-name">拿铁<span class="english">Latte</span></p><div class="price">¥26</div><div class="price">¥24</div></div><div class="item"><p class="item-name">抹茶拿铁<span class="english">MatchaLatte</span></p><div class="price">¥26</div><div class="price">¥28</div></div><div class="item"><p class="item-name">海盐焦糖<span class="english">Sea salt caramel</span></p><div class="price">¥28</div><div class="price">¥30</div></div><div class="item"><p class="item-name">奥利奥雪顶<span class="english">Oreo Snow Top</span></p><div class="price">¥28</div><div class="price">--</div></div></section><section class="category category-tea" aria-label="茶与饮品分类"><svg class="line-art tea-art" viewBox="0 0 51 36" aria-hidden="true"><path d="M13 13c2 13 7 20 18 20s15-9 15-20M13 15L4 11l4 11 9 2M15 12c3-5 8-4 13-6l2-3 3 4c5 0 10 1 13 5M13 13c8 4 24 4 33 0M46 15c6-2 6 9-3 10"/></svg><div class="category-cn">茶＆饮品</div><div class="category-en">TEA＆DRINK</div></section><section class="items tea-items" aria-label="茶与饮品品项"><div class="item"><p class="item-name">红丝绒牛奶<span class="english">Red velvet milk</span></p><div class="price">¥16</div><div class="price">--</div></div><div class="item"><p class="item-name">可乐姜茶<span class="english">Cola ginger tea</span></p><div class="price">¥16</div><div class="price">¥16</div></div><div class="item"><p class="item-name">黑糖红茶<span class="english">Black sugar tea</span></p><div class="price">¥22</div><div class="price">--</div></div><div class="item"><p class="item-name">蜜桃乌龙茶<span class="english">Peach Oolong Tea</span></p><div class="price">--</div><div class="price">¥22</div></div></section></div><footer class="footer"><span>常见过敏原:牛奶/糖/麦等</span><span>· 咖啡与茶，感谢与你相遇</span><span>送你一阵山风，欢迎你常来</span></footer></main>
```

### 使用与验证边界

参考文案与价格仅用于关系验证，生产必须绑定已确认菜单事实。图像槽必须替换成独立商品素材；预览引用的参考局部不进入生产。纸纹与文字分层，不降低正文透明度。固定价格列禁止换行，长品名增加行高，不覆盖相邻行；“--”为参考中不可选状态，不推断为零价格。双页各自保留安全区，中缝不是页面外边距的替代。图示尺寸是参考比例，不是印刷毫米；出血和装订量需由实际成品规格确定。字体先核实文件、逐字覆盖及许可，胡敬礼禁用，不默认得意黑。


<a id="combination.menu-minimal-coffee-spread"></a>

**内容适配**：先按[菜单图文尺度与容量](../../../../references/style/coding/systems/menu-visual-system.md#图文尺度与容量)共同试排图字，再重算列数、坐标与页数。借用关系，不照搬参考的小字、小图或固定几何；按目标显示宽度验收，不靠整版缩小适配。

**设计方法**：[菜单风格、布局、配色与图片](../../../../references/style/coding/scenarios/menu-spec.md#menu-visual-css-routing)。先选方法，再按内容借用本配方。

## 双页纸感咖啡茶饮价目单

**产物适用**：产物：菜单双页；载体：独立竖版双页；多规格价格；小图主推；中缝安全区。社媒／详情页仅借用局部关系，重新确定密度，不直接等比缩放。

### 提取与组合规则

```json
{
  "artifact_tags": [
    "双页竖版菜单",
    "咖啡价目表",
    "现冲茶饮",
    "白色纸感",
    "分组比较",
    "分类细横线",
    "两列产品展示"
  ],
  "dimensions": "近读试排示例左右各800px，展示间距40px；单页独立排版、内容自然撑高，并排不是折页证据。示例用于内容试排，按目标载体重算宽度、列数与分页；试排后测量并锁定最终画布。锁定纸张放不下时调整分区或分页，不缩小整版，也不无限加长纸张。",
  "relationships": [
    {
      "type": "背景/容器",
      "description": "menu-3展示两张独立纸感页面；各页内部以自然流组织分类，分类细线分隔，不使用浮动卡片或阴影。"
    },
    {
      "type": "图片素材",
      "description": "左右页各四张独立产品图，两列展示；object-fit:contain，先清理素材无功能留边，保留杯型与配料，不含标题价目或整页参考。"
    },
    {
      "type": "文字所属",
      "description": "品牌归左页页眉，口号归右页页眉；品名、冷热规格、价格归各自分类下的grid行。照片名称和价格为图片外可编辑DOM；门店信息归右页页脚。"
    }
  ],
  "safe_areas": [
    {
      "area": "页面与中缝",
      "description": "每页32px内边距；40px展示间距不替代页面安全区，图文不跨页。"
    },
    {
      "area": "分类与条目",
      "description": "分类标题允许副标题换行；列表双列间距24px，品名换行撑高但保留规格价格归属。"
    },
    {
      "area": "图片",
      "description": "产品展示按两列组织，图框高160px，图下留12px；清理无功能留边并保留杯型与配料，实际素材仍须验收有效主体尺度。"
    },
    {
      "area": "页脚",
      "description": "门店信息在正文之后留32px，不用绝对定位覆盖茶饮条目。"
    }
  ],
  "fonts": [
    {
      "family": "Source Han Sans SC",
      "weight": 400,
      "role": "价格18px，规格与单位14px，口号24px，门店字段16px；按目标显示尺度验收。"
    },
    {
      "family": "Source Han Sans CN",
      "weight": 700,
      "role": "品名20px、分类标题26px、品牌英文16px；使用真实700字重字体。"
    },
    {
      "family": "Source Han Sans CN",
      "weight": 700,
      "role": "品牌近似，实际粗黑字款；非原字标"
    }
  ],
  "texture": "浅白底叠加低对比暖灰渐变与低透明度SVG细噪点，仅作为容器背景，不降低正文透明度。",
  "limits": [
    "八个资产槽须替换为已确认对应关系的独立产品素材；不得以整页参考、emoji或含相邻文字的裁片充当商品图。",
    "联系电话、地址及二维码无法可靠确认，未转录或生成虚假联系信息；页脚使用中性“门店信息”字段和非二维码占位框。",
    "品牌用可编辑文字与通用豆形装饰近似，不是原logo复刻。",
    "参考小字较密，个别产品字形与规格需对高清原稿复核；无法确认的规格留空，不推断补填。",
    "图片内容按参考位置配置，右页展示杯型与手冲分类的对应关系沿用参考，不自行改换成常规手冲器具。",
    "示例用于内容试排，按目标载体重算宽度、列数与分页；试排后测量并锁定最终画布。锁定纸张放不下时调整分区或分页，不缩小整版，也不无限加长纸张。加载实际字体并替换素材后重新验收；手机端按单页重排，不将双页整体缩小。"
  ]
}
```

### CSS组合

```css
.menu-3{width:1640px;display:grid;grid-template-columns:800px 800px;gap:40px;margin:0;color:#171916;background:#fff;font-family:'Source Han Sans SC',sans-serif;font-weight:400;font-size:16px;line-height:1.5;font-synthesis:none;-webkit-font-smoothing:antialiased}
.menu-3 *{box-sizing:border-box}
.menu-3 .page{min-width:0;padding:32px;background-color:#fafaf8;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.78' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Cpath fill='%236e695d' opacity='.045' filter='url(%23n)' d='M0 0h140v140H0z'/%3E%3C/svg%3E"),linear-gradient(105deg,rgba(229,225,217,.13),rgba(255,255,255,.15) 55%,rgba(230,228,221,.1));}
.menu-3 .brand{display:flex;flex-direction:column;align-items:center;margin:0 0 32px}
.menu-3 .brand-main{display:flex;align-items:center;gap:12px;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:42px;line-height:1.3}
.menu-3 .brand-en{font-size:16px;letter-spacing:4px;margin-top:8px}
.menu-3 .bean-mark{position:relative;display:inline-block;flex:none;width:22px;height:22px;transform:rotate(-24deg)}
.menu-3 .bean-mark:before,.menu-3 .bean-mark:after{content:'';position:absolute;width:12px;height:18px;border-radius:70% 45% 65% 40%;background:linear-gradient(100deg,#171916 43%,#fafaf8 46%,#fafaf8 51%,#171916 54%)}
.menu-3 .bean-mark:before{left:0;top:3px;transform:rotate(-30deg)}
.menu-3 .bean-mark:after{left:9px;top:0;transform:rotate(28deg)}
.menu-3 .section-title{display:flex;align-items:center;flex-wrap:wrap;gap:8px 12px;border-bottom:1px solid #92948e;margin:0 0 20px;padding-bottom:12px}
.menu-3 .section-title strong{font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:26px}
.menu-3 .section-title small{font-size:14px;overflow-wrap:anywhere}
.menu-3 .featured{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
.menu-3 .product{min-width:0;text-align:center;break-inside:avoid}
.menu-3 .product img{display:block;width:100%;height:160px;object-fit:contain;margin:0 auto 12px}
.menu-3 .product-name,.menu-3 .item{font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:20px;line-height:1.5;overflow-wrap:anywhere;min-width:0}
.menu-3 .product-meta,.menu-3 .unit,.menu-3 .spec{font-size:14px}
.menu-3 .product-meta{margin-top:4px}
.menu-3 .product-price,.menu-3 .price{font-size:18px;font-variant-numeric:tabular-nums;white-space:nowrap}
.menu-3 .recommend{display:inline-block;width:14px;height:12px;position:relative;margin-right:6px;vertical-align:0}
.menu-3 .recommend:before{content:'';position:absolute;left:4px;top:4px;width:9px;height:7px;border-radius:1px;background:#151714;box-shadow:-4px 0 0 -1px #151714}
.menu-3 .recommend:after{content:'';position:absolute;left:6px;top:0;width:3px;height:7px;background:#151714;transform:rotate(14deg);border-radius:1px}
.menu-3 .split-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
.menu-3 .espresso-list,.menu-3 .origin-featured{margin-top:24px}
.menu-3 .list{min-width:0}
.menu-3 .row{display:grid;grid-template-columns:minmax(0,1fr) 44px 134px;align-items:baseline;column-gap:8px;min-height:48px;padding:8px 0;break-inside:avoid}
.menu-3 .row.two{grid-template-columns:minmax(0,1fr) 100px}
.menu-3 .spec{text-align:center;white-space:nowrap}
.menu-3 .price{text-align:right}
.menu-3 .plain-indent{padding-left:20px}
.menu-3 .flavors,.menu-3 .tea{margin-top:32px}
.menu-3 .right-header{text-align:right;margin-bottom:32px}
.menu-3 .slogan{font-size:24px;letter-spacing:.7px}
.menu-3 .signature{display:block;width:72px;height:22px;margin:8px 4px 0 auto;position:relative;transform:rotate(-10deg)}
.menu-3 .signature:before,.menu-3 .signature:after{content:'';position:absolute;border-bottom:1px solid #8c8c84;border-radius:50%;width:44px;height:15px;left:0;top:0;transform:rotate(-10deg)}
.menu-3 .signature:after{left:30px;top:6px;width:38px;transform:rotate(-15deg)}
.menu-3 .store{margin-top:32px;display:grid;grid-template-columns:64px minmax(0,1fr);gap:24px;align-items:center}
.menu-3 .store-label{font-size:16px;line-height:1.5}
.menu-3 .store-placeholder{width:64px;height:64px;border:1px solid #c4c5be;display:grid;place-items:center;font-size:14px;line-height:1.5;text-align:center;color:#51534c;background:rgba(255,255,255,.35)}
.menu-3 .store-rule{height:1px;background:#d7d8d0;margin-top:12px}
```

```html
<main class="menu-3" aria-label="双页咖啡茶饮菜单"><article class="page page-left" aria-label="意式咖啡与风味拿铁"><header class="brand"><div class="brand-main"><span class="bean-mark" aria-hidden="true"></span><span>稿定咖啡</span></div><div class="brand-en">GAODING COFFEE</div></header><section class="espresso"><h2 class="section-title"><span class="bean-mark" aria-hidden="true"></span><strong>意式咖啡经典系列</strong><small>YISHIKAFEIJINGDIANXILIE</small></h2><div class="featured"><div class="product"><img data-asset-slot="espresso_latte" src="{{espresso_latte}}" alt="拿铁"><div class="product-name"><span class="recommend" aria-label="推荐"></span>拿铁</div><div class="product-meta">热/冷</div><div class="product-price">¥22 / ¥24</div></div><div class="product"><img data-asset-slot="espresso_cappuccino" src="{{espresso_cappuccino}}" alt="卡布奇诺"><div class="product-name">卡布奇诺</div><div class="product-meta">热/冷</div><div class="product-price">¥20 / ¥22<span class="unit">/杯</span></div></div><div class="product"><img data-asset-slot="espresso_americano" src="{{espresso_americano}}" alt="美式咖啡"><div class="product-name">美式咖啡</div><div class="product-meta">热/冷</div><div class="product-price">¥18 / ¥18<span class="unit">/杯</span></div></div><div class="product"><img data-asset-slot="espresso_caramel_macchiato" src="{{espresso_caramel_macchiato}}" alt="焦糖玛奇朵"><div class="product-name">焦糖玛奇朵</div><div class="product-meta">热/冷</div><div class="product-price">¥23 / ¥25<span class="unit">/杯</span></div></div></div><div class="split-list espresso-list"><div class="list"><div class="row plain-indent"><span class="item">摩卡</span><span class="spec">热/冷</span><span class="price">¥25 / ¥27<span class="unit">/杯</span></span></div><div class="row plain-indent"><span class="item">澳瑞白</span><span class="spec">热/冷</span><span class="price">¥24 / ¥26<span class="unit">/杯</span></span></div><div class="row plain-indent"><span class="item">康宝蓝</span><span class="spec"></span><span class="price">¥20<span class="unit">/杯</span></span></div></div><div class="list"><div class="row"><span class="item">Dirty Coffee</span><span class="spec">冷</span><span class="price">¥22<span class="unit">/杯</span></span></div><div class="row"><span class="item">焦化奶咖啡</span><span class="spec"></span><span class="price">¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item">爱尔兰咖啡</span><span class="spec"></span><span class="price">¥28<span class="unit">/杯</span></span></div></div></div></section><section class="flavors"><h2 class="section-title"><span class="bean-mark" aria-hidden="true"></span><strong>风味拿铁创意系列</strong><small>FENGWEINATIECHUANGYIXILIE</small></h2><div class="split-list"><div class="list"><div class="row"><span class="item"><span class="recommend" aria-label="推荐"></span>榛果拿铁</span><span class="spec">热/冷</span><span class="price">¥24 / ¥26<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">香草拿铁</span><span class="spec">热/冷</span><span class="price">¥23 / ¥25<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">抹茶拿铁</span><span class="spec">热/冷</span><span class="price">¥22 / ¥24<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">红茶拿铁</span><span class="spec">热/冷</span><span class="price">¥21 / ¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item"><span class="recommend" aria-label="推荐"></span>桂花拿铁</span><span class="spec">热/冷</span><span class="price">¥24 / ¥26<span class="unit">/杯</span></span></div></div><div class="list"><div class="row"><span class="item">椰香拿铁</span><span class="spec">热/冷</span><span class="price">¥24 / ¥26<span class="unit">/杯</span></span></div><div class="row"><span class="item">樱桃拿铁</span><span class="spec">热/冷</span><span class="price">¥23 / ¥25<span class="unit">/杯</span></span></div><div class="row"><span class="item">巧克力橙拿铁</span><span class="spec">热/冷</span><span class="price">¥22 / ¥24<span class="unit">/杯</span></span></div><div class="row"><span class="item">玫瑰拿铁</span><span class="spec">热/冷</span><span class="price">¥21 / ¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item">黑芝麻拿铁</span><span class="spec">热/冷</span><span class="price">¥24 / ¥26<span class="unit">/杯</span></span></div></div></div></section></article><article class="page page-right" aria-label="手冲单品与现冲茶饮"><header class="right-header"><div class="slogan">@用心冲每一杯咖啡</div><span class="signature" aria-hidden="true"></span></header><section class="single-origin"><h2 class="section-title"><span class="bean-mark" aria-hidden="true"></span><strong>手冲单品咖啡精选</strong><small>SHOUCHONGDANPINKAFEI</small></h2><div class="split-list origin-list"><div class="list"><div class="row two"><span class="item"><span class="recommend" aria-label="推荐"></span>耶加雪菲</span><span class="price">¥30<span class="unit">/杯</span></span></div><div class="row two plain-indent"><span class="item">哥伦比亚慧兰</span><span class="price">¥32<span class="unit">/杯</span></span></div><div class="row two plain-indent"><span class="item">巴西山多士</span><span class="price">¥28<span class="unit">/杯</span></span></div></div><div class="list"><div class="row two"><span class="item">曼特宁</span><span class="price">¥30<span class="unit">/杯</span></span></div><div class="row two"><span class="item">危地马拉安提瓜</span><span class="price">¥32<span class="unit">/杯</span></span></div><div class="row two"><span class="item">肯尼亚 AA</span><span class="price">¥30<span class="unit">/杯</span></span></div></div></div><div class="featured origin-featured"><div class="product"><img data-asset-slot="special_yunnan_latte" src="{{special_yunnan_latte}}" alt="云南小粒咖啡"><div class="product-name">云南小粒咖啡</div><div class="product-price">¥28<span class="unit">/杯</span></div></div><div class="product"><img data-asset-slot="special_panama_geisha" src="{{special_panama_geisha}}" alt="巴拿马瑰夏"><div class="product-name">巴拿马瑰夏</div><div class="product-price">¥38<span class="unit">/杯</span></div></div><div class="product"><img data-asset-slot="special_iced_berry_drink" src="{{special_iced_berry_drink}}" alt="洪都拉斯雪莉桶发酵"><div class="product-name">洪都拉斯雪莉桶发酵</div><div class="product-price">¥35<span class="unit">/杯</span></div></div><div class="product"><img data-asset-slot="special_ethiopia_flower_drink" src="{{special_ethiopia_flower_drink}}" alt="埃塞俄比亚花魁"><div class="product-name">埃塞俄比亚花魁</div><div class="product-price">¥33<span class="unit">/杯</span></div></div></div></section><section class="tea"><h2 class="section-title"><span class="bean-mark" aria-hidden="true"></span><strong>现冲茶饮</strong><small>XIANCHONGCHAYIN</small></h2><div class="split-list"><div class="list"><div class="row"><span class="item"><span class="recommend" aria-label="推荐"></span>英式红茶</span><span class="spec">热/冷</span><span class="price">¥20<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">玫瑰花茶</span><span class="spec">热/冷</span><span class="price">¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">铁观音</span><span class="spec">热</span><span class="price">¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">小青柑</span><span class="spec">热</span><span class="price">¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item plain-indent">云南普洱</span><span class="spec">热</span><span class="price">¥23<span class="unit">/杯</span></span></div></div><div class="list"><div class="row"><span class="item">碧螺春</span><span class="spec">热</span><span class="price">¥25<span class="unit">/杯</span></span></div><div class="row"><span class="item">白茶</span><span class="spec">热</span><span class="price">¥23<span class="unit">/杯</span></span></div><div class="row"><span class="item">正山小种</span><span class="spec">热</span><span class="price">¥25<span class="unit">/杯</span></span></div><div class="row"><span class="item">老枞红茶</span><span class="spec">热</span><span class="price">¥23<span class="unit">/杯</span></span></div></div></div></section><footer class="store"><div class="store-placeholder">门店<br>信息</div><div class="store-label">门店信息<div class="store-rule"></div></div></footer></article></main>
```

### 使用与验证边界

参考文案与价格仅用于关系验证，生产必须绑定已确认菜单事实。图像槽必须替换成独立商品素材；预览引用的参考局部不进入生产。纸纹与文字分层，不降低正文透明度。固定价格列禁止换行，长品名增加行高，不覆盖相邻行；“--”为参考中不可选状态，不推断为零价格。双页各自保留安全区，中缝不是页面外边距的替代。图示尺寸是参考比例，不是印刷毫米；出血和装订量需由实际成品规格确定。字体先核实文件、逐字覆盖及许可，胡敬礼禁用，不默认得意黑。

<a id="combination.invitation-spring-envelope"></a>

**设计方法**：[邀请函风格、布局、配色与质感](../../../../references/style/coding/scenarios/announcement-poster-spec.md#invitation-visual-css-routing)。先按 Spec 选型与确定画幅，再绑定本配方的原子和必选素材。

## 春绿水彩信封邀请函

风格标签：二级：诗性浪漫风 / 书信叙事。

满版水彩场域上，居中信纸伸入绿色信封；前封片遮纸不遮内容，封印置交界。不是上下两张卡片。背景和燕子为素材职责，信纸、折片、文字为原生层。原图叠在英文里的花体仅是局部书写点缀，不强制替换每个A。

配色覆盖：春绿#92b875/#6e994b、象牙纸#fffef0、黑#172010、金#c39a4b。纸面只让背景色含alpha，正文保持不透明。中文主题直立宋形约70–78px，英文高反差衬线约72px，日期细拉丁60px，信息24–28px；字体的可用family以运行诊断为准。

引用[信纸插入](../layouts/overlap-and-collage.md#layout.letter-in-envelope)、[信封折片](../shapes/notes-and-paper.md#shape.envelope-flaps)、[蜡封](../surfaces/craft-detail.md#shape.wax-seal)。正文末行与折片最高点保留42px，封印不侵入活动地址。文案增长用内容流撑高信纸；若画布高度被用户锁定，调整信息分配后再次验收，不隐去文字。

效果按层绑定，以下值为658px样本的校准起点。复用[通用渐变](../colors/palettes.md#color.gradient)，参数留在组合，不另建同机制原子。背景和封印均为必选资产；纯色底或空封印不能作为此组合的完成效果。

| 效果／承载对象 | 实现、范围与验收 |
|---|---|
| 水彩晕染、颗粒／满版底图 | `spring_watercolor`：浅绿至象牙白、左下深叶绿；湿边、不均匀沉色与约1–3px颗粒（658px成图）；叶片集中四周，中央保持低频净空。满版img覆盖，normal、opacity=1、不平铺，不再叠全页噪点。 |
| 金箔碎片、细金线／同一底图 | 金箔约2–20px碎片及局部更大不规则金斑，细金线约1–2px跨场域；浅金亮部与赭金凹处并存。保持边缘集中、中心疏散；不是同尺寸圆点，缩图仍能辨认金斑与水彩颗粒。已含于底图时不重复加粒子或金线。 |
| 透底信纸／paper背景paint | 从顶部象牙白alpha=.94，经26%的.82、70%的.52，到底部.36；只渐变背景色，不降低article或文字opacity，不模糊底图。纸面越向下越可见叶片、色晕和金线；顶部标题净空仍清楚，不能变成整张不透明奶油卡。 |
| 信封分面／三个折片 | 左右分别135°/225°，浅绿#9abf77→#54823e；前封片180°，#91b66a→#76a452。只用面内渐变表现方向与轻微深度，不附加粗纸纹、玻璃高光或全框投影；交界可辨，渐变不进入信纸正文。 |
| 金色压印／seal透明素材 | `spring_seal`：浅浮雕、不规则圆边、冠形中心；左上乳金窄高光、浅香槟金面、右下蜜金凹槽。复用蜡封的几何职责；旧生成器的暗色GO样例不作为此金属材质验收。透明边界、独立img、约80px盒（可见印章约68–74px），72px缩图仍见高光与冠形，不能退成棕色泥蜡。 |

素材绑定：骨架中的`{{spring_watercolor}}`与`{{spring_seal}}`必须替换成就绪资产；上表同时是生成／检索条件。背景坐标绑定整页，纸面透出同一张底图而非另铺第二张纸纹。换底图后只调paper的alpha色标（上段建议.88–.98，下段.30–.60）；地址后方出现高频枝叶时先调整素材净空，不能降低正文透明度。可选燕子单独叠前景并避让准确文字。

字体与素材：以下是可编辑排版与素材槽位的组合，不声称复原原品牌字体或三维成像。正式字体按[字体绑定契约](#combination-font-binding)核验真实family/weight/style，文案增长应调整行数、区域高度和净空，不默认缩字。样本为658px宽；值为视觉估计。二维码为可替换真实资产，示例不提供可扫码活动地址。

```css
.iv-spring { position:relative; isolation:isolate; box-sizing:border-box; padding:42px 64px 36px; min-height:1424px; background:#d8e8bd; color:#172010; font-family:"Songti SC"; }
.iv-spring__backdrop { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; object-position:center; z-index:-1; pointer-events:none; }
.iv-spring__seal { display:block; width:100%; height:100%; object-fit:contain; }
.iv-spring__header { text-align:center; margin-bottom:32px; }
.iv-spring__wordmark { font:400 70px "Bodoni 72"; letter-spacing:1px; margin:36px 0 0; }
.iv-spring__subtitle { font-size:36px; margin:0; }
.iv-spring__letter { --vl-paper-paint:linear-gradient(180deg,rgba(255,254,240,.94) 0%,rgba(255,254,240,.82) 26%,rgba(255,254,240,.52) 70%,rgba(255,254,240,.36) 100%); --vl-fold-light:#9abf77; --vl-fold-dark:#54823e; --vl-front-light:#91b66a; --vl-front-dark:#76a452; --vl-seal-size:80px; --vl-paper-top:62px; --vl-paper-side:36px; --vl-paper-radius:44px; --vl-envelope-depth:174px; --vl-letter-safe:42px; --vl-letter-gap:38px; text-align:center; }
.iv-spring__theme { font-size:72px; line-height:1.28; font-weight:400; padding:6px 0; margin:30px 0 12px; }
.iv-spring__script { font:italic 42px Baskerville; color:#88a955; margin:0; }
.iv-spring__date { font:400 58px Baskerville; margin:6px 0 0; }
.iv-spring__info { font-size:24px; line-height:1.6; }
.iv-spring__footer { display:flex; justify-content:space-between; font:20px Baskerville; letter-spacing:2px; margin-top:46px; color:#fffef0; }
```

```html
<section class="iv-spring"><img class="iv-spring__backdrop" src="{{spring_watercolor}}" alt="" aria-hidden="true"><header class="iv-spring__header"><p style="text-align:left;font-size:20px;font-family:Songti SC">品牌名称</p><p class="iv-spring__wordmark">INVITATION</p><p class="iv-spring__subtitle">（邀请函）</p></header><section class="vl-letter-envelope iv-spring__letter"><article class="vl-letter-envelope__paper"><div class="vl-letter-envelope__content"><p class="iv-spring__info" style="margin:0">诚挚邀请您莅临我们的开业活动</p><div><h1 class="iv-spring__theme">春启新程<br>共赴美好</h1><p class="iv-spring__script">A New Beginning</p></div><div class="iv-spring__info"><p style="margin:0">活动时间</p><p class="iv-spring__date">06/28</p><p style="font:22px Arial;margin:4px 0">18:00–21:00</p></div><div class="iv-spring__info"><p style="margin:0">活动地点</p><p style="margin:0">城市会客厅 · 五层</p></div></div></article><div class="vl-letter-envelope__front"><div class="vl-envelope-flaps" aria-hidden="true"><span class="vl-envelope-flaps__left"></span><span class="vl-envelope-flaps__right"></span><span class="vl-envelope-flaps__front"></span></div></div><div class="vl-letter-envelope__seal"><img class="iv-spring__seal" src="{{spring_seal}}" alt="金色冠形压印装饰"></div></section><footer class="iv-spring__footer"><span>Nature</span><span>Life</span><span>Beautiful</span></footer></section>
```


<a id="combination.notice-cobalt-paper"></a>

**原子布局对应**：[notice-sheet-stack](../layouts/notice-and-invitation.md#layout.title-letter-stack)、[notice-split-masthead](../layouts/notice-and-invitation.md#layout.split-masthead)、[notice-contact-footer](../layouts/notice-and-invitation.md#layout.contact-footer)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。

## 蓝纸双语公告

**设计选型**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

**产物标签**：公告通知；竖版单屏。适合社媒单张发布；不能直接当多章节长图或商品详情页模板。

**组合状态**：已完成静态结构检查；未做完整视觉渲染验收。

**可复用原子**：[layout.reading-column](../layouts/airy-and-spacious.md#layout.reading-column)、[shape.torn-paper](../shapes/tickets-and-notches.md#shape.torn-paper)、[shape.paper-curl](../surfaces/craft-detail.md#shape.paper-curl)、[surface.light-paper](../surfaces/paper-and-print.md#surface.light-paper)。以下CSS为这些机制的独立、作用域隔离示例，不要求重复叠加原子默认样式；沿用本组合的色值、尺度和作用对象。

### 布局、字体与素材关系

```json
{
  "artifact_tags": [
    "固定画布公告",
    "蓝色纸张",
    "双语排版",
    "外围撕纸拼贴",
    "独立品牌素材",
    "独立二维码",
    "可编辑DOM文案"
  ],
  "dimensions": {
    "canvas": [
      658,
      1170
    ],
    "paper": [
      25,
      90,
      603,
      1009
    ],
    "units": "px",
    "responsive": false
  },
  "layout": {
    "structure": "外围拼贴底层、中央蓝纸、左上中英文标题、右上品牌标识、中文正文、英文正文、底部二维码及说明。",
    "title_bounds": [
      87,
      168,
      370,
      121
    ],
    "chinese_body_bounds": [
      91,
      324,
      466,
      230
    ],
    "english_body_bounds": [
      91,
      608,
      468,
      270
    ],
    "footer_bounds": [
      75,
      928,
      495,
      125
    ],
    "text_handling": "正文使用DOM；中文自然折行，英文保留参考图的行末断词。正文以min-height预留空间，不设置overflow:hidden。"
  },
  "palette": {
    "outer_blue": "#064578",
    "paper_blue": "#086AF4",
    "paper_deep_blue": "#0051E8",
    "text_ivory": "#FFFFED",
    "collage_yellow": "#F0D000",
    "collage_orange": "#F04410",
    "fold_gray": "#B9CED5"
  },
  "relationships": [
    {
      "between": [
        "外围背景",
        "中央蓝纸容器"
      ],
      "detail": "四条局部背景素材覆盖画布外围，中央纸张在x=25、y=90处叠于其上；底部留71px外围拼贴，纸张右侧保留30px。"
    },
    {
      "between": [
        "左上折角素材",
        "蓝纸容器"
      ],
      "detail": "折角在画布[25,90,133,50]处独立叠加，覆盖纸张左上边缘；不与标题混裁。"
    },
    {
      "between": [
        "品牌素材",
        "标题与蓝纸容器"
      ],
      "detail": "品牌位于纸张内[452,63,81,139]，与左侧标题并列；距纸张右边70px，标题框与品牌框间隔20px。"
    },
    {
      "between": [
        "正文",
        "蓝纸容器及品牌素材"
      ],
      "detail": "两种语言正文均从画布x=91起排，距纸张左边66px；中文位于标题及品牌下方，英文从y=608起独立成段，不覆盖任何品牌素材。"
    },
    {
      "between": [
        "二维码素材",
        "页脚文字与纸张"
      ],
      "detail": "二维码位于画布约[279,928,88,89]，下方7px开始两行说明；页脚整体近纸张水平中心，底部保留约47px。"
    }
  ],
  "safe_areas": [
    {
      "target": "背景与纸张",
      "bounds": [
        25,
        90,
        603,
        1009
      ],
      "rule": "外围拼贴不得向此区域追加带文字的裁切；允许独立折角覆盖左上50px高度。"
    },
    {
      "target": "标题",
      "bounds": [
        87,
        168,
        370,
        121
      ],
      "rule": "保持与右侧品牌至少20px框间距，与折角底部至少28px间距。"
    },
    {
      "target": "品牌",
      "bounds": [
        467,
        143,
        101,
        159
      ],
      "rule": "品牌图像四周预留约10px，不侵入正文首行。"
    },
    {
      "target": "中文正文",
      "bounds": [
        91,
        324,
        466,
        230
      ],
      "rule": "区域足以排下当前文案；中文签名与英文首行之间保留空白，不裁字。"
    },
    {
      "target": "英文正文",
      "bounds": [
        91,
        608,
        468,
        270
      ],
      "rule": "当前正文约248px高；至二维码顶部另留50px以上，不允许文字覆盖二维码。"
    },
    {
      "target": "二维码及说明",
      "bounds": [
        75,
        918,
        495,
        145
      ],
      "rule": "二维码四周不得叠加装饰；生产替换二维码时应使用含规范静区的确认版本，并验证实机识别。"
    }
  ],
  "fonts": [
    {
      "target": "中文主标题",
      "family": "Source Han Sans CN",
      "weight": 700,
      "size_px": 49,
      "note": "使用已安装候选中的粗黑体近似参考，不声称与原图定制字形相同。"
    },
    {
      "target": "英文主标题",
      "family": "Arial",
      "weight": 700,
      "size_px": 34,
      "note": "紧字距与紧行距近似原图紧凑粗体效果。"
    },
    {
      "target": "中文正文及页脚",
      "family": "Source Han Sans SC",
      "weight": 400,
      "size_px": [
        15,
        12
      ]
    },
    {
      "target": "英文正文",
      "family": "Arial",
      "weight": 400,
      "size_px": 15.5
    }
  ],
  "texture": {
    "default": "中央纸纹为普通CSS渐变近似，仅模拟明暗折痕，不能等同原图真实纤维、磨损及油墨颗粒。",
    "real_texture_strategy": "以原图无字区域[40,870,225,145]作为蓝纸颗粒与颜色参考，离线生成603×1009无文字、无logo、无二维码的蓝色皱纸材质；通过纹理合成与低频折痕重建消除重复接缝，检查无残留字形。作为本地材质通过--notice-1-paper-texture:url(...)注入，不使用整张海报截图。",
    "perimeter": "外围撕纸与左上折角保留独立局部图像素材，避免CSS伪造复杂纸边。"
  },
  "asset_strategy": {
    "default_network": "无外网依赖，所有{{slot}}由本地资源或data URI绑定。",
    "cropping": "裁切坐标均相对658×1170原图，使用[x,y,w,h]。外围只取可见边带；logo、二维码和折角均独立裁切，不包含旁边正文。",
    "logo": "验证使用原图局部裁切，正式制作优先绑定经授权的透明品牌文件。",
    "qr": "参考二维码仅用于视觉复现，不保证截图码可识别或链接仍有效；生产须绑定已确认公众号地址生成的清晰二维码。",
    "editable_content": "除真实品牌图形与二维码内部信息外，标题、正文、署名及扫码说明均为可编辑DOM。"
  },
  "limits": [
    "仅执行当前图1，不混入其余图的设计元素。",
    "当前转录为参考图演示文案；三年、第四年、千余个夜晚、署名和公众号身份等生产内容必须绑定已确认事实，不能直接作为真实公告发布。",
    "原图清晰度限制细小纹理及二维码中心微字的判断，不额外虚构无法辨认内容。",
    "品牌及二维码裁切带少量原图蓝底，可能与CSS近似纸色产生轻微边界；正式透明logo及独立生成二维码可改善。",
    "参考中文粗标题与英文标题存在印刷或定制字形差异，所选字体仅为可用字体近似。",
    "固定画布以当前全文排版校准；更换更长文案必须重新排版、调整字号或段距，不得使用隐藏溢出裁掉正文。",
    "外围边带含原图已有的装饰性残缺印刷痕迹，作为材质保留，不猜测补写其含义。"
  ]
}
```

### CSS 与可编辑文字骨架

```css
.notice-1{position:relative;width:658px;height:1170px;isolation:isolate;background:#064578;color:#ffffed;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-1 *{box-sizing:border-box}.notice-1 .perimeter{position:absolute;z-index:0;display:block;pointer-events:none}.notice-1 .edge-top{left:0;top:0;width:658px;height:90px}.notice-1 .edge-left{left:0;top:90px;width:25px;height:1009px}.notice-1 .edge-right{left:628px;top:90px;width:30px;height:1009px}.notice-1 .edge-bottom{left:0;top:1099px;width:658px;height:71px}.notice-1 .paper{position:absolute;z-index:1;left:25px;top:90px;width:603px;height:1009px;background:linear-gradient(165deg,rgba(101,199,255,.23),transparent 17%,rgba(0,38,191,.15) 37%,transparent 49%),linear-gradient(10deg,transparent 46%,rgba(0,28,132,.2) 46.4%,transparent 49%),linear-gradient(174deg,transparent 55%,rgba(0,48,161,.25) 55.5%,transparent 57%),linear-gradient(120deg,#086af4,#0051e8 62%,#096df3);box-shadow:2px 3px 3px #002b65}.notice-1 .paper:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.3;background-image:var(--notice-1-paper-texture,none),repeating-linear-gradient(173deg,transparent 0 37px,rgba(185,228,255,.12) 38px,transparent 41px 78px),repeating-linear-gradient(24deg,transparent 0 69px,rgba(0,34,136,.15) 71px,transparent 75px 122px);background-size:cover,auto,auto}.notice-1 .fold{position:absolute;z-index:3;left:25px;top:90px;width:133px;height:50px;display:block}.notice-1 .heading{position:absolute;left:62px;top:78px;width:370px}.notice-1 h1{margin:0;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:49px;line-height:1.15;letter-spacing:-2px}.notice-1 .heading-en{margin:4px 0 0;font-family:Arial,sans-serif;font-size:34px;line-height:.86;font-weight:700;letter-spacing:-1.2px}.notice-1 .brand{position:absolute;left:452px;top:63px;width:81px;height:139px;object-fit:contain}.notice-1 .copy-cn{position:absolute;left:66px;top:234px;width:466px;min-height:230px;font-size:15px;line-height:27px;letter-spacing:.55px}.notice-1 p{margin:0}.notice-1 .copy-cn .gap{margin-top:24px}.notice-1 .copy-cn .sign{margin-top:25px}.notice-1 .copy-en{position:absolute;left:66px;top:518px;width:468px;min-height:270px;font-family:Arial,sans-serif;font-size:15.5px;line-height:21.25px;font-weight:400}.notice-1 .copy-en .gap{margin-top:21px}.notice-1 .copy-en .sign{margin-top:20px}.notice-1 .footer{position:absolute;left:50px;top:838px;width:495px;text-align:center}.notice-1 .qr{display:block;width:88px;height:89px;margin:0 auto;object-fit:contain}.notice-1 .qr-caption{margin-top:7px;font-size:12px;line-height:15px;font-weight:400;letter-spacing:0}
```

```html
<div class="notice-1"><img class="perimeter edge-top" data-asset-slot="edge_top" src="{{edge_top}}" alt=""><img class="perimeter edge-left" data-asset-slot="edge_left" src="{{edge_left}}" alt=""><img class="perimeter edge-right" data-asset-slot="edge_right" src="{{edge_right}}" alt=""><img class="perimeter edge-bottom" data-asset-slot="edge_bottom" src="{{edge_bottom}}" alt=""><main class="paper"><header class="heading"><h1>重要公告</h1><p class="heading-en" lang="en">IMPORTANT<br>ANNOUNCEMENT</p></header><img class="brand" data-asset-slot="one_third_logo" src="{{one_third_logo}}" alt="1/3 ONE THIRD"><section class="copy-cn" lang="zh-CN" aria-label="中文公告"><p>尊敬的你，<br>这不是一份演出取消通知，但这是一份重要公告：</p><p class="gap">三年间，ONE THIRD与你度过了千余个夜晚，在跨入第四年之际，感谢你一直以来的大力支持，期待我们的下一次相遇！</p><p class="sign">此致<br>ONE THIRD团队</p></section><section class="copy-en" lang="en" aria-label="English announcement"><p>DEAR YOU,<br>WE'RE NOT HERE TO ANNOUNCE A PERFORMANCE CANCELLA-<br>TION BUT AN IMPORTANT MESSAGE:</p><p class="gap">OVER THE PAST THREE YEARS, ONE THIRD HAS SPENT MORE<br>THAN A THOUSAND NIGHTS WITH YOU. AND, NOW WE'RE EN-<br>TERING OUR FOURTH YEAR! THANK YOU FOR YOUR CONTIN-<br>UED SUPPORT. WE'RE LOOKING FORWARD TO SEEING YOU<br>NEXT TIME!</p><p class="sign">SINCERELY,<br>ONE THIRD TEAM</p></section><footer class="footer"><img class="qr" data-asset-slot="notice_qr" src="{{notice_qr}}" alt="ONE THIRD微信公众号二维码"><p class="qr-caption">长按识别二维码，关注ONE THIRD微信公众号<br>了解更多嘉宾及派对信息</p></footer></main><img class="fold" data-asset-slot="paper_fold" src="{{paper_fold}}" alt=""></div>
```

### 素材绑定与验证边界

- `edge_top`：顶部蓝底、黄色撕纸及两角拼贴，无公告正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `edge_left`：纸张左侧外围撕纸与蓝色底材窄带，不含正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `edge_right`：右侧外围橙黄碎纸及蓝底窄带，不含公告正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `edge_bottom`：底部紫色、橙红色及蓝色撕纸拼贴。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `paper_fold`：中央蓝纸左上灰色翻折纸角及其阴影，不含标题。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `one_third_logo`：独立1/3与ONE THIRD品牌标识，不含左侧标题及下方正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `notice_qr`：独立二维码及其白边，不含下方扫码说明文字。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。

参考正文、品牌、日期和二维码仅作内部排版样本，不是已确认业务事实。正式生成替换为确认内容；图片槽不得直接引用参考整图或演示裁片。复杂纹理未生成时只能标记近似/待补；页面与文字层不可整体降低透明度。长文先调整分组、容器容量或拆页，不能隐藏溢出；更换标题、字体、素材、尺寸必须重查正文和图片安全区。字体绑定真实文件及字重，核验逐字覆盖；胡敬礼禁用，得意黑不默认回退。正式交付按主Skill路由将样式绑定到图层/行内CSS，示例style规则本身不替代交付协议。


<a id="combination.notice-school-notebook"></a>

**原子布局对应**：[notice-bound-letter](../layouts/notice-and-invitation.md#layout.bound-paper-stack)、[notice-fact-sections](../layouts/notice-and-invitation.md#layout.labeled-facts)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。

## 校园装订通知

**设计选型**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

**产物标签**：公告通知；竖版单屏。适合社媒单张发布；不能直接当多章节长图或商品详情页模板。

**组合状态**：已完成静态结构检查；未做完整视觉渲染验收。

**可复用原子**：[layout.section-masthead](../layouts/layout-and-type.md#layout.section-masthead)、[shape.badge](../shapes/capsules-and-badges.md#shape.badge)、[surface.light-paper](../surfaces/paper-and-print.md#surface.light-paper)。以下CSS为这些机制的独立、作用域隔离示例，不要求重复叠加原子默认样式；沿用本组合的色值、尺度和作用对象。

### 布局、字体与素材关系

```json
{
  "artifact_tags": [
    "图2",
    "固定尺寸公告海报",
    "异形黄色副标题",
    "橙色装订纸",
    "可编辑中文DOM",
    "独立插画素材",
    "无外网依赖"
  ],
  "dimensions": {
    "width": 658,
    "height": 1170,
    "unit": "px",
    "coordinate_origin": "原图左上角",
    "body_region": [
      101,
      470,
      464,
      610
    ]
  },
  "layout": "左上品牌区；顶部红黑双色大标题与拼音；下接黄色异形纸片上的两行副标题；正文位于橙色圆角描边信纸中，六枚橙色装订条跨压上边框；插画沿容器外围和底角分布。根画布固定658×1170，只有画布裁切外伸装饰，正文容器不裁切文字。",
  "palette": {
    "canvas": "#fffaf0",
    "paper": "#fffef9",
    "title_red": "#ff3b10",
    "text": "#090909",
    "subtitle_yellow": "#ffda22",
    "highlight_yellow": "#f6d537",
    "border_orange": "#f7af2b",
    "binding_orange": "#fa9d17",
    "background_yellow": "#fff29a",
    "illustration_accents": [
      "#20bfdf",
      "#3fc6a2",
      "#ff9719"
    ]
  },
  "relationships": [
    "背景与容器：奶油色根背景铺满画布，淡黄有机色块处于最底层；正文纸张在其上以不透明暖白底遮挡，橙框独立清晰。",
    "素材与容器：蓝书位于正文纸张左上方，绿色角色位于右上方；装订条跨越纸张上边框。左侧绿芽、右侧红书和左下橙色角色覆盖边框，形成前后层次。",
    "文字与容器：副标题居中排在黄色异形纸片主体内，不进入下方尖角；正文从纸张左边内缩57px，上边内缩44px，签名右对齐。",
    "文字与素材：左侧插画不进入正文起始列，右侧红书避开提示及落款文本；右中黄色星星放在会议地点右侧留白，不叠压议程。",
    "标题与背景：红色“重要”和黑色“通知”均为独立可编辑文字，采用不同字号及轻微旋转；拼音位于黑色标题上方，黄线独立置于标题与副标题之间。"
  ],
  "safe_areas": [
    {
      "scope": "背景与正文容器",
      "rect": [
        49,
        431,
        560,
        687
      ],
      "rule": "纸张内部覆盖背景色块；描边内侧不得出现未去底素材的矩形底色。"
    },
    {
      "scope": "正文文字",
      "rect": [
        101,
        470,
        464,
        610
      ],
      "rule": "正文完整排入此区域，底部至纸张内边保留约38px；禁止通过overflow:hidden压掉增补文字。"
    },
    {
      "scope": "副标题文字",
      "rect": [
        128,
        283,
        402,
        84
      ],
      "rule": "只放两行标题，不进入黄色纸片尾部尖角，左下蓝书仅靠近外缘。"
    },
    {
      "scope": "主标题与拼音",
      "rect": [
        83,
        94,
        503,
        163
      ],
      "rule": "主标题不得碰品牌区；拼音、叶片、引号分属独立位置，替换字体后需核查字形边界。"
    },
    {
      "scope": "外围素材",
      "rect": [
        18,
        326,
        626,
        844
      ],
      "rule": "各插画遵守自己的定位框，除明确跨框的装饰外不得侵入正文；左下角色允许在画布底部自然裁断。"
    },
    {
      "scope": "品牌",
      "rect": [
        29,
        22,
        219,
        61
      ],
      "rule": "真实logo仅使用独立图像；品牌文字与logo保持16px间隔。"
    }
  ],
  "fonts": [
    {
      "role": "主标题",
      "family": "Source Han Sans CN",
      "weight": 700,
      "size_px": [
        137,
        117
      ],
      "note": "已安装候选中采用粗黑体近似；原图标题有定制字形与不规则笔画，此处不宣称同款字体。"
    },
    {
      "role": "副标题及正文",
      "family": "Source Han Sans SC",
      "weight": 400,
      "size_px": [
        35,
        20,
        19
      ],
      "note": "使用显式换行与分段DOM保持内容可编辑。"
    },
    {
      "role": "称谓、栏目标签及提示标题",
      "family": "Source Han Sans CN",
      "weight": 700,
      "size_px": [
        21,
        20
      ]
    },
    {
      "role": "品牌占位文字及拼音",
      "family": "Arial",
      "weight": 400,
      "size_px": [
        27,
        31
      ],
      "note": "拼音的手写感仅近似。"
    },
    {
      "role": "装饰引号",
      "family": "Songti SC",
      "weight": 700,
      "size_px": 77,
      "note": "旋转字体引号近似原图手绘笔触。"
    }
  ],
  "texture": "默认使用暖白纯色纸面、淡黄色块与CSS异形边缘，属于普通CSS纸感近似，不包含真实扫描纸纹；原图整体较平滑，不额外添加明显噪点。",
  "asset_strategy": "所有复杂角色、星星、叶片及真实logo使用独立本地img槽，默认无外网请求。assets中的crop为原图局部验证框，不含旁边正文。插画须从相应框提取后去除背景、黄底和边框残片，导出保持原框尺寸及透明留白的PNG/WebP，避免矩形裁图压住CSS容器。blue_book框内有少量副标题纸片和黑色装饰短线，不含副标题正文；只保留书本及其自身装饰线。orange_mascot保留角色、喇叭及声波，清除原纸张边框。若生产需要真实纸纹，从原图[260,8,240,72]无字奶油背景和[251,1004,80,99]无字纸面分别采样，去除光照渐变并进行无缝纹理合成，生成独立透明低对比纹理本地资源；不得直接将含文案的整张图用作背景。",
  "limits": [
    "仅重建当前图2，不混用其他图的蓝纸、故障字、爆炸标题或独立银色喇叭。",
    "HTML文案按参考转录，20xx、YOUR LOGO、稿定学校学生发展中心及会议安排均为演示内容；生产必须绑定已确认学校、日期、星期、时间、地点及议程，不得将占位内容当作事实。",
    "参考副标题为第二学期，正文称学期初，落款为20xx年12月15日；保留参考措辞，但生产需核实通知日期与会议日期的实际对应关系。",
    "未辨明或未出现的内容不补写；本图没有二维码，不新增二维码槽。",
    "CSS黄色异形纸、背景色块、手绘引号、黄线及标题字形是可编辑近似，不是原始矢量路径或定制字体的精确复刻。",
    "字体使用指定已安装字体，无远程字体；不同平台字形度量可能略变，交付前须在658×1170实尺寸检查议程末行和会议时间行。",
    "正文使用足够高度的可见内容区，未设置文本裁切；若生产文案增长，应调整字号、行距或结构并重新校验，不能隐藏溢出文字。",
    "素材透明化必须保留抗锯齿边缘；裁切框仅用于定位验证，不应把框内背景直接当成插画的一部分。"
  ]
}
```

### CSS 与可编辑文字骨架

```css
.notice-2{position:relative;width:658px;height:1170px;isolation:isolate;overflow:hidden;background:#fffaf0;color:#090909;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-2 *{box-sizing:border-box}.notice-2 .wash{position:absolute;z-index:0;background:#fff29a}.notice-2 .wash-left{left:-105px;top:593px;width:278px;height:383px;border-radius:45% 56% 46% 40%;transform:rotate(-13deg)}.notice-2 .wash-right{left:451px;top:322px;width:301px;height:264px;border-radius:61% 26% 42% 44%;transform:rotate(-25deg)}.notice-2 .wash-bottom{left:387px;top:932px;width:345px;height:334px;border-radius:53% 38% 0 0;transform:rotate(8deg)}.notice-2 .brand{position:absolute;left:29px;top:22px;display:flex;align-items:center;gap:16px;z-index:3}.notice-2 .brand img{display:block;width:60px;height:61px}.notice-2 .brand-label{font-family:Arial,sans-serif;font-size:27px;color:#dc381c;white-space:nowrap}.notice-2 .title{position:absolute;left:83px;top:99px;width:503px;height:160px;margin:0;z-index:2;font-family:'Source Han Sans CN',sans-serif;font-weight:700;white-space:nowrap;letter-spacing:-8px}.notice-2 .title-red{position:absolute;left:0;top:-5px;color:#ff3b10;font-size:137px;line-height:1.12;transform:rotate(-5deg)}.notice-2 .title-black{position:absolute;left:247px;top:25px;font-size:117px;line-height:1;transform:rotate(-4deg);letter-spacing:-9px}.notice-2 .pinyin{position:absolute;left:362px;top:94px;z-index:3;font-family:Arial,sans-serif;font-size:31px;letter-spacing:1px;transform:rotate(1deg)}.notice-2 .quote{position:absolute;color:#eca50b;font-family:'Songti SC',serif;font-size:77px;font-weight:700;line-height:1;z-index:2}.notice-2 .quote-left{left:31px;top:107px;transform:rotate(-9deg)}.notice-2 .quote-right{left:591px;top:177px;transform:rotate(9deg)}.notice-2 .underline{position:absolute;left:302px;top:237px;width:270px;height:20px;z-index:2;background:#f3d42a;clip-path:polygon(0 76%,48% 0,53% 14%,54% 45%,77% 11%,100% 4%,100% 28%,75% 37%,51% 75%,51% 32%,1% 100%)}.notice-2 .subtitle-paper{position:absolute;left:103px;top:264px;width:453px;height:141px;z-index:2;background:#ffda22;clip-path:polygon(0 34%,3% 15%,6% 6%,22% 1%,37% 4%,68% 0,82% 4%,93% 2%,98% 7%,100% 19%,99% 43%,96% 54%,84% 56%,78% 80%,68% 87%,61% 100%,59% 96%,57% 81%,39% 78%,21% 76%,13% 66%,5% 58%,1% 47%)}.notice-2 .subtitle{position:absolute;left:128px;top:283px;width:402px;margin:0;z-index:3;text-align:center;font-size:35px;line-height:1.2;letter-spacing:0;font-weight:400}.notice-2 .paper{position:absolute;left:44px;top:426px;width:570px;height:697px;border:5px solid #f7af2b;border-radius:30px;background:#fffef9;z-index:1}.notice-2 .binding{position:absolute;top:410px;width:10px;height:39px;border-radius:2px;background:#fa9d17;z-index:5}.notice-2 .b1{left:105px}.notice-2 .b2{left:143px}.notice-2 .b3{left:180px}.notice-2 .b4{left:472px}.notice-2 .b5{left:509px}.notice-2 .b6{left:547px}.notice-2 .copy{position:absolute;left:101px;top:470px;width:464px;min-height:610px;z-index:3;font-size:20px;line-height:25px;letter-spacing:0}.notice-2 .copy p{margin:0}.notice-2 .copy strong{font-family:'Source Han Sans CN',sans-serif;font-weight:700}.notice-2 .salutation{font-size:21px;line-height:28px}.notice-2 .intro{margin-top:21px!important;text-indent:2.2em}.notice-2 .details{margin-top:10px}.notice-2 .detail-row{display:flex;align-items:baseline;gap:12px;min-height:35px;white-space:nowrap}.notice-2 .label{position:relative;display:inline-block;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:21px;line-height:29px;z-index:0}.notice-2 .label:before{content:'';position:absolute;left:-7px;right:-7px;bottom:2px;height:12px;z-index:-1;border-radius:9px;background:#f6d537;transform:rotate(-1deg)}.notice-2 .agenda-title{margin-top:0!important}.notice-2 .agenda{list-style:none;padding:0;margin:7px 0 0;font-size:19px;line-height:32px;white-space:nowrap}.notice-2 .agenda li{display:flex;align-items:baseline;gap:11px}.notice-2 .check{display:inline-block;position:relative;flex:0 0 17px;width:17px;height:15px;border:1px solid #8e8d7b;top:1px}.notice-2 .check:after{content:'';position:absolute;left:2px;top:-4px;width:16px;height:9px;border-left:3px solid #ed8621;border-bottom:3px solid #ed8621;transform:rotate(-43deg)}.notice-2 .tips{margin-top:20px;line-height:25px}.notice-2 .closing{margin-top:22px!important;text-indent:2.2em;line-height:25px}.notice-2 .signature{margin-top:23px!important;text-align:right;padding-right:14px;line-height:25px}.notice-2 .asset{position:absolute;display:block;object-fit:contain;z-index:4}.notice-2 .leaf{left:523px;top:57px;width:77px;height:68px}.notice-2 .star-top{left:44px;top:243px;width:49px;height:50px}.notice-2 .book-blue{left:64px;top:328px;width:139px;height:84px}.notice-2 .grass-right{left:540px;top:326px;width:89px;height:76px}.notice-2 .grass-left{left:18px;top:649px;width:61px;height:52px}.notice-2 .star-paper{left:522px;top:682px;width:51px;height:51px}.notice-2 .book-red{left:562px;top:849px;width:82px;height:89px}.notice-2 .mascot{left:18px;top:998px;width:222px;height:172px;z-index:6}
```

```html
<div class="notice-2"><div class="wash wash-left" aria-hidden="true"></div><div class="wash wash-right" aria-hidden="true"></div><div class="wash wash-bottom" aria-hidden="true"></div><div class="brand"><img data-asset-slot="brand_logo" src="{{brand_logo}}" alt="稿定标志"><span class="brand-label">YOUR LOGO</span></div><img class="asset leaf" data-asset-slot="orange_leaf" src="{{orange_leaf}}" alt=""><span class="quote quote-left" aria-hidden="true">“</span><h1 class="title"><span class="title-red">重要</span><span class="title-black">通知</span></h1><span class="pinyin" aria-hidden="true">tong&nbsp;&nbsp; zhi</span><span class="quote quote-right" aria-hidden="true">”</span><div class="underline" aria-hidden="true"></div><img class="asset star-top" data-asset-slot="yellow_star_top" src="{{yellow_star_top}}" alt=""><div class="subtitle-paper" aria-hidden="true"></div><h2 class="subtitle">关于召开本学年第二学期<br>家长会的通知</h2><img class="asset book-blue" data-asset-slot="blue_book" src="{{blue_book}}" alt="蓝色书本插画"><img class="asset grass-right" data-asset-slot="green_character" src="{{green_character}}" alt="绿色插画"><div class="paper" aria-hidden="true"></div><i class="binding b1" aria-hidden="true"></i><i class="binding b2" aria-hidden="true"></i><i class="binding b3" aria-hidden="true"></i><i class="binding b4" aria-hidden="true"></i><i class="binding b5" aria-hidden="true"></i><i class="binding b6" aria-hidden="true"></i><section class="copy" aria-label="家长会通知正文"><p class="salutation"><strong>尊敬的各位家长：</strong></p><p class="intro">您好！为了加强家校沟通，共同促进学生的健康成长，我校定于近期召开学期初家长会。具体安排如下：</p><div class="details"><div class="detail-row"><span class="label">会议时间</span><span>20xx年2月21日(星期五)晚上18：30</span></div><div class="detail-row"><span class="label">会议地点</span><span>各班教室</span></div><p class="agenda-title"><span class="label">会议议程</span></p><ul class="agenda"><li><span class="check" aria-hidden="true"></span><span>18:30-19:00 校长讲话（校园广播）</span></li><li><span class="check" aria-hidden="true"></span><span>19:00-19:40 各科任老师介绍学期教学计划</span></li><li><span class="check" aria-hidden="true"></span><span>19:40-20:30 班主任介绍班级工作并与家长交流</span></li></ul></div><div class="tips"><p><strong>温馨提示：</strong></p><p>请家长提前安排时间，准时参会；<br>因校园停车位有限，建议您选择绿色出行；<br>会议期间请将手机调至静音模式。</p></div><p class="closing">期待您的莅临，让我们携手共育，为孩子的成长保驾护航！</p><p class="signature">稿定学校学生发展中心<br>20xx年12月15日</p></section><img class="asset grass-left" data-asset-slot="green_sprout" src="{{green_sprout}}" alt=""><img class="asset star-paper" data-asset-slot="yellow_star_paper" src="{{yellow_star_paper}}" alt=""><img class="asset book-red" data-asset-slot="red_book" src="{{red_book}}" alt="红色书本插画"><img class="asset mascot" data-asset-slot="orange_mascot" src="{{orange_mascot}}" alt="举着喇叭的橙色角色插画"></div>
```

### 素材绑定与验证边界

- `brand_logo`：左上红色圆形稿定真实logo；独立提取，不包含右侧YOUR LOGO文字。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `orange_leaf`：标题右上橙色叶片，透明去底保留不规则叶缘。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `yellow_star_top`：主标题左下黄色手绘星形，独立透明素材。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `blue_book`：副标题左下蓝色拟人书本及自身装饰；不包含邻近副标题文字。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `green_character`：正文容器右上带眼睛绿色角色，去除淡黄色背景。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `green_sprout`：正文纸张左侧绿色芽形插画，去除背后纸框残片。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `yellow_star_paper`：正文右侧留白区黄色星星，框内不含议程文字。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `red_book`：正文纸张右侧红色拟人书本，去除纸面、边框及淡黄背景。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `orange_mascot`：左下橙色举喇叭角色及声波，裁至原图底边；不包含右侧落款或上方正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。

参考正文、品牌、日期和二维码仅作内部排版样本，不是已确认业务事实。正式生成替换为确认内容；图片槽不得直接引用参考整图或演示裁片。复杂纹理未生成时只能标记近似/待补；页面与文字层不可整体降低透明度。长文先调整分组、容器容量或拆页，不能隐藏溢出；更换标题、字体、素材、尺寸必须重查正文和图片安全区。字体绑定真实文件及字重，核验逐字覆盖；胡敬礼禁用，得意黑不默认回退。正式交付按主Skill路由将样式绑定到图层/行内CSS，示例style规则本身不替代交付协议。


<a id="combination.notice-lime-letter"></a>

**原子布局对应**：[notice-sheet-stack](../layouts/notice-and-invitation.md#layout.title-letter-stack)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。

## 荧光信纸公告

**设计选型**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

**产物标签**：公告通知；竖版单屏。适合社媒单张发布；不能直接当多章节长图或商品详情页模板。

**组合状态**：已完成静态结构检查；未做完整视觉渲染验收。

**可复用原子**：[layout.reading-column](../layouts/airy-and-spacious.md#layout.reading-column)、[surface.neon-edge](../surfaces/diffuse-light.md#surface.neon-edge)、[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)。以下CSS为这些机制的独立、作用域隔离示例，不要求重复叠加原子默认样式；沿用本组合的色值、尺度和作用对象。

### 布局、字体与素材关系

```json
{
  "artifact_tags": [
    "图3",
    "固定尺寸公告海报",
    "荧光绿故障标题",
    "深色渐变背景",
    "灰色信纸",
    "双语致歉信",
    "可编辑DOM"
  ],
  "dimensions": {
    "width": 658,
    "height": 1266,
    "unit": "px",
    "root": ".notice-3",
    "responsive": false
  },
  "layout": {
    "top_logo": [
      258,
      48,
      152,
      76
    ],
    "editable_glitch_heading": [
      43,
      177,
      573,
      178
    ],
    "transparent_title_panel": [
      47,
      326,
      564,
      136
    ],
    "white_slogan_strip": [
      47,
      465,
      564,
      18
    ],
    "gray_letter": [
      47,
      499,
      564,
      656
    ],
    "chinese_copy": [
      109,
      579,
      456,
      312
    ],
    "english_copy": [
      109,
      918,
      456,
      149
    ],
    "letter_brand_art": [
      213,
      1071,
      232,
      53
    ],
    "footer": [
      43,
      1200,
      572,
      38
    ]
  },
  "palette": {
    "background_top": "#11100e",
    "background_mid": "#648b29",
    "background_bottom": "#aafa26",
    "glitch_title": "#eaffb3",
    "fluorescent_accent": "#b0ff36",
    "letter": "#e3e3e3",
    "body_text": "#080808",
    "panel_border": "#b7bf9d",
    "footer_text": "#ffffff"
  },
  "relationships": [
    {
      "elements": "背景与整体容器",
      "description": "深黑至荧光绿渐变铺满658×1266根画布；细横线纹理叠在渐变上，位于所有文字和图片下方。"
    },
    {
      "elements": "顶部logo与根容器",
      "description": "真实logo独立图片居中放置，裁切仅覆盖标志及其下方英文品牌行，不包含故障标题。"
    },
    {
      "elements": "故障标题与透明标题框",
      "description": "两行可编辑英文位于顶部logo下方；NOTICE下缘被326px起始的半透明标题框轻度覆盖，重现参考图的层叠，而非将标题烘焙成图片。"
    },
    {
      "elements": "文字与标题容器",
      "description": "标题框内依次居中排品牌行、英文致歉标题和荧光绿下三角；白色细标语条与框相隔3px。"
    },
    {
      "elements": "灰信纸与背景",
      "description": "灰信纸位于白条下方16px，左右与标题框对齐，底部柔和黑影让纸张浮于绿色背景上。"
    },
    {
      "elements": "正文与灰信纸",
      "description": "中文标题居中，中文正文和英文正文共用109px全局左边界；两段签名右对齐至565px，正文容器不使用overflow:hidden。"
    },
    {
      "elements": "底部品牌素材与正文",
      "description": "信纸内书法品牌图独立裁切，置于英文签名下方；不将相邻英文正文或签名带入图片，灰色裁切底与信纸底色衔接。"
    },
    {
      "elements": "页脚与信纸",
      "description": "联系方式直接置于根背景上，距信纸底边45px；右侧品牌及口号与左侧地址分栏，避免叠字。"
    }
  ],
  "safe_areas": [
    {
      "scope": "根画布",
      "description": "主要信息保持左右43px以上留白；页脚下方至少28px留白。故障装饰横线允许触及画布左右边缘。"
    },
    {
      "scope": "顶部logo",
      "description": "图片上缘距画布48px；logo底部至主标题约53px，不允许正文侵入裁切范围。"
    },
    {
      "scope": "透明标题框",
      "description": "品牌行上方19px；英文标题保持左右约30px安全距离；三角下方约20px。"
    },
    {
      "scope": "灰信纸",
      "description": "正文左内距61px、右内距47px；中文标题距纸顶24px；中文段落与英文段落之间预留约27px。"
    },
    {
      "scope": "英文正文及品牌图",
      "description": "英文区高度149px，采用7.3px字号和17.2px行距；签名下方与品牌图至少留约4px，品牌图底部距纸底31px。"
    },
    {
      "scope": "页脚",
      "description": "左侧地址控制于约420px宽度，右侧口号使用独立定位，生产地址变长须重新排版，不可裁切。"
    }
  ],
  "fonts": [
    {
      "usage": "IMPORTANT / NOTICE",
      "family": "Arial",
      "weight": 700,
      "description": "使用Arial粗体加斜体、负字距及切片错位近似宽厚故障字；参考为经过特殊处理的字形，不宣称与原定制字体相同。"
    },
    {
      "usage": "LETTER OF APOLOGY",
      "family": "Bodoni 72",
      "weight": 700,
      "description": "候选字体中以Bodoni 72粗体近似参考衬线大标题，实际字宽及衬线形态仍有差异。"
    },
    {
      "usage": "中文正文",
      "family": "Source Han Sans SC",
      "weight": 400,
      "description": "14px正文，26.5px行距。"
    },
    {
      "usage": "中文标题及强调句",
      "family": "Source Han Sans CN",
      "weight": 700,
      "description": "荧光填色配黑色细描边。"
    },
    {
      "usage": "品牌文字、英文正文、页脚",
      "family": "Arial",
      "weight": 400,
      "description": "英文正文保留参考小字号；建议提供独立可访问文本版本。"
    }
  ],
  "texture": {
    "implementation": "使用低透明度repeating-linear-gradient模拟背景细横线和纸面微纹理；故障标题以文字副本clip-path切片、错位、发光及横向扫描线近似。",
    "approximation_notice": "CSS纸纹及故障噪点均为近似，不是真实纸张扫描，也不等同原图随机像素故障效果。",
    "real_texture_strategy": "如需真实纸纹，另行本地扫描无字中性灰纸，600dpi采集后去除光照渐变、校正中性灰并制作256×256无缝透明亮度纹理；作为本地素材低透明度平铺，仅作用于信纸。不得从含字区域提取，也不得使用整张海报截图。默认版本不依赖额外纹理文件或外网。"
  },
  "asset_strategy": {
    "mode": "仅真实logo及书法品牌装饰使用局部原图裁切；其余为可编辑DOM与CSS。",
    "source_coordinate_system": "原图658×1266，左上角为[0,0]，crop格式[x,y,w,h]。",
    "slots": {
      "top_logo": "保留实际品牌标识；建议对深色底做透明蒙版以避免裁切矩形边界。",
      "letter_brand_art": "保留复杂书法字及下方极小品牌微字；微字不够清晰，不另行猜写。可保留匹配灰底或仅提取彩色笔画透明层。"
    },
    "offline": true,
    "editable_text": "主标题、中文标题、全部正文、提示句、签名及页脚均为DOM；图片内真实品牌书法不作伪字体重绘。"
  },
  "limits": [
    "原图故障标题包含不规则颗粒、断裂边缘和复杂辉光，当前使用可编辑字形近似，无法保证像素级相同。",
    "英文正文极小，按可辨识内容转录；其中品牌数字以可读的LINGDU2保留，生产前应由品牌方校对原始文字。",
    "底部书法素材附带的极小微字不清晰，仅随原始局部素材保留，不虚构其内容。",
    "电话、地址、活动时间表达、爆满情况和致歉承诺均为参考图演示信息，生产必须绑定并确认真实事实；不可直接视为已核实公告。",
    "固定信纸可排下当前全文且不裁切文字；替换为更长正文时必须校验换行、调整字号行距或重新布局，不能以overflow:hidden隐藏内容。",
    "字体仅使用指定已安装候选，不使用胡敬礼或得意黑；不同系统字体渲染会产生少量行宽与描边差异。",
    "标题故障层使用CSS mask-image及clip-path；不支持相关特性的渲染器会退化为普通发光文字。"
  ]
}
```

### CSS 与可编辑文字骨架

```css
.notice-3{position:relative;isolation:isolate;width:658px;height:1266px;box-sizing:border-box;background:linear-gradient(180deg,#11100e 0%,#14170f 14%,#344422 34%,#648b29 57%,#a5ed26 89%,#aafa26 100%);color:#080808;font-family:'Arial','Source Han Sans SC',sans-serif;font-weight:400}.notice-3 *{box-sizing:border-box}.notice-3 .paper-grain{position:absolute;inset:0;z-index:0;pointer-events:none;opacity:.11;background-image:repeating-linear-gradient(0deg,rgba(255,255,255,.09) 0,rgba(255,255,255,.09) 1px,transparent 1px,transparent 3px)}.notice-3 .brand{position:absolute;z-index:1;left:258px;top:48px;width:152px;height:76px;object-fit:contain}.notice-3 .hero{position:absolute;z-index:1;left:43px;top:177px;width:573px;text-align:center;color:#eaffb3;font-family:'Arial',sans-serif;font-weight:700;font-style:italic;letter-spacing:-6px;line-height:.94;text-shadow:0 0 3px #fff,0 0 9px #eaffbb,0 0 20px #aaff39,0 0 32px #a2f034}.notice-3 .hero-line{position:relative;display:block;width:100%;font-size:84px;white-space:nowrap;transform:scaleX(1.04)}.notice-3 .hero-line:last-child{margin-top:11px;font-size:89px;letter-spacing:-5px}.notice-3 .hero-line:before,.notice-3 .hero-line:after{content:attr(data-text);position:absolute;inset:0;pointer-events:none}.notice-3 .hero-line:before{color:#faffdf;transform:translate(5px,-1px);clip-path:polygon(0 9%,100% 9%,100% 15%,0 15%,0 32%,100% 32%,100% 36%,0 36%,0 66%,100% 66%,100% 72%,0 72%,0 89%,100% 89%,100% 93%,0 93%)}.notice-3 .hero-line:after{color:#b6fb69;transform:translate(-7px,2px);clip-path:polygon(0 20%,100% 20%,100% 23%,0 23%,0 44%,100% 44%,100% 49%,0 49%,0 77%,100% 77%,100% 80%,0 80%)}.notice-3 .interference{position:absolute;z-index:2;left:0;top:185px;width:658px;height:156px;pointer-events:none;opacity:.42;background:repeating-linear-gradient(0deg,transparent 0,transparent 3px,rgba(205,255,169,.5) 3px,rgba(205,255,169,.5) 4px);mask-image:linear-gradient(90deg,transparent,#000 10%,#000 90%,transparent)}.notice-3 .title-panel{position:absolute;z-index:3;left:47px;top:326px;width:564px;height:136px;border:1px solid #b7bf9d;border-radius:5px;background:rgba(124,143,80,.2);box-shadow:inset 0 0 0 2px rgba(238,242,218,.12);text-align:center;color:#fff}.notice-3 .panel-brand{margin:19px 0 3px;font-size:17px;line-height:22px}.notice-3 .apology-title{margin:0;font-family:'Bodoni 72','Songti SC',serif;font-weight:700;font-size:43px;line-height:53px;letter-spacing:1px;white-space:nowrap}.notice-3 .down-arrow{display:block;margin:7px auto 0;width:0;height:0;border-left:9px solid transparent;border-right:9px solid transparent;border-top:12px solid #aeff35}.notice-3 .slogan-strip{position:absolute;z-index:3;left:47px;top:465px;width:564px;height:18px;border:1px solid #829763;border-radius:5px;background:#fff;text-align:center;font-size:10px;line-height:16px;letter-spacing:-.3px}.notice-3 .letter{position:absolute;z-index:2;left:47px;top:499px;width:564px;height:656px;background:#e3e3e3;border:1px solid #c6cbbf;box-shadow:0 19px 18px -13px rgba(18,31,4,.88)}.notice-3 .letter:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.08;background:repeating-linear-gradient(0deg,rgba(255,255,255,.25) 0,rgba(255,255,255,.25) 1px,transparent 1px,transparent 4px)}.notice-3 .letter-heading{position:absolute;left:30px;right:30px;top:24px;margin:0;text-align:center;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:29px;line-height:39px;color:#b0ff36;-webkit-text-stroke:1px #0b1700;text-shadow:1px 1px 0 #0b1700}.notice-3 .cn-copy{position:absolute;left:61px;top:80px;width:456px;font-size:14px;line-height:26.5px;letter-spacing:-.35px}.notice-3 .cn-copy p{margin:0}.notice-3 .cn-copy .salutation{font-weight:700;margin-bottom:9px}.notice-3 .cn-copy .indent{text-indent:2em}.notice-3 .cn-copy .highlight{margin:9px 0 17px;text-align:center;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:17px;line-height:26px;letter-spacing:0;color:#b5ff47;-webkit-text-stroke:.65px #132300;text-shadow:1px 1px 0 #132300}.notice-3 .cn-copy .signature{text-align:right;line-height:21px;margin-top:-1px}.notice-3 .en-copy{position:absolute;left:61px;top:419px;width:456px;font-family:'Arial',sans-serif;font-size:7.3px;line-height:17.2px;letter-spacing:-.12px}.notice-3 .en-copy p{margin:0}.notice-3 .en-copy .en-salutation{margin-bottom:2px}.notice-3 .en-copy .en-signature{text-align:right;font-size:7.2px;line-height:14px}.notice-3 .letter-brand{position:absolute;left:166px;top:572px;width:232px;height:53px;object-fit:contain}.notice-3 .footer{position:absolute;z-index:2;left:43px;top:1200px;width:572px;color:#fff}.notice-3 .contact{margin:0;font-size:12px;line-height:19px;letter-spacing:-.45px}.notice-3 .contact .address{font-family:'Arial','Source Han Sans SC',sans-serif;font-size:10.5px}.notice-3 .footer-brand{position:absolute;right:0;top:2px;font-size:10px;line-height:15px;font-style:italic;letter-spacing:-.4px}.notice-3 .footer-slogan{position:absolute;right:0;top:22px;font-size:7px;line-height:10px;white-space:nowrap}
```

```html
<div class="notice-3"><div class="paper-grain" aria-hidden="true"></div><img class="brand" data-asset-slot="top_logo" src="{{top_logo}}" alt="LING DU | LIVE HOUSE 2.0"><header class="hero" aria-label="IMPORTANT NOTICE"><span class="hero-line" data-text="IMPORTANT">IMPORTANT</span><span class="hero-line" data-text="NOTICE">NOTICE</span></header><div class="interference" aria-hidden="true"></div><section class="title-panel"><p class="panel-brand">LINGDU²LIVEHOUSE+</p><h1 class="apology-title">LETTER OF APOLOGY</h1><span class="down-arrow" aria-hidden="true"></span></section><div class="slogan-strip">ZERO DEGREE ZERO DEGREE TO GET RICH AND GET RICH</div><main class="letter"><h2 class="letter-heading">致歉信</h2><div class="cn-copy"><p class="salutation">尊敬的LINGDU²LIVE HOUSE+的玩家朋友们:</p><p class="indent">您好!昨天是LINGDU²LIVEHOUSE+的试音派对，也是零度LIVEHOUSE再次新生的时刻，备受众多玩家的关注和支持，再次感谢昨晚每位莅临体验玩家。</p><p class="indent">由于到场的玩家人数众多，场内持续爆满，还是导致许多玩家未能被及时安排，影响到您的体验，在此我们温馨提醒：</p><p class="highlight">提前预定少烦恼&nbsp; 早点到场位置好</p><p class="indent">再次感谢您对LINGDU²LIVEHOUSE+的支持,我们将尽力完善每一个细节，打造最佳氛围的音乐现场。</p><p class="signature">此致<br>LINGDU²LIVEHOUSE+</p></div><div class="en-copy" lang="en"><p class="en-salutation">DEAR LINGDU2LIVE HOUSE+ PLAYERS,</p><p>HELLO! YESTERDAY WAS THE AUDITION CEREMONY OF LINGDU2LIVEHOUSE+, AND IT WAS ALSO THE MOMENT WHEN THE LINGDU2LIVEHOUSE+ WAS REBORN AGAIN, WHICH ATTRACTED THE ATTENTION AND SUPPORT OF MANY PLAYERS.</p><p>DUE TO THE LARGE NUMBER OF PLAYERS PRESENT, THE VENUE CONTINUES TO BE FULL, OR MANY PLAYERS ARE NOT SCHEDULED IN TIME, AFFECTING YOUR EXPERIENCE, WE WOULD LIKE TO REMIND YOU:</p><p>THANK YOU AGAIN FOR YOUR SUPPORT OF LINGDU2LIVEHOUSE+, WE WILL TRY OUR BEST TO PERFECT EVERY DETAIL TO CREATE THE BEST ATMOSPHERE FOR THE MUSIC SCENE.</p><p class="en-signature">SINCERELY<br>LINGDU²LIVEHOUSE+</p></div><img class="letter-brand" data-asset-slot="letter_brand_art" src="{{letter_brand_art}}" alt="零度零度 发财暴富"></main><footer class="footer"><p class="contact">VIP Line / 0527-8898-9898<br><span class="address">Address / 江苏省宿迁市宿豫区中运河非粮库文化创意产业园内 - 零度LIVEHOUSE</span></p><span class="footer-brand">Lingdu Livehouse 2.0</span><span class="footer-slogan">Zero degree zero degree to get rich and get rich</span></footer></div>
```

### 素材绑定与验证边界

- `top_logo`：顶部荧光绿真实标识及LING DU | LIVE HOUSE 2.0品牌行，不含下方主标题。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `letter_brand_art`：灰信纸底部零度零度、发财暴富书法品牌组合与附属微字，不含上方英文正文和右侧签名。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。

参考正文、品牌、日期和二维码仅作内部排版样本，不是已确认业务事实。正式生成替换为确认内容；图片槽不得直接引用参考整图或演示裁片。复杂纹理未生成时只能标记近似/待补；页面与文字层不可整体降低透明度。长文先调整分组、容器容量或拆页，不能隐藏溢出；更换标题、字体、素材、尺寸必须重查正文和图片安全区。字体绑定真实文件及字重，核验逐字覆盖；胡敬礼禁用，得意黑不默认回退。正式交付按主Skill路由将样式绑定到图层/行内CSS，示例style规则本身不替代交付协议。


<a id="combination.notice-pop-promotion"></a>

**原子布局对应**：[notice-bound-letter](../layouts/notice-and-invitation.md#layout.bound-paper-stack)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。

## 波普晋升喜报

**设计选型**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

**产物标签**：公告通知；竖版单屏；内部喜报。适合社媒单张发布；不能直接当多章节长图或商品详情页模板。

**组合状态**：追加抽样完成完整渲染与本地复查，可用于内部组合布局验证，正文无漏句。标题、正文行宽及飘带已校正；素材仍为参考局部。

**可复用原子**：[layout.section-masthead](../layouts/layout-and-type.md#layout.section-masthead)、[shape.badge](../shapes/capsules-and-badges.md#shape.badge)、[surface.dot-pattern](../surfaces/paper-and-print.md#surface.dot-pattern)。以下CSS为这些机制的独立、作用域隔离示例，不要求重复叠加原子默认样式；沿用本组合的色值、尺度和作用对象。

### 布局、字体与素材关系

```json
{
  "artifact_tags": [
    "图4",
    "固定尺寸公告海报",
    "白色爆炸形标题底",
    "橙色装订本",
    "晋升成功",
    "可编辑DOM",
    "局部插画素材"
  ],
  "dimensions": {
    "width": 658,
    "height": 1270,
    "unit": "px",
    "root": ".notice-4",
    "responsive": false
  },
  "layout": {
    "brand": [
      263,
      22,
      137,
      40
    ],
    "title_backplate": [
      24,
      78,
      622,
      361
    ],
    "title": [
      61,
      140,
      537,
      235
    ],
    "period_label": [
      162,
      375,
      355,
      43
    ],
    "notebook": [
      24,
      470,
      610,
      596
    ],
    "white_sheet": [
      24,
      629,
      610,
      420
    ],
    "body_text": [
      59,
      699,
      540,
      319
    ],
    "footer": [
      24,
      1107,
      610,
      117
    ],
    "stacking": "黄色背景与外围色带 → 白色爆炸底与装饰插画 → 黑色标题及日期条 → 橙色本体、装订环及白纸 → 台历手势 → 页脚入口。"
  },
  "palette": {
    "background": "#FFE600",
    "orange_cover": "#FFAE00",
    "orange_label": "#FF8500",
    "orange_text": "#FF8900",
    "paper": "#FFFFFF",
    "text": "#080808",
    "pink": "#FF60C6",
    "purple": "#914AF4",
    "binding": "#E9E8DC"
  },
  "relationships": [
    {
      "type": "背景与容器",
      "detail": "658×1270黄色画布承载顶部白色爆炸底和下方橙色装订本；本体左右各留24px，页脚沿用相同左边界。外围色带仅在独立装饰层裁切，不裁正文。"
    },
    {
      "type": "背景与容器",
      "detail": "白纸从装订本顶部向下159px开始，以左上96px大圆角形成翻页式过渡，底部两道暖色阴影表现叠纸。"
    },
    {
      "type": "素材与容器",
      "detail": "品牌logo独立置于画布顶部中央；笑脸位于爆炸底左上角，奖杯位于右上角，均在标题下层。点赞手势位于画布左侧，跨越日期条下方与装订本起始边缘。"
    },
    {
      "type": "素材与容器",
      "detail": "台历手势相对装订本定位于[405,15]，向右超出本体16px，向下覆盖白纸顶端14px；保留这一越界关系但不覆盖正文。小清单位于日期条右侧。"
    },
    {
      "type": "文字与素材/容器",
      "detail": "两行标题使用独立DOM，整体逆时针旋转4度叠在白爆炸底上；奖杯置于标题下层，避免图片中的透明外框压住标题。日期文字随橙色胶囊逆时针旋转5度。"
    },
    {
      "type": "文字与素材/容器",
      "detail": "正文相对白纸左右各35px、上70px排版，称谓单独一行，正文26px/53px，两段各缩进两字；第一段约三行、第二段约两行，完整结束于白纸底边之前。"
    },
    {
      "type": "文字与素材/容器",
      "detail": "底部左侧评审建议说明与右侧获取链接为两个独立胶囊，间距22px，文字居中；橙色网点底只用于本体和右侧链接。"
    }
  ],
  "safe_areas": [
    {
      "scope": "背景与主容器",
      "area": [
        24,
        22,
        610,
        1202
      ],
      "rule": "主内容不超出左右24px边距；插画和外围色带允许有意越界，正文不允许越界。"
    },
    {
      "scope": "品牌",
      "area": [
        253,
        12,
        157,
        60
      ],
      "rule": "logo外保留约10px净空，禁止标题和装饰穿入。"
    },
    {
      "scope": "标题",
      "area": [
        70,
        139,
        521,
        228
      ],
      "rule": "标题字形尽量留在白底内；字体替换后检查旋转外接框与奖杯、左侧笑脸的重叠。"
    },
    {
      "scope": "素材与白纸",
      "area": [
        429,
        485,
        221,
        158
      ],
      "rule": "台历手势止于y=643，正文始于y=699，二者保留至少56px纵向距离。"
    },
    {
      "scope": "正文",
      "area": [
        59,
        699,
        540,
        319
      ],
      "rule": "称谓、姓名及两段正文共用此区域；当前完整文案约需要319px高度，白纸底部仍有约31px内边距。不设置overflow:hidden或行数截断。"
    },
    {
      "scope": "页脚",
      "area": [
        24,
        1107,
        610,
        117
      ],
      "rule": "两胶囊之间22px净空，底部距画布46px；链接文字与边框至少保留约17px水平空隙。"
    }
  ],
  "fonts": [
    {
      "usage": "主标题",
      "family": "Source Han Sans CN",
      "weight": 700,
      "sizes_px": [
        91,
        137
      ],
      "note": "使用已安装候选中较贴近的粗黑无衬线字体，并以紧字距、轻微横向缩放和旋转近似原图张力；原图标题具有更厚重的定制字形，不声称完全相同。"
    },
    {
      "usage": "中文正文与日期",
      "family": "Source Han Sans SC",
      "weight": 400,
      "sizes_px": [
        26,
        31
      ],
      "note": "正文保持自然字形与53px行高，日期通过紧字距适配胶囊宽度。"
    },
    {
      "usage": "徽章与底部按钮",
      "family": "Source Han Sans CN",
      "weight": 700,
      "sizes_px": [
        13,
        26,
        38
      ]
    },
    {
      "usage": "Dear称谓",
      "family": "Arial",
      "weight": 400,
      "sizes_px": [
        36
      ]
    }
  ],
  "texture": {
    "css_approximation": "橙色装订本与右侧按钮使用10px周期、半径1.7px的半透明圆点模拟印刷网点；白纸使用纯白及暖色叠纸阴影。此为普通CSS近似，不是真实纸纹复原。",
    "real_texture_generation_strategy": "若需真实质感，从原图橙色封面无字、无环、无插画区域[308,535,100,70]提取纹理参考，去除低频明暗后做无缝拼接，生成本地可平铺PNG；白纸可从[310,654,90,35]采样纸面颜色与噪声统计，再生成低对比度纸纤维纹理。两者单独作为可选背景资源，不含文字、不烘焙整张海报，默认CSS不依赖这些额外文件。"
  },
  "asset_strategy": {
    "default": "全部插画和真实品牌图形使用本地槽位素材，无外网依赖；assets中的crop为原图658×1270坐标系中的局部核验框。",
    "extraction": "每个裁切框只覆盖对应插画或logo，不包含旁边正文。对跨越黄色背景、白爆炸底或橙色本体的素材，需要在该框内做前景蒙版并输出透明PNG/WebP，维持原框尺寸和透明边距；不能直接把带矩形底色的截图贴回。",
    "editable_content": "主标题、日期、称谓、正文、徽章及底部文字均为DOM；logo及台历上难以用CSS还原的真实图形保留在独立图像槽。",
    "verification": "先使用原图局部裁切核对位置、尺寸及图形，再进行透明化；不把文字区并入素材以掩盖字体差异。"
  },
  "limits": [
    "日期2023年11月及晋升成功事实仅为参考图演示内容；生产必须同步绑定已确认的晋升窗口、收件人、晋升结果及评审链接，不应把示例当作真实通知。",
    "原图称谓后的姓名为空白下划线，未虚构姓名；右上粉色色带只有被截断的装饰拉丁字母，未擅自补全或转写。",
    "标题候选字体不能完全复刻原图特制粗黑字形；禁止使用胡敬礼及得意黑，也未引用其他未安装字体。",
    "白色爆炸底、外围色带、装订环和黄色对话框由CSS近似，曲线及光影与原图会有差异。",
    "台历、奖杯、笑脸及手势的透明前景需从给定局部框中提取；复杂边缘不可通过emoji或整幅海报背景替代。",
    "固定画布只保证当前转录文案完整排版。生产替换后若正文显著增长，应重新验证白纸高度与页脚间距，不能通过overflow:hidden或省略号裁掉内容。",
    "链接占位符review_url必须在生产绑定已确认地址；所有图片槽位必须绑定本地生成或已授权素材。"
  ],
  "local_review_notes": [
    "奖杯与台历的验证裁片用独立SVG轮廓裁切，去掉原标题与矩形背景；生产必须提供独立透明插画。",
    "展示标题预留字形下伸空间；正文换文案后重新检查容量与安全区。"
  ]
}
```

### CSS 与可编辑文字骨架

```css
.notice-4{position:relative;width:658px;height:1270px;isolation:isolate;background:#ffe600;color:#080808;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-4 *{box-sizing:border-box}.notice-4 .n4-decoration{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:0}.notice-4 .n4-swoosh{position:absolute;background:#ffad00}.notice-4 .n4-swoosh.a{width:235px;height:62px;left:-22px;top:-14px;transform:rotate(31deg);border-radius:0 0 100% 0}.notice-4 .n4-swoosh.b{width:171px;height:76px;right:-25px;top:-31px;transform:rotate(-15deg);border-radius:100% 0 0 0}.notice-4 .n4-swoosh.c{width:210px;height:88px;right:-51px;top:472px;transform:rotate(22deg);border-radius:0 0 0 100%}.notice-4 .n4-ribbon{position:absolute;height:39px;background:#ff60c6;transform:rotate(-36deg)}.notice-4 .n4-ribbon.left{width:163px;left:-71px;top:270px}.notice-4 .n4-ribbon.right{width:185px;height:58px;right:-74px;top:124px}.notice-4 .n4-white-sliver{position:absolute;left:133px;top:-15px;width:39px;height:64px;background:white;clip-path:polygon(0 0,48% 0,100% 100%,48% 69%)}.notice-4 .n4-star{position:absolute;width:40px;height:40px;background:#fff;clip-path:polygon(50% 0,62% 36%,100% 50%,64% 62%,50% 100%,37% 64%,0 50%,36% 37%)}.notice-4 .n4-star.s1{left:90px;top:67px;width:16px;height:16px}.notice-4 .n4-star.s2{left:179px;top:88px}.notice-4 .n4-star.s3{left:579px;top:318px;width:42px;height:43px}.notice-4 .n4-logo{position:absolute;left:263px;top:22px;width:137px;height:40px;object-fit:contain;z-index:2}.notice-4 .n4-burst{position:absolute;left:24px;top:78px;width:622px;height:361px;background:#fff;clip-path:polygon(0 27%,12% 23%,13% 12%,28% 20%,40% 12%,45% 0,49% 7%,55% 11%,61% 11%,71% 0,70% 14%,84% 17%,88% 27%,97% 36%,100% 36%,94% 43%,92% 52%,95% 63%,85% 66%,80% 78%,62% 81%,55% 99%,45% 86%,29% 99%,28% 86%,10% 84%,12% 75%,11% 65%,7% 63%,0 64%,8% 52%,7% 38%);z-index:1}.notice-4 .n4-title{position:absolute;left:61px;top:140px;width:537px;margin:0;text-align:center;z-index:4;font-family:'Source Han Sans CN','Source Han Sans SC',sans-serif;font-weight:700;transform:rotate(-4deg);letter-spacing:-6px}.notice-4 .n4-title span{display:block;white-space:nowrap}.notice-4 .n4-title .first{font-size:91px;line-height:1.05;transform:scaleX(1.03)}.notice-4 .n4-title .second{font-size:137px;line-height:1.01;transform:scaleX(.99);letter-spacing:-9px}.notice-4 .n4-period{position:absolute;left:162px;top:375px;width:355px;height:43px;margin:0;border-radius:28px;background:#ff8500;color:#fff020;text-align:center;font-size:31px;line-height:43px;letter-spacing:-1.3px;transform:rotate(-5deg);z-index:5}.notice-4 .n4-sticker{position:absolute;object-fit:contain;z-index:3}.notice-4 .n4-face{left:23px;top:96px;width:159px;height:145px}.notice-4 .n4-trophy{left:409px;top:64px;width:190px;height:172px}.notice-4 .n4-thumb{left:0;top:360px;width:139px;height:132px;z-index:6}.notice-4 .n4-checklist{left:526px;top:355px;width:91px;height:79px}.notice-4 .n4-book{position:absolute;left:24px;top:470px;width:610px;height:596px;border-radius:65px 25px 39px 39px;background-color:#ffae00;background-image:radial-gradient(circle,rgba(255,230,43,.32) 1.7px,transparent 2px);background-size:10px 10px;box-shadow:0 5px 0 #f89b00;z-index:2}.notice-4 .n4-rings{position:absolute;left:102px;top:-21px;display:flex;gap:25px;z-index:3}.notice-4 .n4-ring{position:relative;width:37px;height:58px}.notice-4 .n4-ring:before{content:'';position:absolute;left:7px;bottom:1px;width:16px;height:17px;border-radius:50%;background:#080808}.notice-4 .n4-ring:after{content:'';position:absolute;inset:0 1px 5px 0;border:6px solid #e9e8dc;border-right-color:transparent;border-radius:50%;transform:rotate(-8deg)}.notice-4 .n4-badge-art{position:absolute;left:24px;top:46px;width:270px;height:106px}.notice-4 .n4-bubble{position:absolute;left:105px;top:2px;width:139px;height:84px;border-radius:29px;background:#fff000}.notice-4 .n4-bubble:after{content:'';position:absolute;left:75px;bottom:-10px;border-left:12px solid transparent;border-right:12px solid transparent;border-top:13px solid #fff000}.notice-4 .n4-eyes{position:absolute;right:25px;top:35px;width:6px;height:6px;border-radius:50%;background:#080808;box-shadow:-16px 0 #080808}.notice-4 .n4-eyes:after{content:'';position:absolute;left:-12px;top:6px;width:12px;height:8px;border-bottom:3px solid #080808;border-radius:50%}.notice-4 .n4-small-tag{position:absolute;left:19px;top:10px;padding:4px 10px;border-radius:18px;background:#914af4;color:#d3a6ff;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:13px;line-height:18px}.notice-4 .n4-success{position:absolute;left:3px;top:49px;margin:0;width:153px;height:44px;border-radius:25px;background:#fff;color:#ffc000;text-align:center;font-family:'Source Han Sans CN',sans-serif;font-weight:700;font-size:26px;line-height:44px}.notice-4 .n4-success:after{content:'';position:absolute;left:65px;bottom:-11px;border-left:12px solid transparent;border-right:12px solid transparent;border-top:13px solid white}.notice-4 .n4-badge-star{left:258px;top:42px;width:17px;height:22px}.notice-4 .n4-calendar{position:absolute;left:405px;top:15px;width:221px;height:158px;object-fit:contain;z-index:5}.notice-4 .n4-sheet{position:absolute;left:0;top:159px;width:610px;min-height:420px;border-radius:96px 0 36px 36px;background:#fff;box-shadow:0 7px 0 #ffd38a,0 14px 0 rgba(255,206,112,.56);padding:70px 35px 31px;z-index:2}.notice-4 .n4-salutation{margin:0 0 8px;font-family:Arial,'Source Han Sans SC',sans-serif;font-size:36px;line-height:48px}.notice-4 .n4-name-line{display:inline-block;width:119px;height:36px;margin-left:8px;vertical-align:baseline;border-bottom:2px solid #555;font-size:26px;text-align:center}.notice-4 .n4-copy{font-size:26px;line-height:53px;letter-spacing:0;text-align:left;overflow-wrap:break-word}.notice-4 .n4-copy p{margin:0;text-indent:2em}.notice-4 .n4-footer{position:absolute;left:24px;top:1107px;width:610px;height:117px;display:flex;gap:22px;align-items:stretch;z-index:3;font-family:'Source Han Sans CN','Source Han Sans SC',sans-serif;font-weight:700}.notice-4 .n4-footer-label{width:337px;margin:0;border:2px solid #ff9600;border-radius:64px;color:#ff8900;display:flex;align-items:center;justify-content:center;font-size:38px;letter-spacing:-2px;white-space:nowrap}.notice-4 .n4-cta{width:251px;border:3px solid #fff35e;border-radius:64px;background-color:#ffae00;background-image:radial-gradient(circle,rgba(255,232,61,.3) 1.7px,transparent 2px);background-size:10px 10px;color:#fff;text-decoration:none;display:flex;align-items:center;justify-content:center;font-size:38px;letter-spacing:-2px;white-space:nowrap}.notice-4 .n4-cta:focus-visible{outline:3px solid #080808;outline-offset:4px}
/* Local full-composition validation */
.notice-4 .n4-title{padding-bottom:24px}.notice-4 .n4-success{height:48px;line-height:44px}.notice-4 .n4-book,.notice-4 .n4-cta{background-image:radial-gradient(circle,rgba(255,230,43,.23) 1.6px,transparent 1.8px)}
.notice-4 .n4-title .first{transform:none}.notice-4 .n4-title .second{font-size:130px;line-height:1.02}.notice-4 .n4-copy{font-size:25px}.notice-4 .n4-ribbon-detail{position:absolute;left:575px;top:103px;width:83px;height:113px;object-fit:contain;z-index:1;clip-path:polygon(100% 0,0 58%,45% 100%,100% 65%)}
.notice-4 .n4-ribbon-detail{z-index:2}
```

```html
<div class="notice-4" role="article" aria-label="晋升成功公告"><img class="n4-ribbon-detail" data-asset-slot="ribbon_detail" src="{{ribbon_detail}}" alt=""><div class="n4-decoration" aria-hidden="true"><i class="n4-swoosh a"></i><i class="n4-swoosh b"></i><i class="n4-swoosh c"></i><i class="n4-ribbon left"></i><i class="n4-ribbon right"></i><i class="n4-white-sliver"></i><i class="n4-star s1"></i><i class="n4-star s2"></i><i class="n4-star s3"></i></div><img class="n4-logo" data-asset-slot="brand_logo" src="{{brand_logo}}" alt="天纵游戏 TIAN ZONG GAMES"><div class="n4-burst" aria-hidden="true"></div><img class="n4-sticker n4-face" data-asset-slot="orange_face" src="{{orange_face}}" alt="橙色笑脸贴纸"><img class="n4-sticker n4-trophy" data-asset-slot="gold_trophy" src="{{gold_trophy}}" alt="金色星星奖杯"><h1 class="n4-title"><span class="first">恭喜你</span><span class="second">晋升成功</span></h1><p class="n4-period" data-field="promotionPeriod">2023年11月晋升窗口期</p><img class="n4-sticker n4-thumb" data-asset-slot="thumbs_up" src="{{thumbs_up}}" alt="点赞手势插画"><img class="n4-sticker n4-checklist" data-asset-slot="small_checklist" src="{{small_checklist}}" alt="评审清单插画"><section class="n4-book" aria-label="晋升通知正文"><div class="n4-rings" aria-hidden="true"><i class="n4-ring"></i><i class="n4-ring"></i><i class="n4-ring"></i><i class="n4-ring"></i><i class="n4-ring"></i><i class="n4-ring"></i><i class="n4-ring"></i></div><div class="n4-badge-art"><div class="n4-bubble" aria-hidden="true"><i class="n4-eyes"></i></div><span class="n4-small-tag">脱颖而出</span><p class="n4-success">晋升成功</p></div><i class="n4-star n4-badge-star" aria-hidden="true"></i><img class="n4-calendar" data-asset-slot="calendar_hand" src="{{calendar_hand}}" alt="带粉色图案的台历与庆祝手势"><div class="n4-sheet"><p class="n4-salutation">Dear<span class="n4-name-line" data-field="recipientName" aria-label="待填写收件人"></span></p><div class="n4-copy" data-field="confirmedAnnouncement"><p>恭喜你在2023年11月晋升窗口期中通过晋升评审，晋升成功！更高的职级意味着你需要承担更大的责任，付出更多的努力。</p><p>希望你在新的职级上能激发个人潜力，持续产出价值，成就更好的自己。</p></div></div></section><footer class="n4-footer"><p class="n4-footer-label">评委的评审建议</p><a class="n4-cta" href="{{review_url}}" aria-label="点击获取评委的评审建议">&lt;点击获取&gt;</a></footer></div>
```

### 素材绑定与验证边界

- `brand_logo`：顶部天纵游戏及TIAN ZONG GAMES真实logo；保留标志与品牌文字整体，去除黄色底。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `orange_face`：左上橙色爆炸笑脸插画；提取橙色轮廓、白眼及黑色五官，排除背景和右侧标题。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `gold_trophy`：右上金色星星奖杯；保留杯体、把手、底座及自身阴影，剔除底层爆炸白底与邻近标题。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `thumbs_up`：左侧粉色点赞手势及袖口；画布左缘自然截断，透明化原背景，不包含日期正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `small_checklist`：日期条右侧小型清单插画；保留纸页、紫色标记与阴影，不扩展到左侧日期文字。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `calendar_hand`：装订本右上独立台历与粉色庆祝手势组合，含台历图案、金色小环及底部黑影；不包含下方Dear或正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。

参考正文、品牌、日期和二维码仅作内部排版样本，不是已确认业务事实。正式生成替换为确认内容；图片槽不得直接引用参考整图或演示裁片。复杂纹理未生成时只能标记近似/待补；页面与文字层不可整体降低透明度。长文先调整分组、容器容量或拆页，不能隐藏溢出；更换标题、字体、素材、尺寸必须重查正文和图片安全区。字体绑定真实文件及字重，核验逐字覆盖；胡敬礼禁用，得意黑不默认回退。正式交付按主Skill路由将样式绑定到图层/行内CSS，示例style规则本身不替代交付协议。



补充素材槽：`ribbon_detail`为右上飘带可见字样，验证用参考局部；生产绑定确认素材。
<a id="combination.notice-mint-editorial"></a>

**原子布局对应**：[notice-sheet-stack](../layouts/notice-and-invitation.md#layout.title-letter-stack)、[notice-contact-footer](../layouts/notice-and-invitation.md#layout.contact-footer)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。 偏轴主视觉复用[单侧信息轴](../layouts/asymmetric-balance.md#layout.cross-column-axis)，标题错位复用[错落标题](../layouts/asymmetric-balance.md#layout.staggered-title)。

## 薄荷编辑公告

**设计选型**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

**产物标签**：公告通知；竖版单屏。适合社媒单张发布；不能直接当多章节长图或商品详情页模板。

**组合状态**：已做参考局部素材组装与完整本地渲染；画布658×1170、无缺图、无文字盒溢出。主体结构、正文完整性与安全区已复核；纹理、标题占位与临时裁片边缘仍有偏差。不代表独立素材生成完成或目标平台验收。

**可复用原子**：[layout.staggered-title](../layouts/asymmetric-balance.md#layout.staggered-title)、[layout.reading-column](../layouts/airy-and-spacious.md#layout.reading-column)、[surface.fine-grain-mist](../surfaces/diffuse-light.md#surface.fine-grain-mist)。以下CSS为这些机制的独立、作用域隔离示例，不要求重复叠加原子默认样式；沿用本组合的色值、尺度和作用对象。

### 布局、字体与素材关系

```json
{
  "artifact_tags": [
    "固定尺寸公告海报",
    "巨型竖排标题",
    "银色独立喇叭",
    "薄荷绿与淡紫渐变",
    "纸张颗粒",
    "可编辑正文",
    "二维码页脚"
  ],
  "dimensions": {
    "width": 658,
    "height": 1170,
    "unit": "px",
    "coordinate_origin": "原图左上角",
    "canvas": "固定画布，不自适应缩放"
  },
  "layout": {
    "title": "左上竖排“公告”，约占x104–255、y108–506。",
    "brand": "英文位于x257、y148起，下方为中文公司名。",
    "illustration": "银色喇叭位于x253–574、y277–645，斜向右下，与正文框右上部分重叠。",
    "body_container": "x83、y587、w492、h512的细边框半透明浅色公告框。",
    "body_text": "x114起，问候语约y624；内容主体约y680–891，保留手动分行。",
    "footer": "y945附近横线分隔；左二维码，右下署名与日期。",
    "decoration": "左侧大号浅绿英文被画布边界截断，右上角为折角。"
  },
  "palette": {
    "paper": "#F4F5F3",
    "ink": "#202221",
    "mint": "#B4DCD1",
    "lavender": "#E4CBE1",
    "border": "#7D8380",
    "fold": "#A5CEC7",
    "panel": "rgba(249,248,248,0.79)"
  },
  "relationships": [
    {
      "type": "背景与容器",
      "detail": "渐变与颗粒覆盖整个658×1170画布；正文容器位于背景之上，半透明底色让薄荷绿和淡紫轻微透出，但保持正文对比度。只有背景装饰层裁切越界英文。"
    },
    {
      "type": "素材与容器",
      "detail": "喇叭独立透明图层高于正文容器，手柄跨过容器上边界约58px；素材不得附带原图的矩形背景，否则会遮掉边框或形成接缝。"
    },
    {
      "type": "文字与素材",
      "detail": "品牌文字位于喇叭上方；问候语限定在左侧区域，避开右侧手柄。正文第一行从约y680开始，晚于喇叭底部约35px。"
    },
    {
      "type": "文字与容器",
      "detail": "正文左右留约30px与24px，分隔线之上完整安排问候语、五行说明和两行致歉；不对正文设置overflow:hidden。"
    },
    {
      "type": "页脚素材与文字",
      "detail": "二维码固定在页脚左侧109×111px槽内，署名日期右对齐；二者水平分离，避免二维码静区被文字侵入。"
    }
  ],
  "safe_areas": [
    {
      "target": "背景与画布",
      "area": [
        0,
        0,
        658,
        1170
      ],
      "rule": "只允许左侧英文及背景纹理被画布边缘截断；正文不得使用同样的裁切策略。"
    },
    {
      "target": "竖排标题",
      "area": [
        99,
        105,
        156,
        407
      ],
      "rule": "候选字体实际字形需校验，不得碰到右侧品牌或正文框。"
    },
    {
      "target": "品牌文字",
      "area": [
        257,
        148,
        310,
        123
      ],
      "rule": "与右上折角分离；中文基线下方保留间隔，不压住喇叭上缘。"
    },
    {
      "target": "喇叭",
      "area": [
        253,
        277,
        321,
        368
      ],
      "rule": "保持原始透明边缘、银色高光及手柄完整，不拉伸、不以emoji替代。"
    },
    {
      "target": "正文",
      "area": [
        110,
        619,
        441,
        302
      ],
      "rule": "完整排入参考内容，末行与y945分隔线至少间隔约45px；替换长文应重排并校验页脚，不得隐藏溢出文字。"
    },
    {
      "target": "二维码",
      "area": [
        105,
        957,
        127,
        127
      ],
      "rule": "外围保持无文字干扰；生产二维码应重新生成并包含不少于四模块的静区。"
    },
    {
      "target": "署名日期",
      "area": [
        329,
        999,
        222,
        61
      ],
      "rule": "保持右对齐，不侵入二维码及其静区。"
    },
    {
      "target": "左上logo",
      "area": [
        18,
        28,
        56,
        57
      ],
      "rule": "保留圆形标志完整轮廓，不用普通文字伪造真实logo。"
    }
  ],
  "fonts": [
    {
      "usage": "巨型竖排公告",
      "family": "Songti SC",
      "weight": 700,
      "size_px": 181,
      "note": "已安装候选中用宋体粗字近似原图尖锐衬线与大字结构，不宣称与原图定制字相同。"
    },
    {
      "usage": "GAODING",
      "family": "Bodoni 72",
      "weight": 400,
      "size_px": 72,
      "note": "高对比衬线候选，采用轻微横向压缩近似原图窄长英文。"
    },
    {
      "usage": "公司名",
      "family": "Source Han Sans SC",
      "weight": 400,
      "size_px": 31
    },
    {
      "usage": "正文与署名日期",
      "family": "Source Han Sans SC",
      "weight": 400,
      "size_px": 22
    },
    {
      "usage": "左侧装饰英文",
      "family": "Arial",
      "weight": 400,
      "size_px": 177,
      "note": "左侧仅有局部字形可见；GAODING为结合主品牌的装饰性近似，不作为完整可读参考文案的精确转录。"
    }
  ],
  "texture": {
    "css_approximation": "CSS重复径向微点与细线叠加近似纸面颗粒，不是真实纸纹，也不能完全复现原图随机喷点。",
    "real_texture_strategy": "生产高保真版本应单独拍摄或扫描无字白纸，去色、去光照梯度并制成无缝512×512或更大的灰度纹理；再程序生成薄荷绿与淡紫随机喷点层。纹理作为本地透明PNG或WebP平铺在背景内，不从整张海报截图取底，不混入文字、logo、二维码或喇叭。",
    "dependency": "默认仅使用CSS近似，无外网纹理依赖。"
  },
  "asset_strategy": {
    "mode": "局部素材槽与可编辑DOM组合",
    "megaphone": "按给定像素框裁出喇叭后进行精细抠图，输出相同321×368尺寸透明PNG或WebP，去掉裁切范围内的背景及公告框线。裁切范围不包含相邻正文。",
    "logo": "局部裁切真实圆形标志，必要时清除圆外纸底，不重新排字假造。",
    "qr": "参考局部裁切只用于视觉验证，不承诺可识别或链接有效；生产用已确认链接生成新二维码后绑定同一槽。",
    "binding": "所有img由{{slot}}绑定本地或内部素材路径。正文、公司名和日期保持DOM可编辑；示例公司、活动、停业安排以及X/XX日期均为参考演示，发布前必须绑定经确认事实。"
  },
  "limits": [
    "未提供原始字体文件，标题和英文只能用指定已安装字体做近似，不能宣称同款定制字体。",
    "喇叭为复杂珠光金属插画，必须使用独立抠图素材，不能以CSS形状或符号替代。",
    "正文日期按参考保留X.19-X.23、X.26及20XX年XX月17日，不自行补全实际月份、年份。",
    "左侧装饰英文缺少完整可读信息，当前属于视觉近似。",
    "固定画布和参考手动换行只保证当前文案布局；生产替换内容后必须检查行数、字宽与安全区。",
    "CSS纸纹为近似效果，真实随机颗粒需按纹理生成策略另行制作。",
    "局部裁切框以658×1170原图为准，不能直接用带背景的喇叭矩形裁图覆盖DOM公告框。"
  ],
  "local_review_notes": [
    "竖排标题使用宋体400与横向.82光学校准，保留与品牌的视觉间距，不默认宋体粗体。",
    "颗粒改为SVG随机噪声，仅绑定背景层；属于程序近似，不宣称原纹理已抠出。",
    "喇叭生产必须提供透明独立素材；验证版使用SVG轮廓裁切原图局部，非交付级抠图。"
  ]
}
```

### CSS 与可编辑文字骨架

```css
.notice-5{position:relative;width:658px;height:1170px;isolation:isolate;background:#f4f5f3;color:#202221;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-5 *{box-sizing:border-box}.notice-5 .notice-5-bg{position:absolute;inset:0;overflow:hidden;z-index:0;background:radial-gradient(ellipse 550px 185px at 330px 930px,rgba(219,177,216,.68),transparent 92%),radial-gradient(ellipse 530px 175px at 330px 654px,rgba(128,204,188,.8),transparent 94%),linear-gradient(180deg,#f6f6f4 0%,#f4f6f3 36%,#b4dcd1 57%,#e4cbe1 76%,#f7f7f4 96%)}.notice-5 .notice-5-bg:after{content:'';position:absolute;inset:0;opacity:.19;background-image:repeating-radial-gradient(circle at 17% 29%,rgba(40,67,59,.42) 0 .45px,transparent .65px 2px),repeating-linear-gradient(113deg,rgba(255,255,255,.75) 0 .6px,transparent .9px 3px);background-size:7px 9px,5px 7px;mix-blend-mode:multiply}.notice-5 .notice-5-edge{position:absolute;left:80px;top:-24px;writing-mode:vertical-rl;font-family:Arial,sans-serif;font-size:177px;line-height:1;font-weight:400;letter-spacing:35px;color:rgba(119,194,179,.38);white-space:nowrap;transform:translateX(-100%)}.notice-5 .notice-5-logo{position:absolute;left:24px;top:34px;width:44px;height:45px;z-index:3;object-fit:contain}.notice-5 .notice-5-fold{position:absolute;right:0;top:0;width:73px;height:75px;z-index:3;background:#a5cec7;clip-path:polygon(0 0,100% 0,100% 100%)}.notice-5 .notice-5-fold-line{position:absolute;right:0;top:0;width:73px;height:75px;z-index:4;border-left:1px solid #4c5250;border-bottom:1px solid #4c5250}.notice-5 .notice-5-fold-line:after{content:'';position:absolute;left:0;top:0;width:104px;height:1px;background:#4c5250;transform:rotate(45.8deg);transform-origin:left center}.notice-5 .notice-5-title{position:absolute;left:104px;top:108px;width:151px;margin:0;z-index:2;font-family:'Songti SC',serif;font-weight:700;font-size:181px;line-height:1.1;text-align:center}.notice-5 .notice-5-title span{display:block}.notice-5 .notice-5-brand{position:absolute;left:257px;top:148px;z-index:2}.notice-5 .notice-5-brand-en{margin:0;font-family:'Bodoni 72',serif;font-size:72px;font-weight:400;line-height:1.1;letter-spacing:-2.5px;transform:scaleX(.9);transform-origin:left center}.notice-5 .notice-5-brand-cn{margin:6px 0 0;font-size:31px;line-height:1.25}.notice-5 .notice-5-card{position:absolute;left:83px;top:587px;width:492px;height:512px;border:1px solid #7d8380;background:rgba(249,248,248,.79);z-index:1}.notice-5 .notice-5-message{position:absolute;left:30px;right:24px;top:31px;min-height:314px;font-size:22px;line-height:32px;letter-spacing:.35px}.notice-5 .notice-5-message p{margin:0}.notice-5 .notice-5-message .notice-5-salutation{margin-left:-4px;margin-bottom:24px}.notice-5 .notice-5-message .notice-5-indent{display:inline-block;width:2em}.notice-5 .notice-5-footer{position:absolute;left:0;right:0;top:357px;height:153px;border-top:2px solid #777573}.notice-5 .notice-5-qr{position:absolute;left:30px;top:18px;width:109px;height:111px;object-fit:contain}.notice-5 .notice-5-signature{position:absolute;right:24px;top:55px;margin:0;text-align:right;font-size:22px;line-height:25px}.notice-5 .notice-5-megaphone{position:absolute;left:253px;top:277px;width:321px;height:368px;object-fit:contain;z-index:5;pointer-events:none}
.notice-5 .notice-5-title{width:181px;font-weight:400;transform:scaleX(.82);transform-origin:left top}.notice-5 .notice-5-brand{width:330px}.notice-5 .notice-5-brand-en{width:330px;white-space:nowrap}.notice-5 .notice-5-fold-line:after{width:102px}.notice-5 .notice-5-logo{clip-path:circle(49% at 50% 50%)}
.notice-5 .notice-5-bg:after{background-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22180%22%20height%3D%22180%22%3E%3Cfilter%20id%3D%22n%22%3E%3CfeTurbulence%20type%3D%22fractalNoise%22%20baseFrequency%3D%22.86%22%20numOctaves%3D%223%22%20stitchTiles%3D%22stitch%22/%3E%3CfeColorMatrix%20type%3D%22saturate%22%20values%3D%220%22/%3E%3C/filter%3E%3Crect%20width%3D%22100%25%22%20height%3D%22100%25%22%20filter%3D%22url%28%23n%29%22%20opacity%3D%22.55%22/%3E%3C/svg%3E");background-size:180px 180px;opacity:.36;mix-blend-mode:multiply}
.notice-5 .notice-5-title{height:432px}.notice-5 .notice-5-brand-en{height:84px}.notice-5 .notice-5-brand-cn{margin-top:1px}
/* Local comparison corrections at 658px sample width */
.notice-5 .notice-5-title{top:88px}.notice-5 .notice-5-title span:last-child{position:relative;top:6px}.notice-5 .notice-5-brand-en{position:relative;top:6px;transform:scaleX(.96)}.notice-5 .notice-5-brand-cn{font-size:29px;font-weight:400}.notice-5 .notice-5-edge{left:92px;top:-16px;font-size:200px;letter-spacing:40px}.notice-5 .notice-5-bg:before{content:"";position:absolute;inset:0;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22240%22%20height%3D%22240%22%3E%3Cfilter%20id%3D%22grain%22%3E%3CfeTurbulence%20type%3D%22fractalNoise%22%20baseFrequency%3D%22.66%22%20numOctaves%3D%222%22%20stitchTiles%3D%22stitch%22/%3E%3CfeColorMatrix%20type%3D%22saturate%22%20values%3D%220%22/%3E%3CfeComponentTransfer%3E%3CfeFuncR%20type%3D%22linear%22%20slope%3D%223.6%22%20intercept%3D%22-1.4%22/%3E%3CfeFuncG%20type%3D%22linear%22%20slope%3D%223.6%22%20intercept%3D%22-1.4%22/%3E%3CfeFuncB%20type%3D%22linear%22%20slope%3D%223.6%22%20intercept%3D%22-1.4%22/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect%20width%3D%22100%25%22%20height%3D%22100%25%22%20filter%3D%22url%28%23grain%29%22/%3E%3C/svg%3E");background-size:240px 240px;opacity:.64;mix-blend-mode:screen;mask-image:linear-gradient(180deg,transparent 32%,#000 47%,#000 57%,transparent 67%,#000 81%,transparent 99%)}
```

```html
<div class="notice-5"><div class="notice-5-bg" aria-hidden="true"><div class="notice-5-edge">GAODING</div></div><img class="notice-5-logo" data-asset-slot="notice5_logo" src="{{notice5_logo}}" alt="稿定设计"><div class="notice-5-fold" aria-hidden="true"></div><div class="notice-5-fold-line" aria-hidden="true"></div><h1 class="notice-5-title" aria-label="公告"><span>公</span><span>告</span></h1><header class="notice-5-brand"><p class="notice-5-brand-en">GAODING</p><p class="notice-5-brand-cn" data-field="brand_name">稿定有限公司</p></header><section class="notice-5-card" aria-label="公告正文"><div class="notice-5-message"><p class="notice-5-salutation">亲爱的客户朋友们：</p><p data-field="notice_content"><span class="notice-5-indent"></span>为配合下周在稿定服务中心举办的集团<br>公司行业技能大赛，公司领导研究决定稿定<br>服务中心自下周一至下周五暂停营业一周<br>（X.19-X.23），下下周一（X.26）开始继续<br>营业，望相互告知。</p><p data-field="notice_apology"><span class="notice-5-indent"></span>感谢您一直以来的支持，给您带来的不<br>便，敬请谅解！</p></div><footer class="notice-5-footer"><img class="notice-5-qr" data-asset-slot="notice5_qr" src="{{notice5_qr}}" alt="公告二维码"><p class="notice-5-signature"><span data-field="issuer">稿定有限公司</span><br><span data-field="issue_date">20XX年XX月17日</span></p></footer></section><img class="notice-5-megaphone" data-asset-slot="notice5_megaphone" src="{{notice5_megaphone}}" alt="银色珠光手持喇叭"></div>
```

### 素材绑定与验证边界

- `notice5_logo`：左上角真实稿定设计圆形logo，仅裁标志区域。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `notice5_megaphone`：银色珠光喇叭与完整手柄；裁后精细抠图，剔除背景及框线，以透明独立素材叠加，不含旁边正文。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。
- `notice5_qr`：页脚二维码局部及白底，供参考验证；生产替换为已确认目标的有效二维码。 生产绑定独立就绪资产；参考裁切坐标仅用于内部验证，不作为生产依赖。

参考正文、品牌、日期和二维码仅作内部排版样本，不是已确认业务事实。正式生成替换为确认内容；图片槽不得直接引用参考整图或演示裁片。复杂纹理未生成时只能标记近似/待补；页面与文字层不可整体降低透明度。长文先调整分组、容器容量或拆页，不能隐藏溢出；更换标题、字体、素材、尺寸必须重查正文和图片安全区。字体绑定真实文件及字重，核验逐字覆盖；胡敬礼禁用，得意黑不默认回退。正式交付按主Skill路由将样式绑定到图层/行内CSS，示例style规则本身不替代交付协议。

<a id="combination.invitation-expo-wave"></a>

## 蓝白曲带展会邀请函

风格标签：二级：理性信息风 / 企业宣讲。

上部0–33%为深蓝标题与地址；中部约33%–61%是白曲带中的日期/展位；展台图位于62%–89%，末尾为主办信息与二维码。标题、数字、展台共同构成阅读层级，不把它们做成三张卡片。曲带不能穿过日期字组。

配色覆盖：深蓝#302d9a、白#ffffff、淡紫灰#dfdbea；蓝约55%、白约35%，其余为图像和辅助背带。中文粗直立黑体，日期与展位号选真实粗斜体拉丁字面，分别约76/110px；品牌小字不能压过邀请标题。

复用[主场](../layouts/hero-focus.md#layout.image-stage)、[数字层级](../layouts/layout-and-type.md#text.metric-unit)，新增[非对称曲带](../shapes/organic-shapes.md#shape.sweeping-band)。长展位号允许单独成行，展台仍保留完整主体。

| 效果／承载对象 | 组合中的实现与验收条件 |
|---|---|
| 深蓝色场／页面底 | CSS顶部略亮#38359f→下部#252482；不要统一纯蓝。背景若已带光场，取消此额外光照，只保留底色。 |
| 工业细纹／蓝场域 | `expo_texture`独立纹理，斜向透视网格/微点随纵深缩小，底部明显、标题区退弱；初始opacity=.16（建议.08–.22），normal、不平铺。只覆盖蓝底，被不透明曲带遮住；不能拿规则CSS圆点冒充。 |
| 双曲带／中部 | 白色主曲带下方再偏移100px叠淡紫灰背带，背景→背带→主带→日期，保持硬轮廓，不把两带融合成模糊渐隐。 |
| 展台与地面／独立主体 | `expo_booth`保留材质高光、接触暗部和下方弱反射；含地面时边缘颜色需接蓝场域，透明素材需保留接触暗部。不能用box-shadow替代展台反射。 |

上述材质按当前任务生成或绑定，方案可直接选用；展台和纹理缺失属于本次制作的资产任务，不改变配方可用状态。

字体与素材：以下是可编辑排版与素材槽位的组合，不声称复原原品牌字体或三维成像。正式字体按[字体绑定契约](#combination-font-binding)核验真实family/weight/style，文案增长应调整行数、区域高度和净空，不默认缩字。样本为658px宽；值为视觉估计。二维码为可替换真实资产，示例不提供可扫码活动地址。

```css
.iv-expo { position:relative; isolation:isolate; box-sizing:border-box; padding:52px; min-height:1424px; background:linear-gradient(180deg,#38359f,#252482); color:white; font-family:"Source Han Sans"; }
.iv-expo__band { position:absolute; top:450px; left:0; right:0; z-index:-1; --vl-band-height:560px; }
.iv-expo__texture { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; opacity:.16; z-index:-3; pointer-events:none; }
.iv-expo__backband { position:absolute; top:550px; left:0; right:0; z-index:-2; --vl-band-height:560px; --vl-band-paint:#dfdbea; }
.iv-expo__booth img { width:100%; height:auto; display:block; }
.iv-expo__facts { position:relative; margin:140px 0 0; text-align:right; color:#292783; }
.iv-expo__booth { min-height:300px; margin-top:70px; }
.iv-expo__footer { display:flex; justify-content:space-between; align-items:end; gap:30px; margin-top:36px; }
```

```html
<section class="iv-expo"><img class="iv-expo__texture" src="{{expo_texture}}" alt="" aria-hidden="true"><div class="iv-expo__backband vl-sweeping-band"></div><div class="iv-expo__band vl-sweeping-band"></div><header><p>品牌名称</p><h1 style="font-size:108px;margin:42px 0 12px">邀请函</h1><h2>年度工业展览会</h2><p>展览中心 · 活动地址</p></header><div class="iv-expo__facts"><p>展览时间</p><strong style="font:italic 700 68px Arial">11/05–08</strong><p style="font:italic 700 110px Arial;margin:25px 0">G07</p></div><div class="iv-expo__booth"><img src="{{expo_booth}}" alt="展台展示"></div><footer class="iv-expo__footer"><p>主办单位</p><div>报名入口</div></footer></section>
```


<a id="combination.invitation-ceremony-red"></a>

## 红金多弧信笺邀请函

风格标签：二级：国潮装饰风 / 传统纹样。

红色标题场与米金纸面形成上下嵌接，徽章压在交界；称谓、邀请正文与时间地点属于同一纸面。纸面下方保留二维码位和外侧祝语。

配色：#a30e15红底、#fbefd1纸面、#f4dfaa标题、#6f1214正文。标题直立中粗宋形约100px，主题句约36px，正文22px/1.8。暖纸色不是强制整页纸纹；徽章和标题星芒分别可选。

引用[多弧压边](../shapes/organic-shapes.md#shape.ceremony-edge)、[阅读栏](../layouts/airy-and-spacious.md#layout.reading-column)、[徽章](../shapes/capsules-and-badges.md#shape.badge)。增加邀请正文时增高纸面；第一行必须在中央弧线/徽章以下。

| 效果／承载对象 | 组合中的实现与验收条件 |
|---|---|
| 红色场／页面与压边 | 顶部较亮#bc2024、约26%到#970b10、底部#84070b；压边红面与相接背景同色，不露矩形拼接缝。CSS参数作为起点，使用时随实际素材调整。 |
| 暖纸、暗纹／纸面内部 | paper自身暖米白光场；`ceremony_paper`透明同色织纹/传统暗纹，图案在658px成图约30–70px尺度，opacity=.14起点（.08–.20）；只裁进纸面，正文opacity=1，不把规则网格当织纹。 |
| 金边与徽章／弧线及跨界 | 复用金属反光带的窄亮带：暗蜜金→乳金高光→中金，纵向偏移边保留；中央徽章要有同光向浅浮雕。纯金色线或空徽章只算几何验收。 |
| 祥云、中国结／独立装饰 | 祥云低对比附着纸面，中国结位于外侧保留编织绳股与光泽，不能叠成全页噪点。标题星芒限局部，不代替金属字面。 |

复用[金属反光带](../surfaces/metal-and-relief.md#surface.metal-bands)与[通用渐变](../colors/palettes.md#color.gradient)。原图纸面细纹无法确认精确织法，素材需按可见周期和低对比验收，不虚构源层。

字体与素材：以下是可编辑排版与素材槽位的组合，不声称复原原品牌字体或三维成像。正式字体按[字体绑定契约](#combination-font-binding)核验真实family/weight/style，文案增长应调整行数、区域高度和净空，不默认缩字。样本为658px宽；值为视觉估计。二维码为可替换真实资产，示例不提供可扫码活动地址。

```css
.iv-ceremony { padding:36px 52px; background:linear-gradient(180deg,#bc2024,#970b10 26%,#84070b); color:#f4dfaa; box-sizing:border-box; min-height:1170px; font-family:"Songti SC"; }
.iv-ceremony__title { position:relative; text-align:center; min-height:380px; z-index:2; }
.iv-ceremony__paper { position:relative; margin-top:-35px; padding:120px 36px 60px; background:radial-gradient(ellipse at 50% 12%,#fff6de,transparent 75%),#f4e4bf; color:#6f1214; border:3px solid #e3bd70; border-radius:0 0 18px 18px; text-align:center; }
.iv-ceremony__texture { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; border-radius:inherit; opacity:.14; pointer-events:none; }
.iv-ceremony__cap { --vl-cap-rim:linear-gradient(105deg,#a66d29,#fff2bd 35%,#cd9d45 55%,#fff0b6 78%,#b97e31); --vl-cap-color:#970b10; position:absolute; top:-118px; left:-3px; right:-3px; --vl-cap-height:200px; }
.iv-ceremony__body { position:relative; font-size:22px; line-height:1.8; }
.iv-ceremony__facts { border:1px solid #d4bf8d; border-radius:14px; padding:20px; margin-top:30px; }
```

```html
<section class="iv-ceremony"><header class="iv-ceremony__title"><p>品牌名称</p><h2 style="font-size:34px;margin-top:55px">协同前行 · 共启新程</h2><h1 style="font-size:106px;margin:34px 0">邀请函</h1></header><article class="iv-ceremony__paper"><img class="iv-ceremony__texture" src="{{ceremony_paper}}" alt="" aria-hidden="true"><div class="iv-ceremony__cap vl-ceremony-edge"><span class="vl-ceremony-edge__rim"></span><span class="vl-ceremony-edge__face"></span></div><div class="iv-ceremony__body"><h2>尊敬的合作伙伴</h2><p>诚邀您参与年度交流活动。<br>分享新的思考，与伙伴共同交流，<br>期待与您相聚。</p><div class="iv-ceremony__facts">时间：06月28日 14:00<br>地点：城市会客厅</div><p style="margin-top:55px">报名信息</p></div></article><p style="text-align:center;letter-spacing:8px;margin-top:36px">期待与您共赴新程</p></section>
```


<a id="combination.invitation-holographic-blue"></a>

## 冰蓝虹彩科技邀请函

风格标签：二级：抽象光感风 / 全息虹彩。

全幅虹彩流体为共享背景，标题跨宽，活动信息处于左下，亮点/二维码横跨页尾。不能因玻璃质感套用玻璃卡片。配色：#3265f2/#79d4f3背景、#92fff1辅色、白标题；彩虹反射色由素材保留，不用统一蓝滤镜覆盖。

引用[单侧信息轴](../layouts/asymmetric-balance.md#layout.cross-column-axis)、[主场](../layouts/hero-focus.md#layout.image-stage)、[胶囊](../shapes/capsules-and-badges.md#shape.badge)、[星芒](../shapes/organic-shapes.md#shape.sparkle)。标题细直立黑体，英文几何感；中文96px，英文78px，信息24–30px。几何英文原字体未识别，替换时记录字宽差异。

现有sphere-glass不能表达本图多层透明环体，保留场景素材职责。

| 效果／承载对象 | 组合中的实现与验收条件 |
|---|---|
| 蓝青色场／满版背景 | 上部蓝、右中青白亮场、下部再回蓝；用多个局部光场表达，单条线性渐变不等价。`holo_scene`已烘焙色场时关闭额外光层。 |
| 透明环体、虹彩／连续场景素材 | `holo_scene`满版、不平铺、不拆卡：右上裁出环体，主要弧线从中右向左下贯穿再卷到右下；保留多层透明边、折射重影、青白窄亮带与粉紫反射。必须能看见背景穿透而非实心蓝管，禁止全局蓝滤镜。 |
| 亮点／标题局部 | 小面积白色星芒只放标题边缘；最亮主体避免文字主笔画、左下活动信息。不能用全页柔光抹掉细节换净空。 |

骨架用`{{holo_scene}}`绑定完整场景，normal、opacity=1、cover/center；净空必须包含标题约x54–470/y320–610和左下活动区。占位渐变只是调试底，不算虹彩质感通过。

字体与素材：以下是可编辑排版与素材槽位的组合，不声称复原原品牌字体或三维成像。正式字体按[字体绑定契约](#combination-font-binding)核验真实family/weight/style，文案增长应调整行数、区域高度和净空，不默认缩字。样本为658px宽；值为视觉估计。二维码为可替换真实资产，示例不提供可扫码活动地址。

```css
.iv-holo { --vl-axis-width:58%; --vl-axis-height:1424px; --vl-axis-inset:54px; --vl-axis-pause:110px; --vl-visual-inset:32% 0 20% 34%; background:radial-gradient(ellipse at 90% 42%,#9ee4f4,transparent 56%),radial-gradient(ellipse at 25% 88%,#3051ed,transparent 52%),#376af2; color:white; font-family:"Source Han Sans"; }
.iv-holo__scene { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; z-index:0; pointer-events:none; }
.iv-holo__title { font-weight:300; font-size:96px; line-height:1.1; margin:60px 0 0; }
.iv-holo__english { font:300 78px Arial; margin:0; }
.iv-holo__highlight { display:inline-block; border-radius:50%; background:#92fff1; color:#1852c6; padding:8px 20px; font-size:26px; }
```

```html
<section class="vl-invite-axis iv-holo"><img class="iv-holo__scene" src="{{holo_scene}}" alt="" aria-hidden="true"><header class="vl-invite-axis__header"><p>品牌名称</p><p style="color:#92fff1;font-size:30px;margin-top:70px">人工智能创新峰会</p><h1 class="iv-holo__title">邀请函</h1><p class="iv-holo__english">Invitation</p><p style="border-block:1px solid #ffffff70;padding:14px 0;font-size:28px;letter-spacing:8px">智启未来 × 共创无限</p></header><div class="vl-invite-axis__rail"><div><p>活动时间</p><p style="font:48px Arial">06.28</p><p>14:00–17:30</p></div><div><p>活动地点</p><p>城市创新中心</p></div></div><footer class="vl-invite-axis__footer"><span class="iv-holo__highlight">核心亮点</span><p style="font-size:26px">前沿洞察 · 技术交流 · 实践分享</p><p style="margin-top:60px">扫码报名</p></footer></section>
```


<a id="combination.invitation-nocturne-gold"></a>

## 深蓝金光私享会邀请函

风格标签：二级：奢雅精致风 / 极简精品。

英文标题横跨上方；中文邀请、活动名、日期和地址形成左侧纵轴；玻璃雕塑右侧出血，末尾短祝语与二维码独立。配色#080d1b/#263e61、白#f7f4ed、香槟金#d9bd7e。标题高反差直立衬线，中英各有职责；日期细拉丁，不能全用粗黑。

引用[单侧信息轴](../layouts/asymmetric-balance.md#layout.cross-column-axis)、[眉线](../layouts/layout-and-type.md#layout.section-masthead)、[星芒](../shapes/organic-shapes.md#shape.sparkle)。英文约80px、中文88px、活动名38px、日期60px；金色折角线为局部装饰，不围成卡片。

玻璃材质与金粒不能用金属渐变替代；页脚与前景书写装饰另查避让。

| 效果／承载对象 | 组合中的实现与验收条件 |
|---|---|
| 暗蓝光场／满版底 | 左侧近黑，右上椭圆蓝光，页底约80%–95%高度形成横向蓝灰柔光带再回暗；两个radial-gradient分别控制，不能一层全页发亮。 |
| 玻璃褶皱／右侧素材 | `nocturne_glass`透明前景，右侧出血；深蓝透射、窄白色镜面边、多层弯折与内部暗部并存。保留透明边界，不加矩形底板、不降低整个主体opacity。 |
| 金粒／玻璃内部 | 金粒沿褶皱内缘聚散，粒度在成图约1–3px；只附着素材内部，不全页撒金粉。金粒亮度与玻璃白亮边分开，不能统一染黄。 |
| 标注线、星芒／文字周边 | 香槟金细线与局部白金星芒独立于玻璃；线不围成信息卡，局部高光不遮中文字形。 |

素材已含完整暗底时改用满版场景并关闭CSS光场，避免两次照明；两种素材模式择一。替换时核对左轴x54–355/y400–1200净空、底部浅带背后文字对比与玻璃边缘，缺图不能认定整页效果完成。

字体与素材：以下是可编辑排版与素材槽位的组合，不声称复原原品牌字体或三维成像。正式字体按[字体绑定契约](#combination-font-binding)核验真实family/weight/style，文案增长应调整行数、区域高度和净空，不默认缩字。样本为658px宽；值为视觉估计。二维码为可替换真实资产，示例不提供可扫码活动地址。

```css
.iv-nocturne { --vl-axis-width:52%; --vl-axis-height:1424px; --vl-axis-inset:54px; --vl-axis-pause:70px; --vl-visual-inset:14% 0 12% 40%; background:radial-gradient(ellipse 95% 13% at 58% 88%,#7794a9 0%,transparent 100%),radial-gradient(ellipse at 100% 20%,#365a85,transparent 60%),#080d1b; color:#f7f4ed; font-family:"Songti SC"; }
.iv-nocturne__english { font:400 79px "Bodoni 72"; margin:55px 0 16px; }
.iv-nocturne__rule { display:block; width:170px; height:1px; background:#d9bd7e; margin:14px 0; }
.iv-nocturne__label { color:#d9bd7e; font:24px Arial; }
```

```html
<section class="vl-invite-axis iv-nocturne"><div class="vl-invite-axis__visual"><img src="{{nocturne_glass}}" alt="" aria-hidden="true"></div><header class="vl-invite-axis__header"><p>品牌名称</p><p class="iv-nocturne__english">INVITATION</p><h1 style="font-size:88px;font-weight:400;margin:0">邀请函</h1><p style="color:#d9bd7e;font-size:28px">诚挚邀请您莅临</p></header><div class="vl-invite-axis__rail"><h2 style="font-size:38px;font-weight:400">年度私享会</h2><div><span class="iv-nocturne__label">TIME</span><i class="iv-nocturne__rule"></i><p style="font:60px Baskerville;margin:0">06/28</p><p style="font:24px Arial">18:00–21:00</p><p class="iv-nocturne__label">ADD</p><i class="iv-nocturne__rule"></i><p style="font-size:26px">城市会客厅<br>顶层宴会空间</p></div></div><footer class="vl-invite-axis__footer"><p style="font-size:24px;letter-spacing:5px">期待与您相聚<br>共同迎接新的时刻</p></footer></section>
```


<a id="combination.notice-blue-ticket"></a>

**原子布局对应**：[notice-ticket-sections](../layouts/notice-and-invitation.md#layout.sectioned-ticket)、[notice-fact-sections](../layouts/notice-and-invitation.md#layout.labeled-facts)、[notice-contact-footer](../layouts/notice-and-invitation.md#layout.contact-footer)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。

## 蓝色悬挂票据公告

产物：通知、公告；布局范围：整张单屏。邀请函仅在替换确认事实并重新校验阅读顺序后采用；喜报不可只换标题硬套。本轮未做整套视觉验收。

**选型策略**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

```json
{
  "artifact_tags": [
    "图6",
    "悬挂票据",
    "固定画布",
    "可编辑DOM",
    "三组标签说明",
    "独立二维码联络行"
  ],
  "dimensions": {
    "canvas": [
      658,
      1170
    ],
    "ticket": [
      62,
      69,
      534,
      893
    ],
    "upper_panel": [
      62,
      69,
      534,
      360
    ],
    "lower_panel": [
      62,
      429,
      534,
      533
    ],
    "footer": [
      112,
      1017,
      450,
      127
    ],
    "unit": "px"
  },
  "layout": {
    "structure": "背景纹理、悬挂横杆、双片票据、票内品牌与标题、分隔点线、三组标签正文、票外二维码信息行。",
    "reusable_atoms": [
      {
        "name": "悬挂容器",
        "description": "横杆置于卡片背后，卡片覆盖横杆中段；可承载通知、邀请函及活动票证，不依赖颜色或图片主题。"
      },
      {
        "name": "双区票据分隔",
        "description": "上区集中标题，下区容纳条目；共用分隔轴，左右对称内凹口与横向点线建立上下关联。"
      },
      {
        "name": "品牌—副标题—主标题栈",
        "description": "三个横向居中层级共享卡片中轴，可替换为主办方、活动名和邀请函标题。"
      },
      {
        "name": "标签与说明配对",
        "description": "左侧轻倾斜短标签位于正文上方，正文统一左缩进；三个同构条目按固定节距排列。"
      },
      {
        "name": "独立联络行",
        "description": "方形码、竖分隔线、三级文字组成横向信息行，与主卡片保持独立间距。"
      }
    ],
    "body_capacity": "正文每组宽420px，行高26px，预留至少78px三行空间；原图各组文案预计两行。正文不设隐藏溢出，装饰裁切只作用于空白背景片。"
  },
  "palette": {
    "background_base": "#438ff1",
    "subtitle_blue": "#5c9ff4",
    "paper": "#ffffff",
    "main_text": "#282828",
    "rail": "#183954",
    "footer_ink": "#103760",
    "perforation": "#b3b3b3",
    "tear_dots": "#3988d3"
  },
  "relationships": [
    {
      "type": "背景与容器",
      "description": "纹理覆盖658×1170画布，白票据在x=62至596区域遮挡纹理；横杆位于票据背后，仅两端与上沿可见，阴影向下投射。"
    },
    {
      "type": "容器与容器",
      "description": "上票据结束于y=429，下票据同轴接续；左右缺口最深处分别为x=85和573，蓝色点线贯穿缺口之间。下缘锯齿在y=948至962形成撕票轮廓。"
    },
    {
      "type": "素材与容器",
      "description": "品牌logo嵌于上票据内的品牌行，二维码不放入票据，而在票据下方独立信息行左侧；纹理素材仅承担背景，不包含标题或正文。"
    },
    {
      "type": "文字与素材",
      "description": "YOUR LOGO位于圆形logo右侧17px；二维码右侧18px后设置4px竖线，文字距竖线15px，互不覆盖。"
    },
    {
      "type": "文字与容器",
      "description": "副标题左右距票据57px，主标题使用更宽的480px居中区域；正文统一从全图x=119起排，标签稍向左伸至x约92，制造印章式层级。"
    }
  ],
  "safe_areas": [
    {
      "name": "背景与悬挂区",
      "rect": [
        0,
        0,
        658,
        64
      ],
      "rule": "保留顶部纹理及横杆上方呼吸区，不增加正文。"
    },
    {
      "name": "品牌行",
      "rect": [
        214,
        96,
        242,
        69
      ],
      "rule": "logo与品牌文本不可侵入下方y=168的灰色点线。"
    },
    {
      "name": "标题区",
      "rect": [
        89,
        203,
        480,
        203
      ],
      "rule": "主标题底部应止于缺口开始位置y=406之前；替换标题时须重新检查字宽。"
    },
    {
      "name": "正文区",
      "rect": [
        119,
        539,
        420,
        300
      ],
      "rule": "三组正文分别在y=539、686、829起排，实际第三组安全框见下一项；本区域为前两组主要排版范围，不覆盖印章。"
    },
    {
      "name": "各组正文安全框",
      "rects": [
        [
          119,
          539,
          420,
          78
        ],
        [
          119,
          686,
          420,
          78
        ],
        [
          119,
          829,
          420,
          78
        ]
      ],
      "rule": "每组最多按三行参考容量验收；增加文案须调整字号或组距，不裁字。"
    },
    {
      "name": "票据底边",
      "rect": [
        85,
        909,
        488,
        39
      ],
      "rule": "正文与锯齿之间留白，禁止文字伸入锯齿裁切带。"
    },
    {
      "name": "二维码与联络",
      "rect": [
        108,
        1017,
        450,
        127
      ],
      "rule": "二维码保留原图白底边界；生产替换码须自身含合规静区，底部保留26px画布余量。"
    }
  ],
  "fonts": [
    {
      "usage": "主标题、副标题、印章标签、联络标题",
      "family": "Source Han Sans CN",
      "weight": 700,
      "note": "已安装候选中选用较贴近的粗黑体；原图标题与印章字形更厚且可能有定制处理，不声称完全同款。"
    },
    {
      "usage": "正文",
      "family": "Source Han Sans SC",
      "weight": 400,
      "note": "22px、26px行高，保持可编辑与可读性。"
    },
    {
      "usage": "英文品牌、电话号码",
      "family": "Arial",
      "weight": 700
    }
  ],
  "texture": {
    "reference": "背景为多层斜向交叉刻线、压纹和蓝色明暗斑块；白票据整体近纯白。印章边线带轻微磨损。",
    "css_approximation": "白纸使用纯白CSS近似；印章用双层边框及虚线近似磨损，不是真实纸纹或真实印刷噪点。横杆与纸影亦为CSS近似。",
    "real_texture_generation_strategy": "从assets指定的右侧无文字蓝色背景窄条提取方向、频率与颗粒特征，离线进行纹理合成和多尺度克隆，生成658×1170无文字背景文件绑定background_texture；不得把原图整张直接作为背景，也不得将窄条直接拉伸充满画布。需要真实纸张微纹时另行离线生成低对比中性纤维纸纹，仅施加于空白纸片装饰层，不栅格化正文。"
  },
  "asset_strategy": {
    "default": "所有素材由本地槽位注入，不依赖外网。",
    "background_texture": "裁切框是原图纹理采样来源，不是最终背景尺寸；须先离线合成为658×1170。",
    "brand_logo": "独立裁取原图圆形标志，不将旁侧YOUR LOGO文字烘焙进素材。",
    "contact_qr": "独立裁取二维码含白底；原图示例码仅供视觉复核，生产应替换为已确认目标地址生成的二维码。",
    "editable_content": "所有标题、条目标签、正文、地址和电话均为DOM文本；复杂纹理、logo、二维码分别独立槽。"
  },
  "limits": [
    "稿定风景区、8月5日、09:00-17:30、免费实名预约、提前至少1天、入园证件规则、地址、电话及品牌均为参考图演示文案；生产必须绑定确认事实，不能视为真实公告。",
    "原图日期未给年份，不补写年份。",
    "原图标题及印章字重、切角和磨损无法凭已安装字体逐像素还原；本实现采用候选粗体和CSS边框近似。",
    "二维码裁图清晰度及可扫描性需要单独验证，不推断其目标链接。",
    "固定画布不提供响应式重排；更长文案需要重新分配组距或字号，不能用overflow:hidden裁切。",
    "纹理采样框仅为合成依据，不能保证未经合成处理的素材直接复用达到参考效果。"
  ]
}
```

```css
.notice-6{position:relative;width:658px;height:1170px;isolation:isolate;background:#438ff1;color:#282828;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-6 *{box-sizing:border-box}.notice-6 .n6-background{position:absolute;inset:0;width:658px;height:1170px;object-fit:cover;z-index:0}.notice-6 .n6-rail{position:absolute;left:36px;top:64px;width:586px;height:20px;border-radius:20px;background:#183954;box-shadow:0 9px 0 rgba(29,55,83,.42);z-index:1}.notice-6 .n6-ticket{position:absolute;left:62px;top:69px;width:534px;height:893px;z-index:2;filter:drop-shadow(0 17px 1px rgba(24,54,82,.42))}.notice-6 .n6-upper{position:absolute;left:0;top:0;width:534px;height:360px;border-radius:11px 11px 0 0;background:#fff;clip-path:polygon(0 0,100% 0,100% calc(100% - 23px),calc(100% - 23px) 100%,23px 100%,0 calc(100% - 23px))}.notice-6 .n6-lower{position:absolute;left:0;top:360px;width:534px;height:533px;background:#fff;clip-path:polygon(23px 0,calc(100% - 23px) 0,100% 23px,100% calc(100% - 14px),98.7% calc(100% - 7px),96.3% 100%,93.9% calc(100% - 14px),91.4% 100%,89% calc(100% - 14px),86.6% 100%,84.1% calc(100% - 14px),81.7% 100%,79.3% calc(100% - 14px),76.8% 100%,74.4% calc(100% - 14px),72% 100%,69.5% calc(100% - 14px),67.1% 100%,64.7% calc(100% - 14px),62.2% 100%,59.8% calc(100% - 14px),57.4% 100%,54.9% calc(100% - 14px),52.5% 100%,50% calc(100% - 14px),47.6% 100%,45.1% calc(100% - 14px),42.7% 100%,40.3% calc(100% - 14px),37.8% 100%,35.4% calc(100% - 14px),33% 100%,30.5% calc(100% - 14px),28.1% 100%,25.7% calc(100% - 14px),23.2% 100%,20.8% calc(100% - 14px),18.4% 100%,15.9% calc(100% - 14px),13.5% 100%,11.1% calc(100% - 14px),8.6% 100%,6.2% calc(100% - 14px),3.8% 100%,1.3% calc(100% - 14px),0 calc(100% - 7px),0 23px)}.notice-6 .n6-brand{position:absolute;left:159px;top:32px;height:59px;display:flex;align-items:center;gap:17px}.notice-6 .n6-logo{display:block;width:59px;height:59px;object-fit:contain}.notice-6 .n6-brand-text{font-family:Arial,sans-serif;font-size:27px;font-weight:700;white-space:nowrap}.notice-6 .n6-perforation{position:absolute;left:23px;top:99px;width:488px;height:6px;background:radial-gradient(circle,#b3b3b3 2.3px,transparent 2.7px) 0 0/16.3px 6px repeat-x}.notice-6 .n6-subtitle{position:absolute;left:57px;top:134px;width:420px;height:63px;margin:0;display:flex;align-items:center;justify-content:center;background:#5c9ff4;border:1px solid #5198ee;color:#fff;font-family:'Source Han Sans CN',sans-serif;font-size:42px;font-weight:700;line-height:1;letter-spacing:-2px;text-shadow:0 2px 0 rgba(43,112,186,.28)}.notice-6 .n6-title{position:absolute;left:27px;top:204px;width:480px;height:133px;margin:0;display:flex;align-items:center;justify-content:center;white-space:nowrap;font-family:'Source Han Sans CN',sans-serif;font-size:112px;font-weight:700;line-height:1;letter-spacing:-5px}.notice-6 .n6-tear-line{position:absolute;left:27px;top:357px;width:480px;height:6px;background:radial-gradient(circle,#3988d3 1.8px,transparent 2.2px) 0 0/8px 6px repeat-x;z-index:3}.notice-6 .n6-section{position:absolute;left:0;width:534px;height:142px}.notice-6 .n6-section-one{top:402px}.notice-6 .n6-section-two{top:549px}.notice-6 .n6-section-three{top:692px}.notice-6 .n6-stamp{position:absolute;left:31px;top:5px;width:151px;height:48px;margin:0;display:flex;align-items:center;justify-content:center;transform:rotate(-9deg);border:3px solid #333;border-radius:4px;outline:1px dashed #fff;outline-offset:-3px;font-family:'Source Han Sans CN',sans-serif;font-size:31px;font-weight:700;line-height:1;letter-spacing:-1.8px}.notice-6 .n6-stamp:before{content:'';position:absolute;inset:3px;border:1px solid #333;pointer-events:none}.notice-6 .n6-copy{position:absolute;left:57px;top:68px;width:420px;min-height:78px;margin:0;font-size:22px;line-height:26px;letter-spacing:-.4px;overflow:visible}.notice-6 .n6-footer{position:absolute;left:112px;top:1017px;width:450px;height:127px;z-index:2;display:flex;align-items:flex-start}.notice-6 .n6-qr{width:108px;height:108px;margin-top:10px;object-fit:contain;background:#fff}.notice-6 .n6-footer-rule{width:4px;height:127px;margin-left:18px;background:#113a68;flex:none}.notice-6 .n6-contact{margin-left:15px;padding-top:13px;white-space:nowrap}.notice-6 .n6-contact-title{margin:0 0 13px;font-family:'Source Han Sans CN',sans-serif;font-size:28px;font-weight:700;line-height:36px;letter-spacing:-1px;color:#103760}.notice-6 .n6-address{margin:0;color:#fff;font-family:'Source Han Sans CN',sans-serif;font-size:22px;font-weight:700;line-height:27px;letter-spacing:-.3px}.notice-6 .n6-phone{margin:0;color:#fff;font-family:Arial,sans-serif;font-size:26px;font-weight:700;line-height:29px}
```

```html
<div class="notice-6" aria-label="景区通知公告"><img class="n6-background" data-asset-slot="background_texture" src="{{background_texture}}" alt="" aria-hidden="true"><div class="n6-rail" aria-hidden="true"></div><main class="n6-ticket"><div class="n6-upper" aria-hidden="true"></div><div class="n6-lower" aria-hidden="true"></div><div class="n6-brand"><img class="n6-logo" data-asset-slot="brand_logo" src="{{brand_logo}}" alt="稿定设计"><span class="n6-brand-text">YOUR LOGO</span></div><div class="n6-perforation" aria-hidden="true"></div><p class="n6-subtitle" data-field="venue_name">稿定风景区</p><h1 class="n6-title">通知公告</h1><div class="n6-tear-line" aria-hidden="true"></div><section class="n6-section n6-section-one"><h2 class="n6-stamp">开放时间</h2><p class="n6-copy" data-field="opening_notice">为保障大家的安全出行，稿定风景区将于8月5日起，调整开放时间为09:00-17:30。</p></section><section class="n6-section n6-section-two"><h2 class="n6-stamp">预约指南</h2><p class="n6-copy" data-field="reservation_notice">景区实行免费实名制预约，需提前至少1天于官网预约。</p></section><section class="n6-section n6-section-three"><h2 class="n6-stamp">入园须知</h2><p class="n6-copy" data-field="entry_notice">游客入园须携带个人身份证，并出示预约码，按次序排队进入景区。</p></section></main><footer class="n6-footer"><img class="n6-qr" data-asset-slot="contact_qr" src="{{contact_qr}}" alt="扫码关注二维码"><div class="n6-footer-rule" aria-hidden="true"></div><div class="n6-contact"><p class="n6-contact-title" data-field="contact_heading">扫码关注&nbsp; 稿定景区</p><p class="n6-address" data-field="contact_address">厦门高林中路稿定大厦27楼</p><p class="n6-phone" data-field="contact_phone">0592-6666888</p></div></footer></div>
```

- `background_texture`：无正文蓝色交叉压纹采样；离线合成完整背景纹理后注入，不直接拉伸此窄条。
- `brand_logo`：圆形稿定设计标志，裁框不含右侧YOUR LOGO文字。
- `contact_qr`：底部独立二维码及原有白底边界，裁框不含右侧竖线和联络文字。

素材槽需绑定独立就绪资产；参考裁片只用于验证。准确正文使用DOM，示例日期、联系方式与品牌必须替换成确认事实；图7页脚黑方块不推断为有效二维码。字体绑定真实family/weight并核对字形，胡敬礼禁用，得意黑不作默认。程序纹理只能标为近似，不能声称原始纹理已提取。正式交付按主Skill路由展开为行内样式。


<a id="combination.notice-summer-notebook"></a>

**原子布局对应**：[notice-bound-letter](../layouts/notice-and-invitation.md#layout.bound-paper-stack)、[notice-fact-sections](../layouts/notice-and-invitation.md#layout.labeled-facts)、[notice-contact-footer](../layouts/notice-and-invitation.md#layout.contact-footer)。按原子读取几何和安全区，以下完整样本保留参考尺寸的局部覆盖；重新组装时用原子骨架，不重复叠加两套默认布局。 偏轴主视觉复用[单侧信息轴](../layouts/asymmetric-balance.md#layout.cross-column-axis)，标题错位复用[错落标题](../layouts/asymmetric-balance.md#layout.staggered-title)。

## 暑假装订纸通知

产物：通知、公告；布局范围：整张单屏。邀请函仅在替换确认事实并重新校验阅读顺序后采用；喜报不可只换标题硬套。本轮未做整套视觉验收。

**选型策略**：[公告通知视觉策略](../../../../references/style/coding/scenarios/announcement-poster-spec.md#notice-visual-css-routing)。

```json
{
  "artifact_tags": [
    "notice-7",
    "固定尺寸海报",
    "可编辑通知正文",
    "偏轴双层标题条",
    "人物跨层叠放",
    "装订纸容器",
    "药丸小标题",
    "独立底部联络行"
  ],
  "dimensions": {
    "width": 469,
    "height": 1024,
    "unit": "px",
    "canvas": "固定469×1024，不包含预览UI",
    "coordinate_origin": "原图左上角"
  },
  "layout": {
    "header": "顶部0–344px；左上品牌，112px起双层标题条，人物位于右上并覆盖标题右端。",
    "body": "白纸位于[37,344,396,557]；背后绿色纸片轻微旋转，顶部12枚装订环；白纸右下有突出折角。",
    "content": "引言位于[74,396,322,约78]；第一药丸标题[153,495,163,35]，日期框[58,543,354,36]；第二药丸标题[153,606,163,35]，说明框[58,657,354,至少213]。",
    "footer": "联络行独立置于白纸下方，左侧深色方块，右侧电话标识、热线说明、号码和公司名。",
    "reusable_atoms": [
      {
        "name": "偏轴双层标题条",
        "description": "主次标题分置两条轻微错位的矩形条，允许独立设定横向偏移和倾斜；可用于通知、邀请函，不依赖颜色和人物主题。"
      },
      {
        "name": "边缘跨层素材锚点",
        "description": "独立透明素材锚定容器右上，局部压住标题，正文安全区不被侵入；可替换为活动主视觉。"
      },
      {
        "name": "背衬与主纸双层容器",
        "description": "正向正文面板加轻微旋转的背衬，装订件和折角作为独立装饰层。"
      },
      {
        "name": "居中短标题加全宽说明框",
        "description": "短标题居中，内容框沿统一左右边界排列；适合日期、地点、注意事项与邀请说明。"
      },
      {
        "name": "分隔式要点列表",
        "description": "同一正文框内以虚线分隔、圆点引导条目，文本维持正常排版。"
      },
      {
        "name": "独立联络行",
        "description": "左侧方形媒体位，右侧紧凑联系方式及机构信息；与主正文容器分离。"
      }
    ]
  },
  "palette": {
    "background_top": "#ACEEFA",
    "background_middle": "#F4F8DD",
    "background_bottom": "#B9E334",
    "title_lime": "#CDF76B",
    "title_dark": "#252823",
    "paper": "#FFFFFF",
    "back_sheet": "#79C829",
    "content_panel": "#F0F7E0",
    "text": "#161616",
    "emphasis": "#EC6400",
    "divider": "#83B752"
  },
  "relationships": [
    {
      "type": "背景与容器",
      "description": "全画布渐变在最底层；绿色背衬位于渐变之上、白纸之下；白纸承载所有正文，不使用原图正文截图。"
    },
    {
      "type": "素材与容器",
      "description": "人物保持原图[262,4,207,341]锚点，位于标题条上方，鞋底在白纸顶部附近结束；装订环覆盖白纸上边缘，彼此独立于正文。"
    },
    {
      "type": "文字与素材",
      "description": "中文标题保持在左侧主要可视区，人物遮住标题条右端及部分英文是参考图的叠放关系；引言起始高度396px，避开人物和装订环。"
    },
    {
      "type": "文字与容器",
      "description": "引言左右内缩37px；日期框与说明框左右内缩21px；说明框文字再内缩21px，段落、虚线及圆点均在框内排版。"
    },
    {
      "type": "底部媒体与文字",
      "description": "左侧方形位和右侧联络信息保留12px间距；电话号码和机构名为DOM文本，不合并进图像。"
    }
  ],
  "safe_areas": [
    {
      "target": "背景与主容器",
      "region": [
        37,
        344,
        396,
        557
      ],
      "rule": "白纸主体左右各约36px画布留白；背衬可越出纸边，不允许覆盖文字。"
    },
    {
      "target": "人物素材",
      "region": [
        262,
        4,
        207,
        341
      ],
      "rule": "只能参与顶部标题叠放；不得向下侵入396px起的引言。"
    },
    {
      "target": "装订区",
      "region": [
        49,
        334,
        372,
        42
      ],
      "rule": "装订装饰占用纸顶区域，正文与装订最低点保留约20px。"
    },
    {
      "target": "引言",
      "region": [
        74,
        396,
        322,
        83
      ],
      "rule": "完整显示三行左右的参考引言，不用overflow:hidden裁字。"
    },
    {
      "target": "正文说明",
      "region": [
        79,
        675,
        312,
        179
      ],
      "rule": "正文自然换行；说明框使用min-height，原文排完后距白纸底部约31px。"
    },
    {
      "target": "底部联络行",
      "region": [
        72,
        929,
        336,
        52
      ],
      "rule": "机构名保持在画布内，整体距底边约43px；若生产置入二维码，应把所需静区包含在媒体资源内并重新校验可扫性。"
    }
  ],
  "fonts": [
    {
      "usage": "暑假、放假通知",
      "family": "Source Han Sans CN",
      "weight": 700,
      "treatment": "负字距与skew(-10deg)近似原图粗黑斜体标题。",
      "limitation": "为已安装候选中的近似，不声称与原图定制标题字形相同。"
    },
    {
      "usage": "正文、药丸标题、机构名",
      "family": "Source Han Sans SC",
      "weight": 400,
      "treatment": "正文14–16px，小标题20px。"
    },
    {
      "usage": "英文与电话号码",
      "family": "Arial",
      "weight": 400,
      "treatment": "顶部英文使用italic，底部号码20px。"
    }
  ],
  "texture": {
    "css_approximation": "白纸用极低透明度重复细线近似轻微纸面质感；背景以CSS渐变近似，装订环以边框曲线近似。以上均非原图真实纹理。",
    "real_texture_strategy": "如需真实纸纹，从原图白纸无文字区域[43,385,25,240]取样，去除亮度渐变与阴影，离线进行无缝扩展和低对比归一化，生成本地透明纸纹小图；仅叠加到.paper，不生成或烘焙任何正文、标题及整张海报。"
  },
  "asset_strategy": {
    "default": "图片均由本地资产槽注入，不依赖外网；文字、色块、装订环、折角、渐变为DOM/CSS。",
    "student_illustration": "给出的矩形是原图人物整体包围框。人物与英文和标题已有重叠，矩形直裁不可直接使用：需在该坐标框内提取人物、书本、背包和鞋的精确前景蒙版，清除所有背景及标题文字，输出同尺寸透明PNG。最终可见素材不得含旁边正文。",
    "brand_logo": "真实品牌标识独立裁切，不用字体假造；生产应替换成有权使用的品牌资产。",
    "phone_icon": "仅截取电话图标，不带邻近热线文案。",
    "qr": "原图[72,929,51,50]仅能确认深色实心方块，未见可识别二维码，故以CSS方块忠实保留，不虚构二维码。生产需要二维码时，将其替换为<img class=\"qr\" data-asset-slot=\"contact_qr\" src=\"{{contact_qr}}\" alt=\"联系二维码\">，且由确认后的链接离线生成；该新素材不是原图裁切资产。"
  },
  "limits": [
    "仅执行图7；不套用其他图的票据、爆炸标题或竖排公告结构。",
    "2025年及日期区间是参考图可读文案，并非当前有效放假事实；生产必须绑定已确认的机构、年份、日期和通知内容。",
    "152-XXXX-8888与众图网网络科技有限公司属于参考演示信息；不可作为真实热线或发布主体直接投产。",
    "底部极小英文按可辨内容转录为NATIONAL UNIFIED FREE SERVICE HOTLINE，发布前宜以源文件复核。",
    "标题字形、装订环与折角为CSS近似，不保证与原图逐像素一致。",
    "人物槽必须经过前景分离；使用未经去背景的矩形裁切会把原图文字带入，属于不合格资产。",
    "正文区域按参考全文保留足够高度，未使用overflow:hidden；替换为明显更长文案时需重新校验分行、扩展正文布局或精简经确认文案，不能裁字。",
    "低分辨率原图无法恢复高清人物细节和真实纸纹；高分辨率生产需取得对应授权原素材。",
    "固定画布不自适应重排；如外部缩放，应整体等比缩放。"
  ]
}
```

```css
.notice-7{position:relative;width:469px;height:1024px;isolation:isolate;background:linear-gradient(180deg,#aceefa 0%,#e8f9fb 35%,#f4f8dd 58%,#b9e334 100%);color:#161616;font-family:'Source Han Sans SC',Arial,sans-serif;font-weight:400}.notice-7 *{box-sizing:border-box}.notice-7 .corner{position:absolute;left:0;top:0;width:130px;height:78px;background:#fff;border-radius:0 0 105px 0}.notice-7 .logo{position:absolute;left:48px;top:47px;width:84px;height:39px;object-fit:contain}.notice-7 .title-top{position:absolute;left:49px;top:112px;width:318px;height:87px;background:#cdf76b;transform:rotate(.15deg)}.notice-7 .summer{position:absolute;left:19px;top:1px;margin:0;font-family:'Source Han Sans CN',sans-serif;font-size:61px;font-weight:700;line-height:1.32;letter-spacing:-4px;transform:skew(-10deg)}.notice-7 .english{position:absolute;left:147px;top:24px;font-family:Arial,sans-serif;font-style:italic;font-size:22px;line-height:24px}.notice-7 .title-main{position:absolute;left:41px;top:198px;width:313px;height:87px;background:#252823;border:1px solid #111;transform:rotate(-.2deg)}.notice-7 .title-main h1{margin:3px 0 0 21px;color:#d1fa79;font-family:'Source Han Sans CN',sans-serif;font-size:60px;font-weight:700;letter-spacing:-3px;line-height:78px;white-space:nowrap;transform:skew(-10deg)}.notice-7 .student{position:absolute;left:262px;top:4px;width:207px;height:341px;object-fit:contain;z-index:4}.notice-7 .back-sheet{position:absolute;left:38px;top:344px;width:395px;height:557px;background:#79c829;transform:rotate(-3.2deg);z-index:1}.notice-7 .paper{position:absolute;left:37px;top:344px;width:396px;height:557px;background:#fff;box-shadow:2px 2px 3px #35680055;z-index:2}.notice-7 .paper:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.035;background-image:repeating-linear-gradient(0deg,#777 0,#777 .35px,transparent .35px,transparent 3px)}.notice-7 .paper:after{content:'';position:absolute;right:39px;bottom:-37px;width:61px;height:39px;background:#fff;clip-path:polygon(0 0,72% 0,100% 100%);filter:drop-shadow(2px 2px 1px #42701b55)}.notice-7 .fold-shadow{position:absolute;left:350px;top:887px;width:60px;height:47px;background:#7ec92f;clip-path:polygon(0 0,77% 0,100% 100%);z-index:1}.notice-7 .binding{position:absolute;left:14px;top:-9px;display:flex;gap:3px;height:40px;z-index:3}.notice-7 .ring{position:relative;width:28px;height:35px;border:2px solid #4b9f0e;border-left-color:transparent;border-radius:50%;transform:rotate(-19deg)}.notice-7 .ring:after{content:'';position:absolute;left:1px;bottom:-3px;width:11px;height:8px;border-radius:50%;background:#6b963844;box-shadow:0 2px 2px #50751733}.notice-7 .intro{position:absolute;left:37px;top:52px;width:322px;margin:0;font-size:16px;line-height:26px;text-indent:2em}.notice-7 .pill{position:absolute;left:116px;width:163px;height:35px;margin:0;border-radius:22px;background:#c8f46b;display:flex;align-items:center;justify-content:center;gap:17px;font-size:20px;line-height:35px;font-weight:400;box-shadow:inset 0 0 0 1px #bce95066}.notice-7 .pill:before,.notice-7 .pill:after{content:'';width:9px;height:9px;border-radius:50%;background:#fff;flex:none}.notice-7 .time-title{top:151px}.notice-7 .time-box{position:absolute;left:21px;top:199px;width:354px;min-height:36px;margin:0;padding:6px 12px;border-radius:13px;background:#f1f7e1;text-align:center;font-size:16px;line-height:24px}.notice-7 .notes-title{top:262px}.notice-7 .notes-box{position:absolute;left:21px;top:313px;width:354px;min-height:213px;padding:18px 21px 16px;background:#f0f7e0;border-radius:14px;font-size:14px;line-height:22px}.notice-7 .notes-box p{margin:0}.notice-7 .notes-box strong{font-weight:400;color:#ec6400}.notice-7 .notes-box ul{list-style:none;margin:10px 0 0;padding:0}.notice-7 .notes-box li{position:relative;margin:0;padding:10px 0 9px 15px;border-top:1px dashed #83b752}.notice-7 .notes-box li:last-child{padding-bottom:0}.notice-7 .notes-box li:before{content:'';position:absolute;left:1px;top:18px;width:6px;height:6px;background:#f38a21;border-radius:50%}.notice-7 .footer{position:absolute;left:72px;top:929px;width:336px;height:52px;display:flex;align-items:flex-start;gap:12px;z-index:3}.notice-7 .qr-placeholder{width:51px;height:50px;background:#252728;border:1px solid #121717;flex:none}.notice-7 .qr{display:block;width:51px;height:50px;object-fit:contain;flex:none}.notice-7 .contact{padding-top:4px;flex:1;min-width:0}.notice-7 .phone-row{display:flex;align-items:center;gap:4px;white-space:nowrap}.notice-7 .phone-icon{width:18px;height:21px;object-fit:contain;flex:none}.notice-7 .phone-caption{display:flex;flex-direction:column;line-height:11px}.notice-7 .phone-caption small{font-family:Arial,sans-serif;font-size:5px;letter-spacing:-.1px}.notice-7 .phone-caption span{font-size:11px;letter-spacing:-.3px}.notice-7 .phone-number{font-family:'Arial',sans-serif;font-size:20px;line-height:22px;letter-spacing:-.8px}.notice-7 .company{margin:3px 0 0;font-size:14px;line-height:18px;white-space:nowrap;letter-spacing:.3px}
```

```html
<div class="notice-7" role="article" aria-label="暑假放假通知"><div class="corner" aria-hidden="true"></div><img class="logo" data-asset-slot="brand_logo" src="{{brand_logo}}" alt="众图网 精品素材·每日更新"><div class="title-top"><p class="summer">暑假</p><div class="english">SUMMER<br>VACATION</div></div><div class="title-main"><h1>放假通知</h1></div><img class="student" data-asset-slot="student_illustration" src="{{student_illustration}}" alt="背书包、抱书挥手的学生插画"><div class="back-sheet" aria-hidden="true"></div><div class="fold-shadow" aria-hidden="true"></div><section class="paper" aria-label="通知正文"><div class="binding" aria-hidden="true"><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i><i class="ring"></i></div><p class="intro">我们即将迎来2025年的暑假，为做好暑假安全工作，度过愉快的暑假，就我校暑假安排做出如下通知:</p><h2 class="pill time-title">放假时间</h2><p class="time-box">2025年7月5日-8月30日</p><h2 class="pill notes-title">注意事项</h2><div class="notes-box"><p>为了孩子的安全，请家长在暑假期间对孩子加强<strong>安全教育</strong>和<strong>自我保护意识</strong>，并配合做好以下几点:</p><ul><li>请注意别让孩子玩水、火、气、电等危险的东西<br>不要把孩子独留在家；外出时注意交通安全。</li><li>请科学合理的安排一天生活，注意动静交替，带领孩子坚持身体锻炼、参加各项有意义的活动。</li></ul></div></section><footer class="footer"><div class="qr-placeholder" aria-label="原图深色方块，未显示可识别二维码"></div><div class="contact"><div class="phone-row"><img class="phone-icon" data-asset-slot="phone_icon" src="{{phone_icon}}" alt="电话"><div class="phone-caption"><small>NATIONAL UNIFIED FREE SERVICE HOTLINE</small><span>全国统一免费服务热线:</span></div><span class="phone-number">152-XXXX-8888</span></div><p class="company">众 / 图 / 网 / 网 / 络 / 科 / 技 / 有 / 限 / 公 / 司</p></div></footer></div>
```

- `brand_logo`：左上众图网真实logo及其标语，局部独立裁切，不含通知正文。
- `student_illustration`：右上学生、书本与背包插画的原图定位包围框；必须抠出透明前景，剔除框内背景及被叠压的标题文字，不可直接矩形贴图。
- `phone_icon`：底部独立电话标识，仅图标，不包含相邻热线说明和号码。

素材槽需绑定独立就绪资产；参考裁片只用于验证。准确正文使用DOM，示例日期、联系方式与品牌必须替换成确认事实；图7页脚黑方块不推断为有效二维码。字体绑定真实family/weight并核对字形，胡敬礼禁用，得意黑不作默认。程序纹理只能标为近似，不能声称原始纹理已提取。正式交付按主Skill路由展开为行内样式。

<a id="combination.bamboo-open-scroll"></a>

## 竹韵东方·开放留白长页

风格标签：二级：新中式风 / 当代东方。

**产物适用标签**：产物：社媒长图；适配产物：品牌详情长图；粒度：连续章节组合。适用于短组信息与自然空间展示；密集参数表或长篇论文不采用。规划时选定“绘画开篇—花窗留白—左右偏置说明—定制服务—室内摄影—竹景结尾”，不按风格名自动套用。

与古画游园长卷的区别：主体为开放白底上的现代编辑结构，四组短说明左右接力，非园林环绕中央窄文或商品画框。原参考的两条展示顺序未知，本条是可复用重组，不规定原图接续顺序；不包括外展示板、左条独立深绿收尾及所有装饰微字。

### 依赖与槽位

必需运行依赖：[中式花瓣窗框](../shapes/cards-and-panels.md#shape.chinese-petal-window)与[偏置内容组](../layouts/asymmetric-balance.md#layout.offset-rhythm)。先加载两个原子的CSS，再加载本组合CSS。其余排版由下列组合关系实现，示例不复制原子网格。配色参考[竹林深绿](../colors/fresh-and-natural.md#palette.bamboo-olive)的色相，但本例白底占主，不继承其65%深绿面积配比。[图片透明衔接](../surfaces/diffuse-light.md#surface.image-fade)仅为可选依赖，默认关闭。

| 槽位 | 必选性与拓扑 | 资产、裁切与文字关系 |
|---|---|---|
| page共底 | 唯一共同父层 | #fbfcf8原生底色；不按内容组重复底图，无独立卡片。整页额外纸纹默认无 |
| painting | 必选，开篇独立图窗 | 无字东方绘画，宽高约3:4，按原比例完整显示；建议长边≥1440px。不是页面背景，图内矿物颜料和笔触不由CSS噪点替代 |
| window-content | 必选，花瓣窗框内部可替换素材 | 使用shape.chinese-petal-window；只提供竹叶图片，不包含花窗轮廓或玻璃外壳。宽330px/max78%，图片在窗内裁切；可换摄影或中央短文字 |
| content-groups | 必选，正常流内四组 | 标题/微标/正文在同组，原子7/12栏宽；2–6组可变但须重排停顿。无底板，无文字蒙版 |
| service | 必选，局部横/竖阅读轴 | 横排英文与短文、右侧中文竖题；文字由coding承载，不与照片烘焙 |
| bamboo-strip | 可选独立图窗 | 无字竹叶横图；启用用bov-strip，宽100%、高86px、object-fit:cover并查裁切。不启用则删除img及对应间距，不另做假色块。本案例未启用 |
| interior | 必选，独立室内图窗 | 枝叶/长凳/挂画/地面摄影关系，建议宽≥1032px，完整等比例显示；无叠字，照片内部光照不另加滤镜 |
| hero | 必选，末章唯一全域背景 | 一张无字连续竹景位于backdrop，共同覆盖末章两段文字和下方场景；可包含已合成前景，不再另拆竹叶层。建议宽≥1024px，按实际章节比例选素材 |
| ending-copy | 必选，背景的兄弟内容层 | 文字z2，背景z0；末章文字框必须处于素材最终裁切后的浅色净空，本例在顶部32%以内。背景实体与高频纹理不得穿字 |

### 字形、配色与质感

600px画幅试排：英文主题42px、服务题34px，中文主题28px、组题22px，正文15px/1.85。实测face为STSongti-SC-Regular、PingFangSC-Regular；辅助英文Arial。原图字体未知，这是已验证候选，换字体需重验断行；不把这些字号推广到所有画幅。

正文#253a2e、辅绿#52634e、点缀绿#376545。绘画与室内木纹来自素材；花窗的淡绿底、柔和内缘和边线来自组合参数，竹叶为可替换图片。本例末章纸感、淡雾到深竹的明暗已包含在hero里，CSS色场、局部光场和alpha均关闭；不重复叠加同效果。需要上缘淡入时，仅对图像上缘安全空场启用image-fade，范围至多0–14%，不得对整个section或文字做opacity/mask。背景整体变暗不可作为“增强质感”的通用选项。

### 增长与验证边界

左右文字安全边42px；正文与图片正常流，无绝对定位文本。四组说明单组增长3倍已验证后组下移；超过约160字或窄画幅难读时主动选wide，不能缩字塞入。末章背景一旦切换素材或增长正文，须重算裁切和净空；本例顶部32%是该最终素材下的验收条件，不是所有竹景的固定阈值。超过净空时换同尺寸更大空场素材或调整段落组织，不拉伸竹叶、不按段拆图。

验证状态：**组合效果已验（本条声明的重组范围、4个必选素材槽位）**。600/420px与默认/三倍说明正文共4种实渲染通过，原型与字体证据留任务报告。生成素材与参考有差异：开篇更偏金棕、窗内植物图不同、室内更暖；本案例验证槽位关系及风格方向，不声称像素级复刻或原素材还原。可选细图带、原图左条深绿结尾与长末章扩容未验证。


### 花窗槽位与表面修正

```json
{"dependencies":["layout.offset-rhythm","shape.chinese-petal-window"]}
```

窗框实例：背景为page共享白底；pw-clip只裁窗内素材，不裁整页。window-content替代旧emblem整图槽位；轮廓固定，换素材不改path。pw-surface径向色场仅限窗内，pw-relief沿轮廓柔化内缘，强度.5；pw-edge淡绿细线。三个层均与内容独立，默认由本组合开启；原子不预设玻璃效果。无需实际折射，禁止生成带外壳的物件图再次叠入窗框。多窗实例ID必须唯一。可选coding文字位于22%中央安全框，不承载长段落。

本次修正对照中部花窗参考，三种替换内容和尺寸测试通过，完整case已重渲染。此前整张玻璃物件生成属于分类偏差，不作为此配方的必需素材或验证结论。

```css
.bov-page{width:600px;max-width:100%;margin:0 auto;position:relative;isolation:isolate;background:#fbfcf8;color:#253a2e;font-family:'PingFang SC',Arial,sans-serif}.bov-page *{box-sizing:border-box}.bov-painting{display:block;width:100%;height:auto}.bov-masthead{padding:26px 24px 0}.bov-english{margin:0;font:400 42px/1.12 'Songti SC',serif;letter-spacing:-1.5px}.bov-micro{margin:12px 0 0;font:11px/1.6 Arial,'PingFang SC',sans-serif;letter-spacing:1.4px}.bov-opening{padding:100px 42px 22px;text-align:center}.bov-opening h1{margin:0;font:400 28px/1.7 'Songti SC',serif;letter-spacing:3px}.bov-opening p{margin:8px 0 0;font-size:11px;letter-spacing:1.4px}.bov-dual{display:flex;justify-content:space-between;margin-top:74px;text-align:left;font-size:12px;line-height:1.7}.bov-rhythm{--orx-pad:42px;--orx-inner:10px;padding-top:0;padding-bottom:96px}.bov-rhythm h2{font:400 22px/1.5 'Songti SC',serif}.bov-rhythm h2::before{content:'•';color:#376545;margin-right:9px}.bov-rhythm p{font-size:15px;line-height:1.85}.bov-rhythm small{font:10px/1.5 Arial,'PingFang SC',sans-serif;letter-spacing:.8px}.bov-service{padding:32px 42px 70px}.bov-service-title{margin:0;font:400 34px/1.2 'Songti SC',serif;letter-spacing:-1px}.bov-service-axis{display:grid;grid-template-columns:minmax(0,1fr) 58px;gap:34px;min-height:300px;padding-top:62px}.bov-service-copy{align-self:end;max-width:310px}.bov-service-copy p{margin:0;font-size:15px;line-height:1.85}.bov-vertical{margin:0;writing-mode:vertical-rl;text-orientation:upright;justify-self:end;font:400 29px/1.7 'Songti SC',serif;letter-spacing:5px;border-left:4px solid #647b51;padding-left:12px}.bov-strip{display:block;width:100%;height:86px;object-fit:cover;margin-top:34px}.bov-interior{display:block;width:100%;height:auto;margin-top:36px}.bov-ending{position:relative;isolation:isolate;min-height:1040px;padding:58px 42px 560px}.bov-backdrop{position:absolute;inset:0;z-index:0;pointer-events:none}.bov-backdrop img{display:block;width:100%;height:100%;object-fit:cover;object-position:center bottom}.bov-ending-copy{position:relative;z-index:2;max-width:450px}.bov-ending-copy h2{margin:0 0 20px;font:400 28px/1.5 'Songti SC',serif}.bov-ending-copy p{margin:0 0 18px;font-size:15px;line-height:1.9}.bov-ending-copy small{font:11px/1.6 Arial,'PingFang SC',sans-serif;letter-spacing:1px}
.bov-window{--pw-relief:.5;--pw-base:#eff4e8;--pw-edge:#a7baa0;--pw-line:.004;--pw-surface:radial-gradient(ellipse at 44% 40%,transparent 52%,rgb(130 158 119 / .24) 89%,rgb(93 122 80 / .40) 100%);width:330px;max-width:78%;margin:56px auto 28px}
```

```html
<article class="bov-page"><img data-slot="painting" src="SLOT:painting" class="bov-painting" alt="青绿山石与白花组成的东方装饰画"><header class="bov-masthead"><p class="bov-english">NEW CHINESE STYLE</p><p class="bov-micro">竹影 · 日常空间</p></header><section class="bov-opening"><h1>绿意生活 · 竹韵东方</h1><p>让自然的秩序，进入日常</p><div class="bov-dual"><span>静处<br>STILL</span><span>雅致<br>REFINED</span></div><figure class="pw-window bov-window" style="--pw-clip:url(#pw-bamboo)"><svg class="pw-defs" aria-hidden="true"><defs><clipPath id="pw-bamboo" clipPathUnits="objectBoundingBox"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></clipPath></defs></svg><div class="pw-clip"><img class="pw-image" data-slot="window-content" src="SLOT:window-content" alt="花瓣窗内的竹叶"><svg class="pw-relief" viewBox="0 0 1 1" aria-hidden="true"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></svg><span class="pw-surface" aria-hidden="true"></span></div><svg class="pw-edge" viewBox="0 0 1 1" aria-hidden="true"><path d="M0.50000,0.04000 C0.52561,0.04000 0.55361,0.05138 0.57684,0.06422 C0.60007,0.07707 0.61968,0.10074 0.63937,0.11708 C0.65907,0.13341 0.67457,0.15046 0.69500,0.16225 C0.71543,0.17404 0.73794,0.17895 0.76194,0.18784 C0.78593,0.19672 0.81624,0.20187 0.83897,0.21557 C0.86171,0.22926 0.88557,0.24782 0.89837,0.27000 C0.91118,0.29218 0.91532,0.32212 0.91581,0.34866 C0.91630,0.37520 0.90561,0.40401 0.90131,0.42924 C0.89701,0.45446 0.89000,0.47641 0.89000,0.50000 C0.89000,0.52359 0.89701,0.54554 0.90131,0.57076 C0.90561,0.59599 0.91630,0.62480 0.91581,0.65134 C0.91532,0.67788 0.91118,0.70782 0.89837,0.73000 C0.88557,0.75218 0.86171,0.77074 0.83897,0.78443 C0.81624,0.79813 0.78593,0.80328 0.76194,0.81216 C0.73794,0.82105 0.71543,0.82596 0.69500,0.83775 C0.67457,0.84954 0.65907,0.86659 0.63937,0.88292 C0.61968,0.89926 0.60007,0.92293 0.57684,0.93578 C0.55361,0.94862 0.52561,0.96000 0.50000,0.96000 C0.47439,0.96000 0.44639,0.94862 0.42316,0.93578 C0.39993,0.92293 0.38032,0.89926 0.36063,0.88292 C0.34093,0.86659 0.32543,0.84954 0.30500,0.83775 C0.28457,0.82596 0.26206,0.82105 0.23806,0.81216 C0.21407,0.80328 0.18376,0.79813 0.16103,0.78443 C0.13829,0.77074 0.11443,0.75218 0.10163,0.73000 C0.08882,0.70782 0.08468,0.67788 0.08419,0.65134 C0.08370,0.62480 0.09439,0.59599 0.09869,0.57076 C0.10299,0.54554 0.11000,0.52359 0.11000,0.50000 C0.11000,0.47641 0.10299,0.45446 0.09869,0.42924 C0.09439,0.40401 0.08370,0.37520 0.08419,0.34866 C0.08468,0.32212 0.08882,0.29218 0.10163,0.27000 C0.11443,0.24782 0.13829,0.22926 0.16103,0.21557 C0.18376,0.20187 0.21407,0.19672 0.23806,0.18784 C0.26206,0.17895 0.28457,0.17404 0.30500,0.16225 C0.32543,0.15046 0.34093,0.13341 0.36063,0.11708 C0.38032,0.10074 0.39993,0.07707 0.42316,0.06422 C0.44639,0.05138 0.47439,0.04000 0.50000,0.04000 Z"/></svg></figure></section><div class="orx-flow bov-rhythm"><section class="orx-group"><h2>自然材质</h2><small>NATURAL MATERIAL</small><p>让木与竹保留原有的纹理，在明亮的空间里，呈现温润而安静的触感。</p></section><section class="orx-group orx-group--right orx-group--quiet"><h2>细处见意</h2><small>THOUGHTFUL DETAILS</small><p>从边缘的收束，到转角的留白，让每一次靠近，都能看见恰到好处的分寸。</p></section><section class="orx-group orx-group--quiet"><h2>循形而作</h2><small>CRAFT AND FORM</small><p>顺着材料的方向安排线条，以简洁的结构承接日常，不用繁复装饰填满空间。</p></section><section class="orx-group orx-group--right orx-group--quiet"><h2>自在相伴</h2><small>EVERYDAY LIVING</small><p>一处阅读、一段独坐、一场与朋友的相聚，让器物在不同场景里安然相处。</p></section></div><section class="bov-service"><h2 class="bov-service-title">CUSTOMIZED SERVICE</h2><div class="bov-service-axis"><div class="bov-service-copy"><p>从空间的光线与动线出发，讨论材质、尺度和摆放方式。让每一件物品，都与真实的生活相互呼应。</p></div><h3 class="bov-vertical">定制服务</h3></div><img data-slot="interior" src="SLOT:interior" class="bov-interior" alt="枝叶、长凳与绿色挂画构成的安静室内"></section><section class="bov-ending"><div class="bov-backdrop"><img data-slot="hero" src="SLOT:hero" alt=""></div><div class="bov-ending-copy"><h2>品牌理念。</h2><small>留白之中，自有生机</small><p>我们关注器物与空间之间的距离，也关注人与自然重新相遇的方式。让光线可以经过，让枝叶能够舒展，让日常不必匆忙。</p><p>以克制的线条承接丰富的生活，在看得见的细节之外，留下一份可以慢慢感受的安静。</p></div></section></article>
```

将SLOT:占位绑定为本次生成或已获用权的真实资产路径，不可留缺图；实际资产不随本配方默认绑定。正式交付按既有协议展开样式。

<a id="combination.woodcraft-airy-scroll"></a>

## 木作人文·疏朗工艺长页

风格标签：二级：杂志编辑风 / 人文出版。

适用产物：社媒长图、品牌工艺长图；粒度：连续章节。可用于当代东方木作叙事，但不因题材是木材就限定为新中式风。原参考左右两条的顺序未知，本方案重组主标题、跨段雕刻、工艺图组、偏置短文、竖题静物和枯木收尾；不包含外展示板或原两条重复枯木切片的精确接续。

```json
{"dependencies":["layout.offset-rhythm","layout.subject-band-bridge"]}
```

运行先读取[偏置正文组](../layouts/asymmetric-balance.md#layout.offset-rhythm)、[跨段主体图带](../layouts/continuous-flow.md#layout.subject-band-bridge)、[共用纹理层](../surfaces/materials.md#surfaces.texture-field)的CSS。纸感覆盖参考[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)，本例改绑细纸纤维素材paper-texture，grain=.58、texture-size=560px、multiply；paper-fiber.svg只作为轻量替代，不能视为已匹配同等纸感，按[资源内嵌约定](../README.md#svg-assets)落地。该示例纸纹是参数化近似，不宣称原纸纤维一致。

| 对象/槽位 | 固定关系 | 可调值与边界 |
|---|---|---|
| 页面纸底 | 一个共同父层覆盖全部章节；正文与影像在其上 | tint=#f5f2e9、ink=#302920；纹理不逐段复制、不覆盖照片、不对文字设opacity/filter |
| 主标题 | 首屏中轴，跨全部列；中文竖排，英文横排 | 600px试排中文76px/700、英文46px/400、章节27px/400；中文标题Songti SC Bold、英文Didot、正文Songti SC Regular 14px/1.75。原字体名称未知，均为按形态匹配的本地候选 |
| 诗句 | 标题下方左侧短文，与木雕分栏避让 | 宽为主内容区57%；上下诗句不是一整幅场景的拆图片 |
| carving | 必选透明木雕图，右侧五列，跨入照片带 | width按列，height:auto，底端锚定图带顶+60px，不能在过高容器内object-fit到底部变成小摆件。上端与文字逐例避让 |
| craft-strip | 必选独立横照片带，满宽145px高 | 与透明木雕重叠但保持独立节点；工具/材料接触点置中部净空，右侧仅允许遮挡非关键背景；本例复用process-one图 |
| process-one/two/three | 三张真实工艺影像，三列等宽20px间隔 | 比例3:4，边线由CSS实现；裁切保护工具与雕刻细节，不使用带边框截图 |
| reading-groups | 左右接力短文，正文正常流，层间留白 | 单组增长3倍已测试；超长改wide或另分章节，不挤压成微字 |
| still-life | 竖题之后的独立透明静物素材 | 木框/枝条/器皿是摄影对象，并非本组合的UI容器；宽340px，max85%，禁止另加伪木纹 |
| wood-end | 页尾真实枯木出血主体，透明底显露同一纸场 | 末章右下出血；本例宽180%、right=-14%、bottom=-9%，图像等比例。按可见alpha轮廓核对右/底裁切，不是仅图片框width100%。下方不再留页脚。换图须重算，不套用这些固定数值 |

本案例采用独立素材方案，有干净alpha才启用。已烘焙木雕的满版场景应整体承载，不强制拆图；该替代方案未在本次验证，不与独立雕刻同时叠加。

### 验证与校准

初稿实渲染发现：标题被左栏限制，木雕在高容器内缩小后落到图带下方，跨段关系失败。已回写校准：标题跨整行，诗句留左侧净空；木雕按自然宽高比，锚定图带交界。600/420px×默认/三倍正文共4种检查通过，纸底始终一个。原子默认未被修改，校准仅属于本组合。

本地实际图像对照通过本声明范围：留白、横图带、右侧雕刻跨段、三图组、偏置说明、竖题静物与枯木收尾。绘画/照片具体形态、宋体细节及木料颜色与参考不同，非像素复刻。API复核请求返回429，未取得API验收结论。主标题大幅增长、换宽横木雕或不透明静物，须另检净空；不能把这4种测试扩称任意内容均适配。


### 字体匹配修订

原图主标题“手藝”的简繁结构、宋体笔画反差，与英文展示体应分开匹配；旧版英文沿用中文字体、正文用平方，属于选型偏差而非加载失败。使用同文案对照宋体SC常规/粗体、TC常规、Didot与Baskerville后，选Songti SC Bold承载中文主标题，Didot Regular承载英文，Songti SC Regular承载正文与短题。标题恢复“手藝”仅为该参考实例，不强制其他文案转繁体。英文从29px校准为46px，以恢复较宽的展示比例；不同文案长度另行试排。微字允许保持较小但不可因参考低清而缩成不可读字。

这是一组更贴近的替代字体，不认定是原设计字体。中文主标题笔势与原图仍有差异。真实face应分别确认STSongti-SC-Bold、Didot、STSongti-SC-Regular；不能把字体成功加载作为参考相似度结论。字体测试仅覆盖字形。后续纹理及出血校准见下节，不将任何单项检查扩大为原图逐像素复刻。


### 纸感、局部木纹与末章出血

paper-texture为细纸纤维扫描/生成素材，在唯一共底层按560px重复，强度.58为本例淡色素材的起点；替换纹理先核颗粒尺度、接缝和正文对比。不是把旧弱噪点直接放大。woodgrain是首屏独立浅木纹槽，覆盖上段630px，以multiply/.52显示细年轮曲线，不覆盖工艺照片或全页。纹理可见但不染暗正文；两者不能合成一张必须随文案切割的背景。

末章将短文与wood-end置于wcv-ending同一父层，纸底从正文连续延至木料。文字在上方净空，木料在右下出血裁切，不把完整轮廓居中摆放。本例padding-bottom=780px、裁切场高780px，木料宽180%、右移14%、下移9%，等比例而非拉伸；参数只适配本例透明素材。依据可见主体检查，透明留边不算贴边。删去原木料之后的页脚，必要署名移到木料前净空，不把纸带加回画面底部。

本地实渲染对照检查：600/420px×默认/三倍末章首段，共4种通过。主体图像包围框始终在文字下方，且跨出右/底边，截图确认实际木料轮廓接到两边；纸感在阅读尺寸可见，首屏浅木纹另层保留。具体纹理纤维与木料裂纹不是原素材，不声称精确复刻。换宽高比、主体透明边距或更高浓度纹理时重新校准，不能只检查scrollWidth。

```css
.wcv-page{width:600px;max-width:100%;margin:0 auto;position:relative;isolation:isolate;background:#f5f0e5;color:#302920;font-family:'PingFang SC',Arial,sans-serif}.wcv-page *{box-sizing:border-box}.wcv-paper{position:absolute;inset:0;z-index:0;pointer-events:none}.wcv-paper img{display:block;width:100%;height:100%;object-fit:cover}.wcv-content{position:relative;z-index:1}.wcv-bridge{--sbx-top-min:630px;--sbx-band-height:145px;--sbx-bottom-min:210px;--sbx-inset:36px}.wcv-top{align-self:start;text-align:center;padding-top:74px}.wcv-title{margin:0 auto 22px;writing-mode:vertical-rl;text-orientation:upright;font:400 64px/1.4 'Songti SC',serif;letter-spacing:14px}.wcv-kicker{margin:0 0 20px;font:400 20px/1.7 'Songti SC',serif}.wcv-english{margin:0;font:400 29px/1.3 'Songti SC',serif;letter-spacing:-1px;overflow-wrap:anywhere}.wcv-poem{margin:64px 0 0;font:400 22px/1.8 'Songti SC',serif}.wcv-scene img{position:absolute;inset:0;display:block;width:100%;height:100%;object-fit:cover;object-position:center center}.wcv-band img{display:block;width:100%;height:100%;object-fit:cover}.wcv-subject img{position:absolute;inset:20% 0 0;display:block;width:100%;height:80%;object-fit:contain;object-position:center bottom}.wcv-page[data-scene='continuous'] .wcv-band,.wcv-page[data-scene='continuous'] .wcv-subject{display:none}.wcv-page[data-scene='split'] .wcv-scene{display:none}.wcv-bridge-copy h2{margin:0 0 14px;font:400 27px/1.55 'Songti SC',serif}.wcv-bridge-copy p{margin:0;font-size:14px;line-height:1.9}.wcv-process{padding:64px 36px 24px}.wcv-rule{display:flex;align-items:center;gap:14px;margin:0 0 60px;font:11px/1.6 Arial,'PingFang SC',sans-serif;letter-spacing:1px}.wcv-rule::before,.wcv-rule::after{content:'';height:1px;flex:1;background:#9c8f7a}.wcv-photo-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.wcv-photo{margin:0;min-width:0}.wcv-photo img{display:block;width:100%;aspect-ratio:3/4;object-fit:cover;border:2px solid #76523a;padding:4px;background:#eee5d5}.wcv-photo figcaption{padding-top:12px;font-size:12px;line-height:1.7;text-align:center}.wcv-rhythm{--orx-pad:42px;--orx-inner:16px;padding-bottom:88px}.wcv-rhythm h2{font:400 27px/1.55 'Songti SC',serif}.wcv-rhythm p{font-size:15px;line-height:1.95}.wcv-rhythm small{font:11px/1.7 Arial,'PingFang SC',sans-serif;letter-spacing:1px}.wcv-material{padding:68px 42px 0}.wcv-vertical-group{display:flex;justify-content:flex-end;gap:22px;min-height:330px;padding-right:18px}.wcv-vertical-title{margin:0;writing-mode:vertical-rl;text-orientation:upright;font:400 31px/1.9 'Songti SC',serif;letter-spacing:6px}.wcv-vertical-note{margin:78px 0 0;writing-mode:vertical-rl;text-orientation:upright;font:14px/2 'Songti SC',serif;letter-spacing:3px}.wcv-still{display:block;width:340px;max-width:85%;height:auto;margin:48px auto 80px}.wcv-material-copy{max-width:360px;margin:0 0 0 auto}.wcv-material-copy h2{margin:0 0 22px;font:400 27px/1.5 'Songti SC',serif}.wcv-material-copy p{margin:0 0 22px;font-size:15px;line-height:1.95}.wcv-end{display:block;width:100%;height:auto;margin-top:100px}.wcv-footer{padding:30px 42px 54px;font-size:11px;line-height:1.8;letter-spacing:1px}
.wcv-page{--vl-tint:#f5f0e5;--vl-texture:url("asset:svg/paper-fiber.svg");--vl-grain:.13;--vl-texture-size:256px;--vl-texture-blend:multiply}
.wcv-top{grid-column:1/-1}.wcv-poem{max-width:57%;margin:64px 0 0;text-align:center}.wcv-subject{grid-column:8/-1}.wcv-subject img{inset:auto;top:auto;bottom:calc(100% - var(--sbx-top-min) - 60px);left:0;width:100%;height:auto;object-fit:contain;object-position:center}.wcv-page{--vl-tint:#f4f1e8;--vl-grain:.08;background:#f4f1e8}

.wcv-page{font-family:'Songti SC',serif}.wcv-title{font:700 76px/1.35 'Songti SC',serif;letter-spacing:12px}.wcv-english{font:400 46px/1.15 Didot,serif;letter-spacing:-.6px}.wcv-rhythm p,.wcv-material-copy p,.wcv-bridge-copy p{font:400 14px/1.75 'Songti SC',serif}.wcv-rule,.wcv-rhythm small,.wcv-footer{font-family:Didot,'Songti SC',serif}

.wcv-page{--vl-texture:url("SLOT:paper-texture");--vl-grain:.58;--vl-texture-size:560px;--vl-tint:#f5f2e9;background:#f5f2e9}.wcv-grain{position:absolute;inset:0 0 auto;height:var(--sbx-top-min);z-index:0;background:url("SLOT:woodgrain") center/100% 100% no-repeat;opacity:.52;mix-blend-mode:multiply;pointer-events:none}.wcv-ending{position:relative;isolation:isolate;min-height:980px;margin-inline:-42px;padding:20px 42px 780px;box-sizing:border-box}.wcv-ending .wcv-material-copy{position:relative;z-index:2;max-width:360px;margin:0 auto}.wcv-wood-bleed{position:absolute;right:0;bottom:0;width:100%;height:780px;overflow:hidden;pointer-events:none;z-index:1}.wcv-wood-bleed .wcv-end{position:absolute;right:-14%;bottom:-9%;width:180%;height:auto;max-width:none;margin:0}

```

```html
<article class="wcv-page vl-texture-field" data-scene="split"><span class="vl-texture-field__texture" aria-hidden="true"></span><div class="wcv-content"><section class="sbx-bridge wcv-bridge"><div class="wcv-grain" aria-hidden="true"></div><header class="sbx-top wcv-top"><h1 class="wcv-title">手藝</h1><p class="wcv-kicker">万木有灵 · 循纹而作</p><p class="wcv-english">WOODCARVING</p><p class="wcv-poem">以匠人之心<br>候万千木来<br>以匠人之思<br>展木理之美</p></header><div class="sbx-band wcv-band"><img data-slot="craft-strip" src="SLOT:process-one" alt="手持工具修整木材的工艺近景"></div><div class="sbx-subject wcv-subject"><img data-slot="carving" src="SLOT:carving" alt="枝叶舒展的浅色树形木雕"></div><section class="sbx-bottom wcv-bridge-copy"><h2>循迹<br>手工木作</h2><p>从材料的纹理出发，在取舍之间寻找形态，让细节回应手掌与目光。</p></section></section><section class="wcv-process"><p class="wcv-rule">观察材料 · 留意细节</p><div class="wcv-photo-row"><figure class="wcv-photo"><img data-slot="process-one" src="SLOT:process-one" alt="手工修整木雕表面"><figcaption>一 · 修整轮廓</figcaption></figure><figure class="wcv-photo"><img data-slot="process-two" src="SLOT:process-two" alt="工具沿木材表面加工"><figcaption>二 · 顺纹落刀</figcaption></figure><figure class="wcv-photo"><img data-slot="process-three" src="SLOT:process-three" alt="雕刻枝叶的局部细节"><figcaption>三 · 收束细节</figcaption></figure></div></section><div class="orx-flow wcv-rhythm"><section class="orx-group"><small>材料札记</small><h2>万木有灵</h2><p>木材的纹理并不重复。深浅之间，是生长留下的方向；疏密之间，是时间沉淀的痕迹。开始动手之前，先花一些时间看清它。</p></section><section class="orx-group orx-group--right orx-group--quiet"><h2>让材料说话</h2><p>有些弧度适合保留，有些边缘需要收束。制作不是把所有痕迹磨平，而是在坚实与轻盈之间，找到可以停下来的位置。</p><p>从较大的轮廓开始，再回到细小的转折。手掌接触的地方、目光停留的地方，都需要不同的耐心。</p></section><section class="orx-group orx-group--quiet"><h2>在细节里相遇</h2><p>一件物品完成之后，仍会继续与环境发生关系。窗边的光、室内的湿度、日常的触摸，让原本安静的纹理慢慢显露。</p></section></div><section class="wcv-material"><div class="wcv-vertical-group"><h2 class="wcv-vertical-title">木里有山川</h2><p class="wcv-vertical-note">循其纹理<br>留其本色</p></div><img data-slot="still-life" src="SLOT:still-life" class="wcv-still" alt="细枝、木框与木质器物构成的静物"><section class="wcv-ending"><div class="wcv-material-copy"><h2>把时间留在木中</h2><p>从一段自然形成的曲线，到一处保留下来的裂隙，材料的经历不必被隐藏。它们可以成为形态的一部分，也可以成为观看的入口。</p><p>不急于填满空间，也不急于给出解释。让器物与一束光、一面墙、一本书相处，在平常的日子里，慢慢呈现自己的样子。</p></div><div class="wcv-wood-bleed"><img data-slot="wood-end" src="SLOT:wood-end" class="wcv-end" alt="深色枯木表面的裂纹与起伏"></div></section></section></div></article>
```

SLOT值绑定本次真实资产；本次craft-strip和process-one共用同一工艺图，不需要重复生产。正式交付按目标组装协议展开样式与内嵌纹理资源。

<a id="combination.resume-01"></a>

## 蓝白身份双栏简历

风格标签：二级：理性信息风 / 极简理性；二级：杂志编辑风 / 人物专题。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1129px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

暖灰白底整页，无独立白卡和投影。左栏约占页面宽度39%，右栏约43%，中间留明显通气带。左上以两行大写职业名建立最大视觉锚点，下接中文姓名与英文名并排、四行基本信息；中段是三组蓝色月桂式业绩标记，一组居上、两组居下。细黑斜箭头由左栏中部右侧朝左下伸展，指向靠近页底的竖幅照片。照片为独立矩形图窗，不是背景也不是人物抠像。右栏从About Me到Work、Awards、Skills顺次排列，四组标题均用空心圆起笔，英文在左、中文小标题在右，下方细线横贯右栏。Work为三条高密度经历，Awards为三条较紧凑记录；Skills在底部与照片底边近乎对齐，六枚软件图标横排。

形状与载体：四个空心圆约直径26px、1.5px蓝色边线，与英文模块标题共基线；右栏分隔线约341px长、1.4px深色线。左栏为无边框竖向照片。箭头为约232px横跨、193px纵跨的细黑斜线，末端两条不对称回钩，不使用三角箭头。业绩标记两侧由细枝与小叶片组成的开口月桂轮廓，以简短SVG绘制，无奖牌底板、贴纸、卡片或色块。

### 配色与质感

页面背景约#F5F4F0，主要蓝色约#3063AB，用于职业名、姓名、圆形标题起笔、英文标题、经历名称、年份及业绩标记。正文为#656460，中文模块说明及横线近#171717。照片中的海蓝与版面蓝呼应，但照片颜色属于素材，不另以渐变模拟。软件图标保留自身综合色彩。

```json
{
  "palette": {
    "background": "#F5F4F0",
    "text": "#656460",
    "primary": "#3063AB",
    "secondary": "#171717"
  }
}
```

纹理：源图背景接近均匀暖灰纸色，没有明确需要复现的颗粒纹理；采用纯色背景，不在照片、图标或文字上叠加噪点。

渐变／光场：版面、标题、线条和照片框均无渐变。真实软件图标含原有高光与局部渐变，交给独立素材槽位，不以整条截图替代布局。

### 字体组合

原图职业名是轻至常规粗细的窄感无衬线大写，非重黑体，VISUAL与DESIGNER两行紧排。选Helvetica Neue 400，59px并微收字距，保持近似字面宽；英文模块标题选Helvetica Neue 400、34px。中文姓名选PingFang SC 400，正文选PingFang SC 400；经历名称使用其真实600字重而不伪造700。数字日期用Arial 700，正文英文和联系方式用Arial 400。原图正文尺寸小且密集，复制时以11px及15px左右行高建立相同密度；个别原中文字可能更接近普通黑体，PingFang的转角略柔。全页font-synthesis:none，不使用合成粗斜体。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 两行职业大标题 | Resume01 Helvetica Light | 300 | 59/62/0.3px | 通过局部字体别名绑定本机HelveticaNeue-Light真实字款，减轻笔画并略放松字距；不横向缩放。 |
| 英文模块标题 | Resume01 Helvetica Light | 300 | 34/40/0px | 使用Helvetica Neue真实Light字款，保留现有字号、圆圈和标题锚点。 |
| 中文姓名 | PingFang SC | 400 | 34/43/0px | 保持现有中文姓名字形；原规则未使用Didot，无需改为Bodoni。 |
| 英文姓名 | Arial | 400 | 26/34/0px | 保留现有姓名并排关系和真实常规字重。 |
| 业绩数字 | Arial | 400 | 16/18/0px | 中文字符由PingFang SC回退，保留原有数字尺寸。 |
| 业绩说明 | Resume01 Helvetica Regular, PingFang SC | 400 | 14/18/0px | 拉丁字符使用Helvetica Neue真实400，中文使用PingFang SC常规字款。 |
| 基本信息 | Resume01 Helvetica Regular, PingFang SC | 400 | 14/22.5/-0.2px | 继承修订后的正文默认字体，不使用FuturaMedium。 |
| 电话与邮箱 | Arial | 400 | 14/22.5/0px | 保留联系方式原有独立字体规则。 |
| 中文模块副标题 | Resume01 Helvetica Regular, PingFang SC | 400 | 14/22/0px | 中文实际使用PingFang SC常规字款，维持原有字号层级。 |
| 经历与奖项名称 | PingFang SC | 600 | 15.5/23/0px | 显式保留真实600字款，避免正文默认字体调整影响蓝色名称。 |
| 年份 | Arial | 700 | 15.5/23/0px | 保持Arial真实700字重。 |
| 职位 | PingFang SC | 600 | 11/16/0px | 显式保留真实600字重，不合成加粗。 |
| 关于我、经历及奖项正文 | Resume01 Helvetica Regular, PingFang SC | 400 | 11/15.2/0px | 局部别名绑定HelveticaNeue真实400字款；中文回退PingFang SC 400，正文宽度、字号及行高不变。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①页面内容安全区左50px/0.0625W、右58px/0.0725W、上55px/0.0487H、下59px/0.0523H；细线和图标均不越界。②双栏隔离区位于x=356—398px，宽42px/0.0525W；左栏正文最大宽306px/0.3825W，右栏有效宽342px/0.4275W，标题中文端与英文端最小间隔10px/0.0125W，避免姓名或长标题侵入右栏。③图文与素材安全区：照片x≈58.8px、y≈747.5px、w≈231.4px、h≈321.8px，归一化约[0.0734,0.6621,0.2893,0.2850]；斜箭头端点与照片顶部至少23px/0.0204H；技能图标顶缘与横线至少16px/0.0142H，正文与其上方横线至少13px/0.0115H。长姓名允许英文名换到下一行，不缩字；超长经历或中英替换通过自然行高撑开条目并下推后续模块，页面增高，不裁切、不隐藏。默认示例锁定源图比例；增高版本同步保持照片在左栏底部的锚定关系。

默认固定800px宽，以1129px最小高度对应885×1249源图；正文保持源图小字号和紧密行距，示例为完整虚构履历。照片、枝叶、箭头及技能条均独立于正文，禁止把原图整页或文字区作为背景。中英替换时保持左栏306px、右栏342px和42px隔离带；英文职业名继续以两行显示，超长职业名允许增加一行并下推个人信息。中文姓名超过四字或英文名过长时在姓名容器内换行；联系方式可按邮箱分隔符自然换行，不降低字号。经历及奖项条目用内容驱动高度，较长内容会推动后续模块并增加整页高度，左栏弹性空段相应拉长，使箭头仍接近照片且照片继续与右栏底部对齐。需要严格1129px导出时，应编辑文案回到示例字数和行数，而非隐藏溢出或机械缩字。字体仅引用允许的本机字体；在配有Helvetica Neue、PingFang SC和Arial的环境排版，无外部字体请求。生产时使用有权使用的高质量素材分别填充对应槽位，照片按既定竖幅比例保留完整选区；替换技能图标推荐透明底，避免暖灰底上的白色矩形边缘。

### 素材槽位

portrait仅覆盖左下矩形照片，裁片不含旁边箭头或履历文字，可用同构图普通竖幅人像替换，不需要透明抠像。六枚软件应用标志各设独立槽位，裁切紧贴标志外缘，包含必要阴影；不把整个技能条或技能标题作为素材。圆圈、横线、斜箭头和业绩枝叶均由HTML/CSS/SVG绘制。所有槽位为空div，库模板不嵌入原始图片；技能图标内字母属于原生图标资产，不另录为履历文本。

- `portrait`：左下海边竖幅人物照片；普通矩形竖幅照片，宽高比约0.719；正面微笑半身人物，头发上方保留少量天空，肩部和上衣在底边截断，蓝色户外背景；无需透明抠像。
- `skill-ps`：技能区第一枚青蓝描边应用标志；独立应用图标或自有同尺寸青蓝标志，优先透明底；不得带技能标题或邻近图标。
- `skill-ai`：技能区第二枚橙色描边应用标志；独立橙色系应用图标，保持近方形及原有细描边。
- `skill-ae`：技能区第三枚紫色描边应用标志；独立紫色系应用图标，透明底，视觉尺寸与前两枚一致。
- `skill-pr`：技能区第四枚深靛方形应用标志；独立深色应用图标，不将原图相邻文字纳入裁片。
- `skill-3d`：技能区第五枚银蓝球形应用标志；带银色球壳高光的独立三维软件图标，透明底，保留原生阴影与球形轮廓。
- `skill-slides`：技能区第六枚橙红演示软件标志；独立橙红演示工具图标，保留前后板片层次，不裁入页面横线。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[非对称身份侧栏](../layouts/asymmetric-balance.md#layout.identity-sidebar)、[圆标双语章节标题](../layouts/layout-and-type.md#layout.bilingual-section-title)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)。

整页结构与几何样式唯一维护在 [信息双栏 · 左疏右密](../layouts/resume-full-page.md#layout.resume-profile-left)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-profile-left"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1129,
    "palette": {
      "background": "#F5F4F0",
      "text": "#656460",
      "primary": "#3063AB",
      "secondary": "#171717"
    }
  }
}
```

校准边界：仅修改现有作用域规则，新增两个仅用于本模板的本机真实字款映射，不重复添加全局字体声明。职业名及英文模块标题改用真实Light字重，职业名字距由-0.5px放松至0.3px。三条虚构经历各补约一行职责说明，恢复接近四行的正文密度，不增加条目间距。姓名未使用Didot，保持不动。双栏、照片与六枚图标槽位、月桂、箭头、文字内容结构及底部对齐机制均保留；需运行环境安装对应本机字款。

<a id="combination.resume-02"></a>

## 黑蓝人物侧栏与竖排导航简历

风格标签：二级：杂志编辑风 / 人物专题。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1129px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

画面不是等宽双栏：左侧履历底板占64.65%，右侧肖像和信息塔占35.35%。左侧内部又分为约160px宽的竖排导视轨与约356px宽的正文区域，正文实际从x=194px起，右端留到x=467px。右侧从x=517px开始，顶部照片直接贴顶、贴右，照片底边约y=334px；其下为连续黑色姓名与技能区，延伸到y=890px；底部为通至画布底边的钴蓝联系方式区。左侧顶部为浅灰底，y=614px以下转为稍深灰底；另有一块从左边缘至x=160px、y=448—759px的中灰矩形，跨越教育和经历两个部分，且在竖排文字与细线后方。左上蓝色圆章位于x=46px、y=69px附近。About Me与圆章横向对应。Education和Experience为整词逆时针旋转90度，不是逐字竖排；两段细竖线在词后向下延伸。三段教育与四段工作经历具有紧凑但清晰的固定节奏，没有卡片、圆角或独立框线。

形状与载体：主要几何包括一个约90px直径蓝色圆章、三种左侧灰色矩形底板、右侧黑蓝两块贯通矩形、两根1.5px黑色竖线，以及六根不同长度的白色技能横条。技能条只有白色有效长度，没有灰色轨道。照片是无边框的顶端矩形窗。中灰矩形不跟随正文分节边界，故必须作为独立背景层，而不是教育卡片背景。竖排导视与背景矩形存在明确叠压关系。

### 配色与质感

浅灰主底近似#EFEFED；左下履历底近似#DADAD8；跨区导视块近似#B2B3AF。右侧姓名技能底为#000000，照片为黑白。圆章及底部联系方式使用较饱和的深钴蓝#09499D，正文小标题使用更沉稳的#104B86。正文为近黑#111210；黑底次级标签为#B9B9B6；白色姓名和技能进度条形成最强明度反差。

```json
{
  "palette": {
    "background": "#EFEFED",
    "text": "#111210",
    "primary": "#09499D",
    "secondary": "#DADAD8"
  }
}
```

纹理：原图平面底色近乎无可见纹理，采用纯CSS平涂，不添加噪点、纸纹或颗粒。肖像内部的胶片感、玻璃和建筑细节由照片资产负责，不在照片或文字上叠加纹理。

渐变／光场：无。蓝色、黑色、浅灰和中灰均采用实色，不添加渐变或投影。

### 字体组合

原图姓名是高笔画反差、紧凑宽度的Didone衬线粗体，两行左对齐，白字在黑底上具有杂志封面气质。采用Didot 700而非普通无衬线或伪粗体，替换姓名使用Alex Morgan并维持两行。圆章内cv同样采用Didot 700。其余原文字体近似几何无衬线：小写a与圆形字腔较明显，标题较粗，正文细而疏朗。正文选本机Futura medium，真实weight 500；小节标题与竖轴选Arial 700，承认其双层a、字腔与原图有差异，不对Futura合成粗体。正文约12px、行高17px，部分段落两端对齐，末行自然收尾。竖轴约35px，姓名约59px，职业标签约16px并带3px字距。全部字体关闭font-synthesis。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名 | Resume02 Bodoni72 Bold | 700 | 59/68/-2px | 通过local绑定Bodoni 72实际Bold字面，增强Didone粗细反差；保留两行、原字号与位置，不使用合成粗体。 |
| 圆章字母 | Resume02 Bodoni72 Bold | 700 | 45/45/-2px | 使用同一真实粗衬线字面，避免未确认的Didot回退；保留cv文字与圆章尺寸。 |
| 竖向导视 | Arial | 700 | 35/42/1px | 保持字号、旋转方式及下端锚点，仅增加字距以恢复整词向上的跨度。 |
| 教育与经历标题 | Arial | 700 | 16.5/19/0 | 保留真实700字重、蓝色双行标题及原行距。 |
| 正文 | Resume02 Helvetica Neue | 400 | 12/17/0.12px | 通过local绑定Helvetica Neue Regular真实400字款，替换偏厚的Futura Medium；保留字号、行高和编辑换行。 |
| 一般小节标题 | Arial | 700 | 16.5/20/0 | 保持原有标题规则；Contact继续使用0.2px字距。 |
| 职业标签 | Resume02 Helvetica Neue | 400 | 16/22/3px | 使用真实Regular字面，恢复细字与宽字距的层级，保留浅灰色和位置。 |
| 技能标签 | Resume02 Helvetica Neue | 400 | 11/17.5/0 | 继承修订后的正文实际400字款，保留标签网格及技能条。 |
| 联系方式 | Resume02 Helvetica Neue | 400 | 11/17/0 | 继承修订后的正文实际400字款，保留原行距、颜色和联系区布局。 |
| 中文正文备用 | "PingFang SC","Source Han Sans SC",Arial,sans-serif | 400 | 12/17/0.12px | 保留既有lang=zh规则，仅中文内容启用。 |
| 中文姓名备用 | "Source Han Sans SC","PingFang SC",sans-serif | 700 | 52/62.4/0 | 保留既有中文姓名规则。 |
| 中文标题备用 | "Source Han Sans SC","PingFang SC",sans-serif | 700 | 16.5/小节20px；条目19px；竖向导视42px/继承对应标题规则 | 保留既有中文标题字体规则；竖向导视仍使用35px字号。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布文字安全区：非出血文字距离左边至少46px（0.0575W），右边至少37px（0.0463W），顶部至少69px（0.0611H），底部至少44px（0.0390H）；照片和背景允许贴边出血。②分栏安全区：正文起点x=194px（0.2425W），宽273px（0.3413W），到右栏边界517px保留50px（0.0625W）；右栏文字起点555px（0.6938W），右侧保留37px（0.0463W），可用208px（0.2600W）。③资产与字形安全区：照片下方到姓名可见字顶约39px（0.0345H）；姓名末行与职业标签保留约24px（0.0213H）；轨道中灰块右缘160px与正文起点间保留34px（0.0425W）；技能标签栏与白条栏之间保留12px（0.015W）。长姓名按姓名组成部分换行，单个超长词允许自然断行，不缩小字号或裁切；右栏黑色区随内容增长，联系区下移。长正文保持原字号与行高，通过网格固有高度增加段落和页面高度，导视轨道保持独立，不把超出内容藏在固定高度内。

标准输出固定800px宽、最小1129px高，忠实对应812:1146源图比例；默认示例保留五行简介、三条双行教育标题和四条双行工作标题，各说明约三行。HTML中的br是本示例的编辑换行点，替换文案时应按词义重新设置或移除，不能强行沿用造成孤词。正文仍使用12px/17px，教育与经历标题仍使用16.5px/19px，超长内容通过minmax网格增长左侧段落和页面，右栏底部联系区吸收合理高度差；若右栏姓名或联系方式更长，则黑色区及蓝色区按内容扩展。英文姓名推荐两个span分成两行，单词较长允许断行，不缩放字体、不隐藏。换成林予安时可分为林与予安两行，显式标记lang="zh"，采用真实可用的Source Han Sans SC 700姓名字重，正文用PingFang SC 400；中文说明按原行数和行宽填充，不做英文字符数等量替换。保持517:283主分栏、160px导视轨、34px轨道至正文间隔以及右侧38px内边距，禁止改成通用均分双栏。照片槽位不含原图位图，宿主负责提供归一化裁切素材；移动设备可由外层容器横向浏览固定800px画布，不使用脚本或外部资源。

### 素材槽位

仅肖像需要素材槽位。裁切限定右上独立黑白照片，保留人物及其建筑背景，不包括下方姓名、左侧履历文字或蓝色联系方式。人物不是透明抠像，不要求透明背景。替换照片应为竖幅黑白半身照，人物居中，头发距顶部约20px，肩部接近照片两侧，胸腹自然被照片底部截断；不能用CSS人物图形替代。圆章、导视线、色块和技能条均由CSS实现，不进入资产槽位。

- `portrait`：右上角黑白半身人物照片，包含照片自身建筑背景，不包含任何履历文字。；使用约283:333比例的黑白竖幅半身照片，人物正面居中、发顶留约6%高度、肩部接近两侧，下缘裁至胸腹；无需透明抠像。宿主按该独立照片区域裁取并填满槽位。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[非对称身份侧栏](../layouts/asymmetric-balance.md#layout.identity-sidebar)、[竖排栏目导轨](../layouts/asymmetric-balance.md#layout.vertical-section-rail)、[对齐标签量尺：平条、框条与圆点](../layouts/grid-and-alignment.md#layout.labeled-meter)、[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)。

整页结构与几何样式唯一维护在 [主次双栏 · 竖标题](../layouts/resume-full-page.md#layout.resume-section-rail)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-section-rail"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1129,
    "palette": {
      "background": "#EFEFED",
      "text": "#111210",
      "primary": "#09499D",
      "secondary": "#DADAD8"
    }
  }
}
```

校准边界：仅修改实际字体与导视字距规则，不追加重复全局字体覆盖。新增两个局部字体别名，分别绑定Helvetica Neue Regular和Bodoni 72 Bold真实本机字面；正文、技能及联系方式不再默认使用Futura Medium。姓名与圆章使用真实粗衬线，竖排标题保持下端锚点并向上延长。保留文案、换行、分栏、背景、技能条及portrait图像槽位。local字体需宿主实际安装；应在渲染字体面板确认HelveticaNeue与BodoniSvtyTwoITCTT-Bold命中，不能以声明名称代替加载验证。

<a id="combination.resume-03"></a>

## 绿橙跨区人物编辑简历

风格标签：二级：杂志编辑风 / 人物专题。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1128px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

原图是奶油底单页，顶端为小型品牌与导航；主视觉左侧为两行大衬线问候及短介绍，右侧为上伸的人物抠像、森林绿矩形图窗、米白圆盘、两枚橙黄色信息胶囊与下接的黑色联系卡。中段森林绿背景从画布左边贯穿到右边，不是局部卡片，约从y=421px到807px；它承载左上教育、右上描边RESUME装饰以及右侧技能。左侧黄色经历卡从y=642px延伸到940px，穿越绿底与下方奶油底，前景关系明确。底部左侧活动，右侧语言与爱好。黄色经历卡比其上教育区左扩约44px，右侧内容列与人像卡不共用同一左边界，不能改成普通等宽双栏。

形状与载体：顶部与时间线采用四尖朱橙星；联系按钮为朱橙长胶囊且内置CSS放大镜。出生与国籍为黄色胶囊，分别压在人像左侧和右侧；右侧胶囊越过人像窗右边界。人像背后是完整米白圆盘，部分被身体遮住。中段两行空心RESUME从联系卡后方露出，字顶约y=380px，跨越奶油与绿底边界。经历卡为无圆角矩形，时间线为细竖线加米白星。技能标识为两排米白小方块，底部技能标签为黑胶囊。爱好区为四个黄色概念图标及两行小字。

### 配色与质感

奶油纸底近似#F4ECDD，承担页首、页尾与人像圆盘；森林绿#324B36用于中段通栏与人像底窗；橙黄#FFB20C用于经历卡、胶囊、技能标题与爱好图形；朱橙#FF5A32用于联系按钮与四角星；黑色#080906用于主标题及联系卡。绿底说明文字为低对比浅灰绿#D4D9C9，正文不是纯白。描边RESUME为低饱和金色细线。

```json
{
  "palette": {
    "background": "#F4ECDD",
    "text": "#080906",
    "primary": "#324B36",
    "secondary": "#FFB20C"
  }
}
```

纹理：原图底色呈轻微纸感，主要来自低对比暖色底。复现只在底层以SVG feTurbulence生成极弱单色纸纹，opacity=0.025，位于所有文字、色块和照片之后；人像、黑卡、绿色条带、黄色卡不叠加噪点，避免将整页做成颗粒滤镜。

渐变／光场：无明显渐变。奶油、森林绿、黄色、朱橙、黑色均使用实色；人像的自然光影属于照片资产，不由CSS渐变伪造。

### 字体组合

原图大标题与栏目标题是笔画对比极强、字腹饱满、略带复古展示感的衬线字；用实际400/700字重的Bodoni 72替代，不使用合成加粗。原图正文为小字号几何无衬线，圆形字腹、较宽字面，用Futura medium近似；正文Futura 500与标题Bodoni 72 700分别声明，缺字回退Arial或PingFang SC。年份用Bodoni 72 700，有明显衬线且视觉比旁侧单位名更粗。RESUME采用Didot 400细线描边；与原图狭长展示字相比仍稍宽，以固定装饰框与正常字距控制，不将正文压缩。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 主视觉标题 | Bodoni72Bold | 700 | 64/70/-2px | 优先使用Bodoni 72真实Bold字面，保留两行准确文字；不合成加粗或横向压缩。相较参考，字形仍更端正、端点较少卷曲。 |
| 分区标题 | Bodoni72Bold | 700 | 32/36/-0.8px | 采用真实Bold字面；联系卡标题保持31px，爱好标题保持原有字距微调。 |
| 页首品牌姓名 | Bodoni72Bold | 700 | 18/22/-0.6px | 与主标题统一使用真实Bodoni Bold，不以细Didot回退承担粗体姓名。 |
| 正文及常规导航 | Helvetica Neue | 400 | 11.5/13.5/0px | 以真实Regular替换Futura Medium正文默认；保留各模块原有10–12.5px字号和行高，不通过缩字减轻视觉重量。相较参考几何字体，字面更中性。 |
| 教育机构名称 | Helvetica Neue | 400 | 12.5/15/0.03px | 移除局部Futura 500覆盖，继承正文真实Regular，以字号区别于说明文字。 |
| 年份及小分组标题 | Bodoni72Bold | 700 | 18/21/-0.25px | 年份保持-0.3px字距，技能小标题保持24px行高；语言名保持17px字号，均使用真实Bold。 |
| 岗位、活动名称及强调导航 | Arial | 700 | 12/14/0px | 保留实际Arial Bold强调，与减轻后的正文重新形成粗细层级；导航与软件标识保留各自原字号。 |
| 背景空心字 | Didot | 400 | 72/66/-4.5px | 保留真实Didot常规体及0.55px细描边，维持现有三行RESUME准确文字与叠压位置。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布裁切安全：非装饰内容左右至少20px，即宽度的0.025；顶边22px，即高度的0.0195；底部主要文字距底至少42px，即0.0372，只有通栏背景允许贴边。②文字内边距安全：主正文左边界94px即0.1175W，右列432px即0.54W；黄色卡左内边距44px即0.055W、右内边距20px即0.025W，文字可用宽273px；黑卡左右内边距43/18px即0.05375W/0.0225W，最小行高15px即0.0133H。③叠压安全：人像位于x=500–641px即0.625–0.80125W、y=92–360px即0.0816–0.3191H；出生标签为x=419–571px、y=231–270px，国籍标签为x=608–724px、y=304–343px，必须维持标签在人物之前、联系卡在人物之前；人物槽下沿与黑卡上沿无缝衔接。姓名若超过Alex Morgan长度，应增加标题行而非缩小字体；长介绍、长岗位和中英混排需增加对应区块高度，并同步下移绿带起点、经历卡和底部内容，画布随之增高，不能裁字或用overflow:hidden隐藏正文。

默认严格800×1128，保留源图658:928比例的整数近似；只做预览缩放时可由宿主对整个main等比缩放，不单独缩字或更改栏宽。英文姓名完整形式显示于左上品牌，主视觉使用同一虚构人物的名字Alex，维持源稿两行构图；中文版本可改为“你好，/我是林予安！”并使用PingFang SC 600，不能让Bodoni伪造中文字形。中英文正文分别采用Futura 500与PingFang SC 400，中文粗体使用PingFang SC 600，避免不存在的500/700合成。当前内容以相近字数和行数填满所有原稿区块；长姓名需移除标题span的white-space:nowrap并允许新增一行，新增高度同步传递给绿带、教育、经历、技能和底部定位值。介绍使用五行参考排法，替换时可以去掉br自然换行；岗位、教育、活动网格均用minmax(0,1fr)，长句正常换行，增加timeline-row的min-height，经历卡保持min-height并随内容增长，再同步下移活动及页底，最终增加main高度。不得以隐藏溢出、强制省略号或机械缩小正文维持旧高度。换人物时保持141×268px的人物视觉量级，眼部约在y=159px、头顶约92px，绿色窗与圆盘位置不跟随裁片矩形移动；透明抠像替换时应撤销验证用分段clip-path。所有联系信息均为example.com及占位号，人物资产槽不承载原图文字、水印或新的文案。

### 素材槽位

仅人物建立portrait资产槽位。原图人像上半部处于奶油背景、下半部压在圆盘与绿窗上，推荐替换为透明PNG/WebP抠像，保留头顶、眼镜、肩背、转头方向与侧身比例。源裁片只覆盖人物紧贴区域，不包含左侧简历段落、右侧国籍标签或下方联系文字；因出生胶囊覆盖人物左边缘，使用分段clip-path排除裁片里原标签残片，再由新的CSS胶囊覆盖同一区域。该裁片仍可能保留贴身米白或绿色背景，仅适用于当前同色验证背景；正式复用必须换透明抠像。所有星形、圆盘、按钮、黑卡、图窗、描边字、时间线和爱好概念图形由HTML/CSS/SVG绘制，不交给照片槽位。

- `portrait`：右上侧身人物，头顶伸出绿色图窗，下方身体接到黑色联系卡；需要朝右看的半身透明抠像，保留发髻、眼镜及深色衣服，人物高约268px。原裁片仅为验证参考，带贴身背景；出生标签所在高度以分段裁切排除原文字后由新胶囊遮挡。透明替换可移除portrait的clip-path并调整object-position，不能改成人物矩形证件照。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[背景分区与跨界内容](../layouts/overlap-and-collage.md#layout.cross-zone-sections)、[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[叠层拼贴](../layouts/overlap-and-collage.md#layout.collage)、[文字描边](../layouts/layout-and-type.md#text.outline)、[圆角容器](../shapes/containers.md#shape.rounded)、[四角星芒](../shapes/organic-shapes.md#shape.sparkle)、[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)。

整页结构与几何样式唯一维护在 [分区双栏 · 跨区交错](../layouts/resume-full-page.md#layout.resume-cross-zone)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-cross-zone"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1128,
    "palette": {
      "background": "#F4ECDD",
      "text": "#080906",
      "primary": "#324B36",
      "secondary": "#FFB20C"
    }
  }
}
```

校准边界：仅修改实际字体、出生标签边界及技能标签换行规则，不新增全局字体定义。正文默认及局部说明统一为Helvetica Neue 400；标题、姓名和年份明确优先使用Bodoni72Bold，继续禁用合成字重，运行环境需提供对应真实字款。出生胶囊提升至人物前方，并将人物验证裁片的上侧矩形缺口改为沿胶囊右上圆弧避让，减少露出的奶油色直角残片；图像槽位、尺寸与定位不变，正式复用仍应换透明抠像。技能标签用显式换行固定为两行各两枚，保留各枚自然宽度与原字号。其他布局、文案事实、色块、装饰及图像槽位均保留。

<a id="combination.resume-04"></a>

## 红色巨字与书写穿插简历

风格标签：二级：都市潮流风 / 字体潮流；二级：杂志编辑风 / 时尚杂志。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1131px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

浅暖灰底铺满整页，无白卡、边框或分栏底色。外侧左右留白约40px。顶部约65px处，一行左置方括号RESUME、右置职业标识。姓名占左上宽约420px的两行区域，红色大写无衬线字上叠一枚红色细线书法式抽象字标；右上肖像是独立的矩形灰阶图窗，约257×279px，顶边111px、右边760px。姓名下方是电话与网站两列小型联系方式，网站保持两行，肖像下沿与联系方式区域交错。正文从约451px起通栏排布简介，随后为双栏技能；工作经历采用左栏职位和时间、右栏对应项目说明的两行配对布局，工作说明第一行高于左侧职位基线。页底证书和教育并置，教育栏比工作说明栏稍向左约13px。全页通过留白而不是横线组织层级。

形状与载体：几何非常克制：仅右上矩形照片和两行大字。姓名装饰为横向小椭圆回环、斜向上挑长环、下垂回转尾线组成的不规则红色曲线；下层同路径背景色粗描边形成遮挡，使装饰跨过两行红字仍可辨识。它不是贴纸或独立色块。列表使用小圆点，纸面没有线框、图钉或撕边。

### 配色与质感

背景接近#EAEAE5，正文为近黑#282927，红色标题与姓名接近#B92028；图窗本身包含中灰背景与灰阶人物。次要文字仍为深灰，不使用大面积浅灰弱化信息。红色只承担姓名、抽象字标和栏目标题的强调作用。

```json
{
  "palette": {
    "background": "#EAEAE5",
    "text": "#282927",
    "primary": "#B92028",
    "secondary": "#555651"
  }
}
```

纹理：原图纸底整体平整，仅有很弱的印刷观感；复现采用纯色背景，不额外叠加噪声，避免在正文或肖像上制造伪纹理。照片的颗粒和明暗属于照片资产自身。

渐变／光场：无CSS渐变。照片背景和面部的连续灰阶由portrait资产提供，不重建为页面渐变。

### 字体组合

原图姓名接近紧凑的粗体新古罗特斯克无衬线，大写、紧字距、两行压排；使用Arial 700与-5.6px字距近似，虚构姓名换成ALEX / MORGAN后每行字数有差别，因此固定字号并保留原有左侧字块宽度，而不拉伸字形。原图正文为较窄的无衬线大写，替代选Arial Narrow 400，栏目与职位选Arial Narrow 700。职业标识中GRAPHIC加粗，DESIGNER常规。装饰字标不是姓名内容，用SVG细曲线重画，避免依赖不可用的花体字形。所有文字font-synthesis:none，使用指定可用的真实400/700字重。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名大标题 | Arial | 700 | 98/96/-5.6px | 两行统一小幅减小字号，保留真实粗体、不横向压缩；MORGAN实际字面回到左侧姓名区，恢复与肖像之间约30px的留白。 |
| 栏目标题 | Arial | 700 | 23/28/-0.35px | 由Arial Narrow改为较宽的Arial真实700字款，减弱瘦高紧缩感，保持标题位置与行高。 |
| 正文与列表 | Arial Narrow | 400 | 17/24/0 | 本次正文问题为偏窄及词距拉伸，并非偏厚；保留原有真实400字款，仅取消简介和工作说明的强制两端拉齐。 |
| 联系方式内容 | Arial Narrow | 400 | 17/21/0 | 保持现有两列联系方式及网站两行结构。 |
| 职位、教育学位与联系标签 | Arial Narrow | 700 | 17/23/0 | 保留真实700字款，不增加正文默认字重。 |
| 页眉职业与简历标记 | Arial Narrow | 400 | 20/24/0 | 保持原有常规字款。 |
| 页眉职业强调 | Arial Narrow | 700 | 20/24/0 | GRAPHIC使用同家族真实700字款。 |
| 中文适配正文 | PingFang SC | 400 | 17/24/0 | 仅在lang-zh模式启用，联系方式行高21px，页眉20px/24px。 |
| 中文适配标题与强调 | PingFang SC | 600 | 23/28/-0.35px | 保留现有中文规则；职位与联系标签17px/23px、字距0，页眉强调20px/24px、字距0。 |
| 中文适配姓名 | Source Han Sans SC | 700 | 98/96/-3px | 沿用现有中文真实700规则，字号随姓名主规则统一修订。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①页面裁切安全区左右40px、顶部62px、底部60px，归一化为左右0.05、顶部0.0548、底部0.0531；装饰与所有文本均在该范围内，姓名字标局部不越出左上姓名区。②文字与图窗安全区：姓名列右界473px、照片左界503.34px，净间隔30.34px，占宽0.0379；联系方式网站右界473px，与照片同样保持约30px；正文双栏间隔24px，占宽0.03。③人物内容安全区：照片图窗256.53×279.64px，建议替换人物关键五官距图窗边缘至少12px，分别占图窗宽0.0468、高0.0429；原图帽子靠近上沿，替换允许帽沿接近顶边，但不得切断眼睛、下巴与托腮手。长姓名保持两行和字重，可在词边界换行，超过两行时启用flow-long自然增高并下推联系方式和正文；长文案自然增高各网格行，不省略、不裁切、不通过整体缩字容纳。

基准画幅固定800px宽、1131px最小高度；默认示例保持原图两行姓名、三行简介、左右各三条技能、两组各三行项目说明以及页底两栏的信息密度。所有内容均为虚构，不使用原图姓名、学校、公司、网址或号码。宿主仅向portrait空槽注入指定裁片，按完整图窗显示，不将照片扩展为页底或姓名背景。替换英文文案时优先维持各段行数；文字变长则为main添加flow-long，使预设行片段恢复自然行流，网格和页面自动增高。姓名按词分两行，超长允许增加行数并把联系方式、正文一起下推，字号不机械缩小。中文替换可使用林予安，为main添加lang-zh，姓名用Source Han Sans SC 700，正文PingFang SC 400、标题600；取消正文英文强制分行，按约每行38至43个汉字重新组织同等信息量。页面底部没有固定定位或overflow:hidden，超出1131px的长履历保持完整显示；打印长内容时应同步调整纸张高度，而不是裁掉页底。

### 素材槽位

唯一资产为右上完整独立肖像图窗，包括人物、贝雷帽、托腮手部和原有灰背景；裁片不包含右侧或下方履历文字。此图不是透明抠像，无需透明底替换。姓名装饰、文字、列表圆点和背景全部使用HTML/CSS/SVG，不能纳入照片槽位。替换需使用近方形竖幅灰阶半身照，保留头顶到胸上部、右侧长发与左下手臂的空间关系。

- `portrait`：右上矩形灰阶托腮肖像，包含帽子、长发、手部与照片自身灰背景。；替换为宽高比约0.917的竖向灰阶半身人像，头部偏上、脸朝镜头、手托下巴，人物占图窗约八成高度；无需透明抠像，不能带边框、水印或履历文字。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[展示字与书写字叠层](../layouts/layout-and-type.md#layout.display-script-overlap)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)。

整页结构与几何样式唯一维护在 [上图下文 · 大字并排](../layouts/resume-full-page.md#layout.resume-name-photo)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-name-photo"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1131,
    "palette": {
      "background": "#EAEAE5",
      "text": "#282927",
      "primary": "#B92028",
      "secondary": "#555651"
    }
  }
}
```

校准边界：仅修改现有规则及装饰SVG：姓名统一由107px调整至98px，不更改姓名、不拉伸字形；栏目标题换为Arial真实粗体；正文保留真实400并取消强制词距拉伸，维持原有行数与模块位置。字标删除重复短弧、减细双色描边，仅作为独立抽象装饰，姓名仍由准确文字呈现。未重复定义全局字体，未引入FuturaMedium或Didot；肖像槽位、背景、网格及文案均保留。

<a id="combination.resume-05"></a>

## 极细字体与窄黑侧栏简历

风格标签：二级：理性信息风 / 极简理性。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1131px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

源图为507×717纵向单页。底色为近白冷灰，不是白色独立卡片。左侧黑色纵柱从约(44,125)延伸至(154,628)，顶部另有与纵柱同宽、贴画布上边的独立黑色CV标牌。姓名位于标牌下方，跨出左柱宽度；两行职业说明紧随其下。照片窗位于(27,112)附近，宽110、高108，向左越过纵柱17px，照片右边在黑柱右边之前约16px结束；照片覆盖纵柱上端，形成前景照片、后景黑柱的明确层级。正文从x≈172开始，顶部工作经历与志愿经历并列；教育经历横跨右侧内容区；技能及末行语言、自述再次分为两列。三条浅灰分隔线仅从正文左边延伸到x≈412，不贯穿页面，也不延伸到最右内容边。下方保留源图已有的留白缓冲，整页底部由约38px高的中灰通栏页脚收束，署名右对齐。

形状与载体：全部几何以直角矩形为主：贴顶黑标牌、长黑侧栏、横向越界照片窗、中灰通栏页脚；无圆角、阴影、胶带、图钉、纸片或曲带。侧栏中有两条短而细的灰分隔线，正文有三条固定宽度但不通栏的横线。六行专业技能与六行个人技能均为水平两段式短矩形条。社交联系方式前保留五个微型浅色图标资产，其大小与正文行高协调，不用emoji代替。

### 配色与质感

页面底色约#F5F5F5，左柱及CV标牌为#030303，正文标题为#171717，细正文主要为#858585，浅色副标题约#A4A4A4。分隔线约#C6C6C6。技能条采用#626262深灰前段与#C1C1C1浅灰余段，避免彩色强调。页脚为#898A8C，页脚文字为#E5E5E5。照片本身的暖棕色只归属于照片素材，不作为页面全局配色。

```json
{
  "palette": {
    "background": "#F5F5F5",
    "text": "#171717",
    "primary": "#030303",
    "secondary": "#898A8C"
  }
}
```

纹理：源图背景整体平整，仅有扫描或压缩带来的极弱细微差异，不将其误当成纸张颗粒。复现采用纯色背景，不给照片或文字叠加噪点；不增加源图没有的泛黄、纤维或屏幕颗粒。

渐变／光场：无。背景、标牌、侧栏、技能条与页脚均为实色；照片内自然明暗仅由照片资产承担。

### 字体组合

姓名是极细、紧凑的大写无衬线，笔画均匀，字宽较常规Arial更窄，原图约23px；采用本机Helvetica Neue 100，在800px画布中设37px，并以轻微负字距保留紧排气质。章节标题为普通字重无衬线，而非粗黑标题，采用Arial 400、18.4px。经历条目的职位与机构保留清晰的常规字重层次，小段落及元数据用Arial Narrow 400取得原图高密度、窄字面效果。教育项目中的局部强调才使用Arial 700。中文替换使用PingFang SC 400/600，不把不存在的细体或粗体交给浏览器伪造；所有文本设置font-synthesis:none。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名 | Helvetica Neue | 100 | 37/39/-1.6px | 保留参考的极细紧排大写无衬线，不改为Didot或Bodoni。 |
| 职业说明 | Helvetica Neue | 300 | 13.2/14.8/-0.15px | 保持现有轻字重与两行结构。 |
| CV标牌 | Helvetica Neue | 300 | 12/16/0px | 保留灰色轻字重标牌文字。 |
| 章节标题 | Arial | 400 | 18.4/23/-0.65px | 保持常规字重，不扩大标题强调。 |
| 正文默认与经历条目标题 | Arial | 400 | 11.8/16/-0.15px | 保留原有正文默认规则；未使用FuturaMedium，也不重复定义全局字体。 |
| 教育条目标题 | Helvetica Neue | 400 | 11.8/16/-0.2px | 实际规则显式指定真实400常规字款，消除h3浏览器默认粗体；专业名称与职位不再整行加粗。 |
| 教育局部强调 | Arial | 700 | 11.8/16/-0.2px | 仅MASTER使用实际粗体，其余文字保持Helvetica Neue 400。 |
| 经历说明 | Arial Narrow | 400 | 9.5/11.5/0px | 依审查保留窄体正文，不进一步加粗。 |
| 经历行内注释 | Arial Narrow | 400 | 9/12/0px | 保持低对比小号注释。 |
| 教育元数据 | Arial Narrow | 400 | 11.5/15/0px | 日期另用9.2px，保持现有元数据层级。 |
| 教育类型代码 | Arial | 400 | 11/15/0px | 保持ED及T的常规字重。 |
| 学校说明 | Arial Narrow | 400 | 9.2/11.5/0px | 保留现有紧凑说明文字。 |
| 侧栏正文 | Arial Narrow | 400 | 10.5/14/0px | 个人信息标签为8.1px/11px，值为10.7px/15px；均保留常规窄体。 |
| 侧栏个人信息标题 | Arial Narrow | 400 | 12/15/-0.35px | 标题位置及字体不变。 |
| 侧栏联系方式与社交标题 | Arial Narrow | 400 | 10.8/14/-0.15px | 仅通过分隔线外边距调整纵向位置，不改字重。 |
| 侧栏电话 | Helvetica Neue | 300 | 13/17/-0.3px | 保留轻字重电话号码。 |
| 社交账号 | Arial Narrow | 400 | 9.5/12/-0.1px | 紧凑职业主页行仍为7.3px/10px，资产槽位及账号文字不变。 |
| 技能及结尾栏目标题 | Arial | 400 | 12.3/17/-0.3px | 保持原有常规字重层级。 |
| 技能标签 | Arial Narrow | 400 | 9.2/10/0px | 保留窄体及六行技能密度，不加粗。 |
| 语言与自述 | Arial Narrow | 400 | 9.2/11.5/0px | 保留现有行距、列宽及低对比字色。 |
| 页脚姓名 | Helvetica Neue | 300 | 12.8/17/-0.3px | 保持右对齐轻字重署名。 |
| 页脚电话 | Helvetica Neue | 300 | 11/14/-0.15px | 保持原有页脚层级。 |
| 中文姓名 | PingFang SC | 400 | 35/43/1px | 保留真实400字款，不伪造细体。 |
| 中文章节标题 | PingFang SC | 400 | 18/25/0px | 保留中文专用标题规则。 |
| 中文替换正文 | PingFang SC | 400 | 11/15/0px | 保留中文说明、学校、自述与技能标签规则，允许自然换行。 |
| 中文教育局部强调 | PingFang SC | 600 | 11.8/16/-0.2px | 沿用中文实际600字重，禁止浏览器合成粗体。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布边缘安全区：常规文字左边69px/800=8.63%，最右文字距右边34px/800=4.25%，照片允许作为特例伸到43px/800=5.38%；顶端黑标牌和底部页脚允许出血到边，姓名起点距顶75px/1131=6.63%，页脚署名距右52px/800=6.50%、距底12px/1131=1.06%。②栏内排字安全区：左柱内边距17px/800=2.13%，有效字宽139px/800=17.38%；照片底至个人信息标题约32px/1131=2.83%；正文与侧栏外边间距29px/800=3.63%；上部两列间隙18px/800=2.25%，下部两列间隙28px/800=3.50%，正文分隔线上下至少12px/1131=1.06%。③素材及前后层级安全区：照片窗174×171px，对应宽21.75%、高15.12%；与黑柱重叠水平148px/800=18.50%、垂直151px/1131=13.35%；照片右边与正文起点净距54px/800=6.75%，不能让文字侵入此间距。照片替换建议人物头部距裁框至少8px，对应画布宽1.00%、高0.71%，但验证源图时保持原裁框。长姓名先在姓名独立行换行，再由页眉自动增高推动下方双栏，不压缩字面；长经历与中文正文在minmax(0,...)列内自然换行并增高，保留栏目间隔与照片层级，不截断或用隐藏溢出掩盖。

基准画幅固定800px，按507:717设最小高度1131px；当前示例维持4条工作经历、2条志愿经历、3条教育经历、两组各6行技能、4行语言和9行自述，复现源图密度。姓名只替换为Alex Morgan或林予安，较短姓名不人为撑满原姓名宽度。英文维持大写细字重层级；中文将main的lang设为zh，使用实际可用PingFang SC 400/600，不能调用伪细体或伪粗体。正文列均采用minmax(0,...)，长机构名、较长姓名、联系方式和自述允许自然折行；自述替换时可移除按参考长度设置的span分行，交由实际内容换行。页眉增高会同步推动照片、侧栏和正文，教育及各正文网格按内容增高，页脚始终位于所有内容之后；当内容确实超出原页密度时允许主画布高于1131px，不使用overflow:hidden、行数裁切或整体缩小文字。侧栏黑色背景随其自身文字增长延伸，但不为匹配右栏高度而任意填满底部留白。资产缺省为空透明槽位，由宿主注入指定裁片，库本身无需外网、脚本、外链字体或原图背景。

### 素材槽位

portrait仅负责独立照片窗，裁片不包含姓名、侧栏标签、电话或履历文字；这是一张矩形实景照片，不是人物透明抠像，替换无需透明通道。五个social-*槽位仅保留原图侧栏内的真实小图标，裁框避开右侧账号文本。照片之外的黑柱、标牌、分隔线、技能条、页脚及所有文字都由HTML/CSS生成。模板不嵌入源图，也不包含源图的个人姓名、号码或账号。

- `portrait`：左上矩形人物照片窗，作为前景覆盖黑色侧栏；接近正方形的暖调人物半身实景照片；不需要透明抠像，保持原窗比例与人物占画面比例，不能携带旁边文字。
- `social-mail`：第一行联系方式的微型信封图标；独立透明信封图标或同等轮廓单色小图标，浅色主体，不能包含账号文字。
- `social-network`：第二行社交链接前的方形平台图标；透明背景的单色平台标识，仅保留图标，不含名称或链接。
- `social-chat`：第三行社交账号前的聊天平台图标；同尺寸白灰色小型聊天标识，透明背景。
- `social-portfolio`：第四行作品集链接前的微型平台图标；独立横向小标识，保持约12:10比例，禁止带入右侧作品集账号。
- `social-professional`：第五行职业主页前的方形平台图标；浅色方形职业社交标识，透明背景，不含个人资料。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[非对称身份侧栏](../layouts/asymmetric-balance.md#layout.identity-sidebar)、[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[对齐标签量尺：平条、框条与圆点](../layouts/grid-and-alignment.md#layout.labeled-meter)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)。

整页结构与几何样式唯一维护在 [主次双栏 · 窄侧栏](../layouts/resume-full-page.md#layout.resume-narrow-sidebar)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-narrow-sidebar"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1131,
    "palette": {
      "background": "#F5F5F5",
      "text": "#171717",
      "primary": "#030303",
      "secondary": "#898A8C"
    }
  }
}
```

校准边界：仅修改4处实际CSS规则。两条侧栏短线延长至栏内有效宽度140px；个人信息后的间距增加13px，社交区前间距增加6px，使联系方式下移13px、社交区下移19px，黑柱及个人信息标题位置不动。教育整行偏粗的根因是.degree未显式设置font-weight，导致h3沿用浏览器默认粗体；现改为Helvetica Neue 400，仅MASTER保留Arial 700。其余窄体依审查保留，不调整全局字体。照片和五个图标槽位、正文网格、页脚、文案及用户事实均不变。

<a id="combination.resume-06"></a>

## 黑色栏目带与灰色贯穿侧栏简历

风格标签：二级：理性信息风 / 极简理性。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1136px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

画面不是常规左右等高卡片：底层为白色整页，顶部黑色横带从左边一直延伸到右边；右侧浅灰竖栏覆盖在黑带之上，从页面顶端贯通到底端。左主栏宽约474px，占59.25%；灰侧栏位于x=474px，宽约294px，占36.75%；最右保留32px底层露出，顶部为黑色、其余为白色。左上姓名块靠右对齐，距侧栏约23px，下接职业；侧栏顶端放置双细线圆形照片窗。左栏正文从y=281px开始，以三条深色通栏题带划分教育、工作、推荐人，题带右端抵住侧栏边缘。教育两条、工作三条、推荐人两列，信息密度较高。侧栏从照片下方依次排简介、联系方式、技能、语言，正文较左栏更密，模块标题不使用黑底。推荐人两列与顶部姓名的对齐方式不同，属于底部独立的小网格。

形状与载体：顶部黑色矩形高239px；右贯通灰色矩形无圆角。照片窗外径约176px，位置约x=535px、y=29px，为黑色实圆、白色内圈及深色外细圈的同心结构。三条章节题带厚约39px，左起29px并延伸到灰侧栏。教育、工作、推荐人的微型白色图标分别作为独立资产槽，保留其真实图形。联系方式以电话、地球、定位三组图标配文本，组间横线；技能和语言为窄长矩形进度轨，宽约233px、高9px，直角无圆角。

### 配色与质感

底色为#FFFFFF；顶部横带与三条节标题带约#222222，照片占位窗底色约#080808；侧栏为中性浅灰#C3C3C3；左栏正文接近#151515，侧栏大标题及图标偏深灰#454545；技能条以深灰填充、浅灰空余与细黑轮廓形成对比。白字仅用于黑色标题区，不将侧栏改成白卡。

```json
{
  "palette": {
    "background": "#FFFFFF",
    "text": "#151515",
    "primary": "#222222",
    "secondary": "#C3C3C3"
  }
}
```

纹理：原图的斜线、淡字及覆盖印记属于水印，不构成复现纹理，全部去除。白纸、黑带及灰栏使用纯色；不添加噪点，不在照片或正文上覆盖纹理。

渐变／光场：无。顶部、侧栏、标题带与技能填充均为平涂色块。

### 字体组合

原图为紧凑无衬线体系，姓名两行大写、粗体、右对齐；职位及题带标签明显窄于普通Arial。侧栏About Me、Contact、Skills为较厚的常规宽度无衬线，主体小字偏窄而密集。替代采用Arial 700呈现姓名和侧栏标题，Arial Narrow 400呈现职位、栏目、小字与日期。Arial Narrow的实际窄体字形承担压缩效果，不使用transform横向压缩或合成粗体。姓名约43px，侧栏标题约32px，题带约18px，主体约13.4px。原图字体的具体家族不可确认，替代在端点和数字宽度上有轻微差异。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名 | Helvetica Neue | 500 | 40/42/-0.7px | 使用实际Medium字款减轻笔画重量，字号由43px降至40px；保留两行右对齐及原行高，不横向压缩。 |
| 职业 | Arial Narrow | 400 | 20/24/0px | 保留真实窄体，字号由22px降至20px，原位置和行高不变。 |
| 深底栏目标题 | Arial Narrow | 400 | 18/21/0px | 维持原有真实窄体及字号，不调整题带。 |
| 侧栏大标题 | Helvetica Neue | 500 | 32/36/-0.65px | About Me、Contact、Skills改用实际Medium字款，减轻视觉重量；保持字号、行高和模块起点。 |
| 条目标题及年份 | Arial Narrow | 400 | 16/19/0px | 保留原有常规窄体，不增加字重。 |
| 正文与联系方式 | Arial Narrow | 400 | 13.4/14.5/0px | 审查确认正文密度接近参考，保留现有实际400窄体；联系方式行高15px，推荐人信息行高17px。 |
| 技能分组标题 | Arial Narrow | 400 | 16/20/0px | 保持现有字形、下划线及分组间距。 |
| 技能与语言标签 | Arial Narrow | 400 | 13/15/0px | 保留现有常规窄体和进度条上方间距。 |
| 中文替换 | PingFang SC | 400 | 13.4/17/0px | 保留中文正文规则；中文姓名及侧栏标题使用实际600字重，字号分别随对应规则为40px和32px。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三级安全区：①画布边缘安全区：左栏正文距左边29px=3.625%W，底部至少24px=2.113%H，右侧保留32px=4%W的背景露出，不能拿来扩展侧栏文字。②栏内安全区：左正文右界约437px，距灰栏37px=4.625%W；侧栏左右内距29px与31px，分别为3.625%W与3.875%W，文字有效宽234px=29.25%W。③局部避让安全区：照片顶距29px=2.553%H，照片底缘到简介标题至少31px=2.729%H；章节图标右缘到题字至少22px=2.75%W；职位与日期之间至少12px=1.5%W，不能叠字。长姓名允许从两行变三行并增加顶部横带及左正文起点；长段落按真实行高向下增长，章节最小间距保留18px，不隐藏文字、不缩字号。需维持严格原比例时，应将文案编辑到示例相同行数，而不是裁切内容。

基准画幅800×1136，保持474/294/32三段横向关系，不做会改变构图的移动端折栏。基准文本保留两段教育、三段工作、两列推荐人与3/4/2项能力轨。main与网格使用min-height而非定高裁切，节距使用min-height保证短文本时位置稳定、长文本时自然增高。英语姓名默认两行右对齐；超长姓名按词拆成三行并添加is-long-name，将顶部横带增至281px，侧栏仍从页顶贯通。中文姓名可用林予安并设置main的lang为zh，正文使用PingFang SC 400、标题600，保留实际字重；中文段落按相近视觉行数重写，不逐字硬塞英文宽度。若必须输出1136px高的单页，应编辑内容到原有行数，而非减小正文、隐藏溢出或删除复杂区域。照片槽无源图照片可裁，故使用null明确区分缺失素材与合法裁片；注入头像后保持圆窗、圈线与侧栏位置不变。页面无外网资源、无脚本、无超链接，所有个人履历与联系方式均为虚构示例。

### 素材槽位

原图圆窗内只有照片占位文字，没有真实人物照片，因此portrait槽不从原图复制含字圆窗，source_crop为null，避免把文字或个人信息当照片资产。圆窗黑底和双圈全部由CSS负责，portrait槽仅用于宿主以后注入独立人像，要求正方形或纵向头像、面部居中、裁切后不含文字。六个实际小图标分别裁取原图中的独立图形，不带栏目文字、分割线或周边水印。原图水印与背景斜线不设资产槽。

- `portrait`：圆形人像注入槽；原图此处仅为含字的占位圆，不存在可合法裁取的独立照片；宿主提供不含字、无水印的正方形或纵向头像；圆形遮罩及双圈由CSS生成，未提供照片时保留无字黑圆。
- `education-icon`：教育题带中的白色学位帽；透明底白色学位帽小图标；原图裁片可带紧贴图标的深色背景。
- `work-icon`：工作题带中的白色公文包；透明底白色公文包图标，不包含题带文字。
- `references-icon`：推荐人题带中的白色人群图形；透明底白色人群小图标，不包含旁边标签。
- `phone-icon`：侧栏电话图标；透明底深灰电话图标，或仅含紧贴图标灰底的原图裁片。
- `web-icon`：侧栏地球图标；透明底深灰地球图标，不带网页地址或组间横线。
- `location-icon`：侧栏定位图标；透明底深灰定位针，不带地址或水印。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[非对称身份侧栏](../layouts/asymmetric-balance.md#layout.identity-sidebar)、[矢量图标通栏标题色带](../layouts/layout-and-type.md#layout.icon-section-band)、[对齐标签量尺：平条、框条与圆点](../layouts/grid-and-alignment.md#layout.labeled-meter)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)。

整页结构与几何样式唯一维护在 [分节双栏 · 贯穿侧栏](../layouts/resume-full-page.md#layout.resume-section-sidebar)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-section-sidebar"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1136,
    "palette": {
      "background": "#FFFFFF",
      "text": "#151515",
      "primary": "#222222",
      "secondary": "#C3C3C3"
    }
  }
}
```

校准边界：仅原位修订审查指出的姓名、职位及三个侧栏标题规则，未重复定义全局字体。Helvetica Neue 500须使用真实Medium字款，继续禁止合成字重；当前姓名非Didot，不引入Bodoni。正文未被审查判为偏厚，因此不改其字体与换行。列宽、标题行盒、正文密度、模块位置、双圈圆窗及全部图像槽位保持不变。

<a id="combination.resume-07"></a>

## 回转蓝带与圆形人像简历

风格标签：二级：先锋实验风 / 解构排版。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1132px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

以近白冷灰整页为底，没有独立白卡或边框。主视觉为从顶部x≈174到453贯穿下来的钴蓝宽带：上端近似直柱，左侧内缘在中段大幅弯向页面左边，右侧外缘经过人像后方继续向左下回收，最后在y≈785贴左边出血。曲带内部上方放个人简介，下方沿曲线排列兴趣英文、姓名弧字及黑色兴趣图形。灰阶圆形人物位于x≈277、y≈397、直径≈225，前压蓝带；姓名绕其左上外缘展开，不能放入照片裁片。右上为教育、奖项、语言三个疏密不同的信息组，左边有一列竖向英文履历标题。下方左侧为三条经历，日期单列、内容列带细分隔线；右下为软件缩写方框和出血到底的深灰U形条，最右以竖排技能标题、向上箭头和蓝色CV圆章收尾。顶部靠右还有一个被画布裁去大半的蓝圆。

形状与载体：蓝色主形状以单一闭合贝塞尔曲带完成，顶边和左边均出血，不以大圆叠加误造弯曲半径。人像为真圆裁切。姓名和兴趣分别使用两条独立SVG文字路径。顶部蓝圆被画布边界裁切；底部灰U条与圆头像没有几何关联，单独画路径。软件框为三个细黑线方框，底部箭头为直线和小三角。兴趣中的游泳、手柄、哑铃、舞动人物以独立简洁黑色SVG剪影重绘，不包含任何原始图标位图。

### 配色与质感

背景约#EEF2F0，蓝色主曲带约#1947F3，顶部圆和CV圆沿用同色。主要文字近#080A09；次级解释文字#858A88；简介及弧字使用略带灰的浅色#DFE7E6。软件U形底条为#858584，日期和学校名保持黑色形成层级，分隔线为#969C98。

```json
{
  "palette": {
    "background": "#EEF2F0",
    "text": "#080A09",
    "primary": "#1947F3",
    "secondary": "#858584"
  }
}
```

纹理：原图大面背景和蓝带基本为平涂，不添加纸噪点或颗粒。仅人物照片保留其摄影层次；照片纹理不得扩展到蓝带、文字或背景。

渐变／光场：无。主体背景、曲带、圆章和灰条均为纯色，人物光影由照片槽位承担。

### 字体组合

原图英文分区标题为紧凑、偏粗的无衬线大写，横向有轻微字距；用Arial 700贴近，不用Arial Black过度加黑。中文标题与正文为现代黑体，用PingFang SC 600和400，其中600是真实半粗体而不是伪造700。简介小字密排，经历说明较细较灰；日期更接近窄身衬线数字，选Baskerville 400。原INTEREST呈明显窄高和弧排，用Arial Narrow 400配SVG沿路径布局；弧形姓名用Arial 700，保留字符之间的呼吸感。软件缩写用Arial 700，沿原图使用不等字号。全部文字font-synthesis:none，不引用外部字体。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 英文分区标题 | Arial | 700 | 20/24/0.5px | 保留实际700字款，不使用Arial Black或额外描边。 |
| 中文分区副题 | PingFang SC | 600 | 14/22/0.3px | 保留实际600半粗体；简介中文副题仍为400。 |
| 简介与正文 | Helvetica Neue | 400 | 13.5/21.8/0px | 直接修改原容器默认字体，拉丁正文使用Helvetica Neue真实400，中文回退PingFang SC 400；不重复定义全局字体。简介字距维持0.1px，教育正文行高21.4px，奖项24px，语言26px。 |
| 经历说明 | Helvetica Neue | 400 | 13.1/21.5/0px | 继承修订后的400正文默认值，保持现有灰色、密度及换行规则。 |
| 学历、学校与经历条目标题 | PingFang SC | 600 | 13.5/21.4/0px | 保留实际半粗体层级；经历条目标题行高20px。 |
| 日期 | Baskerville | 400 | 14/20/0px | 由15px收至14px，减弱宽数字与衬线的视觉分量；经历日期仍保持19px行高。 |
| 弧形姓名 | Arial | 700 | 21/24/1px | 原规则已为真实粗体无衬线，不涉及Didot过细问题，保持姓名与照片位置不变。 |
| 兴趣窄高弧字 | Resume07 Condensed | 700 | 31/38/-0.8px | 专用局部别名明确指向本机真实窄体，避免Arial Narrow未命中后变成普通Arial；配合延长路径显示完整INTEREST，不使用textLength或横向缩放。 |
| 兴趣中文弧字 | PingFang SC | 400 | 15/22/0.4px | 保留原独立中文文字路径。 |
| 竖向联系信息 | Helvetica Neue | 400 | 11.8/16/0.1px | 从700改为真实400，保留位置、竖排方向及全部联系文案。 |
| 竖向履历标题 | Arial | 700 | 22/28/0.35px | 保留实际700，仅略收字号与字距。 |
| 软件方框缩写 | Arial | 700 | 37/37/-1px | 保持原方框尺寸和字款。 |
| 灰条大号软件缩写 | Arial | 700 | 48/53/1px | 保持Ai、Id的不等层级排版。 |
| 竖向技能英文与CV圆章 | Arial | 700 | 20/23/0.4px | 保持原规则；CV圆章行高24px、字距0.5px。 |
| 竖向技能中文 | PingFang SC | 600 | 15/19/1px | 保留真实600及原竖排规则。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①页面文字安全区左右至少40px（0.050W），常规底部至少42px（0.037H）；左侧竖联系栏保留x=60–79px（0.075–0.099W），顶部至少51px（0.045H）；出血蓝带和灰条不受此限。②照片/装饰隔离区：portrait为[278.4,397.6,222.5,222.5]px，归一化[0.348,0.351,0.278,0.197]；教育左界548px（0.685W），与照片右界约501px相距47px（0.059W）；简介正文止于约295px（0.261H），姓名弧字始于约354px（0.313H），两者至少59px（0.052H）；照片上沿与弧字之间保留约14–20px。③块内排字安全区：简介左右内缩38px和28px（0.048W、0.035W），正文行高21.8px（0.019H）；经历日期列至正文起点至少59px（0.074W），正文与横线至少7px（0.006H）；右栏宽214px（0.268W），中文标题与英文之间10px（0.013W）。姓名超过当前长度时优先更换为两段弧排或在圆上方增加一行，不横向压扁字形；正文增加时用扩展模式推动经历区和画布底端，不遮盖、不省略、不缩到不可读。

基准严格为800×1132，所有源图坐标按800/658≈1.2158转换；不以整图缩放背景替代重建。库内portrait为空资产槽，验证时由宿主按source_crop注入背景裁片，模板本身不携带原照片或网络资源。正文示例保持简介10行、奖项5行、教育2段、经历3段与每段2条说明；当前经历说明允许自然换行为3个视觉行，保持原图密度。姓名可用Alex Morgan或林予安，当前弧排为ALEX MORGAN — DESIGN，中文姓名出现在简介。长姓名优先删去职业后缀，再分成两条外弧，不用textLength强制挤压。中文正文使用PingFang SC，英文使用Arial，日期使用Baskerville，字体均来自允许的本机字体集合且禁用伪合成。英文长正文取消简介span的逐行分组，让段落自然换行，保持原字号和行高。经历或奖项变长时可设置data-density="expanded"，把右栏与经历改为正常网格流，自动增高页面并推动技能区，不截断文本。若简介超过约12行，应由制作端同步下移照片与两条文字路径，增加主蓝带中段高度，并把经历顶部留到照片底部之后至少125px；这种构图级调整不靠缩字解决。所有扩展后的列仍使用minmax(0,...)；顶部圆和底部灰条是允许出血的装饰，不能因此裁去实际正文。

### 素材槽位

唯一外部资产为灰阶圆形人物照片。portrait只截原图x≈229至412、y≈327至510的独立人像方形包围区，并在HTML中再用圆形overflow裁切，排除旁边姓名和履历文字。替换使用有暗部侧光、头肩近景、头部朝右的灰阶方图，不要求透明抠像。蓝带、兴趣图形、弧字、软件框、箭头及圆章均由HTML/CSS/SVG负责，禁止并入照片。

- `portrait`：圆形灰阶侧光头肩照片，位于蓝带前方；灰阶方形头肩近景，人物向右，头顶靠近上边、颈肩延伸至下边。宿主将裁片填满222.5px圆窗；无需透明背景，禁止裁入照片外弧字。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[竖排栏目导轨](../layouts/asymmetric-balance.md#layout.vertical-section-rail)、[回转带与人像交界布局](../layouts/overlap-and-collage.md#layout.curve-portrait-junction)、[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[可参数化U/J形回转粗带](../shapes/organic-shapes.md#shape.u-turn-band)、[对齐标签量尺：平条、框条与圆点](../layouts/grid-and-alignment.md#layout.labeled-meter)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)。

整页结构与几何样式唯一维护在 [曲线分区 · 人像穿插](../layouts/resume-full-page.md#layout.resume-curve-junction)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-curve-junction"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1132,
    "palette": {
      "background": "#EEF2F0",
      "text": "#080A09",
      "primary": "#1947F3",
      "secondary": "#858584"
    }
  }
}
```

校准边界：仅修正实际字体、兴趣路径及教育组间距。INTEREST路径由约94px延长至约125px，起点左移并采用明确的本机窄体字面，保留完整准确文字，不用装饰曲线替字。教育首段高度减少24px，分隔线与第二段同步上移；奖项上边距增加24px补偿，因此奖项及语言组位置不变。联系信息改400，竖向履历标题微收，日期缩小1px。主蓝带、照片槽位、姓名弧线、经历与技能布局及所有事实文案均保留；继续禁用字体伪合成。

<a id="combination.resume-08"></a>

## 群青贯穿网格与纸纹简历

风格标签：二级：理性信息风 / 瑞士网格。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1131px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

原图为竖向纸页，浅灰白颗粒背景铺满整幅。两条纵向细蓝线位于x约38和762px，通栏横线位于y约204和1093px；中轴线x=400px仅从标题下延伸至页底。标题带高约204px，左侧巨型Resume.，右侧蓝色六臂星形，标题尾端上方有小型灰色CV椭圆。正文两栏等宽但内边距不对称：左栏正文起于54px，右栏照片起于408px，右栏文字起于416px。左栏为教育与四段经历，右栏依次为近正方形黑白肖像、夸张字号姓名、简介与联系行；y约818px处仅右栏出现分隔线，下方为兴趣、语言、技能双列。照片是直接嵌入网格的矩形图窗，无白卡、阴影和独立底板。页面末端的作品集短注位于右下方，底部通栏线下保留窄纸边。

形状与载体：满页两侧竖向定位线、标题下横线、页底横线、中轴竖线与右下局部分隔线组成严格的细线骨架。右上装饰是三条等长矩形棒以0、60、120度交叠形成的六臂星号，无需真实图片。CV为约52×23px的轻微倾斜椭圆描边。照片矩形无圆角。项目符号使用极小蓝色圆点，不使用复杂图标。

### 配色与质感

主体文字、巨型标题、姓名、星形装饰使用接近深电蓝的#1006AD；细网格线使用同色低透明度，视觉近#716BCE。背景为#F2F2F0附近的冷中性白，颗粒在浅灰间波动；肖像仅承担黑白灰角色。CV椭圆与小字为#525252，不能误做蓝色徽章。

```json
{
  "palette": {
    "background": "#F2F2F0",
    "text": "#1006AD",
    "primary": "#1006AD",
    "secondary": "#525252"
  }
}
```

纹理：仅背景纸面使用短SVG feTurbulence，双频弱颗粒结合浅灰底色，层置于全部文字、线和照片之后。建议可见明暗振幅约3%至6%，不制造明显云团、脏边或斑驳。肖像资产自身黑白颗粒原样保留，不能再叠纸纹；文本与网格不加噪点。

渐变／光场：无显式渐变。背景是均匀浅灰纸面加微弱噪声，不使用聚光、径向光晕或照片上渐变。

### 字体组合

原图主体为紧凑无衬线字体，双层a、短横和相对窄的字面接近Helvetica/Arial系统，正文密度高、行距紧。巨型Resume.是重黑字重，接近Helvetica Neue 700配合负字距，不宜用圆体或过宽的装饰黑体。正文选Arial Narrow 400及700维持原图窄字面与高密度，栏目标题用Helvetica Neue 700。姓名是大写首字母、低位小写尾段与两个间隔放大的大写字母组合，并非普通一行同字号姓名。CV选Arial italic 400；中文回退使用实际可用的PingFang SC 400/600，不合成不存在的字重。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 巨型页标题 | Helvetica Neue | 700 | 96/0.98/-6px | 保留现有真实700字重、字号及负字距。 |
| 栏目标题 | Helvetica Neue | 700 | 24/1.08/-1.25px | 保留现有标题层级与字重。 |
| 条目小标题 | Helvetica Neue | 700 | 14/1.22/-0.3px | 替换Arial Narrow窄体，使用真实700字款恢复条目字面宽度。 |
| 教育及经历正文 | Helvetica Neue | 400 | 13.5/1.29/-0.2px | 正文默认改为真实400常规字款，不使用FuturaMedium或合成加粗；保持原行距。 |
| 简介正文 | Helvetica Neue | 400 | 13.5/1.02/-0.25px | 继承真实400正文，保留紧排行距；简介至少占七行高度。 |
| 联系区标题 | Helvetica Neue | 700 | 18/1.2/-0.9px | 保持现有真实700字重。 |
| 联系信息 | Helvetica Neue | 400 | 13/1.52/-0.2px | 继承修订后的常规正文字款，不改变联系方式。 |
| 兴趣、语言及技能列表 | Helvetica Neue | 400 | 12/1.48/-0.2px | 保持字号和行距，以较宽的真实常规字面修正窄瘦观感。 |
| 作品集短注 | Helvetica Neue | 400 | 12.5/1.3/-0.35px | 继承常规正文，保留右下对齐和底部位置。 |
| 姓名大字 | Arial | 700 | 78/1/-3px | 当前姓名并非Didot细体，保留与参考一致的无衬线大字，不改为衬线体。 |
| 姓名小字 | Arial Narrow | 400 | 26/1/-1.2px | 仅保留在混合字号姓名尾段，不再作为正文默认。 |
| 普通长姓名模式 | Arial | 700 | 60/1.05/-2px | 保留现有自然换行适配规则。 |
| CV椭圆注记 | Arial | 400 | 17/1/-0.4px | 保留真实斜体及灰色椭圆。 |
| 中文正文回退 | PingFang SC | 400 | 13.5/1.29/-0.2px | 保留真实400中文回退；列表与联系方式随所属规则继承字号。 |
| 中文简介 | PingFang SC | 400 | 13.5/1.4/0 | 保留现有中文简介专用规则。 |
| 中文栏目标题 | PingFang SC | 600 | 24/1.08/-1.25px | 保留真实600字重。 |
| 中文条目小标题 | PingFang SC | 600 | 14/1.22/-0.3px | 保留真实600字重，不合成700。 |
| 中文普通姓名 | PingFang SC | 600 | 59/1.05/2px | 保留完整中文姓名模式。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①外缘结构安全区：左右各38px，即画宽4.75%，顶端主要图文起点约79px，即画高6.99%；底部线下留38px，即画高3.36%，细网格可越过内容安全区直达画幅边缘。②栏内文字安全区：左栏起点54px即6.75%W，距左线16px即2%W；左栏右侧距中轴至少20px即2.5%W。右栏正文从416px即52%W起，距中轴16px即2%W，右端距边线16px；照片与中轴间留8px即1%W，与右线间约9px。③肖像与装饰安全区：照片中人脸推荐保持在画布x约490–680px、y约235–411px，即横向61.25%–85%、纵向20.78%–36.34%，不得叠文字；姓名另占照片下约88px即7.78%H，星号保留约94×94px独立盒并距右边线至少28px即3.5%W。长姓名不得机械缩小：切换普通姓名模式，允许80px姓名区自然增高或两行显示并下推右栏。长文案允许条目重排、画布增高及底线下移，不能裁切或隐藏。严格固定1131px导出时应使用此等密度示例，不能同时强塞任意长度文字。

基准输出800×1131px，正文外框724px、左右各362px，列轨道全部使用minmax(0,...)。不加载网络字体、脚本或外链；使用列明的本机真实字体，font-synthesis:none。宿主按portrait裁切信息填充空槽位，模板不嵌入原始照片，灰底仅为未注入资产时的槽位底色。英文示例保留三条教育、四条经历、密集简介、两条联系信息、四项兴趣、四项语言、七项技能及作品集尾注；显式换行为基准画幅的排字控制，换文案时先清理对应br并按实际长度重新断行。姓名Alex Morgan以A/lex与M/orga/N的混合字号复现视觉关系，辅助技术读取完整标准姓名；其他英文姓名可调整片段，中文林予安应改为完整文本并添加plain-name及lang='zh'，不能生硬拆拼拉丁字母。长姓名保持字形比例并自然换行，长段落通过正常文档流推动下方模块与末端通栏线，main采用min-height而非固定height，不使用overflow:hidden、line-clamp或压缩字号。严格复核原图时使用基准文案和高度；扩展版同步更新导出高度，不改变800px宽及50%中轴。纸纹强度由--paper-grain控制，仅作用于背景；不得让纹理覆盖肖像或文字，也不应将整幅原图装入任何背景层。

### 素材槽位

唯一图像资产为右上黑白半身肖像，裁片只包含矩形照片内部及人物原有灰墙背景，不包含标题、姓名或旁边履历文字。替换需要竖向略宽的黑白胸像，人物头顶接近图窗顶部，胸肩覆盖下部，不需要透明抠像。CV、星号、线条、纸纹均由CSS或SVG绘制，不进入资产槽位。

- `portrait`：右上矩形黑白胸像，保留发型、头肩比例和原有墙面背景。；黑白胸像或半身像，图窗约345×322px，脸部居中偏右，头顶留白约0–8px，肩部自然延伸至下边缘。使用含干净灰墙背景的普通照片，不要求透明；不允许裁入履历文字、蓝线或姓名。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[同轴编辑式分隔线](../layouts/grid-and-alignment.md#layout.editorial-rules)、[三预设放射贴纸](../shapes/organic-shapes.md#shape.radial-sticker)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)、[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)。

整页结构与几何样式唯一维护在 [通栏双栏 · 网格对齐](../layouts/resume-full-page.md#layout.resume-editorial-grid)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-editorial-grid"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1131,
    "palette": {
      "background": "#F2F2F0",
      "text": "#1006AD",
      "primary": "#1006AD",
      "secondary": "#525252"
    }
  }
}
```

校准边界：直接修改现有字体和纸纹规则，不追加全局字体覆盖。纸纹提高强度并增大颗粒，仅留在背景伪元素。正文改用Helvetica Neue真实400，小标题保留700层级；虚构经历仅压缩措辞并保持原有行数，避免字面变宽后额外换行推低页底。简介设置七行最小高度，使联系区和右栏分隔线约下移一行；同步减少下区最小高度，保留页底线及尾注锚点，长内容仍可自然撑高。照片槽位、姓名组合、标题、星号及网格均不变；纸纹和最终断行宜在800×1131原尺寸复核。

<a id="combination.resume-09"></a>

## 云天纸张与实物夹具拼贴简历

风格标签：二级：手账拼贴风 / 照片剪贴；二级：手账拼贴风 / 票据档案。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1132px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

整体为无统一白底的云天画布，四块独立信息载体错位拼贴。左上白色圆角身份卡约为[x=39,y=50,w=479,h=271]，照片在卡内左侧，上缘与姓名同高；照片右侧为密集身份说明，下缘横排社交与联系方式。右上教育纸约为[x=486,y=169,w=285,h=527]，置于身份卡后方，身份卡覆盖其左上区域。教育纸上端由红色图钉固定，标题与正文之间保留显著空隙。左下红色经历纸约为[x=36,y=382,w=396,h=710]，以四段履历填满主体，黑色夹子跨过上沿。右下黑色技能纸约为[x=468,y=722,w=289,h=373]，轻微顺时针旋转，与教育纸分离，中间露出云天；其左上叠着赭色折叠纸胶带，右下透明胶带横跨纸片。蓝色天空不是照片框、白卡底或大面积纯色替代物，而是贯穿全部卡片间隙的独立背景。

形状与载体：身份卡为约24px圆角白卡；红经历纸保留轻微非矩形外轮廓；教育纸上下为密集细齿撕边，左右近乎直边；技能纸为轻微旋转的深色矩形。教育末尾条码用可控宽窄竖线重新绘制。技能软件方块为浅蓝小圆角矩形加文字缩写，不使用真实商标图像。赭色胶带由两个斜置多边形组成，带折痕和细高光；透明胶带使用半透明多边形、折射状细线和不规则边缘。银色浮雕装饰、红图钉、黑夹子保留为独立真实素材槽。

### 配色与质感

背景为鲜蓝到灰蓝云天，主蓝近似#419AC5，云朵偏#EEF0E9。身份卡#F8F8F3，教育纸#F1EDE7，经历纸为高饱和朱红#EA292E，技能纸#222326。正文以#111111为主，黑纸上用#F3F1EA。信息微标签为#557F91，折叠纸胶带#B89A55，金属装饰为银蓝色并带红色外缘，图钉为亮红色。

```json
{
  "palette": {
    "background": "#419AC5",
    "text": "#111111",
    "primary": "#EA292E",
    "secondary": "#222326"
  }
}
```

纹理：云天裁片承担原始背景的印刷颗粒；另有极弱CSS点阵仅施加于背景层。白卡、教育纸、红纸和黑纸分别在各自底层施加低透明度短SVG feTurbulence及细微纸纤维，透明度约0.045—0.085；纹理层位于文字与照片下方，不覆于照片、文字或实物槽上。黑纸局部横向细线用于模拟压纹，不把噪点当作完整背景。

渐变／光场：主要渐变仅用于胶带的纸折面和透明胶带折光，以及白卡、教育纸和黑纸表面的极弱明暗变化。红经历纸自左上#ED3035至右下#E6252B，色差很小。天空不用CSS渐变替代云层；头像不添加渐变。实物图钉和金属件保留自身照片高光。

### 字体组合

原图采用细笔画高对比衬线和带花饰的大写首字母作为标题，正文为紧凑几何无衬线；段落标题是较柔和的书刊衬线，微型元信息以大写无衬线组织。复现使用Didot 400表现主标题、Baskerville 400表现经历及学校名、Arial 400/700表现正文，姓名与章节首字母局部使用Snell Roundhand 400。Snell仅用于单个花饰字母，不作毛笔式正文。所有字重使用已允许的真实字重，不使用合成加粗、合成斜体或不存在的500字重Arial。中文替换使用PingFang SC 400/600，因中文字面较满，需重算行数而不是整体压缩。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名与大章节标题 | Didot | 400 | 35/38/-1.1px | 接近原图高对比细衬线，原字体花饰更多，使用独立花饰首字母补足而不伪造整套字形。 |
| 花饰首字母 | Snell Roundhand | 400 | 41/38/-2px | 保留纤细铜版连笔感，仅作用于章节首字母；与原图定制连字的连接位置略有不同。 |
| 经历与教育小标题 | Baskerville | 400 | 23/25/-0.65px | 原图衬线更接近窄体书刊字，Baskerville曲线较温和，使用适度负字距保持宽度。 |
| 履历正文 | Arial | 400 | 10.4/11.8/-0.12px | 原图几何无衬线的a、圆形字腔更规整；Arial真实400保持可用性与相近信息密度。 |
| 角色说明 | Arial | 400 | 14.5/17/-0.2px | 原图略偏几何字体，当前选择更中性，保持原有字号层级。 |
| 标签日期和联系信息 | Arial | 400 | 8/9.5/0px | 原图标签较细且窄，采用真实常规体，不使用合成轻字重。 |
| 软件缩写 | Arial | 700 | 14/23/-0.6px | 仅以通用字母方块再现视觉密度，不复刻品牌图标字形。 |
| 中文替换 | PingFang SC | 400 | 10.5/14/0px | 中文没有拉丁Didot的细衬线对比；中文正文采用真实400，中文标题可用真实600并保留拉丁装饰标题。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布裁切安全区：正文至少距左右边28px（3.50%W）、上下边28px（2.47%H）；装饰允许到x=6px（0.75%W）、y=8px（0.71%H），不将此容差用于正文。②载体内排字安全区：身份卡右侧正文距卡右边20px（2.50%W），照片与正文间22px（2.75%W）；红纸左右约24px（3.00%W），教育纸左右18px（2.25%W），黑纸左右25px（3.125%W）；纸片撕边与正文至少16px（1.41%H）。③实物遮挡安全区：银饰保留x=7—139,y=10—101，即[0.009,0.009,0.165,0.080]；夹子保留x=189—285,y=328—416，即[0.236,0.290,0.120,0.078]；图钉保留x=612—655,y=136—207，即[0.765,0.120,0.054,0.063]；赭色胶带保留x=437—561,y=688—756；透明胶带保留x=589—774,y=980—1027。以上区域不放关键信息。默认姓名Alex Morgan保持单行；长姓名在身份卡右列分两行并增高卡片，教育纸下移或增加顶部留空。长履历增加实际行高所需纸张高度并同步下移邻近纸片和扩展画布，不隐藏、不截断、不自动缩小字体。

默认版本固定800×1132，对应1092×1545原图比例；不依赖外网、脚本或原图整幅背景。宿主按assets中的归一化source_crop为对应ref-asset注入裁片，cloud-sky必须作为25×352px左右的重复背景，其余槽用自身指定宽高显示，透明替换素材保持相同视觉占位。背景窄条重复可能出现周期性，生产版可仅替换该槽为同风格无缝云天。所有个人姓名、机构、联系方式与日期为虚构替换，软件名和技能术语仅为通用能力描述。默认西语文案按原图段落数量、约行数和密度配置，四段工作、三段教育、三组技能完整保留。英文替换尽量保持段内字数，中文用PingFang SC实际400，标题可600，正文行高提高至14px，避免强行追求相同字符数。姓名超过右列宽度时移除white-space:nowrap，以两行展示，身份卡与联系区随内容增高；同时将教育内容起点及下方纸片整体下移。工作或技能增长时增加对应纸片高度，夹子保持绑定纸片上沿，透明胶带绑定设计技能和语言之间的间隙；必要时扩展main高度，背景仍全画布铺满。不得用overflow:hidden、line-clamp、缩放文字或大面积留白消化替换内容。若必须交付原比例固定单页，应由编辑减少同义冗词或调整虚构文案长度，不牺牲既定字号与层次。

### 素材槽位

portrait只截取独立矩形人像照片，不含姓名、社交账号或纸卡文字，替换为相近肩部近景、深发色、略朝侧方的竖幅肖像即可。cloud-sky只取教育纸右侧无文字的纯云天窄条，重复铺满背景，保持原图云天印刷质感。metal-ornament为左上银蓝浮雕饰件，原图没有侵入头像和正文的窄边轮廓可保留；替换应为带透明通道的独立金属装饰。red-pin、binder-clip、phone-charm分别只取实物小区域；原裁片可能含紧贴物体的原底色，生产替换要求透明抠像。折纸、胶带、圆角、纸张撕边、条码及软件缩写全部用CSS/SVG，不进入图片槽。不裁取原图邮箱、网址、水印或其他个人资料。

- `cloud-sky`：纯云天区域镜像平铺验证背景；正式模板须提供独立云天材质；蓝天白云印刷质感的可平铺背景片；本槽为背景贴图，使用repeat而非cover。原裁片窄，建议生产版替换为同风格无缝云天，不能混入纸卡或文字。
- `portrait`：身份卡左侧竖幅肩部人像；约0.776宽高比矩形肖像，人物头顶距上沿约8%，肩部到下缘，背景偏灰蓝；无需抠像，不包含旁边履历文字。
- `metal-ornament`：左上银蓝色浮雕金属饰件与红色轮廓；同宽高比透明金属饰件；若使用原裁片，可保留紧贴轮廓的云天或白卡底，不得包含头像和文字。
- `red-pin`：教育纸顶端红色立体图钉；红色塑料图钉透明抠像，包含金属针尖和紧贴投影，底部针尖指向纸面。
- `binder-clip`：经历纸上沿黑色金属夹；黑色宽口夹透明抠像，上部带圆孔金属柄，下夹口水平；保留夹口高光。
- `phone-charm`：身份卡底部红色复古电话小饰件；透明红色电话小摆件或实物图标，不带号码、字母和原个人信息。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[展示字与书写字叠层](../layouts/layout-and-type.md#layout.display-script-overlap)、[叠层拼贴](../layouts/overlap-and-collage.md#layout.collage)、[圆角容器](../shapes/containers.md#shape.rounded)、[不规则撕纸边](../shapes/tickets-and-notches.md#shape.torn-paper)、[照片衬纸与胶带](../shapes/notes-and-paper.md#shape.paper-mount)、[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)、[彩色屏幕颗粒](../surfaces/paper-and-print.md#surface.screen-grain)。

整页结构与几何样式唯一维护在 [四区双栏 · 错落拼贴](../layouts/resume-full-page.md#layout.resume-paper-collage)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-paper-collage"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1132,
    "palette": {
      "background": "#419AC5",
      "text": "#111111",
      "primary": "#EA292E",
      "secondary": "#222326"
    }
  }
}
```

校准边界：天空背景使用独立资产槽位；验证以原图纯云天区域做CSS镜像平铺，不复制含履历的整图作为材质。

<a id="combination.resume-10"></a>

## 蓝色拍立得与技能贴纸简历

风格标签：二级：手账拼贴风 / 照片剪贴；二级：波普撞色风 / 波普拼贴。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1130px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

源图上部为满幅电蓝矩形，覆盖画布高度约42.12%；下部为浅灰白纸感底，占57.88%，不是浮动白卡。上部左侧在x≈9.78%、y≈6.73%放置窄白边人像相框，相框约35.33%画布宽；黑白照片位于相框上部，底部留白承接三枚分类胶囊、三条井号标签，右下蓝色署名胶囊压住照片与白边交界。三枚花形装饰分别跨越左上、右上和左侧中下边框。右侧姓名以两行细长连笔手写跨行叠排，第二行明显右缩；右上日期与两条错位白底职业签紧邻姓名但不覆盖正文。英文简介从照片下半部对应高度起排，右侧约43%画布宽，9行左右。下部为不等宽双栏，左栏x≈9.3%起、宽约36%，右栏x≈60.6%起、宽约30%；两栏间保留较明显空隙。左栏依次为教育、经历、联系方式、软件；右栏依次为硬技能、软技能、贴纸技能图谱、兴趣及外链文字。经历内部另分时间窄栏和内容宽栏。技能图谱有虚线选框、相互遮挡的多色花瓣贴纸、旋转字标，不能简化为列表。

形状与载体：照片框是无阴影直角白色纸框，照片底边上叠蓝色圆角署名胶囊。小分类签为低高度圆角胶囊。左上蓝花、右上粉花为六瓣扁圆花，左侧橙花为多齿圆形；均以SVG几何重建而非图片。职业签为两条不等宽、错位的直角白条，首条有蓝色小三角。技术技能区域包含黄色尖齿爆炸星、红色横向花团、绿色斜向软花、粉色小花、深蓝放射花、蓝色四叶长瓣与橙色多齿圆花，文字随所属贴纸旋转。底层蓝色细虚线矩形模拟选框，角点是小白心蓝边方块。兴趣为3列2行蓝色小圆角块，软件为5个宽度随内容变化的圆角块。

### 配色与质感

主色为高饱和钴电蓝，近似#2946EC，承担上部整块背景、下部标题、圆点、软件块与兴趣块。正文近黑#111111，上部文字及小条块为灰白#F4F4F0；纸底#F1F2F0带低强度灰纹理。贴纸辅色为橙#ED6634、粉#E74B93、绿#66B862、黄#F4DA3F、红#E83E46及更深蓝#1235DE。姓名并非纯白，呈浅灰蓝且自上至下逐渐降低明度与不透明度。

```json
{
  "palette": {
    "background": "#F1F2F0",
    "text": "#111111",
    "primary": "#2946EC",
    "secondary": "#E74B93"
  }
}
```

纹理：仅下半部浅灰纸底添加SVG feTurbulence细颗粒，opacity约0.085，纹理层位于内容背后，不叠加照片、姓名和正文；上半部电蓝保持平涂。纸感不包含额外暗角、折痕或白卡投影。

渐变／光场：只有姓名使用浅灰白至低透明蓝灰的垂直文字渐变，两行各自略有色阶变化，范围为姓名字形内部；背景、贴纸和蓝块均不做渐变。

### 字体组合

原图主体为近Arial/Helvetica的紧凑无衬线，章节标题约22px源尺寸、半粗至粗体，正文约8–12px源尺寸。姓名是高对比细笔画的拉长连笔英文，采用实际可用的Snell Roundhand 400，不使用假斜体或毛笔体；其字母连接和大写轮廓与原图不同，通过分行、右缩及字距控制复现气质，不压扁字形。章节采用Arial 700，正文Arial 400，细密项目采用Arial 400，白色职业签用Arial 700。所有文字明确font-synthesis:none。上部简介两端对齐并对少量关键词使用真实Arial bold italic；姓名为虚构Alex Morgan，不沿用源图文字。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 手写姓名 | Snell Roundhand | 400 | 109/0.93/-3px | 真实连笔细线字体；原图大写更长且有更显著回环，以两行错位和不同字号近似，不做字形拉伸。 |
| 章节标题 | Arial | 700 | 26/1.08/-0.55px | 原图可能更接近圆润的几何无衬线；Arial的a及端点更常规，保持真实粗体与原图紧凑宽度。 |
| 个人简介 | Arial | 400 | 13.4/1.14/0px | 接近原图中等字面无衬线，采用两端对齐匹配窄间距与9行文字密度。 |
| 时间与经历名称 | Arial | 400 | 12.7/1.16/-0.15px | 字重维持常规，不将单位名称误做粗体；略紧字距使日期列接近原图。 |
| 细密项目正文 | Arial | 400 | 8.9/1.22/-0.1px | 对应源图约8px细正文，保持微小蓝圆点与紧密多行排字。 |
| 职业签及软件块 | Arial | 700 | 15/1.1/0px | 使用真实700，职业白签更接近原图稍厚的无衬线。 |
| 贴纸内标签 | Arial | 400 | 9.5/1.03/-0.1px | 不模拟原图不确定的品牌字体，以短词、分行及倾角还原阅读尺度。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布内容安全区：常规文字距左右边缘至少74px/800=9.25%，底部至少57px/1130=5.04%，顶部首个白框距顶76px/1130=6.73%；满幅蓝背景可出血至0。②照片及装饰安全区：白框内照片左右至少13px/800=1.63%，顶19px/1130=1.68%；脸部建议置于画布x205–338px即25.63%–42.25%、y152–300px即13.45%–26.55%；蓝署名与橙贴允许覆盖衣发，禁止覆盖眼鼻口；照片标签留在y358–414px即31.68%–36.64%。③文字与碰撞安全区：照片右缘361px与简介起点379px之间18px/800=2.25%；下部左栏结束约447px、右栏起点484px之间37px/800=4.63%；章节标题与第一正文基线区域至少6px/1130=0.53%；图谱与兴趣标题至少12px/1130=1.06%。长姓名优先两行重排并下移职业签，不以横向压缩或伪造字重解决；长文案使上部蓝区和画布同步增高，下部采用自然网格流动，不使用overflow:hidden、line-clamp或缩小至不可读字号。

基准宽度固定800px，原比例整数高度1130px，以min-height保留基准且允许实际文案增长；蓝区初始476px，下部纸底最少654px。不得将800px内容机械压缩以容纳新增文字。照片框维持283×343px，portrait为257×259px，宿主使用assets给出的独立裁片填充，不将整张简历铺底；本模板不嵌入源照片。姓名常规按Alex / Morgan两行，长姓名可启用data-long-name='true'并将职业签降到姓名下方；需要更多姓名行时同步增加identity高度。中文可设data-language='zh'，姓名用林予安，采用实际PingFang SC 600而非虚构书法字体，正文用PingFang SC 400；翻译后的经历仍保留4、5、3项密度，窄栏中英文自然换行。简介增加时网格上区自动增高、分界和下部随之下移；其他段落在各自栏内自然推移，不隐藏文本。技能图谱短标保持每枚1–2行，较长内容应改用等义短名或增大局部贴纸和skill-board高度，不能把大段说明塞入花瓣。联系方式和链接仅作为无交互文字，域名统一example.com，号码为占位号。背景纹理仅存在纸底层；没有外部字体、网络资源、脚本或可点击外链。

### 素材槽位

唯一外部素材槽位为portrait，只截取白框内部黑白人物照片，不含白边、花贴、署名胶囊和履历文字。照片原本是矩形照片而非透明抠像，替换需竖向黑白半身/近景肖像，人物头部靠右、长发占据下部、左上保留抬手及深色衣袖，避免改成标准证件照。源图下缘署名覆盖少量照片，因此裁片底边止于署名胶囊之前，再由CSS相框和蓝胶囊恢复前后关系。所有花形、选框、图标、职业签和纸纹均由CSS/SVG承担，无需复杂装饰图片槽位。

- `portrait`：白框内部独立黑白人物照片裁片；避开照片下缘已叠加的署名文字。；竖向黑白近景生活肖像，深色衣发、头部向右倾斜、左上有手臂动作，建议最少520×520像素；不需要透明抠像。宿主以裁片填满portrait槽位，允许轻微纵向补足，面部不得被右下胶囊遮挡。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[展示字与书写字叠层](../layouts/layout-and-type.md#layout.display-script-overlap)、[三预设放射贴纸](../shapes/organic-shapes.md#shape.radial-sticker)、[叠层拼贴](../layouts/overlap-and-collage.md#layout.collage)、[圆角容器](../shapes/containers.md#shape.rounded)、[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)、[照片衬纸与胶带](../shapes/notes-and-paper.md#shape.paper-mount)、[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)。

整页结构与几何样式唯一维护在 [上下分区 · 下部双栏](../layouts/resume-full-page.md#layout.resume-profile-header)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-profile-header"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1130,
    "palette": {
      "background": "#F1F2F0",
      "text": "#111111",
      "primary": "#2946EC",
      "secondary": "#E74B93"
    }
  }
}
```

校准边界：渐变文字的背景绘制框增加0.25em下伸安全区，并以负下外边距保留两行基线；真实Snell Roundhand的Morgan下伸笔画曾被背景裁断，已以Canvas字体墨迹测量和实渲染检查。姓名字长变化时仍需检查实际墨迹。

<a id="combination.resume-11"></a>

## 巨型窄体与红色技能区简历

风格标签：二级：都市潮流风 / 字体潮流；二级：杂志编辑风 / 人物专题。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1132px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

固定800×1132画布。上部约73%以浅奶油纸色组织标题、人物与履历，下部朱红底座从y≈732开始覆盖至底边，实际占画高约35.3%；二者不是上下独立白卡。左上PORTFOLIO为约448×123的超窄黑色大刊头；右上人物在红色圆盘前，人物下沿和y≈290的通栏细红线对齐，红圆在人物之后、纸纹之前。刊头下方左侧是红色手写问候与两行黑色姓名，右侧约255px宽是小胶囊About Me和四行密排介绍，人物占据最右侧。Education为左对齐红底白字标牌，下面一行有两个不等宽教育项；Experience下方首排两栏，第二排只有左起的一条较宽经历，右下留白属于原图布局而非缺项。下部红底座有两个半圆肩、居中奶油标题、六个等间距软件图标及很细的百分比横条。最底部左侧奶油圆角项目卡内是两行极窄黑字和三张竖式封面，右侧联系方式直接排在红底上，并没有额外白卡。

形状与载体：右上直径约227px的纯红圆盘；贯穿上部的0.8px红线，左端有约4px空心方块；栏目标题小圆角红标牌；教育项和经历项左侧细红竖线；经历列表红色微圆点；下部宽800px、高约400px、顶角约56px的圆肩红色底座；六个90px级圆角图标框，奶油描边与柔和下投影；窄矩形进度条；底部约478×152px奶油圆角卡；项目标题间一条短红横线。全部可分离几何由CSS或内联SVG实现。

### 配色与质感

主背景为暖奶油#FFF3DF，文字为接近墨黑的#1B1C18，强主色朱红#E9383D用于圆盘、分隔线、标签、项目符号和下部大色块；次色#F0DCC3仅用于极淡等高线。下部标题、图标边框、进度条填充、联系文字沿用奶油色。软件槽位的蓝、橙、绿来自参考资产而不是整页配色扩展。

```json
{
  "palette": {
    "background": "#FFF3DF",
    "text": "#1B1C18",
    "primary": "#E9383D",
    "secondary": "#F0DCC3"
  }
}
```

纹理：只在上部奶油背景铺设低对比地形等高线。以两组CSS径向重复椭圆和轻微旋转实现，线宽约1.2px、间距约25px、红褐色透明度0.025—0.035。纹理层低于所有内容，不加在照片或文字表面；红色底座保持近纯色，项目卡也不叠加噪点。

渐变／光场：没有宏观颜色渐变。只有上部背景的重复径向渐变承担等高线绘制，覆盖上部y=0—786px；照片、圆盘、红底座和进度条均不另加渐变。

### 字体组合

原刊头像超窄、竖向拉长的重黑无衬线，圆弧紧而竖笔粗；姓名和MY PROJECT也属于同一压缩字形体系。使用实际Arial Black 900，并通过固定设计字面宽度与横向压缩接近原字形，不伪造字重。英文小标题与正文呈几何无衬线气质，以Futura medium近似；中文示例正文用实际PingFang SC 400，小标题与中文经历名用600。原图局部标题黑度略高于PingFang SC 600，不能通过font-synthesis伪加粗。问候采用Snell Roundhand 400的纤细连笔，较原图略规整。所有文字设置font-synthesis:none。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 超窄刊头 | DIN Condensed | 700 | 132/0.95/-7px | 实际DIN Condensed Bold窄体字款；保留高挑窄字面，不使用字形非等比缩放。 |
| 英文姓名 | DIN Condensed | 700 | 43/0.82/-2px | 实际DIN Condensed Bold窄体字款；保留高挑窄字面，不使用字形非等比缩放。 |
| 项目卡标题 | DIN Condensed | 700 | 59/0.85/-3px | 实际DIN Condensed Bold窄体字款；保留高挑窄字面，不使用字形非等比缩放。 |
| 手写问候 | Snell Roundhand | 400 | 26/1/0px | 保持可读的真实连笔文字，不以装饰曲线代替问候。 |
| 英文栏目标签 | Arial | 700 | 19/1.1/-0.5px | 保留红底标签的粗体层级。 |
| 教育年份 | Arial | 700 | 19/1.04/0px | 小年份前缀沿用10px、400字重、1.05行高。 |
| 中文教育与经历标题 | PingFang SC | 600 | 18/1.2/-0.55px | 教育标题沿用1.13行高与-0.6px字距；使用实际600字重，不合成加粗。 |
| 机构名称 | PingFang SC | 600 | 11.5/1.3/0px | 保持现有机构名称与正文的层级差异。 |
| 个人介绍 | PingFang SC | 400 | 10/1.18/0.02px | 保留四行中文介绍及实际常规字重。 |
| 教育正文 | PingFang SC | 400 | 11/1.12/0px | 保留原有教育信息密度。 |
| 经历正文 | PingFang SC | 400 | 10.5/1.32/0px | 中文继续使用实际400字重，不改动内容事实与列表结构。 |
| 默认西文正文与联系方式 | Helvetica Neue | 400 | 14/1.65/0px | 在原默认字体声明及contact-line实际规则中替换Futura 500，使用Helvetica Neue真实400常规字款；14px与1.65行高用于联系正文。 |
| 软件技能总标题 | Arial | 700 | 35/1.2/-1px | 保持奶油色技能标题的原有重量和位置。 |
| 联系标签 | Arial | 700 | 17/1.2/-0.4px | 仅Contact Me标签保留粗体，联系正文改用常规字重。 |
| 介绍胶囊标签 | Arial | 700 | 9/1.667/0px | 保持15px实际行高。 |
| 技能百分比 | Arial | 700 | 8/1.25/0px | 保持细进度条中的10px实际行高。 |
| 长英文姓名条件变体 | Arial Narrow | 700 | 30/1.02/-1px | 仅identity.is-long启用，保留自然换行规则。 |
| 中文姓名条件变体 | PingFang SC | 600 | 35/1.04/-1px | 仅identity.is-chinese启用，保留实际600字重。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①画布内容安全区：主体左边距50px、右边距25px，分别为宽度6.25%、3.125%；底部小字距底边至少43px，为高度3.80%，红底可出血至四边。②人物与叠层安全区：人物框x=529、y=48、w=246、h=242，对应[0.6613,0.0424,0.3075,0.2138]；关于区右界约493px，与人物框间保留36px，即宽度4.5%；脸部关键区域建议落在x=569—680、y=53—173，不在其上叠字。③文字与组件内部安全区：经历正文与竖线至少11px即宽度1.375%，两栏至少28px即3.5%；下部项目卡四周至少20px，卡宽占比4.18%；每个图标与百分条至少11px即画高0.97%。长姓名在205px姓名区按词或汉字换为2—3行，不继续缩小字；介绍、经历增长时增加所在行高度，推动后续内容和红色底座向下，画布随内容增高，不用overflow隐藏正文。

参考模式固定宽800px，基准高1132px，使用min-height保留源图比例并允许真实内容增高；上部最小高732px、下部最小高400px。保留刊头英文PORTFOLIO及底部MY PROJECT可维持原字形气质，中文姓名用林予安并给identity添加is-chinese，长英文姓名添加is-long，取消设计字面压缩后按词换行。正文按原图介绍四行、教育一行两项、经历首排4/3条和次排2条各两行的密度替换，不以字符数强求中英文相同。删除about内部强制分行span即可改为自然换行；行数增加时masthead及正文随内容增高，人物继续贴齐刊头区下沿，后续栏目及红底座顺次下移。不要固定整页height、隐藏文字或继续缩小字号。软件比例可通过--value及可见百分数同步替换。项目封面按三槽独立替换，保持左中窄、右侧略宽的视觉比例；联系信息允许断行并增高红底。输出不依赖网络、脚本、外部字体或原图整页背景，资产槽由宿主填充。

### 素材槽位

人物槽位仅负责紧贴人物的照片及抠像边缘，不包含刊头、姓名或介绍。原人物位于红圆与奶油背景前，因此参考裁片可保留紧贴人物的原背景，但可复用版本必须换成透明背景半身抠像，保留黑色立领与西装的暗轮廓，避免矩形照片遮挡独立红圆。六个软件标志分别建槽，不把百分比、进度条或外围奶油框并入裁片。三张封面分别建槽，仅负责封面视觉，卡片、MY PROJECT和红横线均由CSS重建；正式替换应使用虚构出版物封面，不沿用原图作者、机构或水印。联系方式中的三个线性图标由简单内联SVG绘制，无需真实图标资产。

- `portrait`：右上黑色西装半身人物抠像；默认注入透明半身人像并使用CSS红圆；如资产已含完整红圆与人物，根节点设置data-portrait-mode="composite"关闭重复红圆，采用257×251图窗。两种模式不可重复叠圆。
- `software-ps`：第一枚蓝色图像编辑软件标志，不含外框及进度条；近方形软件标志图像，内部深蓝底与浅蓝字，外部圆角奶油框由CSS提供。
- `software-ai`：第二枚橙色矢量设计软件标志；深棕底橙字近方形标志，独立素材。
- `software-video`：第三枚黑色交叉带状视频编辑标志；白底黑色标志，保持中心位置和留白，不附带文字说明。
- `software-word`：第四枚蓝色文档软件标志；含蓝色叠层和白色W的方形软件标志。
- `software-slide`：第五枚橙色演示软件标志；含橙色叠层和白色P的方形软件标志。
- `software-sheet`：第六枚绿色表格软件标志；含绿色叠层和白色X的方形软件标志。
- `project-cover-a`：项目卡内左侧蓝紫色竖版封面；虚构科普或校园作品封面，蓝紫主色、上方密集小标题、下方人物或场景小图；不得含原个人资料、水印。
- `project-cover-b`：项目卡内中间青绿色竖版封面；虚构校园读物封面，青绿底与人物插图，构图密度接近参考。
- `project-cover-c`：项目卡内右侧米黄绿色儿童插画封面；虚构思维练习册封面，米黄上区与绿色下区，卡通儿童主角，无真实机构或作者资料。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[背景分区与跨界内容](../layouts/overlap-and-collage.md#layout.cross-zone-sections)、[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[对齐标签量尺：平条、框条与圆点](../layouts/grid-and-alignment.md#layout.labeled-meter)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)、[叠层拼贴](../layouts/overlap-and-collage.md#layout.collage)、[圆角容器](../shapes/containers.md#shape.rounded)、[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)。

整页结构与几何样式唯一维护在 [纵向三段 · 通栏分区](../layouts/resume-full-page.md#layout.resume-three-zones)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-three-zones"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1132,
    "palette": {
      "background": "#FFF3DF",
      "text": "#1B1C18",
      "primary": "#E9383D",
      "secondary": "#F0DCC3"
    }
  }
}
```

校准边界：刊头、姓名和项目标题改用真实DIN Condensed Bold窄体，取消字形非等比缩放。验证采用包含原完整红圆与人像的局部合成图窗，并启用composite模式关闭重复圆；不是整页背景。默认透明人像模式的主体裁切须在正式素材注入后再验。封面示例来自参考局部，仅验证数量比例与遮挡，库中不保存原封面。

<a id="combination.resume-12"></a>

## 蓝色编辑选框与时间轴简历

风格标签：二级：理性信息风 / 瑞士网格。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1131px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

浅灰整页底，左上是宽约469px、高101px的虚线文字选框，框外右上有钢笔路径小装饰；姓名与职业两行均在框内。右上角蓝色弥散圆场及环形职业文字被画布上、右边缘裁切，并非人物照片。联系信息在约y=170px处横向分成四组，下面是一条完整细分隔线。自述区横跨页面，标题后有三段正文。约y=401px开始形成左右双栏：左栏约288px，承载教育、软件技能和其他技能；右栏约415px，承载六段工作经历，最后两段正文显著密集。左右各自的星形节点与细竖线形成两条独立时间轴。底部y≈1061px有通栏白色组合条，左下蓝青色弥散圆场在白条上方叠压，页脚文本则位于装饰前方。整页无照片、无独立白卡，灰底一直延伸到内容之间。

形状与载体：标题选择框用1px灰虚线与四个5px蓝色控制点构成，右上关联一条细贝塞尔路径、端点和深色钢笔尖。右上装饰含白色四芒星与细十字线，环字沿圆弧排布并被画布裁切。章节前缀是水平短蓝线，About me没有前缀。教育和工作时间轴是细灰竖线、四芒黑星节点以及同底色节点垫片。技能区八个约51px黑色圆角方块排列为四列两行，内部是白色两字母软件缩写。页脚使用不带圆角的通栏白条。

### 配色与质感

页面基底约#ECECEC，正文与细图形近#101111，章节标题及选框控制点用高饱和电蓝#1046DC。右上及左下装饰以#4389FF到#67D3E6形成柔和发光边缘。页脚底条近#FFFFFF，正文小字与线条使用#343434和#777777。蓝色承担标题和编辑软件语义，不铺满正文栏目。

```json
{
  "palette": {
    "background": "#ECECEC",
    "text": "#101111",
    "primary": "#1046DC",
    "secondary": "#62C7EF"
  }
}
```

纹理：原图灰底视觉上接近无纹理的平滑纸面。本复现不人为添加噪点或纸纤维，背景纹理强度为0；模糊仅作用于两个背景色场，不作用于文字、图标或时间轴。

渐变／光场：右上圆场约以(746,26)为中心、半径132px，电蓝中心向蓝青边缘及透明灰底渐隐，范围横跨x≈615至画幅右侧以外。左下圆场约以(-23,1094)为中心、半径150px，从蓝色到青色再透明，部分覆盖白色页脚条左端。无正文、姓名或卡片渐变。

### 字体组合

原图姓名为宽展、圆形O明显的几何无衬线粗体，章节标题亦有类似几何结构，正文呈较宽的现代无衬线形态。以实际可用Futura medium表现姓名、章节标题和主体正文，利用字号与轻微字距区分层级，不虚构Futura粗体；教育及工作职称使用Arial 700获得真实粗字重。职业行使用Helvetica Neue 400，工作细项使用Arial 400/700。姓名由原约44px视觉高度换成800px画布上的43px字号，英文示例长度稍短，采用正常字距与更宽框内留白，而非伪拉伸。正文主区约15px，右栏职责约10.7px，维持原图不同密度层次。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 姓名 | Futura | 500 | 43/48/0.6px | 保留实际Futura Medium及现有姓名尺寸；本例不是Didot姓名，无需替换为衬线字体。 |
| 正文默认 | Helvetica Neue | 400 | 15.4/18.5/0.1px | 直接修正根容器默认字体为真实Regular字款，不再以Futura Medium充当正文默认。 |
| 职业副标题 | Helvetica Neue | 400 | 20/25/0.3px | 保留现有常规字重与尺寸。 |
| 章节标题 | Helvetica Neue | 500 | 27/34/0.7px | 使用实际Medium较宽字面，略增字距；不合成粗体、不横向拉伸，保留标题行盒及蓝色短线。 |
| 自述正文 | Helvetica Neue | 400 | 15.4/18.5/0.1px | 继承修订后的正文默认字体，移除段落500字重；保留三段文案、字号、行距与段距。 |
| 教育与工作职称 | Arial | 700 | 15.2/19/-0.12px | 保留真实Arial Bold及现有信息层级。 |
| 经历日期 | Helvetica Neue | 400 | 14.6/18/0 | 保持原规则。 |
| 职责细项 | Arial | 400 | 10.7/11.8/-0.08px | 保留右栏密度，强调部分继续使用真实Arial 700。 |
| 其他技能 | Arial | 700 | 15.2/26/0 | 保留现有规则。 |
| 软件缩写 | Arial | 700 | 25/51/-0.5px | 以正常宽度Arial Bold替代Arial Narrow，保留黑色方块尺寸和四列两行排列。 |
| 联系方式 | Arial | 400 | 11.8/16/0 | 保持原规则。 |
| 页脚引导句 | Futura | 500 | 13/18/0.2px | 保留局部展示字体，不作为正文默认。 |
| 页脚网址 | Arial | 400 | 10.8/15/0 | 保持原规则。 |
| 右上职业环字 | Helvetica Neue | 400 | 14/normal/1.1px | 减轻为真实Regular，反转圆路径并调整起点，使底部字形倒向阅读，保留边缘裁切。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

三类安全区：①外缘文字安全区左38px/0.0475W、右38px/0.0475W、顶部40px/0.0354H；正文底界建议1030px/0.9107H，与页脚至少间隔30px/0.0265H。②组件内部安全区：姓名框左右21px/0.0263W，上10px/0.0088H、下12px/0.0106H；时间轴到正文18px/0.0225W；左右栏净间隔23px/0.0288W；技能方块间隙9px/0.0113W。③装饰和前后关系安全区：标题正文右界486px/0.6075W，钢笔图形位于496—542px/0.6200—0.6775W，二者不重叠；右上圆环限制在x≥633px/0.7913W且y≤151px/0.1335H，联系条位于其下；左下色场可占x≤130px/0.1625W、y≥975px/0.8621H，但页脚文字由x=130px开始并置于其前景。长姓名不缩小，先将框扩至570px，再换行并自动增高页头；正文增长使用正常流抬高后续栏目与页脚，禁止隐藏和硬截断。

标准画幅800×1131，对应原图1200×1697等比取整。主元素采用min-height而非固定裁切高度，默认密度按三段自述、四段教育、八个技能块、六段工作经历设置。姓名使用Alex Morgan，不抄录原图私人信息；其他经历均为虚构。中文替换时改main的lang为zh，实际使用PingFang SC 400/600及Source Han Sans SC 700，不合成字重；中文自述以三段、每段约两行为目标，右栏适当增加行高，画布随内容增高。长姓名启用data-long-name='true'，框宽上限570px，超出后自然换行，联系条及后续内容保持正常流下移；职业行也可换行。长联系方式或页脚启用data-fluid-copy='true'，允许组内换行，保持四组结构和可读字号。正文只自然换行，不使用line-clamp、固定高度遮挡或字形横向压缩。左右栏仍维持288px与剩余413px、23px栏距，扩展内容时不将右下高密度职责改成宽松通用卡片；页脚随内容增长后移，两个弥散色场分别固定在画布右上和左下。所有网址均为不可点击文本，无外部网络、脚本、字体下载或原图嵌入。

### 素材槽位

本图没有人物或必须保留的真实照片；钢笔尖、联系方式符号、四芒星、控制框及软件缩写均可用短SVG和CSS准确重建，故assets为空，也不创建无意义portrait槽位。右上原环形标语改为虚构职业描述，页脚与联系方式全部使用example.com及占位号。若后续另加人物图片，应视作新增版式而不是本组合的默认替换。


模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[编辑器选框与控制柄](../shapes/cards-and-panels.md#shape.editor-selection)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)、[圆角容器](../shapes/containers.md#shape.rounded)、[四角星芒](../shapes/organic-shapes.md#shape.sparkle)、[弥散光晕](../surfaces/diffuse-light.md#surface.diffuse-field)。

整页结构与几何样式唯一维护在 [简介双栏 · 时间轴](../layouts/resume-full-page.md#layout.resume-timeline-columns)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-timeline-columns"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1131,
    "palette": {
      "background": "#ECECEC",
      "text": "#101111",
      "primary": "#1046DC",
      "secondary": "#62C7EF"
    }
  }
}
```

校准边界：仅替换现有实际规则，不追加全局字体覆盖。正文减重，标题与软件字母改用较宽真实字面；姓名、双栏、时间轴、文案与页脚位置不重设计。右上环字反向并调整偏移，圆场补回蓝—青—透明过渡。左下删除重复底层色场，仅保留叠压白条的前景色场，将其承载层向上扩大220px，消除页脚容器顶缘硬切；页脚文字仍在色场前方。原assets为空，不新增或移除图像槽位，不用整图替代CSS。

<a id="combination.resume-13"></a>

## 橙色颗粒与书写网格简历

风格标签：二级：都市潮流风 / 字体潮流；二级：先锋实验风 / 解构排版。

产物：简历／个人履历／作品集介绍页。布局范围：整张单屏。基准宽800px，高1131px，按参考比例近似；不是社媒长图或通用详情页布局。

### 布局与背景、照片、文字关系

固定800×1131画布。页顶为约57px高的作品集提示条，横线下是约291px高的主视觉区；左侧x=57和右侧x=743的细线贯穿页顶至联系人条，其中右侧形成57px宽的竖排边栏。主视觉不是卡片：巨大细线花体G与两行粗斜体职业标题相互叠压，标题右侧为圆角人像窗，姓名贴在第二行下沿。联系人条位于y=348—406，左235px橙色渐变标题块，右侧并排三组联系方式。主体保留左侧约57px的竖向线框空间，Bio标题在x=85，正文及经历统计从x=295开始。Experience位于y≈596，三段经历采用左公司及职位、中央正文、最右日期三列，并由浅橙横线、左侧竖线和四角星组织。底部Competences在x=85起，两个橙色矩形分类标签分别位于x≈131、422；右侧有三圈细线椭圆装饰。底部另有被画幅切去部分的巨大浅灰斜体背景字，但不代替实际技能内容。

形状与载体：两条主要纵向细线、页顶横线及通栏联系人边线；圆角约12px的人像窗；巨大线性花体G；左上八向星、三枚联系人小星、经历节点四角星；作品集click字样的四角选框与小方块指针；姓名及公司名的斜切橙色纸条；两枚细橙色斜向箭头；右下三枚错位椭圆。所有选框、贴纸、箭头和线性装饰用CSS或SVG，而非照片裁片。

### 配色与质感

纸面暖白约#F6F3EF，文字及结构线为炭黑#292A28，主要强调色为珊瑚橙#F3663C。左上和左下由浅黄#F4C975过渡至橙色，右侧主视觉下部有少量粉橙色渗染；联系人右半区为很淡的中性灰。橙色用于姓名斜切贴条、公司名贴条、图标、箭头、技能标签和装饰圈；大面积暖色仅属于背景而非内容卡片。

```json
{
  "palette": {
    "background": "#F6F3EF",
    "text": "#292A28",
    "primary": "#F3663C",
    "secondary": "#F4C975"
  }
}
```

纹理：源图背景呈全页细纸纤维颗粒，暖色渗染区域颗粒更显著。复现中仅在最底层背景使用固定seed的SVG feTurbulence，整体透明度约0.085，并辅以约0.06的不均匀低频纹理；不对人像、文字或标签叠加噪点滤镜。右下原图可见浅灰压印般的大号字与朦胧纵向影，使用低透明文字和多层线性渐变近似其轻质背景角色。

渐变／光场：背景左上约x=0—350、y=0—175有橙黄径向漫染，右边x=720—800、y=205—370有窄粉橙漫染，左下x=0—275、y=805—1131有橙黄上升式漫染。联系人左区用由暖白到橙色的水平渐变，联系人右区用透明至浅灰的弱渐变。人像和前景正文不施加渐变。

### 字体组合

源图正文是单层a、圆润低对比的几何无衬线，接近几何Grotesk；使用实际可用Futura medium承接，正文按其真实medium字面和实际注册字重请求，不将Medium猜记为400，也不制造600假字重。职业标题为很重、紧凑、明显前倾的无衬线，样本采用Arial Black 900正体，不用skewX模拟斜体，也不请求未核验的Arial Black italic；需要保留参考的前倾字形时，另选真实重斜体并按当前字体流程核验后试排。花体G的主要气质来自极细的长弧和大幅回转，用SVG路径而非难以一致的花体字体重建。正文局部使用Arial 400以保障数字、标点与邮箱可读，标签使用Arial 700。原图顶部标题属于紧密交叠结构，不应替换为常规上下标题模板。

原字体未确证；以下为本机可用替代，必须加载真实字款，禁止合成字重。

| 角色 | 替代字体 | 字重 | 字号／行高／字距 | 差异 |
|---|---|---|---|---|
| 职业主标题 | Arial Black | 900 | 59/0.88/-3.2px | 源图较紧且为真正重斜体；此处保留900正体字面，明确存在姿态差异，不伪斜或横向压缩。精确复刻需另选并核验真实重斜体。 |
| 章节标题 | Helvetica Neue | 400 | 28/1.12/-1px | 原图几何无衬线的圆形字腔更明显；本机Futura Medium视觉偏厚，改用真实Helvetica Neue Regular保持正文轻重和展开宽度。 |
| 履历正文 | Helvetica Neue | 400 | 13.5/1.14/-0.25px | 原图几何无衬线的圆形字腔更明显；本机Futura Medium视觉偏厚，改用真实Helvetica Neue Regular保持正文轻重和展开宽度。 |
| 姓名及公司标签 | Arial | 700 | 14.5/1.05/-0.4px | 实际Arial Bold的a为双层结构，较原图稍传统，但标签小尺寸下轮廓和重量接近。 |
| 经历数字 | Arial Black | 900 | 53/1/-3px | 数字4形态略有差别，保留宽厚的大数字和小字贴靠关系。 |
| 联系方式与微型文字 | Arial | 400 | 10/1.1/-0.15px | 用于小号信息与日期，数字可读性优先；源图圆润程度稍高。 |

800px是视觉试排基准，字号为px；行高按记录值及模板声明使用。其他设备需确认字体可用性，缺失时使用已授权字体重新校准，不把本机local声明视为跨系统保证。

### 安全区与适配

画布结构安全区：普通内容限制x=57—743，即横向0.0713—0.9288，底部至少20px即高0.0177；允许装饰花体、背景灰字和外沿竖排说明突破普通内容区。文字安全区：主体左标题起点85px即0.1063，正文起点295px即0.3688，正文最右不超过743px即0.9288；经历正文与日期间至少14px即宽0.0175；联系人每栏内侧至少8px即0.01。照片安全区：槽位584×126起、128×170大小，占画布[0.730,0.1114,0.160,0.1503]；头像重点应位于槽内横向15%—85%、纵向8%—80%，图窗与职业标题留至少12px即宽0.015。长姓名在姓名贴条内按词换行，允许贴条及主视觉增高；长邮箱优先在@或句点处断行；长公司名与正文采用自然换行和minmax(0,...)网格，增加经历行高与整页高度，禁止遮罩正文或整体缩字。

基准宽度固定800px，源比例整数高度1131px，以min-height保证默认单页且不裁切内容；默认文本密度按英文三行简介、第一段经历约七行、第二段约四行、第三段约三行设计。姓名使用Alex Morgan，并保留贴条的位置而不为短姓名人为增加空白字距。替换更长姓名或正文时给main设置data-adapt="flow"，主视觉增加22px，正文与经历由网格自然撑高，画布随实际内容增高；不要固定max-height、line-clamp或overflow:hidden来遮正文。中文正文设置lang="zh"，使用PingFang SC 400和实际600章节标题，按视觉行数重写而不是按英文字符数直接粘贴；主体字号不随文字长度缩小。主职业文字如需换成中文，应另行设计两行标题并保留花体曲线的装饰层关系，不能强行把中文套进RAPHIC字宽。照片只由宿主填充portrait槽位，建议object-fit:cover等效展示；CSS圆角始终由模板提供。画布背景、边栏轴线和人像保持原位，延长仅向正文底部发展，底部灰字、漫染与圈线随所属容器延续。

### 素材槽位

仅保留portrait照片槽位，裁切独立人像窗内部，不包含职业标题、姓名条或旁边竖排文字。该原图是有背景的矩形肖像，不属于透明抠像，替换使用竖幅、头肩构图且人物略向右倾的照片即可。原图衣服内自然出现的细节属于照片资产，库HTML不存储原照片及个人水印。花体笔画、星号、教育帽、圈线、选择框、斜切标签均归CSS/SVG职责。

- `portrait`：右上圆角人物照片，保留原图头肩尺度及有背景的近景关系。；竖幅约0.753宽高比的真实头像，头部占照片宽度约65%，人物下部延伸至胸前；不需要透明抠像，不含履历文字、边框或贴纸。

模板不携带参考人物、联系方式、水印或源图裁片。`data-asset-slot`由调用方注入符合比例与透明要求的资产；无素材不能把空槽称为组合效果已完成。验证时的参考裁片仅用于核对关系，不是默认交付素材。

### 原子对应与模板

[日期机构说明行与时间线](../layouts/grid-and-alignment.md#layout.date-event-row)、[同轴编辑式分隔线](../layouts/grid-and-alignment.md#layout.editorial-rules)、[展示字与书写字叠层](../layouts/layout-and-type.md#layout.display-script-overlap)、[三预设放射贴纸](../shapes/organic-shapes.md#shape.radial-sticker)、[编辑器选框与控制柄](../shapes/cards-and-panels.md#shape.editor-selection)、[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)、[章节眉线](../layouts/layout-and-type.md#layout.section-masthead)、[文字描边](../layouts/layout-and-type.md#text.outline)、[轻纸纹](../surfaces/paper-and-print.md#surface.light-paper)、[弥散光晕](../surfaces/diffuse-light.md#surface.diffuse-field)。

整页结构与几何样式唯一维护在 [横向分行 · 标签对齐](../layouts/resume-full-page.md#layout.resume-editorial-rows)；本组合文件只维护视觉样式。读取布局的主结构和布局样式，再追加本组合视觉样式；只借布局时不加载本组合视觉层。上面的局部原子是可选改版入口，不叠加全部默认样式。

```json
{
  "dependencies": ["layout.resume-editorial-rows"],
  "overrides": {
    "reference_width_px": 800,
    "reference_height_px": 1131,
    "palette": {
      "background": "#F6F3EF",
      "text": "#292A28",
      "primary": "#F3663C",
      "secondary": "#F4C975"
    }
  }
}
```

校准边界：正文从实际Futura Medium改为Helvetica Neue Regular，保留网格拓扑、分区、书写穿插与橙色渐变位置。手绘G与纸面颗粒为可编辑近似，不声称与原图字形和纤维逐像素一致。
<a id="combination.cold-blue-terminal-chapters"></a>

## 冷蓝终端章节组

风格标签：二级：未来科技风 / 赛博未来。

产物：社媒长图；粒度：连续章节（导语＋前两章）。适用于暗色终端信息说明；不把整页首屏视为已覆盖。

```json
{
  "dependencies": [
    "shape.chamfered-notched-panel",
    "shape.open-chamfer-brackets",
    "shape.slanted-strip",
    "layout.external-terminal-title",
    "surface.scanline",
    "surface.sparse-glitch-bars",
    "surface.type-channel-offset"
  ],
  "asset_slots": {
    "story": {
      "role": "第一章独立截图",
      "ratio": "496/276",
      "required": true
    },
    "route": {
      "role": "第二章独立截图",
      "ratio": "496/284",
      "required": true
    }
  },
  "font_binding": {
    "css_family": "CyberSourceHan",
    "catalog_id": "chinese-0010-font-4f8d31775b64",
    "face": "SourceHanSansSC-VF.otf",
    "title_weight": 700,
    "body_weight": 400,
    "status": "候选替代；本地文件已加载，原字体未知"
  },
  "scope": "导语与两个连续信息章节，不包含首屏Logo/日期或完整长页"
}
```

依赖：[切角凹口双轨面板](../shapes/cards-and-panels.md#shape.chamfered-notched-panel)；[开放切角四角括框](../shapes/cards-and-panels.md#shape.open-chamfer-brackets)；[文字独立斜切题带](../shapes/cards-and-panels.md#shape.slanted-strip)；[框外避字终端章节标题](../layouts/layout-and-type.md#layout.external-terminal-title)；[正文后置薄扫描线](../surfaces/paper-and-print.md#surface.scanline)；[确定性稀疏背景故障条](../surfaces/paper-and-print.md#surface.sparse-glitch-bars)；[真实字形轻通道错位](../surfaces/diffuse-light.md#surface.type-channel-offset)。

### 绑定与适配

唯一共底为暗蓝灰加24px淡网格与固定稀疏故障；导语仅四角与背后局部蓝光。副题条是可选组件实例，原型在首屏，本局部测试将其置于导语后，不声明逐像素还原原次序。每章为框外标题→双轨轮廓→内阅读面→眉标和图文流；先图后文/先文后图分别保留。

参考宽658px、侧距28px、章间48px；框角22、外净空22、阅读内边30；正文24px/1.55/400、标题36px/1.3/700，窄幅420px按CSS显式减小边距和题字级。正文增长只增高，不拉伸切角或裁掉文字。复制通道文字必须随主文字同步，且aria-hidden。

内阅读面顶部蓝白亮带在约65px内转暗灰紫；扫描3px周期/.055，内容在扫描上方；内缘光6px/.29、外光6px/.14。导语径向蓝光独立；主底、面板和图像不共享opacity。原图复杂故障仅作稀疏近似，不额外给截图加扫描或滤镜。

SLOT:story、SLOT:route必须替换为实际独立截图（无外部章节标题/面板烘焙），保留原比例、不裁人脸/UI关键信息。示例两图来自参考裁片，仅留任务验证目录，未作为库默认资产。正式使用先从字体目录解析真实资源并用@font-face绑定CyberSourceHan，等待document.fonts.ready后验字重和缺字；该别名不是系统字体，不静默以sans-serif冒充已加载。

加载顺序：七个原子的css各加载一次，再加载本组合css；组合只定义排版、配色、阅读面渐变和独立内缘光，不复制七个机制。真实依赖已在HTML引用ct-panel、ct-brackets、ct-strip、ct-title、ct-scan、ct-glitch、ct-offset及其子节点。唯一共底为#18232c，24px淡网格只在最外层绘制；shell半透明、阅读面半透明渐变、阅读面光效分别绑定，不用纯色卡遮盖共底，也不默认backdrop-filter。源宽658px时左右各28px，章框602px；外净空22px、阅读面内距30px，截图净宽约496px。正文默认24px/1.55、400，不发光；标题CyberSourceHan 700，正文CyberSourceHan 400；由外部harness加载已筛选的真实字体文件，必须在document.fonts.ready且确认字体成功后截图，sans-serif仅异常回退，不接受用Arial替代验收。不输出@font-face、CDN或外部依赖。槽位SLOT:story与SLOT:route由harness替换成对应本地截图地址，当前仅占位，不代表已提供素材；默认16:9 contain保全画面，可在实际图片元素上按真实截图设置 aspect-ratio 或使用 auto，避免裁掉UI。章节标题均在外壳之前的正常流中，长标题自然换行带动框下移；正文无截断、无锁定高度，每章超过100中文字符。多实例使用时为两个标题id及aria-labelledby添加唯一实例前缀。组合参数包括gutter=28px、chapter-gap=48px、reading-pad=30px、body-size=24px、body-leading=1.55、grid=24px、grid-alpha=.055；阅读面清晰边固定1px，edge-blur默认6px，允许0–8px，勿超8px；edge-alpha与outer-glow-alpha设0可独立关闭光，不影响外壳或阅读面。scan-enabled、glitch-enabled、offset-enabled分别设0关闭对应装饰；grid-alpha设0关闭网格。小于520px时缩减外净空与阅读内距，正文仍保留24px，靠自然增高而非整体缩放适配；建议最小容器宽320px，更窄需调整凹口宽和标题尺寸。此为章节组而非整页首屏，未声称通过组合实渲染验证；需在真实字体、两张槽图和目标浏览器下复核双轨细线与透明层次。

```css
.ct-chapters{width:min(100%,658px);box-sizing:border-box;margin-inline:auto;color:#f5f7fa;font-family:'CyberSourceHan',sans-serif;font-weight:400;background-color:#18232c;background-image:linear-gradient(to right,rgba(164,190,206,var(--ct-chapters-grid-alpha,.055)) 1px,transparent 1px),linear-gradient(to bottom,rgba(164,190,206,var(--ct-chapters-grid-alpha,.055)) 1px,transparent 1px);background-size:var(--ct-chapters-grid,24px) var(--ct-chapters-grid,24px);--ct-glitch-cyan:rgba(111,195,218,.22);--ct-glitch-violet:rgba(161,124,184,.16);--ct-glitch-p1:3% 4%;--ct-glitch-p2:98% 17%;--ct-glitch-p3:0% 39%;--ct-glitch-p4:100% 60%;--ct-glitch-p5:2% 81%;--ct-glitch-p6:99% 96%;}.ct-chapters,.ct-chapters *{box-sizing:border-box;}.ct-chapters__flow{padding:var(--ct-chapters-top,36px) var(--ct-chapters-gutter,28px) var(--ct-chapters-bottom,38px);}.ct-chapters__intro{width:min(100%,470px);margin:0 auto 28px;--ct-brackets-space:38px;--ct-brackets-arm:48px;--ct-brackets-cut:16px;--ct-brackets-line:2px;--ct-brackets-color:#91b8cb;background:radial-gradient(ellipse at 50% 52%,rgba(80,133,181,.24),rgba(64,111,153,.09) 47%,transparent 73%);}.ct-chapters__intro .ct-brackets__body{font-size:var(--ct-chapters-intro-size,23px);line-height:1.6;text-align:center;}.ct-chapters__intro p{margin:0;}.ct-chapters__strip-row{text-align:center;margin-bottom:var(--ct-chapters-before-first,38px);}.ct-chapters__strip{width:min(100%,350px);font-size:25px;font-weight:700;line-height:1.35;--ct-strip-fill:linear-gradient(105deg,rgba(49,77,110,.8),rgba(48,71,99,.4));--ct-strip-end-color:#98c6db;--ct-strip-text-color:#f4f8ff;--ct-strip-cut:22px;--ct-strip-height:50px;}.ct-chapters__chapter+.ct-chapters__chapter{margin-top:var(--ct-chapters-chapter-gap,48px);}.ct-chapters .ct-title{--ct-title-size:clamp(25px,5.47vw,36px);--ct-title-weight:700;--ct-title-leading:1.3;--ct-title-gap:12px;--ct-title-panel-gap:10px;--ct-title-max:490px;--ct-title-relative-max:calc(100vw - 110px);--ct-title-line-color:rgba(166,202,213,.77);}.ct-chapters .ct-title__text{font-family:'CyberSourceHan',sans-serif;font-weight:700;}.ct-chapters .ct-offset{--ct-offset-x:1px;--ct-offset-y:0px;--ct-offset-cyan:rgba(94,214,243,.6);--ct-offset-violet:rgba(198,140,209,.43);}.ct-chapters__panel{width:100%;--ct-panel-corner:22px;--ct-panel-notch:7px;--ct-panel-top-width:374px;--ct-panel-bottom-width:146px;--ct-panel-notch-width:100px;--ct-panel-line:1px;--ct-panel-rail-gap:6px;--ct-panel-outer-space:22px;--ct-panel-inner-space:0px;--ct-panel-line-color:rgba(137,203,220,.88);--ct-panel-inner-line-color:rgba(111,159,174,.68);--ct-panel-shell:linear-gradient(115deg,rgba(116,178,197,.19),rgba(102,158,178,.045) 30%,rgba(64,111,131,.08) 65%,rgba(123,187,199,.16));}.ct-chapters__reading{min-width:0;border:1px solid var(--ct-chapters-reading-edge,rgba(111,211,243,.8));background:linear-gradient(to bottom,rgba(148,200,225,.23) 0,rgba(102,151,183,.12) 12px,rgba(40,54,72,.48) 55px,rgba(22,31,46,.68) 100%),linear-gradient(110deg,rgba(64,84,109,.45),rgba(30,41,58,.34) 55%,rgba(53,70,89,.39));box-shadow:inset 0 0 var(--ct-chapters-edge-blur,6px) rgba(113,205,243,var(--ct-chapters-edge-alpha,.29)),0 0 var(--ct-chapters-edge-blur,6px) rgba(75,164,202,var(--ct-chapters-outer-glow-alpha,.14));--ct-scan-period:3px;--ct-scan-line:1px;--ct-scan-color:rgba(195,227,246,.055);}.ct-chapters__reading-content{padding:10px var(--ct-chapters-reading-pad,30px) 30px;}.ct-chapters__eyebrow{margin:0 0 24px;margin-left:calc(12px - var(--ct-chapters-reading-pad,30px));font-size:12px;font-weight:400;line-height:1.4;letter-spacing:.7px;color:#c2e7f5;}.ct-chapters__eyebrow span{padding-left:9px;letter-spacing:3px;color:#90c5dc;}.ct-chapters__copy{font-size:var(--ct-chapters-body-size,24px);font-weight:400;line-height:var(--ct-chapters-body-leading,1.55);text-align:left;overflow-wrap:anywhere;word-break:normal;color:#f5f7fa;text-shadow:none;}.ct-chapters__copy p{margin:0 0 16px;}.ct-chapters__copy p:last-child{margin-bottom:0;}.ct-chapters__image{margin:0;min-width:0;}.ct-chapters__image img{display:block;width:100%;height:auto;object-fit:contain;object-position:center;border:1px solid rgba(121,211,246,.86);background:rgba(127,175,195,.06);color:#e5f4ff;font:400 16px/1.5 'CyberSourceHan',sans-serif;}.ct-chapters__image+.ct-chapters__copy,.ct-chapters__copy+.ct-chapters__image{margin-top:24px;}@media(max-width:520px){.ct-chapters__flow{padding-inline:var(--ct-chapters-small-gutter,16px);}.ct-chapters__panel{--ct-panel-top-width:180px;--ct-panel-bottom-width:100px;--ct-panel-corner:18px;--ct-panel-outer-space:14px;}.ct-chapters__reading{--ct-chapters-reading-pad:20px;}.ct-chapters .ct-title{--ct-title-gap:8px;--ct-title-relative-max:calc(100vw - 80px);}.ct-chapters__intro{--ct-brackets-space:35px;}.ct-chapters__intro .ct-brackets__body{font-size:21px;}.ct-chapters__strip{font-size:22px;}}
.ct-chapters__reading{background:linear-gradient(to bottom,rgba(167,212,240,.31) 0,rgba(128,170,199,.12) 24px,rgba(43,47,65,.65) 65px,rgba(32,36,50,.77) 100%),linear-gradient(110deg,rgba(93,103,134,.4),rgba(39,45,60,.34) 55%,rgba(76,88,110,.4));}
```

```html
<div class="ct-chapters ct-glitch" role="group" aria-label="冷蓝终端章节组演示"><span class="ct-glitch__layer" aria-hidden="true"></span><div class="ct-chapters__flow ct-glitch__content"><div class="ct-brackets ct-chapters__intro"><span class="ct-brackets__corner" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--tr" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--bl" aria-hidden="true"></span><span class="ct-brackets__corner ct-brackets__corner--br" aria-hidden="true"></span><div class="ct-brackets__body"><p>活动包含「潜入行动」「拟真训练」、<br>「养成模块」与「信息通路矫正」。</p></div></div><div class="ct-chapters__strip-row"><div class="ct-strip ct-chapters__strip"><span class="ct-strip__text">终端档案 · 玩法说明</span></div></div><section class="ct-chapters__chapter" aria-labelledby="ct-chapters-story-title"><div class="ct-title"><span class="ct-title__line" aria-hidden="true"></span><h2 class="ct-title__text" id="ct-chapters-story-title"><span class="ct-offset"><span class="ct-offset__main">潜入行动 · 剧情阅读</span><span class="ct-offset__copy" aria-hidden="true">潜入行动 · 剧情阅读</span><span class="ct-offset__copy ct-offset__copy--violet" aria-hidden="true">潜入行动 · 剧情阅读</span></span></h2><span class="ct-title__line ct-title__line--right" aria-hidden="true"></span></div><div class="ct-panel ct-chapters__panel"><span class="ct-panel__shell" aria-hidden="true"></span><span class="ct-panel__rail" aria-hidden="true"></span><span class="ct-panel__rail ct-panel__rail--inner" aria-hidden="true"></span><div class="ct-panel__body"><div class="ct-scan ct-chapters__reading"><span class="ct-scan__layer" aria-hidden="true"></span><div class="ct-scan__content ct-chapters__reading-content"><p class="ct-chapters__eyebrow">FOR ALL TIME <span aria-hidden="true">&gt;&gt;&gt;&gt;&gt;</span></p><figure class="ct-chapters__image"><img src="SLOT:story" alt="剧情阅读示意截图：章节节点与分支入口"></figure><div class="ct-chapters__copy"><p>每条剧情线路均设有多个阅读节点，需要切换线路时，可从潜入行动的面板返回起始章节。部分节点共用相同的入口，但叙述视角和对话内容有所不同，切换后可重新查看当前章节。</p><p>首次进入尚未阅读的章节前，请查看所需资源与解锁条件。已完成的章节保留回看入口，便于补读剧情、整理线索，并确认各条线路的阅读进度。</p></div></div></div></div></div></section><section class="ct-chapters__chapter" aria-labelledby="ct-chapters-route-title"><div class="ct-title"><span class="ct-title__line" aria-hidden="true"></span><h2 class="ct-title__text" id="ct-chapters-route-title"><span class="ct-offset"><span class="ct-offset__main">信息通路矫正 · 玩法</span><span class="ct-offset__copy" aria-hidden="true">信息通路矫正 · 玩法</span><span class="ct-offset__copy ct-offset__copy--violet" aria-hidden="true">信息通路矫正 · 玩法</span></span></h2><span class="ct-title__line ct-title__line--right" aria-hidden="true"></span></div><div class="ct-panel ct-chapters__panel"><span class="ct-panel__shell" aria-hidden="true"></span><span class="ct-panel__rail" aria-hidden="true"></span><span class="ct-panel__rail ct-panel__rail--inner" aria-hidden="true"></span><div class="ct-panel__body"><div class="ct-scan ct-chapters__reading"><span class="ct-scan__layer" aria-hidden="true"></span><div class="ct-scan__content ct-chapters__reading-content"><p class="ct-chapters__eyebrow">FOR ALL TIME <span aria-hidden="true">&gt;&gt;&gt;&gt;&gt;</span></p><div class="ct-chapters__copy"><p>调整线路方向，将信息标记与对应的芯片入口相连，并沿连通路径送达目标位置，即可完成通路校验。暂时无法处理的信息可先放入暂存区，待其他路径完成后再取回。</p></div><figure class="ct-chapters__image"><img src="SLOT:route" alt="通路调整示意截图：线路网格、信息标记与目标芯片"></figure><div class="ct-chapters__copy"><p>完成关卡后，可在记录面板查看本次结果与尚未连通的节点。返回线路图继续调整时，请同时核对标记形状、目标位置和连接方向。</p></div></div></div></div></div></section></div></div>
```

验证边界：已对参考局部完成参数校准，658/420px、默认/两倍正文和长标题实测；截图槽、字体替代与表面层次已看图核对。本组合是局部适配，不是完整原图或精确字形复刻。

<a id="combination.tavern-shelf-directory"></a>

## 搁板摄影目录

风格标签：二级：复古商业风 / 怀旧商品目录。

实际绑定搁板截面与色板原子；组合CSS仅定义目录绑定、文件夹图注和响应覆盖。默认最大658px、边距4%、列隙20px、双列照片284:340、纸签压图36px；容器460px以下单列，允许每排1或2项及任意排数。照片槽为独立摄影，不调色；店名、短评、入口均真实可编辑。图注z3高于照片与搁板内容，纸签底部落在搁板承重线上。店名Arial/RetroSource 600–650，仅近似参考窄手绘字，正文400；建议店名1–2行、短评12–28字，增加文案会自然增高。文件夹斜肩保持左高右低，不使用随机拼贴旋转。

```json
{
  "dependencies": [
    "shape.shelf-profile",
    "palette.tavern-umber-orange"
  ],
  "asset_slots": [
    {
      "name": "silver-eye-wide.png",
      "role": "首张Silver Eye室内摄影的无文字矩形区域；原下缘被文件夹遮挡，取遮挡上方范围并由CSS控制宽图比例，不含图注。"
    },
    {
      "name": "wugong-front.png",
      "role": "武宫门店摄影，避开白衬边与下方签头；图像底部原被图注遮挡。"
    },
    {
      "name": "mandrill-front.png",
      "role": "Mandrill门店与青蓝露台摄影，保留霓虹和植物原色，不含纸签。"
    }
  ],
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
.vl-r9-directory{box-sizing:border-box;width:100%;max-width:658px;margin-inline:auto;background:var(--vl-cabinet);container-type:inline-size}.vl-r9-directory .vl-r9-directory-row{padding:42px 4% var(--vl-shelf-depth)}.vl-r9-directory-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;align-items:end}.vl-r9-directory-grid--feature{grid-template-columns:minmax(0,1fr)}.vl-r9-directory-card{position:relative;min-width:0;margin:0}.vl-r9-directory-photo{display:block;box-sizing:border-box;width:calc(100% - 8px);height:auto;aspect-ratio:284/340;object-fit:cover;margin:0 auto;border:4px solid var(--vl-cream);box-shadow:0 2px 5px #14050099}.vl-r9-directory-grid--feature .vl-r9-directory-photo{aspect-ratio:594/343}.vl-r9-directory-label{position:relative;z-index:3;margin-top:-36px;min-height:96px;padding:0 10px 9px;background:linear-gradient(100deg,#ffffff07,#2109000a),var(--vl-paper);color:var(--vl-cream);clip-path:polygon(0 0,52% 0,57% 31px,100% 31px,100% 100%,0 100%);box-shadow:inset 0 0 0 1px #e2b17b66}.vl-r9-directory-name{box-sizing:border-box;display:flex;align-items:flex-start;gap:6px;width:53%;min-height:42px;padding-top:7px;margin:0;color:var(--vl-ink);font-size:clamp(16px,3.1cqw,23px);line-height:1.05;font-weight:650;overflow-wrap:anywhere}.vl-r9-directory-name span{font-family:Arial,RetroSource,sans-serif;font-stretch:condensed;font-weight:600}.vl-r9-directory-pin{flex:0 0 12px;width:12px;height:15px;margin-top:2px;background:var(--vl-ink);border-radius:60% 60% 60% 0;transform:rotate(-45deg);position:relative}.vl-r9-directory-pin::after{content:'';position:absolute;width:4px;height:4px;left:4px;top:4px;border-radius:50%;background:var(--vl-paper)}.vl-r9-directory-copy{display:flex;align-items:center;justify-content:space-between;gap:5px}.vl-r9-directory-copy p{font-size:clamp(12px,2.5cqw,18px);line-height:1.5;margin:5px 0;overflow-wrap:anywhere}.vl-r9-directory-link{flex:0 0 auto;text-decoration:none;padding:5px 7px;border-radius:18px;background:var(--vl-ink);color:var(--vl-cream);font-size:11px;white-space:nowrap}.vl-r9-directory-footer{display:flex;justify-content:space-between;align-items:center;font-family:Arial,sans-serif;font-size:7px;color:var(--vl-ink);opacity:.8;margin-top:3px}.vl-r9-directory-footer i{width:24%;height:1px;background:currentColor}.vl-r9-directory-footer b{font-weight:400;border:1px solid #65381777;padding:1px 3px}.vl-r9-directory-grid--feature .vl-r9-directory-name{min-height:46px;font-size:26px}.vl-r9-directory-grid--feature .vl-r9-directory-copy p{font-size:clamp(19px,4.5cqw,29px)}@container(max-width:460px){.vl-r9-directory-grid{grid-template-columns:minmax(0,1fr);gap:36px}.vl-r9-directory .vl-r9-directory-row{padding-top:32px}.vl-r9-directory-photo{aspect-ratio:1.05}.vl-r9-directory-name{font-size:22px}.vl-r9-directory-copy p{font-size:18px}.vl-r9-directory-label{min-height:105px;padding-inline:12px}.vl-r9-directory-link{font-size:12px}.vl-r9-directory-grid--feature .vl-r9-directory-photo{aspect-ratio:1.4}}
```

```html
<section class="vl-r9-palette vl-r9-directory" aria-label="街区酒馆目录"><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:wugong-front.png" alt="武宫的白色门廊和木门"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>武宫</span></h3><div class="vl-r9-directory-copy"><p>［武夷路的黑胶文化之宫］</p><a class="vl-r9-directory-link" href="#vl-r9-directory-visit">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:mandrill-front.png" alt="Mandrill青蓝色露台与暖黄招牌"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>MANDRILL</span></h3><div class="vl-r9-directory-copy"><p>［演员黄觉的复古机车bar］</p><a class="vl-r9-directory-link" href="#vl-r9-directory-visit">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row" id="vl-r9-directory-visit"><div class="vl-r9-shelf-content vl-r9-directory-grid vl-r9-directory-grid--feature"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:silver-eye-wide.png" alt="Silver Eye室内圆镜与窗边座椅"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>SILVER EYE</span></h3><div class="vl-r9-directory-copy"><p>［神秘感十足的暗黑风bar］</p><a class="vl-r9-directory-link" href="#vl-r9-directory-visit">到店看看 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div></section>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：已核对API实现与实际658/420宽度截图；图像完整加载、真实思源黑体face就绪、无页面横向溢出。API参考关系复核通过：combination.tavern-shelf-directory。验收限本条声明机制，不代表整页或原始字体精确复刻。

<a id="combination.tavern-paper-dispenser"></a>

## 出纸槽垂纸说明组

风格标签：二级：复古商业风 / 怀旧商品目录。

实际依赖纸槽、搁板、语义色板；标题位于机器外，机器与长纸不能合并成背景。默认最大658px、纸宽86%、前便笺负叠108px，460px以下取消遮叠并恢复纸底35px安全距；规则默认三行，可增减为2–6行，每行右侧68–94px独立奖品槽。装置z0、槽z1、纸z2、前唇z3、便笺z4继承原子，搁板在组底承托。横纹橙牌由3px低对比横纹与亮暗包边构成，不冒充金属框；螺钉仅CSS近似。正文RetroSource400，标题750，便笺700；不以900替代参考窄字。奖品裁片保留原纸面场域，非透明抠图；不额外叠颗粒避免干扰小字。日期与规则为参考历史活动内容，不代表现行活动。 复验修正：横纹3px周期亮差降至.067；两侧螺钉显式z0。标题用抖音美好体Bold真实400face，便笺用寒蝉高黑体Medium真实500并禁止伪粗；地址同行优先窄屏换行。原参考曾以右侧7%裁边去除括号残留，该处理不施加给新素材；正式素材默认不裁边，确需裁切时按实际内容单独验证。

```json
{
  "dependencies": [
    "shape.recessed-paper-slot",
    "shape.shelf-profile",
    "palette.tavern-umber-orange"
  ],
  "asset_slots": [
    {
      "name": "map-sticker-gift.png",
      "role": "地图册与贴纸奖品物体；保留局部赭纸不透明场域，无规则文字，非透明素材。"
    },
    {
      "name": "stamp-pass.png",
      "role": "绿色集章卡独立奖品物体；保留四角局部纸面，非透明抠图。"
    },
    {
      "name": "red-knit-bag.png",
      "role": "红色针织手提包奖品；保留原赭纸场域，不含左侧兑换文案，不假装去底。"
    }
  ],
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
.vl-r9-dispenser{box-sizing:border-box;max-width:658px;width:100%;margin-inline:auto;padding-top:64px;background:var(--vl-cabinet)}.vl-r9-dispenser-heading{text-align:center;margin:0 0 22px;padding:0 8%}.vl-r9-dispenser-sign{position:relative;display:block;box-sizing:border-box;max-width:440px;margin:auto;padding:14px 17px;border-radius:16px 16px 10px 10px;color:var(--vl-ink);background:repeating-linear-gradient(0deg,#fff5 0 1px,#00000009 1px 3px),linear-gradient(var(--vl-orange),var(--vl-orange-deep));border:3px solid #756c60;outline:1px solid #25160d;box-shadow:inset 0 2px #ffe0b2,inset 0 -3px #a9430c,0 12px 17px #1807009c;font-size:clamp(23px,5.1vw,35px);line-height:1.35;font-weight:750;letter-spacing:-1px}.vl-r9-dispenser-sign::before,.vl-r9-dispenser-sign::after{content:'';position:absolute;top:24px;width:22px;height:22px;z-index:-1;border-radius:50%;background:radial-gradient(circle,#302923 0 15%,#b2a194 17% 24%,#514b46 28% 36%,#a99889 43% 60%,#5f5348 75%);box-shadow:0 1px 2px #0f0806}.vl-r9-dispenser-sign::before{left:-24px}.vl-r9-dispenser-sign::after{right:-24px}.vl-r9-dispenser-heading small{display:block;margin-top:18px;font-size:16px;font-weight:400;color:var(--vl-cream)}.vl-r9-dispenser .vl-r9-dispenser-base{padding:0 0 var(--vl-shelf-depth)}.vl-r9-dispenser .vl-r9-slot-paper{padding-top:49px;padding-bottom:135px}.vl-r9-dispenser-intro{margin:0 0 15px;font-size:clamp(17px,3.3vw,22px);line-height:1.85}.vl-r9-dispenser-muted{font-size:16px;line-height:1.8;margin:0;color:var(--vl-cream)}.vl-r9-dispenser-rules{list-style:none;margin:22px -14px 0;padding:20px 14px 12px;border-top:2px dashed #633716;border-bottom:2px dashed #633716}.vl-r9-dispenser-rule{display:grid;grid-template-columns:23px minmax(0,1fr) 94px;gap:12px;align-items:center;min-height:95px;margin:0 0 8px}.vl-r9-dispenser-dot{display:block;width:23px;height:23px;border-radius:50%;background:linear-gradient(#ffb16b,var(--vl-orange-deep));box-shadow:inset 0 -2px #ac4e1680,0 1px 1px #5c2e16}.vl-r9-dispenser-rule p{margin:0;font-size:clamp(17px,3.3vw,22px);line-height:1.8}.vl-r9-dispenser-rule small{font-size:13px}.vl-r9-dispenser-prize{display:block;width:100%;height:auto;mix-blend-mode:normal}.vl-r9-dispenser .vl-r9-slot-note{margin-top:-108px;padding:23px 26px 20px 40px;background:linear-gradient(120deg,#ffffff12,#554b3710),var(--vl-note);font-style:italic}.vl-r9-dispenser .vl-r9-slot-note h3{margin:0 0 8px;font-size:22px;font-weight:700}.vl-r9-dispenser .vl-r9-slot-note p{margin:6px 0;font-size:18px;line-height:1.6}.vl-r9-dispenser-address{padding:5px 10px;color:var(--vl-cream);background:var(--vl-ink)}.vl-r9-dispenser .vl-r9-slot-note small{font-size:14px;line-height:1.6;display:block;margin-top:10px}@media(max-width:460px){.vl-r9-dispenser{padding-top:48px}.vl-r9-dispenser .vl-r9-slot-paper{padding-bottom:35px}.vl-r9-dispenser .vl-r9-slot-note{margin:18px auto 0;padding:24px 25px 24px 32px}.vl-r9-dispenser-rule{grid-template-columns:19px minmax(0,1fr) 68px;gap:8px}.vl-r9-dispenser-dot{width:19px;height:19px}.vl-r9-dispenser .vl-r9-slot-note p{font-size:16px}.vl-r9-dispenser-sign{font-size:25px}}
.vl-r9-dispenser-sign{background:repeating-linear-gradient(0deg,#fff1 0 1px,transparent 1px 3px),linear-gradient(var(--vl-orange),var(--vl-orange-deep));font-family:RetroDisplay,RetroSource,sans-serif;font-weight:400;font-synthesis:none;letter-spacing:0}.vl-r9-dispenser-sign::before,.vl-r9-dispenser-sign::after{z-index:0;top:50%;transform:translateY(-50%)}.vl-r9-dispenser .vl-r9-slot-note{font-family:RetroNarrow,RetroSource,sans-serif;font-weight:500;font-synthesis:none}.vl-r9-dispenser .vl-r9-slot-note p{line-height:1.4}.vl-r9-dispenser-address{font-style:normal;display:flex;align-items:baseline;flex-wrap:wrap;gap:5px}.vl-r9-dispenser .vl-r9-dispenser-address small{display:inline;font-size:12px;margin:0}.vl-r9-dispenser-prize{clip-path:none}
```

```html
<section class="vl-r9-palette vl-r9-dispenser" aria-label="团购兑换说明"><header class="vl-r9-dispenser-heading"><h2 class="vl-r9-dispenser-sign">下单团购，解锁限量周边</h2><small>*未成年人禁止饮酒</small></header><div class="vl-r9-shelf vl-r9-dispenser-base"><div class="vl-r9-shelf-content"><div class="vl-r9-slot"><div class="vl-r9-slot-machine" aria-hidden="true"></div><div class="vl-r9-slot-mouth" aria-hidden="true"></div><article class="vl-r9-slot-paper"><p class="vl-r9-dispenser-intro">即日起至2024年1月5日活动期间，下单本活动页面内任一商家的热红酒活动产品，并前往线下店铺出示实时订单进行验券。</p><p class="vl-r9-dispenser-muted">（小红书APP－我－左上角横杠－订单）</p><ul class="vl-r9-dispenser-rules"><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>下单完成首次验券，即可获得纸质版地图＋热红酒贴纸。</p><img class="vl-r9-dispenser-prize" src="SLOT:map-sticker-gift.png" alt="红色地图册与彩色贴纸"></li><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>每打卡一家店铺完成验券，即可获得1枚店铺专属印章。</p><img class="vl-r9-dispenser-prize" src="SLOT:stamp-pass.png" alt="绿色集章卡"></li><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>集满3家不同店铺印章，兑换限量款红酒小红包。<br><small>基础斜挎款与隐藏手提款，先到先选。</small></p><img class="vl-r9-dispenser-prize" src="SLOT:red-knit-bag.png" alt="红色针织手提包"></li></ul></article><div class="vl-r9-slot-lip" aria-hidden="true"></div><aside class="vl-r9-slot-note"><h3>针织挎包兑换方式：</h3><p>1月5日前，周五／周六12:30–13:30 Mandrill点开放；周日18:00–19:00 Tiler点开放。每个领取点每周限量发放100份，先到先得。</p><p class="vl-r9-dispenser-address">● 愚园路－Mandrill<br><small>长宁区江苏路街道愚园路1258号</small></p><p class="vl-r9-dispenser-address">● 复兴中路－Tiler<br><small>黄浦区瑞金二路街道复兴中路612号</small></p><small>*兑换时须出示不可滑动的实时订单，截图不可用。地图遗失不补。</small></aside></div></div></div></section>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：修正后实际658/420截图与正文加倍验证通过。掉墨采用内联SVG资源解析，真实内容独立不透明；出纸说明保留槽后垂纸、前唇、低对比横纹及前便笺层级。验收针对本条机制，非整页精确复刻。

<a id="combination.clipped-archive-reading"></a>

## 夹持剪报阅读组

风格标签：二级：手账拼贴风 / 票据档案。

实际绑定surface.worn-ink的容器、marks和content类；本组合CSS仅负责纸面、刊头、夹持关系及依赖变量覆盖。max-width610px，658宽页内建议左右24px；420宽时人物由右栏改下排，正文自然增加高度。默认两栏比例1.24:0.9、间距18px；可通过grid-template-columns改为单栏，正文可增至1.5倍，禁止固定文章高度。底纸z0、掉墨z1、正文与后报z2、前刊头z3、夹子z6；夹子素材保留周围纸黑场域并以multiply融合，不是真实透明抠图。宽刊头与长正文使用不同撕边轮廓。中文正文RetroSource 400、标题700，英文Georgia 700；话筒是简化内联插画，刊头与手写字均未字体级复原。无真实纸纤维素材，CSS仅模拟纸色、细印刷线与明暗不均。 修正纸形只裁背景伪元素，真实内容与伸出纸面的夹子不裁切；夹具top:-22px、外部净空38px。 报头恢复原图独立艺术标识素材槽，删除普通Georgia代替艺术刊头的示例，不宣称报头字体可编辑或已识别。

```json
{
  "dependencies": [
    "surface.worn-ink"
  ],
  "asset_slots": [
    {
      "name": "archive-clip.png",
      "role": "刊头中央复杂旧金属夹，含物件周围原纸色及少量黑黄背景；multiply只是场域融合，不是真实抠图。"
    },
    {
      "name": "archive-portrait.png",
      "role": "报纸中的西装男子独立人物插画；保留右上原弹壳遮挡和内景背景，下缘止于人物影像附近，不以整段剪报代替CSS正文。"
    },
    {
      "name": "archive-masthead.png",
      "role": "独立报头艺术字及话筒图案，不含正文；原始展示字与叠印作为素材保留，非字体复原。"
    }
  ],
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
.vl-r3-archive{--vl-r3-ground:#242420;--vl-r3-warning:#d7dd16;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;--vl-r3-muted:#999781;position:relative;isolation:isolate;box-sizing:border-box;max-width:610px;margin:38px auto 0;padding:28px clamp(18px,4.7vw,32px) 30px;color:var(--vl-r3-ink);font-family:RetroSource,sans-serif;font-weight:400;line-height:1.65;background:var(--vl-r3-paper);clip-path:polygon(0 2%,3% 1.4%,2% 0,21% .6%,24% 0,48% .7%,61% .2%,76% 1%,96% .4%,100% 2%,99% 28%,100% 29%,98.8% 54%,100% 55%,99% 79%,100% 97%,96% 98%,83% 97.8%,77% 99%,62% 98.3%,49% 100%,31% 98.5%,16% 99.2%,0 98%,1% 70%,0 69%,1% 43%,0 42%)}.vl-r3-archive:before{content:'';position:absolute;inset:0;z-index:0;pointer-events:none;background:linear-gradient(97deg,rgba(255,255,255,.13),transparent 30%,rgba(50,49,31,.07) 74%,transparent),repeating-linear-gradient(0deg,transparent 0 29px,rgba(58,57,39,.045) 30px,transparent 31px)}.vl-r3-archive>.vl-r3-wear__marks{--vl-r3-wear-strength:.15;--vl-r3-wear-color:#66654e}.vl-r3-archive__back{position:relative;z-index:2;margin:-12px -6px 4px;padding:0 8px 14px;border-bottom:3px double var(--vl-r3-ink);transform:rotate(1.5deg);font-family:Georgia,serif;font-size:clamp(22px,5vw,39px);font-weight:700;line-height:1.05}.vl-r3-archive__back small{display:block;margin-top:6px;font-family:Arial,sans-serif;font-size:9px;font-weight:400;letter-spacing:.13em}.vl-r3-archive__clip{position:absolute;z-index:6;top:-3px;left:50%;width:clamp(118px,30%,198px);height:auto;transform:translateX(-50%);mix-blend-mode:multiply;pointer-events:none}.vl-r3-archive__masthead{position:relative;z-index:3;margin:4px -12px 22px;padding:24px 14px 18px;background:#d0cdb8;transform:rotate(-2deg);border-bottom:1px solid #85836d;clip-path:polygon(1% 4%,95% 0,100% 8%,99% 92%,91% 96%,2% 100%,0 88%)}.vl-r3-archive__masthead-row{display:flex;align-items:center;gap:12px}.vl-r3-archive__mic{width:65px;flex:0 0 65px;color:var(--vl-r3-ink)}.vl-r3-archive__masthead-copy{flex:1;min-width:0}.vl-r3-archive__english{margin:0;font-family:Georgia,serif;font-weight:700;font-size:clamp(27px,6.4vw,47px);line-height:1;letter-spacing:-.065em}.vl-r3-archive__edition{display:flex;justify-content:space-between;align-items:end;gap:8px;margin-top:7px;border-top:2px solid var(--vl-r3-ink);padding-top:4px}.vl-r3-archive__edition strong{font-size:clamp(21px,4.7vw,30px);font-weight:700}.vl-r3-archive__edition span{font-family:Arial,sans-serif;font-size:9px;letter-spacing:.06em}.vl-r3-archive__kicker{margin:0 0 12px;font-size:11px;letter-spacing:.12em;color:#65644f}.vl-r3-archive__lead{display:grid;grid-template-columns:minmax(0,1.24fr) minmax(0,.9fr);gap:18px;align-items:start}.vl-r3-archive__copy{margin:0 0 17px;font-size:clamp(14px,2.42vw,16px);line-height:1.65;letter-spacing:.025em;font-weight:400}.vl-r3-archive__copy:last-child{margin-bottom:0}.vl-r3-archive__portrait{margin:0;transform:rotate(.7deg)}.vl-r3-archive__portrait img{display:block;width:100%;height:auto;filter:contrast(1.04)}.vl-r3-archive__portrait figcaption{font-size:10px;line-height:1.5;margin-top:5px;color:#66654f}.vl-r3-archive__continuation{position:relative;margin:17px -5px 0;padding:22px 5px 0;border-top:1px solid #8f8c76}.vl-r3-archive__continuation:before{content:'';position:absolute;top:-6px;left:0;right:0;height:10px;background:#b2ae95;clip-path:polygon(0 20%,9% 63%,17% 10%,28% 70%,36% 20%,49% 77%,62% 20%,73% 80%,82% 17%,91% 67%,100% 20%,100% 50%,92% 90%,81% 44%,72% 100%,61% 51%,49% 100%,36% 51%,28% 100%,17% 42%,9% 91%,0 55%)}@media(max-width:460px){.vl-r3-archive{padding-left:20px;padding-right:20px}.vl-r3-archive__lead{grid-template-columns:1fr;gap:12px}.vl-r3-archive__portrait{width:64%;max-width:230px;justify-self:end;margin-bottom:8px}.vl-r3-archive__mic{width:47px;flex-basis:47px}.vl-r3-archive__masthead-row{gap:7px}.vl-r3-archive__edition{align-items:center}.vl-r3-archive__edition span{font-size:8px}.vl-r3-archive__copy{font-size:14px;line-height:1.75}}
.vl-r3-archive__clip{clip-path:polygon(0 97%,3% 86%,17% 75%,35% 70%,36% 39%,42% 30%,44% 12%,50% 2%,56% 3%,63% 13%,67% 33%,73% 42%,73% 72%,92% 79%,99% 92%,100% 99%)}
.vl-r3-archive{clip-path:none;background:transparent}.vl-r3-archive:before{background-color:var(--vl-r3-paper);clip-path:polygon(0 2%,3% 1.4%,2% 0,21% .6%,24% 0,48% .7%,61% .2%,76% 1%,96% .4%,100% 2%,99% 28%,100% 29%,98.8% 54%,100% 55%,99% 79%,100% 97%,96% 98%,83% 97.8%,77% 99%,62% 98.3%,49% 100%,31% 98.5%,16% 99.2%,0 98%,1% 70%,0 69%,1% 43%,0 42%)}.vl-r3-archive__clip{top:-22px}
.vl-r3-archive__masthead{padding:10px 12px}.vl-r3-archive__masthead-art{display:block;width:100%;height:auto;mix-blend-mode:multiply}
.vl-r3-archive__clip{top:0}.vl-r3-archive__lead{padding:16px;background:#c9c5b0;box-shadow:0 2px 1px #5d5a4330}.vl-r3-archive__continuation{padding:18px 12px;background:#c5c0a7;border-top:0;box-shadow:0 -2px 1px #78715c28}
.vl-r3-archive__back{font-size:32px;height:45px;overflow:hidden;margin-bottom:-12px;padding-bottom:0}.vl-r3-archive__clip{top:8px}.vl-r3-archive:before{background:var(--vl-r3-paper)}.vl-r3-archive__masthead{margin-top:0;background:#cbc7b2;clip-path:polygon(0 4%,4% 2%,8% 4%,22% 0,31% 3%,58% 0,77% 2%,98% 0,100% 7%,99% 29%,100% 44%,99% 77%,100% 96%,91% 99%,73% 97%,62% 100%,42% 98%,23% 100%,2% 97%,0 88%)}.vl-r3-archive__lead,.vl-r3-archive__continuation{position:relative;background:transparent;box-shadow:none;border:0}.vl-r3-archive__lead:before,.vl-r3-archive__continuation:before{content:"";position:absolute;inset:0;z-index:-1;background:#c9c5b0;clip-path:polygon(0 1%,15% 0,26% 1.1%,49% 0,72% 1%,100% 0,99% 33%,100% 55%,99% 76%,100% 98%,83% 100%,61% 99%,42% 100%,22% 98%,0 99%)}.vl-r3-archive__continuation{margin-top:-3px}.vl-r3-archive__continuation:before{height:auto;background:#c5c0a7}.vl-r3-archive>.vl-r3-wear__marks{--vl-r3-wear-strength:.3;--vl-r3-wear-color:#6e6953}
.vl-r3-archive__masthead{padding-top:48px}.vl-r3-archive__back small{display:none}
```

```html
<article class="vl-r3-archive vl-r3-wear" aria-label="夹持剪报：达维镇银行来信"><span class="vl-r3-wear__marks" aria-hidden="true"></span><div class="vl-r3-archive__back">DW.<small>CRIMINAL INCIDENT NEWS · NO.03</small></div><img class="vl-r3-archive__clip" src="SLOT:archive-clip.png" alt="压在刊头上的旧金属夹"><header class="vl-r3-archive__masthead"><img class="vl-r3-archive__masthead-art" src="SLOT:archive-masthead.png" alt="The Daily Fortune 财富日报艺术刊头"></header><div class="vl-r3-wear__content"><p class="vl-r3-archive__kicker">读者来信选登 / 关于达维镇事件的另一种解释</p><div class="vl-r3-archive__lead"><div><p class="vl-r3-archive__copy">因此，我们不难发现这个谣言背后巨大的破绽：银行根本不具备驱逐地域居民的权力和能力，而就算它有，它又能通过这样做获得什么呢？它能取得达维镇的征税权吗？别忘了，居民都被它“赶跑了”。</p><p class="vl-r3-archive__copy">它要管领州政府给予工矿业的发展补贴吗？每年发放前都有检查员核实。要么它就只要那一堆低值房地产，然后附带所有热爱公平正义的哥伦比亚人的痛恨？</p></div><figure class="vl-r3-archive__portrait"><img src="SLOT:archive-portrait.png" alt="报纸中的西装男子插画，右上保留原有弹壳叠压"><figcaption>资料图：刊载于读者来信栏的人物插画。</figcaption></figure></div><div class="vl-r3-archive__continuation"><p class="vl-r3-archive__copy">我的朋友们，我这样说，并不是因为我与银行更加亲近——银行是个机构，不是个能亲近的人——而是我作为专业人士，更需要为你们做出理智的分析。在我们哥伦比亚，所有的银行本质上都是金融公司，是为了盈利而生的私人企业，通过金融服务赚取利润是它们绝对的生存法则。</p><p class="vl-r3-archive__copy">也就是说，一家银行绝对不会去做没有利润可以赚取的事情。哪怕在达维镇，银行因为它所谓的“社会责任”而向那些经济基础不稳固、经济前景不明朗的镇民开放服务，它背后的目的也还是赚取利润。毕竟该地曾经人口基数庞大，银行的策略本应是薄利多销。</p></div></div></article>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：依据API反馈修正夹口覆盖前刊头留白、后报标题主次、独立艺术刊头槽和不规则纸层，已实际查看最终658截图及此前420/加倍正文；保持真实内容自然撑高。仅声明夹持阅读组合，艺术刊头为独立素材，非字体精确复原。本条以本地实渲染检查验收，艺术字素材不视为字体复原。

<a id="combination.silver-coupon-grid"></a>

## 银底优惠票阵

风格标签：一级：未来科技风。

实际绑定色板和腰缺口原子，组合CSS只提供章节层级、网格和变量覆盖。658宽默认3列2行，480以下2列3行，420宽保留全部六券；列数可改但不改变每票单对腰孔。标题、说明、券值均可编辑，说明建议3–6行，网格自然下移。五连星为独立复杂金属物体槽，z=1压住标题上沿；该裁片含原图冷银场域，不是透明抠图。章节背景伪层z=-1，文字无透明度损失。标题RetroSource 700，不使用900；金额Arial 800仅近似运动字形。组合不通过截图承载标题和券内文字。 复验修正：标题绑定抖音美好体Bold实际face（文件weight400，禁止伪粗），保留粗紧展示骨架；底面颗粒独立层.17，券脚soft-light局部叠合，正文不降透明。 最终标题按原参考超粗促销骨架使用思源黑体真实900轴，区别正文400；经同字检查后选择，不将900推广为全页默认。券脚撤掉直接贴图，单色颗粒.045保留青蓝主色。

```json
{
  "dependencies": [
    "shape.paired-waist-ticket",
    "palette.silver-cyan-mono"
  ],
  "asset_slots": [
    {
      "name": "five-chrome-stars.png",
      "role": "活动标题上方五连金属星独立复杂装饰；窄裁片保留星间银灰背景，不包含整块标题条。"
    }
  ],
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
.vl-r8-coupons{box-sizing:border-box;position:relative;isolation:isolate;max-width:658px;margin-inline:auto;padding:36px clamp(22px,7%,48px) 48px;text-align:center;background:radial-gradient(ellipse at 12% 25%,#e3e9e844,transparent 65%),var(--vl-silver)}.vl-r8-coupons:before{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;background:url('asset:svg/screen-grain.svg') repeat;opacity:var(--vl-grain-opacity)}.vl-r8-coupons__heading{margin:0;display:flex;align-items:center;flex-direction:column;font-weight:700}.vl-r8-coupons__number{font-size:clamp(24px,5vw,31px);line-height:1.2;letter-spacing:-1.5px}.vl-r8-coupons__stars{display:block;width:174px;max-width:48%;height:auto;margin:-1px auto -5px;position:relative;z-index:1}.vl-r8-coupons__label{display:inline-block;border-radius:5px;padding:5px 12px 9px;background:var(--vl-ink);color:var(--vl-paper);font-size:clamp(28px,5.7vw,39px);line-height:1.15;letter-spacing:-1.5px}.vl-r8-coupons__intro{margin:26px 0 0;font-size:clamp(14px,2.5vw,16px);line-height:1.6;font-weight:400}.vl-r8-coupons__emphasis{padding:0 5px;background:var(--vl-ink);color:var(--vl-paper);box-decoration-break:clone;-webkit-box-decoration-break:clone}.vl-r8-coupons__grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:27px 23px;max-width:386px;margin:36px auto 0}.vl-r8-coupons .vl-r8-ticket{--ticket-paper:var(--vl-paper);--ticket-ink:var(--vl-ink);--ticket-accent:var(--vl-cyan);--ticket-notch:9px;max-width:none;align-self:start}.vl-r8-coupons .vl-r8-ticket__amount{font-size:48px}.vl-r8-coupons .vl-r8-ticket__condition{font-size:15px;color:#60411f}.vl-r8-coupons .vl-r8-ticket__foot{font-size:14px}@media(max-width:480px){.vl-r8-coupons__grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:290px;gap:22px}.vl-r8-coupons__intro{line-height:1.75}}
.vl-r8-coupons__label,.vl-r8-coupons__number{font-family:RetroDisplay,RetroSource,sans-serif;font-weight:400;font-synthesis:none}.vl-r8-coupons{--vl-grain-opacity:.17}.vl-r8-coupons .vl-r8-ticket__foot{background-image:url(asset:svg/screen-grain.svg);background-blend-mode:soft-light}
.vl-r8-coupons__label,.vl-r8-coupons__number{font-family:RetroSource,sans-serif;font-weight:900;letter-spacing:-2px}.vl-r8-coupons__label{font-size:clamp(30px,6.2vw,41px);padding:2px 10px 5px}.vl-r8-coupons .vl-r8-ticket__foot{background-image:none}.vl-r8-coupons .vl-r8-ticket__foot:after{filter:grayscale(1);opacity:.045;mix-blend-mode:multiply}
```

```html
<section class="vl-r8-palette vl-r8-coupons"><h2 class="vl-r8-coupons__heading"><span class="vl-r8-coupons__number">活动一</span><img class="vl-r8-coupons__stars" src="SLOT:five-chrome-stars.png" alt=""><span class="vl-r8-coupons__label">「满减优惠」</span></h2><p class="vl-r8-coupons__intro">购买登陆计划双十一活动商品<br>单笔订单实付金额满足以下条件即可使用相应优惠券<br>优惠券将发放到高级账号里，请注意查收<br><span class="vl-r8-coupons__emphasis">*单笔订单仅限使用一张优惠券，且不可叠加使用</span></p><div class="vl-r8-coupons__grid"><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>5</div><p class="vl-r8-ticket__condition">满60可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>10</div><p class="vl-r8-ticket__condition">满100可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>30</div><p class="vl-r8-ticket__condition">满200可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>50</div><p class="vl-r8-ticket__condition">满300可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>70</div><p class="vl-r8-ticket__condition">满400可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>100</div><p class="vl-r8-ticket__condition">满500可用</p><div class="vl-r8-ticket__foot">优惠券</div></article></div></section>
```

使用边界：SLOT为任务素材槽，不附带参考品牌摄影；必须按角色替换独立素材。RetroSource为示例字体绑定名，须从字体目录加载实际资源后验证字重，不静默回退。连续背景不拆成多个图卡；纹理层置于内容之后，正文不继承透明度。源码为组装源，成品遵循目标HTML载体规范。

验证：依据API反馈将标题改为思源黑体真实900轴恢复粗紧促销骨架，撤去高对比券脚贴图，保留单色低透明颗粒；已实际查看658/420截图，六券3x2/2x3、双侧单孔、独立银底和真实内容成立。本条以本地实渲染检查验收，不宣称字体精确复原。

<a id="combination.warning-archive-longpage"></a>

## 警戒现场档案长卷

风格标签：二级：手账拼贴风 / 票据档案。

产物：社媒长图；粒度：整页长图。

最后组合为完整长卷，实际绑定两个原子及前置剪报组合，须按依赖顺序加载CSS。语义色板统一为炭黑ground、酸黄warning、橄榄黑ink、灰米纸paper、次要墨muted；覆盖不应将酸黄改为暖金。max-width658px、左右纸距14–25px，420宽自动人物上下排，事实栏仍保持编号窄轨加正文宽轨。章节依次为品牌与复杂物件、弧排英文标题及中英纸条、现场摄影、跨场景警戒带、夹持刊头、人物与两段引文、横跨纸面的正文、三条事实、总结便笺、枪械与版权；无固定整页高度，正文400并由内容自然撑高。底色z0、全页擦损z1、hero z2、剪报z3、事实z4、总结z5、页脚证物z6；警戒带只跨场景和页脚，不切正文。事实默认三条，可增减li，文字增长整行增高；编号默认65px轨，窄屏43px。英文弧排为可编辑SVG textPath，不做横向压缩，适合8–10个大写字母；Georgia 700近似展示字，未复原齿轮替字、手写叠字与原刊头艺术字。摄影已有网点，不二次覆盖；新增网点只用于顶部空白区域。图像均使用原图裁片，不伪造物体或摄影；其余纸面、破边、旗签、深墨栏均为CSS。

### 素材与采用边界

参考裁片仍可能存在底色接缝；主展示字及纸张质感为近似。保留人物、档案、事实栏与收尾关系，不宣称恢复原始分层文件。

```json
{
  "dependencies": [
    "shape.warning-chevron-band",
    "surface.worn-ink",
    "combination.clipped-archive-reading"
  ],
  "scope": "整页章节、连续背景、图文层级和素材槽的可复用组合；保留示例外观近似，不代表精确复刻",
  "asset_slots": [
    {
      "slot": "SLOT:terra-brand.png",
      "role": "左上明日方舟与TERRA艺术字标，保留原黑色底场域；以screen近似融合，未字体复原。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:top-black-object.png",
      "role": "右上黑色复杂机械物件及右缘弹药；身份不作精确断言。矩形保留黑底、右缘纸边及少量黄色场域，无透明抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:single-cartridge.png",
      "role": "顶部独立弹壳，包含周围炭黑底和下缘黄色网点；按原场域显示，不声称透明。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:bank-interior.png",
      "role": "银行建筑内景摄影的连续矩形范围，保留高反差印刷和原有黄网点；为避开下部斜警戒带，裁去其下方地面，不包含整卡或文字段。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:archive-clip.png",
      "role": "刊头中央复杂旧金属夹，含物件周围原纸色及少量黑黄背景；multiply只是场域融合，不是真实抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:archive-portrait.png",
      "role": "报纸中的西装男子独立人物插画；保留右上原弹壳遮挡和内景背景，下缘止于人物影像附近，不以整段剪报代替CSS正文。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:footer-handgun.png",
      "role": "左下复杂枪械证物，含周围深色背景、上缘极少纸边及下缘原警戒黄场域；完整握柄超出该裁片，示例以局部证物方式呈现，不假装透明抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:footer-brand.png",
      "role": "页脚鹰角网络与TERRA联合艺术标志，保留黑色背景，不含下方版权正文；品牌未字体复原。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:archive-masthead.png",
      "role": "独立报头艺术字及话筒图案，不含正文；原始展示字与叠印作为素材保留，非字体复原。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    }
  ],
  "material_contract": {
    "page_background": "整页/章节连续底场由CSS统一承担，不把同一场域切成多张图卡",
    "foreground": "摄影、珠链、吊牌、复杂星饰、艺术Logo为明确素材对象，不由简单轮廓冒充真实材质",
    "seams": "当前参考裁片带原背景，存在接缝；不得把粗clip-path记为透明抠图",
    "text": "正文真实可编辑；艺术字位图不宣称已识别字体或可编辑字形"
  },
  "asset_brief": {
    "subject": "按各槽role定义对象及构图，关联当前主题而非固定品牌",
    "material_and_light": "延续本分支材质与光向；银色对象保留真实反射、厚度和细颗粒，照片保留原色",
    "background": "独立前景优先透明边界；一体场景则保持完整连续背景，二者不可混用",
    "text_handling": "可编辑文字置于HTML；字形参与真实雕刻或艺术标识时作为明确图像槽",
    "composition_and_acceptance": "保留主体完整度、锚点、图文安全区、层级和接触关系；禁带入其他章节正文、状态栏及无关边框",
    "prompt_policy": "记录可参数化素材要求；实际生成prompt按主题填写，不把一条固定prompt作为CSS原子。本示例沿用现有素材。"
  },
  "font_binding": {
    "RetroSource": "思源黑体SourceHanSansSC-VF，实际250–900轴，正文400；标题按组合实值",
    "RetroDisplay": "抖音美好体Bold真实face，文件weight400",
    "RetroNarrow": "寒蝉高黑体Medium真实500；字体匹配为候选替代，非原字体确认"
  }
}
```

```css
.vl-r3-page{--vl-r3-ground:#242420;--vl-r3-warning:#d7dd16;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;--vl-r3-muted:#999781;position:relative;isolation:isolate;max-width:658px;margin:0 auto;overflow:hidden;box-sizing:border-box;background:var(--vl-r3-ground);color:var(--vl-r3-paper);font-family:RetroSource,sans-serif;font-weight:400;border-left:5px solid #bcb9a5;border-right:5px solid #bcb9a5}.vl-r3-page:before{content:'';position:absolute;inset:0;z-index:0;pointer-events:none;opacity:.13;background:repeating-linear-gradient(127deg,transparent 0 101px,#a8a58d 102px,transparent 103px 161px),radial-gradient(ellipse at 9% 21%,#9f9b85,transparent 25%),radial-gradient(ellipse at 92% 76%,#000,transparent 38%)}.vl-r3-page>.vl-r3-wear__marks{--vl-r3-wear-strength:.12;--vl-r3-wear-color:#beb99e;z-index:1}.vl-r3-page__hero{position:relative;z-index:2;padding-top:clamp(25px,5.5vw,38px)}.vl-r3-page__top{position:relative;min-height:clamp(125px,24vw,160px);padding:0 7%;}.vl-r3-page__brand{position:relative;z-index:3;display:block;width:42%;max-width:237px;height:auto;mix-blend-mode:screen}.vl-r3-page__device{position:absolute;z-index:1;right:-5px;top:calc(-1 * clamp(25px,5.5vw,38px));width:39%;height:auto}.vl-r3-page__shell{position:absolute;z-index:3;left:53%;top:18px;width:7%;max-width:43px;height:auto;transform:rotate(5deg)}.vl-r3-page__dotpatch{position:absolute;z-index:2;width:110px;height:82px;right:8%;top:104px;background:radial-gradient(var(--vl-r3-warning) .8px,transparent 1px) 0 0/4px 4px;clip-path:polygon(0 0,100% 65%,92% 100%,8% 25%);opacity:.75}.vl-r3-page__headlines{position:relative;z-index:4;text-align:center;padding:0 5% 18px}.vl-r3-page__case{display:inline-block;margin:0;background:var(--vl-r3-warning);color:var(--vl-r3-ink);padding:0 7px;font-weight:700;font-size:clamp(21px,4.8vw,31px);line-height:1.18;transform:rotate(-.5deg)}.vl-r3-page__title{display:block;width:100%;height:auto;margin:1px 0 -13px;overflow:visible;color:var(--vl-r3-warning)}.vl-r3-page__title text{fill:currentColor;font-family:Georgia,serif;font-size:75px;font-weight:700;letter-spacing:-3px}.vl-r3-page__subtitle{display:flex;align-items:center;gap:5px;justify-content:center;margin:0;color:var(--vl-r3-warning);font-family:Arial,sans-serif;font-size:clamp(18px,4.4vw,30px);font-weight:700;line-height:1.05;letter-spacing:-.045em}.vl-r3-page__subtitle:before,.vl-r3-page__subtitle:after{content:'';flex:1;max-width:53px;height:6px;border-top:2px solid currentColor;border-bottom:2px solid currentColor}.vl-r3-page__paperstrip{display:table;margin:8px auto 0;padding:2px 30px;background:var(--vl-r3-paper);color:var(--vl-r3-ink);font-family:Arial,sans-serif;font-size:clamp(12px,2.8vw,19px);font-weight:700;transform:rotate(-4deg);line-height:1.1}.vl-r3-page__subrow{display:flex;align-items:center;justify-content:center;gap:7px;margin-top:3px;transform:rotate(-3deg)}.vl-r3-page__issue{font-family:Arial,sans-serif;font-size:clamp(20px,4vw,27px);font-weight:700}.vl-r3-page__zhstrip{padding:0 6px;background:var(--vl-r3-warning);color:var(--vl-r3-ink);font-size:clamp(16px,3.8vw,25px);font-weight:500;line-height:1.25}.vl-r3-page__scene{position:relative;margin:4px -1px 0}.vl-r3-page__scene img{display:block;width:100%;height:auto}.vl-r3-page__scene-caption{position:absolute;left:6%;bottom:17%;padding:3px 7px;background:var(--vl-r3-ink);color:var(--vl-r3-paper);font-family:Arial,sans-serif;font-size:9px;letter-spacing:.13em}.vl-r3-page__scene-band{--vl-r3-band-height:53px;--vl-r3-band-angle:-11deg;position:relative;z-index:5;margin-top:-54px;margin-bottom:28px}.vl-r3-page__scene-band>.vl-r3-wear__marks,.vl-r3-page__footer-band>.vl-r3-wear__marks{--vl-r3-wear-color:#4c4c24;--vl-r3-wear-strength:.36}.vl-r3-page__archive-wrap{position:relative;z-index:3;margin:0 clamp(14px,3.8vw,25px)}.vl-r3-page .vl-r3-archive{--vl-r3-ground:inherit;--vl-r3-warning:inherit;--vl-r3-ink:#292a21;--vl-r3-paper:#c6c2aa;margin-top:0;max-width:100%;padding-bottom:65px}.vl-r3-page__facts{position:relative;z-index:4;margin:-43px clamp(14px,3.8vw,25px) 0;padding:7px clamp(17px,4vw,27px) 40px;background:transparent;isolation:isolate;color:var(--vl-r3-ink);}.vl-r3-page__facts::after{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;background:var(--vl-r3-paper);clip-path:polygon(0 0,23% 1%,42% 0,61% 1.4%,79% 0,100% 1%,99% 29%,100% 49%,99% 98%,82% 99%,63% 98%,42% 100%,19% 99%,1% 99%)}.vl-r3-page__facts-title{margin:0 0 16px;font-size:clamp(16px,3.2vw,21px);font-weight:700;line-height:1.5}.vl-r3-page__facts-list{display:grid;gap:15px;margin:0;padding:0;list-style:none}.vl-r3-page__fact{position:relative;display:grid;grid-template-columns:65px minmax(0,1fr);gap:15px;padding:16px 18px 17px 10px;background:var(--vl-r3-ink);color:var(--vl-r3-paper);clip-path:polygon(0 0,20% 0,22% 2%,70% 1%,73% 0,100% 2%,100% 78%,96% 82%,94% 100%,0 99%);--vl-r3-wear-strength:.2;--vl-r3-wear-color:#bcb79c}.vl-r3-page__number{position:relative;z-index:2;align-self:start;justify-self:center;width:45px;margin-top:-15px;padding:10px 0 15px;text-align:center;border-left:2px solid #77765f;border-right:2px solid #77765f;background:#a4a087;color:#dedbc3;clip-path:polygon(0 0,100% 0,100% 100%,50% 88%,0 100%);font-family:Georgia,serif;font-size:47px;font-weight:700;line-height:1.2;text-shadow:2px 3px #35372b;box-shadow:inset 0 0 0 4px #35362a,inset 0 0 0 5px #b9b49a}.vl-r3-page__fact p{position:relative;z-index:2;margin:0;font-size:clamp(13px,2.35vw,15.5px);font-weight:400;line-height:1.55;letter-spacing:.015em}.vl-r3-page__summary{position:relative;z-index:5;margin:-21px clamp(12px,3.1vw,21px) 0;padding:22px clamp(19px,4.7vw,31px) 27px;background:transparent;isolation:isolate;color:var(--vl-r3-ink);transform:rotate(1deg);box-shadow:inset 0 4px 0 #b0ad96;--vl-r3-wear-strength:.1;--vl-r3-wear-color:#686750}.vl-r3-page__summary::after{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;background:#ccc9b5;clip-path:polygon(0 1%,97% 0,100% 4%,99% 88%,96% 89%,96% 98%,86% 96%,74% 99%,62% 94%,49% 98%,36% 96%,24% 100%,11% 97%,0 98%)}.vl-r3-page__summary p{margin:0;font-size:clamp(13px,2.35vw,15.5px);line-height:1.6;font-weight:400}.vl-r3-page__footer{position:relative;z-index:6;min-height:265px;margin-top:-12px;padding:124px 0 23px;box-sizing:border-box;text-align:center}.vl-r3-page__gun{position:absolute;z-index:3;left:-4px;top:-25px;width:43%;max-width:283px;height:auto;mix-blend-mode:lighten;transform:rotate(-1deg)}.vl-r3-page__footer-band{--vl-r3-band-angle:-9deg;--vl-r3-band-height:49px;position:relative;z-index:2;margin-bottom:31px}.vl-r3-page__footer-brand{position:relative;z-index:4;width:27%;max-width:177px;height:auto;mix-blend-mode:screen}.vl-r3-page__copyright{position:relative;z-index:4;margin:7px 12px 0;font-family:Arial,sans-serif;font-size:clamp(9px,1.8vw,12px);color:#bbb9a9}.vl-r3-page__bottom-edge{height:13px;margin-top:23px;background:var(--vl-r3-warning);clip-path:polygon(0 0,12% 65%,26% 100%,0 100%)}@media(max-width:460px){.vl-r3-page__headlines{padding-left:3%;padding-right:3%;padding-bottom:12px}.vl-r3-page__title{margin-bottom:-8px}.vl-r3-page__top{min-height:123px}.vl-r3-page__scene-band{--vl-r3-band-height:43px;margin-top:-39px;margin-bottom:24px}.vl-r3-page__scene-caption{font-size:7px}.vl-r3-page__fact{grid-template-columns:43px minmax(0,1fr);gap:10px;padding-right:14px;padding-left:5px}.vl-r3-page__number{width:35px;font-size:37px}.vl-r3-page__facts{padding-left:15px;padding-right:15px}.vl-r3-page__footer{min-height:213px;padding-top:85px}.vl-r3-page__footer-band{--vl-r3-band-height:43px;margin-bottom:26px}.vl-r3-page__dotpatch{top:80px;width:78px;height:64px}}
.vl-r3-page__footer{margin-top:22px}.vl-r3-page__gun{top:0}.vl-r3-page__summary{margin-top:12px}
```

```html
<main class="vl-r3-page vl-r3-wear" aria-label="达维镇案件：相关州府新闻剪报板"><span class="vl-r3-wear__marks" aria-hidden="true"></span><header class="vl-r3-page__hero"><div class="vl-r3-page__top"><img class="vl-r3-page__brand" src="SLOT:terra-brand.png" alt="明日方舟 TERRA"><img class="vl-r3-page__device" src="SLOT:top-black-object.png" alt="右上角黑色机械物件与弹药细节"><img class="vl-r3-page__shell" src="SLOT:single-cartridge.png" alt="弹壳"><span class="vl-r3-page__dotpatch" aria-hidden="true"></span></div><div class="vl-r3-page__headlines"><p class="vl-r3-page__case">／达维镇 案件</p><h1 style="margin:0"><svg class="vl-r3-page__title" viewBox="0 0 600 112" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="DAVISTOWN"><defs><path id="vl-r3-longpage-title-arc" d="M14 102Q300 -1 586 102"/></defs><text text-anchor="middle"><textPath href="#vl-r3-longpage-title-arc" startOffset="50%">DAVISTOWN</textPath></text></svg></h1><p class="vl-r3-page__subtitle">CRIMINAL INCIDENT</p><p class="vl-r3-page__paperstrip">NEWS CUTTING BOARD</p><div class="vl-r3-page__subrow"><span class="vl-r3-page__issue">NO.03</span><span class="vl-r3-page__zhstrip">相关州府新闻 剪报板</span></div></div><figure class="vl-r3-page__scene"><img src="SLOT:bank-interior.png" alt="高反差印刷处理的银行大厅，保留原图局部黄色网点"><figcaption class="vl-r3-page__scene-caption">DAVISTOWN / SCENE RECORD 03</figcaption></figure><div class="vl-r3-band vl-r3-wear vl-r3-page__scene-band" role="img" aria-label="场景下缘黄黑警戒带"><svg class="vl-r3-band__arrows" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><pattern id="vl-r3-chevron-long-top" width="94" height="52" patternUnits="userSpaceOnUse" viewBox="0 0 94 52"><path d="M-24 0H23L53 26 23 52H-24L6 26ZM70 0H117L147 26 117 52H70L100 26Z"/></pattern></defs><rect width="100%" height="100%" fill="url(#vl-r3-chevron-long-top)"/></svg><span class="vl-r3-wear__marks" aria-hidden="true"></span></div></header><section class="vl-r3-page__archive-wrap" aria-label="剪报正文"><article class="vl-r3-archive vl-r3-wear"><span class="vl-r3-wear__marks" aria-hidden="true"></span><div class="vl-r3-archive__back">DW.<small>CRIMINAL INCIDENT NEWS · NO.03</small></div><img class="vl-r3-archive__clip" src="SLOT:archive-clip.png" alt="夹持两层报纸的旧金属夹"><header class="vl-r3-archive__masthead"><img class="vl-r3-archive__masthead-art" src="SLOT:archive-masthead.png" alt="The Daily Fortune 财富日报艺术刊头"></header><div class="vl-r3-wear__content"><p class="vl-r3-archive__kicker">读者来信选登 / 关于达维镇事件的另一种解释</p><div class="vl-r3-archive__lead"><div><p class="vl-r3-archive__copy">因此，我们不难发现这个谣言背后巨大的破绽：银行根本不具备驱逐地域居民的权力和能力，而就算它有，它又能通过这样做获得什么呢？它能取得达维镇的征税权吗？别忘了，居民都被它“赶跑了”。</p><p class="vl-r3-archive__copy">它要管领州政府给予工矿业的发展补贴吗？每年发放前都有检查员核实。要么它就只要那一堆低值房地产，然后附带所有热爱公平正义的哥伦比亚人的痛恨？</p></div><figure class="vl-r3-archive__portrait"><img src="SLOT:archive-portrait.png" alt="报纸上的西装男子插画，右上方有弹壳局部叠压"><figcaption>资料图 / 读者来信栏所附人物插画</figcaption></figure></div><div class="vl-r3-archive__continuation"><p class="vl-r3-archive__copy">我的朋友们，我这样说，并不是因为我与银行更加亲近——银行是个机构，不是个能亲近的人——而是我作为专业人士，更需要为你们做出理智的分析。在我们哥伦比亚，所有的银行本质上都是金融公司，是为了盈利而生的私人企业，通过金融服务赚取利润是它们绝对的生存法则。</p><p class="vl-r3-archive__copy">也就是说，一家银行绝对不会去做没有利润可以赚取的事情。哪怕在达维镇，银行因为它所谓的“社会责任”而向那些经济基础不稳固、经济前景不明朗的镇民开放服务，它背后的目的也还是赚取利润。毕竟该地曾经人口基数庞大，银行的策略本应是薄利多销。</p></div></div></article></section><section class="vl-r3-page__facts" aria-labelledby="vl-r3-longpage-facts-heading"><h2 class="vl-r3-page__facts-title" id="vl-r3-longpage-facts-heading">我们可以列举这样几个事实：</h2><ol class="vl-r3-page__facts-list"><li class="vl-r3-page__fact vl-r3-wear"><span class="vl-r3-wear__marks" aria-hidden="true"></span><span class="vl-r3-page__number" aria-hidden="true">1</span><p>银行在达维镇地域运行的整个期间，从未中断服务，提供服务时也并不过分看重客户的经济背景；</p></li><li class="vl-r3-page__fact vl-r3-wear"><span class="vl-r3-wear__marks" aria-hidden="true"></span><span class="vl-r3-page__number" aria-hidden="true">2</span><p>有相当数量的达维镇本地人通过为银行工作维持生活，甚至镇政府在宣布变卖办公大楼后也在银行拥有的地产上办公；</p></li><li class="vl-r3-page__fact vl-r3-wear"><span class="vl-r3-wear__marks" aria-hidden="true"></span><span class="vl-r3-page__number" aria-hidden="true">3</span><p>州政府在劫案后曾调查了银行在达维镇的档案并公开了调查结果，相关合同中并不存在任何欺诈、胁迫或语焉不详的内容，也不存在对特定客户提供特权或歧视性条款的现象，退出机制和协商机制亦颇为完备。</p></li></ol></section><aside class="vl-r3-page__summary vl-r3-wear" aria-label="剪报结语"><span class="vl-r3-wear__marks" aria-hidden="true"></span><div class="vl-r3-wear__content"><p>如果我们一定要以批判性的眼光分析这些事实，那么该地之后的工矿业衰败带来的债务问题最多只能说是银行在自身危机面前试图通过贷款推动其他产业发展，试图力挽狂澜，但策略失败、经营不善导致的。换句话说，银行想做点什么收回自己的利益，却犯了蠢，可要说这一切都是由银行造成，则无疑是倒因为果。</p></div></aside><footer class="vl-r3-page__footer"><img class="vl-r3-page__gun" src="SLOT:footer-handgun.png" alt="页脚证物手枪，保留原有深色场域"><div class="vl-r3-band vl-r3-wear vl-r3-page__footer-band" role="img" aria-label="页脚连续实心箭头警戒带"><svg class="vl-r3-band__arrows" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><pattern id="vl-r3-chevron-long-footer" width="94" height="52" patternUnits="userSpaceOnUse" viewBox="0 0 94 52"><path d="M-24 0H23L53 26 23 52H-24L6 26ZM70 0H117L147 26 117 52H70L100 26Z"/></pattern></defs><rect width="100%" height="100%" fill="url(#vl-r3-chevron-long-footer)"/></svg><span class="vl-r3-wear__marks" aria-hidden="true"></span></div><img class="vl-r3-page__footer-brand" src="SLOT:footer-brand.png" alt="鹰角网络 HYPERGRYPH TERRA"><p class="vl-r3-page__copyright">© 2017–2023 HYPERGRYPH. All rights reserved.</p><div class="vl-r3-page__bottom-edge" aria-hidden="true"></div></footer></main>
```

组装时先读取完整依赖；SLOT替换为当前任务资产，字体别名需实际加载。SVG按资源协议内联。复制实例时更新SVG ID及引用；长文案复核正文净空、页脚遮叠和窄幅换行。

<a id="combination.silver-starlight-longpage"></a>

## 连续银底星光促销长页

风格标签：一级：未来科技风。

产物：社媒长图；粒度：整页长图。

完整展开主视觉、活动时间、六券、折扣、满额赠礼、七图拼贴、六商品、八条规则及特别提醒、页尾标识；依赖券阵经其传递依赖加载票形，银框和色板直接绑定，组合CSS仅做长页布局、局部装饰及原子覆盖。默认max-width 658px；420宽券阵2列、商品仍2列，商品可改1列且正文自然增长。参考658×6165的阅读密度，不固定页面总高、不绝对定位正文；赠礼说明建议6–10行，规则不限字数。层级为连续CSS银底与独立颗粒z=-1，主视觉图片z=1，侧星/吉他z=2，标题与人像z=3；赠礼巨大星是z=-1的CSS折面星形近似，不宣称真实金属摄影。主吊坠、侧星、吉他素材保留原图场域，clip-path只是粗范围裁切，不能视为透明抠图。五连星位于标题上沿，人物图保留模糊且不推断身份。商品素材仅截框内商品封面，外框、暗沟、图注全部真实节点。正文RetroSource 400，标题700，日期Georgia 700，价格Arial 800加2px描边；艺术吊坠和页尾Logo未字体复原。未叠加假掉墨、纸纤维、出纸槽或警戒带，原参考不含这些结构。

### 素材与采用边界

当前吊坠、链条及星饰沿用带底参考裁片；赠礼区大星沿用CSS折面近似，不能标为真实充气金属素材。素材槽说明是后续替换依据，不代表本例已经提供透明金属资产。

```json
{
  "dependencies": [
    "palette.silver-cyan-mono",
    "shape.beveled-metal-frame",
    "combination.silver-coupon-grid"
  ],
  "scope": "整页章节、连续背景、图文层级和素材槽的可复用组合；保留示例外观近似，不代表精确复刻",
  "asset_slots": [
    {
      "slot": "SLOT:starlight-chain-pendant.png",
      "role": "珠链与Starlight艺术吊坠的复杂物体场域裁片；含原有银黑背景和链间2025装饰，非透明图。HTML以粗多边形缩减外围，主标题艺术字未字体复原，不作为整页背景。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:outline-silver-star.png",
      "role": "左上空心银星独立物体，含邻近光晕和少量冷银场域，未精细抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:pointed-chrome-star.png",
      "role": "右上尖角铬星独立物体，含原背景，不是CSS生成的真实反射。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:small-silver-star.png",
      "role": "左侧小金属星与紧邻银底场域，不带活动正文。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:blue-inflated-star.png",
      "role": "右侧青银充气空心星独立物体；保留边缘背景和原始反光。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:black-electric-guitar.png",
      "role": "右侧出边电吉他，原图在右边界已截断；保留原始银底场域，不能补画缺失琴颈或称透明抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:five-chrome-stars.png",
      "role": "活动标题上方五连金属星独立复杂装饰；窄裁片保留星间银灰背景，不包含整块标题条。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:playful-music-product.png",
      "role": "乐游奇妙乐商品封面实物内容区，排除外侧银框及原价文字；折扣区与商品列表复用。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-one.png",
      "role": "第一张赠礼小卡内部模糊人物照片，避开原白边，显示时由CSS补白边和旋转。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-two.png",
      "role": "第二张赠礼小卡内接矩形照片，保留原有模糊，不包含卡片框或文字。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-three.png",
      "role": "第三张赠礼小卡内部模糊人物照片，局部视野较原卡略收紧。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-four.png",
      "role": "第四张赠礼小卡内部模糊照片，排除旋转白边。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-five.png",
      "role": "第五张赠礼小卡内部模糊照片，不识别人脸身份。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-six.png",
      "role": "第二排左侧小卡内部模糊人物照片，白边与角度由CSS承担。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:gift-portrait-seven.png",
      "role": "第二排右侧小卡内部模糊人物照片，内接裁切避免带入背景金属星。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:ardently-love-group-product.png",
      "role": "热爱TF_ING套装的商品封面内容区，跨y3750切片边界，排除CSS需要重建的银色包边与下方图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:never-gonna-stop-product.png",
      "role": "张子墨生日企划商品封面内容区，跨切片连续裁取，不包含外框及图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:infinity-concert-product.png",
      "role": "无限音乐会纪念套装商品摄影及包装内容区；包装上的印字属于商品本身，不是规则段落截图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:shun-summer-product.png",
      "role": "SHUN夏日运动会商品封面内容区，不包含外围银框和页面商品说明。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:ardently-love-solo-product.png",
      "role": "热爱余宇涵个人套装商品封面内容区，图注由可编辑HTML重建。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:landing-plan-art-logo.png",
      "role": "页尾登陆计划四字艺术标识；保留冷银底，使用multiply弱化矩形场域但不视作透明抠图；未字体复原，不包含右下展示水印。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    }
  ],
  "material_contract": {
    "page_background": "整页/章节连续底场由CSS统一承担，不把同一场域切成多张图卡",
    "foreground": "摄影、珠链、吊牌、复杂星饰、艺术Logo为明确素材对象，不由简单轮廓冒充真实材质",
    "seams": "当前参考裁片带原背景，存在接缝；不得把粗clip-path记为透明抠图",
    "text": "正文真实可编辑；艺术字位图不宣称已识别字体或可编辑字形"
  },
  "asset_brief": {
    "subject": "按各槽role定义对象及构图，关联当前主题而非固定品牌",
    "material_and_light": "延续本分支材质与光向；银色对象保留真实反射、厚度和细颗粒，照片保留原色",
    "background": "独立前景优先透明边界；一体场景则保持完整连续背景，二者不可混用",
    "text_handling": "可编辑文字置于HTML；字形参与真实雕刻或艺术标识时作为明确图像槽",
    "composition_and_acceptance": "保留主体完整度、锚点、图文安全区、层级和接触关系；禁带入其他章节正文、状态栏及无关边框",
    "prompt_policy": "记录可参数化素材要求；实际生成prompt按主题填写，不把一条固定prompt作为CSS原子。本示例沿用现有素材。"
  },
  "font_binding": {
    "RetroSource": "思源黑体SourceHanSansSC-VF，实际250–900轴，正文400；标题按组合实值",
    "RetroDisplay": "抖音美好体Bold真实face，文件weight400",
    "RetroNarrow": "寒蝉高黑体Medium真实500；字体匹配为候选替代，非原字体确认"
  }
}
```

```css
.vl-r8-page{box-sizing:border-box;position:relative;isolation:isolate;overflow:hidden;width:100%;max-width:658px;margin-inline:auto;background:radial-gradient(ellipse 70% 10% at 0 11%,#d7c2ce55,transparent 80%),radial-gradient(ellipse 80% 10% at 100% 2%,#c1d29f88,transparent 80%),linear-gradient(to bottom,#819697 0%,var(--vl-silver) 13%,var(--vl-silver) 96%,#161d1d 99.5%,#020303 100%);font-size:16px;line-height:1.6}.vl-r8-page:before{content:'';position:absolute;inset:0;z-index:-1;background:url('asset:svg/screen-grain.svg') repeat;opacity:var(--vl-grain-opacity);pointer-events:none}.vl-r8-page__hero{position:relative;min-height:780px;text-align:center;padding:0 0 65px;background:radial-gradient(ellipse at 50% 28%,#020505 0,transparent 51%)}.vl-r8-page__pendant{position:relative;z-index:1;display:block;width:86%;max-width:566px;height:auto;margin:0 auto;clip-path:polygon(20% 0,74% 0,72% 11%,61% 36%,60% 43%,73% 44%,78% 52%,87% 52%,98% 57%,100% 65%,94% 75%,91% 86%,78% 93%,63% 95%,53% 98%,22% 100%,11% 96%,6% 89%,0 87%,0 75%,5% 65%,14% 59%,16% 53%,26% 47%,39% 43%,26% 27%)}.vl-r8-page__hero-star{position:absolute;z-index:2;display:block;object-fit:contain}.vl-r8-page__hero-star--left{left:6%;top:65px;width:23%;clip-path:polygon(32% 0,49% 24%,96% 22%,80% 56%,91% 100%,51% 84%,24% 99%,24% 67%,0 51%,28% 34%)}.vl-r8-page__hero-star--right{right:16%;top:50px;width:19%;clip-path:polygon(69% 0,65% 35%,100% 39%,70% 51%,79% 81%,51% 62%,39% 100%,40% 62%,0 57%,31% 45%,20% 20%,49% 36%)}.vl-r8-page__credit{position:relative;z-index:3;margin:15px auto 0;width:80%;font-size:16px;font-weight:600;line-height:1.6}.vl-r8-page__title{position:relative;z-index:3;margin:34px 15% 0;font-size:clamp(32px,6.4vw,45px);font-weight:700;line-height:1.1;letter-spacing:-2px}.vl-r8-page__small-star{position:absolute;left:9%;bottom:70px;width:13%;height:auto;clip-path:polygon(32% 0,59% 24%,94% 19%,84% 55%,100% 77%,64% 82%,44% 100%,26% 70%,0 64%,20% 39%)}.vl-r8-page__blue-star{position:absolute;right:3%;bottom:135px;width:19%;height:auto;clip-path:polygon(48% 0,69% 25%,99% 31%,85% 62%,88% 98%,50% 88%,16% 100%,17% 64%,0 35%,34% 27%)}.vl-r8-page__guitar{position:absolute;z-index:2;right:0;bottom:-106px;width:27%;height:auto;clip-path:polygon(99% 0,100% 48%,89% 49%,90% 65%,76% 72%,74% 87%,58% 100%,29% 97%,7% 85%,0 69%,7% 55%,23% 44%,39% 41%,45% 27%,62% 22%)}.vl-r8-page__bar{position:relative;display:table;max-width:80%;margin:0 auto;padding:0 10px;background:#5d6260;color:var(--vl-paper);font-size:24px;font-weight:700;line-height:1.5;letter-spacing:-1px;text-align:center}.vl-r8-page__bar:before,.vl-r8-page__bar:after{content:'';position:absolute;top:-3px;bottom:-3px;width:14px;background:linear-gradient(40deg,transparent 42%,var(--vl-spark) 43% 56%,transparent 57%) top/100% 12px no-repeat,linear-gradient(-40deg,transparent 42%,var(--vl-spark) 43% 56%,transparent 57%) bottom/100% 12px no-repeat}.vl-r8-page__bar:before{left:-9px}.vl-r8-page__bar:after{right:-9px;transform:scaleX(-1)}.vl-r8-page__time{position:relative;padding:38px 8% 77px;text-align:center}.vl-r8-page__dates{position:relative;display:flex;justify-content:center;gap:70px;max-width:330px;margin:49px auto 22px}.vl-r8-page__dates:before{content:'';position:absolute;left:20%;right:20%;height:15px;top:52%;background:linear-gradient(#c7c9c7,#e0e1df 40%,#aaa);box-shadow:0 4px 6px #0004}.vl-r8-page__date{position:relative;box-sizing:border-box;flex:1;min-width:0;padding:10px 10px 15px;border-radius:22px;background:linear-gradient(120deg,#e2e8e6,#cbd3d3 55%,#b0babc);box-shadow:7px 9px 9px #0004,inset 1px 1px 1px #fff9}.vl-r8-page__date:before{content:'';position:absolute;left:20%;right:20%;top:5px;height:6px;background:radial-gradient(circle at 3px 3px,#242a2b 0 2px,#f1f4f2 2px 3px,transparent 3px),radial-gradient(circle at calc(100% - 3px) 3px,#242a2b 0 2px,#f1f4f2 2px 3px,transparent 3px)}.vl-r8-page__month{display:block;border-bottom:3px solid #949d9b;font:700 28px Georgia,serif;letter-spacing:-2px}.vl-r8-page__day{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:4px;font:700 73px/.95 Georgia,serif;letter-spacing:-5px}.vl-r8-page__weekday{font:700 20px/1.2 RetroSource,sans-serif;letter-spacing:0;color:#686f6c;writing-mode:vertical-rl}.vl-r8-page__date-summary{margin:0;font-size:19px;font-weight:700}.vl-r8-page .vl-r8-coupons{max-width:none;padding-top:13px;padding-bottom:0;background:transparent}.vl-r8-page .vl-r8-coupons:before{display:none}.vl-r8-page__activity{position:relative;text-align:center;padding:72px 8% 0}.vl-r8-page__heading{display:flex;flex-direction:column;align-items:center;margin:0;font-weight:700}.vl-r8-page__number{font-size:31px;line-height:1.25;letter-spacing:-1.5px}.vl-r8-page__stars{position:relative;z-index:2;display:block;width:174px;max-width:45%;height:auto;margin:-1px auto -5px}.vl-r8-page__label{display:inline-block;padding:5px 12px 9px;border-radius:5px;background:var(--vl-ink);color:var(--vl-paper);font-size:clamp(28px,5.7vw,39px);line-height:1.15;letter-spacing:-1.5px}.vl-r8-page__copy{position:relative;z-index:2;margin:35px 0 0;font-size:16px;line-height:1.6;font-weight:400}.vl-r8-page__mark{padding:0 4px;color:var(--vl-paper);background:var(--vl-ink);box-decoration-break:clone;-webkit-box-decoration-break:clone}.vl-r8-page__discount{font-size:25px;font-family:Arial,sans-serif;font-weight:700;line-height:1}.vl-r8-page .vl-r8-metal{--frame-light:var(--vl-metal-light);--frame-mid:var(--vl-metal-mid);--frame-dark:var(--vl-metal-dark);--frame-slot:var(--vl-silver-light);background-color:var(--frame-mid);max-width:none}.vl-r8-page__featured{width:50%;max-width:274px;min-width:210px;margin:55px auto 0}.vl-r8-page__price-meta{margin:16px 0 0;font-size:17px;line-height:1.5}.vl-r8-page__price-meta del{color:#747d7b}.vl-r8-page__price{margin:0;font:800 clamp(58px,11vw,76px)/1.05 Arial,sans-serif;letter-spacing:-4px;color:var(--vl-paper);-webkit-text-stroke:2px var(--vl-ink);paint-order:stroke fill}.vl-r8-page__price sup{display:inline-block;vertical-align:top;margin:6px 0 0 6px;font:700 15px Arial,sans-serif;color:var(--vl-ink);-webkit-text-stroke:0}.vl-r8-page__gift{isolation:isolate;padding-top:82px;padding-bottom:85px}.vl-r8-page__gift:before{content:'';position:absolute;z-index:-1;left:-21%;right:-18%;top:190px;bottom:-68px;clip-path:polygon(19% 0,49% 34%,100% 4%,75% 48%,96% 88%,58% 77%,37% 100%,33% 67%,0 72%,28% 48%);background:conic-gradient(from 28deg at 51% 51%,#d8e4e7 0deg,#688188 18deg,#edf3f2 42deg,#5d777d 73deg,#bccfd4 103deg,#f4f7f4 143deg,#729095 177deg,#e1e8e7 208deg,#779096 246deg,#d1e0e1 282deg,#536d74 309deg,#eff6f4 340deg,#d8e4e7 360deg);opacity:.82;filter:drop-shadow(0 3px 3px #344d5555)}.vl-r8-page__gift .vl-r8-page__copy{margin-top:42px}.vl-r8-page__collage{position:relative;z-index:3;display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:29px 5px;max-width:516px;margin:126px auto 0;padding:0 1%}.vl-r8-page__portrait{box-sizing:border-box;grid-column:span 2;display:block;width:100%;height:auto;aspect-ratio:100/148;object-fit:cover;border:1px solid #fff;border-radius:8px;box-shadow:1px 2px 3px #0002;background:var(--vl-silver)}.vl-r8-page__portrait:nth-child(1){transform:rotate(-3deg)}.vl-r8-page__portrait:nth-child(2){transform:translateY(-9px) rotate(-6deg)}.vl-r8-page__portrait:nth-child(3){transform:rotate(2deg)}.vl-r8-page__portrait:nth-child(4){transform:rotate(-4deg)}.vl-r8-page__portrait:nth-child(5){transform:translateY(-5px) rotate(3deg)}.vl-r8-page__portrait:nth-child(6){grid-column:4/span 2;transform:rotate(-3deg)}.vl-r8-page__portrait:nth-child(7){grid-column:6/span 2;transform:rotate(4deg)}.vl-r8-page__products{position:relative;z-index:2;padding:45px 6.7% 0;text-align:center}.vl-r8-page__product-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40px 32px;margin:44px 0 0}.vl-r8-page__product{min-width:0;margin:0}.vl-r8-page__caption{margin:9px -5px 0;font-size:clamp(15px,3.3vw,22px);line-height:1.28;font-weight:400;overflow-wrap:anywhere}.vl-r8-page__limited{margin:50px 0 0;font-size:15px;line-height:1.7}.vl-r8-page__rules{padding:108px 9.7% 0}.vl-r8-page__rules-list{margin:47px 0 0;padding:0;list-style:none;counter-reset:vl-r8-rule;font-size:16px;line-height:1.75;font-weight:400}.vl-r8-page__rules-list>li{counter-increment:vl-r8-rule}.vl-r8-page__rules-list>li:before{content:counter(vl-r8-rule) '.'}.vl-r8-page__subrules{margin:0;padding:0;list-style:none}.vl-r8-page__subrules li{text-indent:1.3em}.vl-r8-page__subrules li:before{content:'· ';margin-right:.35em}.vl-r8-page__notice{margin-top:18px;font-size:16px;line-height:1.75}.vl-r8-page__notice h3{margin:0 0 15px;text-align:center;font-size:16px;font-weight:400}.vl-r8-page__notice p{margin:0}.vl-r8-page__footer{padding:48px 0 95px;text-align:center}.vl-r8-page__logo{display:block;width:128px;max-width:25%;height:auto;margin:auto;mix-blend-mode:multiply}@media(max-width:480px){.vl-r8-page{font-size:14px}.vl-r8-page__hero{min-height:0;padding-bottom:70px}.vl-r8-page__hero-star--left{top:42px}.vl-r8-page__hero-star--right{top:32px}.vl-r8-page__credit{font-size:12px;margin-top:12px}.vl-r8-page__title{margin-top:24px;font-size:32px}.vl-r8-page__small-star{bottom:26px}.vl-r8-page__blue-star{bottom:80px}.vl-r8-page__guitar{bottom:-85px}.vl-r8-page__time{padding-top:35px;padding-bottom:60px}.vl-r8-page__bar{font-size:21px}.vl-r8-page__dates{max-width:290px;gap:50px;margin-top:40px}.vl-r8-page__month{font-size:25px}.vl-r8-page__day{font-size:63px}.vl-r8-page__weekday{font-size:17px}.vl-r8-page__activity{padding-left:7%;padding-right:7%;padding-top:65px}.vl-r8-page__copy{font-size:14px}.vl-r8-page__featured{margin-top:40px}.vl-r8-page__gift{padding-bottom:62px}.vl-r8-page__gift:before{top:185px;left:-32%;right:-29%}.vl-r8-page__collage{gap:23px 4px;margin-top:88px}.vl-r8-page__portrait{border-radius:5px}.vl-r8-page__products{padding-left:6%;padding-right:6%}.vl-r8-page__product-grid{gap:29px 20px;margin-top:35px}.vl-r8-page .vl-r8-metal{--frame-band:7px}.vl-r8-page__caption{font-size:15px;line-height:1.45}.vl-r8-page__rules{padding:78px 8% 0}.vl-r8-page__rules-list{margin-top:35px;font-size:14px;line-height:1.9}.vl-r8-page__notice{font-size:14px;line-height:1.9}.vl-r8-page__footer{padding-top:40px;padding-bottom:80px}}
```

```html
<main class="vl-r8-palette vl-r8-page"><header class="vl-r8-page__hero"><img class="vl-r8-page__pendant" src="SLOT:starlight-chain-pendant.png" alt="I FOUND YOU IN THE Starlight"><img class="vl-r8-page__hero-star vl-r8-page__hero-star--left" src="SLOT:outline-silver-star.png" alt=""><img class="vl-r8-page__hero-star vl-r8-page__hero-star--right" src="SLOT:pointed-chrome-star.png" alt=""><p class="vl-r8-page__credit">TF_ING（童禹坤、邓佳鑫、穆祉丞、张子墨、黄朔）<br>张峻豪、余宇涵</p><h1 class="vl-r8-page__title">登陆计划<br>双十一惊喜活动</h1><img class="vl-r8-page__small-star" src="SLOT:small-silver-star.png" alt=""><img class="vl-r8-page__blue-star" src="SLOT:blue-inflated-star.png" alt=""><img class="vl-r8-page__guitar" src="SLOT:black-electric-guitar.png" alt="黑色电吉他装饰"></header><section class="vl-r8-page__time"><h2 class="vl-r8-page__bar">★ 活动时间 ★</h2><div class="vl-r8-page__dates"><div class="vl-r8-page__date"><span class="vl-r8-page__month">2025.11</span><span class="vl-r8-page__day">11<span class="vl-r8-page__weekday">周二</span></span></div><div class="vl-r8-page__date"><span class="vl-r8-page__month">2025.11</span><span class="vl-r8-page__day">20<span class="vl-r8-page__weekday">周四</span></span></div></div><p class="vl-r8-page__date-summary">11月11日–11月20日</p></section><section class="vl-r8-palette vl-r8-coupons"><h2 class="vl-r8-coupons__heading"><span class="vl-r8-coupons__number">活动一</span><img class="vl-r8-coupons__stars" src="SLOT:five-chrome-stars.png" alt=""><span class="vl-r8-coupons__label">「满减优惠」</span></h2><p class="vl-r8-coupons__intro">购买登陆计划双十一活动商品<br>单笔订单实付金额满足以下条件即可使用相应优惠券<br>优惠券将发放到高级账号里，请注意查收<br><span class="vl-r8-coupons__emphasis">*单笔订单仅限使用一张优惠券，且不可叠加使用</span></p><div class="vl-r8-coupons__grid"><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>5</div><p class="vl-r8-ticket__condition">满60可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>10</div><p class="vl-r8-ticket__condition">满100可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>30</div><p class="vl-r8-ticket__condition">满200可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>50</div><p class="vl-r8-ticket__condition">满300可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>70</div><p class="vl-r8-ticket__condition">满400可用</p><div class="vl-r8-ticket__foot">优惠券</div></article><article class="vl-r8-ticket"><span class="vl-r8-ticket__surface" aria-hidden="true"></span><div class="vl-r8-ticket__amount"><span class="vl-r8-ticket__currency">¥</span>100</div><p class="vl-r8-ticket__condition">满500可用</p><div class="vl-r8-ticket__foot">优惠券</div></article></div></section><section class="vl-r8-page__activity"><h2 class="vl-r8-page__heading"><span class="vl-r8-page__number">活动二</span><img class="vl-r8-page__stars" src="SLOT:five-chrome-stars.png" alt=""><span class="vl-r8-page__label">「限时折扣」</span></h2><p class="vl-r8-page__copy">活动期间，乐游奇妙乐单人款<br>将享受限时折扣 <strong class="vl-r8-page__mark vl-r8-page__discount">50%</strong></p><div class="vl-r8-page__featured"><figure class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:playful-music-product.png" alt="乐游奇妙乐单人款商品封面"></div></div></figure></div><p class="vl-r8-page__price-meta"><del>原价：¥79</del> <span class="vl-r8-page__mark">限时价</span></p><p class="vl-r8-page__price">39.5<sup>¥</sup></p></section><section class="vl-r8-page__activity vl-r8-page__gift"><h2 class="vl-r8-page__heading"><span class="vl-r8-page__number">活动三</span><img class="vl-r8-page__stars" src="SLOT:five-chrome-stars.png" alt=""><span class="vl-r8-page__label">「满额赠礼」</span></h2><p class="vl-r8-page__copy">活动期间，<br>同一账号购买登陆计划双十一活动商品订单<br>累计实付金额<span class="vl-r8-page__mark">满500元</span><br><br>可获赠指定小卡一张<br>（共7款单人小卡，备注指定款式）<br><span class="vl-r8-page__mark">※如无备注，则随机发货</span></p><div class="vl-r8-page__collage" aria-label="七款赠礼小卡，原图人物已模糊"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-one.png" alt="赠礼小卡款式一，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-two.png" alt="赠礼小卡款式二，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-three.png" alt="赠礼小卡款式三，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-four.png" alt="赠礼小卡款式四，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-five.png" alt="赠礼小卡款式五，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-six.png" alt="赠礼小卡款式六，模糊人物图"><img class="vl-r8-page__portrait" src="SLOT:gift-portrait-seven.png" alt="赠礼小卡款式七，模糊人物图"></div></section><section class="vl-r8-page__products"><h2 class="vl-r8-page__bar">★ 活动商品 ★</h2><div class="vl-r8-page__product-grid"><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:ardently-love-group-product.png" alt="2025音乐会热爱TF_ING套装封面"></div></div></div><figcaption class="vl-r8-page__caption">2025音乐会《热爱》<br>TF_ING套装</figcaption></figure><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:never-gonna-stop-product.png" alt="张子墨十七岁生日特别企划商品封面"></div></div></div><figcaption class="vl-r8-page__caption">张子墨十七岁生日特别企划</figcaption></figure><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:infinity-concert-product.png" alt="无限音乐会张峻豪纪念套装封面"></div></div></div><figcaption class="vl-r8-page__caption">无限音乐会张峻豪纪念套装</figcaption></figure><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:shun-summer-product.png" alt="张峻豪2025夏日运动会线上官网特典版商品封面"></div></div></div><figcaption class="vl-r8-page__caption">张峻豪2025夏日运动会<br>线上官网特典版</figcaption></figure><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:ardently-love-solo-product.png" alt="2025音乐会热爱余宇涵个人套装封面"></div></div></div><figcaption class="vl-r8-page__caption">2025音乐会《热爱》<br>余宇涵个人套装</figcaption></figure><figure class="vl-r8-page__product"><div class="vl-r8-metal"><div class="vl-r8-metal__recess"><div class="vl-r8-metal__slot"><img class="vl-r8-metal__image" src="SLOT:playful-music-product.png" alt="乐游奇妙乐单人款商品封面"></div></div></div><figcaption class="vl-r8-page__caption">乐游奇妙乐单人款</figcaption></figure></div><p class="vl-r8-page__limited"><span class="vl-r8-page__mark">※ 所有活动商品限量出售，售完即止</span></p></section><section class="vl-r8-page__rules"><h2 class="vl-r8-page__bar">★ 活动规则 ★</h2><ol class="vl-r8-page__rules-list"><li>双十一活动商品11月11日20:00上架开售。</li><li>本活动<span class="vl-r8-page__mark">仅限登陆计划粉丝俱乐部高级会员参与。</span>每款活动商品的具体购买规则，请以各商品详情页内的“购买须知”为准。</li><li>本次活动售卖商品系为首次销售预留的退换备用库存商品，因长时间存放等原因可能存在瑕疵，该等瑕疵不影响商品使用，提交订单即视为购买人已知悉并接受商品存在瑕疵，介意勿拍。</li><li>活动商品非因质量问题不支持退换货。</li><li>若订单发生部分退款，致使累计实付金额不再满足赠礼条件，赠品须随商品一并退回。</li><li>如需申请售后，请在订单上提交售后，提供完整的开箱视频（开箱视频需拍到清晰快递面单以及产品快递包装六面以确保包装完整，视频清晰，过程全程处于视频画框内）。</li><li>所有订单及获赠小卡将于付款成功且活动结束后15个工作日内统一安排发货（发货时间仅供参考，具体发货时间以实际情况为准，如遇不可抗力因素，则顺延发货）。</li><li>优惠券使用说明：<ul class="vl-r8-page__subrules"><li>活动期间，所有登陆计划高级会员，每个账号每个档位各发放3张优惠券，共计18张，直接发放至账号中，请前往【我的】-【我的优惠券】页面查收。</li><li>11月11日00:00开始，系统将为在有效期内的登陆计划高级会员账号发放优惠券。此后注册的高级会员，优惠券将在开通或续费高会后的6小时内发放至账号中。</li><li>优惠券使用有效期为<span class="vl-r8-page__mark">2025年11月11日00:00至2025年11月20日24:00</span>，逾期失效。</li><li>仅活动商品可使用优惠券，且单笔订单中活动商品总金额若不满足满减金额亦无法使用。</li><li>订单售后仅在全额退款时，可返还该优惠券。</li></ul></li></ol><aside class="vl-r8-page__notice"><h3><span class="vl-r8-page__mark">【特别提醒】</span></h3><p>1.优惠券仅支持在“时代峰峻 Fanclub APP”最新版本v2.5.0及以上版本中使用；TF FAMILY FANCLUB微信小程序不支持使用优惠券。</p><p>2.如提交订单，则视为认可并同意本规则的全部内容。</p></aside></section><footer class="vl-r8-page__footer"><img class="vl-r8-page__logo" src="SLOT:landing-plan-art-logo.png" alt="登陆计划"></footer></main>
```

组装时先读取完整依赖；SLOT替换为当前任务资产，字体别名需实际加载。SVG按资源协议内联。复制实例时更新SVG ID及引用；长文案复核正文净空、页脚遮叠和窄幅换行。

<a id="combination.tavern-directory-longpage"></a>

## 街景酒馆目录长页

风格标签：二级：复古商业风 / 怀旧商品目录。

产物：社媒长图；粒度：整页长图。

完整长页实际展开摄影目录、纸槽活动组与两类原子节点；需按依赖顺序合并CSS，本条仅增页面绑定和覆盖。最大658px，420px自动单列商户与任务，整页高度由11个商户、地图、兑换、三步群聊、发布规则、杯垫陈列、抽奖积分及任务正文自然撑开，不锁定8718px。目录保持首张大图加五排双列，窄屏为11张连续单列；可增加排数，章节不随意删减。照片z层沿用目录，纸槽沿用机身0/槽1/纸2/前唇3/便笺4；纸面颗粒为独立低透明层，正文z1不做透明掉墨。主艺术标题为独立Logo图，未字体复原；橙牌RetroSource750、正文400、店名600–650，英文辅助Arial。群聊操作界面以可编辑CSS节点近似，明确不是原始截图；无需授权外网或JS。所有行为是本页锚点演示，四街区导航不伪造动态筛选，地图箭头用于章节跳转而非翻页。书册为真实复杂物体裁片；不得替换成整段说明截图。

### 素材与采用边界

目录摄影、纸本说明及奖品沿用已有素材；部分底色接缝、店名字形和纸纹强度有近似。保持同一柜底贯穿、出纸槽与便笺层级，不将示例称作完整像素复刻。

```json
{
  "dependencies": [
    "combination.tavern-shelf-directory",
    "combination.tavern-paper-dispenser",
    "shape.shelf-profile",
    "palette.tavern-umber-orange"
  ],
  "scope": "整页章节、连续背景、图文层级和素材槽的可复用组合；保留示例外观近似，不代表精确复刻",
  "asset_slots": [
    {
      "slot": "SLOT:shanghai-wine-title.png",
      "role": "主标题艺术字与小红书艺术Logo整体；保留原深红棕不透明场域及下缘轻渐变，未进行字体复原，不含手机状态栏。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:shanghai-street-hero.png",
      "role": "首屏建筑、行人与道路独立街景摄影；裁掉上方艺术标题及三列小字，不包含下方日期导航。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:silver-eye-wide.png",
      "role": "首张Silver Eye室内摄影的无文字矩形区域；原下缘被文件夹遮挡，取遮挡上方范围并由CSS控制宽图比例，不含图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:wugong-front.png",
      "role": "武宫门店摄影，避开白衬边与下方签头；图像底部原被图注遮挡。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:mandrill-front.png",
      "role": "Mandrill门店与青蓝露台摄影，保留霓虹和植物原色，不含纸签。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:brut-eatery-front.png",
      "role": "悦璞食堂树荫与入口摄影，跨切片裁取同一全图区域，避开图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:riink-neon.png",
      "role": "RIINK紫红霓虹轮滑空间独立摄影，无褐色滤镜，无图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:bites-brews-interior.png",
      "role": "Bites and Brews窗边室内摄影，裁片不含文件夹店名。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:barbarian-interior.png",
      "role": "Barbarian酒柜与暖黄灯光摄影，保留摄影内部真实商标，不含页面图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:deck-street.png",
      "role": "甲板老建筑街景摄影；底部避开纸签，不含店名与短评。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:lili-sparkling-entry.png",
      "role": "Lili Sparkling蓝色入口摄影，无下方纸签。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:koya-bistro-night.png",
      "role": "KOYA夜景摄影，原生投影Logo属于照片内容，裁片止于签头上方。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:silver-eye-detail.png",
      "role": "Silver Eye第二张室内摄影，保留圆镜和座椅，不含图注。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:jufuchang-open-book.png",
      "role": "展开书册这一复杂真实物体，包含其印刷页面但不是将说明纸段截图代替HTML；保留书册边沿极少量原柜底，无透明抠图，不含下方搁板和两侧箭头。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:map-sticker-gift.png",
      "role": "地图册与贴纸奖品物体；保留局部赭纸不透明场域，无规则文字，非透明素材。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:stamp-pass.png",
      "role": "绿色集章卡独立奖品物体；保留四角局部纸面，非透明抠图。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:red-knit-bag.png",
      "role": "红色针织手提包奖品；保留原赭纸场域，不含左侧兑换文案，不假装去底。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:coaster-mini-prize.png",
      "role": "发布奖励中的小型杯垫实物组；保留原纸背景，排除左侧正文。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:mascot-figurine.png",
      "role": "土拨薯玩偶手办独立复杂物体；保留赭纸背景，非CSS伪造摄影。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    },
    {
      "slot": "SLOT:coaster-display.png",
      "role": "底部杯垫实物陈列组；保留物体间原红棕与橙色光场及真实投影，不透明矩形裁片，未含标题、抽奖按钮或木搁板。",
      "source_kind": "任务素材；参考裁片不打包为库默认图片",
      "replace_when": "更换主题或需要消除裁片底色时替换此槽，保持对应物体与空间关系"
    }
  ],
  "material_contract": {
    "page_background": "整页/章节连续底场由CSS统一承担，不把同一场域切成多张图卡",
    "foreground": "摄影、珠链、吊牌、复杂星饰、艺术Logo为明确素材对象，不由简单轮廓冒充真实材质",
    "seams": "当前参考裁片带原背景，存在接缝；不得把粗clip-path记为透明抠图",
    "text": "正文真实可编辑；艺术字位图不宣称已识别字体或可编辑字形"
  },
  "asset_brief": {
    "subject": "按各槽role定义对象及构图，关联当前主题而非固定品牌",
    "material_and_light": "延续本分支材质与光向；银色对象保留真实反射、厚度和细颗粒，照片保留原色",
    "background": "独立前景优先透明边界；一体场景则保持完整连续背景，二者不可混用",
    "text_handling": "可编辑文字置于HTML；字形参与真实雕刻或艺术标识时作为明确图像槽",
    "composition_and_acceptance": "保留主体完整度、锚点、图文安全区、层级和接触关系；禁带入其他章节正文、状态栏及无关边框",
    "prompt_policy": "记录可参数化素材要求；实际生成prompt按主题填写，不把一条固定prompt作为CSS原子。本示例沿用现有素材。"
  },
  "font_binding": {
    "RetroSource": "思源黑体SourceHanSansSC-VF，实际250–900轴，正文400；标题按组合实值",
    "RetroDisplay": "抖音美好体Bold真实face，文件weight400",
    "RetroNarrow": "寒蝉高黑体Medium真实500；字体匹配为候选替代，非原字体确认"
  }
}
```

```css
.vl-r9-page{box-sizing:border-box;max-width:658px;width:100%;margin-inline:auto;overflow:hidden;background:var(--vl-cabinet);font-size:20px;line-height:1.75}.vl-r9-page *{box-sizing:border-box}.vl-r9-page-hero{position:relative;padding-top:52px;background:linear-gradient(var(--vl-cabinet-deep),var(--vl-cabinet));isolation:isolate}.vl-r9-page-brand{display:flex;justify-content:space-between;margin:0 8% 32px;font-family:Arial,sans-serif;font-size:10px;line-height:1.3}.vl-r9-page-title-art{position:relative;z-index:2;display:block;width:87%;height:auto;margin:0 auto -18px}.vl-r9-page-scene{position:relative;margin:0}.vl-r9-page-scene::after{content:'';position:absolute;inset:0 0 auto;height:62px;background:linear-gradient(var(--vl-cabinet),transparent)}.vl-r9-page-scene img{display:block;width:100%;height:auto}.vl-r9-page-entry{position:relative;padding:22px 4% 40px;background:linear-gradient(#323433,#434342);isolation:isolate}.vl-r9-page-entry::before{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;background:url('asset:svg/screen-grain.svg');opacity:.09}.vl-r9-page-invite{display:grid;grid-template-columns:1fr 1.5fr;gap:20px;align-items:center;padding:0 4% 16px;border-bottom:1px solid #b2afa338}.vl-r9-page-date{font-family:Arial,RetroSource,sans-serif;font-weight:650;font-style:italic;font-size:clamp(24px,5.2vw,36px);line-height:1.08}.vl-r9-page-date small{font-size:11px;font-weight:400}.vl-r9-page-invite p{margin:0;text-align:right;font-size:clamp(18px,3.9vw,26px);line-height:1.4}.vl-r9-page-benefit{text-align:center;margin:17px 0 24px;font-size:clamp(20px,4.2vw,28px);font-weight:600}.vl-r9-page-nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:clamp(8px,3vw,26px);margin-top:36px}.vl-r9-page-nav a{display:flex;align-items:center;justify-content:center;min-height:70px;padding:7px 3px;border-radius:12px;color:#464642;text-decoration:none;font-size:clamp(19px,4.4vw,31px);font-weight:750;letter-spacing:-1px;background:repeating-linear-gradient(0deg,#ffffff55 0 1px,#0000000a 1px 3px),#aaa9a3;border:3px solid #5f605b;box-shadow:inset 0 2px #e1dcd1,inset 0 -3px #55534e,0 5px 7px #0009;transform:perspective(180px) rotateX(8deg)}.vl-r9-page-nav a:first-child{background:repeating-linear-gradient(0deg,#ffffff44 0 1px,#00000009 1px 3px),var(--vl-orange);color:var(--vl-ink)}.vl-r9-page-awning{height:69px;background:linear-gradient(#b58c69 0 28%,#a77e5d 29% 65%,#97704e 66%);clip-path:polygon(5% 0,95% 0,100% 30%,100% 95%,97% 100%,94% 95%,90% 100%,86% 95%,82% 100%,78% 95%,74% 100%,70% 95%,66% 100%,62% 95%,58% 100%,54% 95%,50% 100%,46% 95%,42% 100%,38% 95%,34% 100%,30% 95%,26% 100%,22% 95%,18% 100%,14% 95%,10% 100%,6% 95%,2% 100%,0 95%,0 30%);filter:drop-shadow(0 8px 5px #160700)}.vl-r9-page .vl-r9-directory-row{padding-top:42px}.vl-r9-page .vl-r9-directory-row:first-child{padding-top:28px}.vl-r9-page-map{padding-top:46px;padding-bottom:var(--vl-shelf-depth)}.vl-r9-page-map h2{text-align:center;margin:0 0 24px;font-size:23px;font-weight:400}.vl-r9-page-map h2::after{content:'';display:block;width:0;height:0;border-left:14px solid transparent;border-right:14px solid transparent;border-top:12px solid var(--vl-cream);margin:8px auto 0}.vl-r9-page-map-stage{position:relative;width:91%;margin:auto}.vl-r9-page-book{display:block;width:100%;height:auto;box-shadow:0 4px 8px #17050077}.vl-r9-page-map-arrow{position:absolute;top:48%;width:20px;height:32px;color:var(--vl-cream);text-decoration:none;font-size:38px;line-height:1}.vl-r9-page-map-arrow:first-of-type{left:-7%}.vl-r9-page-map-arrow:last-of-type{right:-7%}.vl-r9-page .vl-r9-dispenser{padding-top:95px}.vl-r9-page-section{padding-top:96px}.vl-r9-page-section .vl-r9-dispenser-heading{margin-bottom:45px}.vl-r9-page-paper{position:relative;width:87%;margin:auto;padding:28px clamp(24px,5vw,40px);background:linear-gradient(112deg,#ffffff06,transparent 47%,#31150812),var(--vl-paper);border:1px solid #c8996555;box-shadow:inset 1px 0 #e7ba8144,2px 4px 7px #21060088;color:var(--vl-cream)}.vl-r9-page-paper::after{content:'';position:absolute;inset:0;pointer-events:none;background:url('asset:svg/screen-grain.svg');opacity:.06}.vl-r9-page-paper>*{position:relative;z-index:1}.vl-r9-page-paper h3{font-size:clamp(21px,4.3vw,29px);font-weight:650;line-height:1.6;margin:0 -15px 27px;padding:0 5px 19px;border-bottom:1px solid #613319;text-align:center}.vl-r9-page-step{display:grid;grid-template-columns:23px 75px minmax(0,1fr);gap:10px;align-items:start;margin:26px 0}.vl-r9-page-step .vl-r9-dispenser-dot{margin-top:6px}.vl-r9-page-step b{font-family:Arial,sans-serif;font-size:24px;font-weight:600}.vl-r9-page-step p{margin:0;font-size:21px;line-height:1.85}.vl-r9-page-ui{margin:12px auto 30px;max-width:330px;width:83%;padding:14px;background:#847229;color:#f7e8bd;border:1px solid #3d260c;box-shadow:4px 4px 0 #51300c55;font-size:13px;line-height:1.6}.vl-r9-page-ui-head{display:flex;gap:12px;align-items:center}.vl-r9-page-avatar{display:grid;place-items:center;width:47px;height:47px;border-radius:50%;background:#ffd45b;color:#642e13;font-size:26px;font-weight:650}.vl-r9-page-ui strong{font-size:17px;font-weight:650}.vl-r9-page-ui p{margin:9px 0}.vl-r9-page-ui a{display:block;text-align:center;margin-top:12px;padding:6px;color:inherit;text-decoration:none;background:#ffffff1c;outline:2px solid var(--vl-orange);outline-offset:5px}.vl-r9-page-ui--dark{background:#0c0c10;color:#eee;padding:15px;max-width:350px;width:90%}.vl-r9-page-ui--dark h4{font-size:15px;font-weight:500;text-align:center;margin:0 0 15px}.vl-r9-page-ui-room{display:flex;align-items:center;gap:10px;padding:15px 10px;background:#222227;border-radius:12px}.vl-r9-page-ui-room p{flex:1;margin:0;font-size:13px}.vl-r9-page-ui-room a{margin:0;padding:4px 8px;outline:none;background:#ff164b;border-radius:20px;font-size:12px;white-space:nowrap}.vl-r9-page-paper-footer{display:flex;justify-content:space-between;align-items:center;margin-top:24px;font-family:Arial,sans-serif;font-size:9px}.vl-r9-page-paper-footer i{width:27%;height:1px;background:#d7b48799}.vl-r9-page-paper-footer span:last-child{border:1px solid #d7b48777;padding:0 4px}.vl-r9-page .vl-r9-page-paper-shelf{padding:0 0 var(--vl-shelf-depth)}.vl-r9-page-publish p{margin:0 0 17px;font-size:21px;line-height:1.85}.vl-r9-page-publish ol{list-style:none;padding:0;margin:15px 0 28px}.vl-r9-page-publish li{margin:10px 0;font-size:22px}.vl-r9-page-publish em{font-style:normal;color:#ffd06f;font-weight:600}.vl-r9-page-publish-rewards{border-top:2px dashed #754724;border-bottom:2px dashed #754724;margin:23px -12px;padding:19px 10px}.vl-r9-page-publish-reward{display:grid;grid-template-columns:23px minmax(0,1fr) 88px;gap:14px;align-items:center;margin:12px 0}.vl-r9-page-publish-reward p{font-size:18px;margin:0}.vl-r9-page-publish-reward img{width:100%;height:auto;display:block}.vl-r9-page-lottery{padding-top:105px;background:radial-gradient(ellipse at 48% 36%,#d970184d,transparent 53%),var(--vl-cabinet)}.vl-r9-page-lottery .vl-r9-dispenser-heading{padding:0 12%;margin-bottom:12px}.vl-r9-page-lottery .vl-r9-dispenser-sign{max-width:none;padding:16px 12px 20px;border-radius:28px;border-color:#211a12;font-size:25px}.vl-r9-page-lottery .vl-r9-dispenser-sign strong{display:block;color:#ffe371;font-size:clamp(29px,6.6vw,45px);line-height:1.35;font-weight:750}.vl-r9-page-prize-note{margin:0 16% 13px;font-size:14px;color:#d7b18d}.vl-r9-page-coasters{padding:0 0 var(--vl-shelf-depth)}.vl-r9-page-coasters img{display:block;width:80%;height:auto;margin:auto}.vl-r9-page-lottery-action{text-align:center;padding:26px 5% 75px}.vl-r9-page-button{display:inline-block;padding:14px 45px;border:1px solid #ffa765;border-radius:40px;background:var(--vl-orange-deep);color:#fff0d8;font-family:RetroSource,sans-serif;font-size:23px;font-weight:500;text-decoration:none;box-shadow:inset 0 1px 3px #ffdaaa55,0 3px 5px #20050055}.vl-r9-page-lottery-action p{margin:31px 0 0;font-size:20px;font-weight:550}.vl-r9-page-task{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:15px;align-items:center;margin:10px 3% 70px;padding:25px 28px;background:#813803;border:1px solid #a3521455;border-radius:16px;box-shadow:0 3px 4px #26090066}.vl-r9-page-task h3{font-size:23px;font-weight:600;margin:0 0 6px}.vl-r9-page-task p{margin:0;font-size:20px}.vl-r9-page-task .vl-r9-page-button{padding:9px 25px;font-size:20px}.vl-r9-page-ending{text-align:center;margin:0;padding:0 8% 38px;font-size:13px;color:#c49c7c}@media(max-width:460px){.vl-r9-page{font-size:17px}.vl-r9-page-hero{padding-top:30px}.vl-r9-page-brand{margin-bottom:23px}.vl-r9-page-title-art{margin-bottom:-8px}.vl-r9-page-nav{gap:8px;margin-top:25px}.vl-r9-page-nav a{min-height:53px;font-size:21px}.vl-r9-page-awning{height:49px}.vl-r9-page-invite{gap:10px}.vl-r9-page-date{font-size:25px}.vl-r9-page-invite p{font-size:18px}.vl-r9-page .vl-r9-dispenser{padding-top:64px}.vl-r9-page-section{padding-top:64px}.vl-r9-page-paper{width:88%;padding:25px 24px}.vl-r9-page-step{grid-template-columns:19px 58px minmax(0,1fr);gap:7px}.vl-r9-page-step b{font-size:20px}.vl-r9-page-step p,.vl-r9-page-publish p{font-size:18px}.vl-r9-page-step .vl-r9-dispenser-dot{width:19px;height:19px}.vl-r9-page-ui{width:92%}.vl-r9-page-publish li{font-size:19px}.vl-r9-page-publish-reward{grid-template-columns:19px minmax(0,1fr) 67px;gap:8px}.vl-r9-page-publish-reward p{font-size:16px}.vl-r9-page-lottery{padding-top:70px}.vl-r9-page-lottery .vl-r9-dispenser-heading{padding-inline:9%}.vl-r9-page-lottery .vl-r9-dispenser-sign{font-size:21px}.vl-r9-page-task{padding:22px 18px;grid-template-columns:minmax(0,1fr)}.vl-r9-page-task .vl-r9-page-button{justify-self:end}.vl-r9-page-task h3{font-size:21px}.vl-r9-page-task p,.vl-r9-page-lottery-action p{font-size:17px}}
```

```html
<main class="vl-r9-palette vl-r9-page"><header class="vl-r9-page-hero"><div class="vl-r9-page-brand"><span>/ REHONGJIUDITU /</span><span>2023<br>XIAOHONGSHU</span></div><img class="vl-r9-page-title-art" src="SLOT:shanghai-wine-title.png" alt="小红书 上海街头 热红酒地图"><figure class="vl-r9-page-scene"><img src="SLOT:shanghai-street-hero.png" alt="上海老建筑门前，一位行人经过街道"></figure></header><section class="vl-r9-page-entry" aria-label="活动时间与街区导航"><div class="vl-r9-page-invite"><div class="vl-r9-page-date">12月5日<small>（2023）</small><br>－1月5日<small>（2024）</small></div><p>*小红书邀你共赴<br>上海街头热红酒之旅</p></div><p class="vl-r9-page-benefit">〈 品冬日限定红酒 · 领限量周边 〉</p><nav class="vl-r9-page-nav"><a href="#vl-r9-page-shops">愚园路</a><a href="#vl-r9-page-shops">安福路</a><a href="#vl-r9-page-map">巨富长</a><a href="#vl-r9-page-redeem">复兴中路</a></nav></section><div class="vl-r9-page-awning" aria-hidden="true"></div><section class="vl-r9-palette vl-r9-directory" id="vl-r9-page-shops" aria-label="酒馆摄影目录"><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid vl-r9-directory-grid--feature"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:silver-eye-wide.png" alt="Silver Eye窗边的圆镜与座椅"><div class="vl-r9-directory-label"><h2 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>SILVER EYE</span></h2><div class="vl-r9-directory-copy"><p>［神秘感十足的暗黑风bar］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:wugong-front.png" alt="武宫白色门廊"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>武宫</span></h3><div class="vl-r9-directory-copy"><p>［武夷路的黑胶文化之宫］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:mandrill-front.png" alt="Mandrill青蓝露台"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>MANDRILL</span></h3><div class="vl-r9-directory-copy"><p>［演员黄觉的复古机车bar］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:brut-eatery-front.png" alt="悦璞食堂门前的绿色树荫"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>悦璞食堂<br>愚园路店</span></h3><div class="vl-r9-directory-copy"><p>［坐在木头台阶上晒太阳］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:riink-neon.png" alt="RIINK紫红霓虹轮滑空间"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>RIINK</span></h3><div class="vl-r9-directory-copy"><p>［美式复古轮滑餐厅］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:bites-brews-interior.png" alt="Bites and Brews暖阳下的木窗与沙发"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>BITES &amp; BREWS<br>武定路店</span></h3><div class="vl-r9-directory-copy"><p>［经典美式复古风西餐厅］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:barbarian-interior.png" alt="Barbarian金黄色酒柜与灯光"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>BARBARIAN<br>巴巴瑞恩餐厅</span></h3><div class="vl-r9-directory-copy"><p>［上海的霍格沃兹餐厅］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:deck-street.png" alt="甲板所在的老建筑街景"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>甲板</span></h3><div class="vl-r9-directory-copy"><p>［外滩老建筑暗黑哥特bar］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:lili-sparkling-entry.png" alt="Lili Sparkling蓝色入口"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>LILI SPARKLING</span></h3><div class="vl-r9-directory-copy"><p>［上海街头的海底泳池］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div><div class="vl-r9-shelf vl-r9-directory-row"><div class="vl-r9-shelf-content vl-r9-directory-grid"><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:koya-bistro-night.png" alt="KOYA夜间门店和圆形投影招牌"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>KOYA</span></h3><div class="vl-r9-directory-copy"><p>［市中心自带花园的Bistro］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article><article class="vl-r9-directory-card"><img class="vl-r9-directory-photo" src="SLOT:silver-eye-detail.png" alt="Silver Eye圆镜与黑色座椅"><div class="vl-r9-directory-label"><h3 class="vl-r9-directory-name"><i class="vl-r9-directory-pin" aria-hidden="true"></i><span>SILVER EYE</span></h3><div class="vl-r9-directory-copy"><p>［神秘感十足暗黑风bar］</p><a class="vl-r9-directory-link" href="#vl-r9-page-redeem">喝一杯 ▸</a></div><div class="vl-r9-directory-footer"><span>● ○</span><i></i><b>MULLED WINE MAP</b></div></div></article></div></div></section><section class="vl-r9-shelf vl-r9-page-map" id="vl-r9-page-map"><div class="vl-r9-shelf-content"><h2>（巨富长－热红酒地图）</h2><div class="vl-r9-page-map-stage"><img class="vl-r9-page-book" src="SLOT:jufuchang-open-book.png" alt="展开的巨富长街区热红酒导览书册"><a class="vl-r9-page-map-arrow" href="#vl-r9-page-shops" aria-label="返回商户目录">‹</a><a class="vl-r9-page-map-arrow" href="#vl-r9-page-redeem" aria-label="前往兑换说明">›</a></div></div></section><section class="vl-r9-palette vl-r9-dispenser" id="vl-r9-page-redeem"><header class="vl-r9-dispenser-heading"><h2 class="vl-r9-dispenser-sign">下单团购，解锁限量周边</h2><small>*未成年人禁止饮酒</small></header><div class="vl-r9-shelf vl-r9-dispenser-base"><div class="vl-r9-shelf-content"><div class="vl-r9-slot"><div class="vl-r9-slot-machine" aria-hidden="true"></div><div class="vl-r9-slot-mouth" aria-hidden="true"></div><article class="vl-r9-slot-paper"><p class="vl-r9-dispenser-intro">即日起至2024年1月5日活动期间，下单本活动页面内任一商家的热红酒活动产品，并前往线下店铺出示实时订单进行验券。</p><p class="vl-r9-dispenser-muted">（小红书APP－我－左上角横杠－订单）</p><ul class="vl-r9-dispenser-rules"><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>下单完成首次验券，即可获得纸质版地图＋热红酒贴纸。</p><img class="vl-r9-dispenser-prize" src="SLOT:map-sticker-gift.png" alt="纸质地图与贴纸"></li><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>每打卡一家店铺完成验券，即可获得1枚店铺专属印章。</p><img class="vl-r9-dispenser-prize" src="SLOT:stamp-pass.png" alt="绿色集章卡"></li><li class="vl-r9-dispenser-rule"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>集满3家不同店铺印章，兑换限量款红酒小红包。<br><small>基础斜挎款与隐藏手提款，先到先选。</small></p><img class="vl-r9-dispenser-prize" src="SLOT:red-knit-bag.png" alt="红色针织包"></li></ul></article><div class="vl-r9-slot-lip" aria-hidden="true"></div><aside class="vl-r9-slot-note"><h3>针织挎包兑换方式：</h3><p>1月5日前，周五／周六12:30–13:30 Mandrill点开放；周日18:00–19:00 Tiler点开放。每个领取点每周限量发放100份，先到先得。</p><p class="vl-r9-dispenser-address">● 愚园路－Mandrill<br><small>长宁区江苏路街道愚园路1258号</small></p><p class="vl-r9-dispenser-address">● 复兴中路－Tiler<br><small>黄浦区瑞金二路街道复兴中路612号</small></p><small>*兑换时一定要出示实时订单，截图不可以。地图遗失不补。</small></aside></div></div></div></section><section class="vl-r9-page-section" id="vl-r9-page-chat"><header class="vl-r9-dispenser-heading"><h2 class="vl-r9-dispenser-sign">加入群聊，迅速召唤酒搭子</h2></header><div class="vl-r9-shelf vl-r9-page-paper-shelf"><div class="vl-r9-shelf-content"><article class="vl-r9-page-paper"><h3>［ 如何快速找到你的专属酒搭子 ］</h3><div class="vl-r9-page-step"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><b>Step1</b><p>进入土拨薯个人主页，点击群聊按钮。</p></div><div class="vl-r9-page-ui" aria-label="个人主页操作示意，非原始截图"><div class="vl-r9-page-ui-head"><span class="vl-r9-page-avatar">薯</span><div><strong>土拨薯</strong><br>官方账号 · IP属地 上海</div></div><p>是小红书圈内代言人<br>也是人间美食挖掘机<br>更是带你赚赚赚的薯地锦鲤</p><p>85 关注　3.1万 粉丝　2.7万 获赞与收藏</p><a href="#vl-r9-page-chat-join">♧ 群聊　查看详情 ↗</a></div><div class="vl-r9-page-step"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><b>Step2</b><p>一键加入群聊。</p></div><div class="vl-r9-page-ui vl-r9-page-ui--dark" id="vl-r9-page-chat-join" aria-label="群聊入口操作示意，非原始截图"><h4>〈　土拨薯的群聊</h4><div class="vl-r9-page-ui-room"><span class="vl-r9-page-avatar">薯</span><p>上海热红酒地图酒搭子<br>1人</p><a href="#vl-r9-page-chat-guide">立即加入</a></div></div><div class="vl-r9-page-step" id="vl-r9-page-chat-guide"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><b>Step3</b><p>进群找酒搭子或邀请朋友入群，一起美美喝酒，解锁更多土拨薯社群神秘活动及惊喜福利！</p></div><footer class="vl-r9-page-paper-footer"><span>● ○</span><i></i><span>MULLED WINE MAP</span></footer></article></div></div></section><section class="vl-r9-page-section" id="vl-r9-page-publish"><header class="vl-r9-dispenser-heading"><h2 class="vl-r9-dispenser-sign">发布笔记，瓜分千万流量</h2></header><div class="vl-r9-shelf vl-r9-page-paper-shelf"><div class="vl-r9-shelf-content"><article class="vl-r9-page-paper vl-r9-page-publish"><p>活动期间，发布笔记，满足以下条件可自动瓜分千万级官方流量扶持，扶持额度与内容优质度成正比，上不封顶！</p><ol><li>（1）绑定<em>#上海街头热红酒地图</em>话题</li><li>（2）艾特<em>@土拨薯</em></li><li>（3）添加店铺地址</li></ol><div class="vl-r9-page-publish-rewards"><div class="vl-r9-page-publish-reward"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>发布有奖：发布后，在本页面下方即可参与<em>「限量喝酒杯垫」</em>抽奖，随机抽取100份。</p><img src="SLOT:coaster-mini-prize.png" alt="限量杯垫奖品小图"></div><div class="vl-r9-page-publish-reward"><i class="vl-r9-dispenser-dot" aria-hidden="true"></i><p>优质内容：话题下优质内容获得<em>「土拨薯玩偶手办」</em>奖励，随机抽取10份。</p><img src="SLOT:mascot-figurine.png" alt="土拨薯玩偶手办"></div></div><p>活动中的热红酒品味体验，打卡了冬天的第一杯热红酒，偶遇一杯街边小摊的热红酒……<br>不管是什么样的热红酒，都欢迎你一起来分享～</p><footer class="vl-r9-page-paper-footer"><span>● ○</span><i></i><span>MULLED WINE MAP</span></footer></article></div></div></section><section class="vl-r9-page-lottery" id="vl-r9-page-lottery"><header class="vl-r9-dispenser-heading"><h2 class="vl-r9-dispenser-sign">分享体验 一键get<strong>「限量喝酒杯垫」</strong></h2></header><p class="vl-r9-page-prize-note">*杯垫样式随机赠送</p><div class="vl-r9-shelf vl-r9-page-coasters"><div class="vl-r9-shelf-content"><img src="SLOT:coaster-display.png" alt="不同颜色与文字设计的限量杯垫成组陈列"></div></div><div class="vl-r9-page-lottery-action"><a class="vl-r9-page-button" href="#vl-r9-page-task">立即抽奖</a><p>每次抽奖消耗10积分，剩余抽奖积分 0</p></div><article class="vl-r9-page-task" id="vl-r9-page-task"><div><h3>分享上海街头热红酒地图</h3><p>分享活动页面＋10积分，已完成 0/3</p></div><a class="vl-r9-page-button" href="#vl-r9-page-publish">去完成</a></article></section><p class="vl-r9-page-ending">历史活动视觉示例 · 未成年人禁止饮酒<br>静态页面不提供真实下单、入群、积分或抽奖服务</p></main>
```

组装时先读取完整依赖；SLOT替换为当前任务资产，字体别名需实际加载。SVG按资源协议内联。复制实例时更新SVG ID及引用；长文案复核正文净空、页脚遮叠和窄幅换行。


<a id="combination.blue-silver-roster-ticket"></a>

形状原子：[连续圆弧缺口票根](../shapes/tickets-and-notches.md#shape.arc-notched-stub)。原子提供通用轮廓，模板中的参考比例、圆滑路径、配色与响应式规则为组合覆盖；形状不绑定赛博风格。


## 蓝银卷槽名单票券

卷槽→银蓝名单主面→带缺口的深蓝票根。名单、标识、附注和装饰条码各有槽位；票根轮廓与描边共用SVG路径。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline"
  ],
  "scope": "局部模块",
  "asset_slots": {
    "showlogo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 700,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[蓝银卷槽名单票券](blue-silver-roster-ticket.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber6-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：658px画幅设备前沿54px，420px约40px；前沿与台面、投影分别控制。票面银灰中心、深蓝边缘与灰度颗粒并存，避免白雾替代材质；条码与路网为装饰。


<a id="combination.blue-silver-prize-console"></a>

形状原子：[斜台面与独立前沿](../shapes/cards-and-panels.md#shape.sloped-deck)、[薄侧边立体按键](../shapes/cards-and-panels.md#shape.thin-sided-key)。原子提供通用轮廓，模板中的参考比例、圆滑路径、配色与响应式规则为组合覆盖；形状不绑定赛博风格。


## 蓝银抽奖设备组

日期屏→奖品内舱→倾斜操作台面→独立垂直前沿；底座厚度不由阴影代替，按钮键面与侧边分离。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline"
  ],
  "scope": "局部模块",
  "asset_slots": {
    "autograph": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "blindbox": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "ticketprize": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 700,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[蓝银抽奖设备组](blue-silver-prize-console.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber6-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：658px画幅设备前沿54px，420px约40px；前沿与台面、投影分别控制。票面银灰中心、深蓝边缘与灰度颗粒并存，避免白雾替代材质；条码与路网为装饰。


<a id="combination.blue-silver-concert-longpage"></a>

形状原子：[斜台面与独立前沿](../shapes/cards-and-panels.md#shape.sloped-deck)、[薄侧边立体按键](../shapes/cards-and-panels.md#shape.thin-sided-key)、[连续圆弧缺口票根](../shapes/tickets-and-notches.md#shape.arc-notched-stub)。原子提供通用轮廓，模板中的参考比例、圆滑路径、配色与响应式规则为组合覆盖；形状不绑定赛博风格。


## 蓝银演出活动长页

舞台与磁带开场→名单票→参与规则→设备行动→任务与嘉宾→收尾。章节按真实活动取舍，连续黑蓝场域不拆成重复背景卡。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline",
    "combination.blue-silver-roster-ticket",
    "combination.blue-silver-prize-console"
  ],
  "scope": "整页长图",
  "asset_slots": {
    "annualletter": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "authorone": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "authortwo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "autograph": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "blindbox": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "cameras": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "cassette": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "festival": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "guestjason": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "guestletter": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "guestrainie": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "guestroy": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "guestvictor": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "heroletter": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "mapletter": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "newyearplate": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "scriptlogo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "showlogo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "stage": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "ticketlogo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "ticketprize": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "videoone": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "videothree": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "videotwo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 700,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[蓝银演出活动长页](blue-silver-concert-longpage.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber6-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)；[combination.blue-silver-roster-ticket](#combination.blue-silver-roster-ticket)；[combination.blue-silver-prize-console](#combination.blue-silver-prize-console)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：658px画幅设备前沿54px，420px约40px；前沿与台面、投影分别控制。票面银灰中心、深蓝边缘与灰度颗粒并存，避免白雾替代材质；条码与路网为装饰。


<a id="combination.pink-party-window"></a>

## 粉色派对说明窗口

渐变顶栏与近黑正文面分层，说明与角色信息分列；纹理在正文后方，不给正文继承高强度霓虹。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline",
    "surface.neon-edge"
  ],
  "scope": "局部模块",
  "asset_slots": {
    "DouyinSansBold": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "captain": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 500,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[粉色派对说明窗口](pink-party-window.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber10-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)；[surface.neon-edge](../surfaces/diffuse-light.md#surface.neon-edge)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：玫红亮区经过低饱和粉色过渡进入暗酒红/近黑，再接右端玫红；不得铺满高饱和色。关卡字重采用真实VF 500，字距0.025em，字光不能填死字腔；胶囊伪元素须border-box并独立居中。


<a id="combination.pink-party-level-heading"></a>

形状原子：[双层胶囊指示器](../shapes/capsules-and-badges.md#shape.capsule-indicator)。原子提供通用轮廓，模板中的参考比例、圆滑路径、配色与响应式规则为组合覆盖；形状不绑定赛博风格。


## 粉色关卡标题与胶囊

标题与ON胶囊成组；胶囊相对题带居中，黑色内芯相对绿色壳体独立居中。单行和双行标题均需复核。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline",
    "surface.neon-edge"
  ],
  "scope": "局部模块",
  "asset_slots": {
    "DouyinSansBold": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 500,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[粉色关卡标题与胶囊](pink-party-level-heading.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber10-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)；[surface.neon-edge](../surfaces/diffuse-light.md#surface.neon-edge)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：玫红亮区经过低饱和粉色过渡进入暗酒红/近黑，再接右端玫红；不得铺满高饱和色。关卡字重采用真实VF 500，字距0.025em，字光不能填死字腔；胶囊伪元素须border-box并独立居中。


<a id="combination.pink-party-linked-stages"></a>

## 粉色连续步骤导轨

竖导轨→楼层/步骤标签→标题与独立图片；每步随内容增长，导轨连续，不将场景图切成装饰碎块。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline",
    "surface.neon-edge"
  ],
  "scope": "局部模块",
  "asset_slots": {
    "DouyinSansBold": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floorone": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floorthree": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floortwo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 500,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[粉色连续步骤导轨](pink-party-linked-stages.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber10-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)；[surface.neon-edge](../surfaces/diffuse-light.md#surface.neon-edge)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：玫红亮区经过低饱和粉色过渡进入暗酒红/近黑，再接右端玫红；不得铺满高饱和色。关卡字重采用真实VF 500，字距0.025em，字光不能填死字腔；胶囊伪元素须border-box并独立居中。


<a id="combination.pink-party-longpage"></a>

形状原子：[双层胶囊指示器](../shapes/capsules-and-badges.md#shape.capsule-indicator)。原子提供通用轮廓，模板中的参考比例、圆滑路径、配色与响应式规则为组合覆盖；形状不绑定赛博风格。


## 粉色派对关卡长页

完整艺术首屏→说明窗口→复合章题→关卡图文与导轨→场景接力→收束窗口与落款；背景连续，栏目渐变不覆盖照片。

```json
{
  "dependencies": [
    "surface.screen-grain",
    "surface.scanline",
    "surface.neon-edge",
    "combination.pink-party-window",
    "combination.pink-party-level-heading",
    "combination.pink-party-linked-stages"
  ],
  "scope": "整页长图",
  "asset_slots": {
    "DouyinSansBold": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "bartruck": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "captain": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "entrance": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "finalmark": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floorone": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floorthree": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "floortwo": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "friends": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "gifts": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "hero": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "instown": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "parkroute": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "parkscene": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "theatre": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    },
    "yearmark": {
      "role": "独立参考素材；按当前主题替换，保留原始比例",
      "required": true
    }
  },
  "font_binding": {
    "family": "CyberSourceHan",
    "file": "SourceHanSansSC-VF.otf",
    "source": "内部字体目录",
    "body_weight": 400,
    "heading_weight": 500,
    "note": "真实VF字体；固定Bold不能用CSS伪减细。图内字标独立素材，不宣称识别为该字体。"
  },
  "material_contract": "CSS负责轮廓、布局、渐变、颗粒和边光。摄影、字标、复杂主体保留独立图片；一体首屏不得按命中CSS拆开。SLOT:screen-grain绑定库内assets/svg/screen-grain.svg；SVG内图片需内联或改成有效本地资源。",
  "adoption_boundary": "基于最新修订的参考验证稿，不宣称像素级复刻；示例文案与品牌只用于示范，使用时换成任务内容。操作按钮是静态视觉，不包含抽奖服务。"
}
```

完整HTML与CSS：[粉色派对关卡长页](pink-party-longpage.html)。读取模板内 `style[data-cyber-recipe]` 和 `.cyber10-recipe`；CSS已作用域化，独立使用或复用同一套样式一次。不要将设备整体当shape原子。多实例SVG的id和引用需同步加实例前缀。

依赖：[surface.screen-grain](../surfaces/paper-and-print.md#surface.screen-grain)；[surface.scanline](../surfaces/paper-and-print.md#surface.scanline)；[surface.neon-edge](../surfaces/diffuse-light.md#surface.neon-edge)；[combination.pink-party-window](#combination.pink-party-window)；[combination.pink-party-level-heading](#combination.pink-party-level-heading)；[combination.pink-party-linked-stages](#combination.pink-party-linked-stages)。

素材绑定：将 `SLOT:*` 替换为素材路径；由字体目录解析并加载 CyberSourceHan 的真实VF文件。库模板不默认捆绑参考裁片。保留原渐变色标、响应式规则与层级；不要只拷贝最早API草稿。
适配：玫红亮区经过低饱和粉色过渡进入暗酒红/近黑，再接右端玫红；不得铺满高饱和色。关卡字重采用真实VF 500，字距0.025em，字光不能填死字腔；胶囊伪元素须border-box并独立居中。

<a id="combination.mist-green-performance-longpage"></a>

## 雾绿性能跑鞋长页

风格标签：二级：未来科技风 / 产品科技。产物：详情页长图；粒度：完整长页。

采用[性能递进长页](../layouts/continuous-flow.md#layout.product-performance-longpage)的完整结构，读取依赖后追加本条 recipe 皮肤；只取布局时不加载该皮肤。

```json
{
  "components": [
    "layout.product-performance-longpage"
  ],
  "overrides": {
    "root": {
      "--vl-tint": "#dce4dc",
      "--vl-ink": "#111"
    },
    "skin": "读取本条登记的 recipe 样式；不将该层复制到布局原子"
  },
  "asset_mode": "integrated-caption + independent-image-slots"
}
```

风格依据：大尺度悬浮产品、外底／支撑细节与技术层级构成产品科技叙事；雾绿并非独立风格依据。

| 外观职责 | 本组合参数／实现 |
|---|---|
| 底色 | 雾灰绿#dce4dc；浅灰信息区#f1f1ef；白色规格区 |
| 深场／文字 | 深绿#243b31承载白字；浅场#111正文 |
| 点缀 | 荧光黄绿来自产品／技术标识素材，不另铺无关高亮色块 |
| 字体 | 编辑正文Arial/PingFang SC；独立H2 38px、轻量H2 44px、正文18–19px（658px画幅） |
| 特殊标题 | 原参考斜切／粗黑展示标题属于合成素材；未识别具体font face，不以系统黑体冒充 |
| 表面 | 山雾、飞石、网布与金属结构用真实／合成图；资料面板白底24px圆角 |
| 过渡 | mesh/weight的双轴渐变按相邻素材横向多点采样，保留大范围中间色；新素材重采样，不固守色标 |
| 尺码表 | 本组合四列、条带底、女士／男士分组；真实数据替换演示数据，行数随内容增长 |

默认皮肤完整存于模板 recipe 样式，既有根变量 `--vl-tint/ink` 只控制根角色，其余场景底、边缘色和表格必须按章节一起替换。图库内的 photo-bg 只在皮肤选择器，不混入布局节点。

材质图与轻量图之间的过渡先预留无主体／无字边缘，再采左右多个位置；若图片本身没有可用净空，扩展背景素材，不能用遮罩抹掉飞石、产品或标题。未把缺失的门店互动尾部补为该参考能力。

纯布局只保存页面顺序、图窗宽高关系、对齐和留白，字体／配色／表面在组合皮肤层。单独选布局时加载 layout 样式与 main 骨架，不加载 recipe 样式；另选配色、字体和素材。组合与布局共用该 main，不复制第二套排版。图片 width/height 是参考比例而非固定显示高度，所有正文正常流增高。

素材契约：`{{pageN_asset_XX}}` 为真实素材槽，逐图的 alt 和 data-asset-ratio 说明角色及比例。完整合成场景包含标题或引线时保留一体素材，禁止 HTML 重复叠字；若需换产品／改图内文案，应重新制作该场景或获得可分离源素材。图窗边界不等于允许任意裁切，换图先核对主体净空。摄影、飞石、山雾、织物、特殊标题字形均不由布局 CSS 生成，参考图和私人本地路径不进入库模板。

安全底线：禁止给正文模块设固定高度或隐藏溢出；新字体按实际 face 检查字宽、字级和行框。先增加文案区高度，再调整栏宽／图文方向；不靠缩字和裁切过关。以画布容器宽度而非浏览器宽度触发480px窄版重排：性能页资料/用途改单列、测量改图文行；摄影页APP改单列、渠道改双列、缩减门店与页尾内距。背景换色须同步素材边缘与所在章节，不能仅改根变量就宣称整图换色完成。420px 与658px是已测画幅；更窄或更长内容须再次试排。

验收边界：组合效果已验，限本参考可见范围及资产槽位关系；不代表全字可编辑或商业素材、字体、交互授权。微字使用近密度演示文案，正式商品数据需替换。

**short 组装约束：** 此处样式与模板用于读取结构。按实际固定画布选择布局分支，将变量、选择器与继承展开到真实元素行内 style，伪元素转为真实装饰节点；最终 HTML 不保留 style 节点、媒体／容器查询或响应式缩放脚本。658／420 仅为历史测试宽度，不锁定新作品尺寸。参考中含字影像不自动授权新任务烘焙章节文字：按 Brief 保留准确文字 DOM，仅获准图内文字随图使用且不重复覆字。

<a id="combination.cream-sport-editorial-longpage"></a>

## 奶油复古穿搭长页

风格标签：二级：杂志编辑风 / 时尚杂志。产物：详情页长图、社媒长图、品牌专题；粒度：完整长页。

采用[摄影分章长页](../layouts/continuous-flow.md#layout.editorial-lookbook-longpage)的完整结构，读取依赖后追加本条 recipe 皮肤；只取布局时不加载该皮肤。

```json
{
  "components": [
    "layout.editorial-lookbook-longpage"
  ],
  "overrides": {
    "root": {
      "--vl-tint": "#eee8d4",
      "--vl-ink": "#292821"
    },
    "skin": "读取本条登记的 recipe 样式；不将该层复制到布局原子"
  },
  "asset_mode": "integrated-caption + independent-image-slots"
}
```

风格依据：三组服装摄影循环、非对称照片窗口、单品开放排版与刊物式留白形成时尚杂志分支；不是因为米黄色就归复古商业风或感官生活风。

| 外观职责 | 本组合参数／实现 |
|---|---|
| 连续底 | 奶油#eee8d4；墨色#292821 |
| 章节色 | 草绿／赭黄／酒红来自穿搭摄影；页面不额外堆叠色卡 |
| 门店／强调 | 棕灰#927c68、浅字#eee8d4；发布标题#a28a70 |
| 字体 | 正文系统无衬线/PingFang SC，22px/1.65；门店20px；页尾说明13px；按实际内容复测 |
| 展示标题 | 窄粗拉丁与中文大标题留在摄影主场资产，保持原图字形角色，不再覆盖HTML文字 |
| 图像边缘 | 7px轻圆角照片窗；主体保持完整；产品图在开放底，不增加投影卡片 |
| 地图／建筑 | 装饰地图和门店线描为独立净底素材；不重复编码复杂线稿 |
| 尾景 | 一张连续墙面至庭院的摄影背景，100%宽、自然比例；顶端120px过渡，背景不能用小块纹理无限拉伸 |

纯色面板无法替代全幅摄影主场。模板要求干净商品图和建筑图，不内置本次参考清理用的多边形裁角、门店裁边或6px淡边；若新素材需要渐隐，先验证净空再另选既有图片渐隐机制。尾景应按真实资产调明暗；本次验证尾景经过图片编辑补全，未声称恢复原隐藏像素。

三个完整摄影章节可复用 look-cycle 增减，配色须同步摄影后期、连续底与文字对比。电商入口只是示意结构，发布前绑定真实链接；生成静态社媒图时按需求移除交互模块。

纯布局只保存页面顺序、图窗宽高关系、对齐和留白，字体／配色／表面在组合皮肤层。单独选布局时加载 layout 样式与 main 骨架，不加载 recipe 样式；另选配色、字体和素材。组合与布局共用该 main，不复制第二套排版。图片 width/height 是参考比例而非固定显示高度，所有正文正常流增高。

素材契约：`{{pageN_asset_XX}}` 为真实素材槽，逐图的 alt 和 data-asset-ratio 说明角色及比例。完整合成场景包含标题或引线时保留一体素材，禁止 HTML 重复叠字；若需换产品／改图内文案，应重新制作该场景或获得可分离源素材。图窗边界不等于允许任意裁切，换图先核对主体净空。摄影、飞石、山雾、织物、特殊标题字形均不由布局 CSS 生成，参考图和私人本地路径不进入库模板。

安全底线：禁止给正文模块设固定高度或隐藏溢出；新字体按实际 face 检查字宽、字级和行框。先增加文案区高度，再调整栏宽／图文方向；不靠缩字和裁切过关。以画布容器宽度而非浏览器宽度触发480px窄版重排：性能页资料/用途改单列、测量改图文行；摄影页APP改单列、渠道改双列、缩减门店与页尾内距。背景换色须同步素材边缘与所在章节，不能仅改根变量就宣称整图换色完成。420px 与658px是已测画幅；更窄或更长内容须再次试排。

验收边界：组合效果已验，限本参考可见范围及资产槽位关系；不代表全字可编辑或商业素材、字体、交互授权。微字使用近密度演示文案，正式商品数据需替换。

**short 组装约束：** 此处样式与模板用于读取结构。按实际固定画布选择布局分支，将变量、选择器与继承展开到真实元素行内 style，伪元素转为真实装饰节点；最终 HTML 不保留 style 节点、媒体／容器查询或响应式缩放脚本。658／420 仅为历史测试宽度，不锁定新作品尺寸。参考中含字影像不自动授权新任务烘焙章节文字：按 Brief 保留准确文字 DOM，仅获准图内文字随图使用且不重复覆字。

<a id="combination.warm-bakery-story-longpage"></a>

## 暖烘焙食品长页

风格标签：一级：感官生活风。场景标签：暖烘焙；不是新增一级或二级风格。范围：完整长页；曲奇是主版的参考题材；适配范围由编号递进、主辅图组与资料收束是否服务当前内容决定，不按商品类别限定。

[编号分章 · 图文递进](../layouts/continuous-flow.md#layout.numbered-media-longpage)

```json
{"dependencies":["layout.numbered-media-longpage"]}
```

主版采用模板 food-variant=1、food-layout=1、food-skin=1。参考内容依次为原料组成、制作过程、烘烤表现、食用场景、包装关系与产品资料，不是必须保留的六章。复用的是编号分章、影像与解释交替、主辅图组和资料收束关系；按新主题替换内容，必要时删减、重排或重复槽位并调整编号与节奏。不为凑模板编造事实；跨品类同样按上述视觉关系评估组合适配。

| 外观职责 | 可替换参数 |
|---|---|
| 主底／标题 | 奶油浅底 #fff3df；深棕 #702100 |
| 强调／卡片 | 焦糖 #b86024；近白 #fffdfa；低对比辅助棕 #b89981，微字需按成品复核 |
| 字体 | 标题为有重量的展示黑体；验证使用目录已有 DouyinSans Bold，同类替代而非识别原字体；正文无衬线。大标题68px、编号49px、正文约18–22px均为596px试排值 |
| 容器 | 媒体卡25–37px圆角、白底信息卡；不把食品原有光影重复施加为卡片投影 |
| 材质 | 裂纹、馅料、黄油反光、烤箱光及包装印刷由实际素材承担，不新增噪点或“食品纹理”CSS |

素材策略：Hero保留大产品与标题净空；原料图承担组成识别；手作图突出动作；双细节图只补充主图信息；烘烤图承担工艺氛围；两场景卡分别描述场景；包装三图需有各自内容，资料表使用真实字段。原料标签和包装标识属于必须保护区域，图片替换后重新检查。纯色标题底不能盖掉原图枝叶、产品与渐变接缝。

参考资产边界：主版Hero、原料引线照片、双原料图中的原图文字随照片保留，非独立可编辑文字；其余标题、编号、场景卡标题与参数为原生DOM。库只分发可替换槽位，不分发参考商品图、品牌文案或字体文件。新作品以Brief确定准确文字职责，禁止把整张长页作为一个图片槽交付。

### 烘焙沉浸摄影变体（同一组合，不另设CSS ID）

采用 food-variant=2、food-layout=2、food-skin=2。欧包参考中的悬浮陈列、卖点、切面、手掰、原料、托盘、包装与参数均为可替换内容。核心关系是大尺度影像主场、整体与局部的尺度推进、场景展开、连续摄影与疏朗留白；不要求同样章节、动作或产品对象。按内容调整槽位后仍须保留影像主导与景别节奏；不叠加主版编号和场景标题栏。

色彩为麦香橙 #e8a767、奶油 #faf2df、棕色 #65370f；标题采用相对轻的无衬线，照片承担主要重量。此变体的手掰、麦田、托盘、包装参考为含字连续场景，照片内标题不可单独编辑；新作品需要改文案时使用干净完整场景并原生排字，或获准编辑整体素材，不用不透明矩形盖字。

过渡按相邻素材真实安全边缘取色，保留波浪轮廓及无字图像背景；不能用统一白蒙版抹去商品或装饰。当前参考校准仍存在局部接缝与字体差异，非逐像素复刻。此变体已验证完整内容关系，不新增另一全页布局原子。

### 选型与安全

需要编号分章、多图解释与资料收束关系时选主版；需要影像主导、整体与局部的尺度变化及连续摄影时选沉浸变体。包装、切面或动作不是必填内容。换色同步主底、正文、强调与卡片；字体来自既有候选，不将配色变化另立风格。普通圆角、网格、编号、图片标注不重复新建原子。主版长标签换行增高；变体遇到照片内长文案必须重新安排素材净空，不视为自动安全。

最终按short固定画布行内HTML执行；模板仅供读取结构和皮肤，不能保留style节点或媒体查询作为交付。先确认字体与素材就绪，测高、收尾安全区和完整截图分别验收。外部商业宣称不作为模板默认事实。

<a id="combination.resume-letter-rail"></a>

## 蓝色散字侧轨与局部方格简历

风格标签：二级：都市潮流风 / 字体潮流。产物：简历、个人履历、作品集介绍页；粒度：固定A4单页。

依赖：[散字侧轨与自然流正文](../layouts/asymmetric-balance.md#layout.scattered-letter-rail)。
依赖：[上标签、下细轨的纵向列表](../layouts/grid-and-alignment.md#layout.stacked-label-track)。
依赖：[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)。
依赖：[方格纸印纹](../surfaces/craft-detail.md#surface.graph-paper)。

```json
{"dependencies": ["layout.scattered-letter-rail", "layout.stacked-label-track", "layout.evidence-grid", "surface.graph-paper"]}
```

800px参考宽度下，216px散字轨与40px沟槽形成左轻正文右置结构；姓名右对齐，联系方式左对齐，中段教育/技能约1.35:1，下段经历跨正文宽。散字独立旋转、局部出血，方格仅落在上部和经历右侧两块装饰区域。保持正文净空，不将全页铺成均匀网格。

模板：[resume-reference-14.html](resume-reference-14.html)。先读取上述依赖，再读取模板中的组合style与main；组合只覆盖皮肤和本页关系，不重复复制一套依赖CSS。

| 配色变量 | 参考值 |
|---|---|
| `--cvx-paper` | `#edeeec` |
| `--cvx-ink` | `#333333` |
| `--cvx-accent` | `#304fa2` |
| `--cvx-secondary` | `#385495` |
| `--cvx-line` | `#92989c` |

图1组合按固定A4重排为800×1132px，四边48px文字安全区；字形使用Arial实际字形替代，原字体文件未知。细轨长度仅为样例排版值。缩短右下格纹，保持末段经历净空。

复用契约：示例姓名、联系方式、教育、职责与技能均为虚构排版数据，全部按用户内容替换；照片用portrait_asset槽位，不把参考整页作为背景图。换色同时覆盖正文、强调、边线、胶囊、SVG装饰及照片背景关系，不能只改主底色。安全区按真实字体、文案、照片焦点重新测量；装饰可出血，正文不能隐藏溢出。长邮箱允许断行，机构胶囊和记录可以局部增高，但整页高度不变；日期短区间同行，整组可移行；长姓名先扩行及调整栏目净空，不能靠压缩字形遮脸。

导出契约：模板用于读取和组装；先锁定A4宽高，再用真实依赖与素材排版测量安全区；通过后展开为行内样式，最终html/body/main保持预先锁定的宽高，不使用内容实测高度覆盖纸张高度。最终交付不保留style节点、媒体/容器查询或缩放脚本。简历默认固定A4单页，禁止自然增高或自动加页；紧凑重排仍超容量时停止导出，列出精简方案或请求用户决定增加A4页。完整长文本不因截取页面截图而视为已保留。正文文本碰撞、局部裁切、脸部保护区与四边净空均需在导出前后复核。长文本处理与容量判定遵循简历Spec的“固定页面、安全区与长文本验收”；48px只适用于800px基准，其他分辨率按物理安全距离等比换算。

<a id="combination.resume-circle-editorial"></a>

## 圆肖像与胶囊履历编辑简历

风格标签：二级：杂志编辑风 / 人物专题。产物：简历、个人履历、作品集介绍页；粒度：固定A4单页。

依赖：[左侧成组标签、右侧项目说明的履历行](../layouts/grid-and-alignment.md#layout.grouped-record-row)。
依赖：[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)。
依赖：[三预设放射贴纸](../shapes/organic-shapes.md#shape.radial-sticker)。

```json
{"dependencies": ["layout.grouped-record-row", "shape.badge", "shape.radial-sticker"]}
```

头部圆肖像与宣言分列，CV标签和黑色八臂星只占图窗边缘；经历区位于右栏，教育跨下部宽区，大浅蓝八臂星在独立装饰列裁切。公司填色胶囊与日期描边胶囊成组，底部联系条保持正常流。整张A4不因浏览器窗口变窄而重排；成组履历仍可按其自身容器宽度采用25rem局部断点。

模板：[resume-reference-15.html](resume-reference-15.html)。先读取上述依赖，再读取模板中的组合style与main；组合只覆盖皮肤和本页关系，不重复复制一套依赖CSS。

| 配色变量 | 参考值 |
|---|---|
| `--cvx-paper` | `#ffffff` |
| `--cvx-ink` | `#111111` |
| `--cvx-accent` | `#a4cae3` |
| `--cvx-secondary` | `#c5dfef` |
| `--cvx-line` | `#111111` |

固定A4默认800×1132px、四边48px安全区；data-density="normal"为常规构图，data-density="compact"通过缩减照片/装饰和间距、拓宽文字列处理更长字段，字号不变。旧3.37倍文案增高测试的通过结论撤回，4157字符现在作为必须拒绝导出的超容量负例。当前照片裁切较原参考更近，替换后重测脸部净空。

复用契约：示例姓名、联系方式、教育、职责与技能均为虚构排版数据，全部按用户内容替换；照片用portrait_asset槽位，不把参考整页作为背景图。换色同时覆盖正文、强调、边线、胶囊、SVG装饰及照片背景关系，不能只改主底色。安全区按真实字体、文案、照片焦点重新测量；装饰可出血，正文不能隐藏溢出。长邮箱允许断行，机构胶囊和记录可以局部增高，但整页高度不变；日期短区间同行，整组可移行；长姓名先扩行及调整栏目净空，不能靠压缩字形遮脸。

导出契约：模板用于读取和组装；先锁定A4宽高，再用真实依赖与素材排版测量安全区；通过后展开为行内样式，最终html/body/main保持预先锁定的宽高，不使用内容实测高度覆盖纸张高度。最终交付不保留style节点、媒体/容器查询或缩放脚本。简历默认固定A4单页，禁止自然增高或自动加页；紧凑重排仍超容量时停止导出，列出精简方案或请求用户决定增加A4页。完整长文本不因截取页面截图而视为已保留。正文文本碰撞、局部裁切、脸部保护区与四边净空均需在导出前后复核。长文本处理与容量判定遵循简历Spec的“固定页面、安全区与长文本验收”；48px只适用于800px基准，其他分辨率按物理安全距离等比换算。

<a id="combination.resume-pink-name-collage"></a>

## 双色姓名粉带与情境照片简历

风格标签：二级：波普撞色风 / 波普拼贴。产物：简历、个人履历、作品集介绍页；粒度：固定A4单页。

依赖：[叠层拼贴](../layouts/overlap-and-collage.md#layout.collage)。
依赖：[规整对齐](../layouts/grid-and-alignment.md#layout.evidence-grid)。
依赖：[胶囊与徽章](../shapes/capsules-and-badges.md#shape.badge)。

```json
{"dependencies": ["layout.collage", "layout.evidence-grid", "shape.badge"]}
```

三列网格控制左姓名与右情境照片的局部叠放：粗圆姓名在上，细连笔姓氏置于粉色带内。标题可进入照片左侧净空，不能进入脸部；职业椭圆在左下，照片边缘独立花朵、绿弧和四圆线性装饰。About全宽，下方教育/技能与经历分列。

模板：[resume-reference-16.html](resume-reference-16.html)。先读取上述依赖，再读取模板中的组合style与main；组合只覆盖皮肤和本页关系，不重复复制一套依赖CSS。

| 配色变量 | 参考值 |
|---|---|
| `--cvx-paper` | `#ffffff` |
| `--cvx-ink` | `#302b35` |
| `--cvx-accent` | `#6340b6` |
| `--cvx-secondary` | `#f4abe9` |
| `--cvx-line` | `#edade2` |
| `--cvx-muted` | `#70706e` |
| `--cvx-leaf` | `#91d861` |
| `--cvx-note` | `#e7ec93` |
| `--cvx-pink-ink` | `#943b80`（白底小字） |
| `--cvx-profession-ink` | `#4c286b`（粉底职业与花体姓名） |
| `--cvx-on-accent` | `#ffffff` |
| `--cvx-on-secondary` | `#ffffff` |

固定A4 800×1132px、四边48px文字安全区；页脚联系方式改为2×2分组以保证可读性；白底小字与粉底花体/职业文字改深色，分别获得6.57:1、6.50:1对比。测试照片经过生成式清理装饰，仅用于验证情境和槽位，不随库分发。展示字使用Arial Rounded MT Bold与Snell Roundhand，须读取字体库并验证实际face，不能声称恢复参考字体或未测窄版。

复用契约：示例姓名、联系方式、教育、职责与技能均为虚构排版数据，全部按用户内容替换；照片用portrait_asset槽位，不把参考整页作为背景图。换色同时覆盖正文、强调、边线、胶囊、SVG装饰及照片背景关系，不能只改主底色。安全区按真实字体、文案、照片焦点重新测量；装饰可出血，正文不能隐藏溢出。长邮箱允许断行，机构胶囊和记录可以局部增高，但整页高度不变；日期短区间同行，整组可移行；长姓名先扩行及调整栏目净空，不能靠压缩字形遮脸。

导出契约：模板用于读取和组装；先锁定A4宽高，再用真实依赖与素材排版测量安全区；通过后展开为行内样式，最终html/body/main保持预先锁定的宽高，不使用内容实测高度覆盖纸张高度。最终交付不保留style节点、媒体/容器查询或缩放脚本。简历默认固定A4单页，禁止自然增高或自动加页；紧凑重排仍超容量时停止导出，列出精简方案或请求用户决定增加A4页。完整长文本不因截取页面截图而视为已保留。正文文本碰撞、局部裁切、脸部保护区与四边净空均需在导出前后复核。长文本处理与容量判定遵循简历Spec的“固定页面、安全区与长文本验收”；48px只适用于800px基准，其他分辨率按物理安全距离等比换算。

<a id="combination.beverage-sensory-longpage"></a>
## 清透饮品摄影叙事长页

风格标签：二级：自然质朴风 / 清雅自然。以浅黄绿、留白、通透摄影、错位相框与纸卡组织饮品叙事，适用社媒长图和详情页长图。结构通用可复用，但不将原有风格改为无风格通用模板。

**入库就绪＝结构与槽位契约就绪。** 本条目按槽位、内容说明、必要性与可替换性验收；不以生图或原图摄影还原为前提。参考摄影、真实素材及字体还原未验，使用时按业务填槽；不据此宣称最终视觉通过。

### 模板读取

```json
{"template":"beverage-sensory-longpage.html","selector":"main[data-recipe=\"beverage-sensory-longpage\"]","styleSelector":"style[data-recipe-css=\"beverage-sensory-longpage\"]"}
```

同时读取 main 与对应 style，保持附件 HTML 布局，不新增原子或未知依赖。宿主负责外部页面边距和底色，测量以 main 实际宽度为准。背景使用 `data-background-slot`，素材使用 `data-asset-slot`，不是另设 `data-slot`。渐变、纸卡、相框、徽章、分隔线均为 CSS，不计图片。

### 复用必选与可选

本段优先于下文的案例主题、章节名称和示例数量。采用首屏主场结构时，其背景必需；其余章节背景、相框、照片图窗及拼贴仅在保留对应图文模块时条件必需，纯装饰可选。允许跨主题替换、删章、增减或重排模块；这些均为合法的业务适配版，并同步重排/清空指涉、编号、图注、alt及专用占位，不留破图或无效空白。slice/cup/bottle/bag/rim是稳定接口名，分别承载薄透细节、第一产品场、第二产品场、包装或原料展示、近距离感官细节，不强制切片、杯、瓶、透明袋或杯沿；历史也不是必选业务内容。替换以同视觉职责及适配后文案为准，不限原案例对象，但保留清雅自然的风格及背景/独立素材边界。8＋4是默认模板登记槽数，不是所有任务必选素材数。以下尺寸、比例、焦点和净空参数均为适配起点，须按实际内容复核；模板同时提供逐槽构图标记与可选图片渐隐接口，默认不启用渐隐。

### 槽位契约：默认8 背景＋4 素材，共 12 槽

必要性与可替换性独立：必需表示采用对应核心结构时须提供承担该视觉职责的内容，不表示必须使用某一张图片；条件必需仅在保留对应图文模块时成立。所有槽均可替换为同视觉职责、同风格且与新业务一致的素材，不限定饮品、青果、原品牌或指定产品。替换时同步更新标题、配方或业务说明、图注、alt与叙事，不虚构品牌历史或效果宣称。

所有背景为不透明照片，`object-fit:cover`；相框、满宽照片和独立细节图窗采用不透明照片，历史接口的拼贴可用透明底或匹配场景底色的不透明底。四个独立素材槽均为`width:100%;height:auto;object-fit:contain`。若采用透明容器、冰块、液体或其他薄透对象，其通透感由素材提供，不由CSS伪造；对象通透与图片背景透明是不同属性。

表中“不提供时处理”是使用阶段规则，不在本条目中改写HTML。必需槽及条件成立的槽未填时，不输出破图或未解析占位地址；可用现有场景底色作明确标注的结构预览，但不算完成业务填槽，也不阻碍结构入库。删除对应章节或图文模块是合法业务适配，须清理关联文字、专用包装、空位和失效指涉；共享容器仍有内容时仅清理被删项。所得版本标为业务适配版，并同步重排/清空指涉。

|槽名|背景/素材类型|内容说明|必需/条件必需/可选|可替换及约束|不提供时处理|
|---|---|---|---|---|---|
|beverage-hero-bg|背景；不透明摄影|`.bs-hero` 通透摄影主场，承载业务主体及相关环境或材料；比例364/1074，焦点50% 50%，底色#d5dc7d|必需：采用首屏主场结构时|可换同视觉职责的跨主题首屏照片；上部标题及底部脚注净空，保留清雅自然的光色，不限定饮品或容器|待填并仅作结构预览；取消首屏结构时标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-slice-bg|背景；不透明摄影|`.bs-slice` 薄透细节与材料搭配场；比例364/665，焦点50% 72%，底色#e0e3ac|条件必需：保留该章节背景时|可换薄透材质、叶片、织物或其他同视觉职责的细节摄影，不要求切片；主体偏下，上方留标题与说明，透光由照片提供|待填并仅作结构预览；可删该章，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-cup-bg|背景；不透明摄影|`.bs-cup` 第一产品展示子场；比例364/614，焦点50% 60%，底色#e8eabd|条件必需：保留第一产品子场时|可换适配业务的产品、作品或材料陈列，不限定杯装；顶部说明和底部两端标注保持净空，图文须一致|待填并仅作结构预览；可删该子场，标为业务适配版，并同步重排/清空双场对照及其他指涉|
|beverage-bottle-bg|背景；不透明摄影|`.bs-bottle` 第二产品展示子场；比例364/602，焦点50% 45%，底色#e4e6b7|条件必需：保留第二产品子场时|可换适配业务的另一产品、作品或展示视角，不限定瓶装；顶部业务说明及底部文字留空，双场均保留时保持光色协调|待填并仅作结构预览；可删该子场，标为业务适配版，并同步重排/清空双场对照及其他指涉|
|beverage-bag-bg|背景；不透明摄影|`.bs-bag` 包装或原料展示场；比例364/670，焦点57% 55%，底色#ecedce|条件必需：保留该章节背景时|可换包装、材料组合或同视觉职责摄影，不要求袋装或透明包装；避让顶部配对标签及左上标题，若有透明质感须由照片提供|待填并仅作结构预览；可删该章，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-ingredient-bg|背景；不透明摄影|`.bs-ingredient` 深色材料或环境底场，承托上部浅色文案及保留时的下部独立细节图窗；比例364/650，焦点50% 50%，底色#5b7e27|条件必需：保留该章节背景时|可换同风格、同承托职责的材料或环境摄影；维持浅字对比，不把保留的独立图窗并入背景|待填，底色仅供结构预览；可删该章，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-rim-bg|背景；不透明近摄或微距摄影|`.bs-rim` 近距离感官细节背景，展示材质、纹理、光泽或其他感官线索；比例364/602，焦点50% 55%，底色#d8e0a7|条件必需：保留该章节背景时|可换同视觉职责的近摄或微距照片，不要求杯沿、冰块或液体；顶部标题、底部短句留空；真实光学细节不由CSS伪造，保留该模块时不改作独立小图窗|待填并仅作结构预览；可删该章，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-closing-bg|背景；不透明摄影|`.bs-closing` 自然环境收尾，四周露景承托信纸；比例364/590，焦点50% 55%，底色#42562a|条件必需：保留收尾背景模块时|可换同承托职责、同风格的环境摄影；保护中央信纸和底部状态条的可读性，不要求树干枝叶或固定树种|待填并仅作结构预览；可删该章，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-frame-photo|素材；不透明照片|`.bs-frame-story` 错位相框主图，名义比例180:370；业务主体偏左，右侧与文字卡交叠|条件必需：保留相框图文模块时|可换与业务一致的主体、材料或过程照片，不限定果实、茶叶；保留卡片叠压安全区，主体不能被关键文字卡遮没|待填；不得保留空相框冒充实图；可删该模块，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-botanical-photo|素材；不透明照片|`.bs-botanical` 满宽环境或材料照片，名义比例364:510；图注在图外|条件必需：保留满宽照片模块时|可换与新业务相关、同风格的环境或材料摄影，不限定饮品原料或植物；不叠正文，检查与前后章节的色调和接缝|待填；可删整幅照片及图注，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-ice-photo|素材；不透明独立矩形照片|`.bs-ingredient .bs-ice-window` 独立感官或材料细节图窗，名义比例284:402|条件必需：保留独立细节图窗时|可换同视觉职责的业务细节照片，不要求冰块、气泡或饮品；主体完整入窗，窗内不排文字，不并入beverage-ingredient-bg；真实光学细节来自摄影|待填；不得留空图窗或用CSS假造素材细节；可删图窗，标为业务适配版，并同步重排/清空指涉及专用占位|
|beverage-history-montage|素材；透明或不透明摄影拼贴|`.bs-history` 业务补充信息拼贴，可展示样品、来源、制作、观察或其他相关内容，名义比例272:270；正文在图外|条件必需：保留拼贴图文模块时|可换同信息组织职责的拼贴，不要求历史、研发或年表；允许透明拼贴，或匹配场景底色的不透明拼贴，检查边缘与对比，文字须与材料事实一致|待填；可删拼贴模块及空figure，标为业务适配版，并同步重排/清空图文指涉及专用占位|

### CSS关键参数

- 根 `.bs`：`width:364px;max-width:100%;margin:auto`，正文 `13px/1.8`，`overflow-wrap:anywhere`，全体 `box-sizing:border-box`。
- 变量：`--bs-hand:"Kaiti SC","STKaiti","KaiTi",serif`；`--bs-body:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif`；`--bs-ink:#38592b`、`--bs-gold:#a17d27`、`--bs-paper:#e9e9bc`。
- 场景 `.bs-scene`：相对定位、`isolation:isolate`、纵向 flex、`aspect-ratio:var(--bs-ratio)`；背景绝对定位 `inset:0;z-index:-1;width:100%;height:100%`；场景底色允许由 `--bs-scene-paint` 覆盖。比例、焦点、底色逐槽见表；`--bs-focus` 回退 `50% 50%`，`--bs-base` 回退 `#e6e7b2`。`.bs-space{flex:1}` 保持原有上下文案关系。
- 常规 h1/h2/h3 为 `34/28/25px`，手写字体、字重400、行高1.35；小字通常12px。保留章节覆盖：介绍26px、相框标题31px、杯装26px、瓶装24px、袋装27px、原料章18px系统正文栈、微距29px、历史23px。
- 关键场景内边距依次为：首屏 `112px 24px 30px`、薄片 `32px 26px 24px`、杯装 `62px 22px 24px`、瓶装 `24px 24px 56px`、袋装 `54px 22px 24px`、原料 `58px 28px 38px`、微距 `54px 24px 22px`、收尾 `90px 24px 32px`。不以这些数值保证真实摄影净空。
- 错位段保留12列共享网格，相框占 `1/8`，文字卡占 `7/13`、同一行、`margin-top:86px;z-index:1`；相框内7列、图占 `1/7`。相框边框5px，标题旋转 `-3deg`，章节 header 内边距16px。
- 独立冰果窗 `margin-top:auto;margin-inline:12px`，不与背景合并。信纸内边距 `25px 22px 34px`；信纸 header 内边距12px、允许换行、底部间距65px；徽章旋转 `10deg`。

### 章节顺序与适配边界

默认示例顺序（主题对象可替换，章节可按业务增删重排）：通透首屏 → 留白介绍 → 错位相框与笔记 → 满宽植物照 → 薄片搭配 → 杯瓶双子场 → 透明原料袋 → 绿色底场与独立冰果窗 → 杯沿微距 → 历史拼贴 → 自然背景信纸收尾。共11个顶层 section，杯瓶属于同章的两个 scene；参考裁图重叠不新增章节。

8背景＋4素材是默认模板槽位登记，不要求每次业务全部启用。保留相框纸卡、独立细节图窗或收尾信纸模块时，分别保持其交叠、背景与素材分离及文字承托关系。可按业务替换文案、摄影、焦点及协调配色，也可增删重排章节或产品子场；不把摄影细节拆成新原子。适配后标为业务适配版，并同步重排/清空指涉、编号及专用占位；新增重复项沿用对应槽位职责并明确映射，不以默认登记数量限制业务。

`max-width:319px` 时相框与文字卡改为单列，相框宽82%，局部内边距收紧，首屏上内边距78px，信纸 header 底部间距38px；320px不触发该断点。保留附件现有规则，不额外添加断点。完整采用本配方时，正式 Hero 保留 `beverage-hero-bg` 的原有高度关系，不因长文自动增高；内容无法安全容纳时调整构图或说明尺寸冲突。其他非 Hero 场景可随内容增高并改变 cover 裁切，独立照片比例变化也可影响页面总高。不得通过隐藏溢出或强行缩字维持高度；使用时复核标题换行、叠压、主体安全、对比度、接缝与导出尺寸。

### 字体与使用验收

推荐 `font-curated-pool.json → combinations → combination.beverage-sensory-longpage`，为已有有效推荐方案，不代表已加载。附件实际使用上述楷体和系统字体栈；字体缺失会回退，不能据此认定参考字形已还原。不新增字体依赖，使用已具备的授权方案时复核字宽与换行。

附件中的占位和历史结构测试描述不等于本次真实素材验收。保留结构状态与视觉状态的区分；绑定素材时同步更新演示文案和状态说明。入库验收到结构与槽位契约为止，业务发布前再核实真实素材、配方事实、摄影净空与字体表现。

### 微距构图与过渡合同

#### 范围与景别
本规则可跨主题复用，不限定饮品、青果、冰块或杯瓶，可替换为承担相同视觉职责的对象；本组合默认保持11章、12场、8背景＋4素材。cup/bottle共章，ice属于ingredient内部图窗，不另计场。裁片重叠不是新增章节。未绑定时为结构就绪；真实图片绑定并复核后才判断视觉成立，不承诺已经还原。

主场以放大的局部与材质细节建立感官识别，不要求每图出现完整主体。保留微距版时，rim与ice均须呈现真实、可辨的材质微距细节，可使用同视觉职责的其他对象，不固定为冰杯，也不能以普通远景低清放大代替。slice为可替换的细节近摄，不承担唯一微距证明。杯瓶陈列、历史拼贴与林地不强制微距。允许按需删章；仍保留本组合微距识别时，至少留下一个实际微距场景。

`data-shot`：macro＝微距必需；close＝近景优先；medium-environment＝中景或环境；infographic＝信息图。属性表达素材职责，不是已验证结果。`conditional-alpha`只允许条件核验，不自动开启蒙版；hard保持明确边界。

#### 12槽构图表
以下宽×高均为主体在最终可见画面中的占比范围，属于设计目标，非原图实测；背景槽按cover后画面计算，素材槽按自身图窗计算。坐标原点左上。文字净空另须容纳真实排版包围盒及四周至少12px间距；表内比例不是可直接启用的渐隐范围。下列表格及调用片段中的果实、杯瓶、冰块、林地、配色与陈列文案仅作构图示例，不是必需题材；槽名仅为既有接口标识。换题材时沿用景别职责、裁切保护、文字净空和边缘核验机制，将具体对象及保护部位对应到实际主体；占比目标与安全区须按实际主体、裁切和排版重新复核，示例百分比不构成启用依据。

|槽名|景别；主体宽×高目标|主体／焦点区域|裁切允许|清晰与虚焦|文字净空|安全区与替换条件|
|---|---|---|---|---|---|---|
|beverage-hero-bg|近景优先；90–100%×55–75%|中下部巨幅容器局部、气泡与青果|可切容器上沿、侧壁，不必全产品|气泡、凝露和果皮清楚；远层可虚|顶部约35%，底部脚注另留空|只验上下无主体空场；切掉材质证据或文字拥挤则换图|
|beverage-frame-photo|近景优先；65–90%×65–90%|偏左两果，右侧让给叠卡|可切次要果缘，不切主果识别点|主果清晰，后果可浅虚|文字在图外卡片；避开右侧遮挡|相框内硬切；主果被卡片遮住则换左重构图|
|beverage-botanical-photo|近景优先；85–100%×85–100%|枝叶斜贯、果实与水珠分组|可切枝端、边缘次果|主果水珠清晰，边叶可虚|图内不加正文，图注在外|满幅图窗硬切；枝果关系不清则换图|
|beverage-slice-bg|近景优先；85–100%×42–58%|下部透光薄片、果肉边缘|可切薄片侧缘，保留厚薄与透光证据|薄片边缘清晰，远背景可虚|顶部约40–48%|仅验空白边缘；底部接触点不得淡出；冲突则换细节近摄|
|beverage-cup-bg|中景或环境；65–90%×42–60%|中下部杯组与台面|可切道具，不切主要杯口、杯底|主杯轮廓清晰，背景可虚|顶部约30%，底部规格行净空|上下纯空场才候选；杯体或台面接触点受损则换图|
|beverage-bottle-bg|中景或环境；65–90%×45–62%|中段主瓶、果实与器皿|可切次要器皿，不切瓶盖、瓶底和必要标签|主瓶清晰，后景可虚|顶部约20%，底部约22%|仅验上下空场；标签不可读或挡正文则换图|
|beverage-bag-bg|近景优先；80–100%×70–95%|右下斜向透明袋、杨桃与青果|可切袋口及侧缘，保留袋膜和果形|袋膜高光、果肉清晰；背景柔化|左上及左侧标题区低细节|斜袋接边默认硬切；文字落在果实上则换右重构图|
|beverage-ingredient-bg|近景优先；95–100%×90–100%|绿色果皮或切面纹理铺场|可裁纹理，勿伪造成独立透明层|可辨真实纹理，正文背后低反差|左上标题区；下部留给ice图窗|章边硬切；噪乱、抢图窗或遮字则换低干扰纹理|
|beverage-ice-photo|微距必需；85–100%×85–100%|冰中果实、气泡与折射界面居中|可切冰块外缘，不切主要折射证据|关键气泡、果皮与冰界面清晰；非焦面可虚|图内不叠字|矩形内边界硬切；无真实微距细节或低清放大则换图|
|beverage-rim-bg|微距必需；95–100%×60–78%|中下部杯沿弧线、碎冰和泡沫|可切杯身及左右边缘，不追求全杯|杯沿、冰晶清晰，液体深处可虚|顶部约20%，底部脚注低细节区|只验主体外空场，禁止消去冰尖；不够微距或标题冲突则换图|
|beverage-history-montage|信息图；75–95%×75–95%|样瓶与果园照片组合居中|不裁必要年代、标签和拼贴边框|信息清晰；照片内景深自然保留|正文在图外；图内信息留完整|素材边界硬切；信息不清或来源不适用则换等职责拼贴|
|beverage-closing-bg|中景或环境；90–100%×90–100%|树干、枝叶环境包围信纸|可裁外围枝叶，保留树干支撑关系|环境纹理自然，可虚但不抹平|正文位于不透明信纸内|复杂林地硬切；纸外背景破碎或争抢视觉则换环境图|

#### 11个邻接接缝
以下为设计建议；参考裁片不能证明透明通道，不能称为测得Alpha。同色承接也可保留硬边，不必做渐隐。

|顺序|接缝规则|
|---|---|
|hero→intro|浅黄绿同色承接；默认硬切。hero底边确有安全空场才可选局部Alpha，果实接边时禁用。|
|intro→frame|章底浅色场承接，保留frame上边细线硬切；无图片Alpha职责。|
|frame→botanical|明确硬切进入满幅枝果；相框、卡片边界不淡化。|
|botanical→slice|保留图注及分隔硬切；浅色可协调，不擦除枝叶。|
|slice→cup|浅黄绿同色承接、默认硬切；slice底或cup顶安全空场可择一退场，避开薄片接触点。|
|cup→bottle|同色陈列承接、默认硬切；cup底或bottle顶经验证后可择一Alpha，不淡化容器。|
|bottle→bag|浅色同色承接、默认硬切；仅bottle底边空场可选Alpha，bag斜袋边保持。|
|bag→ingredient|浅色到深绿明确硬切，作为风味换场，不统一蒙白。|
|ingredient→rim|深绿到浅绿明确硬切；ice内部矩形始终硬切，不拿窗口代替章间渐隐。|
|rim→history|浅色同色承接、默认硬切；rim底边仅在无杯身、冰晶和图内字时可选Alpha。|
|history→closing|明确硬切进入林地；不以平均绿色拼接复杂树叶，不跨信纸淡出。|

#### 四层与执行顺序
1. 摄影自带光学：真实景深、折射、透射、散景、凝露留在原图内，不自动拆成多层素材，不用滤镜制造折射。
2. 章底CSS色场：只负责图片下方承接。`.bs-scene`支持`--bs-scene-paint`，未设置时仍使用原`--bs-base`，默认视觉不变。
3. 局部光场：只做独立的低对比亮区，不冒充摄影光学、不替代边缘Alpha；本合同不自动新增光场节点或原子。
4. 图片Alpha：复用[surface.image-fade](../surfaces/diffuse-light.md#surface.image-fade)，只作用显式带`vl-image-fade`的img。文字容器不加蒙版，正文保持opacity=1。

先绑定真实图，确定容器与object-position。背景cover缩放系数s=max(窗宽/图宽,窗高/图高)，再按定位求裁切偏移，将主体、图内字和接触点映射到可见坐标；contain图窗按实际显示尺寸核验，不能套用cover裁切值。随后分别取接缝上侧实际底缘色A、下侧实际顶缘色B，必要时用章底A→B色场承接；不得用统一白色或统一tint擦主体。复杂纹理无法连续时直接硬切。

仅当最终可见边缘中存在不含主体、材质证据、图内字及接触点的低细节安全空场，且下方有可衔接色场，才设置退场范围。检查窄屏、实际文字高度及上下邻章后启用；不能为套比例改变主角。已有轮廓mask时不覆盖原mask，本模板默认不启用第二种遮罩。

#### 显式调用与撤销
模板已加入原子原文CSS，仅增加`.bs`作用域，不改参数接口。12个默认图片均不加`vl-image-fade`，无mask生效；属性标记本身不触发样式。不新增槽、不自动生成图片。

以下是绑定真实图并核验后才可采用的调用片段，不是默认模板状态。色值仅演示A/B写法，须替换为双侧实际取色；80%→100%仅适用于已经验证的对应20%安全空场。

底边启用示例：仅当cup槽实际素材底部20%经复核不含主体、材质证据、接触点和图内文字时适用；cup不限定杯装对象。

```html
<section class="bs-scene bs-cup" style="--bs-scene-paint:linear-gradient(#e8eabd,#e4e6b7)">
  <img class="bs-bg vl-image-fade" data-shot="medium-environment" data-edge-policy="conditional-alpha" data-background-slot="beverage-cup-bg" src="{{beverage-cup-bg}}" alt="" style="--vl-fade-angle:180deg;--vl-fade-stops:#000 0%,#000 80%,rgb(0 0 0 / .65) 91%,transparent 100%">
  <h2>杯装陈列</h2>
</section>
```

顶边启用示例：仅适用于bottle素材顶部20%已确认为安全空场时；0deg使退场指向顶部。

```html
<section class="bs-scene bs-bottle" style="--bs-scene-paint:linear-gradient(#e8eabd,#e4e6b7)">
  <img class="bs-bg vl-image-fade" data-shot="medium-environment" data-edge-policy="conditional-alpha" data-background-slot="beverage-bottle-bg" src="{{beverage-bottle-bg}}" alt="" style="--vl-fade-angle:0deg;--vl-fade-stops:#000 0%,#000 80%,rgb(0 0 0 / .65) 91%,transparent 100%">
  <h3>瓶装陈列</h3>
</section>
```

上述两例是同一接缝的备选，不默认叠加。调用时保留正式模板其余正文与布局。删除图片的`vl-image-fade`即可恢复未蒙版整图；同时移除自定义`--bs-scene-paint`可恢复原章底色。未配置stops时原子默认全不透明。换图、改裁切或改排版后，先撤销class，再重新验证。


### 原子采用映射

当前`.bs-*`为组合内联实现，尚未引用下述库类。`layout.dual-anchor-scene`已独立验证，可供调用，但原饮品微距组合尚未迁移。当前映射不新增硬依赖；只有CSS与节点迁移实际落地后，才将相应条目登记为依赖。

```json
{"dependencies":[],"planned_adoptions":["layout.dual-anchor-scene","layout.image-stage","layout.collage","shape.paper-mount","shape.badge","color.gradient"],"optional_candidates":["palette.botanical-green-gold","shape.rounded","material.paper"]}
```

#### 已实现机制与迁移边界

- **双端场景**：`.bs-scene`已有纵向flex、`.bs-bg`绝对覆盖、上下正常流文案及`.bs-space`弹性空场。hero/cup/bottle/rim/closing适合迁移至`layout.dual-anchor-scene`。根节点须实际增加`vl-stage vl-dual-scene`，背景增加`vl-stage__image`，上下内容包装并挂对应类，空场改为`vl-dual-scene__space`，移除被替代的内联布局声明。`--bs-ratio`对应`--vl-stage-ratio`，上述五段依次为364/1074、364/614、364/602、364/602、364/590；`--bs-focus`对应`--vl-stage-position`，fit=cover。原空场无安全下限，迁移可从96px试起，但属于新增保护，可能改变段高，不承诺像素等价。
- **非双端场景**：slice、bag仅有顶部内容，宜按`layout.image-stage`单端适配；ingredient下方为独立图窗，不是底部文案，保留`.bs-ice-window{margin-top:auto}`的组合关系。比例、padding和焦点仍按实例绑定，不机械套用双端原子。
- **拼贴**：`.bs-shared-grid`、`.bs-frame`、`.bs-text-card`对应`layout.collage`候选。迁移使用12列、gap=0、inset=0；相框start=1/span=7/row=1，文卡start=7/span=6/row=1/order=1。文卡86px顶部占位必须保留为margin-top，不改成脱离占位的shift-y。小于319px时改1列、gap=22px，各项start=auto/span=1/row=auto并取消重叠。相框内部7列、图像占6列仍属组合适配。
- **相框衬纸**：`.bs-frame`对应`shape.paper-mount`候选，paper-pad=8px、paper-footer=25px、tint=#e8e7c7；5px描边、阴影与内部网格另保留。小屏footer改8px。当前无胶带节点，不为采用原子额外添加胶带。
- **徽章**：`.bs-seal`对应`shape.badge`候选，radius=50%、pad-y=10px、pad-x=8px、border=2px，背景#e8e79b、边色#758441。它是自适应多行章，不加固定圆形circle类；rotate(10deg)、字体和line-height=1.35由组合保留。
- **渐变**：intro可映射180deg、#e8e9bc→#e7e5b5；frame-story可映射110deg、#e1e4aa→#f0edc4。history现为`radial-gradient(ellipse at 60% 35%,#f2efbf,#e5e4af)`，隐式farthest-corner不与原子的显式半径天然等价，未校准前保留内联，不称完全复用。
- **可选配色与表面**：`palette.botanical-green-gold`仅颜色角色相近；当前ink=#38592b、gold=#a17d27、paper=#e9e9bc，不是已绑定的库预设。`shape.rounded`未采用；若改造须实际引入`shape.folder`的edge/surface/content结构，方角卡片无需强加层级。`material.paper`未实现：无纤维资源与texture/light材质层，浅底、渐变和阴影不能等同纸纤维。

#### CSS与槽位验证

原样式下完成280/320/364px × 普通/双倍文本共6组验证；每组11段、12槽全部加载，其中8个背景、4个独立图像，无报告级水平溢出或正文越界。四模块截图可见相框与错位文卡、背景与独立图窗、双端文案与当前净空、信纸与徽章的几何和层级效果。当前响应式规则为280px单列，320/364px保留共享网格。

成立范围仅为CSS与槽位。第二模块浅黄文字在灰色测试背景上对比偏弱，正式背景需重新验收可读性。原`.bs-space{flex:1}`仍可缩至0，双倍文本测试通过不保证任意长文的中央净空。新原子的12组独立验证不替代组合迁移后的回归测试。

中性标尺图不是摄影；源图净空坐标可能被cover裁切，不能据此保证真实主体位置。实际微距摄影、素材焦点、指定字体及纸纤维均未测，不作摄影还原或整图还原声明。


<a id="combination.clay-citywalk-longpage"></a>
## 3D趣味粘土活动导览长页

风格标签：二级：趣味创意风 / 趣味拟物。以连续的天空、城市、草地和道路承托独立角色、图窗及拟物展架，适用城市漫游、活动导览等社媒长图。结构可复用，仍保留原配方的趣味粘土风；CSS只近似厚边、内高光与阴影，不代表真实粘土表面。

**入库就绪＝结构与槽位契约就绪。** 本条目按槽位、内容说明、必要性与可替换性验收，不要求生图或原图摄影还原。参考摄影、真实素材及字体还原未验，使用时按业务填槽，不据此宣称最终视觉通过。

### 模板读取

```json
{"template":"clay-citywalk-longpage.html","selector":"main[data-recipe=\"clay-citywalk-longpage\"]","styleSelector":"style[data-recipe-css=\"clay-citywalk-longpage\"]"}
```

同时读取 main 与对应 style，保持附件 HTML 布局，不新增原子、图片层或未知依赖。`data-background-slot` 标识背景，`data-asset-slot` 标识独立素材。气泡、路牌、柜体、屋顶、牌匾和门店台面属于 CSS 载体，不计图片。

### 复用必选与可选

本段优先于下文的案例主题、章节名称和示例数量。采用连续背景结构时，clay-page-bg必需且始终为一张连续背景；采用首屏角色主场结构时，主角必需。其余地图、照片图窗、权益及奖品展示仅在保留对应图文模块时条件必需，陪伴角色和装饰可选。允许跨主题替换及增删重排章节、步骤、权益格和展示项；三步、六格、八店均为示例数量。适配后标为业务适配版，并同步重排/清空指涉、数量、编号、图注、alt及专用占位。下表路线、门店、权益等为默认业务示例，可换同视觉职责、同粘土风且事实一致的业务内容，不强制城市漫游主题。1＋28是默认模板登记槽数，不是所有任务必选素材数；新增重复项沿用对应槽位职责并明确映射，不增加背景层。透明角色保持独立，不烘焙进背景；保留门店招牌模块时仍保持42px台面。以下尺寸、比例、位置和焦点参数均为适配起点，须按实际内容复核；本次仅修订契约，不改附件HTML。

### 槽位契约：默认1 整页背景＋28 素材，共 29 槽

仅 `clay-page-bg` 是连续背景；天空、草地和道路不是三张背景。独立角色、配件、奖品及权益图使用透明底并保留轮廓、脚底与投影安全边；地图及照片图窗不透明，均按原有 contain 规则显示。

必要性与可替换性独立。采用连续背景结构时，必需提供1张整页连续背景；采用首屏主角结构时，主角必需。地图、照片图窗、权益格及奖品展示仅在保留对应图文模块时条件必需，陪伴角色、配件和装饰可选。必需不表示指定图片不可替换；duck、pigeon、snail等是稳定接口名，不强制物种、原品牌、原门店或指定奖品。替换以同视觉职责、同粘土风及适配后图文事实一致为准；背景负责连续环境，独立角色和图窗负责前景内容，不得将独立角色烘焙进背景。

下表各行的章节、主题、对象、序号、数量和布局描述均按默认示例理解，不是跨业务必选内容。例如“三步”“六图”“八图”“保持3×2格”说明默认实例及排布，不要求固定条目数；“六图不合并”“八图为独立槽”约束的是启用项各自独立，不是必须凑足数量。路线、门店、活动及权益可换为同视觉职责的业务内容；相应事实核验要求随实际内容更新。地图不限真实街道，可换园区、展区、活动动线或其他导览示意图，须明确示意性质，不虚构实际距离和通行条件。1＋28＝29是默认模板登记槽数，启用素材及登记数量可随模块增删而增减；新增项须明确独立槽名与映射，但采用连续背景结构时仍只用1张整页背景。

删除或增减模块形成业务适配版，须同步重排和更新指涉，包括数量、编号、标题、说明、图注及alt。未采用项须清理对应图片、专用占位包装、空白高度、空网格轨道、依附阴影及失效文字关系，不留破图；共享容器仍有有效内容时仅清理被删项。表中尺寸和布局参数为适配起点，须按实际内容复核。下表为调用时的处理契约，本条目不输出改写后的HTML，不要求生图，也不声称真实素材或最终视觉已验收。

|槽名|背景/素材类型|内容说明|必需/条件必需/可选|可替换及约束|不提供时处理|
|---|---|---|---|---|---|
|clay-page-bg|背景；单张不透明连续场景图|main从hero到closing的天空、城市、草地和道路环境；默认cover、center top|必需|可换同风格连续城市漫游环境；匹配main最终实测比例，给文字、角色和展架留净空；不含独立角色、牌匾或正文|不输出空src或破图；根底色仅供结构预览，不等于已填背景；不得拆成多背景补位|
|clay-hero-duck|素材；透明独立主角|hero主视觉漫游角色，宽随舞台、高262px；与气泡和方向牌呼应|必需|可换同语义粘土风主角，不固定鸭子；避让标题、气泡及路牌，保留完整轮廓与落点|待填；取消主角须连同舞台空位和依附文案调整，所得版本业务适配版，须同步重排和更新指涉|
|clay-step-card|素材；透明配件|steps第一步行内导览凭证，28×23px|可选|可换导览卡、通行凭证等同语义小图，说明以HTML为主，不能遮字|删除行内img及其专用间距；清理指图用语，保留有效的领卡步骤文字|
|clay-step-cone|素材；透明配件|steps第一步右侧引导图标，55×62px，窄屏宽43px|可选|可换表示领取或出发的粘土风配件，不强制路锥；不能用图标代替必要说明|删除图标及右侧专用空位、相关指图文字；不保留空图标列|
|clay-step-bag|素材；透明配件|steps第二步右侧漫游随行图标，55×62px，窄屏宽43px|可选|可换表达出行、探索的配件，不强制提袋；保持同组风格与尺度|删除图标及右侧专用空位、相关指图文字；不保留空图标列|
|clay-step-ticket|素材；透明配件|steps第三步右侧活动参与图标，55×62px，窄屏宽43px|可选|可换活动凭证或体验配件，不强制票券；不得暗示未经核实的参与权益|删除图标及右侧专用空位、相关指图文字；不保留空图标列|
|clay-skate-duck|素材；透明独立角色|steps下方运动或出发陪伴角色，110×99px|可选|可换同语义活泼角色，不固定滑板鸭；不能并入背景或压住步骤板|删除整个专用.cc-step-decor及100px高度、19px上间距，清理相关角色文案|
|clay-benefit-01|素材；透明权益展示|benefits第1格，默认出行灵感；图高67px、宽随格|条件必需：保留第1图文格时|可换真实业务的路线或出行内容图；标题和说明同步替换，保持3×2格及轮廓安全|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-benefit-02|素材；透明权益展示|benefits第2格，默认街角发现；图高67px、宽随格|条件必需：保留第2图文格时|可换探索点位或发现主题配件；与本格文字一致，不限定具体物件|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-benefit-03|素材；透明权益展示|benefits第3格，默认主题体验；图高67px、宽随格|条件必需：保留第3图文格时|可换实际活动体验图形；不把未核实安排写成已确认权益|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-benefit-04|素材；透明权益展示|benefits第4格，默认漫游记录；图高67px、宽随格|条件必需：保留第4图文格时|可换记录、集章等同语义内容；相关玩法文字需同步核实|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-benefit-05|素材；透明权益展示|benefits第5格，默认小店相遇；图高67px、宽随格|条件必需：保留第5图文格时|可换门店互动等同语义内容；不要求固定商户，业务关系须真实|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-benefit-06|素材；透明权益展示|benefits第6格，默认纪念收藏；图高67px、宽随格|条件必需：保留第6图文格时|可换纪念物或收藏主题配件；须与实际规则一致，六图不合并成一张|待填；取消此格须删整格及关联说明，增减权益格后为业务适配版，须同步重排和更新指涉|
|clay-citywalk-map|素材；不透明独立地图|citywalk路线地图，4:5图窗、contain，路线说明在窗外|条件必需：保留地图导览模块时|可换同视觉职责的路线图、园区或展区导览图、活动动线图等，不限实际街道；适用的起终点、图例及关键点须完整可读、不裁断；示意图须明确标注，涉及真实距离和通行信息时须核实|待填；地图空窗不能作为完整路线交付；删地图章则业务适配版，须同步重排和更新指涉|
|clay-resting-duck|素材；透明独立角色|citywalk地图下方休息陪伴角色，91×79px|可选|可换休息或慢行语义角色，不固定鸭子；不能挤压路线详情与安全说明|删除img和91px专用列及空隙；保留有效路线文字，删除依附角色的指图关系|
|clay-reward-group|素材；透明奖品组合|rewards福利牌内独立奖品组，高158px，窄屏160px|条件必需：保留福利图文模块时|可换实际奖品或纪念物组合，不含牌匾；与领取条件、数量和期限一致，避开右侧说明|待填；无福利业务则删除对应图文模块及空位，删福利章须标为业务适配版，须同步重排和更新指涉|
|clay-snail|素材；透明独立装饰|rewards下方慢行节奏装饰，78×65px|可选|可换同语义小角色或慢行装饰，不强制蜗牛；保持轮廓安全|删除整个专用.cc-snail-space及67px高度，清理相关角色文案|
|clay-theme-photo|素材；不透明活动照片|theme红顶活动展架内场景图，4:3图窗、contain|条件必需：保留主题活动图文模块时|可换已核实活动照片；标题、日期、地点和参与方式用HTML另排，不烘焙进照片|待填；取消活动则删除对应图窗、说明及专用空位；删主题章则业务适配版，须同步重排和更新指涉|
|clay-pigeon|素材；透明独立角色|shops蓝顶招牌旁陪伴角色，52×64px，底部对齐并下沉11px|可选|可换同语义小角色，不固定鸽子；避让招牌，脚部落点与CSS台面协调|删除img、专用角色列及接触影伪元素，清理角色指涉；保留招牌和42pxCSS台面，不留空角色位|
|clay-shop-01|素材；不透明门店照片|shops第1项，默认咖啡空间；1:1图窗，宽58px、窄屏49px|条件必需：保留第1门店图文项时|可换任意已确认参与门店的代表照片；店名、地址、说明与图一致，主体contain|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-02|素材；不透明门店照片|shops第2项，默认烘焙小店；1:1图窗，宽58px、窄屏49px|条件必需：保留第2门店图文项时|可换其他已确认门店，不固定烘焙类别；同步名称、地址和营业信息|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-03|素材；不透明门店照片|shops第3项，默认独立书店；1:1图窗，宽58px、窄屏49px|条件必需：保留第3门店图文项时|可换其他已确认门店；同步开放信息及店内规则，不使用无关照片|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-04|素材；不透明门店照片|shops第4项，默认手作工作室；1:1图窗，宽58px、窄屏49px|条件必需：保留第4门店图文项时|可换其他已确认门店；体验或预约信息须与真实业务一致|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-05|素材；不透明门店照片|shops第5项，默认花草生活铺；1:1图窗，宽58px、窄屏49px|条件必需：保留第5门店图文项时|可换其他已确认门店；保留代表主体并同步到店安排，不强制花草类别|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-06|素材；不透明门店照片|shops第6项，默认轻食空间；1:1图窗，宽58px、窄屏49px|条件必需：保留第6门店图文项时|可换其他已确认门店；餐饮或补给说明按真实业务更新|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-07|素材；不透明门店照片|shops第7项，默认创意杂货铺；1:1图窗，宽58px、窄屏49px|条件必需：保留第7门店图文项时|可换其他已确认门店；商品及活动说明与图一致，不限定类别|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-shop-08|素材；不透明门店照片|shops第8项，默认社区艺术空间；1:1图窗，宽58px、窄屏49px|条件必需：保留第8门店图文项时|可换其他已确认门店；同步参观或参与条件，八图为独立槽而非合图|待填；无对应门店则删整项、空图窗并更新数量和编号，增减展示项后为业务适配版，须同步重排和更新指涉|
|clay-closing-cone|素材；透明独立配件|closing左侧出行或方向提示装饰，74×90px|可选|可换同语义粘土配件，不强制路锥；不并入道路背景|删除图片和专用占位列、指图文字；仅剩另一角色时收掉无效空位，两者都删则移除整个装饰包装|
|clay-closing-duck|素材；透明独立角色|closing右侧告别或继续出发的角色，104×117px|可选|可换同语义收尾角色，不固定鸭子；与首屏风格协调但不要求同一物种|删除图片和专用占位列、指图文字；两者都删则移除.cc-closing-decor、117px最小高度及14px底部间距|

### 连续背景与前景边界

背景 img 是 main 直接子节点，位于内容末尾；`position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none`。main 保留相对定位、`isolation:isolate` 和正常流自然高度；直接前景 section/div 为相对定位、`z-index:1`，section及field保持透明。

不使用分区纯色、伪元素、渐变mask或独立道路层重建场景；背景之外的牌匾、纸面及台面仍可使用原有CSS底色与渐变。连续图不包含独立角色、标题和柜体。按最终页面坐标校准道路交界、角色脚下区域及文字保护区，不推断遮挡后的道路拓扑。

`cover` 保证铺满但可能裁切，不保证全图完整或道路自动对齐。文案增高、字体或页面宽度改变后，须重新核对背景母版比例及 `object-position`；必要时由业务提供匹配新成稿比例的连续背景，不靠增加图片槽解决。

### CSS关键参数

- 根 `.cc`：`width:364px;max-width:100%;margin:0 auto`，回退底色 `#a5b868`，正文 `13px/1.6`，`overflow-wrap:anywhere`，全体 `box-sizing:border-box`。
- 变量：`--cc-page-bg-fit:cover`；`--cc-page-bg-position:center top`；`--cc-board-width:calc(100% - 36px)`；`--cc-border:4px`；`--cc-edge:#c7c8b9`；`--cc-paper:#fff9d9`；`--cc-ink:#534a30`；`--cc-blue:#59b4db`；`--cc-red:#e75c43`；`--cc-green:#306c50`；`--cc-shadow:0 5px 0 #656c5266,0 8px 12px #34432230`。
- h1 `34px/1.2`、字重900、字距1px；h2通常 `24px/1.3`、字重900；h3通常 `14px/1.5`，小字12px。首屏文字内边距 `28px 20px 0`，舞台 `min-height:306px;padding:14px 25px 30px`。
- 步骤板默认三步，采用纵向网格、间距8px；每行默认列宽 `54px minmax(0,1fr) 55px`、列间距7px。权益柜默认六格，网格为 `repeat(3,minmax(0,1fr))`、间距7px，形成3×2示例排布；默认后排配色与前排区分。步骤和权益格均可增减，须同步调整行列、配色、编号及专用占位，不以默认数量限制业务。
- 地图窗4:5，活动窗4:3，门店窗1:1，图窗图片 `width:100%;height:100%;object-fit:contain`。福利图文两列 `minmax(0,1.08fr) minmax(0,1fr)`，间距10px；门店行 `58px minmax(0,1fr)`，间距9px。
- 保留圆角厚边、内高光、柜顶负边距、吊牌挂杆、红顶活动展架与蓝顶招牌的原有层级，不以CSS模拟真实照片或完整3D建模。

### 门店招牌台面

`.cc-shop-counter` 总高 **42px**；顶面26px、前沿18px，从24px处开始，重叠2px。台面属于CSS，不计图片，也不新增背景槽。招牌与角色由同一头部网格承托，招牌下沉7px、角色下沉11px；原角色接触影是 `.cc-shop-head:after`。

完整布局保留台面的顶面、前沿、阴影与招牌关系。可选角色删除时只清理其专用列、接触影与空位，不能连带删除42px台面。局部渐变用于台面而非整页环境；真实透明脚部落点仍需使用时检查。

### 章节顺序与适配边界

默认示例为九段：hero首屏 → intro引言 → steps三步参与 → benefits六格补给柜 → citywalk地图导览 → rewards福利 → theme红顶活动 → shops蓝顶八项门店 → closing收尾。章节、步骤、权益格和展示项均可按业务增删重排，主题对象也可替换。默认首屏外其余章节在 `.cc-field` 内；参考中的重复裁图、首屏放大图或展示底不增加章节。

三步、六格3×2及八项门店仅为默认实例，地图、福利和主题活动也不是每次业务必选。保留模块时履行对应槽位契约；移除可选装饰不等于删除章节。增删重排后为业务适配版，须同步重排和更新指涉，并清理失效编号、图文关系及专用占位。1整页背景＋28素材是默认登记，不是固定启用数量；业务适配可增减素材槽并更新登记与映射，连续背景采用时仍必需且仅为1张，不拆分背景层。

`max-width:320px` 时默认板宽改为 `calc(100% - 24px)`，h1降至30px；步骤列宽改为 `47px minmax(0,1fr) 43px`、间距5px；默认六格示例为3×2，间距4px，增减条目时同步重排；福利图文改为单列、图高160px；门店图窗宽49px、列间距7px。本次不改附件HTML或增加断点；业务适配时在现有断点内复核网格、换行和占位。

正文自然增高，不设根或图窗的overflow裁切，不用隐藏溢出或强制缩字维持参考高度。更长内容与不同素材比例需检查板内换行、角色轮廓、背景裁切、道路净空和导出尺寸。缺图时不得输出未解析占位地址或破图；必要图片待填可保留明确标注的结构预览，但不是业务成稿。

### 字体与使用验收

推荐 `font-curated-pool.json → combinations → combination.clay-citywalk-longpage`，为已有有效推荐方案，不代表已加载。附件实际字体栈为 `"PingFang SC","Microsoft YaHei",sans-serif`；不新增字体依赖，也不宣称已还原参考手写字。使用既有授权字体时复核字宽、字重和换行。

附件的占位图及历史结构测试描述不是本次真实素材验收。结构状态与素材、视觉状态分开记录；绑定时同步更新演示标题、alt、状态文字、日期、地点、门店、奖品及参与规则。入库验收到结构与槽位契约为止，业务发布前再核实真实素材、路线事实、权益信息、连续背景适配与字体表现。

### 原子采用映射

当前`.cc-*`均为组合内联实现，下列为待迁移或可选映射，不是已经引用的库类或当前硬依赖。复用已有机制，不新增台面、普通圆角、徽章、渐变或纸纹同义条目。

```json
{"dependencies":[],"planned_adoptions":["shape.sloped-deck","shape.badge","color.gradient"],"optional_candidates":["shape.shelf-profile","shape.rounded","palette.sky-lime","material.paper"]}
```

#### 已实现机制与迁移边界

- **台面**：`.cc-shop-counter`及其top/front已有梯形顶面与独立前沿，直接对应已有`shape.sloped-deck`，不新增台面ID。迁移拟用cs-deck/top/front，cs-inset=4%、cs-front-height=18px；顶面26px、前沿margin-top:-2px，总高42px。须覆盖原子top默认padding为0并设26px高度，不能忽略原子前沿的正常流占位。顶面绑定#a0dced→#7fcce9(42%)→#61b8df，前沿绑定#64bee5→#4ba8d3(55%)→#368ab4；阴影与圆角保留在组合。`shape.shelf-profile`是可选的另一截面机制，并未采用，也不与sloped-deck叠加。
- **徽章**：`.cc-tag`、`.cc-label`、`.cc-pill-title`可迁移至`shape.badge`。三者分别为radius=20/12/40px，padding=4px 13px、6px 18px、6px 20px，border=0/2/4px；背景、ink和edge-color按当前节点绑定。字号、阴影及标题支杆伪元素保留在组合；bubble的不规则椭圆不强称徽章完整复用。
- **圆角**：`.cc-board`、`.cc-window`、`.cc-shop-row`当前只是内联圆角边框，未调用`shape.rounded`。可选参考radius/border-width分别为15/4px、7/3px、10/2px；真实采用须加载`shape.folder`基础并保留edge/surface/content。无需为登记依赖强加结构或玻璃材质。
- **渐变**：两个台面可分别使用`color.gradient`的180deg线性渐变及上述色标，通过cs-top/front消费`--vl-paint`，迁移后不同时维护第二套渐变。店招接触阴影是隐式椭圆径向渐变，未校准显式半径接口前保留内联。
- **配色**：`palette.sky-lime`仅角色相近，当前blue=#59b4db、red=#e75c43、green=#306c50、paper=#fff9d9、ink=#534a30并非库预设，尚未绑定变量，不登记为实际依赖。
- **材质**：`material.paper`未实现，缺少纤维纹理与漫反射层。浅色牌匾、卡片的底色、边框和投影只构成平面表面及厚度提示，不证明真实纸张或真实黏土材质。

店招与鸽子的两列网格、translateY承托和背景覆盖仍属组合关系，未采用`layout.collage`。`shape.thin-sided-key`、`shape.stepped-frame`不对应当前普通卡片轮廓；照片窗无衬纸底部留白，不强绑`shape.paper-mount`。

`layout.dual-anchor-scene`已独立通过其双端布局合同验证，可供有该需求的场景调用；当前黏土节点没有据此建立采用关系，不新增依赖。饮品微距组合也尚未迁移，其测试只覆盖CSS与中性素材槽位，摄影未测；该结果不外推为黏土组合的渲染或材质验收。

只有实际加载原子CSS、迁移节点并完成组合回归后，才将待迁移条目提升为dependencies；外观相似和参数可映射不等于已调用。
