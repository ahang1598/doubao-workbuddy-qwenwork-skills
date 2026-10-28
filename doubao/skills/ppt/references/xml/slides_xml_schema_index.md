## `<a>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 超链接元素 属性: href (仅支持 http/https)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `href` | 是 | - | `匿名简单类型` | URI 字符串；格式正则：(https?\|s?ftp\|ftps\|nfs\|ssh)://\S+ 或 [\w.-]+[.:]\S* 或 (mailto:)?\S+@\S+\.\w{2,} |

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<a href="value"/>
```

## `<animation>`

- 声明类型：`匿名 complexType`
- 出现场景：SlideType
- 父元素：`<slide>`

### 高优先级约束

- 页面动画配置, 本期只包含可选的页面切换 transition 省略或空容器都表示"未提供切换配置", 即沿用继承结果, 不等于关闭切换

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`transition`（0..1）]

### 最小可用 XML

```xml
<animation/>
```

## `<background>`

- 声明类型：`FillType`
- 出现场景：ThemeType
- 父元素：`<theme>`

### 高优先级约束

- 填充类型: - color: 颜色填充 (RGB/RGBA格式) - fillImg: 填充图片 - fillPattern: 填充图案 优先级: fillPattern > fillImg > color

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`fillImg` | `fillPattern` | `fillColor`]（0..1）

### 最小可用 XML

```xml
<background/>
```

## `<body>`

- 声明类型：`匿名 complexType`
- 出现场景：TextStylesType
- 父元素：`<textStyles>`
- 中文检索词：字体, 字号, 字体大小

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontFamily` | 否 | 默认 `思源黑体` | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `fontSize` | 否 | 默认 `16` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontColor` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<body/>
```

## `<border>`

- 声明类型：`BorderType`
- 出现场景：<shape>; <line>; <polyline>; <img>; <icon>
- 父元素：`<icon>`, `<img>`, `<line>`, `<polyline>`, `<shape>`
- 中文检索词：边框, 描边, 虚线, 颜色, 宽, 宽度, 边框样式

### 高优先级约束

- 通用边框样式类型 - color: 边框颜色 - width: 边框宽度（像素） - dashArray: 虚线样式 - compound: 复合边框样式 - lineCap: 线端样式 - lineJoin: 线连接样式 - miterLimit: 斜接限制 - rotateWithShape: 是否随形状旋转 注意: 空边框标签表示默认无边框, 默认样式跟随不同的元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dashArray` | 否 | 默认 `solid` | `DashArrayType` | 字符串；枚举：solid \| dash \| dot \| long-dash \| round-dot \| sys-dot \| sys-dash \| dash-dot \| long-dash-dot \| long-dash-dot-dot |
| `compound` | 否 | 默认 `single` | `CompoundType` | 字符串；枚举：single \| double \| thin-thick \| thick-thin \| three |
| `lineCap` | 否 | 默认 `butt` | `LineCapType` | 字符串；枚举：butt \| square \| round |
| `lineJoin` | 否 | 默认 `round` | `LineJoinType` | 字符串；枚举：round \| bevel \| miter |
| `miterLimit` | 否 | 默认 `8` | `nonNegativeInteger` | 非负整数（>= 0） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<border color="rgb(0,0,0)" width="1" dashArray="solid"/>
```

## `<borderBottom>`

- 声明类型：`BorderType`
- 出现场景：<td>
- 父元素：`<td>`
- 中文检索词：颜色, 宽, 宽度, 虚线, 边框样式

### 高优先级约束

- 通用边框样式类型 - color: 边框颜色 - width: 边框宽度（像素） - dashArray: 虚线样式 - compound: 复合边框样式 - lineCap: 线端样式 - lineJoin: 线连接样式 - miterLimit: 斜接限制 - rotateWithShape: 是否随形状旋转 注意: 空边框标签表示默认无边框, 默认样式跟随不同的元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dashArray` | 否 | 默认 `solid` | `DashArrayType` | 字符串；枚举：solid \| dash \| dot \| long-dash \| round-dot \| sys-dot \| sys-dash \| dash-dot \| long-dash-dot \| long-dash-dot-dot |
| `compound` | 否 | 默认 `single` | `CompoundType` | 字符串；枚举：single \| double \| thin-thick \| thick-thin \| three |
| `lineCap` | 否 | 默认 `butt` | `LineCapType` | 字符串；枚举：butt \| square \| round |
| `lineJoin` | 否 | 默认 `round` | `LineJoinType` | 字符串；枚举：round \| bevel \| miter |
| `miterLimit` | 否 | 默认 `8` | `nonNegativeInteger` | 非负整数（>= 0） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<borderBottom/>
```

## `<borderLeft>`

- 声明类型：`BorderType`
- 出现场景：<td>
- 父元素：`<td>`
- 中文检索词：颜色, 宽, 宽度, 虚线, 边框样式

### 高优先级约束

- 通用边框样式类型 - color: 边框颜色 - width: 边框宽度（像素） - dashArray: 虚线样式 - compound: 复合边框样式 - lineCap: 线端样式 - lineJoin: 线连接样式 - miterLimit: 斜接限制 - rotateWithShape: 是否随形状旋转 注意: 空边框标签表示默认无边框, 默认样式跟随不同的元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dashArray` | 否 | 默认 `solid` | `DashArrayType` | 字符串；枚举：solid \| dash \| dot \| long-dash \| round-dot \| sys-dot \| sys-dash \| dash-dot \| long-dash-dot \| long-dash-dot-dot |
| `compound` | 否 | 默认 `single` | `CompoundType` | 字符串；枚举：single \| double \| thin-thick \| thick-thin \| three |
| `lineCap` | 否 | 默认 `butt` | `LineCapType` | 字符串；枚举：butt \| square \| round |
| `lineJoin` | 否 | 默认 `round` | `LineJoinType` | 字符串；枚举：round \| bevel \| miter |
| `miterLimit` | 否 | 默认 `8` | `nonNegativeInteger` | 非负整数（>= 0） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<borderLeft/>
```

## `<borderRight>`

- 声明类型：`BorderType`
- 出现场景：<td>
- 父元素：`<td>`
- 中文检索词：颜色, 宽, 宽度, 虚线, 边框样式

### 高优先级约束

- 通用边框样式类型 - color: 边框颜色 - width: 边框宽度（像素） - dashArray: 虚线样式 - compound: 复合边框样式 - lineCap: 线端样式 - lineJoin: 线连接样式 - miterLimit: 斜接限制 - rotateWithShape: 是否随形状旋转 注意: 空边框标签表示默认无边框, 默认样式跟随不同的元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dashArray` | 否 | 默认 `solid` | `DashArrayType` | 字符串；枚举：solid \| dash \| dot \| long-dash \| round-dot \| sys-dot \| sys-dash \| dash-dot \| long-dash-dot \| long-dash-dot-dot |
| `compound` | 否 | 默认 `single` | `CompoundType` | 字符串；枚举：single \| double \| thin-thick \| thick-thin \| three |
| `lineCap` | 否 | 默认 `butt` | `LineCapType` | 字符串；枚举：butt \| square \| round |
| `lineJoin` | 否 | 默认 `round` | `LineJoinType` | 字符串；枚举：round \| bevel \| miter |
| `miterLimit` | 否 | 默认 `8` | `nonNegativeInteger` | 非负整数（>= 0） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<borderRight/>
```

## `<borderTop>`

- 声明类型：`BorderType`
- 出现场景：<td>
- 父元素：`<td>`
- 中文检索词：颜色, 宽, 宽度, 虚线, 边框样式

### 高优先级约束

- 通用边框样式类型 - color: 边框颜色 - width: 边框宽度（像素） - dashArray: 虚线样式 - compound: 复合边框样式 - lineCap: 线端样式 - lineJoin: 线连接样式 - miterLimit: 斜接限制 - rotateWithShape: 是否随形状旋转 注意: 空边框标签表示默认无边框, 默认样式跟随不同的元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dashArray` | 否 | 默认 `solid` | `DashArrayType` | 字符串；枚举：solid \| dash \| dot \| long-dash \| round-dot \| sys-dot \| sys-dash \| dash-dot \| long-dash-dot \| long-dash-dot-dot |
| `compound` | 否 | 默认 `single` | `CompoundType` | 字符串；枚举：single \| double \| thin-thick \| thick-thin \| three |
| `lineCap` | 否 | 默认 `butt` | `LineCapType` | 字符串；枚举：butt \| square \| round |
| `lineJoin` | 否 | 默认 `round` | `LineJoinType` | 字符串；枚举：round \| bevel \| miter |
| `miterLimit` | 否 | 默认 `8` | `nonNegativeInteger` | 非负整数（>= 0） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<borderTop/>
```

## `<br>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 换行符, 强制换行, 以形式出现

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<br/>
```

## `<caption>`

- 声明类型：`匿名 complexType`
- 出现场景：TextStylesType
- 父元素：`<textStyles>`
- 中文检索词：字体, 字号, 字体大小

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontFamily` | 否 | 默认 `思源黑体` | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `fontSize` | 否 | 默认 `12` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontColor` | 否 | 默认 `rgba(128, 128, 128, 1)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<caption/>
```

## `<chart>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：图表, 原生图表, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- 图表元素, 用于展示数据可视化 属性: - id: 图表元素ID (可选) - topLeftX: 左上角X坐标 [-8640,10560] - topLeftY: 左上角Y坐标 [-4860,5940] - width: 图表宽度 - height: 图表高度 - rotation: 旋转角度 [0,360), 默认0 - flipX: 水平翻转, 默认false - flipY: 垂直翻转, 默认false - alpha: 透明度 [0,1], 默认1 - ooxml: 是否按 Office OOXML 导入图语义渲染整张图表 子元素: - chartTitle: 标题设置 (可选) - chartSubTitle: 副标题设置 (可选) - chartStyle: 图表样式 (可选) - chartPlotArea: 绘图区配置 (必需) - chartData: 数据容器 (必需) - chartLegend: 图例配置(可选) - chartTooltip: Tooltip 配置(可选) - reflection: 倒影效果 (可选) - shadow: 外阴影效果 (可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |
| `ooxml` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

任意顺序各一次[`chartTitle`（0..1），`chartSubTitle`（0..1），`chartStyle`（0..1），`chartLegend`（0..1），`chartTooltip`（0..1），`chartPlotArea`，`chartData`，`reflection`（0..1），`shadow`（0..1）]

### 最小可用 XML

```xml
<chart topLeftX="0" topLeftY="0" width="320" height="180">
  <chartPlotArea><chartPlot type="pie"/></chartPlotArea>
  <chartData>
    <dim1><chartField name="category" valueType="string">A,B</chartField></dim1>
    <dim2><chartField name="series" valueType="number">1,2</chartField></dim2>
  </chartData>
</chart>
```

## `<chartArea>`

- 声明类型：`ChartSeriesAreaType`
- 出现场景：ChartSeriesType
- 父元素：`<chartSeries>`
- 中文检索词：颜色

### 高优先级约束

- 图表系列面积配置（第二层：单系列统一配置） 继承ChartGlobalAreaType的所有属性 子元素: - fillGradient: 该系列面积填充渐变(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1）]

### 最小可用 XML

```xml
<chartArea/>
```

## `<chartAreas>`

- 声明类型：`ChartGlobalAreaType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`
- 中文检索词：颜色

### 高优先级约束

- 图表全局面积配置（第一层：所有系列的默认填充样式） 适用于: 面积图、组合图的面积部分, 雷达图的填充部分 属性: - color: 填充颜色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartAreas/>
```

## `<chartAxes>`

- 声明类型：`ChartAxesType`
- 出现场景：ChartPlotAreaType
- 父元素：`<chartPlotArea>`

### 高优先级约束

- 图表坐标轴容器 子元素: - chartAxis: 坐标轴配置, 可包含多个坐标轴, 建议至少包含 2 个坐标轴配置 柱状图、条形图、折线图、面积图、组合图: X 轴、Y 轴（可双轴） 雷达图: 角度轴、半径轴

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`chartAxis`（1..unbounded）]

### 最小可用 XML

```xml
<chartAxes><chartAxis type="x"/></chartAxes>
```

## `<chartAxis>`

- 声明类型：`ChartAxisType`
- 出现场景：ChartAxesType
- 父元素：`<chartAxes>`

### 高优先级约束

- 图表单个坐标轴配置 属性: - type: 坐标轴类型(必需) * 直角坐标系: x(横轴)、y(纵轴) * 极坐标系: angle(角度轴)、radius(半径轴) - position: 坐标轴位置(可选)(left|right), 仅对y轴有效 - max: 坐标轴最大值(不设置时自动计算) - min: 坐标轴最小值(不设置时自动计算) - orientation: minMax(正序)|maxMin(逆序)，与旧 reverse 语义不同 - crosses: autoZero(自动零点)|min(最小端)|max(最大端) - domainColor/domainWidth: 轴线颜色/非负宽度 - domainDash: 空白分隔的轴线虚线列表 子元素: - chartTitle: 坐标轴标题(可选) - chartLabel: 坐标轴刻度标签格式(可选) - chartAxisLine: 坐标轴线配置(可选), 未设置时不显示轴线 - chartGridLine: 网格线配置(可选), 未设置时不显示网格线 - chartMinorGridLine: 次网格线配置(可选)，支持 color/width/dash - chartDomainGradient: 轴线渐变(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartAxisKindType` | 图表坐标轴类型 可选值: x \| y \| angle \| radius；字符串；枚举：x \| y \| angle \| radius |
| `position` | 否 | - | `ChartYAxisPositionType` | 图表Y轴位置枚举 可选值: left(左侧) \| right(右侧)；字符串；枚举：left \| right |
| `max` | 否 | - | `integer` | 整数 |
| `min` | 否 | - | `integer` | 整数 |
| `orientation` | 否 | - | `匿名简单类型` | 字符串；枚举：minMax \| maxMin |
| `crosses` | 否 | - | `匿名简单类型` | 字符串；枚举：autoZero \| min \| max |
| `domainColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `domainWidth` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `domainDash` | 否 | - | `ChartDashType` | 空白分隔的非负数列表（像素），如 "8 3 2 3"；空字符串表示实线。；空格分隔列表，单项类型：NonNegativeDouble（浮点数；限制：>= 0.0） |

### 子元素（内容模型）

任意顺序各一次[`chartTitle`（0..1），`chartLabel`（0..1），`chartAxisLine`（0..1），`chartGridLine`（0..1），`chartMinorGridLine`（0..1），`chartDomainGradient`（0..1）]

### 最小可用 XML

```xml
<chartAxis type="x"/>
```

## `<chartAxisLine>`

- 声明类型：`ChartAxisLineType`
- 出现场景：ChartAxisType
- 父元素：`<chartAxis>`

### 高优先级约束

- 图表坐标轴线配置（空标签即显示轴线） 无属性 无子元素

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartAxisLine/>
```

## `<chartBackground>`

- 声明类型：`ChartBackgroundType`
- 出现场景：ChartStyleType
- 父元素：`<chartStyle>`
- 中文检索词：颜色

### 高优先级约束

- 图表背景配置 属性: - color: 背景颜色，省略时使用图表默认背景；无填充可使用透明色 rgba(0,0,0,0)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartBackground/>
```

## `<chartBackgroundGradient>`

- 声明类型：`ChartGradientType`
- 出现场景：ChartRegionType; ChartStyleType
- 父元素：`<chartRegion>`, `<chartStyle>`

### 高优先级约束

- 图表渐变配置 属性: - type: 渐变类型(linear|radial) - x0/y0/x1/y1: 线性渐变起止点坐标 - r0/r1: 径向渐变半径 - gradientMethod: 渐变算法/插值方式 子元素: - stops: 渐变色标列表

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |
| `x0` | 否 | - | `double` | 浮点数 |
| `y0` | 否 | - | `double` | 浮点数 |
| `x1` | 否 | - | `double` | 浮点数 |
| `y1` | 否 | - | `double` | 浮点数 |
| `r0` | 否 | - | `double` | 浮点数 |
| `r1` | 否 | - | `double` | 浮点数 |
| `gradientMethod` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`stops`]

### 最小可用 XML

```xml
<chartBackgroundGradient type="linear"><stops><stop offset="value" color="rgb(0,0,0)"/></stops></chartBackgroundGradient>
```

## `<chartBar>`

- 声明类型：`匿名 complexType`
- 出现场景：ChartSeriesBarsType
- 父元素：`<chartBars>`
- 中文检索词：颜色

### 高优先级约束

- 单个柱子配置（第三层：最高优先级） 属性: - index: 柱子索引(从1开始, 必需), 表示该系列中第几个柱子 - color: 该柱子的填充颜色 - borderColor: 该柱子的边框颜色 - borderWidth: 该柱子的边框宽度(像素) - borderStyle: 该柱子的边框样式(solid|dashed|dotted) 子元素: - fillGradient: 该柱子的填充渐变(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 是 | - | `positiveInteger` | 正整数（> 0） |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderWidth` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `borderStyle` | 否 | - | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1）]

### 最小可用 XML

```xml
<chartBar index="1"/>
```

## `<chartBars>`

- 声明类型：`ChartGlobalBarsType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`, `<chartSeries>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 图表全局柱子配置（第一层：所有系列的默认柱子样式） 适用于: 柱状图、条形图、组合图的柱状部分、帕累托图数值柱 属性: - color: 柱子填充颜色 - borderColor: 柱子边框颜色 - borderWidth: 柱子边框宽度(像素), 默认0 - borderStyle: 柱子边框样式(solid|dashed|dotted), 默认solid - backgroundColor: 柱子背景颜色 - width: 柱子宽度(像素), 未设置时自动计算 - overlap: OOXML 系列重叠率[-100,100] - gapWidth: OOXML 柱间距百分比[0,500]，不是像素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderWidth` | 否 | 默认 `0` | `nonNegativeInteger` | 非负整数（>= 0） |
| `borderStyle` | 否 | 默认 `solid` | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |
| `backgroundColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `overlap` | 否 | - | `匿名简单类型` | 浮点数；限制：>= -100，<= 100 |
| `gapWidth` | 否 | - | `匿名简单类型` | 浮点数；限制：>= 0，<= 500 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartBars/>
```

