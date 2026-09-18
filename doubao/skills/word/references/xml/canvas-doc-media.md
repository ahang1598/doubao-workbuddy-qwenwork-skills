# 本地 Word XML：图片

本页定义 `<img/>` 的属性、取值及浮动/嵌入结构约束。上传、更新命令和回读验证见下方命令参考，本页不重复定义。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

公共 XML 规则先读 [`canvas-doc-xml.md`](canvas-doc-xml.md)。图片插入、资源替换与属性更新的操作契约见 [`canvas-doc-media-insert.md`](../cli/canvas-doc-media-insert.md)。

## 图片

```xml
<img src="res_token"
     mime="image/png"
     alt-description="销售趋势图" alt-title="季度销售趋势"
     width="512" height="512"
     rotation="90"
     flip-horizontal="true" flip-vertical="true"
     layout="floating" wrap="square" wrap-text="both-sides"
     border-style="solid" border-width="1pt" border-color="#000000"/>
```

| 属性 | 取值格式 | 说明 |
|---|---|---|
| `src` | 资源 token，必填 | 来自 `docs +media-upload` 返回的 `file_token`，或 Fetch 已有图片得到的资源 token |
| `id` / `name` | 字符串 | Record ID 和文件名 |
| `mime` | `image/png`、`image/jpeg`、`image/gif`、`image/webp`、`image/bmp` | MIME 类型；JPEG 推荐写 `image/jpeg` |
| `caption` | 字符串 | 图注；省略该属性表示保留原图注，写 `caption=""` 表示清空 |
| `alt-description` / `alt-title` | 任意字符串，可为空 | 图片替代描述和标题；省略表示保留，空串表示显式空值 |
| `remove-alt-description` / `remove-alt-title` | `true` / `false` | `true` 清除对应 direct alt；与同名 value 属性互斥 |
| `width` / `height` | 数值，或数值带单位 | 显示尺寸。裸数字按 `pt` 解释（fetch 返回的就是这一种）；也接受 `512pt`、`6in`、`15cm` 等带单位写法 |
| `scale` | 正数倍率 | 缩放**倍率**不是百分比：`1` 是原始尺寸，`0.5` 是缩小一半 |
| `crop` | `[x1,y1,x2,y2]` | 原图保留区域的归一化坐标（左上为原点），须 `x1 < x2`、`y1 < y2`；可超出 `[0,1]` 表达 OOXML 负裁剪或外延。省略则保留原值；`[0,0,1,1]` 清除裁剪，`[0.25,0,0.75,1]` 保留水平中间 50% |
| `rotation` | 数值 | 顺时针旋转角度 |
| `flip-horizontal` / `flip-vertical` | `true` / `false` | 两个独立的镜像翻转属性 |
| `layout` | `floating`、`inline` | 浮动型或嵌入型。读方向只有浮动图片带 `layout="floating"`，嵌入型通常不带 |
| `wrap` | `none`、`square`、`tight`、`through`、`top-bottom` | 文字环绕方式，仅浮动图片有效 |
| `wrap-text` | `both-sides`、`left`、`right`、`largest` | 文字环绕侧 |
| `wrap-polygon` | JSON 点数组 | 自定义环绕多边形，形如 `[{"x":0,"y":0},{"x":21600,"y":0}]`；坐标沿用 fetch 返回值 |
| `position-h-relative-from` | `margin`、`page`、`column`、`character`、`leftMargin`、`rightMargin`、`insideMargin`、`outsideMargin` | 水平定位基准 |
| `position-v-relative-from` | `margin`、`page`、`paragraph`、`line`、`topMargin`、`bottomMargin`、`insideMargin`、`outsideMargin` | 垂直定位基准 |
| `position-h-align` / `position-v-align` | 水平 `left\|center\|right\|inside\|outside`；垂直 `top\|center\|bottom\|inside\|outside` | 与同一轴 offset / pct-offset 互斥 |
| `position-h-offset` / `position-v-offset` | 有限数值 | 每轴绝对偏移 |
| `position-h-pct-offset` / `position-v-pct-offset` | 有限数值 | 每轴百分比偏移；沿用 Fetch 返回值 |
| `simple-pos-enabled` | `true` / `false` | `true` 时使用 simple position，`false` 时使用双轴定位 |
| `simple-pos-x` / `simple-pos-y` | 有限数值 | 简单绝对坐标，必须成对出现 |
| `wrap-distance-top/right/bottom/left` | 数值 | 四向环绕间距，四个独立属性 |
| `float-effect-extent-top/right/bottom/left` | 数值 | 浮动效果外扩范围，四个独立属性 |
| `behind-doc` / `allow-overlap` / `locked` / `layout-in-cell` | `true` / `false` | 衬于文字下方、允许重叠、锁定和随单元格排版 |
| `relative-height` | 数值 | 浮动层叠顺序 |
| `border-style` | 见下方枚举 | 图片边框线型 |
| `border-width` | 数值 | 图片边框宽度。fetch 返回的是裸数值（如 `border-width="1"`）；写入时带不带 `pt` 都收 |
| `border-color` | 统一颜色格式 | 图片边框颜色，支持真实 alpha；其他对象的颜色规则见公共 XML 与各自专项 |

