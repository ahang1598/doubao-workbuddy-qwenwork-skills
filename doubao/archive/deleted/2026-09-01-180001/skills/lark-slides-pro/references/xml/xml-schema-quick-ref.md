# XML Schema 快速参考

本文是飞书 Slides XML 的元素与属性速查：从根元素结构到各类内容元素、颜色样式和完整范例都在其中，是 [slides_xml_schema_definition.xml](slides_xml_schema_definition.xml) 的精简版摘要。**本文与 XSD 不一致时，以本文为准（与 XSD 冲突处均经实测验证）**。

**生成任何 XML 前务必完整读到末尾**——图表、表格、颜色渐变、完整示例等高频要点集中在文档后半段，中途截断极易漏读。全文结构如下：

- **最小示例**：先看这节建立整体认知。
- **presentation 根元素**、**theme 与文本类型**、**slide 元素**、**content 内容模型**（含 `p 段落与内联标签`）：文档骨架与文本模型。
- **data 常用元素**：`shape`、`line`、`polyline`、`img`、`icon`、`table`、`chart` 七类可视元素的写法。
- **颜色与样式**：`fill`、`border`、`颜色格式`、`页面背景`。
- **note 示例**、**完整示例**、**详细参考**。

每个元素小节统一按 **描述 → 属性 → 子元素 → 注意事项 → 示例** 的顺序组织。

## 最小示例

```xml
<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
  <slide>
    <data>
      <shape type="text" topLeftX="80" topLeftY="80" width="800" height="120">
        <content textType="title" fontSize="36">
          <p>文字</p>
        </content>
      </shape>
    </data>
  </slide>
</presentation>
```

文本和属性值里的 `&`、`<`、`>` 必须转义为 `&amp;` / `&lt;` / `&gt;`。

## presentation 根元素

**属性**

| 属性 | 必需 | 说明 |
|------|------|------|
| `width` | 是 | 演示文稿宽度，必须固定设置为 960 |
| `height` | 是 | 演示文稿高度，必须固定设置为 540 |
| `id` | 否 | 演示文稿标识 |

**子元素**

- `<title>?`
- `<theme>?`
- `<slide>+`

**注意事项**

- 协议标准写法应使用 `<presentation xmlns="https://www.larkoffice.com/sml/2.0">`，始终带上命名空间。
- 所有坐标和尺寸单位是 px，主体元素必须落在画布内。
- `<slide>` 每份最多 100 页。
- `+create` 不带 `--slides` 建出的是 **0 页空演示文稿**（是逐页添加前的合法中间态）。

## theme 与文本类型

**属性**

`<textStyles>` 下各文本类型元素（`<title>`、`<body>` 等）的常用属性：

| 属性 | 说明 |
|------|------|
| `fontFamily` | 字体 |
| `fontSize` | 字号 |
| `fontColor` | 字体颜色 |

`textStyles` 的 schema 默认值如下：

| textType | 默认字号 |
|----------|----------|
| `title` | 54 |
| `headline` | 38 |
| `sub-headline` | 32 |
| `body` | 16 |
| `caption` | 12 |

**子元素**

`<theme>` 当前包含两部分：

- `<background>`：演示文稿级背景填充
- `<textStyles>`：主题文本样式集合

`<textStyles>` 下可选子元素包括：

- `<title>`
- `<headline>`
- `<sub-headline>`
- `<body>`
- `<caption>`

这些元素定义的是主题默认样式，不是页面结构。

**注意事项**

- XSD 中的 `title`、`headline`、`sub-headline`、`body`、`caption` 主要出现在：
  - `<theme><textStyles>...</textStyles></theme>` 中，作为主题文本样式
  - `<content textType="...">` 中，作为内容的文本类型
- 默认字号是省略 `fontSize` 时的兜底字号，不是推荐值，且明显偏大；字号必须在 `<content>` 上显式设置，详见「content 内容模型」。

## slide 元素

**属性**

| 属性 | 必需 | 说明 |
|------|------|------|
| `id` | 否 | 幻灯片标识 |

**子元素**