## `<chartBars>`

- 声明类型：`ChartSeriesBarsType`
- 出现场景：ChartSeriesType
- 父元素：`<chartPlot>`, `<chartSeries>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 图表系列柱子配置（第二层：单系列统一配置 + 单柱精确定制） 继承ChartGlobalBarsType的所有属性；普通柱状/条形/组合图系列不建议设置backgroundColor、width 适用于: 柱状图、条形图、组合图的柱状部分、帕累托图数值柱 属性: - color: 该系列所有柱子的填充颜色 - borderColor: 该系列所有柱子的边框颜色 - borderWidth: 该系列所有柱子的边框宽度 - borderStyle: 该系列所有柱子的边框样式 子元素: - fillGradient: 该系列所有柱子的填充渐变(可选) - strokeGradient: 该系列所有柱子的边框渐变(可选) - chartBar: 单个柱子配置(可选, 多个), 用于覆盖特定柱子的样式

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderWidth` | 否 | 默认 `0` | `nonNegativeInteger` | 非负整数（>= 0） |
| `borderStyle` | 否 | 默认 `solid` | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |
| `backgroundColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `overlap` | 否 | - | `匿名简单类型` | 浮点数；限制：>= -100，<= 100 |
| `gapWidth` | 否 | - | `匿名简单类型` | 浮点数；限制：>= 0，<= 500 |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1），`strokeGradient`（0..1），`chartBar`（0..unbounded）]

### 最小可用 XML

```xml
<chartBars/>
```

## `<chartBorder>`

- 声明类型：`ChartBorderType`
- 出现场景：ChartMainTitleType; ChartRegionType; ChartStyleType
- 父元素：`<chartRegion>`, `<chartStyle>`, `<chartTitle>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 图表边框配置 属性: - color: 边框颜色，默认 rgb(222, 224, 227) - width: 边框宽度(像素), 默认 1；无边框可设置为0，或不设置chartBorder - style: 边框样式(solid|dashed|dotted), 默认 solid - radius: 圆角半径(像素), 默认 6 - dash: OOXML 原始虚线列表，空白分隔；设置时优先于 style 子元素: chartGradient 为边框渐变

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | 默认 `1` | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `style` | 否 | 默认 `solid` | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |
| `radius` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `dash` | 否 | - | `ChartDashType` | 空白分隔的非负数列表（像素），如 "8 3 2 3"；空字符串表示实线。；空格分隔列表，单项类型：NonNegativeDouble（浮点数；限制：>= 0.0） |

### 子元素（内容模型）

任意顺序各一次[`chartGradient`（0..1）]

### 最小可用 XML

```xml
<chartBorder/>
```

## `<chartBubble>`

- 声明类型：`ChartBubbleType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 气泡图专用配置 属性: - aggregate: 是否聚合相同维度的数据 - showNegativeSize: 是否显示大小为负数的气泡, 默认false - opacityGradientStyle: 气泡透明度渐变方式(linear|radial) 子元素: - chartIdLabel: 气泡标识标签及字体样式(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `aggregate` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `showNegativeSize` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `opacityGradientStyle` | 否 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |

### 子元素（内容模型）

任意顺序各一次[`chartIdLabel`（0..1）]

### 最小可用 XML

```xml
<chartBubble/>
```

## `<chartColorGradient>`

- 声明类型：`ChartColorGradientType`
- 出现场景：ChartStyleType
- 父元素：`<chartStyle>`

### 高优先级约束

- 图表渐变填充开关（空标签即启用渐变效果） 无属性 无子元素

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartColorGradient/>
```

## `<chartColorTheme>`

- 声明类型：`ChartColorThemeType`
- 出现场景：ChartStyleType
- 父元素：`<chartStyle>`

### 高优先级约束

- 图表配色主题（定义系列颜色序列, 按系列索引循环应用） 属性: - themeId: 主题标识（可选），主要用于兼容线上图表导出，AI生成不使用主题标识 子元素: - color: 主题颜色项(建议至少1个), 每个color定义一个系列的颜色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `themeId` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`color`（0..unbounded）]

### 最小可用 XML

```xml
<chartColorTheme/>
```

## `<chartConnectorLine>`

- 声明类型：`ChartWaterfallConnectorLineType`
- 出现场景：ChartWaterfallType
- 父元素：`<chartWaterfall>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 瀑布图柱体连接线样式 属性: - color: 连接线颜色 - width: 非负线宽(像素) - style: 线条样式(solid|dashed|dotted) - opacity: 线条透明度[0,1]

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `style` | 否 | - | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |
| `opacity` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartConnectorLine/>
```

## `<chartData>`

- 声明类型：`ChartDataType`
- 出现场景：<chart>
- 父元素：`<chart>`

### 高优先级约束

- 图表数据容器（采用二维数据模型） 数据组织方式: dim1中每个值对应dim2中所有系列的同一位置数据 例如: dim1的第2个值对应dim2中所有系列的第2个值 子元素: - dim1: 分类维度(必需), 定义数据点的位置 - dim2: 数值维度(必需), 定义数据系列

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`dim1`，`dim2`]

### 最小可用 XML

```xml
<chartData><dim1><chartField name="value"/></dim1><dim2><chartField name="value"/></dim2></chartData>
```

## `<chartDomainGradient>`

- 声明类型：`ChartGradientType`
- 出现场景：ChartAxisType
- 父元素：`<chartAxis>`

### 高优先级约束

- 图表渐变配置 属性: - type: 渐变类型(linear|radial) - x0/y0/x1/y1: 线性渐变起止点坐标 - r0/r1: 径向渐变半径 - gradientMethod: 渐变算法/插值方式 子元素: - stops: 渐变色标列表

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |
| `x0` | 否 | - | `double` | 浮点数 |
| `y0` | 否 | - | `double` | 浮点数 |
| `x1` | 否 | - | `double` | 浮点数 |
| `y1` | 否 | - | `double` | 浮点数 |
| `r0` | 否 | - | `double` | 浮点数 |
| `r1` | 否 | - | `double` | 浮点数 |
| `gradientMethod` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`stops`]

### 最小可用 XML

```xml
<chartDomainGradient type="linear"><stops><stop offset="value" color="rgb(0,0,0)"/></stops></chartDomainGradient>
```

## `<chartExtra>`

- 声明类型：`ChartExtraType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`

### 高优先级约束

- 图表额外配置 - chartRadar: 雷达图特有配置(可选), 仅雷达图使用 - chartSmooth: 平滑折线开关(可选), 适用于折线/面积/雷达/组合图 - chartStep: 阶梯折线开关(可选), 适用于折线/面积/组合图 - chartStack: 堆叠设置(可选), 适用于面积/条形/柱状/组合图 - chartBubble: 气泡图专用配置(可选), 仅气泡图使用 - chartWaterfall: 瀑布图全局配置(可选), 仅瀑布图使用 - chartPareto: 帕累托图专用配置(可选), 仅帕累托图使用

### 完整可用属性

无属性。

### 子元素（内容模型）

任意顺序各一次[`chartRadar`（0..1），`chartSmooth`（0..1），`chartStep`（0..1），`chartStack`（0..1），`chartBubble`（0..1），`chartWaterfall`（0..1），`chartPareto`（0..1）]

### 最小可用 XML

```xml
<chartExtra/>
```

## `<chartField>`

- 声明类型：`ChartDataDim2FieldType`
- 出现场景：ChartDataDim2Type
- 父元素：`<dim1>`, `<dim2>`

### 高优先级约束

- 图表第二维度字段 继承通用图表数据字段；role 仅用于气泡图，标识x、y、group、size字段角色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `name` | 是 | - | `string` | 字符串 |
| `valueType` | 否 | - | `ChartValueType` | 字符串；枚举：number \| string |
| `role` | 否 | - | `匿名简单类型` | 字符串；枚举：x \| y \| group \| size |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartField name="value"/>
```

## `<chartField>`

- 声明类型：`ChartDataFieldType`
- 出现场景：ChartDataDim1Type
- 父元素：`<dim1>`, `<dim2>`

### 高优先级约束

- 图表数据字段定义 属性: - name: 字段名称(必需), 列标题或系列名称 - valueType: 数据值类型(string|number) 内容: CSV格式的数据值（逗号分隔） - 用逗号 ', ' 分割值, 禁止传入 array - 当 valueType="string" 时, 若字符串包含逗号需用双引号包裹, 如："a, b", c, d - 当 valueType="number" 时, 直接用逗号分割数字, 如：1, 2, 3.5

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `name` | 是 | - | `string` | 字符串 |
| `valueType` | 否 | - | `ChartValueType` | 字符串；枚举：number \| string |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartField name="value"/>
```

## `<chartFont>`

- 声明类型：`ChartGlobalFontType`
- 出现场景：ChartStyleType
- 父元素：`<chartStyle>`
- 中文检索词：颜色

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `size` | 否 | 默认 `12` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartFont/>
```

## `<chartGradient>`

- 声明类型：`ChartGradientType`
- 出现场景：ChartBorderType
- 父元素：`<chartBorder>`

### 高优先级约束

- 图表渐变配置 属性: - type: 渐变类型(linear|radial) - x0/y0/x1/y1: 线性渐变起止点坐标 - r0/r1: 径向渐变半径 - gradientMethod: 渐变算法/插值方式 子元素: - stops: 渐变色标列表

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |
| `x0` | 否 | - | `double` | 浮点数 |
| `y0` | 否 | - | `double` | 浮点数 |
| `x1` | 否 | - | `double` | 浮点数 |
| `y1` | 否 | - | `double` | 浮点数 |
| `r0` | 否 | - | `double` | 浮点数 |
| `r1` | 否 | - | `double` | 浮点数 |
| `gradientMethod` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`stops`]

### 最小可用 XML

```xml
<chartGradient type="linear"><stops><stop offset="value" color="rgb(0,0,0)"/></stops></chartGradient>
```

## `<chartGridLine>`

- 声明类型：`ChartGridLineType`
- 出现场景：ChartAxisType
- 父元素：`<chartAxis>`
- 中文检索词：宽, 宽度, 颜色

### 高优先级约束

- 图表网格线配置 属性: - width: 网格线宽度(像素) - color: 网格线颜色 - dash: 空白分隔的非负虚线列表，支持小数

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `width` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `dash` | 否 | - | `ChartDashType` | 空白分隔的非负数列表（像素），如 "8 3 2 3"；空字符串表示实线。；空格分隔列表，单项类型：NonNegativeDouble（浮点数；限制：>= 0.0） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartGridLine/>
```

## `<chartIdLabel>`

- 声明类型：`ChartFontStyleType`
- 出现场景：ChartBubbleType
- 父元素：`<chartBubble>`
- 中文检索词：字号, 字体大小, 颜色

### 高优先级约束

- 图表字体样式基类（所有文本元素的基础配置） 属性: - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartIdLabel/>
```

## `<chartInvertIfNegative>`

- 声明类型：`ChartInvertIfNegativeType`
- 出现场景：ChartSeriesType
- 父元素：`<chartSeries>`
- 中文检索词：颜色

### 高优先级约束

- 负值反色配置：enable 控制开关，color 指定反色填充；省略 color 时使用 Office 缺省反色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `enable` | 是 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartInvertIfNegative enable="true"/>
```

## `<chartLabel>`

- 声明类型：`ChartAxisLabelType`
- 出现场景：ChartAxisType
- 父元素：`<chartAxis>`
- 中文检索词：字号, 字体大小, 颜色

### 高优先级约束

- 图表坐标轴标签配置 属性: - angle: 标签旋转角度(-90|-45|0|45|90), 用于避免标签重叠, 不设置时自动计算 - format: 数字格式代码，例如 0%、0.00%、0.00、#,##0.00、¥#,##0.00, 0万 - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `angle` | 否 | - | `ChartAxisLabelAngleType` | 坐标轴标签旋转角度枚举 可选值: -90 \| -45 \| 0 \| 45 \| 90 (单位：度)；整数；枚举：-90 \| -45 \| 0 \| 45 \| 90 |
| `format` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartLabel/>
```

## `<chartLabels>`

- 声明类型：`ChartDataLabelsType`
- 出现场景：<chartPoint>; ChartSeriesType; ChartPlotType
- 父元素：`<chartPlot>`, `<chartPoint>`, `<chartSeries>`
- 中文检索词：字号, 字体大小, 颜色

### 高优先级约束

- 图表数据标签配置 属性: - position: 标签位置(auto|top|bottom|left|right|center|inside|outside), 默认auto - series: 是否显示系列名称, 默认false, 条形图和柱状图下生效 - category: 是否显示分类名称, 默认false - value: 是否显示数值, 默认true - percentage: 是否显示百分比, 默认false - format: 数字格式代码，例如 0%、0.00%、0.00、#,##0.00、¥#,##0.00, 0万 - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色 - separator: 标签要素之间的分隔符；换行使用 &#10;，保留首尾空白 - legendKey: 是否显示系列图例色块 - showGuidLine: 是否显示标签引导线（沿用快照字段拼写） 注意: category、value、percentage至少有一项为true

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `position` | 否 | - | `ChartDataLabelPositionType` | 数据标签位置 - pie: outside \| inside，默认值 outside - column/bar: outside(柱外部) \| center(柱内中间) \| top(柱内顶部) \| bottom(柱内底部)，默认值 outside - line/area/radar: 默认值 auto，且建议只设置 auto；字符串；枚举：auto \| top \| bottom \| left \| right \| center \| inside \| outside |
| `series` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `category` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `value` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |
| `percentage` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `separator` | 否 | - | `string` | 字符串 |
| `legendKey` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `showGuidLine` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `format` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartLabels/>
```

## `<chartLayout>`

- 声明类型：`ChartTitleLayoutType`
- 出现场景：ChartMainTitleType
- 父元素：`<chartTitle>`

### 高优先级约束

- OOXML 主标题手动定位，x/y 是 [0,1] 比例；仅支持 edge 模式。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `xMode` | 否 | - | `匿名简单类型` | 字符串；枚举：edge |
| `x` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `yMode` | 否 | - | `匿名简单类型` | 字符串；枚举：edge |
| `y` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartLayout/>
```

## `<chartLegend>`

- 声明类型：`ChartLegendType`
- 出现场景：<chart>
- 父元素：`<chart>`
- 中文检索词：字号, 字体大小, 颜色

### 高优先级约束

- 图表图例配置 属性: - position: 图例位置(top|bottom|left|right), 默认bottom - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `position` | 否 | 默认 `bottom` | `ChartLegendPositionType` | 图表图例位置枚举 可选值: top(顶部) \| bottom(底部) \| left(左侧) \| right(右侧)；字符串；枚举：top \| bottom \| left \| right |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartLegend/>
```

## `<chartLine>`

- 声明类型：`ChartSeriesLineType`
- 出现场景：ChartSeriesType
- 父元素：`<chartSeries>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 图表系列线条配置（第二层：单系列统一配置） 继承ChartGlobalLineType的所有属性 子元素: - strokeGradient: 该系列线条渐变(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | 默认 `2` | `positiveInteger` | 正整数（> 0） |
| `style` | 否 | 默认 `solid` | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |

### 子元素（内容模型）

按顺序[`strokeGradient`（0..1）]

### 最小可用 XML

```xml
<chartLine/>
```

## `<chartLines>`

- 声明类型：`ChartGlobalLineType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 图表全局线条配置（第一层：所有系列的默认样式） 适用于: 折线图、面积图、组合图的折线部分、帕累托图累计百分比线 属性: - color: 线条颜色 - width: 线条宽度(像素), 默认2 - style: 线条样式(solid|dashed|dotted), 默认solid

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | 默认 `2` | `positiveInteger` | 正整数（> 0） |
| `style` | 否 | 默认 `solid` | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartLines/>
```

## `<chartMinorGridLine>`

- 声明类型：`ChartGridLineType`
- 出现场景：ChartAxisType
- 父元素：`<chartAxis>`
- 中文检索词：宽, 宽度, 颜色

### 高优先级约束

- 图表网格线配置 属性: - width: 网格线宽度(像素) - color: 网格线颜色 - dash: 空白分隔的非负虚线列表，支持小数

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `width` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `dash` | 否 | - | `ChartDashType` | 空白分隔的非负数列表（像素），如 "8 3 2 3"；空字符串表示实线。；空格分隔列表，单项类型：NonNegativeDouble（浮点数；限制：>= 0.0） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartMinorGridLine/>
```

## `<chartNegativeStyle>`

- 声明类型：`ChartWaterfallSeriesStyleType`
- 出现场景：ChartWaterfallSeriesConfigType; ChartWaterfallType
- 父元素：`<chartWaterfall>`
- 中文检索词：颜色

### 高优先级约束

- 瀑布图负值或汇总柱样式 属性: - color: 填充颜色 - opacity: 填充透明度[0,1] - borderColor: 边框颜色 - borderWidth: 非负边框宽度(像素) - borderStyle: 边框样式(solid|dashed|dotted)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `opacity` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderWidth` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `borderStyle` | 否 | - | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartNegativeStyle/>
```

## `<chartPareto>`