暂不支持 SVG、TIFF、WMF、EMF。

协议可以读取和写入尺寸、旋转、翻转、浮动、环绕、定位和边框；浮动位置须遵循下方互斥和锚点规则。

`alt-description` / `alt-title` 已支持读写，清除必须使用对应 `remove-*` 属性，不要复用 `clear` 或写一个笼统 `alt`。`href`、`action-type` 仍是协议里有、编辑器没实现的属性：写了不会失败，但值不会落到文档上，只返回一条 `ATTR_CAPABILITY_LIMITED`。图注请用 `caption`。

`src` 只接受图片资源 token，不接受普通本地文件路径或网络 URL；不支持在线文档的 `<img href="...">` 资源引用写法。

### 图片边框线型

`<img border-style>` 使用 DrawingML `a:prstDash` 枚举，大小写敏感，只接受以下 11 个值：

`solid`、`dot`、`dash`、`lgDash`、`dashDot`、`lgDashDot`、`lgDashDotDot`、`sysDash`、`sysDot`、`sysDashDot`、`sysDashDotDot`。

字符边框使用另一套 23 个 OOXML 线型，不要互相套用；不要把 `single` 写给图片，也不要把 `solid` 写给字符。

### 浮动与嵌入

- `wrap`、`wrap-text`、`position-*`、`wrap-distance-*`、`behind-doc` 等属性属于 `layout="floating"` 的 sidecar。
- 显式写 `layout="inline"` 可切回嵌入式；省略 `layout` 表示保持当前模式。
- 同一轴的 `align`、`offset`、`pct-offset` 只能出现一个；不能依赖属性顺序决定优先级。
- `simple-pos-enabled="true"` 必须同时提供 `simple-pos-x/y`，并且不能再提供水平或垂直轴位置。
- 双轴定位使用 `simple-pos-enabled="false"`，并提供目标双轴位置；位置属性表达最终几何，不表达 pointer delta。
- inline 转 floating 时系统使用现有产品规则补齐默认 sidecar。已有 floating 图片沿用原 anchor carrier，不支持通过静态 XML 跨 carrier 重新锚定。
- inline 图片的水平对齐由宿主 `<p align>` 控制，不写在 `<img>` 上；该属性同时影响同段文字和其他 inline object。段落属性语法见 [`canvas-doc-text.md`](canvas-doc-text.md)。

### 浮动定位 XML 示例

以下片段展示相对页面右下角定位与方形环绕的属性组合，不代表现有图片的完整 XML：

```xml
<img src="res_token"
     layout="floating" wrap="square"
     position-h-relative-from="page" position-h-align="right"
     position-v-relative-from="page" position-v-align="bottom"/>
```

===== 全文完 =====