- `<style>?` - 页面样式，目前可放 `<fill>`
- `<data>?` - 页面元素容器，可放 `shape`、`line`、`polyline`、`img`、`icon`、`table`、`chart`（`<undefined>` 仅在服务端导出时出现、代表不支持的类型，不要手写，写入会报 3350001）
- `<note>?` - 演讲者备注，内部可放 `<content>`

**注意事项**

- 这意味着 `<title>`、`<headline>`、`<sub-headline>`、`<body>`、`<caption>` 不能直接放在 `<slide>` 下；页面文本一律用 `<shape type="text">` + `<content>` 表达。

## content 内容模型

`<content>` 可出现在 `shape`、`table/td`、`note` 中。

**属性**

常用属性包括：

| 属性 | 说明 |
|------|------|
| `textType` | `title` / `headline` / `sub-headline` / `body` / `caption` |
| `verticalAlign` | 垂直对齐：`top` / `middle` / `bottom`（默认 `middle`） |
| `textAlign` | 文本对齐：`left` / `center` / `right` / `justify` / `dist`（`shape type="text"` 默认 `left`，其它形状默认 `center`） |
| `lineSpacing` | 行间距，默认 `multiple:1.5` |
| `letterSpacing` | 字间距，单位 px，作用于 `content`/`p` 层级，默认 `0`（正值拉开、负值收紧） |
| `fontSize` | 字号 |
| `fontFamily` | 字体，常用「思源黑体」「思源宋体」（最终以选定设计系统为准） |
| `color` | 字体颜色（注意用 `color`，不是 `fontColor`；`fontColor` 只用于 `<theme><textStyles>`） |
| `bold` / `italic` / `underline` / `strikethrough` | 内容级样式 |
| `wrap` | 是否自动换行，默认 `true`，会按文本框宽度自动折行 |
| `autoFit` | 自动缩排：`normal-auto-fit` / `no-auto-fit` / `shape-auto-fit`（默认 `no-auto-fit`） |

**子元素**

`<content>` 直接子元素只有：

- `<p>`
- `<ul>`
- `<ol>`

**注意事项**

- 字号必须显式设置 `<content>` 的 `fontSize` 属性，不要依赖 `textType` 的默认字号兜底，这些兜底值明显偏大。本文档示例中的 `fontSize` 仅用于演示"必须显式声明"，不是推荐值，实际字号以选定设计系统为准。
- 文字颜色必须用 `<content>` 的 `color` 属性而不是 `fontColor` 属性（`fontColor` 仅用于 `<theme><textStyles>` 主题样式）。
- 文字行间距必须设置 `<content>` 的 `lineSpacing="multiple:xx"` 或 `lineSpacing="fixed:xx"` 而不是 `lineSpacing="xx"`。
- 字间距 `letterSpacing` 单位是 px：实用区间约 **`-0.5 ~ 2`**：标题想拉开质感设 `1~2`，正文一般 `0` 或轻微负值（如 `-0.5`）收紧即可；数值过大会把文字撑出容器、过小会导致字符重叠。
- **短标签、单行指标、标题，要避免按文本框宽度自动折行，先把 `width` 留够（中英文、数字、符号不等宽，多留三四个字余量），再配 `wrap="false"`。**

### p 段落与内联标签

`<p>` 是段落元素，可混排纯文本和内联标签。

**子元素**

可混排的内联标签：

- `<br/>`
- `<strong>`
- `<em>`
- `<u>`
- `<span>`
- `<del>`
- `<a>`
- `<shadow>`
- `<outline>`
- `<formula>`

**注意事项**