- 声明类型：`ChartParetoType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 帕累托图专用配置 属性: - aggregateType: 数值聚合方式, 默认sum - categoryNumber: 展示的正整数分类数量 系列样式复用 chartSeries: index=1 配置数值柱的 chartBars/chartLabels， index=2 配置累计百分比线的 chartLine/chartPoints/chartLabels

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `aggregateType` | 否 | 默认 `sum` | `匿名简单类型` | 字符串；枚举：sum \| average \| count \| counta \| min \| max \| median |
| `categoryNumber` | 否 | - | `positiveInteger` | 正整数（> 0） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartPareto/>
```

## `<chartPlot>`

- 声明类型：`ChartPlotType`
- 出现场景：ChartPlotAreaType
- 父元素：`<chartPlotArea>`

### 高优先级约束

- 图表绘图区配置（定义图表类型和数据坐标体系） 属性: - type: 图表类型(必需) * line(折线图) | area(面积图) | bar(条形图) | column(柱状图) * pie(饼图) | radar(雷达图) | combo(组合图) * bubble(气泡图) | waterfall(瀑布图) | pareto(帕累托图) - comboType: 组合图系列类型(可选), 仅组合图使用 - yAxisPosition: 右Y轴位置(可选), 只有在笛卡尔坐标系下, 默认值 left, 其他坐标系图表如饼图, 没有 yAxisPosition 子元素: - chartPoints: 全局数据点样式配置(可选) - chartLines: 全局线条样式配置(可选) - chartAreas: 全局面积样式配置(可选) - chartBars: 全局柱子样式配置(可选) - chartLabels: 全局数据标签配置(可选) - chartSeriesList: 系列列表配置(可选), 用于单独配置每个系列 - chartExtra: 额外配置(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartType` | 字符串；枚举：pie \| column \| bar \| line \| area \| radar \| combo \| bubble \| waterfall \| pareto |
| `comboType` | 否 | - | `ChartComboSeriesType` | 组合图系列类型枚举 可选值: column(柱状) \| line(折线) \| area(面积) \| scatter(散点)；字符串；枚举：column \| line \| area \| scatter |
| `yAxisPosition` | 否 | 默认 `left` | `ChartYAxisPositionType` | 图表Y轴位置枚举 可选值: left(左侧) \| right(右侧)；字符串；枚举：left \| right |

### 子元素（内容模型）

任意顺序各一次[`chartPoints`（0..1），`chartLines`（0..1），`chartAreas`（0..1），`chartBars`（0..1），`chartLabels`（0..1），`chartSeriesList`（0..1），`chartExtra`（0..1）]

### 最小可用 XML

```xml
<chartPlot type="pie"/>
```

## `<chartPlotArea>`

- 声明类型：`ChartPlotAreaType`
- 出现场景：<chart>
- 父元素：`<chart>`

### 高优先级约束

- 图表绘图区配置（定义图表类型和数据坐标体系）

### 完整可用属性

无属性。

### 子元素（内容模型）

任意顺序各一次[`chartPlot`，`chartAxes`（0..1）]

### 最小可用 XML

```xml
<chartPlotArea><chartPlot type="pie"/></chartPlotArea>
```

## `<chartPoint>`

- 声明类型：`匿名 complexType`
- 出现场景：ChartSeriesPointsType
- 父元素：`<chartPoints>`
- 中文检索词：颜色

### 高优先级约束

- 单个数据点配置（第三层：最高优先级） 属性: - index: 数据点索引(从1开始, 必需), 表示该系列中第几个数据点 - color: 该点的颜色 - shape: 该点的形状(circle|square|triangle|diamond|rect) - size: 该点的大小(像素) 子元素: - fillGradient: 该点填充渐变(可选) - chartLabels: 单点标签覆盖，支持 separator/legendKey/showGuidLine

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 是 | - | `positiveInteger` | 正整数（> 0） |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `shape` | 否 | - | `ChartPointShapeType` | 图表数据点形状枚举 可选值: circle(圆形) \| square(正方形) \| triangle(三角形) \| diamond(菱形) \| rect(矩形)；字符串；枚举：circle \| square \| triangle \| diamond \| rect |
| `size` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1），`chartLabels`（0..1）]

### 最小可用 XML

```xml
<chartPoint index="1"/>
```

## `<chartPoints>`

- 声明类型：`ChartGlobalPointsType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`, `<chartSeries>`
- 中文检索词：颜色

### 高优先级约束

- 图表全局数据点配置（第一层：所有系列的默认样式） 适用于: 折线图、散点图、气泡图 属性: - color: 数据点颜色 - shape: 数据点形状(circle|square|triangle|diamond|rect), 默认circle - size: 数据点大小(像素)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `shape` | 否 | 默认 `circle` | `ChartPointShapeType` | 图表数据点形状枚举 可选值: circle(圆形) \| square(正方形) \| triangle(三角形) \| diamond(菱形) \| rect(矩形)；字符串；枚举：circle \| square \| triangle \| diamond \| rect |
| `size` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartPoints/>
```

## `<chartPoints>`

- 声明类型：`ChartSeriesPointsType`
- 出现场景：ChartSeriesType
- 父元素：`<chartPlot>`, `<chartSeries>`
- 中文检索词：颜色

### 高优先级约束

- 图表系列数据点配置（第二层：单系列统一配置 + 单点精确定制） 继承ChartGlobalPointsType的所有属性 适用于: 折线图、散点图、气泡图 属性: - color: 该系列所有点的颜色 - shape: 该系列所有点的形状 - size: 该系列所有点的大小 子元素: - fillGradient: 该系列所有点的填充渐变(可选) - strokeGradient: 该系列所有点的边框/描边渐变(可选) - chartPoint: 单个数据点配置(可选, 多个), 用于覆盖特定点的样式

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `shape` | 否 | 默认 `circle` | `ChartPointShapeType` | 图表数据点形状枚举 可选值: circle(圆形) \| square(正方形) \| triangle(三角形) \| diamond(菱形) \| rect(矩形)；字符串；枚举：circle \| square \| triangle \| diamond \| rect |
| `size` | 否 | - | `nonNegativeInteger` | 非负整数（>= 0） |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1），`strokeGradient`（0..1），`chartPoint`（0..unbounded）]

### 最小可用 XML

```xml
<chartPoints/>
```

## `<chartRadar>`

- 声明类型：`ChartRadarType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 雷达图专用配置 属性: - shape: 雷达图外轮廓形状(polygon|circle), 默认polygon - area: 是否填充区域(类似面积图效果), 默认true

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `shape` | 否 | 默认 `polygon` | `ChartRadarShapeType` | 雷达图外轮廓形状枚举 可选值: polygon(多边形) \| circle(圆形)；字符串；枚举：polygon \| circle |
| `area` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartRadar/>
```

## `<chartRegion>`

- 声明类型：`ChartRegionType`
- 出现场景：ChartStyleType
- 父元素：`<chartStyle>`

### 高优先级约束

- 完整绘图区样式，与图表区背景独立；字段缺省时保持既有渲染。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `background` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

任意顺序各一次[`chartBackgroundGradient`（0..1），`chartBorder`（0..1）]

### 最小可用 XML

```xml
<chartRegion/>
```

## `<chartSector>`

- 声明类型：`ChartSectorType`
- 出现场景：ChartSectorsType
- 父元素：`<chartSectors>`
- 中文检索词：颜色

### 高优先级约束

- 图表单个扇区配置 适用于: 饼图、环形图 属性: - index: 扇区索引(从1开始, 必需), 表示第几个扇区 - offsetRadius: 扇区径向偏移比例[0,1], 用于突出显示 - borderColor: 扇区边框颜色 - color: 扇区填充颜色 子元素: - fillGradient: 扇区填充渐变(可选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 是 | - | `positiveInteger` | 正整数（> 0） |
| `offsetRadius` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1）]

### 最小可用 XML

```xml
<chartSector index="1"/>
```

## `<chartSectors>`

- 声明类型：`ChartSectorsType`
- 出现场景：ChartSeriesType
- 父元素：`<chartSeries>`

### 高优先级约束

- 图表扇区整体配置 适用于: 饼图、环形图 属性: - borderColor: 所有扇区的统一边框颜色 - innerRadius: 内半径比例[0,1], 0为饼图, 大于0为环形图, 默认0 - offsetRadius: 整体径向偏移比例[0,1], 将整个饼图从中心推开, 默认0 - startAngle: 起始角度[0,360), 控制第一个扇区的起始位置, 默认0 子元素: - fillGradient: 所有扇区的统一填充渐变(可选) - chartSector: 单个扇区配置(可选, 多个), 用于定制特定扇区

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `innerRadius` | 否 | 默认 `0` | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `offsetRadius` | 否 | 默认 `0` | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `startAngle` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |

### 子元素（内容模型）

按顺序[`fillGradient`（0..1），`chartSector`（0..unbounded）]

### 最小可用 XML

```xml
<chartSectors/>
```

## `<chartSeries>`

- 声明类型：`ChartSeriesType`
- 出现场景：ChartSeriesListType
- 父元素：`<chartSeriesList>`

### 高优先级约束

- 图表单个系列完整配置（用于覆盖全局配置或定制特定系列） 属性: - index: 系列索引(从1开始, 必需), 指定作用于第几个系列 - comboType: 组合图中该系列的类型(column|line|area) - yAxisPosition: 该系列使用的Y轴位置(left|right) 子元素: - chartPoints: 数据点样式配置(可选) - chartLine: 线条样式配置(可选) - chartArea: 面积样式配置(可选) - chartBars: 柱子样式配置(可选) - chartSectors: 扇区样式配置(可选) - chartLabels: 数据标签配置(可选) - chartTooltip: 数据提示框配置(可选) - chartInvertIfNegative: 柱/条负值反色配置(可选) - chartWaterfall: 瀑布图单系列配置(可选), 仅瀑布图使用

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 是 | - | `positiveInteger` | 正整数（> 0） |
| `comboType` | 否 | - | `ChartComboSeriesType` | 组合图系列类型枚举 可选值: column(柱状) \| line(折线) \| area(面积) \| scatter(散点)；字符串；枚举：column \| line \| area \| scatter |
| `yAxisPosition` | 否 | - | `ChartYAxisPositionType` | 图表Y轴位置枚举 可选值: left(左侧) \| right(右侧)；字符串；枚举：left \| right |

### 子元素（内容模型）

任意顺序各一次[`chartPoints`（0..1），`chartLine`（0..1），`chartArea`（0..1），`chartBars`（0..1），`chartSectors`（0..1），`chartLabels`（0..1），`chartTooltip`（0..1），`chartInvertIfNegative`（0..1），`chartWaterfall`（0..1）]

### 最小可用 XML

```xml
<chartSeries index="1"/>
```

## `<chartSeriesList>`

- 声明类型：`ChartSeriesListType`
- 出现场景：ChartPlotType
- 父元素：`<chartPlot>`

### 高优先级约束

- 图表多系列配置 子元素: - chartSeries: 单个系列配置(必需, 1个或多个), 用于定制特定系列

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`chartSeries`（1..unbounded）]

### 最小可用 XML

```xml
<chartSeriesList><chartSeries index="1"/></chartSeriesList>
```

## `<chartSmooth>`

- 声明类型：`ChartLineSmoothType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 图表平滑折线配置（空标签即启用, 将折线转换为贝塞尔曲线） 适用于: 折线图、面积图、雷达图、组合图 无属性 无子元素

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartSmooth/>
```

## `<chartStack>`

- 声明类型：`ChartStackType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 图表堆叠配置（将多个系列的值累加显示） 适用于: 面积图、条形图、柱状图、组合图 属性: - percentage: 是否启用百分比堆叠(显示占比而非绝对值), 默认false

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `percentage` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartStack/>
```

## `<chartStep>`

- 声明类型：`ChartLineStepType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`

### 高优先级约束

- 图表阶梯折线配置（空标签即启用, 将折线转换为阶梯状） 适用于: 折线图、面积图、组合图 无属性 无子元素

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartStep/>
```

## `<chartStyle>`

- 声明类型：`ChartStyleType`
- 出现场景：<chart>
- 父元素：`<chart>`

### 高优先级约束

- 图表全局样式容器 子元素: - chartBackground: 背景配置(可选) - chartFont: 默认字体配置(可选) - chartBorder: 边框配置(可选)，无需边框时不设置 - chartColorTheme: 配色主题(可选) - chartColorGradient: 渐变填充开关(可选) - chartBackgroundGradient: 图表区背景渐变(可选) - chartRegion: 完整绘图区的填充、渐变和边框(可选)

### 完整可用属性

无属性。

### 子元素（内容模型）

任意顺序各一次[`chartBackground`（0..1），`chartFont`（0..1），`chartBorder`（0..1），`chartColorTheme`（0..1），`chartColorGradient`（0..1），`chartBackgroundGradient`（0..1），`chartRegion`（0..1）]

### 最小可用 XML

```xml
<chartStyle/>
```

## `<chartSubTitle>`

- 声明类型：`ChartTitleType`
- 出现场景：<chart>
- 父元素：`<chart>`
- 中文检索词：字号, 字体大小, 颜色, 字体

### 高优先级约束

- 图表标题配置 属性: - textAlign: 文本对齐方式(left|center|right), 默认left - fontFamily: 字体族名称，仅图表根级主标题/副标题支持；坐标轴标题不支持 - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色 内容: 标题文本

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `textAlign` | 否 | 默认 `left` | `ChartTextAlignType` | 图表文本对齐方式枚举 可选值: left(左对齐) \| center(居中) \| right(右对齐)；字符串；枚举：left \| center \| right |
| `fontFamily` | 否 | - | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartSubTitle/>
```

## `<chartSubtotal>`

- 声明类型：`ChartWaterfallSubtotalType`
- 出现场景：ChartWaterfallSubtotalsType
- 父元素：`<chartSubtotals>`

### 高优先级约束

- 瀑布图小计节点 属性: - index: 小计节点索引, 从0开始 - mode: 小计计算模式(0|1) - alias: 小计别名

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 是 | - | `nonNegativeInteger` | 非负整数（>= 0） |
| `mode` | 是 | - | `匿名简单类型` | 整数；枚举：0 \| 1 |
| `alias` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartSubtotal index="1" mode="0"/>
```

## `<chartSubtotals>`

- 声明类型：`ChartWaterfallSubtotalsType`
- 出现场景：ChartWaterfallSeriesConfigType; ChartWaterfallType
- 父元素：`<chartWaterfall>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`chartSubtotal`（0..unbounded）]

### 最小可用 XML

```xml
<chartSubtotals/>
```

## `<chartTitle>`

- 声明类型：`ChartMainTitleType`
- 出现场景：<chart>
- 父元素：`<chart>`, `<chartAxis>`
- 中文检索词：字号, 字体大小, 颜色, 字体

### 高优先级约束

- 主标题专用样式；副标题、坐标轴标题不扩展 overlay/layout/background/border。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `overlay` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `background` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `textAlign` | 否 | 默认 `left` | `ChartTextAlignType` | 图表文本对齐方式枚举 可选值: left(左对齐) \| center(居中) \| right(右对齐)；字符串；枚举：left \| center \| right |
| `fontFamily` | 否 | - | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |

### 子元素（内容模型）

任意顺序各一次[`chartLayout`（0..1），`chartBorder`（0..1）]

### 最小可用 XML

```xml
<chartTitle/>
```

## `<chartTitle>`

- 声明类型：`ChartTitleType`
- 出现场景：ChartAxisType
- 父元素：`<chart>`, `<chartAxis>`
- 中文检索词：字号, 字体大小, 颜色, 字体

### 高优先级约束

- 图表标题配置 属性: - textAlign: 文本对齐方式(left|center|right), 默认left - fontFamily: 字体族名称，仅图表根级主标题/副标题支持；坐标轴标题不支持 - fontSize: 字号大小 - bold: 是否加粗 - italic: 是否斜体, 默认false - underline: 是否下划线, 默认false - strikethrough: 是否删除线, 默认false - color: 文本颜色 内容: 标题文本

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `textAlign` | 否 | 默认 `left` | `ChartTextAlignType` | 图表文本对齐方式枚举 可选值: left(左对齐) \| center(居中) \| right(右对齐)；字符串；枚举：left \| center \| right |
| `fontFamily` | 否 | - | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartTitle/>
```

## `<chartTitleText>`

- 声明类型：`ChartWaterfallTitleTextType`
- 出现场景：ChartWaterfallSeriesConfigType; ChartWaterfallType
- 父元素：`<chartWaterfall>`

### 高优先级约束

- 瀑布图标题文本 属性: - positive: 正值标题 - negative: 负值标题 - subtotal: 小计标题

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `positive` | 否 | - | `string` | 字符串 |
| `negative` | 否 | - | `string` | 字符串 |
| `subtotal` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartTitleText/>
```

## `<chartTooltip>`

- 声明类型：`ChartTooltipType`
- 出现场景：ChartSeriesType; <chart>
- 父元素：`<chart>`, `<chartSeries>`

### 高优先级约束

- 图表 Tooltip 配置 属性: - format: 数字格式代码，例如 0%、0.00%、0.00、#,##0.00、¥#,##0.00, 0万

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `format` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartTooltip/>
```

## `<chartTotalLabels>`

- 声明类型：`ChartWaterfallTotalLabelsType`
- 出现场景：ChartWaterfallType
- 父元素：`<chartWaterfall>`
- 中文检索词：字号, 字体大小, 颜色

### 高优先级约束

- 瀑布图汇总标签配置 继承图表通用字体样式 属性: - template: 标签模板 - position: 标签位置(default|top|middle|bottom) - category: 是否显示类别名 - value: 是否显示数值

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `template` | 否 | - | `string` | 字符串 |
| `position` | 否 | - | `匿名简单类型` | 字符串；枚举：default \| top \| middle \| bottom |
| `category` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `value` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartTotalLabels/>
```

## `<chartTotalStyle>`

- 声明类型：`ChartWaterfallSeriesStyleType`
- 出现场景：ChartWaterfallSeriesConfigType; ChartWaterfallType
- 父元素：`<chartWaterfall>`
- 中文检索词：颜色

### 高优先级约束

- 瀑布图负值或汇总柱样式 属性: - color: 填充颜色 - opacity: 填充透明度[0,1] - borderColor: 边框颜色 - borderWidth: 非负边框宽度(像素) - borderStyle: 边框样式(solid|dashed|dotted)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `opacity` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `borderColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `borderWidth` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `borderStyle` | 否 | - | `ChartLineStyleType` | 图表线条样式枚举 可选值: solid(实线) \| dashed(虚线) \| dotted(点线)；字符串；枚举：solid \| dashed \| dotted |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<chartTotalStyle/>
```

## `<chartWaterfall>`

- 声明类型：`ChartWaterfallSeriesConfigType`
- 出现场景：ChartSeriesType
- 父元素：`<chartExtra>`, `<chartSeries>`

### 高优先级约束

- 瀑布图单系列配置 属性: - firstValueAsTotal: 是否将首值作为汇总值 - lastValueAsSubtotal: 是否将末值作为小计值 子元素: - chartNegativeStyle: 负值柱样式 - chartTotalStyle: 汇总柱样式 - chartTitleText: 正值、负值和小计标题文本 - chartSubtotals: 小计节点列表 正值柱样式复用同一 chartSeries 下的 chartBars

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `firstValueAsTotal` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `lastValueAsSubtotal` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

任意顺序各一次[`chartNegativeStyle`（0..1），`chartTotalStyle`（0..1），`chartTitleText`（0..1），`chartSubtotals`（0..1）]

### 最小可用 XML

```xml
<chartWaterfall/>
```

## `<chartWaterfall>`

- 声明类型：`ChartWaterfallType`
- 出现场景：ChartExtraType
- 父元素：`<chartExtra>`, `<chartSeries>`

### 高优先级约束

- 瀑布图全局配置 属性: - firstValueAsTotal: 是否将首值作为汇总值 - lastValueAsSubtotal: 是否将末值作为小计值 - cornerRadius: 柱体圆角(default|small|large) - gradient: 是否启用渐变填充 - connectorLine: false 时隐藏柱体连接线 - totalLabels: false 时隐藏汇总标签 子元素: - chartConnectorLine: 柱体连接线样式 - chartTotalLabels: 汇总标签样式 - chartNegativeStyle: 负值柱样式 - chartTotalStyle: 汇总柱样式 - chartTitleText: 正值、负值和小计标题文本 - chartSubtotals: 小计节点列表 正值柱样式复用 chartPlot 下的 chartBars

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `firstValueAsTotal` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `lastValueAsSubtotal` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `cornerRadius` | 否 | - | `匿名简单类型` | 字符串；枚举：default \| small \| large |
| `gradient` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `connectorLine` | 否 | - | `匿名简单类型` | 字符串；枚举：false |
| `totalLabels` | 否 | - | `匿名简单类型` | 字符串；枚举：false |

### 子元素（内容模型）

任意顺序各一次[`chartConnectorLine`（0..1），`chartTotalLabels`（0..1），`chartNegativeStyle`（0..1），`chartTotalStyle`（0..1），`chartTitleText`（0..1），`chartSubtotals`（0..1）]

### 最小可用 XML

```xml
<chartWaterfall/>
```

## `<col>`

- 声明类型：`匿名 complexType`
- 出现场景：<colgroup>
- 父元素：`<colgroup>`
- 中文检索词：宽, 宽度

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `span` | 否 | 默认 `1` | `PositiveSize` | 浮点数；限制：> 0 |
| `width` | 否 | 默认 `110` | `PositiveSize` | 浮点数；限制：> 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<col/>
```

## `<colgroup>`

- 声明类型：`匿名 complexType`
- 出现场景：<table>
- 父元素：`<table>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`col`（1..unbounded）]

### 最小可用 XML

```xml
<colgroup><col/></colgroup>
```

## `<color>`

- 声明类型：`匿名 complexType`
- 出现场景：ChartColorThemeType
- 父元素：`<chartColorTheme>`

### 高优先级约束

- 单个主题颜色定义 属性: - value: 颜色值(必需)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `value` | 是 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<color value="value"/>
```

## `<content>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<note>`, `<shape>`, `<td>`
- 中文检索词：正文, 文本内容, 字号, 字体大小, 字体, 颜色

### 高优先级约束

- 文本内容根容器, 用于描述结构化文本 属性说明: - textType: 控制整体文本样式 (title/headline/sub-headline/body/caption) - verticalAlign: 内容在容器中的垂直对齐方式 - paddingTop/Right/Bottom/Left: 内容与容器边缘的间距, 当位于shape中, shape的type为text时, padding默认值各为0, 当shape的type为其他时, padding默认值各为5, 当位于td中, padding默认值各为8 - lineSpacing: Block 级别行间距 - beforeLineSpacing/afterLineSpacing: 段落前/后的行间距, 可选, 默认值为fixed:0 - letterSpacing: content 级别字间距 - textAlign: content 级别文本对齐方式, 可选, 当位于shape中, shape的type为text时, textAlign默认值为left, 当shape的type为其他时, textAlign默认值为center - fontSize: content 级别字体大小 - fontFamily: content 级别字体族 - color: content 级别字体颜色 - backgroundColor: content 级别背景颜色 - bold: content 级别是否加粗 - italic: content 级别是否斜体 - strikethrough: content 级别是否删除线 - underline: content 级别是否下划线 - list: content 级别列表类型 bullet/number - listStyle: content 级别列表样式 - bulletColor: 列表符号颜色（纯色）, 可选 - bulletSize: 列表符号大小, 可选, 百分比字符串（相对于文本字号, 取值范围 25%-400%）如 "100%", 或绝对像素值（取值范围 6-400）如 "14" - autoStartAt: 有序列表起始编号, 可选, 取值范围 [1, 32767]; 作为后代段落的初始计数器, 子元素 <p>/<ol> 可通过自身 autoStartAt 重置 - bulletChar: 自定义列表符号字符, 可选, 如 "★", "→" 等, 设置后覆盖 listStyle 的符号 - tabStopPos/defaultTabSize: 后代段落的默认 Tab 停止位和步长, p 同名属性可覆盖 - anchorCenter: 控制文本对齐方式, 优先级高于 textAlign - autoFit: 控制文本编辑溢出时处理策略 - baseline: 上标/下标, 相较于文本基线的偏移量 - wrap: 是否自动换行 注意：如果content子元素不指定属性, 默认继承content的属性值, 如果局部子元素指定了属性, 则使用局部属性值 autoStartAt 运行计数器示例（显式指定重置, 未指定沿用前序计数器）: <content autoStartAt="5"> <p list="number">A</p> <!-- A=5, 继承 content 初始值 --> <p list="number" autoStartAt="10">B</p> <!-- B=10, 本段显式重置 --> <p list="number">C</p> <!-- C=11, 沿用前序计数器递增 --> </content> 子元素: - p: 段落元素 - ul: 无序列表元素 - ol: 有序列表元素

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `textType` | 否 | 默认 `body` | `TextType` | 文本语义层级, 影响默认字号和样式 title = 大标题 headline = 标题 sub-headline = 副标题 body = 正文 caption = 小号正文；字符串；枚举：title \| headline \| sub-headline \| body \| caption |
| `verticalAlign` | 否 | 默认 `middle` | `VerticalAlignType` | 字符串；枚举：top \| middle \| bottom |
| `paddingTop` | 否 | - | `PaddingValueType` | 单个内边距值, 单位: px, 取值范围 [0, 1584]；浮点数；限制：>= 0，<= 1584 |
| `paddingRight` | 否 | - | `PaddingValueType` | 单个内边距值, 单位: px, 取值范围 [0, 1584]；浮点数；限制：>= 0，<= 1584 |
| `paddingBottom` | 否 | - | `PaddingValueType` | 单个内边距值, 单位: px, 取值范围 [0, 1584]；浮点数；限制：>= 0，<= 1584 |
| `paddingLeft` | 否 | - | `PaddingValueType` | 单个内边距值, 单位: px, 取值范围 [0, 1584]；浮点数；限制：>= 0，<= 1584 |
| `lineSpacing` | 否 | 默认 `multiple:1.5` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `beforeLineSpacing` | 否 | 默认 `fixed:0` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `afterLineSpacing` | 否 | 默认 `fixed:0` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `letterSpacing` | 否 | - | `double` | 浮点数 |
| `textAlign` | 否 | - | `TextAlignType` | 字符串；枚举：left \| center \| right \| justify \| dist |
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontFamily` | 否 | - | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `backgroundColor` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `list` | 否 | 默认 `none` | `ListType` | 字符串；枚举：bullet \| number \| none |
| `listStyle` | 否 | - | `ListStyleType` | 联合类型：OrderedListStyle（有序列表样式 分为两类： 1. 复合样式（按层级循环不同格式）：如 number-lower-alpha-lower-roman 表示第1级用数字、第2级用小写字母、第3级用小写罗马，超过层级数后循环 2. 单一样式（所有层级使用同一格式，不循环）：以 PPTX 标准 scheme 命名，如 alpha-lc-paren-both 表示所有层级都用 (a)(b)(c) 格式；字符串；枚举：number-lower-alpha-lower-roman \| number-lower-alpha-lower-roman-paren \| hierarchical-number \| upper-alpha-lower-alpha-lower-roman \| upper-roman-upper-alpha-number \| zero-padded-lower-alpha-lower-roman \| circle-number \| lower-alpha-paren \| lower-alpha-dot \| chinese-formal \| alpha-lc-paren-both \| alpha-uc-paren-both \| alpha-lc-paren-r \| alpha-uc-paren-r \| alpha-lc-period \| alpha-uc-period \| arabic-paren-both \| arabic-paren-r \| arabic-period \| arabic-plain \| arabic-db-period \| arabic-db-plain \| arabic1-minus \| arabic2-minus \| roman-lc-paren-both \| roman-uc-paren-both \| roman-lc-paren-r \| roman-uc-paren-r \| roman-lc-period \| roman-uc-period \| circle-num-db-plain \| circle-num-wd-black-plain \| circle-num-wd-white-plain \| ea1-chs-period \| ea1-chs-plain \| ea1-cht-period \| ea1-cht-plain \| ea1-jpn-chs-db-period \| ea1-jpn-kor-plain \| ea1-jpn-kor-period \| hebrew2-minus \| thai-alpha-period \| thai-alpha-paren-r \| thai-alpha-paren-both \| thai-num-period \| thai-num-paren-r \| thai-num-paren-both \| hindi-alpha-period \| hindi-num-period \| hindi-num-paren-r \| hindi-alpha1-period） / UnorderedListStyle（无序列表样式 分为两类： 1. 复合样式（按层级循环不同图标）：如 circle-hollow-square 表示第1级实心圆、第2级空心圆、第3级实心方形，超过层级数后循环 2. 单一样式（所有层级使用同一图标，不循环）：以 pptx- 前缀命名，如 pptx-circle 表示所有层级都用 ● 实心圆；枚举：circle-hollow-square \| diamond-triangle-square \| hollow-square-all \| arrow-diamond-circle \| star-hollow-circle-square \| triangle-hollow-circle-square \| solid-square-all \| solid-diamond-all \| check-all \| pptx-circle \| pptx-square \| pptx-diamond \| pptx-square-empty \| pptx-check \| pptx-triangle \| pptx-bullet \| pptx-circle-empty \| pptx-diamond-empty \| pptx-arrow-right \| pptx-star \| pptx-square-shadow） |
| `bulletColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `bulletSize` | 否 | - | `BulletSizeType` | 列表符号大小, 二选一: - 百分比字符串（相对于文本字号）, 取值范围 25%-400%, 如 "100%" - 绝对像素值, 取值范围 6-400, 如 "14"；联合类型：字符串；格式正则：(2[5-9]\|[3-9][0-9]\|[1-3][0-9]{2}\|400)% / 格式正则：[6-9]\|[1-9][0-9]\|[1-3][0-9]{2}\|400 |
| `autoStartAt` | 否 | - | `AutoStartAtType` | 有序列表起始编号, 取值范围 [1, 32767]；正整数（> 0）；限制：>= 1，<= 32767 |
| `bulletChar` | 否 | - | `BulletCharType` | 自定义列表符号, 如 "★", "→", "✓", "◆", 也支持 emoji；字符串；限制：最短长度 1，最长长度 8 |
| `tabStopPos` | 否 | - | `TabStopPosType` | Tab 停止位列表, 用于 content@tabStopPos 或 p@tabStopPos, p 优先级更高。 格式为 位置+对齐方式, 逗号分隔, 如 "100r,200l,300ctr"; 对齐方式支持 l/ctr/r/dec。 位置单位 px, 有限正数, 支持小数, 范围 (0,4031]; 列表长度 1-32。 消费方按位置升序处理; 同一生效配置内位置不重复, 由 Node 层校验。 遇到 tab 元素时, 使用第一个大于当前行内坐标的停止位; 不存在则按 defaultTabSize 步进。；字符串；格式正则：(0\.\d*[1-9]\d*\|([1-9]\d{0,2}\|[1-3]\d{3}\|40[0-2]\d\|4030)(\.\d+)?\|4031(\.0+)?)(l\|ctr\|r\|dec)(,(0\.\d*[1-9]\d*\|([1-9]\d{0,2}\|[1-3]\d{3}\|40[0-2]\d\|4030)(\.\d+)?\|4031(\.0+)?)(l\|ctr\|r\|dec)){0,31} |
| `defaultTabSize` | 否 | - | `TabSizeType` | Tab 默认间距, 单位 px, 有限正数, 支持小数, 取值范围 (0,4031]；十进制数；限制：> 0，<= 4031 |
| `anchorCenter` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `autoFit` | 否 | 默认 `no-auto-fit` | `AutoFitType` | 字符串；枚举：shape-auto-fit \| no-auto-fit \| normal-auto-fit |
| `wrap` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

按顺序[选择其一[`p` | `ul` | `ol`]（0..unbounded）]

### 最小可用 XML

```xml
<content textType="body"><p>文本</p></content>
```

## `<crop>`

- 声明类型：`CropType`
- 出现场景：<img>
- 父元素：`<img>`
- 中文检索词：锚点, 对齐

### 高优先级约束

- 裁剪配置: 将原图裁剪到目标尺寸 (img 元素的 width × height) 可选属性: type: 裁剪形状, 默认 rect path: 自定义裁剪路径, type="custom" 时生效, SVG path 字符串, 坐标系为裁剪框本地坐标系 anchor: 裁剪方位 (top/bottom/left/right/center), 参见 CropAnchorType leftOffset / rightOffset / topOffset / bottomOffset: 四向偏移量 (px), 正值向内裁剪、负值向外扩展留白、0对齐边缘 presetHandlers: 控制点配置, 对应 ECMA 预设形状的控制点。单个或多个数字, 多个用逗号分隔。 示例: type="rect" 且 presetHandlers="60" 时为圆角矩形, 圆角半径 60px 【推荐用法】使用 anchor 指定裁剪方位: - 不设置 anchor 或设置 anchor="center" 时: 默认按图片居中裁剪 - 设置 anchor 时: 按指定方位裁剪, 例如 anchor="top" 表示保留顶部、裁掉底部多余部分 - 使用 anchor 后, 不需要再设置 offset - anchor 模式下原图按等比缩放后裁剪, 不会发生拉伸或压缩 【进阶用法】使用 offset 精细控制裁剪边界: - 适用于用户在编辑器中手动调整裁剪、或从外部协议导入的场景 - 原图先填充到预裁剪区域, 再根据 offset 从四边裁出最终尺寸 - 注意: 若预裁剪尺寸与原图比例不一致会产生拉伸变形; 无法确定原图比例时, 不要指定 offset 【优先级】 如果同时设置了 anchor 和 offset, 以 anchor 为准, offset 被忽略 典型用法: 居中裁剪 (默认行为) 居中裁剪 (显式声明) 保留顶部 保留左侧 圆角矩形裁剪, 默认居中

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 否 | 默认 `rect` | `ShapeType` | 图形形状类型枚举；字符串；枚举：custom \| rect \| ellipse \| text \| triangle \| rt-triangle \| slides-lt-triangle \| pentagon \| hexagon \| heptagon \| octagon \| decagon \| dodecagon \| diamond \| parallelogram \| trapezoid \| non-isosceles-trapezoid \| round-rect \| slides-full-round-rect \| round2diag-rect \| round1rect \| round2same-rect \| snip-round-rect \| snip1rect \| snip2diag-rect \| snip2same-rect \| slides-star \| star4 \| star5 \| star6 \| star7 \| star8 \| star10 \| star12 \| star16 \| star24 \| star32 \| right-arrow \| left-arrow \| up-arrow \| down-arrow \| left-right-arrow \| slides-left-right-arrow \| up-down-arrow \| quad-arrow \| left-right-up-arrow \| left-up-arrow \| bent-arrow \| bent-up-arrow \| curved-right-arrow \| curved-left-arrow \| curved-up-arrow \| curved-down-arrow \| striped-right-arrow \| notched-right-arrow \| circular-arrow \| left-circular-arrow \| left-right-circular-arrow \| swoosh-arrow \| uturn-arrow \| slides-round-rect-callout1 \| slides-round-rect-callout2 \| slides-round-rect-callout3 \| slides-wedge-rect-callout \| slides-wedge-round-rect-callout \| callout1 \| callout2 \| callout3 \| accent-callout1 \| accent-callout2 \| accent-callout3 \| border-callout1 \| border-callout2 \| border-callout3 \| accent-border-callout1 \| accent-border-callout2 \| accent-border-callout3 \| wedge-rect-callout \| wedge-round-rect-callout \| wedge-ellipse-callout \| cloud-callout \| right-arrow-callout \| left-arrow-callout \| up-arrow-callout \| down-arrow-callout \| left-right-arrow-callout \| up-down-arrow-callout \| quad-arrow-callout \| flow-chart-process \| flow-chart-alternate-process \| flow-chart-decision \| flow-chart-input-output \| flow-chart-predefined-process \| flow-chart-internal-storage \| flow-chart-document \| flow-chart-multidocument \| flow-chart-terminator \| flow-chart-preparation \| flow-chart-manual-input \| flow-chart-manual-operation \| flow-chart-connector \| flow-chart-offpage-connector \| flow-chart-punched-card \| flow-chart-punched-tape \| flow-chart-summing-junction \| flow-chart-or \| flow-chart-collate \| flow-chart-sort \| flow-chart-extract \| flow-chart-merge \| flow-chart-offline-storage \| flow-chart-online-storage \| flow-chart-magnetic-tape \| flow-chart-magnetic-disk \| flow-chart-magnetic-drum \| flow-chart-display \| flow-chart-delay \| action-button-blank \| action-button-home \| action-button-help \| action-button-information \| action-button-forward-next \| action-button-back-previous \| action-button-end \| action-button-beginning \| action-button-return \| action-button-document \| action-button-sound \| action-button-movie \| slides-home-plate \| home-plate \| slides-chevron \| chevron \| pie \| pie-wedge \| donut \| arc \| slides-block-arc \| block-arc \| chord \| left-brace \| right-brace \| left-bracket \| right-bracket \| brace-pair \| bracket-pair \| teardrop \| can \| cube \| bevel \| folded-corner \| smiley-face \| heart \| lightning-bolt \| sun \| moon \| cloud \| irregular-seal1 \| irregular-seal2 \| ribbon \| ribbon2 \| ellipse-ribbon \| ellipse-ribbon2 \| left-right-ribbon \| vertical-scroll \| horizontal-scroll \| wave \| double-wave \| plus \| math-plus \| math-minus \| math-multiply \| math-divide \| math-equal \| math-not-equal \| corner \| diag-stripe \| frame \| half-frame \| funnel \| gear6 \| gear9 \| plaque \| plaque-tabs \| corner-tabs \| square-tabs \| chart-plus \| chart-star \| chart-x \| no-smoking \| line-inv |
| `path` | 否 | - | `string` | 字符串 |
| `anchor` | 否 | - | `CropAnchorType` | 裁剪方位枚举, 用于指定保留原图的哪个区域 - top: 保留顶部, 裁掉底部多余部分 - bottom: 保留底部, 裁掉顶部多余部分 - left: 保留左侧, 裁掉右侧多余部分 - right: 保留右侧, 裁掉左侧多余部分 - center: 居中保留, 四周均匀裁剪 居中场景可设置 anchor="center", 不设置 anchor 且不设置 offset 时也为默认居中裁剪；字符串；枚举：top \| bottom \| left \| right \| center |
| `leftOffset` | 否 | - | `double` | 浮点数 |
| `rightOffset` | 否 | - | `double` | 浮点数 |
| `topOffset` | 否 | - | `double` | 浮点数 |
| `bottomOffset` | 否 | - | `double` | 浮点数 |
| `presetHandlers` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<crop/>
```