- **内联样式只能挂在 `<span>` 上**：`<strong>`、`<em>`、`<u>`、`<del>` 不接受任何样式属性（给它们写 `color` / `fontSize` 等会触发 `sxsd_unsupported_attr`）。要给局部文字上色、改字号/字体，用 `<span>`——它支持 `color`、`backgroundColor`、`fontSize`、`fontFamily`、`bold`、`italic`、`underline`、`strikethrough`。例如把"加粗且变色"写成 `<span bold="true" color="rgba(37,99,235,1)">重点</span>`，不要写成 `<strong color="...">`。
- **任何数学/物理/化学公式等表达式一律用 `<formula>`，禁止退化成纯文本或 Unicode 上下标**：只要表达式里出现上下标、根号、分式、积分、求和、极限、矩阵、希腊字母、向量箭头等符号（例如 `E=mc^2`、`x^2+y^2=r^2`、`∫f(x)dx`、`α_i`、`\sum_{i=1}^n`），需要写成 Latex 形式的字符 `<formula><latex><![CDATA[…]]></latex></formula>`，不允许写成 `E=mc^2`、`x²+y²=r²`、`∫f(x)dx` 这类纯文本或 Unicode 近似。LaTeX 源码放在 CDATA 里，无需再对反斜杠做 XML 转义。页面标题、副标题、导读句、正文段落、列表项、坐标/图例标签、里凡是出现公式表达式的，都要写成 `<formula>`。

**示例**

```xml
<content textType="body" textAlign="left" fontSize="16">
  <p>正文内容 <strong>加粗</strong> <em>斜体</em> <a href="https://example.com">链接</a></p>
  <p>令 <formula><latex>表达式1</latex></formula> 代入 <formula><latex>表达式2</latex></formula> 的泰勒展开，分离实部虚部即可推得。</p>
  <ul>
    <li><p>列表项 1<formula><latex>表达式1</latex></formula></p></li>
    <li><p>列表项 2<formula><latex>表达式2</latex></formula></p></li>
  </ul>
</content>
```

## data 常用元素

所有页面元素都放在 `<data>` 中。

**注意事项**

- 同一 `<data>` 内元素按文档先后顺序绘制，**后写的在上层**（想让文字压在形状上，就把文字写在形状之后）。

### shape

`shape` 可表示普通形状，也可表示文本框。文本框推荐使用 `type="text"`。

**属性**

| 属性 | 必需 | 说明 |
|------|------|------|
| `type` | 是 | 形状类型：常用 `text`（文本框）/ `rect` / `round-rect` / `slides-full-round-rect` / `ellipse` / `triangle` / `diamond`，更多取值见 schema |
| `topLeftX` | 是 | 左上角 X 坐标 |
| `topLeftY` | 是 | 左上角 Y 坐标 |
| `width` | 是 | 宽度 |
| `height` | 是 | 高度 |
| `presetHandlers` | 否 | 圆角半径（px） |
| `rotation` | 否 | 旋转角度（度），取值 `[0, 360)`，默认 `0`，不支持负数 |
| `flipX` / `flipY` | 否 | 翻转 |
| `alpha` | 否 | 透明度 |

**子元素**

可选子元素：

- `<fill>`
- `<border>`
- `<reflection>`
- `<shadow>`
- `<content>`

**注意事项**

- `<shape type="rect">` 只是形状不是容器，`<icon>`、`<img>`、`<shape type="text">` 和其他 `<shape>` 必须与它平级靠坐标叠放。
- **圆角**用 `presetHandlers` 设置，值是圆角半径，**单位 px，不是比例**。
- 半径超过 `min(width, height) / 2` 会自动夹紧到该值，所以胶囊形设成 `height/2` 即可，也可以直接用 `type="slides-full-round-rect"`（全圆角，不需要 `presetHandlers`）。
- `rect` 和 `round-rect` 写了 `presetHandlers` 后行为完全一致，区别只在不写时的默认值：`rect` 是 `0`（直角），`round-rect` 是 `16`。
- `<border>` 的 `width` 只能取正整数，不支持小数。
- 估算文本框宽度时需要注意大部分字体里的中文、英文、数字不等宽。

**示例**

文本框：

```xml
<shape type="text" topLeftX="80" topLeftY="80" width="800" height="120">
  <content textType="title" fontSize="36">
    <p>主标题</p>
  </content>
</shape>
```

矩形：

```xml
<shape type="rect" topLeftX="120" topLeftY="120" width="240" height="120">
  <fill>
    <fillColor color="rgb(100, 149, 237)"/>
  </fill>
  <border color="rgb(0, 0, 0)" width="2"/>
</shape>
```

圆角矩形：

```xml
<shape type="rect" topLeftX="120" topLeftY="120" width="240" height="120" presetHandlers="12">
  <fill>
    <fillColor color="rgba(37,99,235,1)"/>
  </fill>
</shape>
```