## `<data>`

- 声明类型：`匿名 complexType`
- 出现场景：SlideType
- 父元素：`<slide>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`shape` | `line` | `polyline` | `img` | `table` | `icon` | `embed` | `chart` | `undefined`]（0..unbounded）

### 最小可用 XML

```xml
<data/>
```

## `<del>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 删除线文本

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<del/>
```

## `<dim1>`

- 声明类型：`ChartDataDim1Type`
- 出现场景：ChartDataType
- 父元素：`<chartData>`

### 高优先级约束

- 图表分类维度（第一维度：X轴/分类） 定义数据点的分类标签或X轴坐标值 子元素: - chartField: 数据字段(有且仅有1个)

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`chartField`]

### 最小可用 XML

```xml
<dim1><chartField name="value"/></dim1>
```

## `<dim2>`

- 声明类型：`ChartDataDim2Type`
- 出现场景：ChartDataType
- 父元素：`<chartData>`

### 高优先级约束

- 图表数值维度（第二维度：Y轴/数值） 包含数值系列数据, 每个field代表一个系列 气泡图使用4个字段并通过role标识x、y、group、size；group可为字符串，其余角色为数值 瀑布图至少包含1个数值字段；帕累托图严格输入包含1个数值字段 子元素: - chartField: 数据字段(至少1个), 每个字段代表一个数据系列

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`chartField`（1..unbounded）]

### 最小可用 XML

```xml
<dim2><chartField name="value"/></dim2>
```

## `<em>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 斜体/强调文本

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<em/>
```

## `<embed>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：内嵌, svg, 矢量图, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- 内层必须恰好有一个 SVG 命名空间元素：`<svg xmlns="http://www.w3.org/2000/svg">`。
- SVG 必须声明 `viewBox`，且所有图形、描边和文字边界都不得越出 viewBox；XSD 以 `xs:any` 接收 SVG，无法替你检查这条运行时约束。
- `embed` 的 width:height 应与 SVG viewBox 的 W:H 一致，避免服务端等比缩放后产生变形或留白。
- 嵌入内容容器, 外层承载 Slides 摆放和效果属性, 内层承载外部标准内容。 当前内层内容为标准 SVG, 必须使用 http://www.w3.org/2000/svg 命名空间。 后续可扩展承载 HTML 等其他外部内容。 必需属性: - topLeftX/topLeftY: 左上角坐标 - width/height: 显示尺寸 可选属性: - id: 唯一标识符 - rotation: 旋转角度[0, 360) - flipX/flipY: 水平/垂直翻转 - alpha: 不透明度[0,1] 子元素: - svg: 标准 SVG 根元素, 仅描述嵌入内容, 不承载 Slides 布局属性 - reflection: 倒影样式, 无reflection标签代表无倒影, 空reflection标签代表使用默认样式 - shadow: 外阴影样式, 无shadow标签代表无外阴影, 空shadow标签代表使用默认样式

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

按顺序[任意元素（namespace=http://www.w3.org/2000/svg），`reflection`（0..1），`shadow`（0..1）]

### 最小可用 XML

```xml
<embed topLeftX="0" topLeftY="0" width="200" height="100">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
    <rect x="0" y="0" width="200" height="100" fill="#FFFFFF"/>
  </svg>
</embed>
```

## `<endArrow>`

- 声明类型：`EndArrowStyleType`
- 出现场景：<line>; <polyline>
- 父元素：`<line>`, `<polyline>`

### 高优先级约束

- 结束箭头样式类型 - type: 结束箭头类型, 可选, 默认arrow - widthScale: 箭头宽度 - heightScale: 箭头高度 如果type为none, 则表示无箭头, 其他属性无效

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 否 | 默认 `none` | `ArrowType` | 箭头类型枚举定义；字符串；枚举：none \| arrow \| empty-triangle \| solid-triangle \| empty-diamond \| solid-diamond \| empty-circle \| solid-circle |
| `widthScale` | 否 | - | `ArrowScaleType` | 箭头缩放等级；字符串；枚举：sm \| med \| lg |
| `heightScale` | 否 | - | `ArrowScaleType` | 箭头缩放等级；字符串；枚举：sm \| med \| lg |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<endArrow/>
```

## `<field>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<outline>`, `<p>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 动态文本字段。 type 属性描述动态语义，元素内容是静态降级文本，可包含行内样式元素。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `FieldType` | 动态文本字段类型: - slidenum: 当前幻灯片页码 - datetime: 默认日期时间格式 - datetime1-datetime13: 预定义日期时间格式；字符串；枚举：slidenum \| datetime \| datetime1 \| datetime2 \| datetime3 \| datetime4 \| datetime5 \| datetime6 \| datetime7 \| datetime8 \| datetime9 \| datetime10 \| datetime11 \| datetime12 \| datetime13 |

### 子元素（内容模型）

选择其一[`strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline`]（0..unbounded）

### 最小可用 XML

```xml
<field type="slidenum"/>
```

## `<fill>`

- 声明类型：`FillType`
- 出现场景：<style>; <shape>; <img>; <icon>; <td>
- 父元素：`<icon>`, `<img>`, `<shape>`, `<style>`, `<td>`
- 中文检索词：填充, 背景色, 渐变

### 高优先级约束

- 填充类型: - color: 颜色填充 (RGB/RGBA格式) - fillImg: 填充图片 - fillPattern: 填充图案 优先级: fillPattern > fillImg > color

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`fillImg` | `fillPattern` | `fillColor`]（0..1）

### 最小可用 XML

```xml
<fill/>
```

## `<fillColor>`

- 声明类型：`FillColorType`
- 出现场景：FillType
- 父元素：`<background>`, `<fill>`
- 中文检索词：颜色

### 高优先级约束

- 颜色填充配置 - color: 纯色和渐变色 - rotateWithShape: 是否随形状旋转, 只对渐变色有效

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<fillColor/>
```

## `<fillGradient>`

- 声明类型：`ChartGradientType`
- 出现场景：ChartSeriesPointsType; <chartPoint>; ChartSeriesAreaType; ChartSeriesBarsType; <chartBar>; ChartSectorType; ChartSectorsType
- 父元素：`<chartArea>`, `<chartBar>`, `<chartBars>`, `<chartPoint>`, `<chartPoints>`, `<chartSector>`, `<chartSectors>`

### 高优先级约束

- 图表渐变配置 属性: - type: 渐变类型(linear|radial) - x0/y0/x1/y1: 线性渐变起止点坐标 - r0/r1: 径向渐变半径 - gradientMethod: 渐变算法/插值方式 子元素: - stops: 渐变色标列表

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |
| `x0` | 否 | - | `double` | 浮点数 |
| `y0` | 否 | - | `double` | 浮点数 |
| `x1` | 否 | - | `double` | 浮点数 |
| `y1` | 否 | - | `double` | 浮点数 |
| `r0` | 否 | - | `double` | 浮点数 |
| `r1` | 否 | - | `double` | 浮点数 |
| `gradientMethod` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`stops`]

### 最小可用 XML

```xml
<fillGradient type="linear"><stops><stop offset="value" color="rgb(0,0,0)"/></stops></fillGradient>
```

## `<fillImg>`

- 声明类型：`FillImgType`
- 出现场景：FillType
- 父元素：`<background>`, `<fill>`
- 中文检索词：平铺图片, 填充图片, 背景图, 透明度, 不透明度, 对齐

### 高优先级约束

- 平铺图片的 `align` 使用 `left-top` / `right-top` / `left-bottom` / `right-bottom`；不要写成效果对齐使用的 `top-left` 等值。
- 拉伸属性与平铺属性不能同时使用。
- 图片填充配置 基础属性: - src: 图片资源标识, 必填 - alt: 图片替代文本/名称, 可选, 默认为空 - rotateWithShape: 是否随形状旋转, 可选, 默认为true - alpha: 图片不透明度, 可选, 范围[0, 1], 默认为1 拉伸填充属性: - stretchLeft/stretchRight: 左右拉伸比例, 可选, 范围[-1000, 1000], (对应 -100000% 到 100000%) - stretchTop/stretchBottom: 上下拉伸比例, 可选, 范围[-1000, 1000], (对应 -100000% 到 100000%) 平铺填充属性: - flip: 平铺翻转方向, 可选 - align: 平铺对齐方式, 可选 - horizontalOffset/verticalOffset: 水平/垂直偏移, 可选 - horizontalRatio/verticalRatio: 水平/垂直缩放比例, 可选, 范围[0, 1] 注意: 拉伸和平铺属性不能同时使用

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `src` | 是 | - | `string` | 字符串 |
| `alt` | 否 | - | `string` | 字符串 |
| `rotateWithShape` | 否 | 默认 `true` | `boolean` | 布尔值：true / false / 1 / 0 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |
| `stretchLeft` | 否 | - | `double` | 浮点数 |
| `stretchRight` | 否 | - | `double` | 浮点数 |
| `stretchTop` | 否 | - | `double` | 浮点数 |
| `stretchBottom` | 否 | - | `double` | 浮点数 |
| `flip` | 否 | - | `TileFlipType` | 字符串；枚举：none \| horizontal \| vertical \| both |
| `align` | 否 | - | `TileAlignType` | 字符串；枚举：left-top \| top \| right-top \| left \| center \| right \| left-bottom \| bottom \| right-bottom |
| `horizontalOffset` | 否 | - | `double` | 浮点数 |
| `verticalOffset` | 否 | - | `double` | 浮点数 |
| `horizontalRatio` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `verticalRatio` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<fillImg src="file_token" align="left-top"/>
```

## `<fillPattern>`

- 声明类型：`FillPatternType`
- 出现场景：FillType
- 父元素：`<background>`, `<fill>`
- 中文检索词：透明度, 不透明度

### 高优先级约束

- 背景图案配置 基础属性: - type: 图案类型, 可选, 默认值为pct5 - foregroundColor: 前景色（纯色）, 可选, 默认跟随字体颜色 - backgroundColor: 背景色（纯色）, 可选, 默认为白色 rgb(255, 255, 255) - alpha: 不透明度

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 否 | 默认 `pct5` | `PatternType` | 字符串；枚举：pct5 \| pct10 \| pct20 \| pct25 \| pct30 \| pct40 \| pct50 \| pct60 \| pct70 \| pct75 \| pct80 \| pct90 \| lt-dn-diag \| lt-up-diag \| dk-dn-diag \| dk-up-diag \| wd-dn-diag \| wd-up-diag \| dn-diag \| up-diag \| lt-vert \| lt-horz \| nar-vert \| nar-horz \| dk-vert \| dk-horz \| horz \| vert \| dash-dn-diag \| dash-up-diag \| dash-horz \| dash-vert \| sm-confetti \| lg-confetti \| zig-zag \| wave \| diag-brick \| horz-brick \| weave \| plaid \| divot \| dot-grid \| dot-dmnd \| sm-grid \| lg-grid \| sm-check \| lg-check \| open-dmnd \| solid-dmnd \| cross \| diag-cross \| shingle \| trellis \| sphere |
| `foregroundColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `backgroundColor` | 否 | 默认 `rgb(255, 255, 255)` | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<fillPattern/>
```

## `<formula>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 通用公式元素。 用于展示各类科学公式。 结构说明： - 必须从支持的公式格式中选择且仅选择一种作为子元素。 - 当前版本支持格式：<latex> 示例： - 基础公式： <formula> <latex><![CDATA[ E = mc^2 ]]></latex> </formula>

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`latex`]

### 最小可用 XML

```xml
<formula><latex>value</latex></formula>
```

## `<headline>`

- 声明类型：`匿名 complexType`
- 出现场景：TextStylesType
- 父元素：`<textStyles>`
- 中文检索词：字体, 字号, 字体大小

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontFamily` | 否 | 默认 `思源黑体` | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `fontSize` | 否 | 默认 `38` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontColor` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<headline/>
```

## `<icon>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：图标, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- 图标元素, 支持外部图标资源和样式配置 属性: - id: 图标唯一标识符(可选) - iconType: 图标类型, 来自iconpark图标库 - width/height: 显示尺寸 - rotation: 旋转角度 - topLeftX/topLeftY: 左上角坐标 - flipX/flipY: 水平/垂直翻转 - alpha: 不透明度[0,1] 子元素: - fill: 填充样式, 无fill标签代表不填充, 空fill标签代表使用默认样式(默认颜色填充, 颜色为rgba(208, 211, 214, 1)) - border: 边框样式, 无border标签代表无边框, 空border标签代表使用默认样式(默认实线边框, 颜色为rgba(51, 51, 51, 1), 宽度为3) - reflection: 倒影样式, 无reflection标签代表无倒影, 空reflection标签代表使用默认样式 - shadow: 外阴影样式, 无shadow标签代表无外阴影, 空shadow标签代表使用默认样式

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `iconType` | 否 | 默认 `iconpark/Base/setting.svg` | `string` | 字符串 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

任意顺序各一次[`fill`（0..1），`border`（0..1），`reflection`（0..1），`shadow`（0..1）]

### 最小可用 XML

```xml
<icon topLeftX="0" topLeftY="0" width="100" height="100"/>
```

## `<img>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：图片, 图像, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- 必需属性: src: 图片token topLeftX, topLeftY: 显示位置左上角坐标(裁剪后) width, height: 显示尺寸(裁剪后) 可选属性: id: 唯一标识符 alt: 描述文本 rotation: 旋转角度[0, 360) flipX, flipY: 水平/垂直翻转 exposure, contrast, saturation, temperature: 图像调整参数 alpha: 不透明度[0, 1] 可选子元素: crop: 裁剪。无标签 / 空标签 / 仅设 anchor 时按等比缩放后裁剪到 width×height; anchor 指定保留方位 (top/bottom/left/right/center), 不设 anchor 即居中裁剪; offset 用于精细控制 reflection: 倒影。无标签代表无倒影,空标签代表使用默认样式 shadow: 外阴影。无标签代表无外阴影,空标签代表使用默认样式 border: 边框。无标签代表无边框,空标签代表使用默认样式(颜色: rgba(43, 47, 54, 1), 宽度: 2) fill: 填充。无标签代表无填充,空标签代表使用默认样式(颜色: rgba(91, 155, 213, 1))

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `src` | 是 | - | `string` | 字符串 |
| `alt` | 否 | - | `string` | 字符串 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `exposure` | 否 | 默认 `0` | `integer` | 整数 |
| `contrast` | 否 | 默认 `0` | `integer` | 整数 |
| `saturation` | 否 | 默认 `0` | `integer` | 整数 |
| `temperature` | 否 | 默认 `0` | `integer` | 整数 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

任意顺序各一次[`crop`（0..1），`border`（0..1），`reflection`（0..1），`shadow`（0..1），`fill`（0..1）]

### 最小可用 XML

```xml
<img src="file_token" topLeftX="0" topLeftY="0" width="160" height="90"/>
```

## `<latex>`

- 声明类型：`匿名 complexType`
- 出现场景：<formula>
- 父元素：`<formula>`

### 高优先级约束

- LaTeX 格式的公式内容。 本元素包含的 LaTeX 字符串必须严格符合附件中定义的宏集范围。 内容语法： - 语法范围：仅使用附件白名单中明确支持的宏。 - 表达建议：优先使用基础运算符、分式(\frac)、根号(\sqrt)、矩阵(matrix)等标准数学环境。 - 格式要求：必须使用 CDATA 包裹内容，且 CDATA 内部严禁进行 XML 转义（如 &lt;, &amp;）。 - 空白处理：解析器将保留 CDATA 内的所有换行和缩进，建议利用此特性保持 LaTeX 源码的结构化和可读性。

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<latex>value</latex>
```

## `<li>`

- 声明类型：`匿名 complexType`
- 出现场景：<ul>
- 父元素：`<ol>`, `<ul>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`p`]

### 最小可用 XML

```xml
<li><p/></li>
```

## `<li>`

- 声明类型：`匿名 complexType`
- 出现场景：<ol>
- 父元素：`<ol>`, `<ul>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `index` | 否 | - | `integer` | 整数 |

### 子元素（内容模型）

按顺序[`p`]

### 最小可用 XML

```xml
<li><p/></li>
```

## `<line>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：直线, 线条, 透明度, 不透明度

### 高优先级约束

- 线条/箭头元素, 支持多种样式和箭头类型 属性说明: - type: 线条类型 - id: 线条唯一标识符(可选) - startX/startY: 起点坐标 - endX/endY: 终点坐标 - alpha: 不透明度[0,1] 坐标说明: - startX/startY 和 endX/endY 都是绝对坐标 - 起点 = (startX, startY) - 终点 = (endX, endY) 子元素: - border: 线条样式(颜色/宽度/虚线等), 必需, 线条必须有边框样式, 空border标签表示默认样式(颜色:rgba(43, 47, 54, 1)), 宽度: 2px) - startArrow: 起点箭头, 可选 - endArrow: 终点箭头, 可选 - shadow: 外阴影效果, 可选, 无shadow标签表示无外阴影效果, 空shadow标签表示默认外阴影效果 - reflection: 倒影效果, 可选, 无reflection标签表示无倒影效果, 空reflection标签表示默认倒影效果

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 否 | 默认 `straight-connector1` | `LineType` | 直线线条类型枚举；字符串；枚举：straight-connector1 \| line |
| `id` | 否 | - | `string` | 字符串 |
| `startX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `startY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `endX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `endY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

任意顺序各一次[`border`，`startArrow`（0..1），`endArrow`（0..1），`shadow`（0..1），`reflection`（0..1）]

### 最小可用 XML

```xml
<line startX="0" startY="0" endX="100" endY="60">
  <border color="rgb(0,0,0)" width="1"/>
</line>
```

## `<note>`

- 声明类型：`匿名 complexType`
- 出现场景：SlideType
- 父元素：`<slide>`

### 高优先级约束

- 演讲者备注, 仅在演示模式显示 支持完整的内容结构 属性: - id: 备注唯一标识符 子元素: - content: 备注文本内容容器

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

任意顺序各一次[`content`（0..1）]

### 最小可用 XML

```xml
<note/>
```

## `<ol>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<content>`

### 高优先级约束

- 有序列表, 可指定序号 属性说明: - listStyle: 列表样式 - bulletColor: 列表符号颜色（纯色）, 可选 - bulletSize: 列表符号大小, 可选, 百分比字符串（相对于文本字号, 取值范围 25%-400%）或绝对像素值（取值范围 6-400） - autoStartAt: 有序列表起始编号, 可选, 取值范围 [1, 32767]; 作用于本列表组的计数器初始值, 子元素 <li@index> 可覆盖单项编号

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `listStyle` | 否 | 默认 `number-lower-alpha-lower-roman` | `OrderedListStyle` | 有序列表样式 分为两类： 1. 复合样式（按层级循环不同格式）：如 number-lower-alpha-lower-roman 表示第1级用数字、第2级用小写字母、第3级用小写罗马，超过层级数后循环 2. 单一样式（所有层级使用同一格式，不循环）：以 PPTX 标准 scheme 命名，如 alpha-lc-paren-both 表示所有层级都用 (a)(b)(c) 格式；字符串；枚举：number-lower-alpha-lower-roman \| number-lower-alpha-lower-roman-paren \| hierarchical-number \| upper-alpha-lower-alpha-lower-roman \| upper-roman-upper-alpha-number \| zero-padded-lower-alpha-lower-roman \| circle-number \| lower-alpha-paren \| lower-alpha-dot \| chinese-formal \| alpha-lc-paren-both \| alpha-uc-paren-both \| alpha-lc-paren-r \| alpha-uc-paren-r \| alpha-lc-period \| alpha-uc-period \| arabic-paren-both \| arabic-paren-r \| arabic-period \| arabic-plain \| arabic-db-period \| arabic-db-plain \| arabic1-minus \| arabic2-minus \| roman-lc-paren-both \| roman-uc-paren-both \| roman-lc-paren-r \| roman-uc-paren-r \| roman-lc-period \| roman-uc-period \| circle-num-db-plain \| circle-num-wd-black-plain \| circle-num-wd-white-plain \| ea1-chs-period \| ea1-chs-plain \| ea1-cht-period \| ea1-cht-plain \| ea1-jpn-chs-db-period \| ea1-jpn-kor-plain \| ea1-jpn-kor-period \| hebrew2-minus \| thai-alpha-period \| thai-alpha-paren-r \| thai-alpha-paren-both \| thai-num-period \| thai-num-paren-r \| thai-num-paren-both \| hindi-alpha-period \| hindi-num-period \| hindi-num-paren-r \| hindi-alpha1-period |
| `bulletColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `bulletSize` | 否 | - | `BulletSizeType` | 列表符号大小, 二选一: - 百分比字符串（相对于文本字号）, 取值范围 25%-400%, 如 "100%" - 绝对像素值, 取值范围 6-400, 如 "14"；联合类型：字符串；格式正则：(2[5-9]\|[3-9][0-9]\|[1-3][0-9]{2}\|400)% / 格式正则：[6-9]\|[1-9][0-9]\|[1-3][0-9]{2}\|400 |
| `autoStartAt` | 否 | - | `AutoStartAtType` | 有序列表起始编号, 取值范围 [1, 32767]；正整数（> 0）；限制：>= 1，<= 32767 |

### 子元素（内容模型）

按顺序[`li`（1..unbounded）]

### 最小可用 XML

```xml
<ol><li><p/></li></ol>
```

## `<outline>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`
- 中文检索词：颜色, 宽, 宽度

### 高优先级约束

- 文本轮廓效果内联元素 可以对文本的特定部分应用轮廓效果

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `width` | 否 | 默认 `2` | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<outline/>
```

## `<p>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<content>`, `<li>`
- 中文检索词：段落

### 高优先级约束

- 段落容器, 支持富文本内容 可包含纯文本和内联格式元素(br/tab/strong/em/u/span/del/a/shadow/outline/formula/field) 内联元素嵌套：所有内联元素均可包含纯文本或其他内联元素，以实现复杂的格式组合 元素自嵌套：除a/formula元素外，其余内联元素支持自身嵌套，当shadow和outline自嵌套时，渲染效果遵循就近原则，以内层定义的样式为准 空格处理规则： - 文本内的连续空格会被合并为单个空格 - 文本开头和结尾的空格会被忽略 - 需要保留空格时（多个连续、首尾位置），请使用 字符 - 标签之间的空格和换行符会自动省略，换行请使用标签 制表符处理规则： - 需要使用制表符时，请使用 tab 元素 富文本元素说明： - br: 换行 - tab: 制表符 - strong: 加粗 - em: 斜体 - u: 下划线 - span: 文本样式 - del: 删除线 - a: 超链接 - shadow: 文本阴影 - outline: 文本轮廓 - formula: 科学公式（支持数学、物理等） - field: 动态文本字段，元素内容作为不支持动态字段时的降级文本 属性说明: - textAlign: 文本对齐方式 - lineSpacing: 行间距 - beforeLineSpacing/afterLineSpacing: 段落前/后的行间距 - letterSpacing: 字间距 - level: 段落级别, 取值范围 [1,10] - list: 列表类型(bullet/number) - listStyle: 列表样式 - bulletColor: 列表符号颜色（纯色）, 可选 - bulletSize: 列表符号大小, 可选, 百分比字符串（相对于文本字号, 取值范围 25%-400%）或绝对像素值（取值范围 6-400） - autoStartAt: 有序列表起始编号, 可选, 取值范围 [1, 32767]; 显式指定时从当前段落起重置计数器, 未指定时沿用同一 content 内的前序计数器 - bulletChar: 自定义列表符号字符, 可选 - marginLeft: 段落左侧缩进宽度 - marginRight: 段落右侧缩进宽度 - indent: 首行缩进宽度 - tabStopPos/defaultTabSize: 段落级 Tab 配置, 覆盖 content 同名配置

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `textAlign` | 否 | - | `TextAlignType` | 字符串；枚举：left \| center \| right \| justify \| dist |
| `lineSpacing` | 否 | 默认 `multiple:1.5` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `beforeLineSpacing` | 否 | 默认 `fixed:0` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `afterLineSpacing` | 否 | 默认 `fixed:0` | `LineSpacingType` | 行间距类型, 支持固定行距和多倍行距两种模式。 - fixed: 固定行距, 单位为px, 例如 "fixed:20" 表示20px固定行距 - multiple: 多倍行距，相对于行内最大字号的倍数, 例如 "multiple:1.5" 表示1.5倍行距, 表示 1.5 * maxFontSize 行距；字符串；格式正则：fixed:\d+(\.\d+)?\|multiple:\d+(\.\d+)? |
| `letterSpacing` | 否 | 默认 `0` | `LetterSpacingType` | 字符间距, 单位: px, 取值范围 [-1000, 1000]；浮点数；限制：>= -1000，<= 1000 |
| `level` | 否 | 默认 `1` | `LevelType` | 段落缩进层级, 取值范围 [1, 10]；整数；限制：>= 1，<= 10 |
| `list` | 否 | 默认 `none` | `ListType` | 字符串；枚举：bullet \| number \| none |
| `listStyle` | 否 | - | `ListStyleType` | 联合类型：OrderedListStyle（有序列表样式 分为两类： 1. 复合样式（按层级循环不同格式）：如 number-lower-alpha-lower-roman 表示第1级用数字、第2级用小写字母、第3级用小写罗马，超过层级数后循环 2. 单一样式（所有层级使用同一格式，不循环）：以 PPTX 标准 scheme 命名，如 alpha-lc-paren-both 表示所有层级都用 (a)(b)(c) 格式；字符串；枚举：number-lower-alpha-lower-roman \| number-lower-alpha-lower-roman-paren \| hierarchical-number \| upper-alpha-lower-alpha-lower-roman \| upper-roman-upper-alpha-number \| zero-padded-lower-alpha-lower-roman \| circle-number \| lower-alpha-paren \| lower-alpha-dot \| chinese-formal \| alpha-lc-paren-both \| alpha-uc-paren-both \| alpha-lc-paren-r \| alpha-uc-paren-r \| alpha-lc-period \| alpha-uc-period \| arabic-paren-both \| arabic-paren-r \| arabic-period \| arabic-plain \| arabic-db-period \| arabic-db-plain \| arabic1-minus \| arabic2-minus \| roman-lc-paren-both \| roman-uc-paren-both \| roman-lc-paren-r \| roman-uc-paren-r \| roman-lc-period \| roman-uc-period \| circle-num-db-plain \| circle-num-wd-black-plain \| circle-num-wd-white-plain \| ea1-chs-period \| ea1-chs-plain \| ea1-cht-period \| ea1-cht-plain \| ea1-jpn-chs-db-period \| ea1-jpn-kor-plain \| ea1-jpn-kor-period \| hebrew2-minus \| thai-alpha-period \| thai-alpha-paren-r \| thai-alpha-paren-both \| thai-num-period \| thai-num-paren-r \| thai-num-paren-both \| hindi-alpha-period \| hindi-num-period \| hindi-num-paren-r \| hindi-alpha1-period） / UnorderedListStyle（无序列表样式 分为两类： 1. 复合样式（按层级循环不同图标）：如 circle-hollow-square 表示第1级实心圆、第2级空心圆、第3级实心方形，超过层级数后循环 2. 单一样式（所有层级使用同一图标，不循环）：以 pptx- 前缀命名，如 pptx-circle 表示所有层级都用 ● 实心圆；枚举：circle-hollow-square \| diamond-triangle-square \| hollow-square-all \| arrow-diamond-circle \| star-hollow-circle-square \| triangle-hollow-circle-square \| solid-square-all \| solid-diamond-all \| check-all \| pptx-circle \| pptx-square \| pptx-diamond \| pptx-square-empty \| pptx-check \| pptx-triangle \| pptx-bullet \| pptx-circle-empty \| pptx-diamond-empty \| pptx-arrow-right \| pptx-star \| pptx-square-shadow） |
| `bulletColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `bulletSize` | 否 | - | `BulletSizeType` | 列表符号大小, 二选一: - 百分比字符串（相对于文本字号）, 取值范围 25%-400%, 如 "100%" - 绝对像素值, 取值范围 6-400, 如 "14"；联合类型：字符串；格式正则：(2[5-9]\|[3-9][0-9]\|[1-3][0-9]{2}\|400)% / 格式正则：[6-9]\|[1-9][0-9]\|[1-3][0-9]{2}\|400 |
| `autoStartAt` | 否 | - | `AutoStartAtType` | 有序列表起始编号, 取值范围 [1, 32767]；正整数（> 0）；限制：>= 1，<= 32767 |
| `bulletChar` | 否 | - | `BulletCharType` | 自定义列表符号, 如 "★", "→", "✓", "◆", 也支持 emoji；字符串；限制：最短长度 1，最长长度 8 |
| `marginLeft` | 否 | - | `double` | 浮点数 |
| `marginRight` | 否 | - | `double` | 浮点数 |
| `indent` | 否 | - | `NonNegativeDouble` | 浮点数；限制：>= 0.0 |
| `tabStopPos` | 否 | - | `TabStopPosType` | Tab 停止位列表, 用于 content@tabStopPos 或 p@tabStopPos, p 优先级更高。 格式为 位置+对齐方式, 逗号分隔, 如 "100r,200l,300ctr"; 对齐方式支持 l/ctr/r/dec。 位置单位 px, 有限正数, 支持小数, 范围 (0,4031]; 列表长度 1-32。 消费方按位置升序处理; 同一生效配置内位置不重复, 由 Node 层校验。 遇到 tab 元素时, 使用第一个大于当前行内坐标的停止位; 不存在则按 defaultTabSize 步进。；字符串；格式正则：(0\.\d*[1-9]\d*\|([1-9]\d{0,2}\|[1-3]\d{3}\|40[0-2]\d\|4030)(\.\d+)?\|4031(\.0+)?)(l\|ctr\|r\|dec)(,(0\.\d*[1-9]\d*\|([1-9]\d{0,2}\|[1-3]\d{3}\|40[0-2]\d\|4030)(\.\d+)?\|4031(\.0+)?)(l\|ctr\|r\|dec)){0,31} |
| `defaultTabSize` | 否 | - | `TabSizeType` | Tab 默认间距, 单位 px, 有限正数, 支持小数, 取值范围 (0,4031]；十进制数；限制：> 0，<= 4031 |

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<p>文本</p>
```

## `<polyline>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：折线, 连接符, 折线连接符, 弯折连接符, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- `bent-connector2`…`bent-connector5` 和 `curved-connector2`…`curved-connector5` 是 `<polyline>` 的 `type`，不是 `<shape>` 的 `type`。
- 折线/曲线元素, 支持多种连接类型和自定义路径 属性说明: - id: 折线唯一标识符(可选) - type: 线条类型, 参考 LineType 枚举 - topLeftX/topLeftY: 外接矩形左上角坐标 - width/height: 外接矩形宽高尺寸 - presetHandlers: 控制折线/曲线的调节点位置 - rotation: 旋转角度 [0,360) 度) - flipX/flipY: 水平/垂直翻转 - alpha: 不透明度[0,1] 坐标系统说明: - topLeftX/topLeftY 定义外接矩形的位置 - width/height 定义外接矩形的大小 子元素: - border: 线条样式(颜色/宽度/虚线等), 必需, 线条必须有边框样式, 空border标签表示默认样式(颜色:rgba(43, 47, 54, 1)), 宽度: 2px) - startArrow: 起点箭头, 可选 - endArrow: 终点箭头, 可选 - shadow: 外阴影效果, 可选, 无shadow标签表示无外阴影效果, 空shadow标签表示默认外阴影效果 - reflection: 倒影效果, 可选, 无reflection标签表示无倒影效果, 空reflection标签表示默认倒影效果

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `type` | 否 | 默认 `bent-connector2` | `PolylineType` | 曲线线条类型枚举；字符串；枚举：bent-connector2 \| bent-connector3 \| bent-connector4 \| bent-connector5 \| curved-connector2 \| curved-connector3 \| curved-connector4 \| curved-connector5 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `presetHandlers` | 否 | - | `string` | 字符串 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

任意顺序各一次[`border`，`startArrow`（0..1），`endArrow`（0..1），`shadow`（0..1），`reflection`（0..1）]

### 最小可用 XML