### line

**属性**

- `line` 使用的是 `startX` / `startY` / `endX` / `endY`，不是 `x1` / `y1` / `x2` / `y2`。

**子元素**

- `<border>` 是必需子元素。
- `<startArrow>` / `<endArrow>` 可选，`type` 取 `none` / `arrow` / `empty-triangle` / `solid-triangle` / `empty-diamond` / `solid-diamond` / `empty-circle` / `solid-circle`，**默认 `none`，必须显式写 `type` 才有箭头**（空标签 `<endArrow/>` 画不出箭头）；`widthScale` / `heightScale` 可选，只有 `sm` / `med` / `lg` 三档，`type="none"` 时无效。

**示例**

```xml
<line startX="120" startY="120" endX="420" endY="120">
  <border color="rgb(43, 47, 54)" width="2"/>
</line>
```

### polyline

折线 / 曲线连接符。

**属性**

- 用外接矩形定位（`topLeftX` / `topLeftY` / `width` / `height`），线条默认从矩形左上角连到右下角，用 `flipX` / `flipY` 换走向。
- `type` 可选 `bent-connector2` ~ `bent-connector5`（折线，数字是线段数，默认 `bent-connector2`）和 `curved-connector2` ~ `curved-connector5`（曲线）。
- `presetHandlers` 可调拐点位置。

**子元素**

- `<border>` 是必需子元素。
- `<startArrow>` / `<endArrow>` 可选，参考 `line`。

**注意事项**

- 直线用 `line`（两端点坐标），需要绕行或带弧度的连接用 `polyline`（外接矩形）。

**示例**

```xml
<polyline type="bent-connector3" topLeftX="120" topLeftY="120" width="200" height="120">
  <border color="rgb(43, 47, 54)" width="2"/>
  <endArrow type="arrow"/>
</polyline>
```

### img

**属性**