```xml
<polyline type="bent-connector3" topLeftX="0" topLeftY="0" width="100" height="60">
  <border color="rgb(0,0,0)" width="1"/>
</polyline>
```

## `<presentation>`

- 声明类型：`PresentationType`
- 出现场景：全局
- 中文检索词：宽, 宽度, 高, 高度

### 高优先级约束

- 演示文稿根类型, 包含整个幻灯片文档结构 - title: 演示文稿标题(可选) - theme: 全局主题设置(可选) - slide: 幻灯片页面(1-100页) 属性： - id: 演示文稿唯一标识符(可选) - width: 演示文稿宽度像素值(必选) - height: 演示文稿高度像素值(必选)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `width` | 是 | - | `positiveInteger` | 正整数（> 0） |
| `height` | 是 | - | `positiveInteger` | 正整数（> 0） |

### 子元素（内容模型）

按顺序[`title`（0..1），`theme`（0..1），`slide`（1..100）]

### 最小可用 XML

```xml
<presentation width="100" height="100"><slide/></presentation>
```

## `<reflection>`

- 声明类型：`ReflectionType`
- 出现场景：<shape>; <line>; <polyline>; <img>; <icon>; <embed>; <chart>
- 父元素：`<chart>`, `<embed>`, `<icon>`, `<img>`, `<line>`, `<polyline>`, `<shape>`
- 中文检索词：透明度, 不透明度

### 高优先级约束

- 倒影效果配置 - alpha: 倒影不透明度, 取值范围 [0,1] - offset: 倒影偏移量, 取值范围 [0,200]（倒影与原始元素的间距, 单位为像素） - size: 倒影大小, 取值范围 [0,1]（相对于原始元素高度的比例） 注意:空标签表示默认倒影效果(alpha=1, offset=8, size=0.3)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |
| `offset` | 否 | 默认 `8` | `Range0To200Type` | 整数范围类型：[0,200]；非负整数（>= 0）；限制：>= 0，<= 200 |
| `size` | 否 | 默认 `0.3` | `RatioType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<reflection/>
```

## `<shadow>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<chart>`, `<del>`, `<em>`, `<embed>`, `<field>`, `<icon>`, `<img>`, `<line>`, `<outline>`, `<p>`, `<polyline>`, `<shadow>`, `<shape>`, `<span>`, `<strong>`, `<u>`
- 中文检索词：阴影, 颜色, 对齐

### 高优先级约束

- 文本阴影效果内联元素 可以对文本的特定部分应用阴影效果, 内联元素shadow只支持基础属性

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `offset` | 否 | 默认 `15` | `Range0To200DotType` | 小数范围类型：[0,200]；浮点数；限制：>= 0，<= 200 |
| `blur` | 否 | 默认 `35` | `PercentageType` | 浮点数；限制：>= 0，<= 100 |
| `angle` | 否 | 默认 `45` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `hScale` | 否 | 默认 `1` | `ScaleType` | 缩放比例, 取值范围 [-2,2]（1为原始大小, 小于1缩小, 大于1放大）；浮点数；限制：>= -2，<= 2 |
| `vScale` | 否 | 默认 `1` | `ScaleType` | 缩放比例, 取值范围 [-2,2]（1为原始大小, 小于1缩小, 大于1放大）；浮点数；限制：>= -2，<= 2 |
| `hSkew` | 否 | 默认 `0` | `SkewType` | 斜切角度, 取值范围 [-90,90]（单位为度）；浮点数；限制：>= -90，<= 90 |
| `vSkew` | 否 | 默认 `0` | `SkewType` | 斜切角度, 取值范围 [-90,90]（单位为度）；浮点数；限制：>= -90，<= 90 |
| `align` | 否 | 默认 `top-left` | `AlignType` | 字符串；枚举：top-left \| top \| top-right \| left \| center \| right \| bottom-left \| bottom \| bottom-right |

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline`]（0..unbounded）

### 最小可用 XML

```xml
<shadow/>
```

## `<shadow>`

- 声明类型：`ShadowType`
- 出现场景：<shape>; <line>; <polyline>; <img>; <icon>; <embed>; <chart>
- 父元素：`<a>`, `<chart>`, `<del>`, `<em>`, `<embed>`, `<field>`, `<icon>`, `<img>`, `<line>`, `<outline>`, `<p>`, `<polyline>`, `<shadow>`, `<shape>`, `<span>`, `<strong>`, `<u>`
- 中文检索词：阴影, 颜色, 对齐

### 高优先级约束

- 外阴影效果配置 基础属性: - color: 阴影颜色 - offset: 阴影偏移距离（像素）, 取值范围 [0, 200]（阴影距离元素的距离, 单位为像素） - angle: 阴影角度, 取值范围 [0, 360)（0度为向右, 90度为向下, 顺时针） - blur: 模糊半径（像素）, 取值范围 [0, 100], 值越大越模糊 变形属性（可选）: - hScale: 水平缩放比例, 取值范围 [-2, 2]（1为原始大小, 小于1缩小, 大于1放大） - vScale: 垂直缩放比例, 取值范围 [-2, 2]（1为原始大小, 小于1缩小, 大于1放大） - hSkew: 水平斜切角度, 取值范围 [-90, 90]（负值向左倾斜, 正值向右倾斜） - vSkew: 垂直斜切角度, 取值范围 [-90, 90]（负值向上倾斜, 正值向下倾斜） 对齐方式: - shadowAlign: 阴影相对于元素的对齐方式（默认为top-left左上对齐） 注意: - 空标签表示默认阴影效果(color=rgba(0, 0, 0, 0.25), offset=15, blur=35, angle=45)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `offset` | 否 | 默认 `15` | `Range0To200DotType` | 小数范围类型：[0,200]；浮点数；限制：>= 0，<= 200 |
| `blur` | 否 | 默认 `35` | `PercentageType` | 浮点数；限制：>= 0，<= 100 |
| `angle` | 否 | 默认 `45` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `hScale` | 否 | 默认 `1` | `ScaleType` | 缩放比例, 取值范围 [-2,2]（1为原始大小, 小于1缩小, 大于1放大）；浮点数；限制：>= -2，<= 2 |
| `vScale` | 否 | 默认 `1` | `ScaleType` | 缩放比例, 取值范围 [-2,2]（1为原始大小, 小于1缩小, 大于1放大）；浮点数；限制：>= -2，<= 2 |
| `hSkew` | 否 | 默认 `0` | `SkewType` | 斜切角度, 取值范围 [-90,90]（单位为度）；浮点数；限制：>= -90，<= 90 |
| `vSkew` | 否 | 默认 `0` | `SkewType` | 斜切角度, 取值范围 [-90,90]（单位为度）；浮点数；限制：>= -90，<= 90 |
| `align` | 否 | 默认 `top-left` | `AlignType` | 字符串；枚举：top-left \| top \| top-right \| left \| center \| right \| bottom-left \| bottom \| bottom-right |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<shadow/>
```

## `<shape>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：形状, 文本框, 矩形, 圆角矩形, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度, 旋转, 角度, 透明度, 不透明度

### 高优先级约束

- 图形元素, 支持多种形状和文本内容 属性说明: - id: 图形唯一标识符(可选) - type: 图形类型 (rect/ellipse/triangle等, 其中text是文本框), 必须。 - topLeftX/topLeftY: 左上角坐标, 必须 - width/height: 宽高尺寸, 必须 - rotation: 旋转角度[0, 360) - path: 自定义路径(仅当type=custom时有效), 可选 - presetHandlers: 图形控制点设置(例如：圆角设置), 可选 - flipX/flipY: 水平/垂直翻转, 可选, 默认false - vert: 文本垂直对齐方式, 可选 - alpha: 不透明度[0,1], 可选 子元素: - fill: 填充样式, 可选, 无fill标签表示无填充, 空fill标签表示默认填充样式(type="text"的默认填充颜色为透明rgba(255, 255, 255, 0), 其他类型的默认填充颜色为rgba(222, 224, 227, 1))) - border: 边框样式, 可选 - 无border标签: 无边框 - 空border标签: 默认边框 - type="text": 透明边框 rgba(255, 255, 255, 0) - type为其他值: 纯色取 S+10%, B-10%；渐变色各颜色停靠点取 S+10%, B-10%；图片/图案无边框 - content: 图形内的文本内容, 可选, 富文本 - reflection: 倒影效果, 可选, 无reflection标签表示无倒影效果, 空reflection标签表示默认倒影效果 - shadow: 外阴影效果, 可选, 无shadow标签表示无外阴影效果, 空shadow标签表示默认外阴影效果

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `type` | 是 | - | `ShapeType` | 图形形状类型枚举；字符串；枚举：custom \| rect \| ellipse \| text \| triangle \| rt-triangle \| slides-lt-triangle \| pentagon \| hexagon \| heptagon \| octagon \| decagon \| dodecagon \| diamond \| parallelogram \| trapezoid \| non-isosceles-trapezoid \| round-rect \| slides-full-round-rect \| round2diag-rect \| round1rect \| round2same-rect \| snip-round-rect \| snip1rect \| snip2diag-rect \| snip2same-rect \| slides-star \| star4 \| star5 \| star6 \| star7 \| star8 \| star10 \| star12 \| star16 \| star24 \| star32 \| right-arrow \| left-arrow \| up-arrow \| down-arrow \| left-right-arrow \| slides-left-right-arrow \| up-down-arrow \| quad-arrow \| left-right-up-arrow \| left-up-arrow \| bent-arrow \| bent-up-arrow \| curved-right-arrow \| curved-left-arrow \| curved-up-arrow \| curved-down-arrow \| striped-right-arrow \| notched-right-arrow \| circular-arrow \| left-circular-arrow \| left-right-circular-arrow \| swoosh-arrow \| uturn-arrow \| slides-round-rect-callout1 \| slides-round-rect-callout2 \| slides-round-rect-callout3 \| slides-wedge-rect-callout \| slides-wedge-round-rect-callout \| callout1 \| callout2 \| callout3 \| accent-callout1 \| accent-callout2 \| accent-callout3 \| border-callout1 \| border-callout2 \| border-callout3 \| accent-border-callout1 \| accent-border-callout2 \| accent-border-callout3 \| wedge-rect-callout \| wedge-round-rect-callout \| wedge-ellipse-callout \| cloud-callout \| right-arrow-callout \| left-arrow-callout \| up-arrow-callout \| down-arrow-callout \| left-right-arrow-callout \| up-down-arrow-callout \| quad-arrow-callout \| flow-chart-process \| flow-chart-alternate-process \| flow-chart-decision \| flow-chart-input-output \| flow-chart-predefined-process \| flow-chart-internal-storage \| flow-chart-document \| flow-chart-multidocument \| flow-chart-terminator \| flow-chart-preparation \| flow-chart-manual-input \| flow-chart-manual-operation \| flow-chart-connector \| flow-chart-offpage-connector \| flow-chart-punched-card \| flow-chart-punched-tape \| flow-chart-summing-junction \| flow-chart-or \| flow-chart-collate \| flow-chart-sort \| flow-chart-extract \| flow-chart-merge \| flow-chart-offline-storage \| flow-chart-online-storage \| flow-chart-magnetic-tape \| flow-chart-magnetic-disk \| flow-chart-magnetic-drum \| flow-chart-display \| flow-chart-delay \| action-button-blank \| action-button-home \| action-button-help \| action-button-information \| action-button-forward-next \| action-button-back-previous \| action-button-end \| action-button-beginning \| action-button-return \| action-button-document \| action-button-sound \| action-button-movie \| slides-home-plate \| home-plate \| slides-chevron \| chevron \| pie \| pie-wedge \| donut \| arc \| slides-block-arc \| block-arc \| chord \| left-brace \| right-brace \| left-bracket \| right-bracket \| brace-pair \| bracket-pair \| teardrop \| can \| cube \| bevel \| folded-corner \| smiley-face \| heart \| lightning-bolt \| sun \| moon \| cloud \| irregular-seal1 \| irregular-seal2 \| ribbon \| ribbon2 \| ellipse-ribbon \| ellipse-ribbon2 \| left-right-ribbon \| vertical-scroll \| horizontal-scroll \| wave \| double-wave \| plus \| math-plus \| math-minus \| math-multiply \| math-divide \| math-equal \| math-not-equal \| corner \| diag-stripe \| frame \| half-frame \| funnel \| gear6 \| gear9 \| plaque \| plaque-tabs \| corner-tabs \| square-tabs \| chart-plus \| chart-star \| chart-x \| no-smoking \| line-inv |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `width` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 是 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `rotation` | 否 | 默认 `0` | `RotationType` | 浮点数；限制：>= 0，< 360 |
| `path` | 否 | - | `string` | 字符串 |
| `presetHandlers` | 否 | - | `string` | 字符串 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `vert` | 否 | 默认 `horz` | `TextVertical` | 字符串；枚举：horz \| vert \| vert270 \| word-art-vert-rtl \| word-art-vert \| ea-vert |
| `alpha` | 否 | 默认 `1` | `AlphaType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

任意顺序各一次[`fill`（0..1），`border`（0..1），`reflection`（0..1），`shadow`（0..1），`content`（0..1）]

### 最小可用 XML

```xml
<shape type="rect" topLeftX="0" topLeftY="0" width="100" height="60"/>
```

## `<slide>`

- 声明类型：`SlideType`
- 出现场景：PresentationType
- 父元素：`<presentation>`

### 高优先级约束

- 单页幻灯片结构 子元素: - style: 页面样式(背景色等), style的fill默认颜色为白色rgba(255, 255, 255, 1) - data: 页面元素容器(shape/line/polyline/img/table/icon/embed/chart/undefined) - note: 演讲者备注 - animation: 页面动画配置, 本期只包含可选的页面切换 transition

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`style`（0..1），`data`（0..1），`note`（0..1），`animation`（0..1）]

### 最小可用 XML

```xml
<slide/>
```

## `<span>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`
- 中文检索词：颜色, 字号, 字体大小, 字体

### 高优先级约束

- 内联样式容器 属性: color (文本颜色), backgroundColor (背景颜色), letterSpacing (字间距)

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `color` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `backgroundColor` | 否 | - | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |
| `fontSize` | 否 | - | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontFamily` | 否 | - | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `letterSpacing` | 否 | - | `LetterSpacingType` | 字符间距, 单位: px, 取值范围 [-1000, 1000]；浮点数；限制：>= -1000，<= 1000 |
| `bold` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `italic` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `underline` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `strikethrough` | 否 | - | `boolean` | 布尔值：true / false / 1 / 0 |
| `baseline` | 否 | - | `double` | 浮点数 |

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<span/>
```

## `<startArrow>`

- 声明类型：`StartArrowStyleType`
- 出现场景：<line>; <polyline>
- 父元素：`<line>`, `<polyline>`

### 高优先级约束

- 起始箭头样式类型 - type: 起始箭头类型 - widthScale: 箭头宽度 - heightScale: 箭头高度 如果type为none, 则表示无箭头, 其他属性无效

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 否 | 默认 `none` | `ArrowType` | 箭头类型枚举定义；字符串；枚举：none \| arrow \| empty-triangle \| solid-triangle \| empty-diamond \| solid-diamond \| empty-circle \| solid-circle |
| `widthScale` | 否 | - | `ArrowScaleType` | 箭头缩放等级；字符串；枚举：sm \| med \| lg |
| `heightScale` | 否 | - | `ArrowScaleType` | 箭头缩放等级；字符串；枚举：sm \| med \| lg |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<startArrow/>
```

## `<stop>`

- 声明类型：`ChartGradientStopType`
- 出现场景：ChartGradientStopsType
- 父元素：`<stops>`
- 中文检索词：颜色

### 高优先级约束

- 图表渐变色标 属性: - offset: 色标位置比例[0,1] - color: 色标颜色 - opacity: 色标透明度[0,1]

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `offset` | 是 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |
| `color` | 是 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `opacity` | 否 | - | `RatioType` | 浮点数；限制：>= 0，<= 1 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<stop offset="value" color="rgb(0,0,0)"/>
```

## `<stops>`

- 声明类型：`ChartGradientStopsType`
- 出现场景：ChartGradientType
- 父元素：`<chartBackgroundGradient>`, `<chartDomainGradient>`, `<chartGradient>`, `<fillGradient>`, `<strokeGradient>`

### 高优先级约束

- 图表渐变色标列表，至少需要2个色标

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`stop`（2..unbounded）]

### 最小可用 XML

```xml
<stops><stop offset="value" color="rgb(0,0,0)"/></stops>
```

## `<strokeGradient>`

- 声明类型：`ChartGradientType`
- 出现场景：ChartSeriesPointsType; ChartSeriesLineType; ChartSeriesBarsType
- 父元素：`<chartBars>`, `<chartLine>`, `<chartPoints>`

### 高优先级约束

- 图表渐变配置 属性: - type: 渐变类型(linear|radial) - x0/y0/x1/y1: 线性渐变起止点坐标 - r0/r1: 径向渐变半径 - gradientMethod: 渐变算法/插值方式 子元素: - stops: 渐变色标列表

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `ChartGradientKindType` | 图表渐变类型 可选值: linear(线性渐变) \| radial(径向渐变)；字符串；枚举：linear \| radial |
| `x0` | 否 | - | `double` | 浮点数 |
| `y0` | 否 | - | `double` | 浮点数 |
| `x1` | 否 | - | `double` | 浮点数 |
| `y1` | 否 | - | `double` | 浮点数 |
| `r0` | 否 | - | `double` | 浮点数 |
| `r1` | 否 | - | `double` | 浮点数 |
| `gradientMethod` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

按顺序[`stops`]

### 最小可用 XML

```xml
<strokeGradient type="linear"><stops><stop offset="value" color="rgb(0,0,0)"/></stops></strokeGradient>
```

## `<strong>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 粗体/加重文本

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<strong/>
```

## `<style>`

- 声明类型：`匿名 complexType`
- 出现场景：SlideType
- 父元素：`<slide>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

任意顺序各一次[`fill`（0..1）]

### 最小可用 XML

```xml
<style/>
```

## `<sub-headline>`

- 声明类型：`匿名 complexType`
- 出现场景：TextStylesType
- 父元素：`<textStyles>`
- 中文检索词：字体, 字号, 字体大小

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontFamily` | 否 | 默认 `思源黑体` | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `fontSize` | 否 | 默认 `32` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontColor` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<sub-headline/>
```

## `<tab>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 文本级制表符占位元素, 不携带属性

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<tab/>
```

## `<table>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`
- 中文检索词：表格, 左上角 X, 横坐标, 位置, 左上角 Y, 纵坐标, 宽, 宽度, 高, 高度

### 高优先级约束

- 表格元素, 用于展示结构化数据 宽高分配规则参考 HTML table 的整体值 / 子项值处理逻辑, 但在 SXSD 中做确定化约束, 以保证跨端实现一致。 边框规则： - 后设置优先：相邻单元格线条只有一个颜色, 如果均设置, 则右下单元格的设置覆盖左上单元格 - 不设置边框属性时使用默认样式 填充规则： - 单元格可设置独立填充样式 - 不设置填充属性时使用表格默认样式 table 属性: - id: 表格唯一标识符(可选) - topLeftX/topLeftY: 左上角坐标 - flipX/flipY: 水平/垂直翻转 - width: 表格目标总宽度(可选)。若设置, 优先用于为未填写列宽的列分配剩余宽度; 当所有列宽均为空时, 所有列均分该值; 当所有列均已填写且该值大于已填写列宽总和时, 多出空间继续分配给现有列, 默认按各列当前宽度作为权重分配; 当已填写列宽之和超过或无法容纳该值时, 保留已填写列宽, 并以最终列宽总和回写 table.width - height: 表格目标总高度(可选)。若设置, 优先用于为未填写行高的行分配剩余高度; 当所有行高均为空时, 所有行均分该值; 当所有行均已填写且该值大于已填写行高总和时, 多出空间继续分配给现有行, 默认按各行当前高度作为权重分配; 当已填写行高之和超过或无法容纳该值时, 保留已填写行高, 并以最终行高总和回写 table.height table 子元素: - colgroup: 列组元素, 用于定义列的宽度 - tr: 行元素, 包含多个单元格 colgroup 子元素: - col: 列元素 col 属性: - span: 列跨数, 默认为1, 可选 - width: 列宽度输入值, 默认值为110, 可选。无 table.width 时, 已填写列保持原值, 空列使用默认值; 有 table.width 时, 已填写列保持原值, 空列优先均分剩余宽度; 若不存在空列且 table.width 大于已填写列宽总和, 则多出空间按各列当前宽度作为权重分配到所有列; 若剩余宽度不足则空列回退为默认值, 并以最终列宽总和作为 table.width tr 属性: - height: 行高输入值, 默认值为37, 可选。无 table.height 时, 已填写行保持原值, 空行使用默认值; 有 table.height 时, 已填写行保持原值, 空行优先均分剩余高度; 若不存在空行且 table.height 大于已填写行高总和, 则多出空间按各行当前高度作为权重分配到所有行; 若剩余高度不足则空行回退为默认值, 并以最终行高总和作为 table.height。若行高低于内容高度, 需要手动修改行高 tr 子元素: - td: 单元格元素, 用于显示数据 td 属性: - id: 单元格唯一标识符(可选) - colspan: 单元格跨列数, 默认为1 - rowspan: 单元格跨行数, 默认为1 td 子元素: - borderTop/borderRight/borderBottom/borderLeft: 单元格边框样式, 无border标签代表无边框, 空border标签代表使用默认样式(实线边框, 颜色为rgba(221, 222, 223, 1), 宽度为1) - fill: 单元格填充样式, 无fill标签代表不填充, 空fill标签代表使用默认样式(默认颜色填充, 颜色为rgba(255, 255, 255, 1)) - content: 单元格内容。内容默认不反向修改表格几何尺寸; 当内容高度大于当前行高时, 需要手动修改行高

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `topLeftX` | 是 | - | `XType` | 浮点数；限制：>= -8640，<= 10560 |
| `topLeftY` | 是 | - | `YType` | 浮点数；限制：>= -4860，<= 5940 |
| `flipX` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `flipY` | 否 | 默认 `false` | `boolean` | 布尔值：true / false / 1 / 0 |
| `width` | 否 | - | `PositiveSize` | 浮点数；限制：> 0 |
| `height` | 否 | - | `PositiveSize` | 浮点数；限制：> 0 |

### 子元素（内容模型）

按顺序[`colgroup`（0..1），`tr`（1..unbounded）]

### 最小可用 XML

```xml
<table topLeftX="0" topLeftY="0"><tr><td/></tr></table>
```

## `<td>`

- 声明类型：`匿名 complexType`
- 出现场景：<tr>
- 父元素：`<tr>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `colspan` | 否 | 默认 `1` | `PositiveSize` | 浮点数；限制：> 0 |
| `rowspan` | 否 | 默认 `1` | `PositiveSize` | 浮点数；限制：> 0 |

### 子元素（内容模型）

任意顺序各一次[`borderTop`（0..1），`borderRight`（0..1），`borderBottom`（0..1），`borderLeft`（0..1），`fill`（0..1），`content`（0..1）]

### 最小可用 XML

```xml
<td/>
```

## `<textStyles>`

- 声明类型：`TextStylesType`
- 出现场景：ThemeType
- 父元素：`<theme>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`title`（0..1），`headline`（0..1），`sub-headline`（0..1），`body`（0..1），`caption`（0..1）]

### 最小可用 XML

```xml
<textStyles/>
```

## `<theme>`

- 声明类型：`ThemeType`
- 出现场景：PresentationType
- 父元素：`<presentation>`
- 中文检索词：主题, 配色

### 高优先级约束

- 主题类型 子元素: - background: 背景填充, 可选, 默认白色rgba(255, 255, 255, 1) - textStyles: 文本样式集合

### 完整可用属性

无属性。

### 子元素（内容模型）

按顺序[`background`（0..1），`textStyles`（0..1）]

### 最小可用 XML

```xml
<theme/>
```

## `<title>`

- 声明类型：`匿名 complexType`
- 出现场景：TextStylesType
- 父元素：`<presentation>`, `<textStyles>`
- 中文检索词：字体, 字号, 字体大小

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `fontFamily` | 否 | 默认 `思源黑体` | `FontFamilyType` | 字体族名称, 支持任意字体。 常用中文字体： 思源宋体、寒蝉德黑体、标小智无界黑、寒蝉锦书宋、站酷小薇体、 寒蝉团圆体 圆体、寒蝉团圆体 黑体、荆南缘默体、寒蝉端黑宋、 资源圆体、钟齐流江毛草、寒蝉端黑体、站酷庆科黄油体、寒蝉云墨黑、 有字库龙藏体、寒蝉全圆体、思源黑体、钟齐志莽行书、抖音美好体、 马善政毛笔楷体、霞鹜 975 圆体、阿里妈妈刀隶体、阿里妈妈东方大楷、 精品点阵体、站酷文艺体、寒蝉正楷体、朱雀仿宋 常用拉丁字体： Francois One、Heebo、Lobster、Roboto Slab、Varela Round、 PT Serif、Signika、Vollkorn、Mulish、Rokkitt、Inconsolata、 PT Sans Caption、EB Garamond、Dancing Script、Rajdhani、Poppins、 Merriweather、PT Sans Narrow、Libre Baskerville、Slabo 27px、 Inter、Noto Serif、Yanone Kaffeesatz、Merriweather Sans、Lato、 Source Code Pro、Mukta、Teko、Hind Siliguri、Catamaran、Arvo、 Alegreya Sans、Titillium Web、Roboto Mono、Play、Indie Flower、 Ubuntu Condensed、Libre Franklin、Barlow、PT Sans、Acme、Cuprum、 Josefin Sans、DM Sans、Playfair Display、Rubik、Questrial、Anton、 Oswald、Cabin、Ubuntu、Abel、Exo 2、Bree Serif、Roboto Condensed、 Amatic SC、Abril Fatface、Comfortaa、IBM Plex Sans、Work Sans、 Kanit、Noto Sans、Alegreya、Shadows Into Light、Barlow Condensed、 Nunito Sans、Quicksand、Overpass、Bebas Neue、Raleway、Exo、 Archivo Narrow、Hind、Open Sans、Poiret One、Asap、Roboto、Nunito、 Bitter、Dosis、Oxygen、Prompt、Karla、Fjalla One、Fira Sans、 Crimson Text、Pacifico、Arimo、Maven Pro、Cairo、Montserrat、 Righteous、Lora、ZCOOL Addict Italic 其他语言字体： 源ノ角ゴシック、본고딕、Nanum Gothic 系统字体： Arial、Arial Black、Calibri、Comic Sans Ms、Sans Serif、Serif、 Times New Roman、Tahoma、Trebuchet MS、Verdana、Georgia、Garamond、 黑体、宋体、楷体、Hiragino Mincho；字符串 |
| `fontSize` | 否 | 默认 `54` | `FontSizeType` | 字体大小, 浮点数, 范围 [1, 4000], 单位px 示例：10, 10.5, 12, 14, 16, 18, 20, 24, 28, 32 等；浮点数；限制：>= 1，<= 4000 |
| `fontColor` | 否 | 默认 `rgba(0, 0, 0, 0.25)` | `Color` | 颜色格式, 支持纯色和渐变色；联合类型：SolidColor（支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))） / GradientColor（渐变色格式支持以下类型： - 线性渐变： 语法：linear-gradient(角度, 颜色停靠点, 颜色停靠点, ...) 角度：[0,360)数字 + deg，如 90deg、180deg，表示渐变方向 颜色停靠点：定义渐变中每个颜色的位置（参见“颜色停靠点说明”） 示例：linear-gradient(90deg, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 射线渐变: 语法：radial-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在半径方向上的分布（参见“颜色停靠点说明”） 示例：radial-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 矩形渐变: 语法：rect-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：定义渐变中心的位置（参见“中心位置说明”） 颜色停靠点：定义颜色在矩形范围内的分布（参见“颜色停靠点说明”） 示例：rect-gradient(circle at 0% 0%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) - 形状渐变: 语法：shape-gradient(circle [at 中心位置], 颜色停靠点, 颜色停靠点, ...) 形状：circle，仅支持 circle 形状 中心位置：仅支持 50% 50%，若输入其他位置，将回退为 50% 50% 颜色停靠点：定义颜色分布（参见“颜色停靠点说明”） 示例：shape-gradient(circle at 50% 50%, rgb(255, 0, 0) 0%, rgb(0, 0, 255) 100%) -------------------------------------------------------- 中心位置说明: 所有非线性渐变（射线渐变、矩形渐变、形状渐变）均可指定渐变中心位置： - 格式：x% y%，为百分比格式 (0-100% 0-100%)，表示相对于容器宽高的比例位置 - 支持以下枚举值： 0% 0%：左上角 100% 0%：右上角 50% 50%：中心 0% 100%：左下角 100% 100%：右下角 - 若位置超出支持范围或格式错误，将会被回退为 50% 50% 颜色停靠点说明： - 格式：颜色 位置% - 颜色：必须为 rgb(r,g,b) 或 rgba(r,g,b,a) 格式 - 无透明通道: rgb(r,g,b)，其中 r,g,b 为 [0,255] 的整数 - 含透明通道: rgba(r,g,b,a)，其中 r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 颜色停靠点（color stop）: - 定义：颜色在渐变路径上的位置，至少需要 2 个颜色停靠点 - 位置：整数百分比，取值范围 [0, 100]，后跟 % 符号；格式正则：linear-gradient\(\s*\d+deg\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 radial-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 rect-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\) 或 shape-gradient\(\s*circle(\s+at\s+\d{1,3}%\s+\d{1,3}%)?\s*,\s*((rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)(\s*,\s*(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\))\s+\d{1,3}%)+\s*\)） |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<title/>
```

## `<title>`

- 声明类型：`string`
- 出现场景：PresentationType
- 父元素：`<presentation>`, `<textStyles>`

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

无属性。

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<title>value</title>
```

## `<tr>`

- 声明类型：`匿名 complexType`
- 出现场景：<table>
- 父元素：`<table>`
- 中文检索词：高, 高度

### 高优先级约束

- XSD 未声明额外语义约束；仍须遵守下表中的类型、必填项和默认值。

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `height` | 否 | 默认 `37` | `PositiveSize` | 浮点数；限制：> 0 |

### 子元素（内容模型）

按顺序[`td`（1..unbounded）]

### 最小可用 XML

```xml
<tr><td/></tr>
```

## `<transition>`

- 声明类型：`TransitionType`
- 出现场景：<animation>
- 父元素：`<animation>`

### 高优先级约束

- 页面切换节点。生成页面时仅使用 fade / cover / pull / push 四种效果；none 用于显式关闭切换。

### 生成页面可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `type` | 是 | - | `TransitionEffectType` | 字符串；枚举：none \| fade \| cover \| pull \| push |
| `durationMs` | 否 | - | `TransitionDurationType` | 整数；限制：>= 0，<= 86399999；默认 1000 毫秒 |
| `style` | 否 | - | `TransitionStyleType` | 字符串；枚举：smoothly \| through-black；仅 fade 使用 |
| `direction` | 否 | - | `TransitionDirectionType` | 字符串；枚举：from-bottom \| from-top \| from-left \| from-right；仅 push / cover / pull 使用 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<transition type="none"/>
```

## `<u>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<a>`, `<del>`, `<em>`, `<field>`, `<outline>`, `<p>`, `<shadow>`, `<span>`, `<strong>`, `<u>`

### 高优先级约束

- 下划线文本

### 完整可用属性

无属性。

### 子元素（内容模型）

选择其一[`br` | `tab` | `formula` | `strong` | `em` | `u` | `span` | `del` | `a` | `shadow` | `outline` | `field`]（0..unbounded）

### 最小可用 XML

```xml
<u/>
```

## `<ul>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<content>`

### 高优先级约束

- 无序列表 属性说明: - listStyle: 列表样式 - bulletColor: 列表符号颜色（纯色）, 可选 - bulletSize: 列表符号大小, 可选, 百分比字符串（相对于文本字号, 取值范围 25%-400%）或绝对像素值（取值范围 6-400） - bulletChar: 自定义列表符号字符, 可选, 设置后覆盖 listStyle 的符号

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `listStyle` | 否 | 默认 `circle-hollow-square` | `UnorderedListStyle` | 无序列表样式 分为两类： 1. 复合样式（按层级循环不同图标）：如 circle-hollow-square 表示第1级实心圆、第2级空心圆、第3级实心方形，超过层级数后循环 2. 单一样式（所有层级使用同一图标，不循环）：以 pptx- 前缀命名，如 pptx-circle 表示所有层级都用 ● 实心圆；字符串；枚举：circle-hollow-square \| diamond-triangle-square \| hollow-square-all \| arrow-diamond-circle \| star-hollow-circle-square \| triangle-hollow-circle-square \| solid-square-all \| solid-diamond-all \| check-all \| pptx-circle \| pptx-square \| pptx-diamond \| pptx-square-empty \| pptx-check \| pptx-triangle \| pptx-bullet \| pptx-circle-empty \| pptx-diamond-empty \| pptx-arrow-right \| pptx-star \| pptx-square-shadow |
| `bulletColor` | 否 | - | `SolidColor` | 支持 RGB/RGBA 两种颜色格式： - RGB: rgb(r,g,b) - 说明：r,g,b 为 [0,255] 的整数 - 示例：rgb(255,0,0) - RGBA: rgba(r,g,b,a) - 说明：r,g,b 为 [0,255] 的整数，a 为 0 或 0.x ... 1 或 1.0 的浮点数 - 示例：rgba(255,0,0,0.5) 注意：允许空格，如 rgb(255, 0, 0) 也是有效格式；字符串；格式正则：(rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)\|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0(\.\d+)?\|1(\.0+)?)\s*\)) |
| `bulletSize` | 否 | - | `BulletSizeType` | 列表符号大小, 二选一: - 百分比字符串（相对于文本字号）, 取值范围 25%-400%, 如 "100%" - 绝对像素值, 取值范围 6-400, 如 "14"；联合类型：字符串；格式正则：(2[5-9]\|[3-9][0-9]\|[1-3][0-9]{2}\|400)% / 格式正则：[6-9]\|[1-9][0-9]\|[1-3][0-9]{2}\|400 |
| `bulletChar` | 否 | - | `BulletCharType` | 自定义列表符号, 如 "★", "→", "✓", "◆", 也支持 emoji；字符串；限制：最短长度 1，最长长度 8 |

### 子元素（内容模型）

按顺序[`li`（1..unbounded）]

### 最小可用 XML

```xml
<ul><li><p/></li></ul>
```

## `<undefined>`

- 声明类型：`匿名 complexType`
- 出现场景：全局
- 父元素：`<data>`

### 高优先级约束

- 未定义元素, 用于处理不支持的形状类型, 当导出时遇到不支持的type数据时, 使用此元素替代 属性说明: - id: 元素唯一标识符(可选) - type: 原始的不支持的类型名称, 包括 video(视频), audio(音频), whiteboard(画板）

### 完整可用属性

| 属性 | 必需 | 默认/固定 | 类型 | 枚举、数值与格式约束 |
|---|---|---|---|---|
| `id` | 否 | - | `string` | 字符串 |
| `type` | 否 | - | `string` | 字符串 |

### 子元素（内容模型）

无。

### 最小可用 XML

```xml
<undefined/>
```