- `src` 的标准来源是 `slides +media-upload` 返回的 `file_token`（统一两步创建下的做法）；`@<本地路径>` 占位符仅 `+create --slides` 一步法自动上传并替换，而一步法已不作默认路径。**禁止使用 http(s) 外链 URL**——飞书 slides 渲染端不会代理外链图，外链 src 在幻灯片里通常不显示；网图必须先用 `wget` 下载到 CWD 内，再 `+media-upload` 上传。单图最大 20 MB。本地图片详见 [lark-slides-media-upload.md](../cli/lark-slides-media-upload.md) / [lark-slides-create.md](../cli/lark-slides-create.md#本地图片path-占位符)。
- **`width`/`height` 是裁剪后的显示尺寸**。比例和原图不一致时一定会裁剪（无法关闭）：原图等比缩放到刚好铺满 `width`×`height`，再从**中心**裁掉多余部分（水平垂直都居中）。**想完整显示整张图，就让 `width:height` 对齐原图比例**。
- `rotation` 可选，旋转角度（度），取值 `[0, 360)`，默认 `0`，不支持负数。

**子元素**

- **裁剪形状**用可选子元素 `<crop>` 控制，`type` 取 `ShapeType` 枚举值，默认 `rect`。
- **裁剪保留哪一侧**用 `<crop>` 的 `anchor` 控制，取 `top` / `bottom` / `left` / `right`，分别表示保留顶部、底部、左侧、右侧，裁掉对侧多余的部分；**不写就是默认居中裁剪**（没有 `anchor="center"`，想要保持居中裁剪就不要写 `anchor`）。
- `<border>` 可选，描边会跟随裁剪形状。

**注意事项**

- 图片元素是 `<img>`，不是 `<image>`；`img` 使用 `topLeftX` / `topLeftY`，不是 `x` / `y`。
- 本地图片统一走 `+media-upload`：先 `slides +media-upload --file ./pic.png --presentation $PID` 拿 `file_token`，再把 token 写进 `+add-slide` 提交那一页的 `<img src>`；新建和给已有幻灯片加页都一样。
- **圆形头像必须 `width == height`**：`<crop type="ellipse">` 是在 `width`×`height` 外接矩形里画椭圆，宽高不等得到的是椭圆不是正圆。
- `<crop>` 的 `presetHandlers` 与 `<shape>` 同义（px 半径，超出夹紧）；圆形头像加描边直接在 `<img>` 里写 `<border>`。
- **人像图别用默认的居中裁剪**：`width:height` 和原图比例对不上时，居中裁剪会从上下（或左右）各裁掉一半多余部分，人物头顶最容易被切掉。竖构图人像放进横框时写 `<crop anchor="top"/>` 保住头部；最稳的做法仍是让 `width:height` 对齐原图比例，压根不触发裁剪。

**示例**

```xml
<img src="file_token" topLeftX="80" topLeftY="120" width="320" height="180"/>
```

```xml
<!-- 圆形头像：ellipse + width == height -->
<img src="file_token" topLeftX="80" topLeftY="120" width="160" height="160">
  <crop type="ellipse"/>
</img>
<!-- 圆角图片：rect + presetHandlers 半径(px) -->
<img src="file_token" topLeftX="280" topLeftY="120" width="240" height="160">
  <crop type="rect" presetHandlers="16"/>
</img>
<!-- 竖构图人像放进横框：anchor="top" 保住头部，不写会居中裁剪切到头顶 -->
<img src="file_token" topLeftX="560" topLeftY="120" width="240" height="160">
  <crop anchor="top"/>
</img>
```

### icon

**注意事项**

- 图标必须填充**不透明** `fillColor`（`<fill><fillColor color="rgba(R,G,B,1)"/></fill>`，alpha 取 1）并和背景有足够对比。
- 禁止盲猜 iconType，必须先用 `iconpark_tool.py` 检索 IconPark，再写 `<icon iconType="...">`；检索方式和更多规则见 [iconpark.md](iconpark.md)。**禁止使用 emoji（任何位置都不能出现）**，所有语义图标一律用检索到的 IconPark `<icon>`。

**示例**

```xml
<icon iconType="iconpark/Charts/chart-line.svg" topLeftX="80" topLeftY="120" width="32" height="32">
  <fill>
    <fillColor color="rgba(37, 99, 235, 1)"/>
  </fill>
</icon>
```

### table

简单表格可优先用 `rect`+`text` 靠坐标模拟以获得更强的版式控制；需要标准表格结构时才用 `<table>`。

**子元素**

表格结构为：

- `<table>` 直接子元素只有 `<colgroup>` 和 `<tr>`，`width` 和 `height` 分别表示表格的目标总宽度和总高度。
- `<colgroup>` 直接子元素只有 `<col width="...">`，width 定义列宽，默认 110。
- `<tr height="...">` 直接子元素只有 `<td>`，height 定义行高，默认 37。
- `<td>` 直接子元素只有 `<fill>`（背景）、`<content>`（文字）和边框配置（一般不用），不能嵌套 `<shape>`、`<img>`、`<icon>`。

**注意事项**

- 表头默认的白底白字视觉效果极差，必须设置背景和文字颜色，需在首行每个 `<td>` 上加 `<fill>`（配合 `bold` 与对比文字色）与正文行区分。
- 表格里的文字默认是居中对齐，可以设置 `textAlign` 调整对齐方式。
- 表格宽高设置：
  - 已设置的列宽和行高优先保留，未设置的列宽、行高会使用表格的目标总宽度、总高度分配剩余空间
  - **`<table>` 必须设置 `width` 和 `height` 固定整体表格大小，行高列宽建议默认分配，只设置少数必要的 `<col>` 的 `width` 和 `<tr>` 的 `height`。**
- 确实需要显式写 `<tr height="...">` 时，不同字号的行高参考：

| `fontSize` | 内容行数 | 紧凑 `height` | 适中 `height` | 宽松 `height` |
|------|------|------|------|------|
| 10 | 单行 | 16 | 20 | 24 |
| 12 | 单行 | 20 | 24 | 28 |
| 10 | 双行 | 32 | 36 | 42 |
| 12 | 双行 | 36 | 42 | 48 |

**示例**

```xml
<table topLeftX="80" topLeftY="140" width="520" height="52">
  <colgroup>
    <col width="160"/>
    <col width="120"/>
    <col />
  </colgroup>
  <tr height="28">
    <td>
      <fill><fillColor color="rgba(30,60,114,1)"/></fill>
      <content textType="body" fontSize="12" bold="true" color="rgba(255,255,255,1)" textAlign="center"><p>项目</p></content>
    </td>
    <td>
      <fill><fillColor color="rgba(30,60,114,1)"/></fill>
      <content textType="body" fontSize="12" bold="true" color="rgba(255,255,255,1)" textAlign="right"><p>营收</p></content>
    </td>
    <td>
      <fill><fillColor color="rgba(30,60,114,1)"/></fill>
      <content textType="body" fontSize="12" bold="true" color="rgba(255,255,255,1)" textAlign="left"><p>备注说明</p></content>
    </td>
  </tr>
  <tr>
    <td><content textType="body" fontSize="10" textAlign="center"><p>线上业务</p></content></td>
    <td><content textType="body" fontSize="10" textAlign="right"><p>195</p></content></td>
    <td><content textType="body" fontSize="10" textAlign="left"><p>同比增长 8%，主要来自新客</p></content></td>
  </tr>
</table>
```

### chart

图表语法十分复杂，必须阅读 [slides_chart_demo.xml](slides_chart_demo.xml)，直接照抄其中的柱状、条形、折线、面积、饼（环）、雷达、组合图。这些是原生 `<chart>` 支持的类型。

**子元素**

- 必需：`<chartPlotArea>`（绘图区）和 `<chartData>`（数据）。
- 可选：`<chartTitle>`、`<chartSubTitle>`、`<chartStyle>`、`<chartLegend>`、`<chartTooltip>`，如果想不展示标题、副标题、图例或悬浮提示，省略相应元素标签即可。

**注意事项**

- 漏斗、金字塔、象限、矩阵、关系网络图等非原生图表改用 `<shape>`+`<line>` 组合模拟。关系网络图用小圆点（`<shape type="ellipse">`）作节点、旁边配 `<shape type="text">` 标注文字（不要放到节点里），节点之间用 `<line>` 连线。
- 环形图不是独立类型：它就是 `<chartPlot type="pie">` 再给 `<chartSectors>` 设 `innerRadius`（如 `innerRadius="0.55"`）挖空中心得到的——**没有 `type="doughnut"` 或 `donut` 这种类型**，画环图照抄范例里「环形图 · Donut」那页即可。
- 隐藏 `<chart>` 的图例只能通过不写或删除 `<chartLegend>` 实现，`<chartLegend>` 不支持 `position="none"`（`position` 只有 `top` / `bottom` / `left` / `right`）。
- `<chartLabel>`（单数，放 `<chartAxis>` 内）是坐标轴刻度标签；`<chartLabels>`（复数，放 `<chartPlot>` 全局或 `<chartSeries>` 单系列内）是数据标签，在柱 / 点 / 扇区上直接显示数值（常用属性 `position` / `value` / `category` / `percentage` / `format`）。两者别写反。`category` / `value` / `percentage` 至少一项为 `true`（默认仅 `value`）；`format` 用 Excel 数字格式码，如 `0`、`0%`、`#,##0.00`；单位要写进 `format` 时，格式码里的字面文本用双引号包（如 `0"bp"`），但直接写进 XML 属性会和属性外层双引号冲突、破坏 XML，必须改用单引号包属性值 `format='0"bp"'`，或把内层引号转义成 `format="0&quot;bp&quot;"`。
- `<chartLabels>` 的 `position` 按图表类型选：折线 / 散点用 `auto`（别用 `right`，会压线或出框）；柱状用 `top` 或 `inside`；饼 / 环用 `outside`。
- **标注图表上某个关键数据点 / 节点**（如折线的阶段性低点、反弹点），不要用 `<shape type="text">` 浮在绘图区上——文字盒会压到图表区，必触发 `bbox_overlap`。正确做法：优先在图表外的右侧 / 下方文字区用文字描述该节点，或给该系列开 `<chartLabels>` 只显示数值；确需就地标注时给 `<chart>` 预留上 / 下方专用标注带（缩小 chart 高度腾出空间），标注文字放在 chart 边界之外。
- `<chartColorTheme>` 只接受纯色 `<color value="rgb(...)"/>` / `rgba(...)`，**不支持渐变**（`linear-gradient` 等只对 `<shape>` 的 `<fill>` 有效）。想要渐变视觉的柱 / 面，用 `<shape>`+`<fill linear-gradient>` 自绘，或接受纯色。
- 详细用法见 [slides_xml_schema_definition.xml](slides_xml_schema_definition.xml)。

## 颜色与样式

### fill

**示例**

```xml
<fill>
  <fillColor color="rgb(255, 0, 0)"/>
</fill>
```

### border

**属性**

- `dashArray` 可选 `solid`（默认）/ `dash` / `dot` / `long-dash` / `round-dot` 等，完整取值见 schema。

**示例**

```xml
<border color="rgb(43, 47, 54)" width="2" dashArray="solid"/>
```

### 颜色格式

**注意事项**

- 颜色用 `rgb` / `rgba` 格式。
- **渐变色必须使用 `rgba()` 格式并带百分比停靠点**，例如 `linear-gradient(135deg,rgba(30,60,114,1) 0%,rgba(59,130,246,1) 100%)`。使用 `rgb()` 或省略停靠点会导致服务端将其回退为白色。此规则对页面背景和 shape fill 均适用。

**示例**

```xml
<fillColor color="rgb(255, 0, 0)"/>
<fillColor color="rgba(255, 0, 0, 0.5)"/>
<fillColor color="linear-gradient(90deg, rgba(255,0,0,1) 0%, rgba(0,0,255,1) 100%)"/>
<fillColor color="radial-gradient(circle at 50% 50%, rgba(255,0,0,1) 0%, rgba(0,0,255,1) 100%)"/>
```

### 页面背景

**示例**

```xml
<!-- 纯色背景 -->
<slide>
  <style>
    <fill>
      <fillColor color="rgb(245, 245, 245)"/>
    </fill>
  </style>
</slide>

<!-- 渐变背景（必须用 rgba + 百分比停靠点） -->
<slide>
  <style>
    <fill>
      <fillColor color="linear-gradient(135deg,rgba(30,60,114,1) 0%,rgba(59,130,246,1) 100%)"/>
    </fill>
  </style>
</slide>
```

## note 示例

```xml
<note>
  <content textType="body">
    <p>这是演讲者备注，一般写 3-5 句演讲者可以直接使用的讲稿。</p>
  </content>
</note>
```

## 完整示例

```xml
<presentation xmlns="https://www.larkoffice.com/sml/2.0" width="960" height="540">
  <title>季度报告</title>
  <theme>
    <textStyles>
      <title fontFamily="思源宋体" fontSize="54" fontColor="rgba(0, 0, 0, 1)"/>
      <body fontFamily="思源宋体" fontSize="18" fontColor="rgba(43, 47, 54, 1)"/>
    </textStyles>
  </theme>
  <slide>
    <style>
      <fill>
        <fillColor color="rgb(245, 245, 245)"/>
      </fill>
    </style>
    <data>
      <shape type="text" topLeftX="80" topLeftY="72" width="760" height="100">
        <content textType="title" fontSize="36">
          <p>2024 年第一季度报告</p>
        </content>
      </shape>
      <shape type="text" topLeftX="80" topLeftY="200" width="520" height="180">
        <content textType="body" fontSize="16">
          <p>核心指标</p>
          <ul>
            <li><p>用户增长：+25%</p></li>
            <li><p>收入增长：+30%</p></li>
            <li><p>市场份额：15%</p></li>
          </ul>
        </content>
      </shape>
      <shape type="rect" topLeftX="660" topLeftY="180" width="180" height="140">
        <fill>
          <fillColor color="rgba(100, 149, 237, 0.25)"/>
        </fill>
        <border color="rgb(100, 149, 237)" width="2"/>
      </shape>
    </data>
    <note>
      <content textType="body">
        <p>讲到增长率时补充样本范围。</p>
      </content>
    </note>
  </slide>
</presentation>
```

## 详细参考

- [slides_xml_schema_definition.xml](slides_xml_schema_definition.xml)
- [slides_chart_demo.xml](slides_chart_demo.xml)
